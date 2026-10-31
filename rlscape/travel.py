"""Travel time between tiles, shared by every option that walks somewhere (gathering sites, combat sites, banks).

Straight-line tile distance with a detour factor, plus a fixed cost per change of plane or between the surface and a
dungeon. The simulator's walks turn that path into ticks with run energy and weight (rlscape.sim.energy);
`travel_ticks` uses an assumed average speed instead, for estimates that don't know the character (ranking fights,
picking the nearest spot). All constants are to be calibrated on the server.
"""

from __future__ import annotations

RUN_TILES_PER_TICK = 1.5  # average speed for estimates: running, with run energy running out now and then
PATH_DETOUR = 1.3  # walking paths are longer than straight lines
UNDERGROUND_Y_OFFSET = 6400  # dungeons sit 6400 tiles north of the surface they lie under
LEVEL_CHANGE_TICKS = 12  # stairs or ladders, per change of plane or underground
BANKING_TICKS = 8  # opening a booth and depositing


def _surface(x: int, y: int) -> tuple[int, int, bool]:
    if y >= UNDERGROUND_Y_OFFSET:
        return x, y - UNDERGROUND_Y_OFFSET, True
    return x, y, False


def path(a: tuple[int, int, int], b: tuple[int, int, int]) -> tuple[float, int]:
    """The path from tile a to tile b: its length in tiles (straight-line distance with a detour factor) and its
    changes of level (stairs and ladders)."""
    ax, ay, a_under = _surface(a[0], a[1])
    bx, by, b_under = _surface(b[0], b[1])
    distance = max(abs(ax - bx), abs(ay - by))
    return distance * PATH_DETOUR, (a[2] != b[2]) + (a_under != b_under)


def travel_ticks(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """Estimated ticks to get from tile a to tile b at the average speed, stairs and ladders included."""
    tiles, level_changes = path(a, b)
    return tiles / RUN_TILES_PER_TICK + level_changes * LEVEL_CHANGE_TICKS
