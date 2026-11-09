"""Calibrate Crafting (sim v1, `docs/sim-v1-skills-draft.md` §7) against the server, as scripts/calibrate_processing.py
does the processing options: the work alone, from a full inventory, on the live server and in the sim, against the
±20% gate (env contract §7).

The cases: cutting a gem (a chisel on it, then the make dialogue's "All"), sewing soft leather (a needle on it, then
the leather interface's "All" for the item), a hard leather body (the make dialogue's "All"), dragonhide (the
dialogue has no "All": "Make 10" again until the leather runs out), spinning at Lumbridge Castle's wheel ("Spin",
then the wheel's "All"), tanning at Ellis ("Trade", then the tanning interface's "All"), and picking flax in Seers'
Village's field ("Pick" on the nearest plant, a pick a click), at the bands the recipe's level allows. The character,
per env contract §7: Crafting at the band (the other skills too), the starter kit dropped, and a full inventory of the
inputs and the tool and thread (setup only, debug_give).

A server run: debug_teleport to the start (setup only), then as a person does it, a tick at a time: the next click
when the character is idle, an interface's button as soon as it's open. It stops when the inputs run out (flax: when
the inventory is full) or the budget does. Measured: the ticks to the last product, the Crafting XP, the products.

The sim runs its own option from the same state: `Craft` (the recipe where the character stands), `Spin` (at the
wheel), the tanner's `_work`, and `PickFlax` (picking to a full inventory).

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/calibrate_crafting.py [--cases cut_opal ...] [--bands 1 31 61 91] [--runs 3]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from rlscape.bridge.client import BridgeClient, run_suffix
from rlscape.gamedata import server as gd
from rlscape.sim.crafting import (FLAX, SEERS_FLAX, Craft, PickFlax, Spin, TanAtTanner, THREAD_CHARGES)
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, INVENTORY_SLOTS, CharacterState

REPO = Path(__file__).resolve().parents[1]
GATE = 0.2
TICKS_PER_HOUR = 6000
TRAINABLE = ("attack", "strength", "defence", "hitpoints", "ranged", "magic", "prayer", "crafting")
THREADS = 10  # reels for a load of leather: 26 items take 6 (decayThread, a reel 5 items)

# The clicks (the server's handlers): the bridge's dialogue_button passes the button less 1 on (DialogueInterpreter).
MAKE_DIALOGUE, ALL_IN_MAKE_DIALOGUE = 309, 3  # SkillDialogue.ONE_OPTION and LeatherCraftDialogue's "hard": 2 is All
DRAGON_DIALOGUE = 304  # LeatherCraftDialogue's "dragon": body, vambraces, chaps; "Make 10" is 5, 9, 13 (sent 6, 10, 14)
DRAGON_MAKE_10 = {"body": 6, "vamb": 10, "vambraces": 10, "chaps": 14}
LEATHER_IFACE = 154  # LeatherCraftInterface: the item's button; option 3 (opcode 124) is All
SOFT_BUTTONS = {"leather_gloves": 29, "leather_boots": 30, "leather_vambraces": 31, "leather_chaps": 32, "coif": 33,
                "leather_cowl": 34}  # LeatherCrafting.SoftLeather
SPIN_IFACE, SPIN_BUTTONS = 459, {"wool": 19, "flax": 17}  # SpinningInterface, SpinningItem's buttons; option 3 is All
TAN_IFACE, TAN_ALL = 324, 5  # TanningInterface: option 5 (opcode 234) tans every hide carried
TAN_BUTTONS = {"leather": 1, "hard_leather": 2, "green_d_leather": 5, "blue_d_leather": 6, "red_dragon_leather": 7,
               "black_d_leather": 8}  # TanningProduct
OPTION_ALL = 3

WHEEL_TILE = (3209, 3213, 1)  # beside Lumbridge Castle's wheel (3209, 3212, 1; data/stations.csv)
ELLIS_TILE = (3274, 3192, 0)  # beside Ellis's spawn (3275, 3193, 0) in Al Kharid
CRAFT_TILE = (3222, 3218, 0)  # anywhere: Lumbridge's home tile
TANNER_SPAWN = (3275, 3193, 0)


@dataclass(frozen=True)
class Case:
    case_id: str  # cut_<gem>, craft_<item>, spin_<item>, tan_<leather>, pick_flax
    band: int

    @property
    def kind(self) -> str:
        if self.case_id.startswith("cut_"):
            return "gem"
        if self.case_id.startswith("craft_"):
            r = gd.crafting_recipes()[self.name]
            if r.kind == "dragonhide":
                return "dragon"
            return "hard" if r.inputs[0][0] == gd.HARD_LEATHER else "leather"
        return self.case_id.split("_")[0]  # spin, tan, pick

    @property
    def name(self) -> str:
        return self.case_id.split("_", 1)[1]


CASES = [Case("cut_opal", 1), Case("cut_emerald", 31), Case("cut_dragonstone", 61), Case("cut_onyx", 91),
         Case("craft_leather_gloves", 1), Case("craft_leather_chaps", 31), Case("craft_hardleather_body", 31),
         Case("craft_green_d_hide_chaps", 61), Case("craft_black_d_hide_body", 91),
         Case("spin_wool", 1), Case("spin_flax", 31), Case("tan_leather", 1), Case("tan_green_d_leather", 61),
         Case("pick_flax", 1)]


def recipe(case: Case) -> Any:
    if case.kind == "spin":
        return gd.spinning_recipes()[case.name]
    if case.kind == "tan":
        return gd.tanning_recipes()[case.name]
    if case.kind == "pick":
        return None
    return gd.crafting_recipes()[case.name]


def product(case: Case) -> int:
    return FLAX if case.kind == "pick" else recipe(case).product


def inputs(case: Case) -> list[tuple[int, int]]:
    """The inventory each run starts with: the tool, thread and as many inputs as fit."""
    r = recipe(case)
    if case.kind == "gem":
        return [(gd.CHISEL, 1), (r.inputs[0][0], INVENTORY_SLOTS - 1)]
    if case.kind in ("leather", "hard", "dragon"):
        item, per = r.inputs[0]
        return [(gd.NEEDLE, 1), (gd.THREAD, THREADS), (item, (INVENTORY_SLOTS - 2) // per * per)]
    if case.kind == "spin":
        return [(r.need, INVENTORY_SLOTS)]
    if case.kind == "tan":
        return [(COINS, 10_000), (r.hide, INVENTORY_SLOTS - 1)]
    return []


def start(case: Case) -> tuple[int, int, int]:
    return {"spin": WHEEL_TILE, "tan": ELLIS_TILE, "pick": SEERS_FLAX.tile}.get(case.kind, CRAFT_TILE)


def character(case: Case) -> CharacterState:
    state = CharacterState.fresh()
    if case.band > 1:
        for skill in TRAINABLE:
            state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[case.band])
        state.hp = state.max_hp()
    state.inventory.clear()  # the starter kit, banked
    for item, amount in inputs(case):
        state.add(item, amount)
    state.thread_charges = THREAD_CHARGES
    state.location = start(case)
    return state


def holding(state: dict[str, Any]) -> dict[int, int]:
    out: dict[int, int] = {}
    for stack in state["inventory"]:
        out[stack["id"]] = out.get(stack["id"], 0) + stack["amount"]
    return out


def crafting_xp(state: dict[str, Any]) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == "crafting")


def next_action(case: Case, state: dict[str, Any], uid: int) -> list[dict[str, Any]] | None:
    """The click a person makes now, or None when there's nothing left to do."""
    held, kind, r = holding(state), case.kind, recipe(case)
    chatbox, iface = state.get("chatbox_id"), state.get("interface_id")
    if kind == "pick":
        if sum(1 for _ in state["inventory"]) >= INVENTORY_SLOTS:
            return None
        return [{"cmd": "interact", "uid": uid, "name": "Flax", "option": "Pick", "object": True, "packet": True}]
    if kind == "tan":
        if not held.get(r.hide):
            return None
        if iface == TAN_IFACE:
            return [{"cmd": "interface_button", "uid": uid, "interface": TAN_IFACE, "button": TAN_BUTTONS[case.name],
                     "option": TAN_ALL, "packet": True}]
        return [{"cmd": "interact", "uid": uid, "name": "Ellis", "option": "Trade", "object": False, "packet": True}]
    if kind == "spin":
        if not held.get(r.need):
            return None
        if iface == SPIN_IFACE:
            return [{"cmd": "interface_button", "uid": uid, "interface": SPIN_IFACE, "button": SPIN_BUTTONS[case.name],
                     "option": OPTION_ALL, "packet": True}]
        return [{"cmd": "interact", "uid": uid, "name": "Spinning wheel", "option": "Spin", "object": True,
                 "packet": True}]
    item, per = r.inputs[0]
    if held.get(item, 0) < per:  # the thread doesn't run out: THREADS reels sew more than a load
        return None
    if kind == "gem" and chatbox == MAKE_DIALOGUE or kind == "hard" and chatbox == MAKE_DIALOGUE:
        return [{"cmd": "dialogue_button", "uid": uid, "interface": MAKE_DIALOGUE, "button": ALL_IN_MAKE_DIALOGUE,
                 "packet": True}]
    if kind == "dragon" and chatbox == DRAGON_DIALOGUE:
        return [{"cmd": "dialogue_button", "uid": uid, "interface": DRAGON_DIALOGUE,
                 "button": DRAGON_MAKE_10[case.name.rsplit("_", 1)[1]], "packet": True}]
    if kind == "leather" and iface == LEATHER_IFACE:
        return [{"cmd": "interface_button", "uid": uid, "interface": LEATHER_IFACE, "button": SOFT_BUTTONS[case.name],
                 "option": OPTION_ALL, "packet": True}]
    tool = gd.CHISEL if kind == "gem" else gd.NEEDLE
    return [{"cmd": "use_item", "uid": uid, "item": tool, "with": item, "packet": True}]


OPEN = {MAKE_DIALOGUE, DRAGON_DIALOGUE, LEATHER_IFACE, SPIN_IFACE, TAN_IFACE}


def server_run(client: BridgeClient, case: Case, budget: int) -> dict[str, Any]:
    """One run, ending at the last product once there's nothing left to do (a pulse can wait a few ticks more)."""
    uid = client.spawn()["uid"]
    try:
        if case.band > 1:
            client.debug_set_levels(uid, {skill: case.band for skill in TRAINABLE})
        for item in {i["id"] for i in client.state(uid)["inventory"]}:
            client.item_option(uid, item, "Drop")
        client.wait(2)
        assert not client.state(uid)["inventory"], "the starter kit didn't all drop"
        for item, amount in inputs(case):
            client.debug_give(uid, item, amount)
        client.debug_teleport(uid, *start(case))
        client.wait(3)
        pending, first, ended, clicks, idle, last_gain, prev = [], None, "completed", 0, 0, 0, None
        made = product(case)
        while True:
            step = client.schedule([[*pending, {"cmd": "state", "uid": uid}]])[0]
            state = step["results"][-1]["state"]
            first = first or (step["tick"], state)
            offset = step["tick"] - first[0]
            count = holding(state).get(made, 0)
            if prev is not None and count > prev:
                last_gain = offset
            prev = count
            if offset >= budget:
                break
            busy = state["busy"] or state["moving"] or state["script"] is not None
            idle = 0 if busy else idle + 1
            action = next_action(case, state, uid)
            if action is None and not busy:
                ended = "inputs_exhausted"
                break
            opened = state.get("chatbox_id") in OPEN or state.get("interface_id") in OPEN
            pending = action if action and (opened or idle >= 1) else []
            clicks += bool(pending)
    finally:
        client.despawn(uid)
    ticks = last_gain if ended == "inputs_exhausted" and last_gain else offset
    return {"ticks": max(ticks, 1), "ended": ended, "clicks": clicks, "until_idle": offset,
            "xp": crafting_xp(state) - crafting_xp(first[1]),
            "made": holding(state).get(made, 0) - holding(first[1]).get(made, 0)}


def sim_option(case: Case) -> Any:
    r = recipe(case)
    if case.kind == "spin":
        return Spin(r)
    if case.kind == "pick":
        return PickFlax()
    if case.kind == "tan":
        return TanAtTanner(r)
    return Craft(r)


def sim_runs(case: Case, runs: int, budget: int) -> list[dict[str, Any]]:
    option, out, made = sim_option(case), [], product(case)
    for seed in range(runs):
        state = character(case)
        before, held = state.xp[SKILL_INDEX["crafting"]], state.inventory.get(made, 0)
        rng = np.random.default_rng(seed)
        result = option._work(state, budget) if case.kind == "tan" else option.run(state, rng, budget)
        out.append({"ticks": max(result.ticks, 1), "ended": result.termination,
                    "xp": state.xp[SKILL_INDEX["crafting"]] - before, "made": state.inventory.get(made, 0) - held})
    return out


def rates(runs: list[dict[str, Any]]) -> dict[str, Any]:
    ticks = sum(r["ticks"] for r in runs)
    ended: dict[str, float] = {}
    for r in runs:
        ended[r["ended"]] = ended.get(r["ended"], 0) + 1 / len(runs)
    return {"xp_per_hour": sum(r["xp"] for r in runs) * TICKS_PER_HOUR / ticks,
            "made_per_hour": sum(r["made"] for r in runs) * TICKS_PER_HOUR / ticks, "ticks": ticks / len(runs),
            "made": sum(r["made"] for r in runs) / len(runs), "runs": len(runs), "ended": ended}


def compare(server: dict[str, Any], sim: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key in ("xp_per_hour", "made_per_hour", "ticks", "made"):
        if not server[key] and not sim[key]:
            continue  # no XP: tanning, picking flax
        ratio = sim[key] / server[key] if server[key] else float("inf")
        out[key] = {"server": round(server[key], 1), "sim": round(sim[key], 1), "sim_over_server": round(ratio, 3),
                    "within_gate": abs(ratio - 1) <= GATE}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cases", nargs="*", help="case ids (default: all of CASES)")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--sim-runs", type=int, default=200)
    parser.add_argument("--budget", type=int, default=1500, help="ticks per run at most")
    parser.add_argument("--tick-ms", type=int, default=50)
    args = parser.parse_args()
    rows = []
    with BridgeClient() as client:
        old_ms = client.set_tick_ms(args.tick_ms)
        try:
            for case in (c for c in CASES if not args.cases or c.case_id in args.cases):
                server = [server_run(client, case, args.budget) for _ in range(args.runs)]
                s, m = rates(server), rates(sim_runs(case, args.sim_runs, args.budget))
                row = {"case": asdict(case), "server_runs": server, "server": s, "sim": m, "compare": compare(s, m)}
                rows.append(row)
                print(f'{case.case_id:24s} band {case.band:2d}  ' + "  ".join(
                    f'{k} {v["server"]:.0f}/{v["sim"]:.0f} ({v["sim_over_server"]:.2f})' for k, v in row["compare"].items())
                      + f'  ended {s["ended"]} / {m["ended"]}', flush=True)
        finally:
            client.set_tick_ms(old_ms)
    which = f"-{'+'.join(args.cases)}" if args.cases else ""
    out = REPO / "results" / "calibration" / f"crafting-{datetime.now():%Y%m%d-%H%M}{which}{run_suffix(args.tick_ms)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(args), "cases": rows}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
