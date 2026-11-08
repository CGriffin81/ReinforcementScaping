"""Client for the RL bridge in the 2009Scape fork (``content/rl/RLBridge.kt``).

The bridge speaks newline-delimited JSON over a localhost TCP socket: one request object per
line, one response object per line. Every response carries ``ok`` and the server's game
``tick``; failed requests carry ``error``. Commands run on the game thread, so a response
reflects the world as of the tick that processed it.

Several servers can run at once (scripts/server_instances.py), each its own world with its own bridge port. The
environment variable RL_BRIDGE_PORT picks one for every client that doesn't name a port: the scripts and the live
tests alike.
"""

from __future__ import annotations

import json
import os
import socket
from typing import Any

BASE_PORT = 43610  # instance 1's (worldprops/rl.conf); instance n listens on BASE_PORT + n - 1
DEFAULT_PORT = int(os.environ.get("RL_BRIDGE_PORT", BASE_PORT))
CALIBRATION_TICK_MS = 50  # the tick calibration runs at, 12x real time (env contract §7; OQ-21)


def run_suffix(tick_ms: int) -> str:
    """A results file's name suffix for a run off the defaults: its tick if not calibration's ("-600ms"), and its
    server instance if not the first ("-i2"), so runs started together on several servers don't overwrite each
    other."""
    suffix = "" if tick_ms == CALIBRATION_TICK_MS else f"-{tick_ms}ms"
    return suffix + (f"-i{DEFAULT_PORT - BASE_PORT + 1}" if DEFAULT_PORT != BASE_PORT else "")


class BridgeError(RuntimeError):
    """The bridge answered a request with ``ok: false``."""


class BridgeClient:
    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float | None = None):
        self._sock = socket.create_connection((host, port), timeout=timeout)
        self._io = self._sock.makefile("rw", encoding="utf-8", newline="\n")

    def close(self) -> None:
        self._io.close()
        self._sock.close()

    def __enter__(self) -> BridgeClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def request(self, cmd: str, **fields: Any) -> dict[str, Any]:
        self._io.write(json.dumps({"cmd": cmd, **fields}) + "\n")
        self._io.flush()
        line = self._io.readline()
        if not line:
            raise ConnectionError("bridge closed the connection")
        response = json.loads(line)
        if not response.get("ok"):
            raise BridgeError(f"{cmd}: {response.get('error', 'unknown error')}")
        return response

    def ping(self) -> dict[str, Any]:
        return self.request("ping")

    def set_tick_ms(self, ms: int) -> int:
        return self.request("set_tick_ms", ms=ms)["tick_ms"]

    def wait(self, ticks: int) -> int:
        """Block until ``ticks`` game ticks have passed; returns the tick it resumed on."""
        return self.request("wait", ticks=ticks)["tick"]

    def ge_snapshot(self) -> dict[str, Any]:
        """The full GE price index (``prices``), bot stock per item (``bot_stock``) and ``open_player_offers``."""
        return self.request("ge_snapshot")

    def item_definitions(self) -> list[dict[str, Any]]:
        """Every tradeable item: id, name, unnoted_id, value, high/low alch, alchemizable, members, ge_price."""
        return self.request("item_definitions")["items"]

    def npc_definitions(self) -> list[dict[str, Any]]:
        """Every cache NPC definition: id, name, combat_level (as the client shows it), attackable, size."""
        return self.request("npc_definitions")["npcs"]

    def ge_offer(self, uid: int, item: int, amount: int, price: int, sell: bool = False) -> int:
        """Place a GE offer through the human path (the character must be at the GE); returns its slot."""
        return self.request("ge_offer", uid=uid, item=item, amount=amount, price=price, sell=sell)["slot"]

    def ge_status(self, uid: int) -> list[dict[str, Any]]:
        return self.request("ge_status", uid=uid)["slots"]

    def ge_collect(self, uid: int) -> list[dict[str, Any]]:
        return self.request("ge_collect", uid=uid)["slots"]

    def debug_teleport(self, uid: int, x: int, y: int, z: int = 0) -> None:
        """Setup only (tests, calibration). Breaks game rules; never exposed to the agent."""
        self.request("debug_teleport", uid=uid, x=x, y=y, z=z)

    def debug_give(self, uid: int, item: int, amount: int) -> None:
        """Setup only (tests, calibration). Breaks game rules; never exposed to the agent."""
        self.request("debug_give", uid=uid, item=item, amount=amount)

    def spawn(self) -> dict[str, Any]:
        """Spawn a fresh level-3 character at Lumbridge, with every quest the server has complete (flags only); returns
        its state."""
        return self.request("spawn")["state"]

    def quests(self, uid: int) -> dict[str, Any]:
        """The quest tab: ``complete`` (Quests enum names), ``points`` and ``available`` (the most there are)."""
        return self.request("quests", uid=uid)

    def state(self, uid: int) -> dict[str, Any]:
        return self.request("state", uid=uid)["state"]

    def walk_to(self, uid: int, x: int, y: int, z: int = 0, packet: bool = False) -> None:
        """Start walking. With ``packet``, as a client's walk click: it clears what the character was doing and goes at
        most MAX_PATHFIND_DISTANCE - 1 tiles toward (x, y). Without, the bundled bots' walk, which doesn't."""
        self.request("walk_to", uid=uid, x=x, y=y, z=z, packet=packet)

    def set_run(self, uid: int, on: bool = True) -> bool:
        """Turn run on or off, as the run orb does; returns whether it's on. The server turns it off when run energy
        drops under 1%."""
        return self.request("set_run", uid=uid, on=on)["run"]

    def safespots(self, uid: int, name: str, ids: list[int] | None = None, radius: int | None = None,
                  object: bool = True) -> list[dict[str, Any]]:
        """Tiles beside scenery (or, ``object=False``, NPCs such as fishing spots) called ``name`` (of ``ids``, within
        ``radius``) that the character can walk to and no aggressive melee monster that would pick it can hit it on,
        nearest first."""
        fields: dict[str, Any] = {"uid": uid, "name": name, "object": object}
        if ids is not None:
            fields["ids"] = ids
        if radius is not None:
            fields["radius"] = radius
        return self.request("safespots", **fields)["tiles"]

    def ranged_safespots(self, uid: int, name: str, ids: list[int] | None = None, radius: float | None = None,
                         range: int | None = None, limit: int | None = None,
                         at: tuple[int, int, int] | None = None) -> dict[str, Any]:
        """Where to shoot a melee monster called ``name`` (of ``ids``, spawned within ``radius``) from that it can't
        hit back from, as rangers safespot: ``tiles``, best first, each with the monsters it holds against
        (``against``: index, spawn, where it gets stuck chasing, the chase's steps, the walk to its arrows, and the
        aggressive monsters whose leash covers them). ``range`` is the attack style's (7, or 9 long-ranged); ``melee``
        is false, with no tiles, for a monster that casts or shoots. ``at`` centres the search on a site's tile
        instead of the character's (so it can ask from its safespot, not among the monsters)."""
        fields: dict[str, Any] = {"uid": uid, "name": name}
        for key, value in (("ids", ids), ("radius", radius), ("range", range), ("limit", limit)):
            if value is not None:
                fields[key] = value
        if at is not None:
            fields["at"] = {"x": at[0], "y": at[1], "z": at[2]}
        return self.request("ranged_safespots", **fields)

    def npcs(self, uid: int, name: str, ids: list[int] | None = None, radius: int | None = None,
             range: int | None = None) -> list[dict[str, Any]]:
        """The NPCs called ``name`` (of ``ids``, within ``radius``) the character sees, nearest first: index, id,
        location, whether each is fighting (``attacking_me``: the character), and ``holds``: whether, shot from where
        the character stands with ``range``, it would stay stuck in shot chasing it (as ranged_safespots has it)."""
        fields: dict[str, Any] = {"uid": uid, "name": name, "object": False}
        for key, value in (("ids", ids), ("radius", radius), ("range", range)):
            if value is not None:
                fields[key] = value
        return self.request("npcs", **fields)["npcs"]

    def set_retaliate(self, uid: int, on: bool = True) -> bool:
        """Turn auto-retaliate on or off, as the options tab's button does; off, the character doesn't fight back when
        attacked."""
        return self.request("set_retaliate", uid=uid, on=on)["retaliate"]

    def interact(self, uid: int, name: str, option: str, is_object: bool = True, ids: list[int] | None = None,
                 radius: int | None = None, index: int | None = None) -> dict[str, Any]:
        """Use ``option`` on the scenery object (or NPC, with ``is_object=False``) called ``name`` (and, with ``ids``, of
        those ids) that the character can walk to soonest; raises BridgeError ("none reachable") if it can reach
        none within ``radius`` tiles (default the server's MAX_PATHFIND_DISTANCE). With ``index``, the NPC with that
        index (e.g. one of ``state()["attackers"]``)."""
        fields: dict[str, Any] = {"uid": uid, "name": name, "option": option, "object": is_object}
        if index is not None:
            fields["index"] = index
        if ids is not None:
            fields["ids"] = ids
        if radius is not None:
            fields["radius"] = radius
        return self.request("interact", **fields)

    def ground_items(self, uid: int, radius: int | None = None) -> list[dict[str, Any]]:
        """The items on the ground the character can see within ``radius`` tiles (default the server's
        MAX_PATHFIND_DISTANCE), nearest first: its own drops (``own``, which no one else sees yet) and the public
        ones, each with ``id``, ``name``, ``amount`` and ``location``."""
        fields: dict[str, Any] = {"uid": uid}
        if radius is not None:
            fields["radius"] = radius
        return self.request("ground_items", **fields)["items"]

    def take(self, uid: int, item: int, tile: tuple[int, int] | None = None, radius: int | None = None) -> dict[str, Any]:
        """Click "Take" on a ground item of id ``item`` the character can see: the one on ``tile`` (x, y), or else the
        one it can walk to soonest within ``radius``; raises BridgeError ("none reachable") if there's none. The
        character walks to it and picks it up as a click would; poll ``state`` for the inventory."""
        fields: dict[str, Any] = {"uid": uid, "item": item}
        if tile is not None:
            fields["x"], fields["y"] = tile
        if radius is not None:
            fields["radius"] = radius
        return self.request("take", **fields)

    def item_option(self, uid: int, item: int, option: str) -> bool:
        """Click an inventory item's ``option`` ("bury", "eat"); False if the server dropped the click (locked)."""
        return self.request("item_option", uid=uid, item=item, option=option)["handled"]

    def use_item(self, uid: int, item: int, with_item: int) -> bool:
        """Use one inventory item on another; False if the server dropped it (locked)."""
        return self.request("use_item", uid=uid, item=item, **{"with": with_item})["handled"]

    def use_item_on(self, uid: int, item: int, name: str, ids: list[int] | None = None,
                    radius: int | None = None) -> dict[str, Any]:
        """Use an inventory item on the scenery called ``name`` (of ``ids``) the character can walk to soonest, as a
        client's UseWithScenery packet (raw fish on a range, a bar on an anvil); the server walks there and runs the
        use. Raises BridgeError ("none reachable") if it can reach none within ``radius`` tiles."""
        fields: dict[str, Any] = {"uid": uid, "item": item, "name": name}
        if ids is not None:
            fields["ids"] = ids
        if radius is not None:
            fields["radius"] = radius
        return self.request("use_item_on", **fields)

    def dialogue_button(self, uid: int, interface: int, button: int) -> None:
        """Click a button of the open chatbox dialogue, e.g. a skill dialogue's "Make 1"."""
        self.request("dialogue_button", uid=uid, interface=interface, button=button)

    def interface_button(self, uid: int, interface: int, button: int, option: int = 1) -> bool:
        """Click a button of an open interface (the bank's deposit button, 762/18, say) with its right-click option
        (1 to 10); False if the server dropped the click (locked)."""
        return self.request("interface_button", uid=uid, interface=interface, button=button, option=option)["handled"]

    def interface_item(self, uid: int, interface: int, child: int, slot: int, item: int, option: int) -> bool:
        """Click an item's option in an open interface's container: the bank's withdraw 1, 5, 10, X or All (762/73,
        options 1, 2, 3, 5, 6), say; False if the server dropped the click (locked)."""
        return self.request("interface_item", uid=uid, interface=interface, child=child, slot=slot, item=item,
                            option=option)["handled"]

    def prayer(self, uid: int, prayer: str) -> bool:
        """Click a prayer's button on the prayer tab (a PrayerType name, e.g. "PROTECT_FROM_MELEE"), turning it on or
        off. Returns whether it's on afterwards; it can't be toggled with no prayer points left."""
        return self.request("prayer", uid=uid, prayer=prayer)["active"]

    def flick(self, uid: int, on: bool = True) -> bool:
        """Have the bridge flick the character's protection prayers (or stop): each tick, the one against an attacker
        due to swing next tick, as prayer-tab packets, so it blocks the swing and never drains. As the sim's fights
        flick (env contract v1.8). Returns whether it's flicking."""
        return self.request("flick", uid=uid, on=on)["flicking"]

    def schedule(self, steps: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        """Run ``steps[0]`` this game tick, ``steps[1]`` the next, and so on. A step is a list of commands (dicts with
        ``cmd`` and its fields) run in order, as packets that arrive together are. Returns one ``{tick, results}`` per
        step, each result being that command's response; failures don't raise or stop the rest."""
        return self.request("schedule", steps=steps)["steps"]

    def debug_collision(self, x0: int, y0: int, x1: int, y1: int, z: int = 0,
                        objects: list[int] | None = None) -> dict[str, Any]:
        """Data export only (the travel planner's map): the area's collision flags, row by row from (x0, y0), its
        doors and gates, and the scenery of the given ids (crossings). Never exposed to the agent."""
        return self.request("debug_collision", x0=x0, y0=y0, x1=x1, y1=y1, z=z, objects=objects or [])

    def debug_set_levels(self, uid: int, levels: dict[str, int]) -> None:
        """Setup only (tests, calibration): set skills' levels, by skill name. Never exposed to the agent."""
        self.request("debug_set_levels", uid=uid, levels=levels)

    def debug_complete_quest(self, uid: int, quest: str) -> None:
        """Setup only (tests, calibration): mark a quest (Quests enum name) complete. Never exposed to the agent."""
        self.request("debug_complete_quest", uid=uid, quest=quest)

    def debug_clocks(self, uid: int) -> dict[str, Any]:
        """Measurement only (tests, calibration): the skilling clock, the active script's next execution and the
        entity delay, in game ticks, with the current ``tick``. Never exposed to the agent."""
        return self.request("debug_clocks", uid=uid)

    def run_script(self, uid: int, script: str) -> None:
        """Run a bundled ``content.global.bots`` script on the character without resetting its stats."""
        self.request("run_script", uid=uid, script=script)

    def stop_script(self, uid: int) -> None:
        self.request("stop_script", uid=uid)

    def despawn(self, uid: int) -> None:
        self.request("despawn", uid=uid)
