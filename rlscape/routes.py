"""Walking routes over the server's own collision map (Caleb, 2026-11-01: a collision map and a planner).

The map is scripts/export_collision.py's: each surface tile's collision flags (RegionManager.getClippingFlag) over the
box the sim travels in, and the doors and gates there. A step goes to one of the 8 neighbouring tiles when the server's
pathfinder allows it for a size-1 mover (SmartPathfinder.checkSingleTraversal: the target tile's flags, and for a
diagonal the two tiles beside it, masked per direction). Every step is a tile, diagonal or not, so a route's length
in steps is what the server walks. A closed door or gate is a step too, through the wall it stands in, costing
DOOR_STEPS more for opening it; the Al Kharid toll gate and locked doors aren't (rlscape.sim.movement has the toll).

`route(a, b)` is the shortest walk between two surface tiles (for the server walker and calibration).
"""

from __future__ import annotations

import csv
from functools import cache
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

DATA = Path(__file__).resolve().parent.parent / "data" / "travel"
DOOR_STEPS = 2  # opening a door, in steps of walking; to calibrate
# SmartPathfinder.checkSingleTraversal's masks, by the step's direction (dx, dy): the target tile's flags
STEP_MASKS = {(0, -1): 0x12C0102, (-1, 0): 0x12C0108, (0, 1): 0x12C0120, (1, 0): 0x12C0180,
              (-1, -1): 0x12C010E, (-1, 1): 0x12C0138, (1, -1): 0x12C0183, (1, 1): 0x12C01E0}
BLOCKS_TILE = 0x12C0100  # the flags that block a tile from every side (scenery, floor), not just walls
# Doors a route can't count on opening: the toll gate (paid; rlscape.sim.movement) and locked ones
NOT_OPENED = {"Prison Door", "Cell door"}
NOT_OPENED_IDS = {35549, 35551}  # the Al Kharid toll gate


class Map:
    """The surface's collision map as a graph of tiles: node r * width + c is tile (x0 + c, y0 + r)."""

    def __init__(self, flags: np.ndarray, origin: tuple[int, int], doors: list[dict[str, int | str]]):
        self.flags, (self.x0, self.y0) = flags.view(np.uint32), origin
        self.height, self.width = flags.shape
        self.doors = doors
        self.door_edges: dict[tuple[int, int], dict[str, int | str]] = {}  # (node, node) -> the door between them
        self.graph = self._graph()

    def node(self, tile: tuple[int, int, int] | tuple[int, int]) -> int | None:
        c, r = tile[0] - self.x0, tile[1] - self.y0
        return r * self.width + c if 0 <= c < self.width and 0 <= r < self.height else None

    def tile(self, node: int) -> tuple[int, int, int]:
        r, c = divmod(int(node), self.width)
        return self.x0 + c, self.y0 + r, 0

    def _graph(self) -> csr_matrix:
        f, h, w = self.flags, self.height, self.width
        open_to = {d: (f & np.uint32(m)) == 0 for d, m in STEP_MASKS.items()}  # entering each tile that way is allowed
        rows, cols = np.mgrid[0:h, 0:w]
        sources, targets, weights = [], [], []
        for (dx, dy), ok in open_to.items():
            # the target is (r + dy, c + dx); its own mask, and for a diagonal the two orthogonal tiles beside it
            r0, r1 = max(0, -dy), h - max(0, dy)
            c0, c1 = max(0, -dx), w - max(0, dx)
            allowed = ok[r0 + dy:r1 + dy, c0 + dx:c1 + dx].copy()
            if dx and dy:
                allowed &= open_to[(dx, 0)][r0:r1, c0 + dx:c1 + dx] & open_to[(0, dy)][r0 + dy:r1 + dy, c0:c1]
            src_r, src_c = rows[r0:r1, c0:c1][allowed], cols[r0:r1, c0:c1][allowed]
            sources.append(src_r * w + src_c)
            targets.append((src_r + dy) * w + src_c + dx)
            weights.append(np.ones(len(src_r)))
        door_s, door_t = [], []
        for door in self.doors:
            if door["name"] in NOT_OPENED or door["id"] in NOT_OPENED_IDS or door["type"] != 0:
                continue
            x, y = door["x"], door["y"]
            other = {0: (x - 1, y), 1: (x, y + 1), 2: (x + 1, y), 3: (x, y - 1)}[door["rotation"]]
            a, b = self.node((x, y)), self.node(other)
            if a is None or b is None or self.flags.flat[a] & BLOCKS_TILE or self.flags.flat[b] & BLOCKS_TILE:
                continue
            door_s += [a, b]
            door_t += [b, a]
            self.door_edges[a, b] = self.door_edges[b, a] = door
        sources.append(np.array(door_s, dtype=np.int64))
        targets.append(np.array(door_t, dtype=np.int64))
        weights.append(np.full(len(door_s), 1.0 + DOOR_STEPS))
        n = h * w
        return csr_matrix((np.concatenate(weights), (np.concatenate(sources), np.concatenate(targets))), shape=(n, n))

    def route(self, a: tuple[int, ...], b: tuple[int, ...]) -> list[tuple[int, int, int]] | None:
        """The shortest walk from tile a to tile b (both on the surface, in the map), a's tile first; None if b can't
        be walked to."""
        start, end = self.node(a), self.node(b)
        if start is None or end is None:
            return None
        dist, pred = dijkstra(self.graph, indices=start, return_predecessors=True)
        if not np.isfinite(dist[end]):
            return None
        out = [end]
        while out[-1] != start:
            out.append(pred[out[-1]])
        return [self.tile(n) for n in reversed(out)]

    def door_between(self, a: tuple[int, ...], b: tuple[int, ...]) -> dict[str, int | str] | None:
        """The door a route's step from tile a to tile b goes through, if it's one."""
        return self.door_edges.get((self.node(a), self.node(b)))

    def steps(self, a: tuple[int, ...], b: tuple[int, ...]) -> float:
        """The length of the shortest walk from a to b in steps (doors included), or inf."""
        start, end = self.node(a), self.node(b)
        if start is None or end is None:
            return float("inf")
        return float(dijkstra(self.graph, indices=start)[end])


@cache
def surface() -> Map:
    """The exported surface map (data/travel)."""
    data = np.load(DATA / "collision.npz")
    with open(DATA / "doors.csv", encoding="utf-8") as f:
        doors = [{k: v if k == "name" else int(v) for k, v in row.items()} for row in csv.DictReader(f)]
    return Map(data["flags"], tuple(int(v) for v in data["origin"]), doors)
