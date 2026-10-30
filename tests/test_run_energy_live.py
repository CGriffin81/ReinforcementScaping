"""Live checks of the simulator's run energy and weight (rlscape.sim.energy) against the server, and of `set_run`.

Needs the forked server running with worldprops/rl.conf; skipped when the server is down.
"""

from __future__ import annotations

import pytest

from rlscape.bridge import BridgeClient
from rlscape.sim.energy import drain_per_run_tick, restore_per_tick, weight
from rlscape.sim.state import CharacterState
from test_bridge_live import bridge_reachable

pytestmark = pytest.mark.skipif(not bridge_reachable(), reason="RL bridge not running on localhost")
NORTH, SOUTH = (3225, 3240), (3233, 3225)  # around the Lumbridge spawn; the existing live tests walk there


@pytest.fixture
def client():
    with BridgeClient() as c:
        c.set_tick_ms(100)  # long enough that a state read lands on every tick
        yield c
        c.set_tick_ms(600)


@pytest.fixture
def uid(client):
    state = client.spawn()
    yield state["uid"]
    client.despawn(state["uid"])


def walk_reading_every_tick(client: BridgeClient, uid: int, tile: tuple[int, int]) -> list[tuple[int, dict]]:
    """Walk to `tile`, reading the state until the character stops: (server tick, state) pairs, the first before
    moving. The bridge runs commands once a tick, so back-to-back reads land on consecutive ticks."""
    def read() -> tuple[int, dict]:
        response = client.request("state", uid=uid)
        return response["tick"], response["state"]

    reads, started = [read()], False
    client.walk_to(uid, *tile)
    for _ in range(300):
        reads.append(read())
        still = not reads[-1][1]["moving"] and reads[-1][1]["location"] == reads[-2][1]["location"]
        if started and still:
            break
        started = started or not still  # the walk begins a tick or so after walk_to
    return reads


def ticks_of(reads: list[tuple[int, dict]]) -> list[tuple[int, float, float]]:
    """(tiles moved, energy before, energy after) for each one-tick interval, tiles as the sim counts them."""
    out = []
    for (t0, a), (t1, b) in zip(reads, reads[1:]):
        if t1 - t0 == 1:
            moved = max(abs(a["location"]["x"] - b["location"]["x"]), abs(a["location"]["y"] - b["location"]["y"]))
            out.append((moved, a["run_energy"], b["run_energy"]))
    return out


def test_a_fresh_character_runs_with_full_energy_and_the_sims_weight(client, uid):
    state = client.state(uid)
    assert state["run"] is True and state["run_energy"] == 100.0  # AIPlayer.init turns run on
    assert state["weight"] == pytest.approx(weight(CharacterState.fresh()))  # the starter kit


def test_each_tick_drains_or_restores_exactly_as_the_sim_says(client, uid):
    drain, gain = drain_per_run_tick(weight(CharacterState.fresh())), restore_per_tick(1)
    walk_reading_every_tick(client, uid, NORTH)  # spend some energy so restoring shows
    ran = ticks_of(walk_reading_every_tick(client, uid, SOUTH))
    assert len(ran) >= 8 and sum(moved == 2 for moved, _, _ in ran) >= 5  # running covers 2 tiles a tick
    for moved, before, after in ran:
        assert after == pytest.approx(before - drain if moved == 2 else min(before + gain, 100.0)), (moved, before)

    assert client.set_run(uid, on=False) is False
    walked = ticks_of(walk_reading_every_tick(client, uid, NORTH))
    assert {moved for moved, _, _ in walked} <= {0, 1} and sum(moved == 1 for moved, _, _ in walked) >= 10
    for moved, before, after in walked:
        assert after == pytest.approx(min(before + gain, 100.0))  # walking restores like standing still


def test_the_server_turns_run_off_when_energy_runs_out_and_set_run_turns_it_back_on(client, uid):
    for leg in range(200):
        reads = walk_reading_every_tick(client, uid, NORTH if leg % 2 == 0 else SOUTH)
        if not reads[-1][1]["run"]:
            break
    assert reads[-1][1]["run"] is False and reads[-1][1]["run_energy"] < 5  # ran out on the way, rested a little
    assert client.set_run(uid) is True and client.state(uid)["run"] is True
