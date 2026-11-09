"""Live checks of the bridge's input commands: `schedule`, `item_option`, `use_item`, `dialogue_button`, `prayer`, and
their `packet` form, which hands the server the packet a client's click would send.

Needs the forked server running with worldprops/rl.conf; skipped when the server is down.
"""

from __future__ import annotations

import pytest

from rlscape.bridge import BridgeClient
from rlscape.gamedata import server as gd
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


def test_the_runecrafting_ruins_are_found_by_the_name_a_player_sees(client, uid):
    """The ruins are a multi-object (2452 at the air ruins) whose own definition is named "null"; a player sees
    "Mysterious ruins". The bridge matches scenery by the form a player sees (RLCommands.shown, 2026-11-08), so the
    talisman used on "Mysterious ruins" lands the character inside, beside the altar."""
    from rlscape.gamedata import runecrafting as rcd
    talisman, ruins = rcd.talismans()["air"], rcd.ruins()["air"]
    client.debug_give(uid, talisman, 1)
    client.debug_teleport(uid, ruins.base[0], ruins.base[1] - 3, 0)
    client.wait(2)
    client.use_item_on(uid, talisman, "Mysterious ruins")
    for _ in range(12):
        client.wait(1)
        here = client.state(uid)["location"]
        if here["y"] > 4000:
            break
    assert (here["x"], here["y"], here["z"]) == ruins.end


def test_craftings_interfaces_and_dialogues_stay_open_for_the_next_click(client, uid):
    """The bridge leaves open what Crafting's clicks open (2026-11-08): a needle on soft leather opens the leather
    interface (154), and on hard leather the how-many (chatbox 309, LeatherCraftDialogue, not a skill dialogue); the
    spinning wheel's Spin opens 459, Ellis's Trade the tanning interface (324). Before, the bridge closed them."""
    needle, thread, soft, hard, wool, cowhide = 1733, 1734, 1741, 1743, 1737, 1739
    for item in {i["id"] for i in client.state(uid)["inventory"]}:  # the starter kit, for room
        client.item_option(uid, item, "Drop")
    client.wait(2)
    for item, amount in ((needle, 1), (thread, 5), (soft, 2), (hard, 2), (wool, 2), (cowhide, 2), (995, 1_000)):
        client.debug_give(uid, item, amount)
    client.debug_set_levels(uid, {"crafting": 30})
    client.wait(1)

    def stays(key: str, opened: int) -> None:
        for _ in range(6):
            if client.state(uid)[key] == opened:
                break
            client.wait(1)
        client.wait(3)
        assert client.state(uid)[key] == opened

    client.request("use_item", uid=uid, item=needle, **{"with": soft}, packet=True)
    stays("interface_id", 154)
    client.request("use_item", uid=uid, item=needle, **{"with": hard}, packet=True)
    stays("chatbox_id", 309)
    client.debug_teleport(uid, 3209, 3213, 1)  # beside Lumbridge Castle's wheel
    client.wait(2)
    client.interact(uid, "Spinning wheel", "Spin")
    stays("interface_id", 459)
    client.debug_teleport(uid, 3274, 3192, 0)  # beside Ellis, Al Kharid's tanner
    client.wait(2)
    client.request("interact", uid=uid, name="Ellis", option="Trade", object=False, packet=True)
    stays("interface_id", 324)


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


OGRE, OGRE_SPAWN = 3419, (2504, 2984, 0)  # data/ranged_safespots.csv: a range-7 tile that holds from all its wandering
SETTLED_READINGS = 10  # readings back on the tile before a hit counts against it (a swing in flight lands within a few)


def test_a_ranger_on_a_ranged_safespot_takes_no_hits(client, uid):
    """The ogre at (2504, 2984) (level 53, melee, aggressive): ranged_safespots finds a tile its chase can't get next
    to from anywhere its wandering leaves it, and no other aggressive monster reaches (Caleb, OQ-27 (d) and OQ-36). A
    ranger on it, auto-retaliate off, attacking only when the ogre stands still where `npcs` says it holds, gains
    Ranged XP and takes no hit while it stands there.

    The click lands a tick after the reading (the bridge serves a request a tick), and a person's does too. Now and
    then the ogre steps out of shot first and the ranger walks after it; it then clicks back onto the tile, as a person
    safespotting does (scripts/calibrate_combat.py). Until 2026-11-08 this was the moss giant at (2825, 3249), whose
    best tile holds from only 51.5% of its wandering, under OQ-36's 80%: once a ranger was dragged off it, the giant
    could reach it there, and it never walked back (a full run: 0 hitpoints of 59). (Varrock sewers' giants have no
    such tile: other aggressive giants reach every one until aggression runs out.)"""
    shortbow, leather, bronze_arrow = 841, 1129, 882
    client.debug_set_levels(uid, {"ranged": 60, "hitpoints": 60})
    client.set_retaliate(uid, False)
    for item, amount in ((shortbow, 1), (leather, 1), (bronze_arrow, 500)):
        client.debug_give(uid, item, amount)
    client.wait(1)
    for item, option in ((shortbow, "Wield"), (leather, "Wear"), (bronze_arrow, "Wield")):
        client.item_option(uid, item, option)
        client.wait(1)
    client.debug_teleport(uid, *OGRE_SPAWN)
    client.wait(1)
    spots = client.ranged_safespots(uid, "Ogre", ids=[OGRE], limit=1)["tiles"]
    assert spots and not spots[0]["threats"], "no unthreatened safespot at the ogre"
    tile = (spots[0]["tile"]["x"], spots[0]["tile"]["y"])
    held_by = {a["index"] for a in spots[0]["against"]}
    client.debug_teleport(uid, *tile, 0)
    client.wait(2)
    start = client.state(uid)
    xp = lambda s: next(k["xp"] for k in s["skills"] if k["name"].lower() == "ranged")  # noqa: E731
    hitpoints, settled, off, hits_on_tile = start["hitpoints"], 0, 0, 0
    for t in range(400):
        s = client.state(uid)
        here = (s["location"]["x"], s["location"]["y"])
        hits_on_tile += s["hitpoints"] < hitpoints and settled >= SETTLED_READINGS
        hitpoints = s["hitpoints"]
        if here != tile:
            off, settled = off + 1, 0
            client.walk_to(uid, *tile, packet=True)  # back onto it
        else:
            settled += 1
            if s["target"] is None and not s["moving"] and t % 2 == 0:
                ready = [n for n in client.npcs(uid, "Ogre", ids=[OGRE], radius=20) if n["index"] in held_by
                         and n["holds"] and (n["attacking_me"] or not (n["fighting"] or n["moving"]))]
                if ready:
                    client.interact(uid, "Ogre", "Attack", is_object=False, index=ready[0]["index"])
        client.wait(1)
    for _ in range(10):  # a walk back under way at the last reading
        end = client.state(uid)
        if (end["location"]["x"], end["location"]["y"]) == tile:
            break
        client.wait(1)
    assert xp(end) > xp(start) and (end["location"]["x"], end["location"]["y"]) == tile
    assert hits_on_tile == 0, f"hit on the tile ({off} readings off it)"


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


COWS = (3257, 3270, 0)  # Lumbridge's cow field, east of the castle
AIR_RUNE, MIND_RUNE = 556, 558


def test_a_hand_cast_is_one_spell_and_casting_again_each_tick_keeps_the_autocast_rate(client, uid):
    """`cast`, a client's spell-on-NPC packet: wind strike on a cow takes an air and a mind rune a cast and gives at
    least its 5.5 base XP. A hand cast is one spell: the combat pulse stops after it. Cast again each tick (the
    server refuses one within 3 ticks of the last), the spells land 5 ticks apart, the autocast rate the sim's magic
    fights assume (rlscape.sim.combat).

    The cow is one at its full 8 hitpoints, so wind strike (at most 2 a hit at Magic 1) takes at least 4 casts to
    kill it. A cow keeps the damage an earlier run left (it heals 1 a 100 ticks, only while someone is near), and
    one at 1 or 2 died to the first cast: the flaky `assert 1 >= 3` (2026-11-08)."""
    client.set_retaliate(uid, False)  # retaliating would swing in melee between casts
    client.debug_set_levels(uid, {"hitpoints": 99})
    client.debug_give(uid, AIR_RUNE, 100)
    client.debug_give(uid, MIND_RUNE, 100)
    client.debug_teleport(uid, *COWS)
    client.wait(2)
    spell = gd.combat_spells()["wind_strike"].button
    unhurt = [n for n in client.npcs(uid, "Cow", ids=[81]) if n["hitpoints"] == gd.npcs()[81].hitpoints]
    assert unhurt, "no cow at full hitpoints in the field"
    start = client.state(uid)
    casts, stopped, minds = [], 0, held(client, uid, MIND_RUNE)  # before the first cast, which can land at once
    index = client.cast(uid, spell, "Cow", index=unhurt[0]["index"])["index"]
    for _ in range(60):
        step = client.schedule([[{"cmd": "state", "uid": uid},
                                 {"cmd": "npcs", "uid": uid, "name": "Cow", "ids": [81], "object": False}]])[0]
        state, seen = step["results"][0]["state"], step["results"][1]["npcs"]
        now = sum(s["amount"] for s in state["inventory"] if s["id"] == MIND_RUNE)
        if now < minds:
            casts.append(step["tick"])
        minds = now
        if index not in {n["index"] for n in seen}:
            break  # killed
        if state["target"] is None:  # the pulse stopped after the spell: cast again
            stopped += 1
            client.cast(uid, spell, "Cow", index=index)
    assert len(casts) >= 3, casts
    assert stopped >= len(casts) - 1  # each spell stopped the pulse
    assert all(b - a == 5 for a, b in zip(casts, casts[1:])), casts
    client.wait(6)  # a cast sent at the last reading lands after it
    end = client.state(uid)
    runes = lambda s, rune: sum(i["amount"] for i in s["inventory"] if i["id"] == rune)
    cast = runes(start, MIND_RUNE) - runes(end, MIND_RUNE)
    assert runes(start, AIR_RUNE) - runes(end, AIR_RUNE) == cast and cast in (len(casts), len(casts) + 1)
    magic = lambda s: next(k["xp"] for k in s["skills"] if k["name"].lower() == "magic")
    assert magic(end) - magic(start) >= 5.5 * cast


def test_a_spell_that_lands_counts_in_hits_landed_and_a_splash_doesnt(client, uid):
    """`hits_landed` (ImpactHandler.handleImpact; Caleb, OQ-47 (c)): every hit that lands, 0s included; a splash never
    reaches it (MagicSwingHandler.impact skips a hit of -1). Wind strike at Magic 1 on cows at their full 8 hitpoints,
    20 casts: a third of the landed hits are 0s (RandomFunction.random(2) is 0, 1 or 2), so more hits land than do
    damage, and none land beyond the casts."""
    client.set_retaliate(uid, False)
    client.debug_set_levels(uid, {"hitpoints": 99})
    client.debug_give(uid, AIR_RUNE, 100)
    client.debug_give(uid, MIND_RUNE, 100)
    client.debug_teleport(uid, *COWS)
    client.wait(2)
    spell, full = gd.combat_spells()["wind_strike"].button, gd.npcs()[81].hitpoints
    landed0, minds0 = client.state(uid)["hits_landed"], held(client, uid, MIND_RUNE)
    damaging, index, hp, casts = 0, None, None, 0
    for _ in range(300):
        step = client.schedule([[{"cmd": "state", "uid": uid},
                                 {"cmd": "npcs", "uid": uid, "name": "Cow", "ids": [81], "object": False}]])[0]
        state, seen = step["results"][0]["state"], step["results"][1]["npcs"]
        casts = minds0 - sum(s["amount"] for s in state["inventory"] if s["id"] == MIND_RUNE)
        cow = next((n for n in seen if n["index"] == index), None)
        if index is not None and cow is None:
            damaging, index = damaging + 1, None  # killed: its last hit did damage
        elif cow is not None and cow["hitpoints"] < hp:
            damaging += 1
        hp = cow["hitpoints"] if cow is not None else None
        if casts >= 20 and state["target"] is None:
            break
        if index is None:
            unhurt = [n for n in seen if n["hitpoints"] == full]
            if unhurt:
                index, hp = unhurt[0]["index"], full
                client.cast(uid, spell, "Cow", index=index)
        elif state["target"] is None:
            client.cast(uid, spell, "Cow", index=index)
    client.wait(6)  # the last spell's impact
    landed = client.state(uid)["hits_landed"] - landed0
    casts = minds0 - held(client, uid, MIND_RUNE)
    assert casts >= 20 and damaging < landed <= casts, (casts, landed, damaging)


def test_the_monsters_in_the_regions_a_human_would_see_are_live(client, uid):
    """An RL character keeps the regions in a client's view active, as a human's does (RLPlayer.update; Caleb,
    2026-11-08): from (3257, 3270), in region (50, 51), the cows across the boundary at y = 3264 walk about. Before,
    only the character's own region was active, and those cows stood frozen and couldn't be attacked."""
    client.debug_teleport(uid, *COWS)
    client.wait(2)
    here = client.state(uid)["location"]
    region = lambda n: (n["location"]["x"] >> 6, n["location"]["y"] >> 6)  # noqa: E731
    elsewhere = lambda: {n["index"]: n["location"] for n in client.npcs(uid, "Cow", ids=[81], radius=30)  # noqa: E731
                         if region(n) != (here["x"] >> 6, here["y"] >> 6)}
    before = elsewhere()
    assert before, "no cow outside the character's region"
    client.wait(60)
    after = elsewhere()
    assert any(after.get(index) not in (None, tile) for index, tile in before.items()), (before, after)


def test_the_walker_takes_the_crandor_passage_both_ways(client, uid):
    """The planned route from Karamja volcano's rim to Crandor is the passage (OQ-16 (a)): the walker's scripted
    clicks take a character with Dragon Slayer complete through the pot hole, the secret wall and the rope, and back
    by Crandor's hole."""
    from rlscape.bridge.walker import walk_route
    from rlscape.routes import surface
    client.debug_set_levels(uid, {"hitpoints": 99, "defence": 99})
    client.debug_teleport(uid, 2856, 3167, 0)
    client.wait(2)
    there = walk_route(client, uid, surface(), (2834, 3258, 0))
    assert there.arrived and there.doors >= 1, there.tiles[-3:]
    back = walk_route(client, uid, surface(), (2856, 3167, 0))
    assert back.arrived, back.tiles[-3:]


def test_the_trollheim_teleport_needs_eadgars_ruses_own_requirement_and_lands_by_the_trolls(client, uid):
    """With Eadgar's Ruse not on the server, the Trollheim teleport (the standard spellbook's button 44) asks the
    quest's own requirement: Druidic Ritual and Troll Stronghold (complete from the start) and Herblore 31. It lands
    at (2891, 3678), from where the walker reaches a mountain troll's site (Caleb, 2026-11-08)."""
    from rlscape.bridge.walker import walk_route
    from rlscape.routes import surface
    client.debug_set_levels(uid, {"magic": 61, "herblore": 30, "hitpoints": 99, "defence": 99})
    client.debug_give(uid, 554, 10)  # fire runes
    client.debug_give(uid, 563, 10)  # law runes
    client.set_retaliate(uid, False)
    client.interface_button(uid, 192, 44)
    client.wait(8)
    here = client.state(uid)["location"]
    assert (here["x"], here["y"]) != (2891, 3678)  # Herblore 30: refused
    client.debug_set_levels(uid, {"herblore": 31})
    client.interface_button(uid, 192, 44)
    for _ in range(12):
        client.wait(1)
        here = client.state(uid)["location"]
        if (here["x"], here["y"]) == (2891, 3678):
            break
    assert (here["x"], here["y"], here["z"]) == (2891, 3678, 0)
    walk = walk_route(client, uid, surface(), (2843, 3682, 0))
    assert walk.arrived, walk.tiles[-3:]


@pytest.mark.parametrize("spell,button,levels,runes,arrival", [
    ("ape_atoll", 47, {"magic": 64}, {554: 2, 555: 2, 563: 2, 1963: 1}, (2795, 2798, 1)),
    ("watchtower", 37, {"magic": 58, "agility": 25, "herblore": 14, "mining": 40, "thieving": 15}, {557: 2, 563: 2},
     (2549, 3112, 0)),
])
def test_the_teleports_of_quests_the_server_lacks_open_with_their_own_requirements(client, uid, spell, button, levels,
                                                                                   runes, arrival):
    """Monkey Madness and Watchtower aren't on the server, so their teleports ask the quests' own requirements
    (Caleb, 2026-11-08: open, as the quests are flagged complete): Ape Atoll's two quests, complete from the start;
    Watchtower's levels, refused a level short."""
    for item, amount in runes.items():
        client.debug_give(uid, item, amount * 2)
    short = {skill: (level - 1 if skill != "magic" else level) for skill, level in levels.items()}
    if spell == "watchtower":
        client.debug_set_levels(uid, short)
        client.interface_button(uid, 192, button)
        client.wait(8)
        here = client.state(uid)["location"]
        assert (here["x"], here["y"]) != arrival[:2]  # a level short: refused
    client.debug_set_levels(uid, levels)
    client.interface_button(uid, 192, button)
    for _ in range(12):
        client.wait(1)
        here = client.state(uid)["location"]
        if (here["x"], here["y"], here["z"]) == arrival:
            break
    assert (here["x"], here["y"], here["z"]) == arrival


def test_the_barcrawl_and_enter_the_abyss_are_complete_from_the_start(client, uid):
    """Two miniquests are flagged complete at spawn (Caleb, 2026-11-08, OQ-2): the Barcrawl, so the Barbarian Outpost
    course's gate lets the character through (BarbarianOutpostCourse), and Enter the Abyss, so the Mage of Zamorak in
    the Wilderness shows the form with Teleport (2257's 2259) and sends the character to the Abyss's outer ring,
    draining its prayer. The bridge finds the mage by the name a player sees (its own definition is "null")."""
    client.debug_teleport(uid, 2546, 3569)
    client.wait(2)
    client.interact(uid, "Gate", "Open", ids=[2115, 2116], radius=4)
    client.wait(10)
    assert client.state(uid)["location"]["x"] == 2545  # through the gate, not stopped by the guard's dialogue
    # the Abyss's monsters are aggressive: at 10 hitpoints a landing beside them can kill a new character before the
    # check (it failed now and then that way), so it arrives with 99
    client.debug_set_levels(uid, {"hitpoints": 99})
    client.debug_teleport(uid, 3103, 3554)
    client.wait(2)
    client.interact(uid, "Mage of Zamorak", "Teleport", is_object=False, radius=8)
    client.wait(12)
    state = client.state(uid)
    x, y = state["location"]["x"] - 3039, state["location"]["y"] - 4832  # AbyssLoc.origin
    assert 20 <= (x * x + y * y) ** 0.5 <= 27 and state["prayer_points"] == 0


def test_a_death_sends_the_character_to_lumbridges_home_tile(client, uid):
    """DeathTask sends the dead to their spawn location, a human's being the home location (rl.conf: 3222, 3218),
    where the sim respawns a character (rlscape.sim.combat.RESPAWN). AIPlayer had set the tile the character was made
    on (3233, 3230); the fork sets the home location (RLPlayer.init). The death: a new character left in the Abyss,
    whose monsters are aggressive."""
    client.debug_teleport(uid, 3103, 3554)
    client.wait(2)
    client.interact(uid, "Mage of Zamorak", "Teleport", is_object=False, radius=8)
    client.wait(6)
    for _ in range(200):
        state = client.state(uid)
        if abs(state["location"]["x"] - 3039) > 100:
            break
        client.wait(5)
    assert any("you are dead" in m for m in state["messages"])
    assert (state["location"]["x"], state["location"]["y"], state["location"]["z"]) == (3222, 3218, 0)


def test_barbarian_fishing_needs_no_miniquest_and_trains_agility_and_strength(client, uid):
    """Barbarian fishing (BarbFishingPulse) needs Fishing 48, Agility 15, Strength 15, a barbarian rod and bait, and
    no miniquest. A leaping trout gives 50 Fishing XP and 5 Agility and Strength."""
    client.debug_set_levels(uid, {"fishing": 48, "agility": 15, "strength": 15})
    client.debug_give(uid, 11323, 1)
    client.debug_give(uid, 314, 50)  # feathers
    client.debug_teleport(uid, 2502, 3500)
    client.wait(2)
    before = {s["name"]: s["xp"] for s in client.state(uid)["skills"]}
    client.interact(uid, "Fishing spot", "Use-rod", is_object=False, ids=[2722], radius=20)
    client.wait(200)
    after = {s["name"]: s["xp"] for s in client.state(uid)["skills"]}
    trout = held(client, uid, 11328)
    assert trout > 0
    assert after["Fishing"] - before["Fishing"] == 50 * trout
    assert after["Agility"] - before["Agility"] == after["Strength"] - before["Strength"] == 5 * trout
