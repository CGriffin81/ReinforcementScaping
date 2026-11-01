"""Week-2 property tests of the simulator (ROADMAP week 2): over whole episodes, every unmasked action runs, counts
never go negative, and the same seed gives the same trajectory, in this process or another."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys

import numpy as np
import pytest

from rlscape.envs import SimEnv
from rlscape.gamedata import server as gd
from rlscape.sim.economy import nearest_bank
from rlscape.sim.movement import route_ticks
from rlscape.sim.state import CharacterState

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
SEEDS = (0, 1, 2)


def check_state(state: CharacterState, horizon: int) -> None:
    for name, items in (("inventory", state.inventory), ("bank", state.bank), ("worn", state.worn_amounts),
                        ("dropped", state.dropped)):
        assert all(n > 0 for n in items.values()), f"a {name} count isn't positive: {items}"
    assert state.free_slots() >= 0
    assert state.coins() >= 0 and state.net_worth() >= 0
    assert 0 <= state.hp <= state.max_hp() and 0 <= state.run_energy <= 100
    assert 0 <= state.tick <= horizon


@pytest.mark.parametrize("seed", SEEDS)
def test_a_random_episode_runs_every_unmasked_action_and_counts_stay_valid(seed):
    """A whole 20-hour episode of masked random actions: none raises, each takes time, and nothing goes negative."""
    env = SimEnv()
    env.reset(seed=seed)
    rng, tick, steps = np.random.default_rng(seed), 0, 0
    while True:
        mask = env.action_masks()
        assert mask.any(), "no action is open"
        _, _, terminated, truncated, info = env.step(int(rng.choice(np.flatnonzero(mask))))
        steps += 1
        assert not terminated and info["duration"] >= 1 and info["game_ticks"] == tick + info["duration"]
        tick = info["game_ticks"]
        check_state(env.sim.state, env.sim.horizon_ticks)
        if truncated:
            break
    assert tick == env.sim.horizon_ticks and steps > 100


def trajectory_digest(seed: int, steps: int) -> str:
    """A hash of a seeded random run's observations, rewards and info, for comparing runs across processes."""
    env = SimEnv()
    obs, _ = env.reset(seed=seed)
    rng, digest = np.random.default_rng(seed), hashlib.sha256(obs.tobytes())
    for _ in range(steps):
        obs, reward, _, truncated, info = env.step(int(rng.choice(np.flatnonzero(env.action_masks()))))
        digest.update(obs.tobytes())
        digest.update(repr((reward, sorted(info["option"].items()), info["termination"], info["duration"],
                            sorted(info["items_delta"]["inventory"].items()))).encode())
        if truncated:
            break
    return digest.hexdigest()


def test_the_same_seed_gives_the_same_trajectory_in_another_process():
    """Training runs many worker processes, each with its own string-hash seed. A trajectory mustn't depend on it
    (set or dict order over strings, say)."""
    code = "import sys; from tests.test_sim_properties import trajectory_digest; print(trajectory_digest(5, 150))"
    digests = set()
    for hash_seed in ("1", "2", "3"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True,
                             cwd=gd.REPO)
        digests.add(out.stdout.strip())
    assert digests == {trajectory_digest(5, 150)}


def test_the_cached_nearest_bank_is_the_one_a_fresh_search_finds():
    """nearest_bank caches on what a walk depends on; along random episodes it must agree with a search from scratch."""
    env = SimEnv()
    for seed in (3, 4):
        env.reset(seed=seed)
        rng = np.random.default_rng(seed)
        for _ in range(200):
            state = env.sim.state
            fresh = min(gd.banks(), key=lambda b: route_ticks(state, (b.x, b.y, b.plane)))
            assert route_ticks(state, (nearest_bank(state).x, nearest_bank(state).y, nearest_bank(state).plane)) ==                 route_ticks(state, (fresh.x, fresh.y, fresh.plane))
            if env.step(int(rng.choice(np.flatnonzero(env.action_masks()))))[3]:
                break

