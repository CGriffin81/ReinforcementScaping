"""Walking between tiles, including the Al Kharid toll gate and the Shantay Pass. Every option that walks somewhere
goes through `walk`, which runs while run energy lasts (rlscape.sim.energy); `route_ticks` predicts the same walk
without making it, and `reachable` says whether it can be made at all.

The toll (TollGateOptionPlugin, BorderGuardDialogue): passing the gate between Lumbridge and Al Kharid takes 10
coins from the inventory, in either direction, unless Prince Ali Rescue is past stage 50 (counted here as complete).
The planned routes (rlscape.routes) never open the gate, so a walk between Al Kharid and west of its fence goes
round the fence's north end, as players did via the Al Kharid mine, unless going through the gate is shorter and the
toll is waived or can be paid from the inventory: then it pays and goes through. A character without coins is slower
but never stranded.

The Shantay Pass (ShantayPassPlugin, ShantayGuard, ShantayOptionPlugin): the desert south of the pass (DesertZone's
borders, dungeons under them included) is entered only through the gate, whose guard takes a Shantay pass going
south; going north is free. Shantay, by the gate, sells a pass for 5 coins ("buy-pass"). The sim buys one on the way
and hands it over, so a walk south needs 5 coins in the inventory; without them the desert is unreachable. The Al
Kharid toll on the way to the gate is paid only from coins beyond the pass's 5. Not modelled: the magic carpets, and
desert heat on the walk between the gate and a site (DesertZone: a hit of 1-7 every 116 ticks without water, so 0-1
hits on the way to the Bandit Camp or Pollnivneach, which are both heat-free).

The fence line is an estimate (it only decides whether the gate could shorten a walk); the gate rules are the
server's.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from math import ceil, inf

import numpy as np

from rlscape.gamedata.transports import ABYSS_EXIT, GATE_NORTH, GATE_SOUTH, Transport, in_abyss, wilderness_level
from rlscape.sim.energy import MAX_ENERGY, rest, restore_per_tick, walk_plan
from rlscape.sim.state import COINS, CharacterState
from rlscape.sim.transport import boats, can_use, home_ready, usable_teleports, use
from rlscape import travel
from rlscape.travel import LEVEL_CHANGE_TICKS, UNDERGROUND_Y_OFFSET, Reach, on_foot, overhead, path, projected

TOLL = 10
AL_KHARID = (3268, 2700, 3400, 3330)  # x1, y1, x2, y2: east of the Lumbridge-Al Kharid fence, south of its end
PASS_PRICE = 5  # ShantayOptionPlugin: "buy-pass" takes 5 coins for one Shantay pass
DESERT = (3063, 2725, 3544, 3115)  # DesertZone's borders: everything south of the Shantay Pass gate
SHANTAY_GATE = (2.0, 0)  # the leg through the gate: quick-pass moves 2 tiles
# The toll gate (scenery 35549 and 35551 at 3268, 3227-3228, its wall on their west side): the step through it
TOLL_WEST, TOLL_EAST = (3267, 3227, 0), (3268, 3227, 0)
TOLL_GATE = (1.0, 0)
GATES = (TOLL_WEST, TOLL_EAST, GATE_NORTH, GATE_SOUTH)  # tiles walks pass on the way (the planner's places)


def in_desert(tile: tuple[int, int, int]) -> bool:
    """South of the Shantay Pass: inside DesertZone's borders, or in a dungeon under them."""
    x, y = tile[0], tile[1] - UNDERGROUND_Y_OFFSET if tile[1] >= UNDERGROUND_Y_OFFSET else tile[1]
    x1, y1, x2, y2 = DESERT
    return x1 <= x <= x2 and y1 <= y <= y2


def _in_al_kharid(tile: tuple[int, int, int]) -> bool:
    x1, y1, x2, y2 = AL_KHARID
    return (tile[1] < UNDERGROUND_Y_OFFSET and x1 <= tile[0] <= x2 and y1 <= tile[1] <= y2
            and not in_desert(tile))


def _west_of_fence(tile: tuple[int, int, int]) -> bool:
    return (tile[1] < UNDERGROUND_Y_OFFSET and tile[0] < AL_KHARID[0] and tile[1] <= AL_KHARID[3]
            and not in_desert(tile))


def uses_toll_gate(a: tuple[int, int, int], b: tuple[int, int, int]) -> bool:
    return (_in_al_kharid(a) and _west_of_fence(b)) or (_in_al_kharid(b) and _west_of_fence(a))


def toll_exempt(state: CharacterState) -> bool:
    return "PRINCE_ALI_RESCUE" in state.progress.quests_complete


@dataclass(frozen=True)
class Route:
    legs: list[tuple[float, int]]
    toll: int = 0  # times it pays the Al Kharid toll
    shantay_pass: bool = False  # buys a Shantay pass and hands it to the guard
    transports: tuple[Transport, ...] = ()  # teleports and boats, in order
    on_foot: bool = True  # every leg is a walk (planned, or off the planner's map), none across water

    @property
    def fixed(self) -> float:
        """The transports' ticks, resting."""
        return float(sum(t.ticks for t in self.transports))

    @property
    def coins(self) -> int:
        return self.toll * TOLL + self.shantay_pass * PASS_PRICE + sum(t.coins for t in self.transports)

    def estimate(self) -> float:
        """Ticks at a run, for choosing between routes (a walk is timed with run energy by timed())."""
        tiles = sum(t for t, _ in self.legs)
        return tiles / 2 + overhead(tiles) + sum(c for _, c in self.legs) * LEVEL_CHANGE_TICKS + self.fixed


def _leg(a: tuple[int, int, int], b: tuple[int, int, int]) -> tuple[tuple[float, int], bool]:
    return path(a, b), on_foot(a, b)


def _al_kharid_route(state: CharacterState, a: tuple[int, int, int], b: tuple[int, int, int], coins: int) -> Route:
    """Through the toll gate if that's shorter and the toll is waived or can be paid from coins, otherwise the
    planned walk (round the fence, where it's in the way)."""
    leg, walkable = _leg(a, b)
    direct = Route([leg], on_foot=walkable)
    exempt = toll_exempt(state)
    if not uses_toll_gate(a, b) or (coins < TOLL and not exempt):
        return direct
    near, far = (TOLL_EAST, TOLL_WEST) if _in_al_kharid(a) else (TOLL_WEST, TOLL_EAST)
    (to_gate, ok_to), (from_gate, ok_from) = _leg(a, near), _leg(far, b)
    gate = Route([to_gate, TOLL_GATE, from_gate], toll=int(not exempt), on_foot=ok_to and ok_from)
    return gate if sum(t for t, _ in gate.legs) < sum(t for t, _ in direct.legs) else direct


def _walking(state: CharacterState, a: tuple[int, int, int], destination: tuple[int, int, int],
             coins: int) -> Route | None:
    """The walk on foot from a, with the toll and the Shantay Pass; None if it can't be made (no coins for a
    pass)."""
    if in_desert(a) == in_desert(destination):
        return _al_kharid_route(state, a, destination, coins)
    if in_desert(a):  # leaving the desert: the gate is free going north
        north = _al_kharid_route(state, GATE_NORTH, destination, coins)
        leg, walkable = _leg(a, GATE_SOUTH)
        return Route([leg, SHANTAY_GATE, *north.legs], toll=north.toll, on_foot=walkable and north.on_foot)
    if coins < PASS_PRICE:
        return None
    north = _al_kharid_route(state, a, GATE_NORTH, coins - PASS_PRICE)
    leg, walkable = _leg(GATE_SOUTH, destination)
    return Route([*north.legs, SHANTAY_GATE, leg], toll=north.toll, shantay_pass=True,
                 on_foot=walkable and north.on_foot)


def _then(first: Route, transport: Transport, after: Route) -> Route:
    return Route([*first.legs, *after.legs], first.toll + after.toll, first.shantay_pass or after.shantay_pass,
                 (*first.transports, transport, *after.transports), first.on_foot and after.on_foot)


def _landing(transport: Transport) -> tuple[int, int, int]:
    """Where the walk on starts: a boat's dock, off the gangplank (in the boat's ticks), or where a teleport lands."""
    return transport.land or transport.end


def _surface_xy(tile: tuple[int, int, int]) -> tuple[int, int]:
    return tile[0], tile[1] - UNDERGROUND_Y_OFFSET if tile[1] >= UNDERGROUND_Y_OFFSET else tile[1]


@cache
def _boat_arrays() -> tuple[np.ndarray, ...]:
    """The boats' boarding and landing tiles (surface x, y), ticks and fares, for bounding many at once."""
    rows = [(*_surface_xy(b.start), *_surface_xy(_landing(b)), b.ticks, b.coins) for b in boats()]
    return tuple(np.array(column, dtype=float) for column in zip(*rows))


def _by_transport(state: CharacterState, a: tuple[int, int, int], destination: tuple[int, int, int], coins: int,
                  best: float, home: bool) -> Route | None:
    """The fastest way there with a teleport, a boat, or a teleport and then a boat, if faster than best ticks;
    `home`: the home teleport is ready. Each alternative is first bounded from below by straight lines (a planned
    walk is never shorter), which skips most of them without looking a walk up."""
    found = None
    dx, dy = _surface_xy(destination)
    depth = wilderness_level(a)
    usable = [t for t in usable_teleports(state) if depth <= t.wilderness_limit and (home or t.kind != "home")]
    if in_abyss(a):  # out of the Abyss: its exit, as a teleport from there (rlscape.gamedata.transports)
        usable.append(ABYSS_EXIT)
    starts = [(Route([]), a)] + [(Route([], transports=(t,)), t.end) for t in usable if t.ticks < best]
    for tele in usable:
        ex, ey = _surface_xy(tele.end)
        if tele.ticks + max(abs(ex - dx), abs(ey - dy)) / 2 >= best:
            continue
        after = _walking(state, tele.end, destination, coins)
        if after is not None and after.on_foot:
            option = _then(Route([]), tele, after)
            if option.estimate() < best:
                found, best = option, option.estimate()
    start_x, start_y, land_x, land_y, ticks, fares = _boat_arrays()
    from_land = np.maximum(np.abs(land_x - dx), np.abs(land_y - dy))
    for start, here in starts:
        hx, hy = _surface_xy(here)
        bound = start.fixed + (np.maximum(np.abs(start_x - hx), np.abs(start_y - hy)) + from_land) / 2 + ticks
        for i in np.flatnonzero((bound < best) & (fares <= coins - start.coins)):
            boat = boats()[i]
            if bound[i] >= best or not can_use(state, boat, boat.start, coins - start.coins):
                continue
            to_boat = _walking(state, here, boat.start, coins - boat.coins)
            if to_boat is None or not to_boat.on_foot:
                continue
            to_boat = Route(to_boat.legs, to_boat.toll, to_boat.shantay_pass, start.transports)
            after = _walking(state, _landing(boat), destination, coins - boat.coins - to_boat.coins)
            if after is not None and after.on_foot:
                option = _then(to_boat, boat, after)
                if option.estimate() < best:
                    found, best = option, option.estimate()
    return found


def route(state: CharacterState, destination: tuple[int, int, int], elapsed: int = 0) -> Route | None:
    """The fastest way there the character can use `elapsed` ticks into the step (Caleb, 2026-11-01): the walk, or a
    teleport or boat and the walks around it, with what it pays on the way. None if none can be made (Caleb,
    2026-11-01): an island without a fare or a teleport, a place no way the model knows reaches, no coins for a
    Shantay pass. Upstairs or underground, where the map lacks the stairs and ladders, the walk keeps the
    straight-line estimate."""
    a, coins = state.location, state.inventory.get(COINS, 0)
    walking = _walking(state, a, destination, coins)
    best = walking.estimate() if walking is not None and walking.on_foot else float("inf")
    found = _by_transport(state, a, destination, coins, best, home_ready(state, elapsed))
    if found is not None or walking is None or walking.on_foot:
        return found or walking
    return walking if (projected(a) or projected(destination)) and walking.estimate() < inf else None


def reach(state: CharacterState, elapsed: int = 0) -> Reach:
    """Where the character can get to now, as `route` goes (rlscape.travel.reach): for the combat ranker, which
    weighs every site at once."""
    a, coins = state.location, state.inventory.get(COINS, 0)
    depth, home = wilderness_level(a), home_ready(state, elapsed)
    ends = tuple(sorted({_landing(t) for t in usable_teleports(state)
                         if depth <= t.wilderness_limit and (home or t.kind != "home")}))
    return travel.reach(a, ends, tuple(b for b in boats() if can_use(state, b, b.start, coins)), coins >= PASS_PRICE)


def pays_toll(state: CharacterState, origin: tuple[int, int, int], destination: tuple[int, int, int]) -> bool:
    """Whether the walk from origin pays the Al Kharid toll, with the coins the character holds."""
    return bool(_al_kharid_route(state, origin, destination, state.inventory.get(COINS, 0)).toll)


def reachable(state: CharacterState, destination: tuple[int, int, int]) -> bool:
    return route(state, destination) is not None


def timed(state: CharacterState, legs: list[tuple[float, int]]) -> tuple[float, float]:
    """The walk's ticks and the energy left: the steps with run energy (rlscape.sim.energy) and the ticks a walk
    loses beyond them on the server, starting and pausing (rlscape.travel.overhead), resting."""
    ticks, energy = walk_plan(state, legs)
    lost = overhead(sum(tiles for tiles, _ in legs))
    return ticks + lost, min(energy + lost * restore_per_tick(state.level("agility")), MAX_ENERGY)


def _timed_route(state: CharacterState, planned: Route) -> tuple[float, float]:
    """A route's ticks and the energy left: its walks (timed) and its transports, resting."""
    ticks, energy = timed(state, planned.legs)
    gain = restore_per_tick(state.level("agility"))
    return ticks + planned.fixed, min(energy + planned.fixed * gain, MAX_ENERGY)


def route_ticks(state: CharacterState, destination: tuple[int, int, int]) -> float:
    """Ticks to get from the character's tile to `destination` with its current run energy and weight; infinite if
    it can't be done."""
    planned = route(state, destination)
    return inf if planned is None else ceil(_timed_route(state, planned)[0])


def _pay(state: CharacterState, coins: int) -> None:
    state.inventory[COINS] -= coins
    if state.inventory[COINS] == 0:
        del state.inventory[COINS]


def walk(state: CharacterState, destination: tuple[int, int, int], budget: int, elapsed: int = 0) -> int | None:
    """Go to `destination` the fastest way the character can (`route`), paying the toll, a Shantay pass, fares and
    teleports' runes, charges or items as the route needs. Returns the ticks taken, or None if the budget runs out on
    the way or it can't be done (then the character hasn't arrived, pays nothing and uses no energy). `elapsed` is how
    far into the option the walk starts; the ticks before it restore energy first."""
    planned = route(state, destination, elapsed)
    if planned is None:
        return None
    rest(state, elapsed - state.energy_clock)
    state.energy_clock = max(state.energy_clock, elapsed)
    ticks, energy = _timed_route(state, planned)
    ticks = ceil(ticks)
    if ticks >= budget:
        return None
    if planned.toll:
        _pay(state, TOLL * planned.toll)
    if planned.shantay_pass:
        _pay(state, PASS_PRICE)
    for transport in planned.transports:
        use(state, transport, state.tick + elapsed)  # a teleport starts the route
    if (destination[0] >> 6, destination[1] >> 6) != (state.location[0] >> 6, state.location[1] >> 6):
        state.region_since = state.tick + elapsed + ticks  # a new map region: aggression tolerance starts again
    state.location, state.run_energy = destination, energy
    state.energy_clock += ticks
    return ticks
