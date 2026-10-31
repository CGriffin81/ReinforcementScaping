"""Live checks of the bridge's input commands: `schedule`, `item_option`, `use_item`, `dialogue_button`, and their
`packet` form, which hands the server the packet a client's click would send.

Needs the forked server running with worldprops/rl.conf; skipped when the server is down.
"""

from __future__ import annotations

import pytest

from rlscape.bridge import BridgeClient
from test_bridge_live import bridge_reachable

pytestmark = pytest.mark.skipif(not bridge_reachable(), reason="RL bridge not running on localhost")
BONES, KNIFE, LOGS, ARROW_SHAFT = 526, 946, 1511, 52
CLEAN_GUAM, SWAMP_TAR, PESTLE_AND_MORTAR = 249, 1939, 233
MAKE_1_ARROW_SHAFTS = (305, 9)  # knife on logs' four-option dialogue; DialogueInterpreter passes button - 1 on
MAKE_1_TAR = (309, 6)


@pytest.fixture
def client():
    with BridgeClient() as c:
        c.set_tick_ms(100)
        yield c
        c.set_tick_ms(600)


@pytest.fixture
def uid(client):
    state = client.spawn()
    yield state["uid"]
    client.despawn(state["uid"])


def held(client: BridgeClient, uid: int, item: int) -> int:
    return sum(stack["amount"] for stack in client.state(uid)["inventory"] if stack["id"] == item)


def test_a_schedule_runs_one_step_per_tick(client, uid):
    steps = client.schedule([[{"cmd": "ping"}, {"cmd": "debug_clocks", "uid": uid}] for _ in range(5)])
    ticks = [step["tick"] for step in steps]
    assert ticks == list(range(ticks[0], ticks[0] + 5))
    assert all(r["ok"] for step in steps for r in step["results"])
    with pytest.raises(Exception, match="can't be scheduled"):
        client.schedule([[{"cmd": "wait", "ticks": 1}]])


@pytest.mark.parametrize("packet", [False, True])
def test_burying_a_bone_through_its_item_option(client, uid, packet):
    client.debug_give(uid, BONES, 1)
    before = client.debug_clocks(uid)
    client.request("item_option", uid=uid, item=BONES, option="Bury", packet=packet)
    client.wait(4)
    assert held(client, uid, BONES) == 0
    assert client.debug_clocks(uid)["skilling"] > before["skilling"]  # BoneBuryListener delays the skilling clock


@pytest.mark.parametrize("packet", [False, True])
def test_knife_on_logs_then_make_1_arrow_shafts(client, uid, packet):
    client.debug_give(uid, KNIFE, 1)
    client.debug_give(uid, LOGS, 2)
    iface, button = MAKE_1_ARROW_SHAFTS
    client.schedule([[{"cmd": "use_item", "uid": uid, "item": KNIFE, "with": LOGS, "packet": packet},
                      {"cmd": "dialogue_button", "uid": uid, "interface": iface, "button": button, "packet": packet}]])
    client.wait(4)
    assert held(client, uid, LOGS) == 1 and held(client, uid, ARROW_SHAFT) == 15


def test_herb_on_tar_answers_its_dialogue_the_next_tick(client, uid):
    """UseWithHandler opens the tar dialogue in a 1-tick pulse, and the bridge leaves a skill dialogue open."""
    for item, amount in ((CLEAN_GUAM, 1), (SWAMP_TAR, 15), (PESTLE_AND_MORTAR, 1)):
        client.debug_give(uid, item, amount)
    client.debug_set_levels(uid, {"herblore": 19})
    client.debug_complete_quest(uid, "DRUIDIC_RITUAL")
    iface, button = MAKE_1_TAR
    client.schedule([[{"cmd": "use_item", "uid": uid, "item": CLEAN_GUAM, "with": SWAMP_TAR, "packet": True}],
                     [{"cmd": "dialogue_button", "uid": uid, "interface": iface, "button": button, "packet": True}]])
    client.wait(8)
    assert held(client, uid, CLEAN_GUAM) == 0 and held(client, uid, SWAMP_TAR) == 0
