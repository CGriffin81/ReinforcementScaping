"""Travel time between tiles, shared by every option that walks somewhere (gathering sites, combat sites, banks).

A walk's length is the planned route's on the server's collision map (rlscape.routes; Caleb, 2026-11-01), in steps,
plus a fixed cost per change of plane or between the surface and a dungeon. Off the planner's map, or where no walk
on foot joins the two but some way does (a boat or a teleport: rlscape.sim.movement finds which, if the character
can use one), it's the straight-line distance times PATH_DETOUR, as before. A place no way the model knows reaches
at all is unreachable (Caleb, 2026-11-01): its walks are infinite. `unplanned` counts all of those. A walk also loses ticks beyond its steps, measured on the server
(scripts/calibrate_travel.py): starting it (WALK_START_TICKS) and pauses on the way (WALK_PAUSE_TICKS a step).

The simulator's walks turn that path into ticks with run energy and weight (rlscape.sim.energy); `travel_ticks` uses
an assumed average speed instead, for estimates that don't know the character (ranking fights, picking the nearest
spot).
"""

from __future__ import annotations

from collections import Counter
from functools import cache
from math import inf, isfinite

import numpy as np
from scipy.sparse.csgraph import connected_components, dijkstra

from rlscape.gamedata.transports import GATE_NORTH, GATE_SOUTH, HOME, HOME_TICKS, Transport, transports, wilderness_level
from rlscape.routes import UNDERGROUND_Y_OFFSET, places, planned_steps, surface

RUN_TILES_PER_TICK = 1.5  # average speed for estimates: running, with run energy running out now and then
PATH_DETOUR = 1.3  # off the planner's map: walking paths are longer than straight lines
LEVEL_CHANGE_TICKS = 12  # stairs or ladders, per change of plane or underground
BANKING_TICKS = 8  # opening a booth and depositing (measured: 7 from the click, scripts/calibrate_travel.py)
# Measured on 12 site-to-bank walks of 15 to 166 steps, running (2026-11-01): ticks = steps / 2 + 2.3 + 0.083 x steps
WALK_START_TICKS = 2.3  # the first click handled and the first step taken
WALK_PAUSE_TICKS = 0.083  # a step: a standing tick about every 18, and odd-length hops between clicks
unplanned: Counter[str] = Counter()  # walks (pairs of tiles) the planner couldn't give: "off the map", "no walk", "no way"


def _surface(x: int, y: int) -> tuple[int, int, bool]:
    if y >= UNDERGROUND_Y_OFFSET:
        return x, y - UNDERGROUND_Y_OFFSET, True
    return x, y, False


def _straight(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    ax, ay, _ = _surface(a[0], a[1])
    bx, by, _ = _surface(b[0], b[1])
    return max(abs(ax - bx), abs(ay - by)) * PATH_DETOUR


def projected(tile: tuple[int, int, int]) -> bool:
    """Upstairs or underground: anchored at the surface tile it lies over or under, its stairs or ladders unmapped."""
    return tile[2] > 0 or tile[1] >= UNDERGROUND_Y_OFFSET


def _closure(starts: set[int | None], buys_pass: bool, reached: np.ndarray | None = None) -> np.ndarray:
    """Per node of the planner's map: whether a walk from one of `starts` gets there, through the Shantay gate too
    (going south needs a pass, `buys_pass`; leaving is free), added to `reached`."""
    world = surface()
    reached = np.zeros(world.graph.shape[0], dtype=bool) if reached is None else reached.copy()
    north, south = world.anchor(GATE_NORTH), world.anchor(GATE_SOUTH)
    while starts := {n for n in starts if n is not None and not reached[n]}:
        reached |= np.isfinite(dijkstra(world.graph, indices=sorted(starts), min_only=True))
        starts = {north} if reached[south] else set()
        if buys_pass and reached[north]:
            starts.add(south)
    return reached


def _landings(boats: tuple[Transport, ...], reached: np.ndarray) -> set[int | None]:
    world = surface()
    return {world.anchor(b.land or b.end) for b in boats if (n := world.anchor(b.start)) is not None and reached[n]}


@cache
def _reached() -> np.ndarray:
    """Per node of the planner's map: whether some way the model knows gets there from Lumbridge, for a character
    that could use any of them: walking and the crossings, the Shantay gate, every teleport, and every boat from where
    those reach, until no more do."""
    world = surface()
    boats = tuple(t for t in transports() if t.start is not None)
    starts = {world.anchor(HOME)} | {world.anchor(t.end) for t in transports() if t.start is None}
    reached = _closure(starts, True)
    while more := _landings(boats, reached):
        grown = _closure(more, True, reached)
        if np.array_equal(grown, reached):
            break
        reached = grown
    return reached


def has_a_way(tile: tuple[int, int, int]) -> bool:
    """Whether any way the model knows gets there from Lumbridge, for some character (Caleb, 2026-11-01: a place
    with really no way there is unreachable). Off the planner's map, upstairs or underground, it's taken as yes."""
    node = None if projected(tile) else surface().anchor(tile)
    return node is None or bool(_reached()[node])


@cache
def _strong() -> np.ndarray:
    """Each node's strongly connected part of the planner's map: from anywhere in one, a walk reaches the same."""
    return connected_components(surface().graph, directed=True, connection="strong")[1]


def _bits(packed: np.ndarray, nodes: np.ndarray | int) -> np.ndarray | int:
    """The nodes' bits in a mask packed with np.packbits."""
    return (packed[nodes >> 3] >> (7 - (nodes & 7))) & 1


_CLOSURES: dict[tuple[int, bool], np.ndarray] = {}


def _closure_of(nodes: set[int | None], buys_pass: bool) -> np.ndarray:
    """_closure from any of `nodes`, packed into bits: the union of each one's, remembered per strongly connected part
    of the map it's in (a walk from anywhere in a part reaches the same), so the few parts characters start from cost
    a search each once."""
    out = np.zeros((surface().graph.shape[0] + 7) // 8, dtype=np.uint8)
    for node in nodes - {None}:
        key = (int(_strong()[node]), buys_pass)
        if key not in _CLOSURES:
            if len(_CLOSURES) >= 256:
                _CLOSURES.clear()
            _CLOSURES[key] = np.packbits(_closure({node}, buys_pass))
        out |= _CLOSURES[key]
    return out


class Reach:
    """Where a character can get to now, as rlscape.sim.movement.route goes: a walk from where it is or from where a
    teleport it can use lands, then at most one boat it can take, and the walks on (with the Shantay gate). Upstairs,
    underground and off the planner's map are taken as reachable, as in has_a_way. Without a mask: every place some
    way reaches (has_a_way)."""

    def __init__(self, packed: np.ndarray | None = None):
        self.packed = packed  # per node, packed into bits

    def allows(self, tile: tuple[int, int, int]) -> bool:
        node = None if projected(tile) else surface().anchor(tile)
        if node is None:
            return True
        return bool(_reached()[node] if self.packed is None else _bits(self.packed, node))

    def allows_nodes(self, nodes: np.ndarray) -> np.ndarray:
        """`allows` for many tiles' anchors at once (-1: projected or off the map)."""
        out, on = np.ones(len(nodes), dtype=bool), nodes >= 0
        out[on] = _reached()[nodes[on]] if self.packed is None else _bits(self.packed, nodes[on])
        return out


EVERYWHERE = Reach()
_REACH: dict[tuple, Reach] = {}


def reach(origin: tuple[int, int, int], teleport_ends: tuple[tuple[int, int, int], ...],
          boats: tuple[Transport, ...], buys_pass: bool) -> Reach:
    """Where a character at `origin` can get to with the teleports (their landings) and boats it can use, and whether
    it can buy a Shantay pass; remembered per part of the map it stands in and what it can use."""
    world = surface()
    node = None if projected(origin) else world.anchor(origin)
    if node is None:
        return EVERYWHERE  # upstairs, underground or off the map: as its walks (rlscape.sim.movement.route)
    key = (int(_strong()[node]), teleport_ends, tuple(b.id for b in boats), buys_pass)
    if key not in _REACH:
        if len(_REACH) >= 256:
            _REACH.clear()
        first = _closure_of({node} | {world.anchor(end) for end in teleport_ends}, buys_pass)
        landings = {world.anchor(b.land or b.end) for b in boats
                    if (n := world.anchor(b.start)) is not None and _bits(first, n)}
        _REACH[key] = Reach(first | _closure_of(landings, buys_pass))
    return _REACH[key]


def level_changes(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return (a[2] != b[2]) + (_surface(a[0], a[1])[2] != _surface(b[0], b[1])[2])


def path(a: tuple[int, int, int], b: tuple[int, int, int]) -> tuple[float, int]:
    """The walk from tile a to tile b: its length in steps (the planned route, or the straight-line estimate off the
    planner's map) and its changes of level (stairs and ladders). Remembered: the sim asks for the same walks often."""
    return _path(tuple(int(v) for v in a), tuple(int(v) for v in b))[:2]


def on_foot(a: tuple[int, int, int], b: tuple[int, int, int]) -> bool:
    """Whether a walk joins the two: planned, or off the planner's map (taken as walkable); not across water or into a
    quest-locked area (then only a boat or a teleport gets there, or nothing)."""
    return _path(tuple(int(v) for v in a), tuple(int(v) for v in b))[2]


@cache
def _path(a: tuple[int, int, int], b: tuple[int, int, int]) -> tuple[float, int, bool]:
    steps = planned_steps(a, b)
    walkable = steps is None or isfinite(steps)
    if steps is None or not isfinite(steps):
        steps = _unwalked(a, b)
        walkable &= isfinite(steps)  # off the map, but to a place with no way: no walk either
        unplanned["no way" if not isfinite(steps) else "off the map" if walkable else "no walk"] += 1  # each pair once
    return steps, level_changes(a, b), walkable


def _unwalked(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """The steps estimated where the planner has no walk: the straight line if some way joins the two, else none."""
    return _straight(a, b) if has_a_way(a) and has_a_way(b) else inf


def overhead(tiles: float) -> float:
    """The ticks a walk of `tiles` steps takes beyond its steps (measured): starting it, and pauses on the way."""
    return WALK_START_TICKS + WALK_PAUSE_TICKS * tiles if tiles > 0 else 0.0


def _walk_ticks(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    tiles, changes = path(a, b)
    return tiles / RUN_TILES_PER_TICK + overhead(tiles) + changes * LEVEL_CHANGE_TICKS


def travel_ticks(a: tuple[int, int, int], b: tuple[int, int, int], home: bool = False) -> float:
    """Estimated ticks to get from tile a to tile b at the average speed, stairs and ladders included: walking, or,
    if `home` (the home teleport is ready: rlscape.sim.transport.home_ready), the home teleport (not from deep in
    the Wilderness) and walking from Lumbridge, whichever is faster. Trips an option repeats (bank trips) walk: the
    teleport is ready only once every 30 minutes. Other transports depend on what the character holds, so only its
    walks (rlscape.sim.movement) count them."""
    walk = _walk_ticks(a, b)
    if not home or wilderness_level(a) > 20:
        return walk
    return min(walk, HOME_TICKS + _walk_ticks(HOME, b))


def travel_ticks_from_many(sources: list[tuple[int, int, int]], target: tuple[int, int, int]) -> np.ndarray:
    """`travel_ticks` from each of many tiles to one, from a single search from the target (walks are taken as the
    same both ways, as the table takes them): for the combat pool's spawns, most of which aren't places."""
    world = surface()
    node = world.anchor(target)
    lengths = world.lengths(node) if node is not None else None
    out = np.empty(len(sources))
    for i, source in enumerate(sources):
        n = world.anchor(source)
        steps = float(lengths[n]) if lengths is not None and n is not None else inf
        if not isfinite(steps):
            steps = _unwalked(source, target)
        out[i] = steps / RUN_TILES_PER_TICK + overhead(steps) + level_changes(source, target) * LEVEL_CHANGE_TICKS
    return out


class Destinations:
    """`travel_ticks` from one tile to many fixed ones at once (the combat ranker's sites), from the same planned
    lengths, so it gives exactly what `travel_ticks` would."""

    def __init__(self, tiles: list[tuple[int, int, int]]):
        world, table = surface(), places()
        self.tiles = tiles
        self.plane = np.array([t[2] for t in tiles])
        self.under = np.array([t[1] >= UNDERGROUND_Y_OFFSET for t in tiles])
        anchors = [world.anchor(t) for t in tiles]
        self.column = np.array([table.index.get(n, -1) if n is not None else -1 for n in anchors])
        self.planned = self.column >= 0  # elsewhere: travel_ticks one by one (rare: off the map, or off the table)
        self.nodes = np.array([n if n is not None and not projected(t) else -1 for n, t in zip(anchors, tiles)])
        self.home = HOME_TICKS + self._walking(HOME)  # the home teleport, then the walk

    def reachable(self, reach: Reach) -> np.ndarray:
        """Per tile: whether the character can get there (Reach.allows)."""
        return reach.allows_nodes(self.nodes)

    def ticks_from(self, origin: tuple[int, int, int], home: bool = False) -> np.ndarray:
        walk = self._walking(origin)
        return walk if not home or wilderness_level(origin) > 20 else np.minimum(walk, self.home)

    def _walking(self, origin: tuple[int, int, int]) -> np.ndarray:
        world, table = surface(), places()
        node = world.anchor(origin)
        out = np.empty(len(self.tiles))
        planned = np.zeros(len(self.tiles), dtype=bool)
        if node is not None and self.planned.any():
            steps = np.full(len(self.tiles), np.inf)
            steps[self.planned] = table.row(node)[self.column[self.planned]]
            planned = np.isfinite(steps)
            tiles = steps[planned]
            changes = ((self.plane[planned] != origin[2]).astype(int)
                       + (self.under[planned] != (origin[1] >= UNDERGROUND_Y_OFFSET)).astype(int))
            out[planned] = tiles / RUN_TILES_PER_TICK + np.where(tiles > 0, WALK_START_TICKS + WALK_PAUSE_TICKS * tiles,
                                                                 0.0) + changes * LEVEL_CHANGE_TICKS
        for i in np.flatnonzero(~planned):
            out[i] = _walk_ticks(origin, self.tiles[i])
        return out
