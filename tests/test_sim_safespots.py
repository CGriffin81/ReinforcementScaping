"""Ranged fights from safespots and their arrow piles (rlscape.combat.safespots; Caleb, 2026-11-07, OQ-27 (d)).

The safespots are the server's (data/ranged_safespots.csv); these tests give the sim a table of their own for a few
sites, so they don't depend on the export, and check what the sim does with it."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat import safespots as ss
from rlscape.combat.access import Progress
from rlscape.combat.candidates import Character, enemy_pool, evaluate, loot_rule, pickups_per_kill, select_candidates
from rlscape.combat.ranking import CandidateRanker
from rlscape.combat.rates import OVERHEAD_TICKS_PER_KILL, PICKUP_TICKS, Plan, combat_rates
from rlscape.combat.candidates import ANTI_DRAGON_SHIELD
from rlscape.sim.potions import ANTIFIRE
from rlscape.gamedata import server as gd
from rlscape.sim.combat import fight, guarded_trip
from rlscape.sim.equipment import fighter_for, wield_best
from rlscape.sim.state import TOLERANCE_TICKS, CharacterState

SHORTBOW, BRONZE_ARROW = 841, 882
RAT, COW, GREEN_DRAGON = 47, 81, 941
RAPID, LONGRANGE = Plan("ranged", "rapid"), Plan("ranged", "longrange")
OVERHEAD = OVERHEAD_TICKS_PER_KILL["ranged"]


def entry(npc_id: int):
    return next(e for e in enemy_pool() if e.npc.id == npc_id)


def ranger(arrows: int = 500) -> CharacterState:
    state = CharacterState.fresh()
    state.add(SHORTBOW)
    state.add(BRONZE_ARROW, arrows)
    wield_best(state, "ranged")
    return state


def spot(site, walk: int | None = 4, held: int = 9, share: float = 0.9, pickup_threats: int = 0):
    return gd.RangedSafespot((site.spawn[0] + 3, site.spawn[1], site.spawn[2]), held, share, 2.0, walk, 0,
                             pickup_threats)


@pytest.fixture
def table(monkeypatch):
    """Give the sim a safespot table of the test's own (both ranges), and return it to fill."""
    spots: dict = {}
    monkeypatch.setattr(gd, "ranged_safespots", lambda: spots)

    def put(npc_id: int, site, found):
        for tiles_range in (ss.RANGE_TILES, ss.LONGRANGE_TILES):
            spots[(npc_id, site.spawn, tiles_range)] = found
    return put


def character(state: CharacterState, loot: str = "valuable") -> Character:
    return Character(state.location, state.max_hp(), state.hp, 0.0, state.free_slots(), None, loot, Progress(),
                     float("inf"))


def test_only_a_monster_whose_damage_is_trivial_needs_no_safespot():
    """Trivial: the fight needs no food (Caleb, OQ-30 (b)). Over the option, the expected damage less the hitpoints
    regenerated meanwhile (one every 101 ticks) fits in those above the retreat point: 5 for a fresh ranger, whom a
    rat never hurts and cows' hits of 1 would take some 80 over 1,500 ticks."""
    state = ranger()
    fighter = fighter_for(state)
    rat, cow = (combat_rates(fighter, RAPID, entry(i).npc, 0.0) for i in (RAT, COW))
    margin = ss.hp_margin(state.hp, state.max_hp())
    assert margin == 5
    assert not ss.needs_safespot(rat, margin, 1500)
    assert ss.needs_safespot(cow, margin, 1500)
    left = cow.damage_taken_per_hour * 1500 / 6000 - 1500 / 101  # what the food would have to cover
    assert left > margin and not ss.needs_safespot(cow, left, 1500)  # with that much to spare, no food needed
    assert ss.hp_margin(4, 10) == 0  # under the retreat point, nothing to spare


def test_a_pile_for_every_hundred_ticks_of_shooting():
    """Arrows join a pile only while it's private, its first 100 ticks (GroundItemManager.increase)."""
    assert [ss.piles_per_kill(t) for t in (0, 35, 100, 101, 250)] == [1, 1, 1, 2, 3]
    assert ss.style_range(LONGRANGE) == 9 and ss.style_range(RAPID) == 7


def test_a_target_that_hurts_is_ranged_only_from_a_safespot(table):
    """Without a safespot a cow is no ranged candidate for a fresh ranger; with one at a site it is, there: it deals
    nothing, and each kill adds a pickup for its drops and its arrow pile and the walk to them and back."""
    state = ranger()
    cows, loot = entry(COW), loot_rule("valuable")
    fighter = fighter_for(state)
    assert evaluate(cows, fighter, RAPID, character(state), 1500, loot) is None
    site = cows.sites[0]
    table(COW, site, spot(site, walk=4))
    got = evaluate(cows, fighter, RAPID, character(state), 1500, loot)
    assert got is not None and got.site == site
    fought = combat_rates(fighter, RAPID, cows.npc, 0.0)
    piles = ss.piles_per_kill(ss.fighting_ticks(fought, OVERHEAD))
    extra = PICKUP_TICKS * (pickups_per_kill(cows.drops, loot) + piles) + 2 * 4
    assert got.rates.damage_taken_per_kill == 0 and got.rates.npc_max_hit == 0
    assert got.rates.ticks_per_kill == pytest.approx(fought.ticks_per_kill + extra)
    # a safespot that holds from too little of the monsters' wandering doesn't count
    table(COW, site, spot(site, share=ss.MIN_SHARE / 2))
    assert evaluate(cows, fighter, RAPID, character(state), 1500, loot) is None


def test_a_ranger_needs_no_shield_against_dragonfire_from_a_safespot(table):
    """A bow takes no shield, so the special-damage gear check rules green dragons out for a ranger, except from a
    safespot, where the dragon can't attack at all (its breath, like its bite, needs melee reach on this server:
    ChromaticDragonNPC's handlers)."""
    state = ranger()
    state.xp = [10.0**6] * len(state.xp)  # strong enough to hurt a dragon
    state.hp = state.max_hp()
    dragons, loot = entry(GREEN_DRAGON), loot_rule("valuable")
    fighter = fighter_for(state)
    assert state.equipment.get(5) is None  # no shield with the bow
    assert evaluate(dragons, fighter, RAPID, character(state), 1500, loot) is None
    site = dragons.sites[0]
    table(GREEN_DRAGON, site, spot(site))
    got = evaluate(dragons, fighter, RAPID, character(state), 1500, loot)
    assert got is not None and got.site == site and got.rates.damage_taken_per_kill == 0


def test_guarded_dragon_arrows_need_a_shield_to_fetch(table):
    """Where other dragons guard the arrows, they're fetched late with an anti-dragon shield worn for the trip
    (Caleb, OQ-33): a ranger carrying none isn't offered the site."""
    state = ranger()
    state.xp = [10.0**6] * len(state.xp)
    state.hp = state.max_hp()
    dragons, loot = entry(GREEN_DRAGON), loot_rule("valuable")
    site = dragons.sites[0]
    table(GREEN_DRAGON, site, spot(site, pickup_threats=2))
    fighter, who = fighter_for(state), character(state)
    assert evaluate(dragons, fighter, RAPID, who, 1500, loot) is None
    shielded = Character(**{**who.__dict__, "shields_carried": frozenset({ANTI_DRAGON_SHIELD})})
    assert evaluate(dragons, fighter, RAPID, shielded, 1500, loot) is not None


def test_a_guarded_trip_takes_the_guards_hits_and_the_shield_stops_the_breath():
    """The late trip's hits: two green dragons swinging over 40 ticks. With a shield and an antifire dose carried
    there's no breath at all, only their bites; without, the breath is up to 52 (the potion alone cuts a tenth)."""
    dragon = entry(GREEN_DRAGON).npc
    taken = {}
    for kit in ("none", "shield", "both"):
        total = 0
        for seed in range(200):
            state = ranger()
            state.xp = [10.0**6] * len(state.xp)
            state.hp = 10**4
            if kit != "none":
                state.add(ANTI_DRAGON_SHIELD)
            if kit == "both":
                state.add(ANTIFIRE[0])
            before = state.hp
            extra = guarded_trip(state, np.random.default_rng(seed), dragon, fighter_for(state), RAPID, 2, 40, 0)
            assert extra >= (2 if kit != "none" else 0)  # the shield swap, and the drink
            total += before - state.hp
        taken[kit] = total / 200
    assert taken["none"] > 3 * taken["shield"] > 0
    assert taken["both"] <= taken["shield"]


def test_arrows_that_cant_be_walked_to_are_left(table):
    """A safespot with no way to the arrows: no pile pickups or walks, only the drops'."""
    state = ranger()
    cows, loot = entry(COW), loot_rule("valuable")
    site = cows.sites[0]
    table(COW, site, spot(site, walk=None))
    got = evaluate(cows, fighter_for(state), RAPID, character(state), 1500, loot)
    fought = combat_rates(fighter_for(state), RAPID, cows.npc, 0.0)
    assert got.rates.ticks_per_kill == pytest.approx(fought.ticks_per_kill
                                                     + PICKUP_TICKS * pickups_per_kill(cows.drops, loot))


def test_the_fast_ranker_matches_the_reference_with_safespots(table):
    """rlscape.combat.ranking with safespots at some sites, as candidates.select_candidates: the same monsters,
    sites and rates."""
    for npc_id in (COW, 41, 100, 117, GREEN_DRAGON):  # cows, chickens, goblins, hill giants, green dragons
        for k, site in enumerate(entry(npc_id).sites):
            table(npc_id, site, spot(site, walk=2 + k % 5, held=1 + k % 3))
    state = ranger()
    fighter = fighter_for(state)
    plans = {"ranged": (fighter, [Plan("ranged", s) for s in ("accurate", "rapid", "longrange")])}
    for loot in ("valuable", "none"):
        who = character(state, loot)
        reference = select_candidates(enemy_pool(), plans, who, 1500)["ranged"]
        ours = CandidateRanker(enemy_pool()).select(plans, who, 1500)["ranged"]
        assert [(c.entry.npc.id, c.site.spawn, c.plan) for c in ours] == [
            (c.entry.npc.id, c.site.spawn, c.plan) for c in reference]
        for a, b in zip(ours, reference):
            assert a.total_xp_per_hour == pytest.approx(b.total_xp_per_hour)
            assert a.gp_per_hour == pytest.approx(b.gp_per_hour)
            assert a.rates.ticks_per_kill == pytest.approx(b.rates.ticks_per_kill)
        assert any(c.rates.damage_taken_per_kill == 0 for c in reference)


def run(table, walk: int, pickup_threats: int = 0, tolerated: bool = True, runs: int = 30, budget: int = 900):
    cows = entry(COW)
    site = cows.sites[0]
    table(COW, site, spot(site, walk=walk, pickup_threats=pickup_threats))
    total, hurt = 0, 0
    for seed in range(runs):
        state = ranger()
        state.location = site.spawn
        state.tick = 5_000
        state.region_since = state.tick - (TOLERANCE_TICKS if tolerated else 0)
        hp = state.hp
        result = fight(state, np.random.default_rng(seed), budget, cows, RAPID, site, loot_rule("valuable"))
        total += result.detail["kills"]
        hurt += hp - state.hp
    return total, hurt


def test_a_safespot_fight_takes_no_hits_and_walks_for_its_arrows(table):
    """From a safespot the cow never hits; a longer walk to its arrows means fewer kills in the same time."""
    near, hurt_near = run(table, walk=1)
    far, hurt_far = run(table, walk=25)
    assert hurt_near == hurt_far == 0
    assert far < near


def test_guarded_arrows_wait_until_aggression_runs_out(table):
    """With aggressive monsters guarding the arrows and aggression not yet run out, the fight leaves them until the
    oldest pile would go (200 ticks): fewer walks, so more kills than when it's safe to fetch them every kill; once
    aggression has run out, it fetches them every kill again."""
    every_kill, _ = run(table, walk=25, pickup_threats=1, tolerated=True)
    waiting, _ = run(table, walk=25, pickup_threats=1, tolerated=False)
    assert waiting > every_kill
