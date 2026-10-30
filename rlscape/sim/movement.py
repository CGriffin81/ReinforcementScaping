"""Walking between tiles, including the Al Kharid toll gate. Every option that walks somewhere goes through `walk`,
which runs while run energy lasts (rlscape.sim.energy); `route_ticks` predicts the same walk without making it.

The toll (TollGateOptionPlugin, BorderGuardDialogue): passing the gate between Lumbridge and Al Kharid takes 10
coins from the inventory, in either direction, unless Prince Ali Rescue is past stage 50 (counted here as complete).
A walk uses the gate when one end is inside Al Kharid and the other is west of the fence, south of its north end.
With the toll unpaid (no 10 coins in the inventory), the walk goes round the fence's north end instead, as players
did via the Al Kharid mine, so a character without coins is slower but never stranded.

The fence line and its north end are estimates to verify on the server; the gate rules are the server's.
"""

from __future__ import annotations

from math import ceil

from rlscape.sim.energy import rest, walk_plan
from rlscape.sim.state import COINS, CharacterState
from rlscape.travel import UNDERGROUND_Y_OFFSET, path

TOLL = 10
AL_KHARID = (3268, 2700, 3400, 3330)  # x1, y1, x2, y2: east of the Lumbridge-Al Kharid fence, south of its end
FENCE_NORTH_END = (3270, 3335, 0)  # where the free way round passes; estimate, verify


def _in_al_kharid(tile: tuple[int, int, int]) -> bool:
    x1, y1, x2, y2 = AL_KHARID
    return tile[1] < UNDERGROUND_Y_OFFSET and x1 <= tile[0] <= x2 and y1 <= tile[1] <= y2


def _west_of_fence(tile: tuple[int, int, int]) -> bool:
    return tile[1] < UNDERGROUND_Y_OFFSET and tile[0] < AL_KHARID[0] and tile[1] <= AL_KHARID[3]


def uses_toll_gate(a: tuple[int, int, int], b: tuple[int, int, int]) -> bool:
    return (_in_al_kharid(a) and _west_of_fence(b)) or (_in_al_kharid(b) and _west_of_fence(a))


def toll_exempt(state: CharacterState) -> bool:
    return "PRINCE_ALI_RESCUE" in state.progress.quests_complete


def _legs(state: CharacterState, destination: tuple[int, int, int]) -> list[tuple[float, int]]:
    """The route's legs: by the gate if the toll can be paid or is waived, otherwise round the fence's north end."""
    a = state.location
    if uses_toll_gate(a, destination) and not toll_exempt(state) and state.inventory.get(COINS, 0) < TOLL:
        return [path(a, FENCE_NORTH_END), path(FENCE_NORTH_END, destination)]
    return [path(a, destination)]


def route_ticks(state: CharacterState, destination: tuple[int, int, int]) -> int:
    """Ticks to walk from the character's tile to `destination` with its current run energy and weight."""
    return ceil(walk_plan(state, _legs(state, destination))[0])


def walk(state: CharacterState, destination: tuple[int, int, int], budget: int, elapsed: int = 0) -> int | None:
    """Walk to `destination`, paying the toll if the route uses the gate. Returns the ticks taken, or None if the
    budget runs out on the way (then the character hasn't arrived, pays nothing and uses no energy). `elapsed` is
    how far into the option the walk starts; the ticks before it restore energy first."""
    rest(state, elapsed - state.energy_clock)
    state.energy_clock = max(state.energy_clock, elapsed)
    ticks, energy = walk_plan(state, _legs(state, destination))
    ticks = ceil(ticks)
    if ticks >= budget:
        return None
    if uses_toll_gate(state.location, destination) and not toll_exempt(state) and state.inventory.get(COINS, 0) >= TOLL:
        state.inventory[COINS] -= TOLL
        if state.inventory[COINS] == 0:
            del state.inventory[COINS]
    state.location, state.run_energy = destination, energy
    state.energy_clock += ticks
    return ticks
