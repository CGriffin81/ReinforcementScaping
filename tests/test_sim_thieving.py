"""Tests for sim v0's pickpocketing and the hitpoint rules it brings in (regeneration, eating, retreat)."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.health import REGEN_TICKS, eat_one, regenerate
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.skilling import slot_holding
from rlscape.sim.state import CharacterState
from rlscape.combat.access import rules_at
from rlscape.sim.combat import in_wilderness
from rlscape.sim.thieving import (FLEE_TICKS, LEFT_OUT, PICKPOCKET_TARGETS, STALLS, STEAL_TICKS, SUCCESS_TICKS,
                                  StealFromStall, pickpocket_chance, pickpocket_options, server_random,
                                  stall_options)

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
    action = [o.id for o in sim.options].index(slot_holding(sim.options, sim.state, "pickpocket_men"))
    info = sim.step(action).info
    assert info["termination"] == "out_of_food" and sim.state.hp <= sim.state.max_hp() / 2
    assert SHRIMPS not in sim.state.inventory and BREAD not in sim.state.inventory
    coins = info["items_delta"]["inventory"][COINS]
    assert coins % 3 == 0 and info["xp_gained"]["thieving"] == 8.0 * coins / 3
    assert not sim.action_mask()[action]  # half HP and no food: masked until HP regenerates or food is bought


@needs_server
def test_sampled_coin_rate_matches_the_success_chance():
    """With HP to spare (no eating), coins per tick = 3p / (2p + 5(1 - p))."""
    option = pickpocket_options()[0]  # men
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
    ids = [o.id for o in sim.options]
    duration = sim.step(ids.index(slot_holding(sim.options, sim.state, "wc_logs"))).info["duration"]  # chop, keep
    assert sim.state.hp == 5 + duration // REGEN_TICKS


@needs_server
def test_every_pickpocket_target_parses():
    targets = gd.pickpocket_targets()
    assert len(targets) == 18
    assert targets["CAVE_GOBLIN"].npc_ids == tuple(range(5752, 5769))  # IntStream.rangeClosed(5752, 5768)
    for ham in ("MALE_HAM_MEMBER", "FEMALE_HAM_MEMBER"):  # .insertEasyClue(1.0)
        assert [(l.item, l.weight) for l in targets[ham].loot if l.item == gd.CLUE_SLOT_EASY] == [(1, 1.0)]
        assert len(targets[ham].loot) == 27
    hero = targets["HERO"]
    assert (hero.level, hero.experience, hero.stun_damage_min, hero.stun_damage_max, hero.stun_ticks) == (
        80, 273.3, 6, 6, 4)


@needs_server
def test_each_target_has_an_option_or_a_reason():
    options = pickpocket_options()
    named = {o.target.name for o in options}
    assert named | set(LEFT_OUT) == set(gd.pickpocket_targets()) and not named & set(LEFT_OUT)
    assert [o.id for o in options] == list(PICKPOCKET_TARGETS)
    assert [o.target.level for o in options] == sorted(o.target.level for o in options)
    for option in options:
        assert not in_wilderness(option.tile)
        npc = next(n for n in option.target.npc_ids if option.tile in gd.spawns().get(n, ()))  # a real spawn
        assert not rules_at(gd.npcs()[npc].name, option.tile)


@needs_server
def test_weighted_loot_follows_the_table():
    """One weighted pick per success, P = weight / total; the clue slot gives nothing."""
    option = next(o for o in pickpocket_options() if o.target.name == "MALE_HAM_MEMBER")
    rng, counts, n, state = np.random.default_rng(3), {}, 20_000, CharacterState.fresh()
    for _ in range(n):
        state.inventory = {}
        assert option._succeed(state, rng, 1) == 1
        for item in state.inventory:
            counts[item] = counts.get(item, 0) + 1
    total = sum(loot.weight for loot in option.target.loot)
    for loot in option.target.loot:
        if loot.item == gd.CLUE_SLOT_EASY:
            continue
        expected = loot.weight / total
        assert counts.get(loot.item, 0) / n == pytest.approx(expected, abs=4 * (expected / n) ** 0.5 + 1e-3)
    assert gd.CLUE_SLOT_EASY not in counts


@needs_server
def test_can_roll_and_lost_loot_follow_the_server():
    options = {o.target.name: o for o in pickpocket_options()}
    man, ham, watchman = options["MAN"], options["MALE_HAM_MEMBER"], options["YANILLE_WATCHMAN"]
    full = CharacterState.fresh()
    full.inventory = {LOBSTER: 28}
    assert not man.can_roll(full) and not ham.can_roll(full)
    full.inventory = {LOBSTER: 27, COINS: 5}
    assert man.can_roll(full)  # coins already held: the guaranteed item fits
    assert not ham.can_roll(full) and not watchman.can_roll(full)  # no free slot; the bread doesn't fit
    one_free = CharacterState.fresh()
    one_free.inventory = {LOBSTER: 27}
    assert watchman.can_roll(one_free)  # the inventory isn't full, though coins and bread need two slots
    assert watchman._succeed(one_free, np.random.default_rng(0), 1) == 1
    assert one_free.inventory == {LOBSTER: 27, COINS: 60}  # the bread didn't fit, so it's lost
    assert watchman._succeed(one_free, np.random.default_rng(0), 1) == 0


@needs_server
def test_non_stackable_loot_fills_the_inventory():
    option = next(o for o in pickpocket_options() if o.target.name == "MALE_HAM_MEMBER")
    state = with_level(with_level(CharacterState.fresh(), "hitpoints", 99), "thieving", 40)
    state.inventory, state.hp, state.location = {}, 99, option.tile
    result = option.run(state, np.random.default_rng(4), 6_000)
    assert result.termination == "inventory_full" and state.free_slots() == 0 and not option.available(state)


@needs_server
def test_eating_keeps_a_heros_hit_from_killing():
    """Heroes hit for 6, above a 10-HP character's retreat point of 5: it eats at 6 or below instead."""
    option = next(o for o in pickpocket_options() if o.target.name == "HERO")
    for seed in range(20):
        state = with_level(CharacterState.fresh(), "thieving", 80)  # 10 hitpoints
        state.inventory, state.location = {LOBSTER: 20}, option.tile
        assert option.eat_below(state) == 6
        option.run(state, np.random.default_rng(seed), 6_000)  # would raise on a death
        assert state.hp > 0


@needs_server
def test_stalls_parse():
    stalls = gd.stalls()
    baker = stalls["BAKER_STALL"]
    assert (baker.level, baker.experience, baker.restock_ticks) == (5, 16.0, 4)
    assert baker.rewards == ((1891, 1), (BREAD, 1), (1901, 1))  # cake, bread, chocolate slice
    assert stalls["GEM_STALL"].restock_ticks == 300
    assert 2564 not in stalls["SPICE_STALL"].full_ids  # Ardougne's spice stall can't be stolen from


@needs_server
def test_the_stalls_are_in_the_guarded_ardougne_market():
    options = stall_options()
    assert [o.id for o in options] == list(STALLS)
    assert [o.stall.level for o in options] == [5, 20, 35, 50, 75]
    for option in options:
        assert max(abs(option.tile[0] - 2662), abs(option.tile[1] - 3305)) <= 12
        assert option.notice == pytest.approx(4 / 15)


def _thief(option: StealFromStall, level: int = 99) -> CharacterState:
    state = with_level(with_level(CharacterState.fresh(), "hitpoints", 99), "thieving", level)
    state.inventory, state.hp, state.location = {}, 99, option.tile
    return state


@needs_server
def test_an_unnoticed_steal_waits_for_the_restock():
    """Unguarded, the baker's stall gives one steal every 3 + 4 ticks, until the inventory is full."""
    option = next(o for o in stall_options() if o.id == "steal_bakers_stall")
    option.notice = 0.0
    state = _thief(option, level=5)
    result = option.run(state, np.random.default_rng(0), 6_000)
    assert result.termination == "inventory_full" and result.detail["steals"] == 28
    assert result.ticks == 28 * (STEAL_TICKS + 4)
    assert state.xp[SKILL_INDEX["thieving"]] == XP_FOR_LEVEL[5] + 28 * 16.0
    assert not option.available(state)


@needs_server
def test_a_steal_takes_one_reward_uniformly():
    option = next(o for o in stall_options() if o.id == "steal_bakers_stall")
    option.notice = 0.0
    rng, counts = np.random.default_rng(1), {}
    for _ in range(300):
        state = _thief(option)
        option.run(state, rng, 6_000)
        for item, amount in state.inventory.items():
            counts[item] = counts.get(item, 0) + amount
    assert sum(counts.values()) == 300 * 28
    for item, _ in option.stall.rewards:
        assert counts[item] / (300 * 28) == pytest.approx(1 / 3, abs=0.02)


@needs_server
def test_noticed_steals_run_off_and_come_back():
    option = next(o for o in stall_options() if o.id == "steal_silk_stall")
    rng, steals, ticks = np.random.default_rng(2), 0, 0
    for _ in range(200):
        state = _thief(option)
        result = option.run(state, rng, 2_000)
        steals += result.detail["steals"]
        ticks += result.ticks
    attempts = (ticks - steals * (STEAL_TICKS + 13)) / (STEAL_TICKS + FLEE_TICKS) + steals  # about; the end is cut off
    assert (attempts - steals) / attempts == pytest.approx(4 / 15, abs=0.03)


@needs_server
def test_eating_keeps_the_guards_swings_from_killing():
    option = next(o for o in stall_options() if o.id == "steal_bakers_stall")
    option.notice = 1.0  # every steal noticed
    for seed in range(20):
        state = with_level(CharacterState.fresh(), "thieving", 5)  # 10 hitpoints, starter gear
        state.inventory, state.location = {LOBSTER: 10}, option.tile
        assert option.eat_below(state) >= option._escape_hits(state)[1] * 2
        result = option.run(state, np.random.default_rng(seed), 6_000)  # would raise on a death
        assert result.termination == "out_of_food" and result.detail["steals"] == 0 and state.hp > 0
