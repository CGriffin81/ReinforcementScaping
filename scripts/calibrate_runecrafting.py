"""Measure Runecrafting's times on the server against the sim (sim v1, docs/sim-v1-skills-draft.md §5; env contract §7),
as scripts/calibrate_crafting.py does Crafting's.

The cases:
- rc_<rune>, for each of the sim's runes but chaos (its maze needs ladders the runner doesn't climb yet): a character
  with the talisman and 27 essence (rune essence where the altar takes it), three tiles south of the ruins (setup
  only). As a person does it: the talisman used on the ruins; once inside, the altar's Craft-rune; once the crafting's
  lock is over, the portal's Use. Measured: the ticks from the talisman's click to landing inside ("enter"), and from
  landing to standing outside again ("inside": the walks, the crafting and the portal).
The sim's side is the same steps from the same start: the walk to the ruins and ENTER_TICKS, and inside_ticks.
(Essence isn't mined, Caleb 2026-11-08, so the essence mine isn't measured.)

The ruins are a multi-object whose own definition is named "null" (the form a player sees is "Mysterious ruins"), so
the runner names them by id, the id `debug_nearby` finds at the ruins (setup only).

Usage, with the server running (worldprops/rl.conf, or an instance with RL_BRIDGE_PORT):
    uv run python scripts/calibrate_runecrafting.py [--runes air ...] [--runs 3]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from rlscape.bridge.client import BridgeClient, run_suffix
from rlscape.gamedata import runecrafting as rcd
from rlscape.sim.movement import timed
from rlscape.sim.runecrafting import ENTER_TICKS, RC_RUNES, inside_ticks
from rlscape.sim.state import CharacterState

REPO = Path(__file__).resolve().parents[1]
GATE = 0.2
START_OFFSET = (0, -3)  # where a run starts, from the ruins' tile
RECLICK_TICKS = 1  # a click a lock dropped is repeated the next tick (the bridge's busy flag doesn't show locks)


def tick(c: BridgeClient, uid: int, *cmds: dict) -> tuple[int, dict[str, Any]]:
    step = c.schedule([[*cmds, {"cmd": "state", "uid": uid}]])[0]
    return step["tick"], step["results"][-1]["state"]


def where(s: dict[str, Any]) -> tuple[int, int, int]:
    return s["location"]["x"], s["location"]["y"], s["location"]["z"]


def held(s: dict[str, Any], item: int) -> int:
    return sum(i["amount"] for i in s["inventory"] if i["id"] == item)


def idle(s: dict[str, Any]) -> bool:
    return not (s["busy"] or s["moving"] or s["script"] is not None)


def fresh(c: BridgeClient, uid: int, items: list[tuple[int, int]]) -> None:
    for item in {i["id"] for i in c.state(uid)["inventory"]}:
        c.item_option(uid, item, "Drop")
    c.wait(2)
    for item, amount in items:
        c.debug_give(uid, item, amount)
    c.set_run(uid, True)


def rc_run(c: BridgeClient, rune: str, budget: int = 200) -> dict[str, Any]:
    r, ruins = rcd.runes()[rune], rcd.ruins()[rune]
    essence = rcd.PURE_ESSENCE if r.pure_only else rcd.RUNE_ESSENCE
    uid = c.spawn()["uid"]
    try:
        c.debug_set_levels(uid, {"runecrafting": max(r.level, 1)})
        fresh(c, uid, [(rcd.talismans()[rune], 1), (essence, 27)])
        start = (ruins.base[0] + START_OFFSET[0], ruins.base[1] + START_OFFSET[1], ruins.base[2])
        c.debug_teleport(uid, *start)
        c.wait(3)
        nodes = c.request("debug_nearby", uid=uid, name="null", radius=6, object=True)["nodes"]
        ruin = min(nodes, key=lambda n: n["distance"])["id"]
        c.use_item_on(uid, rcd.talismans()[rune], "null", ids=[ruin])
        t0, s = tick(c, uid)
        phase, out = "enter", {}
        for _ in range(budget):
            t, s = tick(c, uid)
            if phase == "enter" and where(s)[1] > 4000:
                out["enter"], t_in, phase = t - t0, t, "altar"
                c.interact(uid, "Altar", "Craft-rune")
            elif phase == "altar" and held(s, r.item):
                out["craft"], phase = t - t_in, "lock"
            elif phase == "lock" and idle(s):
                c.interact(uid, "Portal", "Use")
                phase, clicked = "portal", t
            elif phase == "portal" and where(s)[1] < 4000:
                out["inside"], out["out_at"] = t - t_in, where(s)
                break
            elif phase == "portal" and t - clicked >= RECLICK_TICKS and idle(s):
                c.interact(uid, "Portal", "Use")  # the click came in the crafting's lock: a person clicks again
                clicked, out["reclicks"] = t, out.get("reclicks", 0) + 1
        out["runes"] = held(s, r.item)
        return out
    finally:
        c.despawn(uid)


def sim_rc(rune: str) -> dict[str, float]:
    """The sim's times for the same trip, run energy full (the runner's character runs from a full bar): the walk to
    the ruins as walks are timed (movement.timed), then ENTER_TICKS; inside_ticks for the rest."""
    walk_in = timed(CharacterState.fresh(), [(abs(START_OFFSET[1]), 0)])[0]
    return {"enter": walk_in + ENTER_TICKS, "inside": inside_ticks(rune) - ENTER_TICKS}


def ratio(server: float, sim: float) -> dict[str, Any]:
    r = sim / server if server else float("inf")
    return {"server": round(server, 2), "sim": round(sim, 2), "sim_over_server": round(r, 3),
            "within_gate": abs(r - 1) <= GATE}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runes", nargs="*", default=[r for r in RC_RUNES if r != "chaos"])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--tick-ms", type=int, default=50)
    args = parser.parse_args()
    rows: dict[str, Any] = {"rc": {}}
    with BridgeClient() as c:
        old_ms = c.set_tick_ms(args.tick_ms)
        try:
            for rune in args.runes:
                runs = [rc_run(c, rune) for _ in range(args.runs)]
                done = [r for r in runs if "inside" in r]
                server = {k: float(np.mean([r[k] for r in done])) for k in ("enter", "inside")} if done else {}
                sim = sim_rc(rune)
                rows["rc"][rune] = {"runs": runs, "compare": {k: ratio(server[k], sim[k]) for k in server}}
                print(rune, {k: (v["server"], v["sim"], v["sim_over_server"]) for k, v in rows["rc"][rune]["compare"].items()},
                      f"{len(done)}/{len(runs)} done", flush=True)
        finally:
            c.set_tick_ms(old_ms)
    out = REPO / "results" / "calibration" / f"runecrafting-{datetime.now():%Y%m%d-%H%M}{run_suffix(args.tick_ms)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(args), **rows}, indent=1, default=str))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
