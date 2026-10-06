"""Integration tests against a live forked server; skipped when the bridge isn't reachable.

Start the server first (from server/Server):
    java -jar target/server-1.0.0-jar-with-dependencies.jar worldprops/rl.conf
"""

from __future__ import annotations

import socket

import pytest

from rlscape.bridge import DEFAULT_PORT, BridgeClient, BridgeError

WOODCUTTING = 8
LOGS = 1511
TUTORIAL_EXIT = {"x": 3233, "y": 3230, "z": 0}


def bridge_reachable() -> bool:
    try:
        socket.create_connection(("127.0.0.1", DEFAULT_PORT), timeout=1).close()
        return True
    except OSError:
        return False


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


def test_spawn_matches_a_character_leaving_tutorial_island(character):
    assert character["combat_level"] == 3
    assert sum(s["level"] for s in character["skills"]) == 33
    assert character["location"] == TUTORIAL_EXIT
    assert character["equipment"] == []
    assert [(i["id"], i["amount"]) for i in character["bank"]] == [(995, 25)]
    assert len(character["inventory"]) == 18


def test_unknown_uid_is_rejected(client):
    with pytest.raises(BridgeError, match="not a bridge-controlled character"):
        client.state(999_999)


def test_wait_advances_the_requested_ticks(client):
    start = client.wait(0)
    assert client.wait(20) - start >= 20


def test_woodcutting_xp_is_not_capped(client, character):
    """Regression: without the tutorial-complete flag the server caps every skill at 175 xp."""
    uid = character["uid"]
    start = client.wait(0)
    state = character
    while sum(i["amount"] for i in state["inventory"] if i["id"] == LOGS) < 8:
        assert client.wait(0) - start < 2000, "chopping made no progress"
        if not state["busy"] and not state["moving"]:
            client.interact(uid, "Tree", "Chop down")
        client.wait(10)
        state = client.state(uid)
    logs = sum(i["amount"] for i in state["inventory"] if i["id"] == LOGS)
    xp = next(s["xp"] for s in state["skills"] if s["id"] == WOODCUTTING)
    assert xp == pytest.approx(25.0 * logs)
    assert xp > 175
