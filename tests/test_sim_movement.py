"""Tests for walking, the Al Kharid toll gate and the Shantay Pass."""

from __future__ import annotations

from math import ceil, inf

import pytest

from rlscape.combat.access import Progress
from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.movement import (GATE_NORTH, GATE_SOUTH, PASS_PRICE, TOLL, in_desert, reachable, route_ticks,
                                  uses_toll_gate, walk)
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, CharacterState
from rlscape.sim.thieving import pickpocket_options
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


BANDIT_CAMP, POLLNIVNEACH = (3172, 2992, 0), (3333, 2950, 0)


def test_the_desert_lies_south_of_the_shantay_pass():
    assert in_desert(BANDIT_CAMP) and in_desert(POLLNIVNEACH) and in_desert(GATE_SOUTH)
    assert not in_desert(GATE_NORTH) and not in_desert(AL_KHARID_FURNACE) and not in_desert(LUMBRIDGE)
    assert in_desert((3480, 9495, 0))  # the Kalphite Queen, under the desert
    assert not uses_toll_gate(LUMBRIDGE, BANDIT_CAMP)  # west of x 3268, but in the desert: not by the toll gate


@needs_server
def test_going_south_buys_a_shantay_pass_and_coming_back_is_free():
    state = at(AL_KHARID_FURNACE, coins=20)
    assert walk(state, POLLNIVNEACH, 10_000) is not None and state.inventory[COINS] == 20 - PASS_PRICE
    assert walk(state, AL_KHARID_FURNACE, 10_000) is not None and state.inventory[COINS] == 20 - PASS_PRICE
    inside = at(BANDIT_CAMP)  # within the desert, nothing to pay
    assert walk(inside, POLLNIVNEACH, 10_000) is not None and inside.location == POLLNIVNEACH


@needs_server
def test_without_coins_for_a_pass_the_desert_is_unreachable():
    broke = at(AL_KHARID_FURNACE, coins=PASS_PRICE - 1)
    assert not reachable(broke, BANDIT_CAMP) and route_ticks(broke, BANDIT_CAMP) == inf
    assert walk(broke, BANDIT_CAMP, 10_000) is None and broke.location == AL_KHARID_FURNACE
    assert broke.inventory[COINS] == PASS_PRICE - 1


@needs_server
def test_the_pass_comes_before_the_al_kharid_toll():
    """From Lumbridge, coins short of both go round the fence and keep 5 for the pass."""
    short, both = at(LUMBRIDGE, coins=TOLL + PASS_PRICE - 1), at(LUMBRIDGE, coins=TOLL + PASS_PRICE)
    assert route_ticks(short, BANDIT_CAMP) > route_ticks(both, BANDIT_CAMP)
    walk(short, BANDIT_CAMP, 10_000)
    walk(both, BANDIT_CAMP, 10_000)
    assert short.inventory[COINS] == TOLL - 1 and COINS not in both.inventory


@needs_server
def test_the_desert_pickpocket_targets_need_the_pass():
    options = {o.id: o for o in pickpocket_options()}
    thugs = options["pickpocket_menaphite_thugs"]
    assert in_desert(thugs.tile) and in_desert(options["pickpocket_desert_bandits"].tile)
    state = at(AL_KHARID_FURNACE, coins=PASS_PRICE)
    state.xp[SKILL_INDEX["thieving"]] = float(XP_FOR_LEVEL[65])
    assert thugs.available(state)
    state.inventory[COINS] = PASS_PRICE - 1
    assert not thugs.available(state)
