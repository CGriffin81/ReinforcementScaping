"""Tests for run energy and weight (rlscape.sim.energy) and bank_deposit_worn."""

from __future__ import annotations

from copy import deepcopy
from math import ceil

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.combat import die
from rlscape.sim.economy import BankDepositWorn
from rlscape.sim.energy import drain_per_run_tick, restore_per_tick, walk_plan, weight
from rlscape.sim.movement import route_ticks, walk
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, CharacterState
from rlscape.travel import path

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
SHARK, SHARK_NOTE, RUNE_BODY, RUNE_LEGS, BOOTS_OF_LIGHTNESS = 385, 386, 1127, 1079, 88
BRONZE_AXE, BRONZE_ARROW, BONES = 1351, 882, 526
LUMBRIDGE, VARROCK = (3222, 3218, 0), (3212, 3424, 0)


def character(inventory: dict[int, int] | None = None, worn: tuple[int, ...] = (), energy: float = 100.0,
              agility: int = 1) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory = dict(inventory or {})
    state.equipment = {gd.items()[item].equipment_slot: item for item in worn}
    state.run_energy, state.location = energy, LUMBRIDGE
    state.xp[SKILL_INDEX["agility"]] = float(XP_FOR_LEVEL[agility])
    return state


def tick_by_tick(energy: float, tiles: int, drain: float, gain: float) -> tuple[int, float]:
    """WalkingQueue.update one tick at a time: run off under 1% energy; a running tick takes 2 tiles and drains, any
    other tick takes 1 and restores."""
    running, ticks = True, 0
    while tiles > 0:
        if energy < 1.0:
            running = False
        if running and tiles >= 2:
            tiles, energy = tiles - 2, max(energy - drain, 0.0)
        else:
            tiles, energy = tiles - 1, min(energy + gain, 100.0)
        ticks += 1
    return ticks, energy


@needs_server
def test_weight_counts_a_stack_once_and_worn_items_even_below_zero():
    state = character({SHARK: 3, SHARK_NOTE: 100, COINS: 5_000, BOOTS_OF_LIGHTNESS: 1}, worn=(RUNE_BODY,))
    assert weight(state) == pytest.approx(3 * 0.6 + 9.9)  # banknotes, coins and carried boots add nothing
    state.inventory.pop(BOOTS_OF_LIGHTNESS)
    state.equipment[gd.items()[BOOTS_OF_LIGHTNESS].equipment_slot] = BOOTS_OF_LIGHTNESS
    assert weight(state) == pytest.approx(3 * 0.6 + 9.9 - 4.5)  # worn, they take 4.5 kg off


def test_drain_grows_with_weight_and_restore_with_agility():
    assert drain_per_run_tick(0) == drain_per_run_tick(-4.5) == 0.55
    assert drain_per_run_tick(50) == pytest.approx(0.825)
    assert restore_per_tick(1) == pytest.approx(60 / 174) and restore_per_tick(99) == pytest.approx(60 / 76)


@needs_server
@pytest.mark.parametrize("energy, tiles, worn, agility", [
    (100.0, 100, (), 1),  # runs all the way
    (100.0, 600, (), 1),  # runs out, then walks
    (100.0, 600, (RUNE_BODY, RUNE_LEGS), 1),  # heavier: runs out sooner
    (37.5, 300, (RUNE_BODY,), 60),
    (0.5, 40, (), 1),  # too tired to run at all
])
def test_a_walk_matches_the_server_tick_by_tick(energy, tiles, worn, agility):
    state = character(worn=worn, energy=energy, agility=agility)
    expected = tick_by_tick(energy, tiles, drain_per_run_tick(weight(state)), restore_per_tick(agility))
    assert walk_plan(state, [(tiles, 0)]) == pytest.approx(expected)


@needs_server
def test_plate_slows_a_long_walk_once_energy_runs_out():
    light, plated = character(), character(worn=(RUNE_BODY, RUNE_LEGS))
    assert walk_plan(light, [(300, 0)])[0] == walk_plan(plated, [(300, 0)])[0] == 150  # both run all the way
    assert walk_plan(plated, [(600, 0)])[0] > walk_plan(light, [(600, 0)])[0]


@needs_server
def test_walking_spends_energy_and_the_rest_of_the_step_restores_it():
    state = character()
    ticks = walk(state, VARROCK, 10_000)
    assert state.run_energy == pytest.approx(100 - ticks * 0.55, abs=0.6)  # ran there
    sim = Simulator(build_catalog())
    sim.reset(seed=0)
    sim.state.inventory, sim.state.run_energy = {BONES: 20}, 0.0
    info = sim.step([o.id for o in sim.options].index("bury_bones")).info  # buried where it stands: no walk
    assert sim.state.run_energy == pytest.approx(info["duration"] * restore_per_tick(1))


@needs_server
def test_a_second_walk_starts_with_the_energy_restored_since_the_first():
    state, north = character(energy=30.0), (VARROCK[0], VARROCK[1] + 150, 0)
    first = walk(state, VARROCK, 10_000)
    expected = deepcopy(state)
    expected.run_energy = min(expected.run_energy + 200 * restore_per_tick(1), 100.0)
    ticks, energy = walk_plan(expected, [path(VARROCK, north)])
    walk(state, north, 10_000, elapsed=first + 200)  # 200 ticks after arriving
    assert state.run_energy == pytest.approx(energy) and state.energy_clock == first + 200 + ceil(ticks)


@needs_server
def test_route_ticks_predicts_the_walk():
    state = character(worn=(RUNE_BODY, RUNE_LEGS), energy=12.0)
    predicted = route_ticks(state, VARROCK)
    assert walk(state, VARROCK, 10_000) == predicted > route_ticks(character(), VARROCK)


@needs_server
def test_death_restores_run_energy():
    state = character(energy=3.0)
    die(state, now=0)
    assert state.run_energy == 100.0


@needs_server
def test_bank_deposit_worn_banks_armour_but_keeps_tools_and_ammunition_on():
    state = character(worn=(RUNE_BODY, RUNE_LEGS, BRONZE_AXE, BRONZE_ARROW))
    state.worn_amounts[gd.items()[BRONZE_ARROW].equipment_slot] = 50
    option = BankDepositWorn()
    assert option.available(state)
    before = weight(state)
    option.run(state, np.random.default_rng(0), 10_000)
    assert sorted(state.equipment.values()) == [BRONZE_ARROW, BRONZE_AXE] and state.worn(13) == 50
    assert state.bank[RUNE_BODY] == state.bank[RUNE_LEGS] == 1
    assert weight(state) == pytest.approx(before - 9.9 - 9.0)
    assert not option.available(state)  # only kept items are worn now
