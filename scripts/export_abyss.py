"""Export the Abyss for the sim (sim v1, Runecrafting part 4; docs/sim-v1-skills-draft.md §5): data/abyss/.

From the server (an instance with RL_BRIDGE_PORT; setup and data export only, never the agent):
- the Abyss's collision flags (debug_collision: map region 47, 75, which holds both rings) and the tiles of its twelve
  obstacles (scenery 7142-7153) and its rifts;
- the layouts: the mage's teleport, again and again until every place has been the landing's (blocked) one, and at
  each landing the kind every other place shows (rlscape.bridge.abyss.places). The layout follows varbit 625, the
  landing's segment, so each segment's is recorded once and checked against every repeat.

Then the walks, on that collision map with the travel planner's steps (rlscape.routes.Map, as the server's
pathfinder steps):
- `outer_steps[segment][place]`: from the landing to beside each obstacle, the mean over the segment's landings
  (AbyssLoc.randomLoc's angles, a degree apart, each drawn in from radius 25.1 until its tile can be stood on, as
  AbyssLoc.isValid has it);
- `inner_steps[place][rune]`: from the inner ring's landing past each obstacle (AbyssPlugin.innerRing) to beside each
  rift.
A tile beside a node is one next to its footprint, not at a corner, that a character can stand on.

Written: data/abyss/collision.npz (the flags, int32, rows from the box's south edge, as data/travel's) and
data/abyss/abyss.json (the places, rifts, layouts and walks).

Usage, with the server running:
    uv run python scripts/export_abyss.py [--teleports 200]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from rlscape.bridge.abyss import (MAGE_TILE, OBSTACLES, ORIGIN, OUTER_RADIUS, INNER_STEPS, RIFTS, beside,
                                  landing_place, places, polar, segment, teleport, xy)
from rlscape.bridge.client import BridgeClient
from rlscape.routes import Map

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "abyss"
BOX = (3008, 4800, 3071, 4863)  # map region (47, 75): the outer ring is 22 to 26 tiles from (3039, 4832)


def drawn_in(world: Map, radius: float, angle: float) -> int:
    """AbyssLoc.toAbs at (radius, angle), drawn in a tile at a time until it can be stood on (AbyssLoc.attract and
    isValid; the toInt truncates towards 0, as Python's int does)."""
    while radius > 0:
        node = world.node((ORIGIN[0] + int(radius * math.cos(angle)), ORIGIN[1] + int(radius * math.sin(angle))))
        if node is not None and world.standable[node]:
            return node
        radius -= 1
    raise ValueError("no tile to stand on")


def steps_to(lengths: np.ndarray, targets: list[int]) -> float:
    return float(min(lengths[targets])) if targets else float("inf")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--teleports", type=int, default=200, help="the most teleports to see every layout")
    parser.add_argument("--repeats", type=int, default=2, help="landings wanted on each place")
    args = parser.parse_args()
    x0, y0, x1, y1 = BOX
    with BridgeClient(timeout=600) as c:
        old_ms = c.set_tick_ms(50)
        try:
            part = c.debug_collision(x0, y0, x1, y1, 0, objects=[*OBSTACLES, *RIFTS.values()])
            uid = c.spawn()["uid"]
            layouts: dict[int, dict[int, str]] = {}  # segment -> place -> kind ("blocked" for the landing's)
            landings: dict[int, int] = {}  # segment -> landings seen
            angles: dict[int, float] = {}
            try:
                c.debug_set_levels(uid, {"hitpoints": 99, "defence": 99})
                for n in range(args.teleports):
                    c.debug_teleport(uid, *MAGE_TILE[:2])
                    c.wait(2)
                    _, _, s = teleport(c, uid)
                    seen = places(c, uid)
                    for i, p in seen.items():
                        angles.setdefault(i, p["angle"])
                    if len(angles) < 12 or len(seen) != 11:
                        continue
                    here = landing_place(seen, angles, polar(*xy(s))[1])
                    layout = {**{i: p["kind"] for i, p in seen.items()}, here: "blocked"}
                    # the segment the layout follows: the one whose blocked place this is (the landing tile's angle
                    # can stray over a boundary from the teleport's own)
                    v = segment(angles[here])
                    if v in layouts and layouts[v] != layout:
                        raise RuntimeError(f"segment {v}: two layouts seen")
                    layouts[v] = layout
                    landings[v] = landings.get(v, 0) + 1
                    c.debug_set_levels(uid, {"hitpoints": 99})  # heal: the outer ring's monsters attack
                    if len(layouts) == 12 and min(landings.values()) >= args.repeats:
                        break
                print(f"{n + 1} teleports: landings by segment {dict(sorted(landings.items()))}")
            finally:
                c.despawn(uid)
        finally:
            c.set_tick_ms(old_ms)
    if len(layouts) < 12:
        raise RuntimeError(f"only {len(layouts)} of 12 segments seen")
    flags = np.array(part["flags"], dtype=np.int64).astype(np.int32).reshape(y1 - y0 + 1, x1 - x0 + 1)
    world = Map(flags, (x0, y0), [])
    objects = {o["id"]: o for o in part["objects"]}
    places_ = {i: {"tile": (objects[i]["x"], objects[i]["y"]), "size": (objects[i]["size_x"], objects[i]["size_y"])}
               for i in OBSTACLES}
    rifts = {rune: {"id": i, "tile": (objects[i]["x"], objects[i]["y"]),
                    "size": (objects[i]["size_x"], objects[i]["size_y"])} for rune, i in RIFTS.items()}
    near = {i: beside(world, p["tile"], p["size"]) for i, p in places_.items()}
    near_rift = {rune: beside(world, r["tile"], r["size"]) for rune, r in rifts.items()}
    outer: dict[int, dict[int, float]] = {}
    for v in range(12):
        centre = 30 * ((9 - v) % 12)  # getSegment's inverse: the segment's middle angle
        rows = []
        for a in range(-15, 15):
            lengths = world.lengths(drawn_in(world, OUTER_RADIUS, math.radians((centre + a + 0.5) % 360)))
            rows.append([steps_to(lengths, near[i]) for i in OBSTACLES])
        outer[v] = {i: round(float(m), 2) for i, m in zip(OBSTACLES, np.mean(rows, axis=0))}
    inner_tiles, inner = {}, {}
    for i, p in places_.items():
        r, a = polar(*p["tile"])
        node = drawn_in(world, r - INNER_STEPS, math.radians(a))
        inner_tiles[i] = world.tile(node)[:2]
        lengths = world.lengths(node)
        inner[i] = {rune: steps_to(lengths, near_rift[rune]) for rune in RIFTS}
    out = {"box": BOX, "places": places_, "rifts": rifts, "layouts": layouts, "landings": landings,
           "outer_steps": outer, "inner_tiles": inner_tiles, "inner_steps": inner}
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "collision.npz", flags=flags, origin=np.array([x0, y0]))
    (OUT / "abyss.json").write_text(json.dumps(out, indent=1, default=lambda o: list(o) if isinstance(o, tuple)
                                               else str(o)))
    print(f"saved {OUT.relative_to(REPO)}")
    for v in range(12):
        print(v, {layouts[v][i][:3]: outer[v][i] for i in OBSTACLES if layouts[v][i] != "blocked"})
    for i in OBSTACLES:
        print(i, inner_tiles[i], inner[i])


if __name__ == "__main__":
    main()
