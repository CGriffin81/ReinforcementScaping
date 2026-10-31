"""Walking between tiles, including the Al Kharid toll gate and the Shantay Pass. Every option that walks somewhere
goes through `walk`, which runs while run energy lasts (rlscape.sim.energy); `route_ticks` predicts the same walk
without making it, and `reachable` says whether it can be made at all.

The toll (TollGateOptionPlugin, BorderGuardDialogue): passing the gate between Lumbridge and Al Kharid takes 10
coins from the inventory, in either direction, unless Prince Ali Rescue is past stage 50 (counted here as complete).
A walk uses the gate when one end is inside Al Kharid and the other is west of the fence, south of its north end.
With the toll unpaid (no 10 coins in the inventory), the walk goes round the fence's north end instead, as players
did via the Al Kharid mine, so a character without coins is slower but never stranded.

The Shantay Pass (ShantayPassPlugin, ShantayGuard, ShantayOptionPlugin): the desert south of the pass (DesertZone's
borders, dungeons under them included) is entered only through the gate, whose guard takes a Shantay pass going
south; going north is free. Shantay, by the gate, sells a pass for 5 coins ("buy-pass"). The sim buys one on the way
and hands it over, so a walk south needs 5 coins in the inventory; without them the desert is unreachable. The Al
Kharid toll on the way to the gate is paid only from coins beyond the pass's 5. Not modelled: the magic carpets, and
desert heat on the walk between the gate and a site (DesertZone: a hit of 1-7 every 116 ticks without water, so 0-1
hits on the way to the Bandit Camp or Pollnivneach, which are both heat-free).

The fence line and its north end are estimates to verify on the server; the gate rules are the server's.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, inf

from rlscape.sim.energy import rest, walk_plan
from rlscape.sim.state import COINS, CharacterState
from rlscape.travel import UNDERGROUND_Y_OFFSET, path

TOLL = 10
AL_KHARID = (3268, 2700, 3400, 3330)  # x1, y1, x2, y2: east of the Lumbridge-Al Kharid fence, south of its end
FENCE_NORTH_END = (3270, 3335, 0)  # where the free way round passes; estimate, verify
PASS_PRICE = 5  # ShantayOptionPlugin: "buy-pass" takes 5 coins for one Shantay pass
DESERT = (3063, 2725, 3544, 3115)  # DesertZone's borders: everything south of the Shantay Pass gate
GATE_NORTH, GATE_SOUTH = (3304, 3117, 0), (3304, 3115, 0)  # ShantayGuard's gate tiles; quick-pass moves 2 tiles


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
    toll: bool = False  # pays the Al Kharid toll
    shantay_pass: bool = False  # buys a Shantay pass and hands it to the guard


def _al_kharid_route(state: CharacterState, a: tuple[int, int, int], b: tuple[int, int, int], coins: int) -> Route:
    """By the gate if the toll can be paid from `coins` or is waived, otherwise round the fence's north end."""
    if uses_toll_gate(a, b) and not toll_exempt(state):
        if coins >= TOLL:
            return Route([path(a, b)], toll=True)
        return Route([path(a, FENCE_NORTH_END), path(FENCE_NORTH_END, b)])
    return Route([path(a, b)])


def route(state: CharacterState, destination: tuple[int, int, int]) -> Route | None:
    """The walk's legs and what it pays on the way; None if it can't be made (no coins for a Shantay pass)."""
    a, coins = state.location, state.inventory.get(COINS, 0)
    if in_desert(a) == in_desert(destination):
        return _al_kharid_route(state, a, destination, coins)
    if in_desert(a):  # leaving the desert: the gate is free going north
        north = _al_kharid_route(state, GATE_NORTH, destination, coins)
        return Route([path(a, GATE_SOUTH), path(GATE_SOUTH, GATE_NORTH), *north.legs], toll=north.toll)
    if coins < PASS_PRICE:
        return None
    north = _al_kharid_route(state, a, GATE_NORTH, coins - PASS_PRICE)
    return Route([*north.legs, path(GATE_NORTH, GATE_SOUTH), path(GATE_SOUTH, destination)], toll=north.toll,
                 shantay_pass=True)


def reachable(state: CharacterState, destination: tuple[int, int, int]) -> bool:
    return route(state, destination) is not None


def route_ticks(state: CharacterState, destination: tuple[int, int, int]) -> float:
    """Ticks to walk from the character's tile to `destination` with its current run energy and weight; infinite if
    the walk can't be made."""
    planned = route(state, destination)
    return inf if planned is None else ceil(walk_plan(state, planned.legs)[0])


def _pay(state: CharacterState, coins: int) -> None:
    state.inventory[COINS] -= coins
    if state.inventory[COINS] == 0:
        del state.inventory[COINS]


def walk(state: CharacterState, destination: tuple[int, int, int], budget: int, elapsed: int = 0) -> int | None:
    """Walk to `destination`, paying the toll and buying a Shantay pass if the route needs them. Returns the ticks
    taken, or None if the budget runs out on the way or the walk can't be made (then the character hasn't arrived,
    pays nothing and uses no energy). `elapsed` is how far into the option the walk starts; the ticks before it
    restore energy first."""
    planned = route(state, destination)
    if planned is None:
        return None
    rest(state, elapsed - state.energy_clock)
    state.energy_clock = max(state.energy_clock, elapsed)
    ticks, energy = walk_plan(state, planned.legs)
    ticks = ceil(ticks)
    if ticks >= budget:
        return None
    if planned.toll:
        _pay(state, TOLL)
    if planned.shantay_pass:
        _pay(state, PASS_PRICE)
    state.location, state.run_energy = destination, energy
    state.energy_clock += ticks
    return ticks
