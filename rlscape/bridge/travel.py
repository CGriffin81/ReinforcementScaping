"""Going somewhere on the server the way the sim plans it (rlscape.sim.movement.route), as a player does it.

The route's transports are taken in order, with walks between them (rlscape.bridge.walker):
- the home teleport and spells: their spellbook button (the standard spellbook, interface 192);
- jewellery: "Rub" (it's carried), then the destination in the menu it opens;
- a tablet "Break", the seed pod "Squash" or "Launch";
- a ship: "Pay-fare" on its NPC, which before Pirate's Treasure opens its conversation: the answers a player gives
  (SHIP_ANSWERS); a charter: "Charter" on a crewmember, the destination's button on the charter interface (95), then
  "Ok" (the bridge clicks through the fare's message); off a ship's deck, "Cross" the gangplank;
- an Agility shortcut (rlscape.gamedata.shortcuts): its option on the nearest of its scenery, from its near side.
Each step waits for its effect, a tick at a time, and the trip's ticks are the game's own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from rlscape.bridge.client import BridgeClient
from rlscape.bridge.walker import chebyshev, walk_route
from rlscape.gamedata.shortcuts import LINKS
from rlscape.gamedata.transports import CHARTER_IFACE, SPELLBOOK, Transport
from rlscape.routes import Map, surface, toll_surface

ARRIVED = 3  # tiles from where a transport lands that count as having arrived
STEP_TICKS = 60  # the longest any one step may take
OPTIONS_IFACE = {2: 228, 3: 230, 4: 232, 5: 234}  # DialogueInterpreter.sendOptions: 224 + 2 x options
ITEM_OPTIONS = {"tablet": "Break"}
# The options to pick, in order, in a ship NPC's conversation (SeamanDialoguePlugin: "Yes, please."; CustomsOfficer:
# "Can I journey on this ship?", "Search away, I have nothing to hide.", "Ok.")
SHIP_ANSWERS = {"Seaman Thresnor": (1,), "Customs officer": (1, 2, 1)}
SHORTCUTS = {f"shortcut:{link.key}": link for link in LINKS}


@dataclass
class Trip:
    ticks: int = 0
    arrived: bool = False
    steps: list[tuple[str, int]] = field(default_factory=list)  # (what, its ticks)


class Stuck(Exception):
    pass


def _tick(client: BridgeClient, uid: int, *commands: dict[str, Any]) -> dict[str, Any]:
    return client.schedule([[*commands, {"cmd": "state", "uid": uid}]])[0]["results"][-1]["state"]


def _until(client: BridgeClient, uid: int, done: Callable[[dict[str, Any]], bool], what: str) -> int:
    for ticks in range(1, STEP_TICKS + 1):
        if done(_tick(client, uid)):
            return ticks
    raise Stuck(what)


def _click_npc(client: BridgeClient, uid: int, name: str, option: str) -> int:
    """Click an NPC, again each tick until the server takes it (a wandering one can be out of reach a moment)."""
    for ticks in range(1, STEP_TICKS + 1):
        step = client.schedule([[{"cmd": "interact", "uid": uid, "name": name, "option": option, "object": False,
                                  "packet": True}]])[0]
        if step["results"][0].get("ok"):
            return ticks
    raise Stuck(f"{option} on {name}")


def _here(state: dict[str, Any]) -> tuple[int, int, int]:
    loc = state["location"]
    return loc["x"], loc["y"], loc["z"]


def _near(tile: tuple[int, int, int]) -> Callable[[dict[str, Any]], bool]:
    return lambda s: chebyshev(_here(s), tile) <= ARRIVED and _here(s)[2] == tile[2]


def _held(state: dict[str, Any], items: tuple[int, ...]) -> int:
    carried = {i["id"] for i in state["inventory"]}
    return next(i for i in reversed(items) if i in carried)  # the piece closest to running out, as the sim does


def _disembark(client: BridgeClient, uid: int) -> int:
    """Cross the gangplank off the deck, clicking again until it's taken (the arrival holds the character a moment)."""
    for ticks in range(1, STEP_TICKS + 1):
        state = _tick(client, uid, {"cmd": "interact", "uid": uid, "name": "Gangplank", "option": "Cross",
                                    "object": True, "packet": True} if ticks % 3 == 1 else {"cmd": "state", "uid": uid})
        if _here(state)[2] == 0:
            return ticks
    raise Stuck("off the gangplank")


def perform(client: BridgeClient, uid: int, transport: Transport) -> int:
    """Take one transport from where the character is (a boat: next to its NPC); the ticks it took."""
    kind, uid_ = transport.kind, {"uid": uid}
    if kind in ("home", "spell"):
        _tick(client, uid, {"cmd": "interface_button", **uid_, "interface": SPELLBOOK, "button": transport.button,
                            "packet": True})
        return 1 + _until(client, uid, _near(transport.end), transport.id)
    if kind == "jewellery":
        item = _held(client.state(uid), transport.items)
        _tick(client, uid, {"cmd": "item_option", **uid_, "item": item, "option": "Rub", "packet": True})
        ticks = 1 + _until(client, uid, lambda s: s["chatbox"] in OPTIONS_IFACE.values(), "the jewellery's menu")
        chatbox = client.state(uid)["chatbox"]
        _tick(client, uid, {"cmd": "dialogue_button", **uid_, "interface": chatbox, "button": transport.button + 2,
                            "packet": True})
        return ticks + 1 + _until(client, uid, _near(transport.end), transport.id)
    if kind in ("tablet", "seed_pod"):
        option = ITEM_OPTIONS.get(kind) or transport.id.split(":")[1].capitalize()
        _tick(client, uid, {"cmd": "item_option", **uid_, "item": transport.items[0], "option": option,
                            "packet": True})
        return 1 + _until(client, uid, _near(transport.end), transport.id)
    if kind == "ship":
        ticks, answers = _click_npc(client, uid, transport.npc, "Pay-fare"), list(SHIP_ANSWERS.get(transport.npc, ()))
        arrived = _near(transport.end)
        while True:
            ticks += 1
            if ticks > STEP_TICKS:
                raise Stuck(transport.id)
            state = _tick(client, uid)
            if arrived(state):
                break
            if state["chatbox"] in OPTIONS_IFACE.values() and answers:
                _tick(client, uid, {"cmd": "dialogue_button", **uid_, "interface": state["chatbox"],
                                    "button": answers.pop(0) + 1, "packet": True})
                ticks += 1
        return ticks + (_disembark(client, uid) if transport.end[2] > 0 else 0)
    if kind == "charter":
        ticks = _click_npc(client, uid, transport.npc, "Charter")
        ticks += _until(client, uid, lambda s: s["interface"] == CHARTER_IFACE, "the charter interface")
        _tick(client, uid, {"cmd": "interface_button", **uid_, "interface": CHARTER_IFACE, "button": transport.button,
                            "packet": True})
        ticks += 1 + _until(client, uid, lambda s: s["chatbox"] == OPTIONS_IFACE[3], "the fare's Ok")
        _tick(client, uid, {"cmd": "dialogue_button", **uid_, "interface": OPTIONS_IFACE[3], "button": 2,
                            "packet": True})
        ticks += 1 + _until(client, uid, _near(transport.end), transport.id)
        return ticks + (_disembark(client, uid) if transport.end[2] > 0 else 0)
    if kind == "shortcut":
        link = SHORTCUTS[transport.id]
        _tick(client, uid, {"cmd": "interact", **uid_, "name": link.name, "option": link.option, "object": True,
                            "ids": list(link.ids), "packet": True})
        return 1 + _until(client, uid, _over(link.end), transport.id)
    raise ValueError(f"no way to take {transport.id}")


def _over(tile: tuple[int, int, int]) -> Callable[[dict[str, Any]], bool]:
    """Standing on a shortcut's far end, done with it: on the tile itself, as a stepping stone stands idle a moment
    between its one-tile jumps, and some ends are 2 tiles from the start (ARRIVED won't do)."""
    return lambda s: _here(s) == tile and not (s["busy"] or s["moving"] or s["script"] is not None)


def go(client: BridgeClient, uid: int, transports: tuple[Transport, ...], destination: tuple[int, int, int],
       pays_toll: bool = False) -> Trip:
    """Take the transports in order, walking to each boat first, then walk to `destination`; through the Al Kharid
    toll gate, paying, if the sim's route does."""
    world = toll_surface() if pays_toll else surface()
    trip = Trip()
    try:
        for transport in transports:
            if transport.start is not None:  # a boat or a shortcut: walk up to its NPC or scenery (it walks the last steps)
                walked = walk_route(client, uid, world, _short_of(world, _here(client.state(uid)), transport.start))
                trip.steps.append((f"walk to {transport.id}", walked.ticks))
                trip.ticks += walked.ticks
            ticks = perform(client, uid, transport)
            trip.steps.append((transport.id, ticks))
            trip.ticks += ticks
        walked = walk_route(client, uid, world, _standable(world, destination))  # the sim's anchor
        trip.steps.append(("walk", walked.ticks))
        trip.ticks += walked.ticks
        trip.arrived = walked.arrived
    except Stuck as stuck:
        trip.steps.append((f"stuck: {stuck}", 0))
    return trip


def _short_of(world: Map, here: tuple[int, int, int], tile: tuple[int, int, int], steps: int = 2) -> tuple[int, int, int]:
    """A tile a couple of steps short of `tile` on the way from `here`: clicking an NPC from its own tile finds no
    path to it."""
    route = world.route(here, _standable(world, tile))
    return route[max(0, len(route) - 1 - steps)] if route else _standable(world, tile)


def _standable(world: Map, tile: tuple[int, int, int]) -> tuple[int, int, int]:
    node = world.anchor(tile)
    return world.tile(node) if node is not None else tile
