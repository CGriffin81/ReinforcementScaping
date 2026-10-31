"""Client for the RL bridge in the 2009Scape fork (``content/rl/RLBridge.kt``).

The bridge speaks newline-delimited JSON over a localhost TCP socket: one request object per
line, one response object per line. Every response carries ``ok`` and the server's game
``tick``; failed requests carry ``error``. Commands run on the game thread, so a response
reflects the world as of the tick that processed it.
"""

from __future__ import annotations

import json
import socket
from typing import Any

DEFAULT_PORT = 43610


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
        """Spawn a fresh level-3 character at Lumbridge; returns its state."""
        return self.request("spawn")["state"]

    def state(self, uid: int) -> dict[str, Any]:
        return self.request("state", uid=uid)["state"]

    def walk_to(self, uid: int, x: int, y: int, z: int = 0) -> None:
        self.request("walk_to", uid=uid, x=x, y=y, z=z)

    def set_run(self, uid: int, on: bool = True) -> bool:
        """Turn run on or off, as the run orb does; returns whether it's on. The server turns it off when run energy
        drops under 1%."""
        return self.request("set_run", uid=uid, on=on)["run"]

    def interact(self, uid: int, name: str, option: str, is_object: bool = True) -> dict[str, Any]:
        """Use ``option`` on the nearest scenery object (or NPC, with ``is_object=False``) called ``name``."""
        return self.request("interact", uid=uid, name=name, option=option, object=is_object)

    def item_option(self, uid: int, item: int, option: str) -> bool:
        """Click an inventory item's ``option`` ("bury", "eat"); False if the server dropped the click (locked)."""
        return self.request("item_option", uid=uid, item=item, option=option)["handled"]

    def use_item(self, uid: int, item: int, with_item: int) -> bool:
        """Use one inventory item on another; False if the server dropped it (locked)."""
        return self.request("use_item", uid=uid, item=item, **{"with": with_item})["handled"]

    def dialogue_button(self, uid: int, interface: int, button: int) -> None:
        """Click a button of the open chatbox dialogue, e.g. a skill dialogue's "Make 1"."""
        self.request("dialogue_button", uid=uid, interface=interface, button=button)

    def schedule(self, steps: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        """Run ``steps[0]`` this game tick, ``steps[1]`` the next, and so on. A step is a list of commands (dicts with
        ``cmd`` and its fields) run in order, as packets that arrive together are. Returns one ``{tick, results}`` per
        step, each result being that command's response; failures don't raise or stop the rest."""
        return self.request("schedule", steps=steps)["steps"]

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
