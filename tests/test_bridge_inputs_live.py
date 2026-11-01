"""Live checks of the bridge's input commands: `schedule`, `item_option`, `use_item`, `dialogue_button`, `prayer`, and
their `packet` form, which hands the server the packet a client's click would send.

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


@pytest.mark.parametrize("packet", [False, True])
def test_a_prayer_button_turns_the_prayer_on_and_off(client, uid, packet):
    client.debug_set_levels(uid, {"prayer": 43})
    for expected in (["PROTECT_FROM_MELEE"], []):
        client.request("prayer", uid=uid, prayer="PROTECT_FROM_MELEE", packet=packet)
        client.wait(1)
        assert client.state(uid)["prayers"] == expected


def test_setting_levels_refills_hitpoints_and_prayer_points(client, uid):
    client.debug_set_levels(uid, {"hitpoints": 50, "prayer": 43})
    state = client.state(uid)
    assert (state["hitpoints"], state["prayer_points"]) == (50, 43)


def test_a_prayer_on_every_other_tick_never_drains(client, uid):
    """Prayer.tick drains on every second tick in a row with a prayer on, and a tick with none on resets the count. A
    click every tick turns the prayer on and off on alternate ticks, so it never drains; left on, it drains 0.15
    points every 2 ticks (Protect from Melee, no prayer bonus)."""
    client.debug_set_levels(uid, {"prayer": 43})
    click = {"cmd": "prayer", "uid": uid, "prayer": "PROTECT_FROM_MELEE", "packet": True}
    steps = client.schedule([[click, {"cmd": "state", "uid": uid}] for _ in range(20)])
    on = [step["results"][1]["state"]["prayers"] != [] for step in steps]
    assert on == [i % 2 == 0 for i in range(1, 21)]  # each click is handled the next tick
    assert client.state(uid)["prayer_points"] == 43
    client.schedule([[click]])
    client.wait(20)
    assert client.state(uid)["prayer_points"] < 43 - 1



def nearby(client: BridgeClient, uid: int, name: str, obj: bool = True, **fields) -> list[dict]:
    return client.request("debug_nearby", uid=uid, name=name, object=obj, **fields)["nodes"]


def reachable(node: dict) -> bool:
    return node["successful"] and not node["move_near"]


def test_interact_clicks_the_reachable_target_with_the_shortest_walk(client, uid):
    """Draynor Manor's grounds have dead trees the pathfinder can't reach; interact picks among those it can."""
    client.debug_teleport(uid, 3108, 3350, 0)
    client.wait(2)
    nodes = nearby(client, uid, "Dead tree")
    assert any(not reachable(n) for n in nodes) and any(reachable(n) for n in nodes)
    target = client.request("interact", uid=uid, name="Dead tree", option="Chop down", object=True)["target"]
    chosen = next(n for n in nodes if n["location"] == target)
    assert reachable(chosen) and chosen["steps"] == min(n["steps"] for n in nodes if reachable(n))


def test_interact_can_pick_by_id_and_reports_none_reachable(client, uid):
    client.debug_teleport(uid, 3228, 3147, 0)  # Lumbridge swamp mine: rocks of several ores
    client.wait(2)
    rocks = nearby(client, uid, "Rocks")
    other = next(n["id"] for n in rocks if n["id"] != rocks[0]["id"])
    target = client.request("interact", uid=uid, name="Rocks", option="Mine", object=True, ids=[other])["target"]
    assert next(n for n in rocks if n["location"] == target)["id"] == other
    with pytest.raises(Exception, match="none reachable"):
        client.request("interact", uid=uid, name="Yew", option="Chop down", object=True)


def test_a_walk_click_clears_what_the_character_was_doing(client, uid):
    """walk_to as a client packet resets the character's scripts, as PacketProcessor does with a walk click. Netting
    shrimps keeps its script running until the inventory is full."""
    client.debug_teleport(uid, 3087, 3229, 0)  # the shore by Draynor's net spots
    client.wait(2)
    client.request("interact", uid=uid, name="Fishing spot", option="Net", object=False, packet=True)
    client.wait(6)
    assert client.debug_clocks(uid)["script_next"] is not None  # fishing
    start = client.state(uid)["location"]
    client.request("walk_to", uid=uid, x=start["x"] + 5, y=start["y"], packet=True)  # inland; the spots are west
    client.wait(4)
    assert client.debug_clocks(uid)["script_next"] is None and client.state(uid)["location"] != start


def test_auto_retaliate_turns_off_and_on(client, uid):
    assert client.state(uid)["retaliate"] is True  # the game's default
    assert client.set_retaliate(uid, False) is False and client.state(uid)["retaliate"] is False
    assert client.set_retaliate(uid, False) is False  # setting it again leaves it off
    assert client.set_retaliate(uid, True) is True


WIZARDS = (3093, 3235, 0)  # by Draynor's willows: aggressive Dark wizards (npc 4659)


def first_attacker(client: BridgeClient, uid: int, ticks: int) -> dict | None:
    for _ in range(ticks):
        attackers = client.state(uid)["attackers"]
        if attackers:
            return attackers[0]
        client.wait(1)
    return None


def test_the_state_names_who_is_attacking_and_interact_attacks_it_by_index(client, uid):
    client.set_retaliate(uid, False)  # so the character doesn't start the fight itself
    client.debug_teleport(uid, *WIZARDS)
    attacker = first_attacker(client, uid, 150)
    assert attacker is not None and attacker["name"] == "Dark wizard" and attacker["hitpoints"] > 0
    target = client.interact(uid, "Dark wizard", "Attack", is_object=False, index=attacker["index"])["target"]
    assert target == next(a for a in client.state(uid)["attackers"] if a["index"] == attacker["index"])["location"]


def test_aggression_tolerance_counts_game_ticks():
    """After 1,000 ticks in a region its monsters leave a character alone (Region.TOLERANCE_TICKS). At 15 ms ticks
    that's 15 seconds: on wall-clock time, as the server had it, it would take 10 minutes."""
    with BridgeClient() as c:
        c.set_tick_ms(15)
        settled, newcomer = c.spawn()["uid"], None
        try:
            c.set_retaliate(settled, False)
            c.debug_teleport(settled, 3120, 3250, 0)  # the wizards' map region, away from them
            c.wait(1_100)
            c.debug_teleport(settled, *WIZARDS)  # the same region, so its tolerance stands
            newcomer = c.spawn()["uid"]
            c.set_retaliate(newcomer, False)
            c.debug_teleport(newcomer, *WIZARDS)
            newcomer_attacked = settled_attacked = False
            for _ in range(300):  # wizards do attack here, but not one that has been in the region 1,000 ticks
                newcomer_attacked |= bool(c.state(newcomer)["attackers"])
                settled_attacked |= bool(c.state(settled)["attackers"])
                if newcomer_attacked:
                    break
                c.wait(1)
            assert newcomer_attacked and not settled_attacked
        finally:
            c.despawn(settled)
            if newcomer is not None:
                c.despawn(newcomer)
            c.set_tick_ms(600)


@pytest.mark.parametrize("levels", [{"woodcutting": 31}, {"attack": 31, "strength": 25, "defence": 20, "hitpoints": 30,
                                                          "prayer": 15}, {"magic": 40, "hitpoints": 20}])
def test_setting_levels_updates_the_combat_level_the_sim_computes(client, uid, levels):
    """Aggression reads the combat level (AggressiveBehavior.canSelectTarget), which debug_set_levels must update."""
    from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
    from rlscape.sim.state import CharacterState
    client.debug_set_levels(uid, levels)
    state = CharacterState.fresh()
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    assert client.state(uid)["combat_level"] == state.combat_level()


def test_safespots_beside_rocks_from_every_melee_aggressor(client, uid):
    """At Lumbridge Swamp's copper some tiles are out of every aggressive melee monster's reach; at Al Kharid's iron
    none is, for a level-3 character: five scorpions (level 14) reach every rock within their leash."""
    from rlscape.gamedata import server as gd
    client.debug_teleport(uid, 3228, 3147, 0)
    client.wait(2)
    assert client.safespots(uid, "Rocks", sorted(gd.rock_objects()[1]), 10)
    client.debug_teleport(uid, 3300, 3310, 0)
    client.wait(2)
    assert client.safespots(uid, "Rocks", sorted(gd.rock_objects()[6]), 10) == []


def _tick(client: BridgeClient, uid: int, *cmds: dict) -> dict:
    return client.schedule([[*cmds, {"cmd": "state", "uid": uid}]])[0]["results"][-1]["state"]


def test_a_bank_opens_deposits_and_withdraws_through_the_players_clicks(client, uid):
    """Draynor's bank, as a client clicks it: the booth, the deposit button and its "Deposit Inventory" option, and
    a bank slot's "Withdraw All". The bank stays open between the clicks (only messages are dismissed)."""
    client.debug_teleport(uid, 3094, 3243, 0)
    client.wait(2)
    _tick(client, uid, {"cmd": "interact", "uid": uid, "name": "Bank booth", "option": "Use-quickly", "object": True,
                        "ids": [2213], "packet": True})
    states = [_tick(client, uid) for _ in range(3)]
    assert [s["interface"] for s in states[1:]] == [762, 762]
    held_before = len(states[-1]["inventory"])
    _tick(client, uid, {"cmd": "interface_button", "uid": uid, "interface": 762, "button": 18, "packet": True})
    assert _tick(client, uid)["chatbox"] == 232  # Deposit Inventory / Worn Equipment / Beast of Burden / Cancel
    _tick(client, uid, {"cmd": "dialogue_button", "uid": uid, "interface": 232, "button": 2, "packet": True})
    state = _tick(client, uid)
    assert not state["inventory"] and len(state["bank"]) >= held_before
    coins = next(i for i, stack in enumerate(state["bank"]) if stack["id"] == 995)
    _tick(client, uid, {"cmd": "interface_item", "uid": uid, "interface": 762, "child": 73, "slot": coins,
                        "item": 995, "option": 6, "packet": True})
    assert held(client, uid, 995) == 25


def test_a_planned_route_is_walked_as_clicks(client, uid):
    """The planner's route from the spawn to Draynor's bank is what the server walks: the same number of tiles."""
    from rlscape.bridge.walker import walk_route
    from rlscape.routes import surface

    world = surface()
    start = client.state(uid)["location"]
    walk = walk_route(client, uid, world, (3092, 3245, 0))
    moved = sum(max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a, b in zip(walk.tiles, walk.tiles[1:]))
    assert walk.arrived and walk.replans == 0
    assert moved == world.steps((start["x"], start["y"], 0), (3092, 3245, 0))
