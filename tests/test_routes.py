"""Tests for the walking planner (rlscape/routes.py): the server's step rules on a small map, doors, and the export."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.routes import DATA, DOOR_STEPS, Map, surface

WALL_EAST = 0x8  # a wall on a tile's east edge: it can't be entered going west (STEP_MASKS[(-1, 0)])
WALL_NORTH, WALL_SOUTH = 0x2, 0x20
BLOCKED = 0x200000  # floor blocked (water and the like)


def small(flags: dict[tuple[int, int], int], size: int = 5, doors: list | None = None) -> Map:
    grid = np.zeros((size, size), dtype=np.int32)
    for (x, y), f in flags.items():
        grid[y, x] = f
    return Map(grid, (0, 0), doors or [])


def test_open_ground_walks_diagonally_one_step_a_tile():
    world = small({})
    assert world.steps((0, 0), (4, 4)) == 4 and world.steps((0, 0), (4, 1)) == 4


def test_a_blocked_tile_is_walked_round():
    world = small({(1, 1): BLOCKED, (2, 1): BLOCKED, (3, 1): BLOCKED})
    assert world.steps((2, 0), (2, 2)) == 6  # round the end of the row, without cutting its corners
    assert world.route((2, 0), (2, 1)) is None


def test_a_diagonal_needs_both_tiles_beside_it_open():
    """SmartPathfinder: the diagonal (x, y) -> (x+1, y+1) also checks (x+1, y) and (x, y+1)."""
    world = small({(1, 0): BLOCKED})
    route = world.route((0, 0), (1, 1))
    assert route == [(0, 0, 0), (0, 1, 0), (1, 1, 0)]


def test_a_wall_blocks_one_direction_only_where_the_server_masks_it():
    world = small({(1, 2): WALL_EAST})
    assert world.steps((0, 2), (1, 2)) == 1  # going east, into its open west side
    assert world.steps((2, 2), (1, 2)) > 1  # going west, through the wall


def test_a_door_is_a_step_through_its_wall_that_costs_opening_it():
    walls = {(x, 2): BLOCKED for x in range(5) if x != 2}
    walls[(2, 2)], walls[(2, 3)] = WALL_NORTH, WALL_SOUTH  # a wall between them, flagged on both sides
    door = {"id": 1, "name": "Door", "x": 2, "y": 2, "type": 0, "rotation": 1}  # its wall is on the north side
    assert small(walls).route((2, 1), (2, 4)) is None
    world = small(walls, doors=[door])
    assert world.steps((2, 1), (2, 4)) == 3 + DOOR_STEPS
    assert world.door_between((2, 2), (2, 3)) == door


@pytest.mark.skipif(not (DATA / "collision.npz").exists(), reason="no exported map")
def test_the_exported_map_routes_lumbridge_to_draynor():
    """Walked on the server: from the RL character's spawn to Draynor's bank is 144 tiles (live test)."""
    world = surface()
    assert world.steps((3233, 3230, 0), (3092, 3245, 0)) == 144
    assert world.route((3233, 3230, 0), (2957, 3158, 0)) is None  # Karamja: a boat away


@pytest.mark.skipif(not (DATA / "collision.npz").exists(), reason="no exported map")
def test_the_crandor_passage_joins_karamjas_volcano_rim_to_crandor():
    """Caleb, 2026-11-08, OQ-16 (a): with Dragon Slayer complete, Karamja volcano's pot hole, the dungeon's secret wall
    and the rope up are one crossing from the rim to Crandor, both ways (its places had no way before)."""
    from rlscape.routes import CROSSINGS
    from rlscape.travel import has_a_way
    world = surface()
    rim, crandor = (2856, 3167, 0), (2834, 3258, 0)
    assert 492 in CROSSINGS
    assert world.crossing_between(rim, crandor) is not None and world.crossing_between(crandor, rim) is not None
    assert 89 + CROSSINGS[492][1] <= world.steps(rim, crandor) <= 89 + CROSSINGS[492][1] + 2  # (and onto it)
    assert has_a_way(crandor) and has_a_way((2835, 3262, 0))  # a Crandor place, by its lesser demons
