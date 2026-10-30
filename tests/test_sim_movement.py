"""Tests for walking and the Al Kharid toll gate."""

from __future__ import annotations

from math import ceil

import pytest

from rlscape.combat.access import Progress
from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.movement import TOLL, route_ticks, uses_toll_gate, walk
from rlscape.sim.state import COINS, CharacterState
from rlscape.travel import path

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
LUMBRIDGE, AL_KHARID_FURNACE, VARROCK = (3222, 3218, 0), (3274, 3186, 0), (3212, 3424, 0)


def at(tile: tuple[int, int, int], coins: int = 0, **progress) -> CharacterState:
    state = CharacterState.fresh()
    state.location = tile
    state.inventory = {COINS: coins} if coins else {}
    state.progress = Progress(**progress)
    return state


def test_the_gate_lies_between_lumbridge_and_al_kharid_only():
    assert uses_toll_gate(LUMBRIDGE, AL_KHARID_FURNACE) and uses_toll_gate(AL_KHARID_FURNACE, LUMBRIDGE)
    assert not uses_toll_gate(VARROCK, AL_KHARID_FURNACE)  # north of the fence: the way round needs no gate
    assert not uses_toll_gate(LUMBRIDGE, (3190, 3235, 0))


@needs_server
def test_the_toll_is_paid_from_the_inventory_both_ways():
    state = at(LUMBRIDGE, coins=25)
    assert walk(state, AL_KHARID_FURNACE, 10_000) is not None and state.inventory[COINS] == 25 - TOLL
    walk(state, LUMBRIDGE, 10_000)
    assert state.inventory[COINS] == 25 - 2 * TOLL


@needs_server
def test_prince_ali_rescue_waives_the_toll():
    state = at(LUMBRIDGE, coins=25, quests_complete=frozenset({"PRINCE_ALI_RESCUE"}))
    walk(state, AL_KHARID_FURNACE, 10_000)
    assert state.inventory[COINS] == 25


@needs_server
def test_without_coins_the_walk_goes_round_the_fence():
    broke, paying = at(LUMBRIDGE), at(LUMBRIDGE, coins=TOLL)
    assert route_ticks(broke, AL_KHARID_FURNACE) > route_ticks(paying, AL_KHARID_FURNACE)
    assert route_ticks(paying, AL_KHARID_FURNACE) == ceil(path(LUMBRIDGE, AL_KHARID_FURNACE)[0] / 2)  # runs all the way
    ticks = walk(broke, AL_KHARID_FURNACE, 10_000)
    assert ticks == route_ticks(at(LUMBRIDGE), AL_KHARID_FURNACE) and broke.location == AL_KHARID_FURNACE


@needs_server
def test_nothing_is_paid_when_the_budget_runs_out_on_the_way():
    state = at(LUMBRIDGE, coins=25)
    assert walk(state, AL_KHARID_FURNACE, 5) is None and state.inventory[COINS] == 25 and state.location == LUMBRIDGE


@needs_server
def test_cooking_pays_the_toll_to_reach_al_kharids_range():
    sim = Simulator(build_catalog())
    sim.reset(seed=0)
    sim.state.inventory = {317: 5, COINS: 20}  # raw shrimps; no Cook's Assistant, so not the castle range
    info = sim.step([o.id for o in sim.options].index("cook_fish")).info
    assert info["items_delta"]["inventory"][COINS] == -TOLL
    assert sim.state.location == next(s.tile for s in gd.stations() if s.name == "Al Kharid" and s.kind == "range")
