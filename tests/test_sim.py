"""Tests for sim v0's core (skills, character state, the step loop) and its first option family, woodcutting."""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.engine import HORIZON_TICKS, WEALTH_SCALE
from rlscape.sim.skills import SKILL_INDEX, SKILLS, XP_FOR_LEVEL, capped_total_xp, level_for_xp, progress
from rlscape.sim.skilling import slot_holding
from rlscape.sim.state import SPAWN, CharacterState
from rlscape.sim.woodcutting import (
    AFTER_LOG_TICKS,
    SWING_TICKS,
    Site,
    Woodcutting,
    best_hatchet,
    chop_chance,
    skill_success_chance,
)

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
LOGS, BRONZE_AXE, RUNE_AXE, BRONZE_ARROW = 1511, 1351, 1359, 882


def with_level(state: CharacterState, skill: str, level: int) -> CharacterState:
    state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


def test_xp_table_matches_the_server_formula():
    assert (XP_FOR_LEVEL[1], XP_FOR_LEVEL[2], XP_FOR_LEVEL[10], XP_FOR_LEVEL[99]) == (0, 83, 1154, 13_034_431)
    assert level_for_xp(82) == 1 and level_for_xp(83) == 2 and level_for_xp(200_000_000) == 99
    assert progress(83) == 0.0 and progress(13_034_431) == 0.0


def test_total_xp_counts_each_skill_up_to_level_99():
    xp = [0.0] * len(SKILLS)
    xp[SKILL_INDEX["attack"]], xp[SKILL_INDEX["mining"]] = 20_000_000.0, 50_000.0
    assert capped_total_xp(xp) == 13_034_431 + 50_000  # attack's XP past 99 isn't counted


@needs_server
def test_fresh_character_leaves_tutorial_island():
    state = CharacterState.fresh()
    assert state.total_level() == 33 and state.skill_measure() == pytest.approx(33.0)
    assert state.free_slots() == 10  # 18 starter items, every stack in one slot
    assert state.bank == {995: 25} and state.coins() == 25 and state.location == SPAWN


@needs_server
def test_inventory_slots_follow_stacking():
    state = CharacterState.fresh()
    assert state.add(BRONZE_ARROW, 100) == 100 and state.free_slots() == 10  # joins the existing stack
    assert state.add(LOGS, 15) == 10 and state.free_slots() == 0


@needs_server
def test_server_tables_parse():
    trees = gd.tree_types()
    assert (trees[1].reward, trees[1].level, trees[1].experience, trees[1].always_falls) == (1511, 1, 25.0, True)
    assert (trees[15].reward, trees[15].level, trees[15].experience, trees[15].always_falls) == (1515, 60, 175.0, False)
    assert not trees[18].depletes  # respawnRate = -1
    tools = gd.skilling_tools()
    assert len(tools) == 36 and tools["BRONZE_AXE"].ordinal == 0 and tools["DRAGON_AXE"].ordinal == 7


def test_skill_success_chance_matches_random_function():
    assert skill_success_chance(64, 200, 1) == pytest.approx(65 / 256)
    assert skill_success_chance(64, 200, 99) == pytest.approx(201 / 256)


@needs_server
def test_best_hatchet_respects_the_level_requirement():
    state = CharacterState.fresh()
    assert best_hatchet(state).name == "BRONZE_AXE"
    state.add(RUNE_AXE)
    assert best_hatchet(state).name == "BRONZE_AXE"  # rune needs Woodcutting 41
    assert best_hatchet(with_level(state, "woodcutting", 41)).name == "RUNE_AXE"


@needs_server
def test_sampled_logs_match_the_server_success_chance():
    """With felling switched off, ticks per log average SWING_TICKS / chop_chance, plus the tick the swing after a log
    waits (AFTER_LOG_TICKS, measured on the server), for all but the last log."""
    option = Woodcutting("test", 1, Site((3190, 3235, 0), 1, "test"))
    option.tree = dataclasses.replace(option.tree, respawn_min=-1, respawn_max=-1)
    state = with_level(CharacterState.fresh(), "woodcutting", 40)
    state.location = option.site.tile
    expected = SWING_TICKS / chop_chance(option.tree, best_hatchet(state), 40) + AFTER_LOG_TICKS * 26 / 27
    rng, per_log = np.random.default_rng(0), []
    for _ in range(300):
        state.inventory = {BRONZE_AXE: 1}
        with_level(state, "woodcutting", 40)  # 27 logs (675 XP) stay inside level 40
        result = option.run(state, rng, 100_000)
        per_log.append(result.ticks / state.inventory[LOGS])
    assert np.mean(per_log) == pytest.approx(expected, rel=0.03)


@needs_server
def test_fresh_character_chops_until_the_inventory_is_full():
    sims = [Simulator(build_catalog()) for _ in range(2)]
    infos = []
    for sim in sims:
        sim.reset(seed=7)
        ids = [o.id for o in sim.options]
        infos.append(sim.step(ids.index(slot_holding(sim.options, sim.state, "wc_logs"))).info)  # chop and keep
    info = infos[0]
    assert info == infos[1]  # same seed, same trajectory
    assert info["termination"] == "inventory_full" and info["items_delta"]["inventory"] == {LOGS: 10}
    assert info["xp_gained"] == {"woodcutting": 250.0}
    assert info["reward_vec"][1] == pytest.approx(10 * gd.item_values()[LOGS] / WEALTH_SCALE)


@needs_server
def test_masked_options_raise():
    sim = Simulator(build_catalog())
    sim.reset(seed=0)
    # woodcutting's slots: normal trees kept or burned fill the XP slots; nothing else is open at level 1
    assert sim.action_mask().tolist()[:4] == [True, True, False, False]
    with pytest.raises(ValueError, match="masked"):
        sim.step(2)


@needs_server
def test_the_horizon_truncates_and_checkpoints_are_reported():
    sim = Simulator(build_catalog())
    sim.reset(seed=0)
    sim.state.inventory = {BRONZE_AXE: 1}
    sim.state.location = (3190, 3235, 0)
    sim.state.tick = HORIZON_TICKS - 50
    result = sim.step(0)
    assert result.truncated and result.info["termination"] == "horizon" and result.info["duration"] == 50
    assert result.info["checkpoints"].keys() == {20}
    assert result.info["checkpoints"][20] == {"total_level": result.info["total_level"],
                                              "total_xp": result.info["total_xp"],
                                              "net_worth": result.info["net_worth"]}
