"""The mask speed-up (2026-11-09) changes no result: the remembered route is the one planning gives, in every state a
played episode passes through. scripts/trajectory_digest.py proves the whole of it on E1's 30 seeds."""

from __future__ import annotations

import pytest

from rlscape.baselines.guide import ScriptedGuidePolicy
from rlscape.envs import SimEnv
from rlscape.gamedata import server as gd
from rlscape.sim import movement
from rlscape.sim.state import COINS

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")


def test_a_remembered_route_is_the_planned_one_in_every_state_of_an_episode():
    env, policy = SimEnv(horizon_ticks=4 * 6_000), ScriptedGuidePolicy()
    obs, _ = env.reset(seed=3)
    policy.reset(3)
    places = [(b.x, b.y, b.plane) for b in gd.banks()][::4] + [(2887, 10212, 0), (3222, 3218, 0)]
    checked = 0
    for _ in range(60):
        state = env.sim.state
        for place in places:
            for elapsed in (0, 3_000):
                assert movement.route(state, place, elapsed) == movement._plan(state, place, elapsed)
                checked += 1
        obs, _, terminated, truncated, _ = env.step(policy.act(env, obs))
        if terminated or truncated:
            break
    assert checked >= 800  # the states of a 4-hour episode's first decisions (up to 60), each place, now and later


def test_a_route_is_planned_again_when_what_it_reads_changes():
    env = SimEnv(horizon_ticks=6_000)
    env.reset(seed=0)
    state, lumbridge_to_draynor = env.sim.state, (3092, 3245, 0)
    before = movement.route(state, lumbridge_to_draynor)
    state.inventory[COINS] = 10_000  # fares and the toll can be paid now
    assert movement.route(state, lumbridge_to_draynor) == movement._plan(state, lumbridge_to_draynor, 0)
    state.location = (3164, 3486, 0)  # the Grand Exchange
    after = movement.route(state, lumbridge_to_draynor)
    assert after == movement._plan(state, lumbridge_to_draynor, 0) and after != before
