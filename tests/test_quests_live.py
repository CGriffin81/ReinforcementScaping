"""Live: a spawned character has done every quest the server has, as flags only (Caleb, 2026-11-06), and the sim
counts the same quests complete. Skipped when the bridge isn't reachable."""

from __future__ import annotations

import pytest

from rlscape.bridge import BridgeClient
from rlscape.gamedata import server as gd
from rlscape.sim.state import CharacterState
from test_bridge_live import bridge_reachable

pytestmark = pytest.mark.skipif(not bridge_reachable(), reason="RL bridge not running on localhost")

RUNE_PLATEBODY = 1127  # ItemQuestRequirementListener: Dragon Slayer
CANIFIS = (3493, 3488, 0)  # inside MorytaniaArea's borders, which throw out anyone without Priest in Peril


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


def test_spawn_completes_the_quests_the_sim_counts_with_their_points_and_no_rewards(client, character):
    quests = client.quests(character["uid"])
    assert set(quests["complete"]) == gd.implemented_quests() == CharacterState.fresh().progress.quests_complete
    assert quests["points"] == quests["available"] > 0
    assert character["combat_level"] == 3 and sum(s["level"] for s in character["skills"]) == 33  # no quest XP
    assert sum(s["xp"] for s in character["skills"]) == pytest.approx(1154)  # 10 Hitpoints' XP only
    # no quest items: the bank is 25 coins and Enter the Abyss's small pouch, the one reward given (OQ-40 (c))
    assert len(character["inventory"]) == 18 and [(i["id"], i["amount"]) for i in character["bank"]] == [(995, 25),
                                                                                                         (5509, 1)]


def test_a_quest_locked_item_can_be_worn(client, character):
    uid = character["uid"]
    client.debug_set_levels(uid, {"defence": 40})
    client.debug_give(uid, RUNE_PLATEBODY, 1)
    client.request("item_option", uid=uid, item=RUNE_PLATEBODY, option="Wear", packet=True)
    client.wait(2)
    assert RUNE_PLATEBODY in [i["id"] for i in client.state(uid)["equipment"]]


def test_morytania_lets_the_character_stay(client, character):
    uid = character["uid"]
    client.debug_teleport(uid, *CANIFIS)
    client.wait(15)
    state = client.state(uid)
    assert (state["location"]["x"], state["location"]["y"]) == CANIFIS[:2] and state["chatbox"] is None
