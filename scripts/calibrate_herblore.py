"""Calibrate Herblore (sim v1, `docs/sim-v1-skills-draft.md` §7) against the server, as scripts/calibrate_crafting.py
does Crafting: the work alone, from a full inventory, on the live server and in the sim, against the ±20% gate (env
contract §7).

The cases, a stage at a time and two whole loads:
- `clean`: the grimy herb's "Clean" (an item option), a click a tick;
- `unf`: a vial of water on the clean herb, then the how-many's All;
- `finish`: the unfinished potion on the secondary, then All;
- `grind`: the pestle and mortar on the whole ingredient, then All;
- `load`: a potion path's load, as `PotionAtBank.mix` makes it: grind, clean, the unfinished potions, the finished
  ones, a person's clicks for each stage in turn.
The character, per env contract §7: Herblore at the band (the other skills too), the starter kit dropped, and the
inventory (setup only, debug_give). Druidic Ritual is complete from the start.

A server run: debug_teleport to Lumbridge (setup only), then the next click when the character is idle, the
how-many's button as soon as it's open, until the inputs run out or the budget does. Measured: the ticks to the last
product, the Herblore XP, the products. The sim: the stage's time (`herblore.unfinished_ticks` and the rest), or
`PotionAtBank.mix` for a load.

Usage, with a server running:
    RL_BRIDGE_PORT=43616 uv run python scripts/calibrate_herblore.py [--cases clean_guam ...] [--runs 3]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from rlscape.bridge.client import BridgeClient, run_suffix
from rlscape.gamedata import server as gd
from rlscape.sim import herblore as hb
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import INVENTORY_SLOTS, CharacterState

REPO = Path(__file__).resolve().parents[1]
GATE = 0.2
TICKS_PER_HOUR = 6000
TRAINABLE = ("attack", "strength", "defence", "hitpoints", "ranged", "magic", "prayer", "herblore")
MAKE_DIALOGUE, ALL = 309, 3  # SkillDialogue.ONE_OPTION: the bridge passes the button less 1 on, and 2 is All
START = (3222, 3218, 0)
VIAL, PESTLE = gd.VIAL_OF_WATER, gd.PESTLE_AND_MORTAR


@dataclass(frozen=True)
class Case:
    case_id: str  # clean_<herb>, unf_<herb>, finish_<potion>, grind_<whole id>, load_<potion>
    band: int

    @property
    def kind(self) -> str:
        return self.case_id.split("_", 1)[0]

    @property
    def name(self) -> str:
        return self.case_id.split("_", 1)[1]


CASES = [Case("clean_guam", 31), Case("clean_torstol", 91), Case("unf_guam", 31), Case("unf_torstol", 91),
         Case("finish_attack", 31), Case("finish_super_restore", 91), Case("grind_237", 31),
         Case("load_attack", 31), Case("load_super_antipoison", 61)]


def potion(case: Case) -> gd.Potion:
    return gd.herblore_potions()[case.name]


def herb(case: Case) -> gd.Herb:
    return gd.herbs()[case.name] if case.kind in ("clean", "unf") else hb.herb_by_clean()[potion(case).herb]


def inputs(case: Case) -> list[tuple[int, int]]:
    if case.kind == "clean":
        return [(herb(case).grimy, INVENTORY_SLOTS)]
    if case.kind == "unf":
        return [(VIAL, INVENTORY_SLOTS // 2), (herb(case).clean, INVENTORY_SLOTS // 2)]
    if case.kind == "finish":
        return [(potion(case).unfinished, INVENTORY_SLOTS // 2), (potion(case).secondary, INVENTORY_SLOTS // 2)]
    if case.kind == "grind":
        return [(PESTLE, 1), (int(case.name), INVENTORY_SLOTS - 1)]
    p, h = potion(case), herb(case)  # a load: 9 units, from grimy herbs and, if it has one, the whole ingredient
    whole = hb.whole_of().get(p.secondary)
    return [(PESTLE, 1), (VIAL, 9), (h.grimy, 9), (whole, 9)] if whole else [(VIAL, 9), (h.grimy, 9), (p.secondary, 9)]


def product(case: Case) -> int:
    if case.kind == "clean":
        return herb(case).clean
    if case.kind == "unf":
        return gd.unfinished_potions()[case.name][1]
    if case.kind == "grind":
        return gd.grindings()[int(case.name)]
    return potion(case).product


def holding(state: dict[str, Any]) -> dict[int, int]:
    out: dict[int, int] = {}
    for stack in state["inventory"]:
        out[stack["id"]] = out.get(stack["id"], 0) + stack["amount"]
    return out


def herblore_xp(state: dict[str, Any]) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == "herblore")


def use(uid: int, item: int, other: int) -> list[dict[str, Any]]:
    return [{"cmd": "use_item", "uid": uid, "item": item, "with": other, "packet": True}]


def next_action(case: Case, state: dict[str, Any], uid: int) -> list[dict[str, Any]] | None:
    """The click a person makes now, or None when there's nothing left to do."""
    held, kind = holding(state), case.kind
    if state.get("chatbox_id") == MAKE_DIALOGUE:
        return [{"cmd": "dialogue_button", "uid": uid, "interface": MAKE_DIALOGUE, "button": ALL, "packet": True}]
    grimy = herb(case).grimy if kind in ("clean", "load") else None
    if kind == "clean" or (kind == "load" and held.get(grimy)
                           and not (hb.whole_of().get(potion(case).secondary) in held)):
        return [{"cmd": "item_option", "uid": uid, "item": grimy, "option": "Clean", "packet": True}] \
            if held.get(grimy) else None
    if kind == "unf":
        return use(uid, VIAL, herb(case).clean) if held.get(VIAL) and held.get(herb(case).clean) else None
    if kind == "grind":
        return use(uid, PESTLE, int(case.name)) if held.get(int(case.name)) else None
    p = potion(case)
    if kind == "load":
        whole = hb.whole_of().get(p.secondary)
        if whole and held.get(whole):
            return use(uid, PESTLE, whole)
        if held.get(VIAL) and held.get(p.herb):
            return use(uid, VIAL, p.herb)
    return use(uid, p.unfinished, p.secondary) if held.get(p.unfinished) and held.get(p.secondary) else None


def server_run(client: BridgeClient, case: Case, budget: int) -> dict[str, Any]:
    uid = client.spawn()["uid"]
    try:
        client.debug_set_levels(uid, {skill: case.band for skill in TRAINABLE})
        for item in {i["id"] for i in client.state(uid)["inventory"]}:
            client.item_option(uid, item, "Drop")
        client.wait(2)
        assert not client.state(uid)["inventory"], "the starter kit didn't all drop"
        for item, amount in inputs(case):
            client.debug_give(uid, item, amount)
        client.debug_teleport(uid, *START)
        client.wait(3)
        pending, first, ended, clicks, idle, last_gain, prev, made = [], None, "completed", 0, 0, 0, None, product(case)
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
            opened = state.get("chatbox_id") == MAKE_DIALOGUE
            # cleaning is a click a tick (the option locks a tick); a how-many's button as soon as it's open
            pending = action if action and (opened or idle >= 1 or case.kind == "clean") else []
            clicks += bool(pending)
    finally:
        client.despawn(uid)
    ticks = last_gain if ended == "inputs_exhausted" and last_gain else offset
    return {"ticks": max(ticks, 1), "ended": ended, "clicks": clicks, "until_idle": offset,
            "xp": herblore_xp(state) - herblore_xp(first[1]),
            "made": holding(state).get(made, 0) - holding(first[1]).get(made, 0)}


def sim_run(case: Case, budget: int) -> dict[str, Any]:
    """The sim's time for the case (deterministic): a stage's, or a load's through PotionAtBank.mix."""
    n = dict(inputs(case))
    if case.kind == "clean":
        units = n[herb(case).grimy]
        return {"ticks": hb.clean_ticks(units), "xp": units * herb(case).experience, "made": units,
                "ended": "inputs_exhausted"}
    if case.kind == "unf":
        units = n[VIAL]
        return {"ticks": hb.unfinished_ticks(units), "xp": 0.0, "made": units, "ended": "inputs_exhausted"}
    if case.kind == "finish":
        units = n[potion(case).unfinished]
        return {"ticks": hb.finished_ticks(units), "xp": units * potion(case).experience, "made": units,
                "ended": "inputs_exhausted"}
    if case.kind == "grind":
        units = n[int(case.name)]
        return {"ticks": hb.grind_ticks(units), "xp": 0.0, "made": units, "ended": "inputs_exhausted"}
    state = CharacterState.fresh()
    for skill in TRAINABLE:
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[case.band])
    state.inventory = dict(n)
    before = state.xp[SKILL_INDEX["herblore"]]
    result = hb.PotionAtBank(potion(case)).mix(state, budget)
    return {"ticks": result.ticks, "xp": state.xp[SKILL_INDEX["herblore"]] - before,
            "made": state.inventory.get(potion(case).product, 0), "ended": result.termination}


def rates(runs: list[dict[str, Any]]) -> dict[str, Any]:
    ticks = sum(r["ticks"] for r in runs)
    return {"xp_per_hour": sum(r["xp"] for r in runs) * TICKS_PER_HOUR / ticks,
            "made_per_hour": sum(r["made"] for r in runs) * TICKS_PER_HOUR / ticks, "ticks": ticks / len(runs),
            "made": sum(r["made"] for r in runs) / len(runs), "runs": len(runs)}


def compare(server: dict[str, Any], sim: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key in ("xp_per_hour", "made_per_hour", "ticks", "made"):
        if not server[key] and not sim[key]:
            continue  # no XP: unfinished potions, grinding
        ratio = sim[key] / server[key] if server[key] else float("inf")
        out[key] = {"server": round(server[key], 1), "sim": round(sim[key], 1), "sim_over_server": round(ratio, 3),
                    "within_gate": abs(ratio - 1) <= GATE}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cases", nargs="*", help="case ids (default: all of CASES)")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--budget", type=int, default=1500, help="ticks per run at most")
    parser.add_argument("--tick-ms", type=int, default=50)
    args = parser.parse_args()
    rows = []
    with BridgeClient() as client:
        old_ms = client.set_tick_ms(args.tick_ms)
        try:
            for case in (c for c in CASES if not args.cases or c.case_id in args.cases):
                server = [server_run(client, case, args.budget) for _ in range(args.runs)]
                s, m = rates(server), rates([sim_run(case, args.budget)])
                row = {"case": asdict(case), "server_runs": server, "server": s, "sim": m, "compare": compare(s, m)}
                rows.append(row)
                print(f'{case.case_id:24s} band {case.band:2d}  ' + "  ".join(
                    f'{k} {v["server"]:.0f}/{v["sim"]:.0f} ({v["sim_over_server"]:.2f})' for k, v in row["compare"].items()),
                      flush=True)
        finally:
            client.set_tick_ms(old_ms)
    which = f"-{'+'.join(args.cases)}" if args.cases else ""
    out = REPO / "results" / "calibration" / f"herblore-{datetime.now():%Y%m%d-%H%M}{which}{run_suffix(args.tick_ms)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(args), "cases": rows}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
