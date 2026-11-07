"""Tests for sim v0's buying (option catalog §8): shop stock and prices, GE and shop buys, their masks, and the gear
and food withdrawals."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat.access import Progress
from rlscape.gamedata import server as gd
from rlscape.sim import build_catalog
from rlscape.sim.buying import (
    FOOD_TIERS,
    BankWithdrawForSale,
    LUMBRIDGE_STORE,
    BankWithdrawFood,
    BankWithdrawGear,
    BuyGE,
    BuyShop,
    buying_options,
    gear_to_withdraw,
    is_upgrade,
)
from rlscape.sim.economy import STORE_TICKS, BankDeposit, BankWithdraw, SellGE, SellStore, store_sale_value
from rlscape.sim.equipment import wield_best
from rlscape.sim.movement import TOLL
from rlscape.sim.processing import Smith
from rlscape.sim.shops import PLAYER_STOCK, PLAYER_STOCK_CLEAR_TICKS, purchase_cost, set_stock, stock, unit_price
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, CharacterState
from rlscape.travel import BANKING_TICKS

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
IRON_AXE, STEEL_AXE, RUNE_AXE, HAMMER, FISHING_ROD, STAFF_OF_AIR = 1349, 1353, 1359, 2347, 307, 1381
SHARK, SHARK_NOTE, TUNA, BREAD, AIR, BRONZE_ARROW, IRON_BAR, IRON_BAR_NOTE = 385, 386, 361, 2309, 556, 882, 2351, 2352
RUNE_HELM, RUNE_BODY, IRON_SCIMITAR, SHORTBOW, BRONZE_SWORD = 1163, 1127, 1323, 841, 1277
DRAGON_LONGSWORD, BERSERKER_HELM = 1305, 3751
ATTRACTOR, ACCUMULATOR = 10498, 10499
RNG = np.random.default_rng(0)


def character(inventory: dict[int, int], bank: dict[int, int] | None = None, **levels: int) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory, state.bank = dict(inventory), dict(bank or {})
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


@needs_server
def test_the_catalog_has_153_buys_and_9_withdrawals():
    ids = [o.id for o in buying_options()]
    assert sum(i.startswith("buy_ge_") for i in ids) == 116 and sum(i.startswith("buy_shop_") for i in ids) == 37
    assert [i for i in ids if i.startswith("bank_withdraw")] == [
        "bank_withdraw_gear_melee", "bank_withdraw_gear_ranged", "bank_withdraw_gear_magic",
        *(f"bank_withdraw_{food}" for food in FOOD_TIERS), "bank_withdraw_food", "bank_withdraw_for_sale"]
    assert len(set(ids)) == len(ids) and set(ids) <= {o.id for o in build_catalog()}
    assert all(o.item in gd.ge_prices_2009() for o in buying_options() if isinstance(o, BuyGE))


@needs_server
def test_shop_prices_and_restocking_follow_the_server():
    value, normal = gd.item_base_values()[IRON_AXE], 10  # Bob's stocks 10 iron axes
    assert unit_price(IRON_AXE, normal, 10) == value and unit_price(IRON_AXE, normal, 0) == -(-value * 130 // 100)
    assert unit_price(IRON_AXE, normal, 5) == -(-value * 115 // 100)  # 130 - 30 * 5 // 10 = 115%
    assert purchase_cost(54, IRON_AXE, 10, 3) == sum(unit_price(IRON_AXE, normal, s) for s in (10, 9, 8))
    state = CharacterState.fresh()
    set_stock(state, 54, IRON_AXE, 7, now=150)
    assert [stock(state, 54, IRON_AXE, t) for t in (150, 199, 200, 399, 400, 10_000)] == [7, 7, 8, 9, 10, 10]
    set_stock(state, PLAYER_STOCK, 1511, 30, now=100)  # sold to a general store, which doesn't stock logs
    assert stock(state, PLAYER_STOCK, 1511, PLAYER_STOCK_CLEAR_TICKS - 1) == 30
    assert stock(state, PLAYER_STOCK, 1511, PLAYER_STOCK_CLEAR_TICKS) == 0  # Shops.tick clears the player stock


@needs_server
def test_ge_buys_come_as_banknotes_unless_one_item_or_a_stack():
    price = gd.ge_prices_2009()[SHARK]
    state = character({COINS: 10 * price + 5})
    result = BuyGE(SHARK).run(state, RNG, 10_000)
    assert state.inventory == {SHARK_NOTE: 10, COINS: 5} and result.termination == "completed"
    single = character({COINS: price})
    BuyGE(SHARK).run(single, RNG, 10_000)
    assert single.inventory == {SHARK: 1}
    runes = character({COINS: 10_000})
    BuyGE(AIR).run(runes, RNG, 10_000)
    assert runes.inventory == {AIR: 100, COINS: 10_000 - 100 * gd.ge_prices_2009()[AIR]}  # the lot of 100


@needs_server
def test_coins_in_the_bank_cost_a_bank_stop_at_the_ge():
    price = gd.ge_prices_2009()[IRON_BAR]
    pocket, banked = character({COINS: 1_000_000}), character({}, {COINS: 1_000_000})
    first, second = BuyGE(IRON_BAR).run(pocket, RNG, 10_000), BuyGE(IRON_BAR).run(banked, RNG, 10_000)
    assert second.ticks == first.ticks + BANKING_TICKS
    assert pocket.inventory[IRON_BAR_NOTE] == banked.inventory[IRON_BAR_NOTE] == 1_000  # the lot for inputs
    assert banked.bank[COINS] == 1_000_000 - 1_000 * price and COINS not in banked.inventory  # just the shortfall


@needs_server
def test_shop_buys_land_as_items_and_move_the_shared_stock():
    state = character({COINS: 1_000})
    result = BuyShop(BREAD).run(state, RNG, 10_000)  # Wydin's stocks 10 bread
    assert state.inventory[BREAD] == 10 and result.ticks >= STORE_TICKS
    assert state.inventory[COINS] == 1_000 - purchase_cost(77, BREAD, 10, 10)
    assert stock(state, 77, BREAD, result.ticks) == 0  # sold out (the stock is shared)
    assert stock(state, 77, BREAD, result.ticks + 1_000) == 10  # a unit back every 100 ticks
    full = character({COINS: 1_000, 1925: 25})  # two free slots
    BuyShop(BREAD).run(full, RNG, 10_000)
    assert full.inventory[BREAD] == 2


@needs_server
def test_a_shop_buy_short_of_coins_stops_at_a_bank_first():
    state = character({}, {COINS: 500})
    BuyShop(HAMMER).run(state, RNG, 10_000)
    assert state.inventory == {HAMMER: 1} and state.bank[COINS] == 500 - unit_price(HAMMER, 10, 10)
    assert stock(state, LUMBRIDGE_STORE, HAMMER, state.tick) == 9


@needs_server
def test_buying_at_zekes_pays_the_al_kharid_toll_too():
    price = purchase_cost(150, IRON_SCIMITAR, 10, 1)
    state = character({COINS: price + TOLL})  # at the Lumbridge spawn, west of the gate
    state.progress = Progress()  # before Prince Ali Rescue, which a new character has done (no toll)
    BuyShop(IRON_SCIMITAR).run(state, RNG, 10_000)
    assert state.inventory == {IRON_SCIMITAR: 1}


@needs_server
def test_buys_are_masked_unless_affordable_usable_an_upgrade_and_with_room():
    rich = 10**7
    assert BuyGE(IRON_AXE).available(character({COINS: rich}))
    assert not BuyGE(IRON_AXE).available(character({COINS: 27}))  # 28 gp at the GE
    assert not BuyGE(IRON_AXE).available(character({COINS: rich}, {STEEL_AXE: 1}, woodcutting=6))  # a better axe
    assert BuyGE(IRON_AXE).available(character({COINS: rich}, {STEEL_AXE: 1}))  # held, but the level is too low
    assert not BuyGE(RUNE_AXE).available(character({COINS: rich}, woodcutting=40))
    assert BuyGE(RUNE_AXE).available(character({COINS: rich}, woodcutting=41))  # the tool's level, not Attack's
    assert BuyGE(RUNE_HELM).available(character({COINS: rich}, defence=40))  # pieces: no quest for the helm
    assert not BuyGE(DRAGON_LONGSWORD).available(character({COINS: rich}, attack=59))
    assert BuyGE(DRAGON_LONGSWORD).available(character({COINS: rich}, attack=60))  # Lost City is done (OQ-24)
    assert BuyGE(BERSERKER_HELM).available(character({COINS: rich}, defence=45))  # the Fremennik Trials too
    no_quests = character({COINS: rich}, defence=45, attack=60)
    no_quests.progress = Progress()
    assert not BuyGE(DRAGON_LONGSWORD).available(no_quests) and not BuyGE(BERSERKER_HELM).available(no_quests)
    no_quests = character({COINS: rich}, defence=40)
    no_quests.progress = Progress()
    assert not BuyGE(RUNE_BODY).available(no_quests)  # the body needs Dragon Slayer
    assert BuyGE(RUNE_BODY).available(character({COINS: rich}, defence=40))  # which a new character has done
    assert not BuyGE(FISHING_ROD).available(character({COINS: rich}, {FISHING_ROD: 1}))
    assert not BuyGE(STAFF_OF_AIR).available(character({COINS: rich, STAFF_OF_AIR: 1}))
    assert BuyGE(TUNA).available(character({COINS: rich, TUNA: 20}))  # consumables have no upgrade check
    full = character({COINS: rich, 1925: 27})
    assert not BuyGE(IRON_AXE).available(full) and not BuyGE(TUNA).available(full)
    assert BuyGE(AIR).available(character({COINS: rich, AIR: 1, 1925: 26}))  # stacks onto the runes held
    assert is_upgrade(character({}, {BRONZE_SWORD: 1}), IRON_SCIMITAR)
    state = character({COINS: rich})
    set_stock(state, 54, IRON_AXE, 0, now=0)
    assert not BuyShop(IRON_AXE).available(state)  # sold out at Bob's


@needs_server
def test_avas_devices_are_bought_on_the_ge_at_calebs_prices_one_better_than_any_held():
    """Caleb, 2026-11-07: the GE sells Ava's devices at 2,500 and 10,000 gp, and net worth values them there. The
    accumulator outranks the attractor and needs Ranged 50 (the fork's item config); both need Animal Magnetism
    (done by every new character)."""
    assert BuyGE(ATTRACTOR).price == 2_500 and BuyGE(ACCUMULATOR).price == 10_000
    assert gd.item_values()[ATTRACTOR] == 2_500 and gd.item_values()[ACCUMULATOR] == 10_000
    rich = 10**5
    assert BuyGE(ATTRACTOR).available(character({COINS: rich}))  # no Ranged level for the attractor
    assert not BuyGE(ACCUMULATOR).available(character({COINS: rich}, ranged=49))
    assert BuyGE(ACCUMULATOR).available(character({COINS: rich}, ranged=50))
    assert not BuyGE(ATTRACTOR).available(character({COINS: 2_499}))
    assert not BuyGE(ATTRACTOR).available(character({COINS: rich}, {ATTRACTOR: 1}))
    assert BuyGE(ACCUMULATOR).available(character({COINS: rich}, {ATTRACTOR: 1}, ranged=50))  # the upgrade
    worn = character({COINS: rich}, ranged=50)
    worn.equipment[1] = ACCUMULATOR
    assert not BuyGE(ATTRACTOR).available(worn) and not BuyGE(ACCUMULATOR).available(worn)
    no_quests = character({COINS: rich})
    no_quests.progress = Progress()
    assert not BuyGE(ATTRACTOR).available(no_quests)
    state = character({COINS: 3_000})
    BuyGE(ATTRACTOR).run(state, RNG, 10_000)
    assert state.inventory.get(ATTRACTOR) == 1 and state.inventory.get(COINS) == 500
    # untradeable: no Drop (the game offers Destroy; checked live), no alchemy, no store sale; the GE buys it back
    actions = {o.id: o for o in build_catalog()}
    assert not any(actions[f"{kind}_{ATTRACTOR}"].available(state)
                   for kind in ("drop", "high_alch", "low_alch", "sell_store"))
    assert actions[f"sell_ge_{ATTRACTOR}"].available(state)


@needs_server
def test_gear_withdrawals_bring_back_what_the_last_deposit_banked():
    state = CharacterState.fresh()
    wield_best(state, "melee")
    BankDeposit().run(state, RNG, 10_000)
    assert SHORTBOW in state.bank and not BankWithdrawGear("melee").available(state)
    BankWithdrawGear("ranged").run(state, RNG, 10_000)
    assert state.inventory.get(SHORTBOW) == 1 and SHORTBOW not in state.bank
    armoured = character({}, {RUNE_HELM: 1, 1153: 1, 1191: 1, IRON_SCIMITAR: 1}, defence=40)
    BankWithdrawGear("melee").run(armoured, RNG, 10_000)
    order = list(armoured.inventory)
    assert order[0] == IRON_SCIMITAR and set(order) == {IRON_SCIMITAR, RUNE_HELM, 1191}  # not the worse iron helm


@needs_server
def test_food_withdrawals_bank_the_notes_and_fill_the_free_slots():
    state = character({SHARK_NOTE: 40, 1925: 10}, {SHARK: 3})
    assert BankWithdrawFood(SHARK).available(state) and not BankWithdrawFood(TUNA).available(state)
    BankWithdrawFood(SHARK).run(state, RNG, 10_000)
    assert state.inventory[SHARK] == 18 and state.bank[SHARK] == 25 and SHARK_NOTE not in state.inventory


@needs_server
def test_processing_withdrawals_bank_notes_of_their_inputs_first():
    state = character({IRON_BAR_NOTE: 100, HAMMER: 1})
    assert BankWithdraw("smith_iron").available(state)
    BankWithdraw("smith_iron").run(state, RNG, 10_000)
    assert state.inventory == {HAMMER: 1, IRON_BAR: 27} and state.bank == {IRON_BAR: 73}


@needs_server
def test_magic_leaves_metal_armour_off_and_brings_back_its_runes():
    """Iron armour lowers magic attack (an iron set: -65), so a magic fight takes it off and the magic withdrawal
    leaves it banked; the runes a deposit for another task banked come back with it."""
    iron = (1153, 1115, 1067, 1191)  # full helm, platebody, platelegs, kiteshield
    worn = character({}, defence=10)
    for item in iron:
        worn.add(item)
    wield_best(worn, "melee")
    assert set(worn.equipment.values()) >= set(iron)
    wield_best(worn, "magic")
    assert not set(worn.equipment.values()) & set(iron) and all(worn.inventory.get(i) == 1 for i in iron)
    banked = character({}, {**dict.fromkeys(iron, 1), AIR: 50, 558: 40, STAFF_OF_AIR: 1}, defence=10)
    assert gear_to_withdraw(banked, "magic") == [STAFF_OF_AIR, AIR, 558]
    assert set(gear_to_withdraw(banked, "melee")) == {*iron, STAFF_OF_AIR}  # the staff is its best melee weapon
    BankWithdrawGear("magic").run(banked, RNG, 10_000)
    assert banked.inventory == {STAFF_OF_AIR: 1, AIR: 50, 558: 40}


@needs_server
def test_processing_withdrawals_take_only_inputs_the_level_allows():
    logs, oak, willow = 1511, 1521, 1519
    state = character({590: 1}, {logs: 5, oak: 5, willow: 5}, firemaking=15)
    BankWithdraw("burn_logs").run(state, RNG, 10_000)
    assert state.inventory == {590: 1, oak: 5, logs: 5} and state.bank == {willow: 5}  # willows need Firemaking 30
    raw_lobster = 377
    cook = character({590: 1}, {raw_lobster: 5}, cooking=39)  # cooking also needs a tinderbox
    assert not BankWithdraw("cook_fish").available(cook)  # lobsters need Cooking 40
    cook.xp[SKILL_INDEX["cooking"]] = float(XP_FOR_LEVEL[40])
    assert BankWithdraw("cook_fish").available(cook)


@needs_server
def test_general_store_overstock_carries_over_between_sales():
    logs = 1511  # no general store stocks logs: they go to the player stock every general store shares
    state = character({logs: 5})
    SellStore(logs).run(state, RNG, 10_000)
    first = state.inventory.pop(COINS)
    assert first == store_sale_value(logs, 5)
    state.inventory[logs] = 5
    SellStore(logs).run(state, RNG, 10_000)
    assert state.inventory[COINS] == store_sale_value(logs, 5, already_overstocked=5) <= first


@needs_server
def test_bought_mithril_bars_can_be_smithed():
    mithril_bar, dagger = 2359, 1209  # Smithing 50 makes only the dagger
    state = character({COINS: 10**7, HAMMER: 1}, smithing=50)
    BuyGE(mithril_bar).run(state, RNG, 10_000)
    assert state.inventory[gd.noted_ids()[mithril_bar]] == 1_000
    BankWithdraw("smith_mithril").run(state, RNG, 10_000)
    assert state.inventory[mithril_bar] == 26 and state.bank[mithril_bar] == 974  # beside the coins and the hammer
    result = Smith("smith_mithril", "MITHRIL").run(state, RNG, 10_000)
    assert result.termination == "inputs_exhausted" and state.inventory[dagger] == 26
    assert state.xp[SKILL_INDEX["smithing"]] == XP_FOR_LEVEL[50] + 26 * 50.0


@needs_server
def test_withdrawing_for_sale_takes_produce_as_banknotes_and_keeps_what_the_character_uses():
    logs, iron_ore, rune_scimitar, bronze_axe = 1511, 440, 1333, 1351
    bank = {logs: 300, iron_ore: 100, IRON_SCIMITAR: 1, rune_scimitar: 1, SHARK: 20, bronze_axe: 1, AIR: 500, COINS: 99}
    state = character({}, bank, attack=40)
    option = BankWithdrawForSale()
    assert option.available(state)
    option.run(state, RNG, 10_000)
    notes = gd.noted_ids()
    assert state.inventory == {notes[logs]: 300, notes[iron_ore]: 100, notes[IRON_SCIMITAR]: 1}  # one slot a stack
    # kept: the scimitar it would fight with, food, the tool, runes and coins
    assert state.bank == {rune_scimitar: 1, SHARK: 20, bronze_axe: 1, AIR: 500, COINS: 99}
    assert not option.available(state)
    SellGE(logs).run(state, RNG, 10_000)  # a per-item sell takes the banknotes too
    assert notes[logs] not in state.inventory and state.inventory[COINS] == 300 * gd.ge_prices_2009()[logs]


@needs_server
def test_a_buy_is_masked_when_the_banked_coins_cant_reach_the_inventory():
    mind_rune = 558
    price = gd.ge_prices_2009()[mind_rune]
    full = character({BREAD: 27, mind_rune: 1}, {COINS: price})  # the runes would stack, but the coins can't come out
    assert full.coins() >= price and not BuyGE(mind_rune).available(full)
    full.inventory = {BREAD: 26, mind_rune: 1, COINS: 1}
    assert BuyGE(mind_rune).available(full)  # the withdrawal stacks onto the coins carried
    BuyGE(mind_rune).run(full, RNG, 10_000)
    assert full.inventory[mind_rune] == 2
