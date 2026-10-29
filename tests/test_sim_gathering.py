"""Tests for sim v0's mining and fishing, checked against the server's tables and its own random rolls."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.fishing import Fishing
from rlscape.sim.gathering import WALK_BETWEEN_RESOURCES, Site
from rlscape.sim.mining import ATTEMPT_TICKS, GEMS, Mining, best_pickaxe, mine_chance, uniform_race
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
BRONZE_PICKAXE, RUNE_PICKAXE, IRON_ORE, FLY_ROD, FEATHER = 1265, 1275, 440, 309, 314
RAW_SHRIMPS, RAW_ANCHOVIES = 317, 321


def with_level(state: CharacterState, skill: str, level: int) -> CharacterState:
    state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


@needs_server
def test_rock_fish_and_tree_tables_parse():
    rocks = gd.rock_types()
    assert (rocks[1].reward, rocks[2].reward) == (436, 438)  # copper and tin share a case with a ?: reward
    assert (rocks[6].reward, rocks[6].level, rocks[6].experience) == (IRON_ORE, 15, 35.0)
    assert (rocks[8].reward, rocks[8].level, rocks[8].rate, rocks[8].respawn_min) == (453, 30, 0.4, 50)
    assert set(range(19, 24)) <= gd.tree_types().keys()  # WoodcuttingNode's second constructor (farming trees)
    shrimp = gd.fish_types()["SHRIMP"]
    assert (shrimp.item, shrimp.level, shrimp.experience, shrimp.low_chance, shrimp.high_chance) == (
        RAW_SHRIMPS, 1, 10.0, 0.191, 0.5)
    methods = gd.fishing_methods()
    assert methods["SMALL_NET"].fish == ("SHRIMP", "ANCHOVIE") and methods["LURE"].bait == (FEATHER, 10087)
    assert gd.fish_spot_locations()["DRAYNOR"] == ((3085, 3230, 0), (3086, 3227, 0))


def test_uniform_race_matches_the_servers_two_rolls():
    rng = np.random.default_rng(0)
    for a, b in ((5.0, 1.05), (20.0, 37.8), (40.0, 40.0)):
        rolls = rng.random(400_000) * a < rng.random(400_000) * b  # Math.random() * a < Math.random() * b
        assert rolls.mean() == pytest.approx(uniform_race(a, b), abs=0.004)


@needs_server
def test_best_pickaxe_respects_the_level_requirement():
    state = CharacterState.fresh()
    assert best_pickaxe(state).name == "BRONZE_PICKAXE"
    state.add(RUNE_PICKAXE)
    assert best_pickaxe(state).name == "BRONZE_PICKAXE"
    assert best_pickaxe(with_level(state, "mining", 41)).name == "RUNE_PICKAXE"


@needs_server
def test_sampled_ores_match_the_server_success_chance():
    """Every ore empties its rock, so with plenty of rocks an ore costs ATTEMPT_TICKS / p plus a walk."""
    option = Mining("test", 6, Site((3286, 3368, 0), 10_000, "test"))
    state = CharacterState.fresh()
    state.location = option.site.tile
    p = mine_chance(option.rock, gd.skilling_tools()["BRONZE_PICKAXE"], 50)
    rng, per_ore, ores, gems = np.random.default_rng(1), [], 0, 0
    for _ in range(300):
        state.inventory = {BRONZE_PICKAXE: 1}
        with_level(state, "mining", 50)  # 27 iron ores (945 XP) stay inside level 50
        result = option.run(state, rng, 100_000)
        mined = state.inventory.get(IRON_ORE, 0)
        per_ore.append(result.ticks / mined)
        ores += mined
        gems += sum(state.inventory.get(g, 0) for g in GEMS)
    assert np.mean(per_ore) == pytest.approx(ATTEMPT_TICKS / p + WALK_BETWEEN_RESOURCES, rel=0.03)
    assert 10 <= gems <= 50  # 1 in 282 of about 8,000 ores: about 29


@needs_server
def test_catch_mix_follows_the_servers_sequential_roll():
    option = Fishing("test", "SMALL_NET", "DRAYNOR")
    state = with_level(CharacterState.fresh(), "fishing", 30)
    fish, weights, p_any = option.catch_odds(state)
    assert [f.name for f in fish] == ["SHRIMP", "ANCHOVIE"]
    # rollFish line for line: shrimp first, anchovies only if the shrimp roll fails
    rng = np.random.default_rng(2)
    p_shrimp, p_anchovy = (f.success_chance(30) for f in fish)
    shrimp_roll, anchovy_roll = rng.random(400_000) < p_shrimp, rng.random(400_000) < p_anchovy
    caught = shrimp_roll | anchovy_roll
    assert caught.mean() == pytest.approx(p_any, abs=0.004)
    assert shrimp_roll[caught].mean() == pytest.approx(weights[0], abs=0.004)


@needs_server
def test_sampled_fish_follow_the_catch_odds():
    option = Fishing("test", "SMALL_NET", "DRAYNOR")
    state = with_level(CharacterState.fresh(), "fishing", 30)
    _, weights, _ = option.catch_odds(state)
    rng, shrimps, anchovies = np.random.default_rng(3), 0, 0
    for _ in range(300):
        state.inventory, state.location = {303: 1}, option.spots[0]
        with_level(state, "fishing", 30)
        option.run(state, rng, 100_000)
        shrimps += state.inventory.get(RAW_SHRIMPS, 0)
        anchovies += state.inventory.get(RAW_ANCHOVIES, 0)
    assert shrimps / (shrimps + anchovies) == pytest.approx(weights[0], abs=0.02)


@needs_server
def test_lure_fishing_uses_a_feather_per_fish_and_stops_without_them():
    option = Fishing("test", "LURE", "BARBARIAN")
    state = with_level(CharacterState.fresh(), "fishing", 30)
    state.inventory, state.location = {FLY_ROD: 1, FEATHER: 5}, option.spots[0]
    assert "RAINBOW_FISH" not in {f.name for f in option.catch_odds(state)[0]}  # needs stripy feathers
    result = option.run(state, np.random.default_rng(4), 100_000)
    assert result.termination == "inputs_exhausted" and FEATHER not in state.inventory
    assert sum(n for item, n in state.inventory.items() if item != FLY_ROD) == 5


@needs_server
def test_fresh_character_can_chop_mine_copper_and_tin_net_shrimp_and_pickpocket():
    sim = Simulator(build_catalog())
    sim.reset(seed=0)
    available = {o.id for o, ok in zip(sim.options, sim.action_mask()) if ok and o.family == "gathering"}
    assert available == {"wc_logs", "mine_copper", "mine_tin", "fish_shrimp", "pickpocket_men"}
