"""Live check of rl.conf's world.shop_worlds (Caleb, 2026-11-09, OQ-57) on the Gem Store (shop 92, Hervi in
Keldagrim): its stock and restock stand for January 2009's 87 members' worlds, on one server and one world, and each
unit costs what it would at one world's full stock. Needs the forked server running with worldprops/rl.conf (or an
instance made from it); skipped when the server is down.
"""

from __future__ import annotations

import pytest

from rlscape.bridge import BridgeClient
from rlscape.gamedata import server as gd
from test_bridge_live import bridge_reachable

pytestmark = pytest.mark.skipif(not bridge_reachable(), reason="RL bridge not running on localhost")

COINS, UNCUT_SAPPHIRE = 995, 1623
SHOP_IFACE, MAIN_STOCK, BUY_10 = 620, 23, 4  # Shops.kt: the main stock's container, and option 4 (opcode 199)


@pytest.fixture
def client():
    with BridgeClient() as c:
        old = c.set_tick_ms(50)
        yield c
        c.set_tick_ms(old)


@pytest.fixture
def uid(client):
    state = client.spawn()
    yield state["uid"]
    client.despawn(state["uid"])


def held(state: dict, item: int) -> int:
    return sum(i["amount"] for i in state["inventory"] if i["id"] == item)


def open_gem_store(client: BridgeClient, uid: int) -> None:
    hervi = gd.shops()[92].tile()
    client.debug_teleport(uid, hervi[0], hervi[1] - 2, hervi[2])
    client.wait(2)
    client.interact(uid, "Hervi", "Trade", is_object=False)
    for _ in range(40):
        client.wait(1)
        if client.state(uid).get("interface") == SHOP_IFACE:
            return
    raise AssertionError("the Gem Store didn't open")


def test_the_gem_store_sells_87_worlds_of_uncut_gems_at_one_worlds_price(client, uid):
    """More uncut sapphires than one world's stock of 1, as many as the inventory has room for (the starter kit and
    the coins leave 9 slots), each at its value (25 gp, one world's full stock)."""
    client.debug_give(uid, COINS, 5_000)
    open_gem_store(client, uid)
    free = 28 - len(client.state(uid)["inventory"])
    for _ in range(2):  # 20 asked for: well past one world's 1
        assert client.interface_item(uid, SHOP_IFACE, MAIN_STOCK, 0, UNCUT_SAPPHIRE, BUY_10)
        client.wait(1)
    state = client.state(uid)
    value = gd.item_base_values()[UNCUT_SAPPHIRE]
    bought = held(state, UNCUT_SAPPHIRE)
    assert bought == min(20, free) > 1 and held(state, COINS) == 5_000 - bought * value
