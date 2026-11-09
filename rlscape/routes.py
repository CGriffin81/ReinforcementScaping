"""Walking routes over the server's own collision map (Caleb, 2026-11-01: a collision map and a planner).

The map is scripts/export_collision.py's: each surface tile's collision flags (RegionManager.getClippingFlag) over the
box the sim travels in, and the doors and gates there. A step goes to one of the 8 neighbouring tiles when the server's
pathfinder allows it for a size-1 mover (SmartPathfinder.checkSingleTraversal: the target tile's flags, and for a
diagonal the two tiles beside it, masked per direction). Every step is a tile, diagonal or not, so a route's length
in steps is what the server walks. A closed door or gate is a step too, through the wall it stands in, costing
DOOR_STEPS more for opening it; the Al Kharid toll gate and locked doors aren't (rlscape.sim.movement has the toll).
Some scenery is crossed by its own handler (CROSSINGS: the Wilderness ditch, the Gnome Stronghold's gate, the Grand
Tree's doors): a crossing joins the two tiles the handler moves the character between, costing its steps across plus
its extra steps.

`route(a, b)` is the shortest walk between two surface tiles (for the server walker and calibration).

The sim asks for walk lengths between any two tiles (`planned_steps`). A walk starts and ends at a tile's anchor: the
tile itself, or the nearest one a character can stand on (a tree's or a rock's tile is the object's, a fishing spot's
is water); a tile upstairs or underground is anchored at the surface tile it lies over or under (the dungeons sit
UNDERGROUND_Y_OFFSET tiles north), and the stairs or ladders are counted apart (rlscape.travel). Between the places the
sim travels (data/travel/places.csv) the lengths are a table, built once (a search from each place) and kept in
data/travel/places.npz; from any other tile, the search runs when it's first asked for and is remembered.
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
# Scenery a route crosses other than by a door, by id: the server's handler and the extra steps it costs (to calibrate)
CROSSINGS = {
    23271: ("Wilderness ditch", 2),  # WildernessInterfacePlugin.handleDitch: a jump from one tile before it to two past
    190: ("Gnome Stronghold gate", 2),  # GnomeStrongholdPlugin.openGates: (2461, 3382) <-> (2461, 3385)
    1967: ("Grand Tree door", 2),  # GnomeStrongholdPlugin: two tiles through, north or south
    1968: ("Grand Tree door", 2),
    # The Crandor passage (Caleb, 2026-11-08, OQ-16 (a); Dragon Slayer complete): Karamja volcano's pot hole down,
    # the dungeon, its secret wall (DragonSlayerPlugin, 2606: open with the quest done), the rope up onto Crandor; back
    # by Crandor's hole. Underground, so one crossing from the rim to Crandor: its 89 steps across plus the climbs and
    # the wall (timed on the server: 77 and 83 ticks, clicked, in two of three runs each way)
    492: ("Crandor passage", 6),
}
# The Al Kharid toll gate, crossed paying (TollGateOptionPlugin, "pay-toll(10gp)"): only on the map for a walker that
# pays (toll_surface); the sim's walks route through it themselves (rlscape.sim.movement)
TOLL_GATE = {35549: ("Al Kharid toll gate", 0), 35551: ("Al Kharid toll gate", 0)}
UNDERGROUND_Y_OFFSET = 6400  # dungeons sit 6400 tiles north of the surface they lie under
ANCHOR_REACH = 6  # tiles to look for a tile to stand on around one that can't be stood on
UNREACHABLE = np.iinfo(np.uint16).max  # in the table: no walk between the two


class Map:
    """The surface's collision map as a graph of tiles: node r * width + c is tile (x0 + c, y0 + r)."""

    def __init__(self, flags: np.ndarray, origin: tuple[int, int], doors: list[dict[str, int | str]],
                 crossings: list[dict[str, int | str]] = ()):
        self.flags, (self.x0, self.y0) = flags.view(np.uint32), origin
        self.height, self.width = flags.shape
        self.doors, self.crossings = doors, list(crossings)
        self.door_edges: dict[tuple[int, int], dict[str, int | str]] = {}  # (node, node) -> the door between them
        self.crossing_edges: dict[tuple[int, int], dict[str, int | str]] = {}  # (node, node) -> what's crossed
        self.graph = self._graph()
        # a tile a character can stand on: nothing blocks it from every side, and it can be stepped off
        self.standable = ((self.flags & np.uint32(BLOCKS_TILE)) == 0).ravel() & (np.diff(self.graph.indptr) > 0)
        self._anchors: dict[tuple[int, int, int], int | None] = {}
        self._reverse: csr_matrix | None = None  # the graph with every edge turned round (lengths_to)

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
        cross_s, cross_t, cross_w = [], [], []
        for thing in self.crossings:
            for here, there in crossing_tiles(thing):
                a, b = self.node(here), self.node(there)
                if a is None or b is None:
                    continue
                extra = {**CROSSINGS, **TOLL_GATE}[int(thing["id"])][1]
                steps = max(abs(here[0] - there[0]), abs(here[1] - there[1])) + extra
                cross_s += [a, b]
                cross_t += [b, a]
                cross_w += [steps, steps]
                self.crossing_edges[a, b] = self.crossing_edges[b, a] = thing
        sources.append(np.array(cross_s, dtype=np.int64))
        targets.append(np.array(cross_t, dtype=np.int64))
        weights.append(np.array(cross_w, dtype=float))
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

    def crossing_between(self, a: tuple[int, ...], b: tuple[int, ...]) -> dict[str, int | str] | None:
        """The scenery a route's step from tile a to tile b crosses (CROSSINGS), if it's one."""
        return self.crossing_edges.get((self.node(a), self.node(b)))

    def anchor(self, tile: tuple[int, int, int]) -> int | None:
        """The node a walk to or from the tile starts or ends at (see the module's docstring); None off the map."""
        if tile in self._anchors:
            return self._anchors[tile]
        x, y = tile[0], tile[1] - UNDERGROUND_Y_OFFSET if tile[1] >= UNDERGROUND_Y_OFFSET else tile[1]
        found = None
        for r in range(ANCHOR_REACH + 1):
            ring = [(x + dx, y + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1) if max(abs(dx), abs(dy)) == r]
            found = next((n for n in map(self.node, ring) if n is not None and self.standable[n]), None)
            if found is not None:
                break
        self._anchors[tile] = found
        return found

    def lengths(self, node: int) -> np.ndarray:
        """The shortest walk from the node to every node, in steps (inf where there's none)."""
        return dijkstra(self.graph, indices=node)

    def lengths_to(self, node: int) -> np.ndarray:
        """The shortest walk from every node to this one, in steps (inf where there's none): a search on the reversed
        graph. The graph is directed (a wall flagged on one side, a one-way crossing), so this isn't `lengths`."""
        if self._reverse is None:
            self._reverse = self.graph.transpose().tocsr()
        return dijkstra(self._reverse, indices=node)

    def steps(self, a: tuple[int, ...], b: tuple[int, ...]) -> float:
        """The length of the shortest walk from a to b in steps (doors included), or inf."""
        start, end = self.node(a), self.node(b)
        if start is None or end is None:
            return float("inf")
        return float(dijkstra(self.graph, indices=start)[end])


def crossing_tiles(thing: dict[str, int | str]) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """The pairs of tiles a crossing joins, as its handler moves the character (CROSSINGS)."""
    x, y, rotation = int(thing["x"]), int(thing["y"]), int(thing["rotation"])
    sx = int(thing["size_x"])  # the ditch pieces and doors run along x (rotated ones: their own length)
    match int(thing["id"]):
        case 23271:  # the ditch: from one tile before it to two past it, across its length
            if rotation % 2 == 0:
                return [((x + i, y - 1), (x + i, y + 2)) for i in range(sx)]
            return [((x + 2, y + i), (x - 1, y + i)) for i in range(sx)]
        case 190:  # the Stronghold's gate: GnomeStrongholdPlugin.openGates' two tiles
            return [((2461, 3382), (2461, 3385))]
        case 1967 | 1968:  # the Grand Tree's doors: two tiles north or south
            return [((x + i, y - 1), (x + i, y + 1)) for i in range(sx)]
        case 35549 | 35551:  # the toll gate's halves: their wall is on the tile's west side
            return [((x - 1, y), (x, y))]
        case 492:  # the Crandor passage: the volcano's rim (KaramjaListeners.VOLCANO_RIM) and Crandor's landing
            return [((2856, 3167), (2834, 3258))]
    return []


def _rows(name: str) -> list[dict[str, int | str]]:
    path = DATA / name
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [{k: v if k == "name" else int(v) for k, v in row.items()} for row in csv.DictReader(f)]


@cache
def toll_surface() -> Map:
    """The surface map with the toll gate crossable, for a walker that pays the toll."""
    data = np.load(DATA / "collision.npz")
    gate = [{**door, "size_x": 1, "size_y": 1} for door in _rows("doors.csv") if door["id"] in TOLL_GATE]
    return Map(data["flags"], tuple(int(v) for v in data["origin"]), _rows("doors.csv"),
               _rows("crossings.csv") + gate)


@cache
def surface() -> Map:
    """The exported surface map (data/travel)."""
    data = np.load(DATA / "collision.npz")
    return Map(data["flags"], tuple(int(v) for v in data["origin"]), _rows("doors.csv"), _rows("crossings.csv"))


def beside(world: Map, tile: tuple[int, int], size: tuple[int, int]) -> list[int]:
    """The nodes next to a footprint's sides (not its corners) that a character can stand on."""
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


@cache
def abyss_map() -> Map:
    """The Abyss's map (data/abyss, scripts/export_abyss.py): map region (47, 75), closed to the surface's."""
    data = np.load(DATA.parent / "abyss" / "collision.npz")
    return Map(data["flags"], tuple(int(v) for v in data["origin"]), [])


class Places:
    """Planned walk lengths between anchors: the places' table, and searches from other tiles as they come."""

    def __init__(self, world: Map, nodes: np.ndarray, table: np.ndarray):
        self.world, self.nodes, self.table = world, nodes, table
        self.index = {int(n): i for i, n in enumerate(nodes)}
        self.rows: dict[int, np.ndarray] = {}  # a node off the table: the walks from it to the table's places
        self.columns: dict[int, np.ndarray] = {}  # a node off the table: the walks from the table's places to it
        self.pairs: dict[tuple[int, int], float] = {}  # (a, b), both off the table: the walk from a to b
        self.searches = 0

    def _search(self, node: int) -> np.ndarray:
        self.searches += 1
        return dijkstra(self.world.graph, indices=node)

    def row(self, node: int) -> np.ndarray:
        """The planned lengths from a node to every place in the table (inf where there's no walk)."""
        i = self.index.get(node)
        if i is not None:
            return np.where(self.table[i] == UNREACHABLE, np.inf, self.table[i].astype(float))
        if node not in self.rows:
            self.rows[node] = self._search(node)[self.nodes]
        return self.rows[node]

    def steps(self, a: int, b: int) -> float:
        """The planned length of the walk from node a to node b, in steps; inf if there's no walk. The graph is
        directed (a wall flagged on one side, a one-way crossing: 834,294 of its 5.1M edges), so a walk's length can
        depend on its direction, and each is searched from its own start: the same in any process, whatever was asked
        before (Caleb, 2026-11-09, OQ-64 (a); the pairs were cached both ways under the first one asked)."""
        if a == b:
            return 0.0
        i, j = self.index.get(a), self.index.get(b)
        if i is not None and j is not None:
            value = self.table[i, j]  # row i: the search from place i
            return float("inf") if value == UNREACHABLE else float(value)
        if i is None and j is None:
            if (a, b) not in self.pairs:
                dist = self._search(a)
                self.rows.setdefault(a, dist[self.nodes])
                self.pairs[(a, b)] = float(dist[b])
            return self.pairs[(a, b)]
        if i is None:  # off the table to a place: the search from a
            if a not in self.rows:
                self.rows[a] = self._search(a)[self.nodes]
            return float(self.rows[a][j])
        if b not in self.columns:  # a place to a node off the table: the search to b, on the reversed graph
            self.searches += 1
            self.columns[b] = self.world.lengths_to(b)[self.nodes]
        return float(self.columns[b][i])


def build_table(world: Map, nodes: np.ndarray, batch: int = 8) -> np.ndarray:
    """Planned lengths between every pair of the nodes (one search from each), as uint16 steps."""
    table = np.full((len(nodes), len(nodes)), UNREACHABLE, dtype=np.uint16)
    for start in range(0, len(nodes), batch):
        dist = dijkstra(world.graph, indices=nodes[start:start + batch])[:, nodes]
        table[start:start + batch] = np.where(np.isfinite(dist), np.minimum(dist, UNREACHABLE - 1), UNREACHABLE)
    return table


def place_tiles() -> list[tuple[int, int, int]]:
    """The places the sim travels between (scripts/build_travel_places.py)."""
    path = DATA / "places.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [(int(r["x"]), int(r["y"]), int(r["z"])) for r in csv.DictReader(f)]


@cache
def places() -> Places:
    """The places' table: data/travel/places.npz if it was built from the same places and map, else built now (a few
    minutes) and saved there."""
    world = surface()
    nodes = np.array(sorted({n for n in map(world.anchor, place_tiles()) if n is not None}), dtype=np.int64)
    key = np.array([len(nodes), int(nodes.sum()) if len(nodes) else 0, world.graph.nnz, DOOR_STEPS], dtype=np.int64)
    cached = DATA / "places.npz"
    if cached.exists():
        data = np.load(cached)
        if np.array_equal(data["key"], key) and np.array_equal(data["nodes"], nodes):
            return Places(world, nodes, data["table"])
    table = build_table(world, nodes)
    np.savez_compressed(cached, key=key, nodes=nodes, table=table)
    return Places(world, nodes, table)


def planned_steps(a: tuple[int, int, int], b: tuple[int, int, int]) -> float | None:
    """The planned walk from tile a to tile b in steps, between their anchors (stairs and ladders apart); inf if
    there's no walk on foot (an island: boats), None if either is off the map."""
    world = surface()
    na, nb = world.anchor(a), world.anchor(b)
    if na is None or nb is None:
        return None
    return places().steps(na, nb)
