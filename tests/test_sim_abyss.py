"""The Abyss in the sim (sim v1, Runecrafting part 4; docs/sim-v1-skills-draft.md §5): its export from the server
(data/abyss), the crossing (rlscape.sim.abyss) and abyss_rc_<rune>, with the times measured on the server
(scripts/measure_abyss.py)."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import runecrafting as rcd
from rlscape.gamedata import server as gd
from rlscape.sim import abyss
from rlscape.sim.combat import RESPAWN, die
from rlscape.sim.runecrafting import (ABYSS_RUNES, RC_RUNES, AbyssRunecraft, RunecraftAtRuins, edgeville_bank,
                                      runecrafting_paths)
from rlscape.sim.skilling import path_options
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
RUNE_PICKAXE, RUNE_AXE, WEAPON, LOBSTER, RUNE_SCIMITAR = 1275, 1359, 3, 379, 1333
KINDS = {"rocks", "tendrils", "boil", "eyes", "gap", "passage"}


def character(inventory: dict[int, int] | None = None, bank: dict[int, int] | None = None,
              **levels: int) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory, state.bank, state.equipment = dict(inventory or {}), dict(bank or {}), {}
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.hp = state.max_hp()
    return state


def test_the_export_has_a_layout_for_each_segment_with_the_landings_place_blocked_and_the_passage_opposite():
    """Every one of the teleport's twelve segments turns the obstacles so the place by the landing is blocked
    (scripts/export_abyss.py saw each at least twice, always the same), and the passage stands opposite it, six places
    round; each other kind shows twice. The walks are the planner's on the server's collision map."""
    a = rcd.abyss()
    assert a.places == tuple(range(7142, 7154)) and len(a.layouts) == 12
    by_angle = sorted(range(12), key=lambda i: (np.arctan2(a.inner_tiles[i][1] - 4832, a.inner_tiles[i][0] - 3039)))
    for v, layout in enumerate(a.layouts):
        assert layout.count("blocked") == 1 and layout.count("passage") == 1
        assert set(layout) == KINDS | {"blocked"}
        here, there = by_angle.index(layout.index("blocked")), by_angle.index(layout.index("passage"))
        assert (there - here) % 12 == 6
        steps = [s for s, kind in zip(a.outer_steps[v], layout) if kind != "blocked"]
        assert 5 < min(steps) < 15 and 60 < a.outer_steps[v][layout.index("passage")] < 70  # beside it; half round
    assert all(0 < s < 40 for i in range(12) for s in a.inner_steps[i].values())
    assert set(a.inner_steps[0]) == set(ABYSS_RUNES) | {"chaos"}  # the server's eleven rifts; the sim takes ten


def test_a_try_passes_at_its_level_plus_one_in_a_hundred_and_the_passage_always():
    """AbyssPlugin.handleObstacle: RandomFunction.random(100) < level + 1; a fail takes FAIL_TICKS (7 between tries
    on the server, every time)."""
    state = character(agility=60, thieving=1)
    assert abyss.pass_chance(state, "gap") == pytest.approx(0.61)
    assert abyss.pass_chance(state, "eyes") == pytest.approx(0.02)
    assert abyss.pass_chance(character(agility=99), "gap") == 1.0
    assert abyss.pass_chance(state, "passage") == 1.0
    assert abyss.expected_pass_ticks(state, "gap") == pytest.approx(abyss.PASS_TICKS + 0.39 / 0.61 * abyss.FAIL_TICKS)
    assert abyss.expected_pass_ticks(state, "passage") == abyss.PASSAGE_TICKS


@needs_server
def test_rocks_and_tendrils_take_a_worn_tool_and_a_boil_isnt_tried():
    """getTool looks in the equipment too, and the trip's inventory is essence: the pickaxe or axe used is the one
    worn. A boil's tinderbox must be carried (inInventory), so a trip doesn't try one."""
    state = character({RUNE_PICKAXE: 1, 590: 1}, mining=61, woodcutting=61, firemaking=99)
    assert not abyss.usable(state, "rocks") and not abyss.usable(state, "boil")
    state.inventory, state.equipment = {}, {WEAPON: RUNE_PICKAXE}
    assert abyss.usable(state, "rocks") and not abyss.usable(state, "tendrils")
    assert abyss.usable(state, "eyes") and abyss.usable(state, "gap") and abyss.usable(state, "passage")
    state.equipment = {WEAPON: RUNE_AXE}
    assert abyss.usable(state, "tendrils") and not abyss.usable(character(mining=1), "rocks")


@needs_server
def test_a_crossing_takes_the_obstacle_that_reaches_the_rift_soonest():
    """With nothing but the passage usable, every segment's crossing is the passage; with a worn pickaxe and Mining 99,
    the rocks beside the landing where a segment puts them there (segments 0 to 5; the others put them five places
    round, where the passage can reach the rift sooner), and on average much sooner."""
    weak = character()
    assert {abyss.best_crossing(weak, v, "nature").kind for v in range(12)} == {"passage"}
    miner = character(mining=99)
    miner.equipment = {WEAPON: RUNE_PICKAXE}
    a = rcd.abyss()
    for v in range(6):
        crossing = abyss.best_crossing(miner, v, "nature")
        assert a.layouts[v][crossing.place] == "rocks" == crossing.kind
    assert abyss.expected_crossing_ticks(miner, "nature") < abyss.expected_crossing_ticks(weak, "nature") - 10


@needs_server
def test_a_crossing_skulls_the_character_and_lands_it_inside_the_ruins():
    """The teleport skulls it for 2,000 ticks; the rift lands it where entering the ruins does (Altar.enterRift)."""
    for rune in ("nature", "cosmic"):
        state = character(hitpoints=99, defence=99, agility=99)
        state.tick = 500
        trip = abyss.cross(state, np.random.default_rng(1), rune, at=100)
        assert not trip.died and state.skulled_until == 600 + abyss.TELEPORT_TICKS + abyss.SKULL_TICKS
        assert state.location == rcd.ruins()[rune].end
        assert 25 < trip.ticks < 90


@needs_server
def test_a_skulled_death_keeps_nothing_and_leaves_no_grave_and_the_skull_clears():
    """DeathTask.getContainers keeps 3 less 3 while skulled; GraveController.allowGenerate makes no grave for a
    skulled death; the Skulled timer clears on death."""
    state = character({RUNE_SCIMITAR: 1, 1079: 1, 995: 500})
    state.location, state.hp, state.skulled_until = (3039, 4856, 0), 0, 3000
    die(state, now=1000)
    assert state.inventory == {} and state.gravestone is None and state.skulled_until == 0
    assert state.location == RESPAWN
    unskulled = character({RUNE_SCIMITAR: 1, 1079: 1, 995: 500})
    unskulled.location, unskulled.skulled_until = (3255, 3255, 0), 1000
    die(unskulled, now=1000)  # the skull ran out as it died: three kept (a stack as one), the rest in a grave
    assert len(unskulled.inventory) == 3 and unskulled.gravestone.items == {995: 499}


@needs_server
def test_the_outer_rings_monsters_pick_a_character_their_levels_allow_and_hit_less_through_defence():
    """AggressiveBehavior: a monster picks a character of at most twice its combat level (leeches 41, guardians 59,
    walkers 81). The damage a swing is the sim's npc_offence with no prayer (on the server, 634 hitpoints against the
    sim's 636 over 678 swings)."""
    assert abyss.mean_damage(character(defence=20)) > abyss.mean_damage(character(defence=60)) > 0
    strong = character(attack=99, strength=99, defence=99, hitpoints=99)  # combat level 99: leeches pass it by
    assert {npc.id for npc, *_ in abyss._drawn(strong)} == {2264, 2265}
    assert {npc.id for npc, *_ in abyss._drawn(character())} == set(abyss.ABYSSAL)
    damage, hardest = abyss.crossing_damage(character(defence=40, agility=60), "air")
    assert 10 < damage < 60 and hardest > 0


@needs_server
def test_a_weak_crossing_eats_the_food_it_carries_and_can_die_skulled():
    """Under twice the hardest hit it eats what it carries; a death on the outer ring is skulled."""
    deaths, ate = 0, 0
    for seed in range(40):
        state = character({LOBSTER: 6, rcd.PURE_ESSENCE: 22}, hitpoints=30)
        trip = abyss.cross(state, np.random.default_rng(seed), "air")
        ate += state.inventory.get(LOBSTER, 0) < 6
        if trip.died:
            deaths += 1
            assert state.inventory == {} and state.location == RESPAWN and state.gravestone is None
    assert ate > 10 and 0 < deaths < 40


@needs_server
def test_abyss_rc_paths_are_one_for_each_altar_the_rifts_reach():
    """OQ-39 (b): death opens at Ranged 60 and Thieving 50; cosmic only by the Abyss (OQ-45 (a)); blood and astral
    never; chaos out (Caleb, 2026-11-09). Eight ruins paths, eight tiaras', ten Abyss paths."""
    assert len(runecrafting_paths()) == 2 * len(RC_RUNES) + len(ABYSS_RUNES) == 26
    assert "abyss_rc_chaos" not in {p.id for p in runecrafting_paths()}
    ids = {p.id for p in path_options()}
    assert {f"abyss_rc_{r}" for r in ABYSS_RUNES} <= ids and "abyss_rc_blood" not in ids
    death = AbyssRunecraft("death")
    assert not death.allowed(character(runecrafting=65, ranged=60, thieving=49))
    assert death.allowed(character(runecrafting=65, ranged=60, thieving=50))
    assert not AbyssRunecraft("nature").allowed(character(runecrafting=43))


@needs_server
def test_abyss_rc_banks_at_edgeville_takes_no_talisman_and_food_for_the_need():
    """A rift needs no talisman, so a load is all essence, but for the food the crossing's need asks for: its
    expected damage and twice the hardest hit there, over the hitpoints."""
    path = AbyssRunecraft("nature")
    state = character({}, {rcd.PURE_ESSENCE: 500, LOBSTER: 20}, runecrafting=44, hitpoints=40, defence=40)
    assert path.available(state) and edgeville_bank().name == "Edgeville"
    path._prepare(state)
    need = path.need(state)
    path._take_food(state, need)
    path._restock(state)
    food = state.inventory.get(LOBSTER, 0)
    assert need > state.max_hp() and food == -(-(need - state.hp) // 12)  # lobsters heal 12
    assert state.inventory[rcd.PURE_ESSENCE] == 28 - food
    assert rcd.talismans()["nature"] not in state.inventory


@needs_server
def test_abyss_rc_law_banks_the_worn_arms_and_cosmic_needs_a_way_out():
    """The law rift asks Entrana's rule (MysteriousRuinListener.checkReq); cosmic's and death's portals lead where the
    travel model doesn't go, so their trips leave by teleport and start only when one will be ready."""
    law = AbyssRunecraft("law")
    state = character({}, {rcd.PURE_ESSENCE: 100}, runecrafting=54)
    state.equipment = {WEAPON: RUNE_SCIMITAR}
    law._prepare(state)
    assert WEAPON not in state.equipment and state.bank.get(RUNE_SCIMITAR) == 1
    cosmic = AbyssRunecraft("cosmic")
    ready = character({}, {rcd.PURE_ESSENCE: 100}, runecrafting=27)
    assert cosmic.station(ready) is not None  # the home teleport is ready
    cooling = character({}, {rcd.PURE_ESSENCE: 100}, runecrafting=27)
    cooling.home_teleport_ready = cooling.tick + 3000
    assert cosmic.station(cooling) is None and not cosmic.available(cooling)


@needs_server
def test_abyss_rc_runs_trips_and_its_rate_is_the_abyss_s():
    """A strong character runs nature by the Abyss: its runes and XP, and a rate in the slots' model; its gp is the
    runes over the essence."""
    path = AbyssRunecraft("nature")
    state = character({}, {rcd.PURE_ESSENCE: 2000, LOBSTER: 100}, runecrafting=44, hitpoints=99, defence=99, agility=99)
    xp, rate = state.xp[SKILL_INDEX["runecrafting"]], path.rate(state, 6000)
    result = path.run(state, np.random.default_rng(0), 6000)
    made = state.inventory.get(rcd.runes()["nature"].item, 0) + state.bank.get(rcd.runes()["nature"].item, 0)
    assert result.detail["trips"] >= 2 and made > 0
    assert state.xp[SKILL_INDEX["runecrafting"]] - xp == pytest.approx(made * 9.0)
    assert rate[0] > 0 and rate[2] > 0 and rate[3] > 0
    assert isinstance(RunecraftAtRuins("nature").rate(state, 6000)[0], float)


@needs_server
def test_the_observation_shows_the_skulls_ticks_left():
    """Caleb, 2026-11-09, OQ-48 (a): the ticks the skull has left, over the Abyss's 2,000; 0 without one. A crossing
    puts it on, and a death clears it."""
    from rlscape.envs.sim_env import SimEnv
    env = SimEnv()
    env.reset(seed=0)
    state = env.sim.state
    reading = lambda: float(env.encoder.encode(state, env.sim.action_mask())[env.encoder.parts["skull"]][0])  # noqa: E731
    assert env.encoder.names[env.encoder.parts["skull"]] == ("skull_ticks",) and reading() == 0.0
    state.skulled_until = state.tick + abyss.SKULL_TICKS // 2
    assert reading() == pytest.approx(0.5)
    state.hp, state.xp[SKILL_INDEX["defence"]], state.xp[SKILL_INDEX["agility"]] = 99, XP_FOR_LEVEL[99], XP_FOR_LEVEL[99]
    state.xp[SKILL_INDEX["hitpoints"]] = XP_FOR_LEVEL[99]
    abyss.cross(state, np.random.default_rng(0), "air")  # skulled from the landing: 2,000 ticks and the teleport's
    assert reading() == 1.0
    state.hp = 0
    die(state, state.tick)
    assert reading() == 0.0


@needs_server
def test_the_abyss_is_closed_in_by_the_mages_teleport_and_out_by_a_teleport_or_its_exit():
    """No walk joins the Abyss to anywhere else; the way in is the mage's teleport, which skulls, and the way out a
    teleport or the Abyss's exit (the passage, the body rift and its altar's portal: rlscape.gamedata.transports)."""
    from rlscape.gamedata.transports import ABYSS_EXIT, BODY_RUINS, in_abyss
    from rlscape.sim.movement import route, walk
    from rlscape.travel import on_foot, travel_ticks
    edgeville, site = (3094, 3493, 0), (3039, 4856, 0)
    assert in_abyss(site) and not in_abyss(edgeville) and not on_foot(edgeville, site)
    state = character()
    state.location = edgeville
    into = route(state, site)
    assert [t.id for t in into.transports] == ["abyss:mage"]
    walked = walk(state, site, 10_000)
    assert walked < travel_ticks(edgeville, site) + 30 and state.location == site
    # skulled from the teleport, which comes after the walk to the mage
    assert state.tick + abyss.SKULL_TICKS < state.skulled_until <= state.tick + walked + abyss.SKULL_TICKS
    state.home_teleport_ready = state.tick + 10 ** 9  # no home teleport: the exit
    out = route(state, edgeville)
    assert [t.id for t in out.transports] == ["abyss:exit"] and ABYSS_EXIT.end == BODY_RUINS
    state.home_teleport_ready = 0  # the home teleport is ready: faster than the exit's walk from the body ruins?
    home = route(state, (3222, 3218, 0))
    assert [t.id for t in home.transports] == ["home"]


@needs_server
def test_the_rings_attacks_on_a_fight_are_the_crossings_less_the_monster_fought():
    """OQ-49 (a): a fight's ring has the crossing's damage mix at the fight's rate (rate x mean =
    FIGHT_ATTACKS_PER_TICK x mean_damage); beside a monster fighting the character, the rest of the rate; none past the
    region's tolerance."""
    state = character(attack=61, strength=61, defence=61, hitpoints=61)
    ring = abyss.Ring.at(state, 1000.0)
    assert ring.rate * ring.mean() == pytest.approx(abyss.FIGHT_ATTACKS_PER_TICK * abyss.mean_damage(state))
    assert ring.beside(6) == pytest.approx(ring.rate - 1 / 6) and ring.beside(1) == 0.0
    rng = np.random.default_rng(0)
    assert len(ring.attacks(rng, 1000.0, 500.0)) == 0
    hits = ring.attacks(rng, 0.0, 10_000.0)  # up to the tolerance's 1,000 ticks
    assert len(hits) == pytest.approx(ring.rate * 1000, rel=0.1) and hits.max() <= len(ring.cdf) - 1
    assert ring.damage(rng, 50_000).mean() == pytest.approx(ring.mean(), rel=0.05)


@needs_server
def test_a_fight_in_the_abyss_takes_the_rings_attacks_with_no_prayer(monkeypatch):
    """OQ-49 (a): at the guardians, a band-61 melee fighter eats for the ring's crowd and the guardians' unprotected
    swings; with the region's tolerance run out, for the guardians' alone; out of the Abyss (prayers flicked, no
    ring), nothing. 1,000 ticks, with food to spare."""
    from rlscape.combat.candidates import enemy_pool
    from rlscape.combat.rates import Plan
    from rlscape.sim import combat
    entry = next(e for e in enemy_pool() if e.npc.id == 2264)
    site = next(s for s in entry.sites if s.spawn == (3017, 4821, 0))
    rune = {1333: 1, 1163: 1, 1113: 1, 1079: 1, 1201: 1}  # scimitar, full helm, chainbody, platelegs, kiteshield

    def eaten(seed: int, tolerated: bool = False) -> int:
        state = character({**rune, LOBSTER: 23}, attack=61, strength=61, defence=61, hitpoints=61, prayer=61)
        state.location = site.spawn
        state.region_since = -1000 if tolerated else 0
        combat.fight(state, np.random.default_rng(seed), 1000, entry, Plan("melee", "accurate"), site,
                     lambda _: False)
        return 23 - state.inventory.get(LOBSTER, 0)

    inside = np.mean([eaten(seed) for seed in range(20)])
    tolerated = np.mean([eaten(seed, tolerated=True) for seed in range(20)])
    assert tolerated > 3 and inside > tolerated + 4
    monkeypatch.setattr(combat, "in_abyss", lambda tile: False)
    assert sum(eaten(seed) for seed in range(20)) == 0


@needs_server
def test_a_crossing_the_hitpoints_and_food_cant_cover_is_masked():
    """Found 2026-11-09 (the guide's extension, OQ-53): abyss_rc_air was open to a character whose hitpoints and food
    couldn't reach what the crossing needs, so each pick stopped at Edgeville's booth (OUT_OF_FOOD, 8 ticks) with
    nothing done, and a policy could pick it again and again. Now it's masked, as run() would turn back."""
    path = AbyssRunecraft(ABYSS_RUNES["air"]) if isinstance(ABYSS_RUNES, dict) else AbyssRunecraft("air")
    state = character({1436: 1})  # a rune essence, no food
    state.inventory = {1436: 1}
    state.bank = {}
    state.hp = 1
    assert path.need(state) > 1 and not path.available(state)
    state.bank = {379: 10}  # ten lobsters at the bank cover it
    assert path.available(state)
    state.bank, state.hp = {}, state.max_hp()  # or full hitpoints, if they're enough
    assert path.available(state) == (state.hp >= min(path.need(state), state.max_hp()))
