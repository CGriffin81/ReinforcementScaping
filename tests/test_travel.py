"""Tests for travel times on planned routes (rlscape/travel.py): the planned steps, the measured overheads, the
straight-line fallback, places with no way (unreachable), and the ranker's many-at-once version."""

from __future__ import annotations

import pytest

from rlscape.routes import DATA, planned_steps
from rlscape.sim.movement import route, route_ticks, timed
from rlscape.sim.state import SPAWN, CharacterState
from rlscape.travel import (RUN_TILES_PER_TICK, WALK_PAUSE_TICKS, WALK_START_TICKS, Destinations, has_a_way,
                            on_foot, overhead, path, travel_ticks, unplanned)

needs_map = pytest.mark.skipif(not (DATA / "collision.npz").exists(), reason="no exported map")
DRAYNOR_BANK, MUSA_POINT = (3092, 3245, 0), (2915, 3152, 0)


@needs_map
def test_a_walk_is_the_planned_route_plus_the_measured_overheads():
    steps, changes = path(SPAWN, DRAYNOR_BANK)
    assert (steps, changes) == (144, 0)  # walked on the server: 144 tiles
    assert travel_ticks(SPAWN, DRAYNOR_BANK) == pytest.approx(144 / RUN_TILES_PER_TICK + WALK_START_TICKS
                                                              + WALK_PAUSE_TICKS * 144)
    assert overhead(0) == 0 and travel_ticks(SPAWN, SPAWN) == 0


@needs_map
def test_upstairs_and_underground_count_their_level_changes_on_the_surface_walk():
    castle_bank = (3208, 3220, 2)
    steps, changes = path(SPAWN, castle_bank)
    assert changes == 1 and steps == planned_steps(SPAWN, (3208, 3220, 0)) > 0  # the walk to below it, then the stairs


@needs_map
def test_no_walk_to_an_island_falls_back_to_the_straight_line():
    before, origin = unplanned["no walk"], (3233, 3229, 0)  # a pair no other test asks for: paths are remembered
    steps, _ = path(origin, MUSA_POINT)  # Karamja: a boat away (rlscape.sim.movement.route takes it)
    assert unplanned["no walk"] == before + 1
    assert path(origin, MUSA_POINT) == (steps, 0) and unplanned["no walk"] == before + 1  # counted once a pair
    assert steps == pytest.approx(max(abs(origin[0] - MUSA_POINT[0]), abs(origin[1] - MUSA_POINT[1])) * 1.3)


def test_a_walk_rests_through_its_start_and_pauses():
    state = CharacterState.fresh()
    ticks, energy = timed(state, [(100.0, 0)])
    assert ticks == pytest.approx(50 + WALK_START_TICKS + WALK_PAUSE_TICKS * 100)
    assert timed(state, [(0.0, 0)])[0] == 0


@needs_map
def test_many_destinations_at_once_match_one_at_a_time():
    """The combat ranker's travel (Destinations) gives exactly travel_ticks, planned or not."""
    tiles = [DRAYNOR_BANK, MUSA_POINT, (3208, 3220, 2), (3040, 9738, 0), (3100, 3500, 0), (1500, 1500, 0)]
    for origin in (SPAWN, (3086, 3230, 0), (3040, 9738, 0)):
        assert list(Destinations(tiles).ticks_from(origin)) == [travel_ticks(origin, t) for t in tiles]



@needs_map
def test_a_place_with_no_way_there_is_unreachable_even_from_off_the_map():
    """Caleb (2026-11-01): a place no way reaches (walk, crossing, teleport or boat) is unreachable. Shilo Village's
    bank is behind its quest; the rabbit by Isafdar (x 2297) is off the planner's map, which counts as walkable."""
    shilo_bank, off_map = (2852, 2954, 0), (2297, 3176, 0)
    assert not has_a_way(shilo_bank) and has_a_way(MUSA_POINT) and has_a_way(off_map)
    for origin in (SPAWN, off_map):
        assert path(origin, shilo_bank)[0] == float("inf") and not on_foot(origin, shilo_bank)
        assert travel_ticks(origin, shilo_bank) == float("inf")
        state = CharacterState.fresh()
        state.location = origin
        assert route(state, shilo_bank) is None and route_ticks(state, shilo_bank) == float("inf")
