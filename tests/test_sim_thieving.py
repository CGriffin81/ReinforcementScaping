"""Tests for sim v0's pickpocketing and the hitpoint rules it brings in (regeneration, eating, retreat)."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.health import REGEN_TICKS, eat_one, regenerate
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState
from rlscape.sim.thieving import SUCCESS_TICKS, Pickpocket, pickpocket_chance, server_random

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
COINS, SHRIMPS, BREAD, LOBSTER = 995, 315, 2309, 379


def with_level(state: CharacterState, skill: str, level: int) -> CharacterState:
    state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


@needs_server
def test_pickpocket_and_food_tables_parse():
    man = gd.pickpocket_targets()["MAN"]
    assert (man.level, man.low, man.high, man.experience, man.stun_ticks) == (1, 180.0, 240.0, 8.0, 5)
    assert (man.stun_damage_min, man.stun_damage_max) == (1, 1) and man.loot[0].item == COINS
    assert man.loot[0].min_amount == man.loot[0].max_amount == 3 and man.loot[0].always
    heals = gd.food_healing()
    assert (heals[SHRIMPS], heals[BREAD], heals[LOBSTER]) == (3, 5, 12)


@needs_server
def test_pickpocket_chance_matches_the_servers_roll():
    man, rng = gd.pickpocket_targets()["MAN"], np.random.default_rng(0)
    for level in (1, 40, 99):
        threshold = 100 * (np.floor(180 * (99 - level) / 98) + np.floor(240 * (level - 1) / 98) + 1) / 256
        rolls = rng.uniform(1.0, 100.0, 400_000) <= threshold  # randomDouble(1, 100) <= threshold
        assert rolls.mean() == pytest.approx(pickpocket_chance(man, level), abs=0.003)


def test_server_random_excludes_the_upper_bound():
    rng = np.random.default_rng(1)
    assert server_random(rng, 1, 1) == 1
    assert set(server_random(rng, 1, 3) for _ in range(500)) == {1, 2}


@needs_server
def test_regeneration_runs_on_a_101_tick_cycle():
    state = CharacterState.fresh()
    state.hp = 5
    regenerate(state, REGEN_TICKS - 1)
    assert state.hp == 5
    regenerate(state, 1)
    assert state.hp == 6 and state.regen_counter == 0
    regenerate(state, 20 * REGEN_TICKS)
    assert state.hp == state.max_hp() == 10  # never above the maximum


@needs_server
def test_cheapest_food_is_eaten_first():
    state = CharacterState.fresh()  # one shrimp (3) and one bread (5)
    state.hp = 2
    assert eat_one(state) and state.hp == 5 and SHRIMPS not in state.inventory
    assert eat_one(state) and state.hp == 10 and BREAD not in state.inventory
    assert not eat_one(state)


@needs_server
def test_fresh_character_pickpockets_until_the_food_runs_out():
    sim = Simulator(build_catalog())
    sim.reset(seed=5)
    action = [o.id for o in sim.options].index("pickpocket_men")
    info = sim.step(action).info
    assert info["termination"] == "out_of_food" and sim.state.hp <= sim.state.max_hp() / 2
    assert SHRIMPS not in sim.state.inventory and BREAD not in sim.state.inventory
    coins = info["items_delta"]["inventory"][COINS]
    assert coins % 3 == 0 and info["xp_gained"]["thieving"] == 8.0 * coins / 3
    assert not sim.action_mask()[action]  # half HP and no food: masked until HP regenerates or food is bought


@needs_server
def test_sampled_coin_rate_matches_the_success_chance():
    """With HP to spare (no eating), coins per tick = 3p / (2p + 5(1 - p))."""
    sim = Simulator(build_catalog())
    option = next(o for o in sim.options if isinstance(o, Pickpocket))
    p = pickpocket_chance(option.target, 40)
    expected = 3 * p / (SUCCESS_TICKS * p + option.target.stun_ticks * (1 - p))
    rng, coins, ticks = np.random.default_rng(2), 0, 0
    for _ in range(300):
        state = with_level(with_level(CharacterState.fresh(), "hitpoints", 99), "thieving", 40)
        state.hp, state.location = 99, option.tile
        result = option.run(state, rng, 600)  # about 46 failures: never down to the 49.5 HP retreat point
        coins += state.inventory.get(COINS, 0)
        ticks += result.ticks
    assert coins / ticks == pytest.approx(expected, rel=0.03)


@needs_server
def test_the_engine_regenerates_hitpoints_during_other_options():
    sim = Simulator(build_catalog())
    sim.reset(seed=0)
    sim.state.hp = 5
    duration = sim.step(0).info["duration"]  # wc_logs
    assert sim.state.hp == 5 + duration // REGEN_TICKS
