"""Integration tests for the RL character being treated as a human player, and for the frozen GE.

Needs the forked server running with worldprops/rl.conf (frozen prices, frozen-price buyer and seller, no random events)
and the frozen GE installed (scripts/install_ge_db.py); skipped when the server is down.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from rlscape.bridge import BridgeClient, BridgeError
from test_bridge_live import bridge_reachable

COINS = 995
ANTI_DRAGON_SHIELD = 1540
GE = (3165, 3489)
DATA = Path(__file__).resolve().parent.parent / "data"

pytestmark = pytest.mark.skipif(not bridge_reachable(), reason="RL bridge not running on localhost")


@pytest.fixture
def client():
    with BridgeClient() as c:
        c.set_tick_ms(15)
        yield c
        c.set_tick_ms(600)


@pytest.fixture
def character(client):
    state = client.spawn()
    yield state
    client.despawn(state["uid"])


def amount_of(state: dict, item_id: int) -> int:
    return sum(i["amount"] for i in state["inventory"] if i["id"] == item_id)


def wait_for_state(client: BridgeClient, uid: int, wanted: str, ticks: int = 200) -> list[dict]:
    for _ in range(ticks // 5):
        client.wait(5)
        slots = client.ge_status(uid)
        if slots and slots[0]["state"] == wanted:
            return slots
    return client.ge_status(uid)


def test_rl_character_is_human_and_can_move(client, character):
    uid = character["uid"]
    assert character["artificial"] is False
    # Regression: a human who finished the tutorial is parked on the welcome screen until Play is clicked.
    assert character["interface_open"] is False
    client.walk_to(uid, 3225, 3240)
    client.wait(15)
    assert client.state(uid)["location"] != character["location"]


def test_ge_buy_fills_from_bot_stock_at_the_frozen_price(client, character):
    uid = character["uid"]
    snapshot = client.ge_snapshot()
    prices = {p["id"]: p["value"] for p in snapshot["prices"]}
    names = {p["id"]: p["name"] for p in snapshot["prices"]}
    item, stock = max(((s["id"], s["amount"]) for s in snapshot["bot_stock"]), key=lambda s: s[1])
    assert stock >= 3, "no bot stock to buy from"
    price = prices[item]

    def held(state: dict) -> int:  # items or banknotes; a note shares the item's name
        return sum(i["amount"] for i in state["inventory"] if i["name"] == names[item])

    client.debug_teleport(uid, *GE)
    client.debug_give(uid, COINS, price * 3 + 100)
    client.wait(3)
    before = client.state(uid)

    client.ge_offer(uid, item=item, amount=3, price=price)
    slots = wait_for_state(client, uid, "COMPLETED")
    assert slots[0]["completed"] == 3
    client.ge_collect(uid)
    client.wait(1)
    after = client.state(uid)

    assert amount_of(before, COINS) - amount_of(after, COINS) == 3 * price
    assert held(after) - held(before) == 3
    assert client.ge_status(uid) == []
    frozen = {p["id"]: p["value"] for p in client.ge_snapshot()["prices"]}
    assert frozen[item] == price


def bot_stock_of(client: BridgeClient, item: int) -> int:
    return sum(s["amount"] for s in client.ge_snapshot()["bot_stock"] if s["id"] == item)


def test_ge_sell_fills_at_the_frozen_price_and_restocks_the_market(client, character):
    """rl.conf's ge_frozen_buyer takes sell offers at the frozen 2009 price, paying that price even when asked less."""
    uid = character["uid"]
    bronze_axe = 1351
    price = {p["id"]: p["value"] for p in client.ge_snapshot()["prices"]}[bronze_axe]
    stock_before = bot_stock_of(client, bronze_axe)
    client.debug_teleport(uid, *GE)
    client.wait(3)
    before = client.state(uid)

    client.ge_offer(uid, item=bronze_axe, amount=1, price=1, sell=True)
    slots = wait_for_state(client, uid, "COMPLETED")
    assert slots[0]["completed"] == 1
    client.ge_collect(uid)
    client.wait(3)
    after = client.state(uid)

    assert amount_of(after, COINS) - amount_of(before, COINS) == price
    assert amount_of(after, bronze_axe) == amount_of(before, bronze_axe) - 1
    for _ in range(20):  # the GE worker thread writes the restocked item asynchronously
        if bot_stock_of(client, bronze_axe) == stock_before + 1:
            break
        client.wait(2)
    assert bot_stock_of(client, bronze_axe) == stock_before + 1


def test_ge_sell_above_the_frozen_price_stays_open(client, character):
    uid = character["uid"]
    wooden_shield = 1171
    price = {p["id"]: p["value"] for p in client.ge_snapshot()["prices"]}[wooden_shield]
    client.debug_teleport(uid, *GE)
    client.wait(3)
    client.ge_offer(uid, item=wooden_shield, amount=1, price=price + 1, sell=True)
    slots = wait_for_state(client, uid, "COMPLETED", ticks=100)
    assert slots[0]["completed"] == 0


def test_ge_buyer_ignores_items_without_a_2009_price(client, character):
    """The buyer only takes items listed in the frozen database's historical_price_items table."""
    empty_oyster = 409
    assert empty_oyster not in historical_ids(), "precondition: no 2009 price"
    uid = character["uid"]
    price = {p["id"]: p["value"] for p in client.ge_snapshot()["prices"]}[empty_oyster]
    client.debug_teleport(uid, *GE)
    client.debug_give(uid, empty_oyster, 1)
    client.wait(3)
    client.ge_offer(uid, item=empty_oyster, amount=1, price=price, sell=True)
    slots = wait_for_state(client, uid, "COMPLETED", ticks=100)
    assert slots[0]["completed"] == 0


def historical_ids() -> set[int]:
    with (DATA / "ge_prices_2009.csv").open(newline="") as f:
        return {int(row["item_id"]) for row in csv.DictReader(f)}


def test_frozen_seller_supplies_items_bot_stock_lacks_and_refunds_overpayment(client, character):
    """rl.conf's ge_frozen_seller fills buy offers at the frozen 2009 price when bot stock has none."""
    steel_scimitar = 1325
    assert steel_scimitar in historical_ids(), "precondition: has a 2009 price"
    assert bot_stock_of(client, steel_scimitar) == 0, "precondition: bot stock has none"
    uid = character["uid"]
    price = {p["id"]: p["value"] for p in client.ge_snapshot()["prices"]}[steel_scimitar]
    client.debug_teleport(uid, *GE)
    client.debug_give(uid, COINS, price + 100)
    client.wait(3)
    before = client.state(uid)

    client.ge_offer(uid, item=steel_scimitar, amount=1, price=price + 50)
    slots = wait_for_state(client, uid, "COMPLETED")
    assert slots[0]["completed"] == 1
    client.ge_collect(uid)
    client.wait(1)
    after = client.state(uid)

    assert amount_of(after, steel_scimitar) == 1
    assert amount_of(before, COINS) - amount_of(after, COINS) == price  # offered price + 50, refunded 50


def test_frozen_seller_ignores_items_without_a_2009_price(client, character):
    # Not the Empty oyster: the buyer test leaves an unfilled sell offer for it, which a buy offer here would
    # match as an ordinary player-to-player trade. GE offers outlive the character that placed them.
    cup_of_tea = 712
    assert cup_of_tea not in historical_ids(), "precondition: no 2009 price"
    assert bot_stock_of(client, cup_of_tea) == 0, "precondition: bot stock has none"
    uid = character["uid"]
    price = {p["id"]: p["value"] for p in client.ge_snapshot()["prices"]}[cup_of_tea]
    client.debug_teleport(uid, *GE)
    client.debug_give(uid, COINS, price + 100)
    client.wait(3)
    client.ge_offer(uid, item=cup_of_tea, amount=1, price=price)
    slots = wait_for_state(client, uid, "COMPLETED", ticks=100)
    assert slots[0]["completed"] == 0


def test_anti_dragon_shield_is_not_tradeable_on_the_ge(client, character):
    """rl.conf blocks the anti-dragon shield (and its note) on the GE: it only comes from Duke Horacio."""
    uid = character["uid"]
    client.debug_teleport(uid, *GE)
    client.debug_give(uid, COINS, 1000)
    client.debug_give(uid, ANTI_DRAGON_SHIELD, 1)
    client.wait(3)
    with pytest.raises(BridgeError, match="can't be traded on the GE"):
        client.ge_offer(uid, item=ANTI_DRAGON_SHIELD, amount=1, price=500)
    with pytest.raises(BridgeError, match="can't be traded on the GE"):
        client.ge_offer(uid, item=ANTI_DRAGON_SHIELD, amount=1, price=1, sell=True)


def test_slayer_level_blocks_attacks(client, character):
    """Cave crawlers need Slayer 10 (Tasks.java). A fresh character (Slayer 1) gets the server's warning and no fight."""
    uid = character["uid"]
    client.debug_teleport(uid, 2786, 9998)  # Fremennik Slayer Dungeon, among the cave crawlers
    client.wait(2)
    client.interact(uid, "Cave crawler", "Attack", is_object=False)
    client.wait(8)
    assert client.state(uid)["target"] is None


def test_random_events_are_off_for_training(character):
    """rl.conf sets rl.random_events = false, so no AntiMacro timer is attached to the RL character."""
    assert character["random_events"] is False
