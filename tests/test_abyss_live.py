"""Live checks of the Abyss against its export (data/abyss; scripts/export_abyss.py) and the sim's crossing
(rlscape.sim.abyss): the mage's teleport, the layout the landing's segment shows, and a rift.
Needs the forked server running with worldprops/rl.conf; skipped when the server is down.
"""

from __future__ import annotations

import json

import pytest

from rlscape.bridge import BridgeClient
from rlscape.bridge.abyss import (MAGE_TILE, OUTER_RADIUS, in_abyss, landing_place, places, polar, segment, teleport,
                                  tick, xy)
from rlscape.gamedata import runecrafting as rcd
from rlscape.sim.abyss import SKULL_TICKS
from test_bridge_live import bridge_reachable

pytestmark = pytest.mark.skipif(not bridge_reachable(), reason="RL bridge not running on localhost")


@pytest.fixture
def client():
    with BridgeClient() as c:
        c.set_tick_ms(100)
        yield c
        c.set_tick_ms(600)


@pytest.fixture
def uid(client):
    state = client.spawn()
    client.debug_set_levels(state["uid"], {"hitpoints": 99, "defence": 99})
    yield state["uid"]
    client.despawn(state["uid"])


def test_the_mages_teleport_lands_on_the_outer_ring_drained_and_the_layout_is_the_exports(client, uid):
    """The teleport lands the character on the outer ring with no prayer and a skull for 2,000 ticks (the bridge's
    `skull_ticks`, which the observation shows: OQ-48 (a)); the obstacles show the layout the export has for the
    segment of the place they block, the passage among them."""
    client.debug_teleport(uid, *MAGE_TILE[:2])
    client.wait(2)
    assert client.state(uid)["skull_ticks"] == 0
    _, _, s = teleport(client, uid)
    assert in_abyss(s) and s["prayer_points"] == 0
    assert SKULL_TICKS - 20 < s["skull_ticks"] <= SKULL_TICKS
    r, angle = polar(*xy(s))
    assert OUTER_RADIUS - 4 < r <= OUTER_RADIUS
    a = rcd.abyss()
    data = json.loads((rcd.ABYSS / "abyss.json").read_text(encoding="utf-8"))
    angles = {i: polar(*data["places"][str(i)]["tile"])[1] for i in a.places}
    seen = places(client, uid)
    here = landing_place(seen, angles, angle)
    layout = a.layouts[segment(angles[here])]
    assert {i: p["kind"] for i, p in seen.items()} == {i: k for i, k in zip(a.places, layout) if k != "blocked"}


def test_a_rift_from_the_inner_ring_lands_inside_its_altars_ruins(client, uid):
    """Exit-through on the nature rift, from the inner ring's landing past the nearest obstacle, lands the character
    where entering the nature ruins does (Altar.enterRift)."""
    a = rcd.abyss()
    start = min(a.inner_tiles, key=lambda t: a.inner_steps[a.inner_tiles.index(t)]["nature"])
    client.debug_teleport(uid, *start)
    client.wait(2)
    client.set_run(uid, True)
    client.interact(uid, "Nature rift", "Exit-through", ids=[7133])
    for _ in range(40):
        _, s = tick(client, uid)
        if not in_abyss(s):
            break
    assert (s["location"]["x"], s["location"]["y"], s["location"]["z"]) == rcd.ruins()["nature"].end
