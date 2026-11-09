"""Live checks of the Agility shortcuts in travel (rlscape.gamedata.shortcuts) against the server: a trip the sim plans
over one is taken on the server as a player does (rlscape.bridge.travel), and the server holds a character a level
short of it on its side.

Needs the forked server running with worldprops/rl.conf; skipped when the server is down.
"""

from __future__ import annotations

import pytest

from rlscape.bridge import BridgeClient
from rlscape.bridge.travel import SHORTCUTS, go
from rlscape.sim.movement import route, route_ticks
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState
from test_bridge_live import bridge_reachable

pytestmark = pytest.mark.skipif(not bridge_reachable(), reason="RL bridge not running on localhost")
OUTSIDE, INSIDE = (2924, 3355, 0), (2945, 3356, 0)  # either side of Falador's west wall (validate_travel's trip)
WALL = SHORTCUTS["shortcut:falador_wall_in"]


@pytest.fixture
def client():
    with BridgeClient() as c:
        c.set_tick_ms(50)
        yield c
        c.set_tick_ms(600)


@pytest.fixture
def uid(client):
    state = client.spawn()
    yield state["uid"]
    client.despawn(state["uid"])


def character(agility: int) -> CharacterState:
    state = CharacterState.fresh()
    state.xp[SKILL_INDEX["agility"]] = float(XP_FOR_LEVEL[agility])
    state.location = OUTSIDE
    return state


def here(client: BridgeClient, uid: int) -> tuple[int, int, int]:
    loc = client.state(uid)["location"]
    return loc["x"], loc["y"], loc["z"]


def test_a_trip_over_falador_s_wall_goes_over_it_on_the_server_in_the_sim_s_time(client, uid):
    planned = route(character(5), INSIDE)
    assert [t.id for t in planned.transports] == ["shortcut:falador_wall_in"]
    client.debug_set_levels(uid, {"agility": 5})  # setup only
    client.debug_teleport(uid, *OUTSIDE)
    client.wait(3)
    trip = go(client, uid, planned.transports, INSIDE)
    assert trip.arrived, trip.steps
    assert [what for what, _ in trip.steps] == ["walk to shortcut:falador_wall_in", "shortcut:falador_wall_in", "walk"]
    assert abs(route_ticks(character(5), INSIDE) / trip.ticks - 1) <= 0.20, trip.steps  # env contract §7


def test_a_level_short_the_server_keeps_the_character_outside_the_wall(client, uid):
    client.debug_set_levels(uid, {"agility": 4})  # setup only
    client.debug_teleport(uid, *WALL.start)
    client.wait(3)
    client.request("interact", uid=uid, name=WALL.name, option=WALL.option, object=True, ids=list(WALL.ids),
                   packet=True)
    client.wait(10)
    assert here(client, uid)[0] < 2935  # still west of the wall
