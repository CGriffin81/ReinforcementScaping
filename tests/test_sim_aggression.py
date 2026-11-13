"""Tests for aggressive monsters at gathering sites (rlscape.sim.aggression; Caleb's rule, 2026-10-31)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim.aggression import TOLERANCE_TICKS, Exposure, site_aggressors
from rlscape.sim.engine import Simulator
from rlscape.sim.equipment import WEAPON
from rlscape.sim.fishing import fishing_options
from rlscape.sim.options import DIED
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState
from rlscape.sim.woodcutting import Woodcutting, woodcutting_options

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
ADAMANT_AXE, RUNE_SCIMITAR = 1357, 1333


def willows():
    return next(o for o in woodcutting_options() if o.id == "wc_willow")


def woodcutter(**levels: int) -> CharacterState:
    state = CharacterState.fresh()
    for skill, level in {"woodcutting": 31, **levels}.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.add(ADAMANT_AXE)
    if levels.get("hitpoints"):
        state.hp = state.max_hp()
    return state


def chop(state: CharacterState, seed: int) -> tuple[int, float]:
    """One willow option from the site's tile: its ticks and the hitpoints it cost (before the end's regeneration)."""
    option = willows()
    state.location = option.site.tile
    before = state.hp
    result = option.run(state, np.random.default_rng(seed), 3_000)
    return result.ticks, before - state.hp


@needs_server
def test_the_willows_have_two_dark_wizards_that_pick_only_low_levels():
    wizards = site_aggressors(willows().site.tile)
    assert [(a.npc.name, a.level) for a in wizards] == [("Dark wizard", 7)] * 2
    assert len(Exposure.at(woodcutter(), willows().site.tile, np.random.default_rng(0)).active) == 2
    strong = woodcutter(attack=20, strength=20, defence=20, hitpoints=20)  # combat level 23 > 2 x 7
    assert strong.combat_level() > 14 and not Exposure.at(strong, willows().site.tile, np.random.default_rng(0)).active


@needs_server
def test_a_low_level_woodcutter_gets_hit_and_sometimes_runs_but_keeps_chopping():
    exposures = []
    for seed in range(60):
        state = woodcutter()
        option = willows()
        state.location = option.site.tile
        exposure = Exposure.at(state, option.site.tile, np.random.default_rng(seed))
        exposure.gather(0, 300)
        exposures.append(exposure.counts)
        assert state.hp > 0
    assert sum(c["hits"] for c in exposures) > 0 and any(c["flees"] for c in exposures)
    assert not any(c["fights"] for c in exposures)  # strength 1 can't kill a 12-hitpoint wizard in two hits


@needs_server
def test_tolerance_ends_the_attacks_after_1000_ticks_in_the_region():
    state = woodcutter()
    state.tick, state.region_since = 5_000, 5_000 - TOLERANCE_TICKS
    exposure = Exposure.at(state, willows().site.tile, np.random.default_rng(0))
    assert exposure.gather(0, 1_000) == 0 and exposure.counts["attacks"] == 0


@needs_server
def test_a_trivial_monster_is_fought_and_stops_attacking():
    """A character the wizards pick is combat level 14 at most. Strength 33 with a rune scimitar hits up to 7, over
    half a wizard's 12 hitpoints, and the wizard's max hit of 2 is under a quarter of 10 hitpoints: trivial, by
    Caleb's rule."""
    state = woodcutter(strength=33)
    state.equipment[WEAPON] = RUNE_SCIMITAR
    assert state.combat_level() <= 14  # still one the wizards pick
    exposure = Exposure.at(state, willows().site.tile, np.random.default_rng(1))
    before = state.xp[SKILL_INDEX["attack"]]
    exposure.gather(0, 600)
    assert exposure.counts["fights"] >= 1 and state.xp[SKILL_INDEX["attack"]] > before


@needs_server
def test_a_strong_character_chops_willows_unbothered():
    strong = woodcutter(attack=20, strength=20, defence=20, hitpoints=20)
    assert all(chop(strong, seed)[1] == 0 for seed in range(10))


@needs_server
def test_the_rock_objects_and_al_kharid_iron_with_its_scorpions():
    from rlscape.sim.mining import mining_options
    assert {2092, 2093} <= gd.rock_objects()[6] and not gd.rock_objects()[6] & gd.rock_objects()[1]  # iron, copper
    alkharid = next(o for o in mining_options() if o.id == "mine_iron_alkharid")
    assert [a.npc.name for a in site_aggressors(alkharid.site.tile)] == ["Scorpion"] * 3
    miner = CharacterState.fresh()
    miner.xp[SKILL_INDEX["mining"]] = float(XP_FOR_LEVEL[31])
    exposure = Exposure.at(miner, alkharid.site.tile, np.random.default_rng(0), alkharid.site.exposure)
    exposure.gather(0, 500)
    assert exposure.counts["hits"] > 0 and exposure.rate == alkharid.site.exposure.attack_rate


def test_draynor_shrimp_wizards_chase_a_fleeing_level_3_fisher_and_can_kill_it():
    """Measured at Draynor's shrimp spots: the wizards go on casting as a level-3 fisher runs, and it often dies. The
    option then ends when the character died, not when the wait it died in started."""
    shrimp = next(o for o in fishing_options() if o.id == "fish_shrimp")
    assert shrimp.exposure.engage_rate and shrimp.exposure.cadence == 5 and shrimp.exposure.chase > 0
    results = []
    for seed in range(200):
        state = CharacterState.fresh()
        state.inventory, state.location = {303: 1}, shrimp.start  # a net and room for 27 fish, as calibrated
        results.append(shrimp.run(state, np.random.default_rng(seed), 3_000))
    died = [r for r in results if r.termination == DIED]
    assert 0.5 < len(died) / len(results) < 0.95  # the server: 9 of 10 runs
    assert all(r.ticks < 3_000 for r in died)


def test_without_a_chase_running_away_is_safe():
    """At a site with no measured chase, the character only dies of an attack while it gathers."""
    state = CharacterState.fresh()
    exposure = Exposure.at(state, (3085, 3230, 0), np.random.default_rng(0))
    assert exposure.site.chase == 0
    shrimp = next(o for o in fishing_options() if o.id == "fish_shrimp")
    exposure = Exposure.at(state, shrimp.start, np.random.default_rng(0), shrimp.exposure)
    assert exposure.site.chase == shrimp.exposure.chase


def test_a_death_after_the_budget_ends_the_option_at_the_budget():
    """sim v1.3 (2026-11-12): running away and waiting for hitpoints can put the wizards' kill after the option's
    budget, and the engine raised (E3's (.5, .5) seed 1: 1,711 ticks of 1,500). The option now ends at its budget,
    with the death."""
    shrimp = next(o for o in fishing_options() if o.id == "fish_shrimp")
    sim, late = Simulator([shrimp], activity_ticks=600), 0
    for seed in range(300):  # on sim v1.2, seeds 130, 138, 241 and 253 died after 600 ticks
        sim.reset(seed)
        sim.state.inventory, sim.state.location = {303: 1}, shrimp.start  # a net, at the spot
        info = sim.step(0).info
        assert 1 <= info["duration"] <= 600
        late += info["duration"] == 600 and info["termination"] == DIED
    assert late >= 4


def test_both_depleting_gathering_death_returns_end_at_the_budget():
    """gathering.py's two death returns, while it makes attempts and while it waits for a resource to come back, cap
    the same way. No woodcutting or mining site has a measured chase, so neither can die late in the catalog: here the
    willows' site takes Draynor's exposure, and a tree that always falls, alone at it, makes the character wait."""
    draynor, site = next(o for o in fishing_options() if o.id == "fish_shrimp").exposure, willows().site
    cases = [(Woodcutting("wc_willow", 8, replace(site, exposure=draynor)), 30, 300),  # dies making attempts
             (Woodcutting("wc_willow", 1, replace(site, exposure=draynor, resources=1)), 1, 150)]  # dies waiting
    for option, level, budget in cases:
        late = 0
        for seed in range(100):
            state = CharacterState.fresh()
            state.xp[SKILL_INDEX["woodcutting"]] = float(XP_FOR_LEVEL[level])
            state.add(1351)  # a bronze axe
            state.location = site.tile
            result = option.run(state, np.random.default_rng(seed), budget)
            assert 1 <= result.ticks <= budget
            late += result.ticks == budget and result.termination == DIED
        assert late >= 2
