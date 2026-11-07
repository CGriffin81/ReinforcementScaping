"""Calibrate the processing options against the server (ROADMAP week 2; env contract §7), as scripts/calibrate.py does
gathering: the activity alone, from the same start on the live server and in the sim, against the ±20% gate.

The cases (rlscape.sim.processing): burying bones, burning logs, smelting (bronze, iron, steel) at the Lumbridge
furnace (Edgeville's needs the Varrock Diary), smithing (bronze to mithril) at Varrock's south-east anvil, and cooking fish on Lumbridge Castle's range, at
each band of `--bands` the option's level allows. The character, per env contract §7: the trainable skills at the
band, the starter kit dropped, and a full inventory of the option's inputs and its tool (setup only, debug_give).

A server run: debug_teleport to the start (setup only), then as a person does it, a tick at a time: when the
character is idle (no pulse or script running, not walking, no interface open), start the next batch: "Bury" a bone,
a tinderbox on a log, "Smelt" at the furnace then "Smelt 10" of the bar, a bar on the anvil (use_item_on) then the
item's "Make All", raw fish on the range then "Cook All". Stop when the inputs run out or the budget does. Measured:
the ticks, the skill's XP, the products.

The sim runs its option from the same state (the same start; its own walk to the station).

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/calibrate_processing.py [--options bury_bones ...] [--bands 1 31 61 91] [--runs 3]
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from rlscape.bridge.client import BridgeClient, run_suffix
from rlscape.gamedata import server as gd
from rlscape.sim.processing import HAMMER, TINDERBOX, Smith, processing_options
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

REPO = Path(__file__).resolve().parents[1]
GATE = 0.2
TICKS_PER_HOUR = 6000
TRAINABLE = ("attack", "strength", "defence", "hitpoints", "ranged", "magic", "prayer", "smithing", "cooking",
             "firemaking", "fletching")
BONES, COPPER, TIN, IRON_ORE, COAL = 526, 436, 438, 440, 453
LOGS = {1: 1511, 31: 1519, 61: 1515, 91: 1513}  # the best log the band burns: normal, willow, yew, magic
RAW_FISH = {1: 317, 31: 335, 61: 377, 91: 383}  # shrimps, trout, lobster, shark
BARS = {"smith_bronze": 2349, "smith_iron": 2351, "smith_steel": 2353, "smith_mithril": 2359}
ORES = {"smelt_bronze": ((COPPER, 14), (TIN, 14)), "smelt_iron": ((IRON_ORE, 28),),
        "smelt_steel": ((IRON_ORE, 9), (COAL, 18))}
PER_BAR = {"smelt_bronze": ((COPPER, 1), (TIN, 1)), "smelt_iron": ((IRON_ORE, 1),),
           "smelt_steel": ((IRON_ORE, 1), (COAL, 2))}  # smelting.Bar
SMELT_10 = {"smelt_bronze": 14, "smelt_iron": 22, "smelt_steel": 30}  # SmeltingInterface's "Smelt 10" buttons
SMELTING_IFACE, SMITHING_IFACE, COOKING_DIALOGUE, COOK_ALL = 311, 300, 307, 3  # 3: the bridge passes 2, "All"
# firemaking starts each run on its own clear row (the east ends of 30-tile rows, from the server's collision flags),
# in the fields between Rimmington and Falador: a run's fires outlast the next run (Log.life: 180 ticks for normal logs
# to 450 for magic), and lit fires block a row. Rows by Falador's walls won't take a fire (2982, 3307; 2999, 3396; 2989,
# 3402: no fire in 1,500 ticks of trying); these were each checked live.
FIRE_ROWS = ((2982, 3224, 0), (2990, 3264, 0), (2983, 3272, 0), (2996, 3303, 0), (2973, 3220, 0), (2973, 3271, 0),
             (2982, 3226, 0), (2991, 3414, 0))
START = {"bury_bones": (2982, 3224, 0), "burn_logs": FIRE_ROWS[0],
         "smelt": (3222, 3254, 0), "smith": (3247, 3407, 0), "cook_fish": (3208, 3214, 0)}
SKILL = {"bury_bones": "prayer", "burn_logs": "firemaking", "smelt": "smithing", "smith": "smithing",
         "cook_fish": "cooking"}
LEVEL = {"smelt_bronze": 1, "smelt_iron": 15, "smelt_steel": 30, "smith_bronze": 1, "smith_iron": 15,
         "smith_steel": 30, "smith_mithril": 50}


@dataclass(frozen=True)
class Case:
    option_id: str
    band: int

    @property
    def kind(self) -> str:
        return self.option_id.split("_")[0] if self.option_id.startswith(("smelt", "smith")) else self.option_id

    @property
    def skill(self) -> str:
        return SKILL[self.kind]


def cases(options: list[str] | None, bands: list[int]) -> list[Case]:
    ids = [o.id for o in processing_options() if not options or o.id in options]
    return [Case(i, b) for i in ids for b in bands if b >= LEVEL.get(i, 1)]


def inputs(case: Case) -> list[tuple[int, int]]:
    """The inventory each run starts with: the tool and as many inputs as fit."""
    if case.option_id == "bury_bones":
        return [(BONES, 28)]
    if case.option_id == "burn_logs":
        return [(TINDERBOX, 1), (LOGS[max(b for b in LOGS if b <= case.band)], 27)]
    if case.option_id == "cook_fish":
        return [(RAW_FISH[max(b for b in RAW_FISH if b <= case.band)], 28)]
    if case.kind == "smelt":
        return list(ORES[case.option_id])
    return [(HAMMER, 1), (BARS[case.option_id], 27)]


def character(case: Case) -> CharacterState:
    state = CharacterState.fresh()
    if case.band > 1:
        for skill in TRAINABLE:
            state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[case.band])
        state.hp = state.max_hp()
    state.inventory.clear()  # the starter kit, banked
    for item, amount in inputs(case):
        state.add(item, amount)
    state.location = START[case.kind]
    return state


def smith_buttons() -> dict[str, tuple[int, ...]]:
    """SmithingType -> its interface buttons, for 1, 5, X and All (SmithingType.forButton)."""
    text = (gd.SMITHING / "SmithingType.java").read_text(encoding="utf-8")
    return {name: tuple(int(b) for b in buttons.split(",")) for name, buttons in
            re.findall(r"^\s*(TYPE_[A-Z_]+)\([^{]*\{\s*([\d,\s]+)\}", text, re.M)}


def holding(state: dict[str, Any]) -> dict[int, int]:
    out: dict[int, int] = {}
    for stack in state["inventory"]:
        out[stack["id"]] = out.get(stack["id"], 0) + stack["amount"]
    return out


def xp(state: dict[str, Any], skill: str) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == skill)


def next_action(case: Case, state: dict[str, Any], uid: int) -> list[dict[str, Any]] | None:
    """The click a person makes now, or None when the inputs have run out."""
    held, kind = holding(state), case.kind
    if kind == "bury_bones":
        return [{"cmd": "item_option", "uid": uid, "item": BONES, "option": "Bury", "packet": True}] if held.get(BONES) \
            else None
    if kind == "burn_logs":
        log = next((i for i in LOGS.values() if held.get(i)), None)
        return None if log is None else [{"cmd": "use_item", "uid": uid, "item": TINDERBOX, "with": log,
                                          "packet": True}]
    if kind == "cook_fish":
        raw = next((i for i in RAW_FISH.values() if held.get(i)), None)
        if raw is None:
            return None
        if state.get("chatbox_id") == COOKING_DIALOGUE:
            return [{"cmd": "dialogue_button", "uid": uid, "interface": COOKING_DIALOGUE, "button": COOK_ALL,
                     "packet": True}]
        return [{"cmd": "use_item_on", "uid": uid, "item": raw, "name": "Cooking range", "ids": [114]}]
    if kind == "smelt":
        if any(held.get(item, 0) < n for item, n in PER_BAR[case.option_id]):
            return None
        if state.get("chatbox_id") == SMELTING_IFACE:
            return [{"cmd": "interface_button", "uid": uid, "interface": SMELTING_IFACE,
                     "button": SMELT_10[case.option_id], "packet": True}]
        return [{"cmd": "interact", "uid": uid, "name": "Furnace", "option": "Smelt", "object": True, "packet": True}]
    bar = BARS[case.option_id]
    smith_all = smith_all_button(case, held.get(bar, 0))
    if smith_all is None:
        return None
    if state.get("interface_id") == SMITHING_IFACE:
        return [{"cmd": "interface_button", "uid": uid, "interface": SMITHING_IFACE, "button": smith_all,
                 "packet": True}]
    return [{"cmd": "use_item_on", "uid": uid, "item": bar, "name": "Anvil"}]


def smith_all_button(case: Case, bars: int) -> int | None:
    """The "All" button of the item the sim's Smith makes next with `bars` left (its best item that fits: leftover
    bars go into the next best), or None when none fits."""
    option = next(o for o in processing_options() if o.id == case.option_id)
    assert isinstance(option, Smith)
    state = character(case)
    state.inventory[BARS[case.option_id]] = bars
    if not bars:
        del state.inventory[BARS[case.option_id]]
    best = option.best_item(state)
    return None if best is None else smith_buttons()[best.kind][3]


def server_run(client: BridgeClient, case: Case, budget: int, run: int = 0) -> dict[str, Any]:
    """One run, ending at the last XP gain once the inputs are gone: a person moves on when the last product is made
    (a pulse can wait a few ticks more, as smithing's "All" does before it finds too few bars)."""
    uid = client.spawn()["uid"]
    start = FIRE_ROWS[run % len(FIRE_ROWS)] if case.kind == "burn_logs" else START[case.kind]
    try:
        if case.band > 1:
            client.debug_set_levels(uid, {skill: case.band for skill in TRAINABLE})
        for item in {i["id"] for i in client.state(uid)["inventory"]}:
            client.item_option(uid, item, "Drop")
        client.wait(2)
        assert not client.state(uid)["inventory"], "the starter kit didn't all drop"
        for item, amount in inputs(case):
            client.debug_give(uid, item, amount)
        client.debug_teleport(uid, *start)
        client.wait(3)
        pending, first, ended, clicks, idle, last_gain, prev_xp = [], None, "completed", 0, 0, 0, None
        seen: set[str] = set(client.state(uid)["messages"])
        stepped_off = 0
        while True:
            step = client.schedule([[*pending, {"cmd": "state", "uid": uid}]])[0]
            state = step["results"][-1]["state"]
            first = first or (step["tick"], state)
            offset = step["tick"] - first[0]
            gained = xp(state, case.skill)
            if prev_xp is not None and gained > prev_xp:
                last_gain = offset
            prev_xp = gained
            if offset >= budget:
                break
            busy = state["busy"] or state["moving"] or state["script"] is not None
            idle = 0 if busy else idle + 1
            action = next_action(case, state, uid)
            if action is None and not busy:
                ended = "inputs_exhausted"
                break
            # a click when idle; an interface's button as soon as it's open
            opened = state.get("chatbox_id") in (SMELTING_IFACE, COOKING_DIALOGUE) or state.get("interface_id") == \
                SMITHING_IFACE
            pending = action if action and (opened or idle >= 1) else []
            new = [m for m in state["messages"] if m not in seen]
            seen.update(new)
            if case.kind == "burn_logs" and any("can't light a fire here" in m for m in new) and not state["moving"]:
                # left standing on its own fire (FireMakingPulse's moveStep found the way blocked, by a passing NPC,
                # say): a person steps off it and goes on lighting
                here = state["location"]
                pending = [{"cmd": "walk_to", "uid": uid, "x": here["x"] - 1, "y": here["y"], "z": here["z"],
                            "packet": True}]
                stepped_off += 1
            clicks += bool(pending)
    finally:
        client.despawn(uid)
    ticks = last_gain if ended == "inputs_exhausted" and last_gain else offset
    return {"ticks": max(ticks, 1), "ended": ended, "clicks": clicks, "until_idle": offset, "stepped_off": stepped_off,
            "xp": xp(state, case.skill) - xp(first[1], case.skill),
            "made": {str(i): n for i, n in holding(state).items() if i not in holding(first[1])}}


def sim_runs(case: Case, runs: int, budget: int) -> list[dict[str, Any]]:
    option, out = next(o for o in processing_options() if o.id == case.option_id), []
    for seed in range(runs):
        state = character(case)
        before = state.xp[SKILL_INDEX[case.skill]]
        result = option.run(state, np.random.default_rng(seed), budget)
        out.append({"ticks": max(result.ticks, 1), "ended": result.termination,
                    "xp": state.xp[SKILL_INDEX[case.skill]] - before})
    return out


def rates(runs: list[dict[str, Any]]) -> dict[str, Any]:
    ticks = sum(r["ticks"] for r in runs)
    ended: dict[str, float] = {}
    for r in runs:
        ended[r["ended"]] = ended.get(r["ended"], 0) + 1 / len(runs)
    return {"xp_per_hour": sum(r["xp"] for r in runs) * TICKS_PER_HOUR / ticks, "ticks": ticks / len(runs),
            "xp": sum(r["xp"] for r in runs) / len(runs), "runs": len(runs), "ended": ended}


def compare(server: dict[str, Any], sim: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key in ("xp_per_hour", "ticks", "xp"):
        ratio = sim[key] / server[key] if server[key] else float("inf")
        out[key] = {"server": round(server[key], 1), "sim": round(sim[key], 1), "sim_over_server": round(ratio, 3),
                    "within_gate": abs(ratio - 1) <= GATE}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--options", nargs="*", help="option ids (default: every processing option)")
    parser.add_argument("--bands", type=int, nargs="+", default=[1, 31, 61, 91])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--sim-runs", type=int, default=200)
    parser.add_argument("--budget", type=int, default=1500, help="ticks per run at most")
    parser.add_argument("--tick-ms", type=int, default=50)
    args = parser.parse_args()
    rows, runs = [], itertools.count()
    with BridgeClient() as client:
        old_ms = client.set_tick_ms(args.tick_ms)
        try:
            for case in cases(args.options, args.bands):
                server = [server_run(client, case, args.budget, next(runs)) for _ in range(args.runs)]
                s, m = rates(server), rates(sim_runs(case, args.sim_runs, args.budget))
                row = {"case": asdict(case), "server_runs": server, "server": s, "sim": m, "compare": compare(s, m)}
                rows.append(row)
                c = row["compare"]
                print(f'{case.option_id:14s} band {case.band:2d}  xp/h server {s["xp_per_hour"]:7.0f} sim '
                      f'{m["xp_per_hour"]:7.0f} ({c["xp_per_hour"]["sim_over_server"]:.2f})  ticks {s["ticks"]:6.1f} '
                      f'{m["ticks"]:6.1f} ({c["ticks"]["sim_over_server"]:.2f})  xp {s["xp"]:7.1f} {m["xp"]:7.1f}  '
                      f'ended {s["ended"]} / {m["ended"]}', flush=True)
        finally:
            client.set_tick_ms(old_ms)
    which = f"-{'+'.join(args.options)}-b{'+'.join(map(str, args.bands))}" if args.options else ""
    out = (REPO / "results" / "calibration"
           / f"processing-{datetime.now():%Y%m%d-%H%M}{which}{run_suffix(args.tick_ms)}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(args), "cases": rows}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
