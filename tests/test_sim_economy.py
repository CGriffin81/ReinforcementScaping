"""Tests for sim v0's inventory and alchemy options: banking, withdrawing for an activity, dropping, alchemy."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.economy import (
    ALCH_TICKS,
    Alch,
    BankDeposit,
    BankWithdraw,
    Drop,
    DropMisc,
    can_cast_alchemy,
    kept_on_deposit,
)
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, CharacterState
from rlscape.travel import BANKING_TICKS

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
LOGS, LOGS_NOTE, RUNE_SCIMITAR, NATURE, FIRE, STAFF_OF_FIRE = 1511, 1512, 1333, 561, 554, 1387
COPPER, TIN, COAL, IRON_ORE, HAMMER, BRONZE_BAR, BONES = 436, 438, 453, 440, 2347, 2349, 526


def character(inventory: dict[int, int], bank: dict[int, int] | None = None, **levels: int) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory, state.bank = dict(inventory), dict(bank or {})
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


@needs_server
def test_banking_keeps_tools_food_ammunition_runes_and_bait():
    for item in (1351, 1265, 590, 303, 315, 2309, 882, 556, 314, HAMMER):  # axe, pickaxe, tinderbox, net, food, ...
        assert kept_on_deposit(item), item
    for item in (LOGS, COPPER, BONES, 1205, 1925, COINS):  # products, starter junk, coins
        assert not kept_on_deposit(item), item


@needs_server
def test_deposit_banks_products_and_turns_notes_into_items():
    state = character({1351: 1, LOGS: 5, LOGS_NOTE: 20, COINS: 40}, {LOGS: 1})
    state.task = "woodcutting"  # the axe is its kit
    result = BankDeposit().run(state, np.random.default_rng(0), 10_000)
    assert state.inventory == {1351: 1} and state.bank == {LOGS: 26, COINS: 40}
    assert result.ticks >= BANKING_TICKS and result.termination == "completed"


@needs_server
def test_withdrawing_for_steel_keeps_the_two_to_one_mix():
    state = character({}, {COAL: 100, IRON_ORE: 100})
    BankWithdraw("smelt_steel").run(state, np.random.default_rng(1), 10_000)
    assert state.inventory == {COAL: 18, IRON_ORE: 9}  # 9 bars' worth of 2 coal + 1 iron ore fill 27 of 28 slots


@needs_server
def test_withdrawing_for_smithing_fetches_the_hammer_first():
    state = character({}, {HAMMER: 1, BRONZE_BAR: 50})
    option = BankWithdraw("smith_bronze")
    assert option.available(state)
    option.run(state, np.random.default_rng(2), 10_000)
    assert state.inventory == {HAMMER: 1, BRONZE_BAR: 27}


@needs_server
def test_withdrawing_for_cooking_brings_a_log_for_the_fire():
    state = character({590: 1}, {317: 40, LOGS: 5})
    BankWithdraw("cook_fish").run(state, np.random.default_rng(3), 10_000)
    assert state.inventory[LOGS] == 1 and state.inventory[317] == 26 and state.free_slots() == 0


@needs_server
def test_drops_leave_net_worth_and_are_reported():
    sim = Simulator(build_catalog(vocabulary=[LOGS]))
    sim.reset(seed=0)
    sim.state.inventory[LOGS] = 3
    worth = sim.state.net_worth()
    info = sim.step([o.id for o in sim.options].index(f"drop_{LOGS}")).info
    assert info["items_delta"]["dropped"] == {LOGS: 3} and info["duration"] == 3
    assert sim.state.net_worth() == pytest.approx(worth - 3 * gd.item_values()[LOGS])


@needs_server
def test_drop_misc_spares_vocabulary_coins_and_kept_items():
    state = character({LOGS: 2, 1205: 1, COINS: 10, 1351: 1, 315: 1})
    DropMisc(frozenset({LOGS})).run(state, np.random.default_rng(4), 10_000)
    assert state.inventory == {LOGS: 2, COINS: 10, 1351: 1, 315: 1} and state.dropped == {1205: 1}


@needs_server
def test_high_alchemy_follows_the_server():
    state = character({NATURE: 2, FIRE: 10, RUNE_SCIMITAR: 2}, magic=55)
    result = Alch(True, RUNE_SCIMITAR).run(state, np.random.default_rng(5), 10_000)
    assert state.inventory == {COINS: 2 * gd.alchemy_values()[RUNE_SCIMITAR][0]}
    assert result.ticks == 2 * ALCH_TICKS and state.xp[SKILL_INDEX["magic"]] == XP_FOR_LEVEL[55] + 2 * 65.0


@needs_server
def test_alchemy_needs_the_level_and_runes_unless_a_fire_staff_is_wielded():
    assert not can_cast_alchemy(character({NATURE: 1, FIRE: 5}, magic=54), high=True)
    assert not can_cast_alchemy(character({NATURE: 1, FIRE: 4}, magic=55), high=True)
    assert can_cast_alchemy(character({NATURE: 1, FIRE: 3}, magic=21), high=False)
    staffed = character({NATURE: 1, LOGS: 1}, magic=55)
    staffed.equipment = {3: STAFF_OF_FIRE}
    assert can_cast_alchemy(staffed, high=True)
    Alch(True, LOGS).run(staffed, np.random.default_rng(6), 10_000)
    assert NATURE not in staffed.inventory and LOGS not in staffed.inventory  # no fire runes were needed


@needs_server
def test_an_empty_vocabulary_leaves_only_the_misc_actions():
    ids = [o.id for o in build_catalog(vocabulary=())]
    assert "drop_misc" in ids and "high_alch_misc" in ids and not any(i.startswith("drop_") and i != "drop_misc"
                                                                      for i in ids)
    assert f"high_alch_{LOGS}" in [o.id for o in build_catalog(vocabulary=[LOGS])]
    assert Drop(LOGS).id == f"drop_{LOGS}"


@needs_server
def test_the_frozen_buyer_pays_the_2009_price_and_skips_items_without_one():
    from rlscape.sim.economy import SellGE
    prices = gd.ge_prices_2009()
    no_price = next(i for i in gd.alchemy_values() if i not in prices and i != COINS and not kept_on_deposit(i))
    state = character({LOGS: 10, LOGS_NOTE: 5, no_price: 1})
    SellGE(vocabulary=frozenset()).run(state, np.random.default_rng(7), 10_000)
    assert state.inventory == {no_price: 1, COINS: 15 * prices[LOGS]}  # banknotes sell as their item
    assert prices[1540] == 301  # the anti-dragon shield: on the GE since 2026-11-06 (Caleb), at its 2009 price


@needs_server
def test_general_stores_pay_low_alchemy_less_overstock():
    from rlscape.sim.economy import SellStore, store_sale_value
    low, value = gd.alchemy_values()[RUNE_SCIMITAR][1], gd.item_base_values()[RUNE_SCIMITAR]
    assert store_sale_value(RUNE_SCIMITAR, 1) == low
    assert store_sale_value(RUNE_SCIMITAR, 3) == low + round(low - 0.03 * value) + round(low - 0.06 * value)
    assert store_sale_value(LOGS, 20) >= 20  # never below a coin each
    state = character({RUNE_SCIMITAR: 2})
    SellStore(RUNE_SCIMITAR).run(state, np.random.default_rng(8), 10_000)
    assert state.inventory == {COINS: store_sale_value(RUNE_SCIMITAR, 2)}


@needs_server
def test_deposit_keeps_only_the_kit_of_the_task_at_hand():
    bronze_axe, iron_axe, bronze_pickaxe, shrimps, iron_scimitar = 1351, 1349, 1265, 315, 1323
    held = {bronze_axe: 1, iron_axe: 1, bronze_pickaxe: 1, shrimps: 5, iron_scimitar: 1, LOGS: 3}
    expected = {None: {}, "woodcutting": {iron_axe: 1}, "mining": {bronze_pickaxe: 1}, "thieving": {shrimps: 5},
                "combat:melee": {iron_scimitar: 1, shrimps: 5}}
    for task, kept in expected.items():
        state = character(dict(held))
        state.task = task
        BankDeposit().run(state, np.random.default_rng(0), 10_000)
        assert state.inventory == kept, task  # the obsolete bronze axe and the food go unless the task needs them


@needs_server
def test_kit_withdrawals_bring_back_a_gathering_tool_and_any_food():
    from rlscape.sim.buying import BankWithdrawAnyFood
    from rlscape.sim.economy import BankWithdrawKit

    bronze_axe, iron_axe, rune_axe, shrimps, trout, feathers, fly_rod = 1351, 1349, 1359, 315, 333, 314, 309
    state = character({bronze_axe: 1}, {iron_axe: 1, rune_axe: 1, shrimps: 5, trout: 3, feathers: 500, fly_rod: 1})
    option = BankWithdrawKit("woodcutting", "woodcutting")
    option.run(state, np.random.default_rng(0), 10_000)
    assert state.inventory == {bronze_axe: 1, iron_axe: 1}  # rune needs Woodcutting 41
    assert not option.available(state)
    BankWithdrawKit("fish_fly", "fishing:LURE").run(state, np.random.default_rng(0), 10_000)
    assert state.inventory[fly_rod] == 1 and state.inventory[feathers] == 500
    state.inventory.update({LOGS: 21})  # 3 free slots
    BankWithdrawAnyFood().run(state, np.random.default_rng(0), 10_000)
    assert state.inventory[trout] == 3 and shrimps not in state.inventory  # the best healing first
