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


def test_raw_fish_used_on_a_range_cooks_it(client, uid):
    """`use_item_on` (Caleb, 2026-11-07): raw shrimps on Lumbridge Castle's range (object 114; Cook's Assistant, which
    `spawn` completes), as a client's UseWithScenery packet. The server walks the character there and cooks it (one
    raw item cooks at once, CookingRewrite): the shrimps cooked or burnt, and the walk done."""
    RAW_SHRIMPS = 317
    for item in {i["id"] for i in client.state(uid)["inventory"]}:
        client.item_option(uid, item, "Drop")
    client.wait(2)
    client.debug_give(uid, RAW_SHRIMPS, 1)
    client.debug_teleport(uid, 3208, 3214, 0)  # the castle kitchen, a few steps from the range
    client.wait(2)
    out = client.use_item_on(uid, RAW_SHRIMPS, "Cooking range", ids=[114])
    assert out["id"] == 114 and out["queued"]
    client.wait(12)
    state = client.state(uid)
    assert held(client, uid, RAW_SHRIMPS) == 0 and len(state["inventory"]) == 1  # shrimps, or burnt
    with pytest.raises(Exception, match="none reachable"):
        client.use_item_on(uid, state["inventory"][0]["id"], "Furnace", radius=10)


def test_a_bar_on_an_anvil_and_raw_fish_on_a_range_open_their_interfaces_and_they_stay_open(client, uid):
    """`use_item_on`: a bronze bar on Varrock's south-east anvil, with a hammer, opens the smithing interface (300);
    two raw shrimps on Lumbridge Castle's range, cooking's how-many (chatbox 307). The bridge leaves both open for the
    next click, as it leaves the furnace's bars (311)."""
    HAMMER, BRONZE_BAR, RAW_SHRIMPS = 2347, 2349, 317
    for item, amount in ((HAMMER, 1), (BRONZE_BAR, 1), (RAW_SHRIMPS, 2)):
        client.debug_give(uid, item, amount)
    client.debug_teleport(uid, 3247, 3407, 0)
    client.wait(2)
    client.use_item_on(uid, BRONZE_BAR, "Anvil")
    client.wait(8)
    assert client.state(uid)["interface_id"] == 300
    client.wait(3)
    assert client.state(uid)["interface_id"] == 300  # still open
    client.debug_teleport(uid, 3208, 3214, 0)
    client.wait(2)
    client.use_item_on(uid, RAW_SHRIMPS, "Cooking range", ids=[114])
    client.wait(8)
    assert client.state(uid)["chatbox_id"] == 307
    client.wait(3)
    assert client.state(uid)["chatbox_id"] == 307


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


def test_a_ranger_on_a_ranged_safespot_takes_no_hits(client, uid):
    """The moss giant west of Ardougne (level 42, melee): ranged_safespots finds a tile its chase can't get next to
    and no aggressive monster reaches (Caleb, 2026-11-07, OQ-27 (d)). A ranger on it, auto-retaliate off, attacking
    only when the giant stands still where `npcs` says it holds, gains Ranged XP, takes no hits and never leaves the
    tile. (Varrock sewers' giants have no such tile: other aggressive giants reach every one until aggression runs
    out.)"""
    shortbow, leather, bronze_arrow = 841, 1129, 882
    client.debug_set_levels(uid, {"ranged": 60, "hitpoints": 60})
    client.set_retaliate(uid, False)
    for item, amount in ((shortbow, 1), (leather, 1), (bronze_arrow, 500)):
        client.debug_give(uid, item, amount)
    client.wait(1)
    for item, option in ((shortbow, "Wield"), (leather, "Wear"), (bronze_arrow, "Wield")):
        client.item_option(uid, item, option)
        client.wait(1)
    client.debug_teleport(uid, 2825, 3249, 0)
    client.wait(1)
    spots = client.ranged_safespots(uid, "Moss giant", ids=[112], limit=1)["tiles"]
    assert spots and not spots[0]["threats"], "no unthreatened safespot at the moss giant"
    tile = (spots[0]["tile"]["x"], spots[0]["tile"]["y"])
    held_by = {a["index"] for a in spots[0]["against"]}
    client.debug_teleport(uid, *tile, 0)
    client.wait(2)
    start = client.state(uid)
    xp = lambda s: next(k["xp"] for k in s["skills"] if k["name"].lower() == "ranged")  # noqa: E731
    lowest, off = start["hitpoints"], 0
    for t in range(400):
        s = client.state(uid)
        lowest = min(lowest, s["hitpoints"])
        off += (s["location"]["x"], s["location"]["y"]) != tile
        if s["target"] is None and not s["moving"] and t % 2 == 0:
            ready = [n for n in client.npcs(uid, "Moss giant", ids=[112], radius=20) if n["index"] in held_by
                     and n["holds"] and (n["attacking_me"] or not (n["fighting"] or n["moving"]))]
            if ready:
                client.interact(uid, "Moss giant", "Attack", is_object=False, index=ready[0]["index"])
        client.wait(1)
    assert xp(client.state(uid)) > xp(start)
    assert lowest == start["hitpoints"] and off == 0


def _tick(client: BridgeClient, uid: int, *cmds: dict) -> dict:
    return client.schedule([[*cmds, {"cmd": "state", "uid": uid}]])[0]["results"][-1]["state"]


def test_a_bank_opens_deposits_and_withdraws_through_the_players_clicks(client, uid):
    """Draynor's bank, as a client clicks it: the booth, the deposit button and its "Deposit Inventory" option, and
    a bank slot's "Withdraw All". The bank stays open between the clicks (only messages are dismissed)."""
    client.debug_teleport(uid, 3094, 3243, 0)
    client.wait(2)
    _tick(client, uid, {"cmd": "interact", "uid": uid, "name": "Bank booth", "option": "Use-quickly", "object": True,
                        "ids": [2213], "packet": True})
    # the booth opens the bank a tick or two after the click (one more when the server is loaded, as under the full
    # suite in parallel); then it stays open
    states = [_tick(client, uid)]
    while states[-1]["interface"] != 762 and len(states) < 6:
        states.append(_tick(client, uid))
    states.append(_tick(client, uid))
    assert [s["interface"] for s in states[-2:]] == [762, 762]
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


def on_ground(client: BridgeClient, uid: int, item: int) -> list[dict]:
    return [i for i in client.ground_items(uid) if i["id"] == item]


@pytest.mark.parametrize("packet", [False, True])
def test_a_dropped_item_is_seen_on_the_ground_and_taken_back(client, uid, packet):
    """`ground_items` lists the character's own drop on its tile; `take` walks back to it and picks it up, as a
    click on the item does; with nothing left to take, it fails."""
    client.debug_give(uid, BONES, 1)
    client.item_option(uid, BONES, "Drop")
    client.wait(2)
    here = client.state(uid)["location"]
    assert [(i["location"], i["own"], i["amount"]) for i in on_ground(client, uid, BONES)] == [(here, True, 1)]
    key = on_ground(client, uid, BONES)[0]["key"]
    client.walk_to(uid, here["x"] + 3, here["y"], packet=True)
    client.wait(4)
    assert [i["key"] for i in on_ground(client, uid, BONES)] == [key]  # the same item, the same key
    assert client.request("take", uid=uid, item=BONES, packet=packet)["target"] == here
    client.wait(6)
    assert held(client, uid, BONES) == 1 and not on_ground(client, uid, BONES)
    with pytest.raises(Exception, match="none reachable"):
        client.take(uid, BONES)


def test_another_character_doesnt_see_a_drop_while_its_private(client, uid):
    """Each bridge character has its own account uid (RLPlayer), which drops are private to."""
    client.debug_give(uid, BONES, 1)
    client.item_option(uid, BONES, "Drop")
    client.wait(2)
    here = client.state(uid)["location"]
    other = client.spawn()["uid"]
    try:
        assert not [i for i in on_ground(client, other, BONES) if i["location"] == here]
        with pytest.raises(Exception, match="none reachable"):
            client.take(other, BONES)
    finally:
        client.despawn(other)


CHICKENS = (3234, 3295, 0)  # the pen north of Lumbridge's cow field


def test_a_kills_drop_is_the_killers_own_and_taken_from_its_tile(client, uid):
    """A chicken always drops bones, which only its killer sees at first; `take` by tile picks them up."""
    client.debug_set_levels(uid, {"attack": 40, "strength": 40})  # a hit or two a chicken
    client.debug_teleport(uid, *CHICKENS)
    client.wait(2)
    already = {(i["location"]["x"], i["location"]["y"]) for i in on_ground(client, uid, BONES)}
    client.interact(uid, "Chicken", "Attack", is_object=False)
    dropped = []
    for _ in range(40):
        client.wait(1)
        dropped = [i for i in on_ground(client, uid, BONES) if (i["location"]["x"], i["location"]["y"]) not in already]
        if dropped:
            break
    assert dropped and dropped[0]["own"]
    tile = (dropped[0]["location"]["x"], dropped[0]["location"]["y"])
    client.take(uid, BONES, tile=tile)
    for _ in range(10):
        client.wait(1)
        if held(client, uid, BONES):
            break
    assert held(client, uid, BONES) == 1


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


def test_the_home_teleport_waits_30_minutes_of_game_ticks():
    """The home teleport can be cast once every 3,000 ticks (the fork's cooldown, as in January 2009): cast, then
    refused with the time left, then cast again once that many ticks have passed. At 15 ms ticks that's 45 seconds."""
    from rlscape.gamedata.transports import HOME, HOME_COOLDOWN_TICKS, SPELLBOOK

    varrock, cast = (3212, 3428, 0), {"cmd": "interface_button", "interface": SPELLBOOK, "button": 0, "packet": True}

    def home(c: BridgeClient, uid: int) -> dict:
        state = _tick(c, uid, {**cast, "uid": uid})
        for _ in range(30):
            loc = state["location"]
            if max(abs(loc["x"] - HOME[0]), abs(loc["y"] - HOME[1])) <= 3:
                break
            state = _tick(c, uid)
        return state

    with BridgeClient() as c:
        c.set_tick_ms(15)
        uid = c.spawn()["uid"]
        try:
            c.debug_teleport(uid, *varrock)
            c.wait(2)
            assert c.state(uid)["home_teleport_ready_in"] == 0
            state = home(c, uid)
            assert state["location"]["y"] < 3300  # in Lumbridge
            assert HOME_COOLDOWN_TICKS - 30 <= state["home_teleport_ready_in"] <= HOME_COOLDOWN_TICKS
            c.debug_teleport(uid, *varrock)
            c.wait(2)
            state = home(c, uid)
            assert state["location"]["y"] > 3400  # still in Varrock
            assert any("You need to wait another 30 minutes to cast this spell." in m for m in state["messages"])
            c.wait(state["home_teleport_ready_in"])
            assert home(c, uid)["location"]["y"] < 3300
        finally:
            c.despawn(uid)
            c.set_tick_ms(600)


def test_the_bridge_flicks_protection_so_no_swing_lands_and_no_prayer_drains(client):
    """`flick`: each tick the bridge clicks Protect from Melee on for a swing due next tick and off after, so a lone
    hill giant (a swing every 6 ticks) never hits a Defence-1 character, and prayer points never drain (Prayer.tick
    drains only on even counts of ticks in a row with a prayer on). Without it, the giant hits (the flicking test,
    decision log 2026-10-31: 13 and 11 hits in 120 ticks)."""
    uid = client.spawn()["uid"]
    try:
        client.debug_set_levels(uid, {"prayer": 43, "hitpoints": 99, "attack": 1, "strength": 1, "defence": 1})
        client.debug_teleport(uid, 2439, 3214, 0)  # the hill giant's lone spawn (npc 117)
        client.wait(3)
        assert client.flick(uid)
        client.request("interact", uid=uid, name="Hill Giant", option="Attack", object=False, packet=True)
        client.wait(6)
        start = client.state(uid)
        steps = client.schedule([[{"cmd": "state", "uid": uid}] for _ in range(120)])
        states = [s["results"][0]["state"] for s in steps]
        assert states[-1]["target"] == "Hill Giant" or any(s["target"] for s in states)  # it fought
        assert min(s["hitpoints"] for s in states) == start["hitpoints"]  # no swing landed
        assert states[-1]["prayer_points"] == start["prayer_points"]  # none drained
        assert sum("PROTECT_FROM_MELEE" in s["prayers"] for s in states) >= 120 // 6 - 1  # on for the swings
    finally:
        client.despawn(uid)
