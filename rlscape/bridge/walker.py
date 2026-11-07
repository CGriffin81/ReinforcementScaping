"""Walking a planned route on the server as a player clicks it (rlscape.routes; Caleb, 2026-11-01).

A long walk is a series of walk clicks (WorldspaceWalk packets, as the bridge's walk_to with packet=true sends): each
to the farthest tile of the route within HOP tiles, and the next one once the character is within AHEAD tiles of it,
so a running character doesn't stop between them. A closed door on the route is opened first (the bridge's interact,
"Open", from the tile before it), and a crossing (rlscape.routes.CROSSINGS) is crossed with its own option. If the character stops short of the end, the rest is planned again from where it
stands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rlscape.bridge.client import BridgeClient, BridgeError
from rlscape.routes import Map

HOP = 20  # tiles to the next click: within the server's MAX_PATHFIND_DISTANCE (25) and a minimap's reach
AHEAD = 3  # click the next waypoint when this close to the current one
STUCK_TICKS = 3  # not moving this long short of a waypoint (a click dropped while busy, say): plan again
MAX_TICKS = 3000
CROSSING_WAIT = 6  # ticks to let a crossing's own movement finish before clicking on (a click would cancel it)
# A crossing's (scenery name, option), by id; doors are "Open"
CROSSING_CLICKS = {23271: ("Wilderness Ditch", "Cross"), 190: ("Gate", "Open"), 1967: ("Tree Door", "Open"),
                   1968: ("Tree Door", "Open"), 35549: ("Gate", "Pay-toll(10gp)"), 35551: ("Gate", "Pay-toll(10gp)")}


def chebyshev(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


@dataclass
class Walk:
    """A walk's outcome: the ticks it took, whether it arrived, and each tick's tile."""

    ticks: int = 0
    arrived: bool = False
    clicks: int = 0
    doors: int = 0
    replans: int = 0
    tiles: list[tuple[int, int, int]] = field(default_factory=list)


def _here(state: dict[str, Any]) -> tuple[int, int, int]:
    loc = state["location"]
    return loc["x"], loc["y"], loc["z"]


def _next_waypoint(route: list[tuple[int, int, int]], at: int, world: Map,
                   opened: set[tuple[int, int]]) -> tuple[int, dict | None]:
    """From route index `at`: the index of the next click, and the door or crossing to use there first if the route
    goes through one within HOP tiles (then the click is the tile before it)."""
    j = at
    while j + 1 < len(route) and chebyshev(route[j + 1], route[at]) <= HOP:
        door = world.door_between(route[j], route[j + 1]) or world.crossing_between(route[j], route[j + 1])
        if door is not None and (door["x"], door["y"]) not in opened:
            return j, door
        j += 1
    return j, None


def walk_route(client: BridgeClient, uid: int, world: Map, goal: tuple[int, int, int],
               max_ticks: int = MAX_TICKS) -> Walk:
    """Walk the character to `goal` along the planned route, a tick at a time (the bridge's schedule)."""
    out = Walk()
    route = world.route(_here(client.state(uid)), goal)
    if route is None:
        return out
    at, waypoint, door, still = 0, None, None, 0
    opened: set[tuple[int, int]] = set()
    crossing_to, waited = None, 0  # the far side of a crossing being made
    pending: list[dict[str, Any]] = []
    while out.ticks < max_ticks:
        step = client.schedule([[*pending, {"cmd": "state", "uid": uid}]])[0]
        state, out.ticks, pending = step["results"][-1]["state"], out.ticks + 1, []
        here = _here(state)
        out.tiles.append(here)
        if here == goal:
            out.arrived = True
            break
        if crossing_to is not None:  # let the gate or ditch move the character through
            waited += 1
            if here != crossing_to and waited < CROSSING_WAIT:
                continue
            crossing_to = None
        nearest = min(range(at, len(route)), key=lambda i: (chebyshev(route[i], here), -i))
        if chebyshev(route[nearest], here) <= 1:
            at = nearest  # how far along the route the character is
        still = 0 if state["moving"] else still + 1
        if still >= STUCK_TICKS:  # stopped short: plan the rest again from here
            route = world.route(here, goal)
            if route is None:
                break
            at, waypoint, door, still = 0, None, None, 0
            opened.clear()  # a click the server dropped (the character still busy, say) is tried again
            out.replans += 1
        if door is not None:  # heading for a door or crossing: use it once there
            if chebyshev(here, route[waypoint]) <= 1 and not state["moving"]:
                name, option = CROSSING_CLICKS.get(int(door["id"]), (str(door["name"]), "Open"))
                try:
                    client.interact(uid, name, option, ids=[int(door["id"])], radius=3)
                    out.doors += 1
                    if world.crossing_between(route[waypoint], route[waypoint + 1]) is not None:
                        crossing_to, waited = route[waypoint + 1], 0
                except BridgeError:
                    pass  # it's open already (no "Open" option): walk on
                opened.add((door["x"], door["y"]))
                door, waypoint = None, None
            continue
        last = waypoint == len(route) - 1
        if waypoint is None or (not last and chebyshev(here, route[waypoint]) <= AHEAD) or (last and still >= 2):
            waypoint, door = _next_waypoint(route, at, world, opened)
            if waypoint > at or door is None:
                x, y, z = route[waypoint]
                pending = [{"cmd": "walk_to", "uid": uid, "x": x, "y": y, "z": z, "packet": True}]
                out.clicks += 1
                still = 0  # standing still counts from the click (a walk starts a tick or two after it)
    return out
