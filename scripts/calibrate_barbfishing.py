"""Calibrate Barbarian Fishing (sim v1, `docs/sim-v1-skills-draft.md` §3) against the server, as scripts/calibrate.py
does gathering: the activity alone, from the same start on the live server and in the sim, against the ±20% gate (env
contract §7).

A run: a calibration character at the case's Fishing, Agility and Strength (setup only, debug_set_levels), the starter
kit dropped, a barbarian rod and feathers given (debug_give), teleported to Otto's Grotto (debug_teleport). Then, as a
person fishes: "Use-rod" on the nearest fishing spot, and again only if it stops with room and bait left (the pulse
fishes a placeholder spot, so the spots' moves shouldn't stop it: counted as `reclicks`). Until the inventory is full or
the budget runs out. Measured: the ticks to the last catch, the catches by fish, the XP in each skill.

The sim runs its BarbFish from the same state (rlscape.sim.barbfishing).

Usage, with a server running (RL_BRIDGE_PORT for an instance):
    uv run python scripts/calibrate_barbfishing.py [--runs 3]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from rlscape.bridge.client import BridgeClient, BridgeError, run_suffix
from rlscape.sim.barbfishing import GROTTO, ROD, BarbFish
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

REPO = Path(__file__).resolve().parents[1]
GATE = 0.2
TICKS_PER_HOUR = 6000
FEATHER, FISH = 314, (11328, 11330, 11332)
SKILLS = ("fishing", "agility", "strength")
CASES = ((48, 15, 15), (70, 45, 45), (99, 99, 99))  # Fishing, Agility, Strength: trout only; all three fish; the top
# beside each of SpotManager's spot tiles: the spots move, and one in the water is often reachable only "near", which
# the bridge's interact doesn't take, so a run starts beside whichever spot it can click (setup only)
STANDS = ((2501, 3509, 0), (2501, 3506, 0), (2501, 3512, 0), (2505, 3497, 0), (2507, 3494, 0), (2505, 3516, 0))


def held(state: dict[str, Any]) -> dict[int, int]:
    out: dict[int, int] = {}
    for stack in state["inventory"]:
        out[stack["id"]] = out.get(stack["id"], 0) + stack["amount"]
    return out


def xp(state: dict[str, Any], skill: str) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == skill)


def server_run(client: BridgeClient, case: tuple[int, int, int], budget: int) -> dict[str, Any]:
    uid = client.spawn()["uid"]
    try:
        client.debug_set_levels(uid, dict(zip(SKILLS, case)))
        for item in {i["id"] for i in client.state(uid)["inventory"]}:
            client.item_option(uid, item, "Drop")
        client.wait(2)
        client.debug_give(uid, ROD, 1)
        client.debug_give(uid, FEATHER, 500)
        for stand in STANDS * 3:
            client.debug_teleport(uid, *stand)
            client.wait(3)
            first = client.schedule([[{"cmd": "state", "uid": uid}]])[0]
            start, s0 = first["tick"], first["results"][0]["state"]
            try:
                client.request("interact", uid=uid, name="Fishing spot", option="Use-rod", object=False, ids=[2722],
                               packet=True)
                break
            except BridgeError:
                continue
        else:
            raise RuntimeError("no fishing spot to click from any stand")
        last, reclicks, prev, idle = start, 0, 0, 0
        while True:
            step = client.schedule([[{"cmd": "state", "uid": uid}]])[0]
            s = step["results"][0]["state"]
            caught = sum(held(s).get(f, 0) for f in FISH)
            if caught > prev:
                last, prev = step["tick"], caught
            if len(s["inventory"]) >= 28 or step["tick"] - start > budget:
                break
            busy = s["busy"] or s["moving"] or s["script"] is not None
            idle = 0 if busy else idle + 1
            if idle >= 3 and step["tick"] - start > 8:  # it stopped with room and bait: as a person does, click again
                try:
                    client.request("interact", uid=uid, name="Fishing spot", option="Use-rod", object=False,
                                   ids=[2722], packet=True)
                    reclicks += 1
                except BridgeError:
                    pass
                idle = 0
    finally:
        client.despawn(uid)
    h = held(s)
    return {"ticks": last - start, "caught": {str(f): h.get(f, 0) for f in FISH}, "reclicks": reclicks,
            "xp": {k: xp(s, k) - xp(s0, k) for k in SKILLS}, "full": len(s["inventory"]) >= 28}


def sim_run(case: tuple[int, int, int], seed: int, budget: int) -> dict[str, Any]:
    state = CharacterState.fresh()
    for skill, level in zip(SKILLS, case):
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.inventory, state.location = {ROD: 1, FEATHER: 500}, GROTTO
    before = {k: state.xp[SKILL_INDEX[k]] for k in SKILLS}
    result = BarbFish().run(state, np.random.default_rng(seed), budget)
    return {"ticks": result.ticks, "caught": {str(f): state.inventory.get(f, 0) for f in FISH},
            "xp": {k: state.xp[SKILL_INDEX[k]] - before[k] for k in SKILLS}}


def per_hour(runs: list[dict[str, Any]]) -> dict[str, float]:
    ticks = sum(r["ticks"] for r in runs)
    out = {f"{k}_xp_per_hour": sum(r["xp"][k] for r in runs) * TICKS_PER_HOUR / ticks for k in SKILLS}
    out["catches_per_hour"] = sum(sum(r["caught"].values()) for r in runs) * TICKS_PER_HOUR / ticks
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--sim-runs", type=int, default=200)
    parser.add_argument("--budget", type=int, default=3000)
    parser.add_argument("--tick-ms", type=int, default=50)
    parser.add_argument("--case", type=int, nargs=3, action="append", metavar=("FISHING", "AGILITY", "STRENGTH"),
                        help="run only these levels (repeatable; default: every case in CASES)")
    args = parser.parse_args()
    rows = []
    with BridgeClient() as client:
        old_ms = client.set_tick_ms(args.tick_ms)
        try:
            for case in [tuple(c) for c in args.case] if args.case else CASES:
                server = [server_run(client, case, args.budget) for _ in range(args.runs)]
                sim = [sim_run(case, seed, args.budget) for seed in range(args.sim_runs)]
                s, m = per_hour(server), per_hour(sim)
                compare = {k: {"server": round(s[k], 1), "sim": round(m[k], 1), "sim_over_server": round(m[k] / s[k], 3),
                               "within_gate": abs(m[k] / s[k] - 1) <= GATE} for k in s if s[k]}
                rows.append({"case": dict(zip(SKILLS, case)), "server_runs": server, "server": s, "sim": m,
                             "compare": compare})
                print(f"{case}: " + "  ".join(f"{k} {v['server']:.0f}/{v['sim']:.0f} ({v['sim_over_server']:.2f})"
                                              for k, v in compare.items())
                      + f"  reclicks {[r['reclicks'] for r in server]}", flush=True)
        finally:
            client.set_tick_ms(old_ms)
    out = REPO / "results" / "calibration" / f"barbfishing-{datetime.now():%Y%m%d-%H%M}{run_suffix(args.tick_ms)}.json"
    out.write_text(json.dumps({"args": vars(args), "cases": rows}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
