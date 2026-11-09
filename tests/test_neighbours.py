"""Aggressive monsters of other kinds near a fight (rlscape.combat.neighbours; Caleb, 2026-11-07, OQ-35 (a)): which
engage, how the rankers count them, and the sim's fights with them."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from rlscape.combat import neighbours as nb
from rlscape.combat import safespots as ss
from rlscape.combat.candidates import Character, Neighbours, Site, enemy_pool, loot_rule, neighbour_kills, site_rates
from rlscape.combat.rates import Plan, Rates, combat_rates
from rlscape.sim.combat import FightNeighbours, fight
from rlscape.sim.equipment import fighter_for, wield_best
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

SPADE, PICKAXE, RAT = 5414, 5413, 47
# The animated spades in the Abandoned Mine, with a possessed pickaxe spawned beside them: where ENGAGE_PER_TICK was
# fitted to the server. A hazard since 2026-11-08 (OQ-42), so not a site in the pool; the fights here still are.
SPADES = (3420, 9657, 0)
FIRE_BLAST = Plan("magic", "fire_blast")
DEATH_RUNE, AIR_RUNE, STAFF_OF_FIRE = 560, 556, 1387


def entry(npc_id: int):
    return next(e for e in enemy_pool() if e.npc.id == npc_id)


def mine_site() -> Site:
    """The spades' site in the Abandoned Mine, as the pool built it before it was a hazard: its two spades. Its bank
    is the spades' other site's (the Chaos Tunnels'), which doesn't matter here: these fights loot nothing."""
    return replace(entry(SPADE).sites[0], spawn=SPADES, spawns=2)


@pytest.fixture(autouse=True)
def no_safespots(monkeypatch):
    """Fights here stand where the monsters reach them: neighbours don't apply from a safespot, whatever the
    exported table has for these sites."""
    monkeypatch.setattr(ss, "safespot", lambda npc_id, site, plan: None)


def caster(level: int = 61) -> CharacterState:
    """A calibration caster (scripts/calibrate_combat.py, band 61): fire blast from a staff of fire."""
    state = CharacterState.fresh()
    state.inventory.clear()
    for skill in ("attack", "strength", "defence", "hitpoints", "ranged", "prayer", "magic"):
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.hp = state.max_hp()
    for item, amount in ((STAFF_OF_FIRE, 1), (DEATH_RUNE, 400), (AIR_RUNE, 1600)):
        state.add(item, amount)
    wield_best(state, "magic")
    return state


def test_a_fights_neighbours_are_the_sites_aggressive_monsters_of_other_kinds():
    neighbours = nb.site_neighbours(SPADE, SPADES)
    assert [(n.npc.id, n.spawns) for n in neighbours] == [(PICKAXE, 1)]
    assert nb.site_neighbours(PICKAXE, SPADES) == ()  # the spades aren't aggressive
    level = neighbours[0].level
    assert nb.engaging(neighbours, 2 * level) == neighbours and nb.engaging(neighbours, 2 * level + 1) == ()


def test_aggression_lasts_tolerance_ticks_after_arriving_in_another_region():
    assert nb.aggression_ticks(SPADES, (3222, 3218, 0), 0.0) == nb.TOLERANCE_TICKS
    assert nb.aggression_ticks(SPADES, (3421, 9650, 0), 250.0) == 250.0  # already there: what's left of it
    assert nb.aggression_ticks(SPADES, (3421, 9650, 1), 250.0) == nb.TOLERANCE_TICKS  # another plane


def test_neighbour_fights_take_the_place_of_target_kills():
    """By hand: a kill of 100 ticks (60 an hour, 1,000 attack XP an hour, 600 gp an hour); half a neighbour fight per
    kill of 50 ticks and 10 attack XP: 125 ticks a kill, 48 kills an hour, 800 + 0.5 x 10 x 48 = 1,040 XP an hour."""
    rates = Rates(60.0, {"attack": 1000.0}, 600.0, 120.0, 30.0, 0.5, 3, 0.4, 2, 100.0, 2.0, 0.5, 20.0)
    kill = nb.NeighbourKill(50.0, {"attack": 10.0}, 4.0, 1.0, 0.0, 0.0, 0.25)
    out = nb.with_neighbours(rates, [(0.5, kill)])
    assert out.ticks_per_kill == 125.0 and out.kills_per_hour == pytest.approx(48.0)
    assert out.xp_per_hour == pytest.approx({"attack": 1040.0})
    assert out.gp_per_hour == pytest.approx(480.0 + 0.5 * 4.0 * 48)
    assert out.damage_taken_per_hour == pytest.approx(96.0 + 0.5 * 1.0 * 48)
    assert out.damage_taken_per_kill == rates.damage_taken_per_kill  # the danger filter's: the target's own
    assert nb.with_neighbours(rates, []) is rates


def test_the_rankers_count_the_neighbours_while_aggression_lasts():
    state = caster()
    spades = entry(SPADE)
    site = mine_site()
    fighter, rule = fighter_for(state), loot_rule("none")
    character = Character((3222, 3218, 0), state.max_hp(), state.hp, 0.0, state.free_slots(), None, "none",
                          combat_level=state.combat_level())
    fought = combat_rates(fighter, FIRE_BLAST, spades.npc, 0.0)
    kills = neighbour_kills(spades, fighter, FIRE_BLAST, character, rule, None)
    assert kills[PICKAXE] is not None  # a band-61 caster can fight it
    margin = 1e9  # its damage taken as trivial: no safespot needed
    alone, _ = site_rates(spades, FIRE_BLAST, fought, site, 0.0, False, True, margin, 1500)
    with_them, _ = site_rates(spades, FIRE_BLAST, fought, site, 0.0, False, True, margin, 1500,
                              neighbours=Neighbours(kills, state.combat_level(), character.location,
                                                    character.tolerance_left, 1500))
    assert with_them.kills_per_hour < alone.kills_per_hour and with_them.ticks_per_kill > alone.ticks_per_kill
    assert sum(with_them.xp_per_hour.values()) > sum(alone.xp_per_hour.values()) * with_them.kills_per_hour \
        / alone.kills_per_hour  # the pickaxes' XP comes on top of the spades' that's left
    tolerated, _ = site_rates(spades, FIRE_BLAST, fought, site, 0.0, False, True, margin, 1500,
                              neighbours=Neighbours(kills, state.combat_level(), (3421, 9650, 0), 0.0, 1500))
    assert tolerated == alone  # already there long enough: aggression has run out
    unfit = Neighbours({PICKAXE: None}, state.combat_level(), character.location, character.tolerance_left, 1500)
    assert site_rates(spades, FIRE_BLAST, fought, site, 0.0, False, True, margin, 1500, neighbours=unfit) is None


def test_the_sims_fight_kills_the_neighbours_that_engage_it():
    spades = entry(SPADE)
    site = mine_site()
    totals = {"kills": 0, "neighbour_kills": 0}
    for seed in range(20):
        state = caster()
        state.location = SPADES
        result = fight(state, np.random.default_rng(seed), 1500, spades, FIRE_BLAST, site, loot_rule("none"))
        for key in totals:
            totals[key] += result.detail[key]
    # fitted to the server's 3.7 pickaxe kills a run (rlscape.combat.neighbours)
    assert 2.0 < totals["neighbour_kills"] / 20 < 6.0 and totals["kills"] > 0


def test_no_neighbour_engages_after_the_tolerance_or_where_there_are_none():
    spades = entry(SPADE)
    site = mine_site()
    state = caster()
    state.location, state.tick, state.region_since = SPADES, 5000, 0  # here for 5,000 ticks: tolerated
    result = fight(state, np.random.default_rng(0), 1500, spades, FIRE_BLAST, site, loot_rule("none"))
    assert result.detail["neighbour_kills"] == 0 and result.detail["kills"] > 0
    rats = entry(RAT)
    lumbridge = next(s for s in rats.sites if s.spawn == (3211, 3211, 0))  # nothing aggressive near
    assert FightNeighbours.at(caster(), rats.npc, lumbridge, None).active == ()
    assert FightNeighbours.at(caster(), entry(SPADE).npc, lumbridge, object()).active == ()  # from a safespot


def test_a_fight_without_neighbours_draws_as_one_with_no_engagements(monkeypatch):
    """Where none would engage, the fight is the same as with the engagement rate at nothing: the neighbours draw
    nothing from the rng."""
    spades = entry(SPADE)
    site = mine_site()
    results = []
    for rate in (nb.ENGAGE_PER_TICK, 0.0):
        monkeypatch.setattr(nb, "ENGAGE_PER_TICK", rate)
        state = caster(99)  # combat level over 100: the level-50 pickaxe doesn't pick it
        state.location = SPADES
        result = fight(state, np.random.default_rng(3), 1500, spades, FIRE_BLAST, site, loot_rule("none"))
        results.append((result.ticks, result.termination, result.detail["kills"], tuple(state.xp)))
    assert results[0] == results[1]
