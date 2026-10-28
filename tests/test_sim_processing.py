"""Tests for sim v0's processing options: smelting, smithing, cooking, firemaking and burying bones."""

from __future__ import annotations

import re

import numpy as np
import pytest

from rlscape.combat.access import Progress
from rlscape.gamedata import server as gd
from rlscape.sim.processing import (
    BURY_TICKS,
    CHAIN_TICKS,
    HAMMER,
    LIGHT_TICKS,
    SMELT_TICKS,
    BurnLogs,
    BuryBones,
    Cook,
    Smelt,
    Smith,
    light_chance,
    nearest_station,
)
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState
from rlscape.sim.woodcutting import skill_success_chance

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
COPPER, TIN, IRON_ORE, BRONZE_BAR, IRON_BAR, RAW_SHRIMPS, SHRIMPS, BURNT_SHRIMP = 436, 438, 440, 2349, 2351, 317, 315, 7954
LOGS, BONES, TINDERBOX = 1511, 526, 590


def character(inventory: dict[int, int], **levels: int) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory = dict(inventory)
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


@needs_server
def test_processing_tables_parse():
    bars = gd.smelted_bars()
    assert (bars["BRONZE"].level, bars["BRONZE"].experience, bars["BRONZE"].ores) == (1, 6.2, ((COPPER, 1), (TIN, 1)))
    assert bars["STEEL"].ores == ((453, 2), (IRON_ORE, 1))
    text = (gd.SMITHING / "Bars.java").read_text(encoding="utf-8")
    assert len(gd.smithables()) == len(re.findall(r"^\s*[A-Z_]+\(BarType\.", text, re.M))
    plate = gd.smithables()["BRONZE_PLATEBODY"]
    assert (plate.level, plate.bars, plate.amount, plate.experience_per_bar) == (18, 5, 1, 12.5)
    shrimp = gd.cookables()[RAW_SHRIMPS]
    assert (shrimp.cooked, shrimp.level, shrimp.experience, shrimp.range, shrimp.lumbridge_range) == (
        SHRIMPS, 1, 30.0, (128, 512), (138, 532))
    assert gd.log_types()[LOGS] == (1, 40.0) and gd.log_types()[1515] == (60, 202.5)
    assert gd.bone_experience()[BONES] == 4.5 and gd.bone_experience()[532] == 15.0


@needs_server
def test_iron_smelts_half_the_time_and_ores_go_either_way():
    option, rng, bars, ores = Smelt("smelt_iron", "IRON"), np.random.default_rng(0), 0, 0
    for _ in range(200):
        state = character({IRON_ORE: 20}, smithing=15)
        state.location = nearest_station(state, "furnace").tile
        result = option.run(state, rng, 10_000)
        assert result.termination == "inputs_exhausted" and IRON_ORE not in state.inventory
        bars += state.inventory.get(IRON_BAR, 0)
        ores += 20
    assert bars / ores == pytest.approx(0.5, abs=0.02)


@needs_server
def test_smithing_makes_the_most_bars_per_item_the_level_allows():
    option = Smith("smith_bronze", "BRONZE")
    assert option.best_item(character({HAMMER: 1, BRONZE_BAR: 5}, smithing=18)).kind == "TYPE_PLATEBODY"
    assert option.best_item(character({HAMMER: 1, BRONZE_BAR: 5}, smithing=17)).bars == 3
    assert option.best_item(character({HAMMER: 1, BRONZE_BAR: 2}, smithing=18)).bars == 2  # leftovers still used
    state = character({HAMMER: 1, BRONZE_BAR: 10}, smithing=18)
    option.run(state, np.random.default_rng(1), 10_000)
    assert BRONZE_BAR not in state.inventory and state.inventory.get(1117) == 2  # two bronze platebodies
    assert state.xp[SKILL_INDEX["smithing"]] == XP_FOR_LEVEL[18] + 10 * 12.5


@needs_server
def test_the_lumbridge_range_needs_cooks_assistant():
    state = character({RAW_SHRIMPS: 1})
    state.location = (3211, 3215, 0)  # standing in the castle kitchen
    assert nearest_station(state, "range").name != "Lumbridge Castle"
    state.progress = Progress(quests_complete=frozenset({"COOKS_ASSISTANT"}))
    assert nearest_station(state, "range").name == "Lumbridge Castle"


@needs_server
def test_burn_rate_matches_the_range_bounds():
    option, rng, cooked, total = Cook("cook_fish"), np.random.default_rng(2), 0, 0
    for _ in range(300):
        state = character({RAW_SHRIMPS: 20}, cooking=10)
        option.run(state, rng, 10_000)  # Al Kharid range: the plain range bounds
        cooked += state.inventory.get(SHRIMPS, 0)
        total += 20
    assert cooked / total == pytest.approx(skill_success_chance(128, 512, 10), abs=0.02)


def test_light_chance_matches_the_servers_roll():
    rng = np.random.default_rng(3)
    for level, req in ((1, 1), (60, 60), (75, 60)):
        threshold = np.ceil(((level + 1) * 50 - req * 15) / req / 3 * 4)
        rolls = threshold >= rng.integers(0, 99, 400_000)  # RandomFunction.random(99): 0..98
        assert rolls.mean() == pytest.approx(light_chance(level, req), abs=0.003)


@needs_server
def test_a_line_of_fires_rolls_only_for_the_first_log():
    state = character({TINDERBOX: 1, LOGS: 10})
    result = BurnLogs("burn_logs").run(state, np.random.default_rng(4), 10_000)
    assert result.ticks == LIGHT_TICKS + 9 * CHAIN_TICKS  # normal logs always light at level 1
    assert state.xp[SKILL_INDEX["firemaking"]] == 400.0 and LOGS not in state.inventory


@needs_server
def test_bones_bury_two_ticks_apart():
    state = character({BONES: 10})
    result = BuryBones("bury_bones").run(state, np.random.default_rng(5), 10_000)
    assert result.ticks == 10 * BURY_TICKS and state.xp[SKILL_INDEX["prayer"]] == 45.0


@needs_server
def test_processing_masks_follow_the_inputs():
    fresh = CharacterState.fresh()  # tinderbox but no logs; no ores, raw food, bones or hammer
    assert not any(o.available(fresh) for o in (Smelt("s", "BRONZE"), Smith("h", "BRONZE"), Cook("c"),
                                                 BurnLogs("b"), BuryBones("y")))
    assert Smelt("s", "STEEL").available(character({453: 2, IRON_ORE: 1}, smithing=30))
    assert not Smelt("s", "STEEL").available(character({453: 1, IRON_ORE: 1}, smithing=30))
    assert not Smelt("s", "STEEL").available(character({453: 2, IRON_ORE: 1}, smithing=29))
    assert SMELT_TICKS == 5
