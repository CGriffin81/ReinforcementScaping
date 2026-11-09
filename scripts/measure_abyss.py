"""Measure the Abyss's times on the server against the sim (sim v1, Runecrafting part 4; rlscape.sim.abyss; env
contract §7), as scripts/calibrate_runecrafting.py does the ruins'.

The cases (a fresh character, set up only by debug_teleport and debug_set_levels; every click as a person makes it;
rlscape.bridge.abyss):
- `--pass N`: for each kind of obstacle, N trips at level 99 in its skill (every try passes) with its tool: from a few
  tiles south of the mage, its Teleport; then to beside the nearest of that kind by the planner's steps on the
  server's collision map (data/abyss/collision.npz), walked as the travel walker walks a route (rlscape.bridge.walker:
  a click 20 tiles ahead, the next 3 tiles before it), and the obstacle clicked. Measured: the teleport (click to
  landing), the outer ring (the walk's first click to standing on the inner ring), and the hitpoints the monsters
  took from landing to the inner ring. The sim's side: those steps timed as walks are (rlscape.sim.movement.timed:
  running, with the walker's overhead), and PASS_TICKS or PASSAGE_TICKS; and ATTACKS_PER_TICK of the sim's mean
  damage a swing over the same ticks, at the character's levels (rlscape.sim.abyss.mean_damage). The rate is fitted
  from the hitpoints lost: the sim's damage a swing is the server's (probed standing: 634 against 636 over 678
  swings), and the walker's ticks hide the swings from a count.
- `--fails N`: as --pass, at level 1 (a 2% pass): the ticks between tries, a try clicked again as its fail shows.
- `--rifts`: from each of the twelve inner-ring landings (data/abyss), each rift walked to and clicked, as above: the
  ticks to its altar's landing, against the planner's steps timed as walks are and RIFT_TICKS.
- `--trips N`: for each rune, N whole crossings as abyss_rc_<rune> makes them: a character with Agility 60, Thieving
  50, Mining 61 and a rune pickaxe worn, and 27 pure essence; the teleport; the obstacle the sim takes for the
  landing's segment (rlscape.sim.abyss.best_crossing), walked to and tried until it passes; the rift; the altar's
  Craft-rune. Measured: the teleport's click to the runes. The sim's side: the same trip's walks (the planner's steps
  from the actual landing and inner landing) and tries timed by the sim's constants, and the walk to the altar and
  CRAFT_TICKS (rlscape.sim.runecrafting); and the sim's expectation for the segment (Crossing.expected).
The probes that name the obstacles (debug_nearby) take game ticks at 50 ms, so the outer ring is timed from the
trip's first click after them; the attacks count from landing.

Usage, with the server running (an instance with RL_BRIDGE_PORT):
    uv run python scripts/measure_abyss.py --pass 6 --fails 2 --rifts
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from rlscape.bridge.abyss import (INNER_RADIUS, KINDS, MAGE_TILE, RIFTS, in_abyss, landing_place, places, polar,
                                  segment, teleport, tick, xy)
from rlscape.bridge.client import BridgeClient, BridgeError, run_suffix
from rlscape.bridge.walker import walk_route
from rlscape.gamedata import runecrafting as rcd
from rlscape.routes import Map
from rlscape.sim.abyss import (ATTACKS_PER_TICK, FAIL_TICKS, PASS_TICKS, PASSAGE_TICKS, RIFT_TICKS, TELEPORT_TICKS,
                               best_crossing, mean_damage, walk_ticks)
from rlscape.sim.energy import RUN_TILES
from rlscape.sim.runecrafting import CRAFT_TICKS, INSIDE, RIFT_INSIDE
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

REPO = Path(__file__).resolve().parents[1]
GATE = 0.2
START = (MAGE_TILE[0] - 1, MAGE_TILE[1] - 4)  # a few tiles south of the mage's spawn
TOOLS = {"rocks": 1275, "tendrils": 1359, "boil": 590}  # rune pickaxe, rune axe, tinderbox
# every rift's own checks (MysteriousRuinListener.checkReq): death asks Ranged 60 and Thieving 50 (Mourning's End
# Part II's own requirement, the server lacking the quest)
TRIP_LEVELS = {"hitpoints": 99, "defence": 99, "runecrafting": 99, "ranged": 60, "thieving": 50}


def abyss_map() -> Map:
    data = np.load(rcd.ABYSS / "collision.npz")
    return Map(data["flags"], tuple(int(v) for v in data["origin"]), [])


def beside(world: Map, tile: tuple[int, int], size: tuple[int, int]) -> list[int]:
    (x, y), (sx, sy) = tile, size
    around = ([(x - 1, y + j) for j in range(sy)] + [(x + sx, y + j) for j in range(sy)]
              + [(x + i, y - 1) for i in range(sx)] + [(x + i, y + sy) for i in range(sx)])
    return [n for n in map(world.node, around) if n is not None and world.standable[n]]


def nearest_beside(world: Map, start: tuple[int, int], tile: tuple[int, int],
                   size: tuple[int, int]) -> tuple[float, tuple[int, int, int] | None]:
    """The planner's steps from a tile to beside a node, and the tile beside it the walk ends on."""
    node = world.node(start)
    targets = beside(world, tile, size)
    if node is None or not targets:
        return float("inf"), None
    lengths = world.lengths(node)
    end = min(targets, key=lambda n: lengths[n])
    return float(lengths[end]), world.tile(end)


def walk_and_click(c: BridgeClient, uid: int, world: Map, goal: tuple[int, int, int] | None, name: str,
                   option: str, ids: list[int]) -> tuple[int, int]:
    """Walk to `goal` as the travel walker does (not if it's where the character stands), then click the node; the
    walk's first tick and the click's."""
    first = tick(c, uid)[0]
    if goal is not None and goal[:2] != xy(c.state(uid)):
        walk_route(c, uid, world, goal)
    c.interact(uid, name, option, ids=ids, radius=30)
    return first, tick(c, uid)[0]


def spawn_trip(c: BridgeClient, levels: dict[str, int], items: list[tuple[int, int]]) -> int:
    uid = c.spawn()["uid"]
    c.debug_set_levels(uid, levels)
    for item in {i["id"] for i in c.state(uid)["inventory"]}:
        c.item_option(uid, item, "Drop")
    c.wait(2)
    for item, amount in items:
        c.debug_give(uid, item, amount)
    c.set_run(uid, True)
    return uid


def sim_character(levels: dict[str, int]) -> CharacterState:
    """A fresh sim character at the trip's levels (nothing worn, as the runner's)."""
    state = CharacterState.fresh()
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.hp = state.max_hp()
    return state


def pass_run(c: BridgeClient, world: Map, kind: str, level: int, max_tries: int = 40,
             budget: int = 600) -> dict[str, Any]:
    name, option, skill = KINDS[kind]
    data = json.loads((rcd.ABYSS / "abyss.json").read_text(encoding="utf-8"))
    levels = dict(TRIP_LEVELS, **({skill: level} if skill else {}))
    uid = spawn_trip(c, levels, [(TOOLS[kind], 1)] if kind in TOOLS else [])
    try:
        c.debug_teleport(uid, *START)
        c.wait(3)
        t0, t1, s = teleport(c, uid)
        hp0, landing = s["hitpoints"], xy(s)
        seen = places(c, uid)
        angles = {int(i): polar(*p["tile"])[1] for i, p in data["places"].items()}
        here = landing_place(seen, angles, polar(*landing)[1])
        ways = {i: nearest_beside(world, landing, tuple(data["places"][str(i)]["tile"]),
                                  tuple(data["places"][str(i)]["size"])) for i, p in seen.items() if p["kind"] == kind}
        chosen = min(ways, key=lambda i: ways[i][0])
        steps, goal = ways[chosen]
        # the probes above take game ticks: the trip's walk starts after them
        start, clicked = walk_and_click(c, uid, world, goal, name, option, [chosen])
        clicks, tries, last_fail, arrived = [clicked], 1, None, None
        for _ in range(budget):
            t, s = tick(c, uid)
            if polar(*xy(s))[0] < INNER_RADIUS:
                arrived = t
                break
            fails = [m for m in s["messages"] if "...but fail" in m]
            if fails and fails[-1] != last_fail:
                last_fail = fails[-1]
                if tries >= max_tries:
                    break
                c.interact(uid, name, option, ids=[chosen], radius=30)
                clicks.append(t)
                tries += 1
        sim_outer = walk_ticks(steps) + (PASSAGE_TICKS if kind == "passage" else PASS_TICKS)
        return {"kind": kind, "level": level, "teleport": t1 - t0, "landing": landing, "place": here,
                "chosen": chosen, "tries": tries, "passed": arrived is not None,
                "outer": (arrived - start) if arrived else None, "sim_outer": round(sim_outer, 2),
                "steps": steps, "between_tries": [b - a for a, b in zip(clicks, clicks[1:])],
                "inner_landing": xy(s) if arrived else None, "hp_lost": hp0 - s["hitpoints"],
                "exposed": (arrived or t) - t1, "sim_damage_a_swing": round(mean_damage(sim_character(levels)), 3)}
    finally:
        c.despawn(uid)


def rift_run(c: BridgeClient, world: Map, start: tuple[int, int], rune: str, budget: int = 200) -> dict[str, Any]:
    data = json.loads((rcd.ABYSS / "abyss.json").read_text(encoding="utf-8"))
    rift = data["rifts"][rune]
    uid = spawn_trip(c, TRIP_LEVELS, [])
    try:
        c.debug_teleport(uid, *start)
        c.wait(3)
        steps, goal = nearest_beside(world, start, tuple(rift["tile"]), tuple(rift["size"]))
        t0, _ = walk_and_click(c, uid, world, goal, f"{rune.capitalize()} rift", "Exit-through", [rift["id"]])
        for _ in range(budget):
            t, s = tick(c, uid)
            if not in_abyss(s):
                return {"rune": rune, "start": start, "ticks": t - t0, "to": s["location"], "steps": steps,
                        "sim": round(walk_ticks(steps) + RIFT_TICKS, 2)}
        return {"rune": rune, "start": start, "error": "no exit"}
    finally:
        c.despawn(uid)


TRIP_SKILLS = {"agility": 60, "mining": 61}  # with TRIP_LEVELS (Thieving 50): every kind but the boil is usable
RUNE_PICKAXE, WEAPON = 1275, 3  # the pickaxe and the equipment slot it's worn in


def trip_run(c: BridgeClient, world: Map, rune: str, budget: int = 600) -> dict[str, Any]:
    data, a = json.loads((rcd.ABYSS / "abyss.json").read_text(encoding="utf-8")), rcd.abyss()
    levels = dict(TRIP_LEVELS, **TRIP_SKILLS)
    armed = rune != "law"  # the law rift asks Entrana's rule: no weapons (abyss_rc_law banks its arms)
    uid = spawn_trip(c, levels, [(RUNE_PICKAXE, 1)] * armed + [(rcd.PURE_ESSENCE, 27)])
    try:
        sim = sim_character(levels)
        if armed:
            c.item_option(uid, RUNE_PICKAXE, "Wield")
            sim.equipment[WEAPON] = RUNE_PICKAXE
        c.debug_teleport(uid, *START)
        c.wait(3)
        t0, t1, s = teleport(c, uid)
        landing = xy(s)
        seen = places(c, uid)
        angles = {int(i): polar(*p["tile"])[1] for i, p in data["places"].items()}
        here = landing_place(seen, angles, polar(*landing)[1])
        v = segment(angles[here])
        crossing = best_crossing(sim, v, rune)
        obstacle, kind = a.places[crossing.place], crossing.kind
        name, option, _ = KINDS[kind]
        place = data["places"][str(obstacle)]
        steps, goal = nearest_beside(world, landing, tuple(place["tile"]), tuple(place["size"]))
        start, _ = walk_and_click(c, uid, world, goal, name, option, [obstacle])
        tries, last_fail, inner = 1, None, None
        for _ in range(budget):
            t, s = tick(c, uid)
            if polar(*xy(s))[0] < INNER_RADIUS:
                inner = xy(s)
                break
            fails = [m for m in s["messages"] if "...but fail" in m]
            if fails and fails[-1] != last_fail:
                last_fail = fails[-1]
                c.interact(uid, name, option, ids=[obstacle], radius=30)
                tries += 1
        if inner is None:
            return {"rune": rune, "error": "didn't pass"}
        rift = data["rifts"][rune]
        inner_steps, rift_goal = nearest_beside(world, inner, tuple(rift["tile"]), tuple(rift["size"]))
        walk_and_click(c, uid, world, rift_goal, f"{rune.capitalize()} rift", "Exit-through", [rift["id"]])
        for _ in range(budget):
            t, s = tick(c, uid)
            if not in_abyss(s):
                break
        c.interact(uid, "Altar", "Craft-rune")
        item, end = rcd.runes()[rune].item, None
        for _ in range(budget):
            t, s = tick(c, uid)
            if any(i["id"] == item for i in s["inventory"]):
                end = t
                break
        if end is None:
            return {"rune": rune, "error": "no runes"}
        to_altar = RIFT_INSIDE[rune] if rune in RIFT_INSIDE else INSIDE[rune][0]
        inside = to_altar[0] / RUN_TILES + CRAFT_TICKS
        passing = PASSAGE_TICKS if kind == "passage" else PASS_TICKS + (tries - 1) * FAIL_TICKS
        sim_trip = (TELEPORT_TICKS + 4 / 2 + walk_ticks(steps) + passing + walk_ticks(inner_steps) + RIFT_TICKS
                    + inside)
        expected = TELEPORT_TICKS + 4 / 2 + crossing.expected + inside
        return {"rune": rune, "segment": v, "kind": kind, "tries": tries, "server": (t1 - t0) + (end - start),
                "sim": round(sim_trip, 2), "sim_expected": round(expected, 2), "steps": steps,
                "inner_steps": inner_steps, "hp_lost": 99 - s["hitpoints"]}
    finally:
        c.despawn(uid)


def ratio(server: float, sim: float) -> dict[str, Any]:
    r = sim / server if server else float("inf")
    return {"server": round(server, 2), "sim": round(sim, 2), "sim_over_server": round(r, 3),
            "within_gate": abs(r - 1) <= GATE}


def summarise(rows: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if rows.get("pass"):
        done = [r for r in rows["pass"] if r["outer"] is not None]
        # the sim walks to the mage's tile and clicks there; here it's four tiles south, a click away
        out["teleport"] = ratio(float(np.mean([r["teleport"] for r in done])), TELEPORT_TICKS + 4 / 2)
        out["outer"] = {kind: ratio(float(np.mean([r["outer"] for r in done if r["kind"] == kind])),
                                    float(np.mean([r["sim_outer"] for r in done if r["kind"] == kind])))
                        for kind in KINDS if any(r["kind"] == kind for r in done)}
        out["outer_all"] = ratio(float(np.mean([r["outer"] for r in done])),
                                 float(np.mean([r["sim_outer"] for r in done])))
        lost = sum(r["hp_lost"] for r in done)
        swing_damage = sum(r["exposed"] * r["sim_damage_a_swing"] for r in done)
        out["hp_lost"] = ratio(lost, ATTACKS_PER_TICK * swing_damage)
        out["attacks_per_tick_fit"] = round(lost / swing_damage, 3) if swing_damage else None
        out["hp_lost_per_tick"] = round(lost / sum(r["exposed"] for r in done), 4)
    if rows.get("fails"):
        gaps = [g for r in rows["fails"] for g in r["between_tries"]]
        out["between_tries"] = (len(gaps), float(np.mean(gaps)) if gaps else None)
    if rows.get("rifts"):
        done = [r for r in rows["rifts"] if "ticks" in r]
        out["rifts"] = {rune: ratio(float(np.mean([r["ticks"] for r in done if r["rune"] == rune])),
                                    float(np.mean([r["sim"] for r in done if r["rune"] == rune])))
                        for rune in RIFTS if any(r["rune"] == rune for r in done)}
        out["rifts_all"] = ratio(float(np.mean([r["ticks"] for r in done])), float(np.mean([r["sim"] for r in done])))
    if rows.get("trips"):
        done = [r for r in rows["trips"] if "server" in r]
        out["trips"] = {rune: ratio(float(np.mean([r["server"] for r in done if r["rune"] == rune])),
                                    float(np.mean([r["sim"] for r in done if r["rune"] == rune])))
                        for rune in RIFTS if any(r["rune"] == rune for r in done)}
        out["trips_all"] = ratio(float(np.mean([r["server"] for r in done])), float(np.mean([r["sim"] for r in done])))
        out["trips_expected"] = ratio(float(np.mean([r["server"] for r in done])),
                                      float(np.mean([r["sim_expected"] for r in done])))
        out["trip_kinds"] = {k: sum(r["kind"] == k for r in done) for k in KINDS}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pass", dest="passes", type=int, default=0)
    parser.add_argument("--kinds", nargs="*", default=list(KINDS))
    parser.add_argument("--fails", type=int, default=0)
    parser.add_argument("--rifts", action="store_true")
    parser.add_argument("--trips", type=int, default=0)
    parser.add_argument("--runes", nargs="*", default=list(RIFTS))
    parser.add_argument("--defence", type=int, default=TRIP_LEVELS["defence"],
                        help="the trips' Defence (the damage's check set: hitpoints stay 99)")
    parser.add_argument("--tick-ms", type=int, default=50)
    args = parser.parse_args()
    TRIP_LEVELS["defence"] = args.defence
    world, rows = abyss_map(), {}
    data = json.loads((rcd.ABYSS / "abyss.json").read_text(encoding="utf-8"))
    with BridgeClient() as c:
        old_ms = c.set_tick_ms(args.tick_ms)
        try:
            if args.passes:
                rows["pass"] = []
                for kind in args.kinds:
                    for _ in range(args.passes):
                        row = pass_run(c, world, kind, 99)
                        rows["pass"].append(row)
                        print("pass", kind, row["place"], row["chosen"], row["steps"], row["outer"], row["sim_outer"],
                              row["hp_lost"], row["exposed"], flush=True)
            if args.fails:
                rows["fails"] = []
                for kind in [k for k in args.kinds if KINDS[k][2]]:
                    for _ in range(args.fails):
                        row = pass_run(c, world, kind, 1, max_tries=12)
                        rows["fails"].append(row)
                        print("fails", kind, row["tries"], row["between_tries"], row["passed"], flush=True)
            if args.rifts:
                rows["rifts"] = []
                for obstacle, start in sorted(data["inner_tiles"].items()):
                    for rune in args.runes:
                        row = rift_run(c, world, tuple(start), rune)
                        row["obstacle"] = obstacle
                        rows["rifts"].append(row)
                        print("rift", obstacle, rune, row.get("ticks"), row.get("sim"), row.get("steps"),
                              row.get("error", ""), flush=True)
            if args.trips:
                rows["trips"] = []
                for rune in args.runes:
                    for _ in range(args.trips):
                        try:
                            row = trip_run(c, world, rune)
                        except BridgeError as e:
                            row = {"rune": rune, "error": str(e)}
                        rows["trips"].append(row)
                        print("trip", rune, row.get("segment"), row.get("kind"), row.get("tries"), row.get("server"),
                              row.get("sim"), row.get("sim_expected"), row.get("error", ""), flush=True)
        finally:
            c.set_tick_ms(old_ms)
    summary = summarise(rows)
    print(json.dumps(summary, indent=1))
    out = REPO / "results" / "calibration" / f"abyss-{datetime.now():%Y%m%d-%H%M}{run_suffix(args.tick_ms)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(args), "summary": summary, **rows}, indent=1, default=str))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
