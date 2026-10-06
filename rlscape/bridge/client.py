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

    def spawn(self) -> dict[str, Any]:
        """Spawn a fresh level-3 character at Lumbridge; returns its state."""
        return self.request("spawn")["state"]

    def state(self, uid: int) -> dict[str, Any]:
        return self.request("state", uid=uid)["state"]

    def walk_to(self, uid: int, x: int, y: int, z: int = 0) -> None:
        self.request("walk_to", uid=uid, x=x, y=y, z=z)

    def interact(self, uid: int, name: str, option: str, is_object: bool = True) -> dict[str, Any]:
        """Use ``option`` on the nearest scenery object (or NPC, with ``is_object=False``) called ``name``."""
        return self.request("interact", uid=uid, name=name, option=option, object=is_object)

    def run_script(self, uid: int, script: str) -> None:
        """Run a bundled ``content.global.bots`` script on the character without resetting its stats."""
        self.request("run_script", uid=uid, script=script)

    def stop_script(self, uid: int) -> None:
        self.request("stop_script", uid=uid)

    def despawn(self, uid: int) -> None:
        self.request("despawn", uid=uid)
