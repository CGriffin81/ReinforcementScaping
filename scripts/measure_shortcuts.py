"""Measure the Agility shortcuts the travel model takes (rlscape.gamedata.shortcuts: LINKS) on the server: for each
one-way link, a calibration character (Agility 99; setup only) teleported to its start clicks the shortcut as a client does
(the nearest of its ids, the handler's option) and the run times it to standing on the far end, able to walk on. Measured:
the ticks, the tile it ends on, and any Agility XP (AgilityShortcut configures XP but never gives it; some handlers
might).

Usage, with a server running (RL_BRIDGE_PORT for an instance):
    uv run python scripts/measure_shortcuts.py [--runs 3]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rlscape.bridge.client import BridgeClient, BridgeError, run_suffix
from rlscape.gamedata.shortcuts import LINKS

REPO = Path(__file__).resolve().parents[1]
BOX = 8  # tiles round a link's start to look for its scenery


def agility_xp(state: dict[str, Any]) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == "agility")


def names(client: BridgeClient, ids: tuple[int, ...], near: tuple[int, int, int]) -> dict[int, str]:
    """The shortcut objects' names, read from the server's map around `near` (setup only)."""
    found = client.debug_collision(near[0] - BOX, near[1] - BOX, near[0] + BOX, near[1] + BOX, near[2],
                                   objects=sorted(ids))
    return {o["id"]: o["name"] for o in found["objects"]}


def cross(client: BridgeClient, uid: int, start: tuple[int, int, int], end: tuple[int, int, int], ids: tuple[int, ...],
          option: str, name: str) -> dict[str, Any]:
    client.debug_teleport(uid, *start)  # setup only
    client.wait(3)
    s = client.state(uid)
    xp0 = agility_xp(s)
    step = client.schedule([[{"cmd": "interact", "uid": uid, "name": name, "option": option, "object": True,
                              "ids": list(ids), "packet": True}, {"cmd": "state", "uid": uid}]])[0]
    clicked = step["tick"]
    for _ in range(80):
        step = client.schedule([[{"cmd": "state", "uid": uid}]])[0]
        s = step["results"][0]["state"]
        here = (s["location"]["x"], s["location"]["y"], s["location"]["z"])
        idle = not (s["busy"] or s["moving"] or s["script"] is not None)
        if idle and here == end:  # on it: a stepping stone stands idle a moment between its one-tile jumps
            return {"ticks": step["tick"] - clicked, "end": here, "xp": agility_xp(s) - xp0, "crossed": True}
    return {"ticks": None, "end": here, "xp": agility_xp(s) - xp0, "crossed": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--tick-ms", type=int, default=50)
    args = parser.parse_args()
    rows = []
    with BridgeClient() as client:
        old_ms = client.set_tick_ms(args.tick_ms)
        uid = client.spawn()["uid"]
        try:
            client.debug_set_levels(uid, {"agility": 99, "hitpoints": 99})
            for link in LINKS:
                name = next(iter(names(client, link.ids, link.start).values()), None)
                if name is None:
                    print(f"{link.key}: no object {link.ids} found near {link.start}", flush=True)
                    continue
                runs = []
                for _ in range(args.runs):
                    try:
                        runs.append(cross(client, uid, link.start, link.end, link.ids, link.option, name))
                    except BridgeError as e:
                        runs.append({"error": str(e), "crossed": False})
                rows.append({"shortcut": link.key, "name": name, "level": link.level, "runs": runs})
                print(f"{link.key} ({name}, Agility {link.level}): "
                      + ", ".join(f"{r['ticks']} ticks, {r.get('xp', 0):.1f} xp" if r.get("crossed")
                                  else f"failed {r.get('error', r.get('end'))}" for r in runs), flush=True)
        finally:
            client.despawn(uid)
            client.set_tick_ms(old_ms)
    out = REPO / "results" / "calibration" / f"shortcuts-{datetime.now():%Y%m%d-%H%M}{run_suffix(args.tick_ms)}.json"
    out.write_text(json.dumps({"args": vars(args), "shortcuts": rows}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
