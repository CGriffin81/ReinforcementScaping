"""Calibrate pickpocketing against the server (ROADMAP week 2; env contract §7), as scripts/calibrate.py does
gathering: the activity alone at the target's site, on the live server and in the sim from the same start, against
the ±20% gate.

The cases: each pickpocket target (rlscape.sim.thieving.PICKPOCKET_TARGETS) at each band of `--bands` its level
allows, at the sim's site for it. The character, per env contract §7: the trainable skills at the band (Thieving with
them), a fresh character's at band 1; and food (15 lobsters above band 1, 10 trout at band 1). The starter kit is
dropped first, on both sides, as a deposit before thieving would bank it (the thieving kit keeps only food): with it
and the food, the inventory is full before the first attempt.

A server run: debug_teleport to the site (setup only), then as a person pickpockets, a tick at a time: when the
character is idle (no pulse running and not walking), click "Pickpocket" on the nearest target it can reach; eat
when hitpoints are at or under the sim's point (half the maximum, or the target's largest hit if higher: a failure
then never kills); stop with no food left at that point, at a full inventory, at death, or when the budget runs out.
A stunned character's clicks do nothing, as a person's. What's measured: XP (so successes), stuns (hitpoints lost
outside an eat), loot value and food eaten (what the inventory gains and loses).

The sim runs its option (rlscape.sim.thieving.Pickpocket) from the same state, at the site.

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/calibrate_thieving.py [--targets pickpocket_men ...] [--bands 1 31 61 91] [--runs 3]
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
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, CharacterState
from rlscape.sim.thieving import Pickpocket, largest_random, pickpocket_options

REPO = Path(__file__).resolve().parents[1]
GATE = 0.2
TICKS_PER_HOUR = 6000
TRAINABLE = ("attack", "strength", "defence", "hitpoints", "ranged", "magic", "prayer", "thieving")
LOBSTER, TROUT = 379, 333
FOOD = {1: (TROUT, 10)}  # above band 1: 15 lobsters


@dataclass(frozen=True)
class Case:
    option_id: str
    band: int
    site: tuple[int, int, int]
    target: str  # the NPC's name
    ids: tuple[int, ...]


def cases(targets: list[str] | None, bands: list[int]) -> list[Case]:
    out, npcs = [], gd.npcs()
    for option in pickpocket_options():
        if targets and option.id not in targets:
            continue
        for band in bands:
            if band >= option.target.level:
                name = npcs[option.target.npc_ids[0]].name
                out.append(Case(option.id, band, option.tile, name, option.target.npc_ids))
    return out


def option_of(case: Case) -> Pickpocket:
    return next(o for o in pickpocket_options() if o.id == case.option_id)


def food_of(case: Case) -> tuple[int, int]:
    return FOOD.get(case.band, (LOBSTER, 15))


def eat_below(case: Case, max_hp: int) -> float:
    """The sim's eating point (Pickpocket.eat_below): half the maximum, or the target's largest hit if higher."""
    target = option_of(case).target
    return max(0.5 * max_hp, largest_random(target.stun_damage_min, target.stun_damage_max))


def holding(state: dict[str, Any]) -> dict[int, int]:
    out: dict[int, int] = {}
    for stack in state["inventory"]:
        out[stack["id"]] = out.get(stack["id"], 0) + stack["amount"]
    return out


def gp(held: dict[int, int]) -> float:
    values = gd.item_values()
    return sum(n * (1 if i == COINS else values.get(i, 0)) for i, n in held.items() if i not in gd.food_healing())


def xp(state: dict[str, Any], skill: str) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == skill)


def server_run(client: BridgeClient, case: Case, budget: int) -> dict[str, Any]:
    uid = client.spawn()["uid"]
    try:
        if case.band > 1:
            client.debug_set_levels(uid, {skill: case.band for skill in TRAINABLE})
        for item in {i["id"] for i in client.state(uid)["inventory"]}:
            client.item_option(uid, item, "Drop")
        client.wait(2)  # the last drops land a tick later
        assert not client.state(uid)["inventory"], "the starter kit didn't all drop"
        client.debug_give(uid, *food_of(case))
        client.set_retaliate(uid, False)
        client.debug_teleport(uid, *case.site)
        client.wait(3)
        click = {"cmd": "interact", "uid": uid, "name": case.target, "option": "Pickpocket", "object": False,
                 "ids": list(case.ids), "packet": True}
        heals = gd.food_healing()
        pending, first, prev_hp, food = [], None, None, None
        counts = {"clicks": 0, "no_target": 0, "eaten": 0, "stuns": 0, "damage": 0}
        ended = "completed"
        while True:
            step = client.schedule([[*pending, {"cmd": "state", "uid": uid}]])[0]
            if pending and pending[0] is click:
                counts["clicks" if step["results"][0].get("ok") else "no_target"] += 1
            state = step["results"][-1]["state"]
            first = first or (step["tick"], state)
            offset = step["tick"] - first[0]
            held_food = sum(n for i, n in holding(state).items() if i in heals)
            if food is not None and held_food < food:
                counts["eaten"] += food - held_food
            elif prev_hp is not None and state["hitpoints"] < prev_hp:  # hit, outside an eat: a failed attempt's stun
                counts["stuns"] += 1
                counts["damage"] += prev_hp - state["hitpoints"]
            food, prev_hp = held_food, state["hitpoints"]
            max_hp = next(s["level"] for s in state["skills"] if s["name"].lower() == "hitpoints")
            if state["hitpoints"] <= 0:
                ended = "died"
                break
            if len(state["inventory"]) >= 28:
                ended = "inventory_full"
                break
            if offset >= budget:
                break
            if state["hitpoints"] <= eat_below(case, max_hp):
                edible = [i["id"] for i in state["inventory"] if i["id"] in heals]
                if not edible:
                    ended = "out_of_food"
                    break
                pending = [{"cmd": "item_option", "uid": uid, "item": edible[0], "option": "Eat", "packet": True}]
            elif not state["busy"] and not state["moving"]:
                pending = [click]
            else:
                pending = []
    finally:
        client.despawn(uid)
    return {"ticks": max(offset, 1), "ended": ended, "xp": xp(state, "thieving") - xp(first[1], "thieving"),
            "gp": gp(holding(state)) - gp(holding(first[1])), **counts}


def sim_runs(case: Case, runs: int, budget: int) -> list[dict[str, Any]]:
    option, heals, out = option_of(case), gd.food_healing(), []
    for seed in range(runs):
        state = CharacterState.fresh()
        if case.band > 1:
            for skill in TRAINABLE:
                state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[case.band])
            state.hp = state.max_hp()
        state.inventory.clear()  # the starter kit, banked
        state.add(*food_of(case))
        state.location = case.site
        before_xp, before = state.xp[SKILL_INDEX["thieving"]], dict(state.inventory)
        food_before = sum(n for i, n in state.inventory.items() if i in heals)
        result = option.run(state, np.random.default_rng(seed), budget)
        out.append({"ticks": max(result.ticks, 1), "ended": result.termination,
                    "xp": state.xp[SKILL_INDEX["thieving"]] - before_xp, "gp": gp(state.inventory) - gp(before),
                    "eaten": food_before - sum(n for i, n in state.inventory.items() if i in heals)})
    return out


def rates(runs: list[dict[str, Any]]) -> dict[str, Any]:
    ticks = sum(r["ticks"] for r in runs)
    ended: dict[str, float] = {}
    for r in runs:
        ended[r["ended"]] = ended.get(r["ended"], 0) + 1 / len(runs)
    return {"xp_per_hour": sum(r["xp"] for r in runs) * TICKS_PER_HOUR / ticks,
            "gp_per_hour": sum(r["gp"] for r in runs) * TICKS_PER_HOUR / ticks,
            "food_per_hour": sum(r["eaten"] for r in runs) * TICKS_PER_HOUR / ticks,
            "ticks": ticks / len(runs), "runs": len(runs), "ended": ended}


def compare(server: dict[str, Any], sim: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key in ("xp_per_hour", "gp_per_hour"):
        ratio = sim[key] / server[key] if server[key] else float("inf")
        out[key] = {"server": round(server[key], 1), "sim": round(sim[key], 1), "sim_over_server": round(ratio, 3),
                    "within_gate": abs(ratio - 1) <= GATE}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--targets", nargs="*", help="option ids (default: every pickpocket target)")
    parser.add_argument("--bands", type=int, nargs="+", default=[1, 31, 61, 91])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--sim-runs", type=int, default=200)
    parser.add_argument("--budget", type=int, default=1500, help="ticks per run at most (D: 15 game-minutes)")
    parser.add_argument("--tick-ms", type=int, default=50)
    args = parser.parse_args()
    rows = []
    with BridgeClient() as client:
        old_ms = client.ping()["tick_ms"]
        client.set_tick_ms(args.tick_ms)
        try:
            for case in cases(args.targets, args.bands):
                server = [server_run(client, case, args.budget) for _ in range(args.runs)]
                sim = sim_runs(case, args.sim_runs, args.budget)
                s, m = rates(server), rates(sim)
                row = {"case": asdict(case), "server_runs": server, "server": s, "sim": m, "compare": compare(s, m)}
                rows.append(row)
                c = row["compare"]
                print(f'{case.option_id:28s} band {case.band:2d}  xp/h server {s["xp_per_hour"]:7.0f} sim '
                      f'{m["xp_per_hour"]:7.0f} ({c["xp_per_hour"]["sim_over_server"]:.2f})  gp/h {s["gp_per_hour"]:7.0f} '
                      f'{m["gp_per_hour"]:7.0f}  food/h {s["food_per_hour"]:5.1f} {m["food_per_hour"]:5.1f}  stuns '
                      f'{[r["stuns"] for r in server]}  ended {s["ended"]} / {m["ended"]}', flush=True)
        finally:
            client.set_tick_ms(old_ms)
    # the targets and bands in the name: several runs can share a server and end in the same minute
    which = (f"-{'+'.join(t.removeprefix('pickpocket_') for t in args.targets)}-b{'+'.join(map(str, args.bands))}"
             if args.targets else "")
    out = (REPO / "results" / "calibration"
           / f"thieving-{datetime.now():%Y%m%d-%H%M}{which}{run_suffix(args.tick_ms)}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(args), "cases": rows}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
