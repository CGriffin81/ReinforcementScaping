"""Integration tests for the RL character being treated as a human player, and for the frozen GE.

Needs the forked server running with worldprops/rl.conf (ge_freeze_prices = true); skipped otherwise.
"""

from __future__ import annotations

import pytest

from rlscape.bridge import BridgeClient
from test_bridge_live import bridge_reachable

COINS = 995
GE = (3165, 3489)

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


def test_ge_sell_offer_waits_because_nothing_in_this_world_buys(client, character):
    uid = character["uid"]
    client.debug_teleport(uid, *GE)
    client.wait(3)
    bronze_axe = 1351
    client.ge_offer(uid, item=bronze_axe, amount=1, price=1, sell=True)
    slots = wait_for_state(client, uid, "COMPLETED", ticks=100)
    assert slots[0]["completed"] == 0
