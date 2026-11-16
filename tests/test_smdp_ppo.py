"""MaskablePPO with SMDP discounting (rlscape.agents.ppo): its rollout buffer against hand-computed returns, and a
short run on the sim."""

from __future__ import annotations

import numpy as np
import pytest
import torch as th
from gymnasium import spaces

from rlscape.agents.smdp import TICKS_PER_HOUR
from rlscape.gamedata import server as gd

ppo = pytest.importorskip("rlscape.agents.ppo")
needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
HALF_HOUR, HOUR, QUARTER = TICKS_PER_HOUR // 2, TICKS_PER_HOUR, TICKS_PER_HOUR // 4


def buffer(n_steps: int, gamma_hr: float, gae_lambda: float, floor: float = 0.0) -> ppo.SMDPMaskableRolloutBuffer:
    return ppo.SMDPMaskableRolloutBuffer(n_steps, spaces.Box(-1, 1, (2,)), spaces.Discrete(3), device="cpu",
                                         gae_lambda=gae_lambda, n_envs=1, gamma_hr=gamma_hr,
                                         discount_floor_ticks=floor)


def fill(buf: ppo.SMDPMaskableRolloutBuffer, rewards, values, durations, starts) -> None:
    for r, v, d, s in zip(rewards, values, durations, starts):
        buf.add(np.zeros((1, 2), dtype=np.float32), np.zeros((1, 1)), np.array([r], dtype=np.float32),
                np.array([s], dtype=np.float32), th.tensor([[v]]), th.tensor([0.0]),
                action_masks=np.ones((1, 3)), durations=np.array([d]))


def test_the_buffer_gives_the_hand_computed_smdp_returns():
    """An episode of three options (half an hour, an hour, a quarter), rewards 1, 2, 3, γ_hr 0.5, λ 1, ending at the
    last: R2 = 3, R1 = 2 + 0.5·3, R0 = 1 + 0.5^0.5·R1. sb3 marks episode starts; the buffer turns them into ends."""
    buf = buffer(3, 0.5, 1.0)
    fill(buf, [1, 2, 3], [0.4, -1.0, 2.0], [HALF_HOUR, HOUR, QUARTER], [True, False, False])
    buf.compute_returns_and_advantage(last_values=th.tensor([[99.0]]), dones=np.array([True]))
    expected = np.array([1 + 0.5 ** 0.5 * 3.5, 3.5, 3.0])
    assert buf.returns[:, 0] == pytest.approx(expected, rel=1e-6)
    assert buf.advantages[:, 0] == pytest.approx(expected - np.array([0.4, -1.0, 2.0]), rel=1e-6)


def test_an_episode_start_inside_the_rollout_cuts_the_return():
    """Decision 1 starts a new episode, so decision 0's return is its reward alone; decision 1 bootstraps from the
    last value with its own discount."""
    buf = buffer(2, 0.5, 0.95)
    fill(buf, [1, 2], [10.0, 0.0], [HOUR, HOUR], [False, True])
    buf.compute_returns_and_advantage(last_values=th.tensor([[5.0]]), dones=np.array([False]))
    assert buf.returns[:, 0] == pytest.approx([1.0, 2 + 0.5 * 5.0])


def test_the_buffer_discounts_with_the_decision_floor():
    """2026-11-15: a one-tick option then a half-hour, rewards 0 and 1, γ_hr 0.25, λ 1, a half-hour floor, the
    episode ending at the second: R1 = 1, R0 = 0 + 0.25^0.5·1 (the tick discounted as the floor's half hour)."""
    buf = buffer(2, 0.25, 1.0, floor=HALF_HOUR)
    fill(buf, [0, 1], [0.0, 0.0], [1, HALF_HOUR], [True, False])
    buf.compute_returns_and_advantage(last_values=th.tensor([[99.0]]), dones=np.array([True]))
    assert buf.returns[:, 0] == pytest.approx([0.5, 1.0])


@needs_server
def test_the_model_passes_its_floor_to_its_buffer():
    from stable_baselines3.common.vec_env import DummyVecEnv

    from rlscape.envs import SimEnv
    model = ppo.SMDPMaskablePPO("MlpPolicy", DummyVecEnv([lambda: SimEnv()]), gamma_hr=0.9, n_steps=8,
                                batch_size=8, device="cpu", discount_floor_ticks=100)
    assert model.rollout_buffer.discount_floor_ticks == 100 and model.discount_floor_ticks == 100


def test_the_buffer_needs_the_durations():
    buf = buffer(1, 0.9, 0.95)
    with pytest.raises(ValueError):
        buf.add(np.zeros((1, 2), dtype=np.float32), np.zeros((1, 1)), np.array([1.0], dtype=np.float32),
                np.array([1.0], dtype=np.float32), th.tensor([[0.0]]), th.tensor([0.0]), action_masks=np.ones((1, 3)))


@needs_server
def test_a_short_run_on_the_sim_stores_each_decisions_duration():
    """Two envs, two rollouts of 8 decisions: it learns without error, and the buffer holds the options' durations
    (each a whole number of ticks, most of them more than none)."""
    from stable_baselines3.common.vec_env import DummyVecEnv

    from rlscape.envs import SimEnv
    env = DummyVecEnv([lambda: SimEnv(), lambda: SimEnv()])
    model = ppo.SMDPMaskablePPO("MlpPolicy", env, gamma_hr=0.9, n_steps=8, batch_size=8, n_epochs=1, seed=0,
                                device="cpu")
    model.learn(total_timesteps=32)
    durations = model.rollout_buffer.durations
    assert durations.shape == (8, 2) and (durations >= 0).all() and (durations > 0).mean() > 0.5
    assert np.isfinite(model.rollout_buffer.returns).all() and model.gamma == 1.0
    with pytest.raises(ValueError):
        ppo.SMDPMaskablePPO("MlpPolicy", env, gamma=0.99)


@needs_server
def test_the_horizon_is_bootstrapped_only_when_asked():
    """2026-11-15: with bootstrap_horizon False the horizon is the task's end, so its step keeps the env's reward. The
    same seeded rollout with it True differs only at the horizon's steps, by γ_hr^τ·V(final observation)."""
    from stable_baselines3.common.vec_env import DummyVecEnv

    from rlscape.envs import SimEnv

    def rollout(bootstrap: bool):
        env = DummyVecEnv([lambda: SimEnv(horizon_ticks=3_000)])  # half an hour: several episodes in 16 decisions
        model = ppo.SMDPMaskablePPO("MlpPolicy", env, gamma_hr=0.9, n_steps=16, batch_size=16, n_epochs=1, seed=0,
                                    device="cpu", bootstrap_horizon=bootstrap)
        model.learn(total_timesteps=16)  # one rollout, then one update, which leaves the buffer's rewards as they were
        return model.rollout_buffer

    with_it, without = rollout(True), rollout(False)
    assert (with_it.durations[:, 0] == without.durations[:, 0]).all()  # the same decisions
    differ = np.flatnonzero(~np.isclose(with_it.rewards[:, 0], without.rewards[:, 0]))
    assert len(differ) >= 1  # the horizon came within the rollout, and its step was bootstrapped only with it True
    starts = without.episode_starts[:, 0]  # sb3 marks each decision that starts an episode
    assert all(starts[t + 1] for t in differ if t + 1 < len(starts))  # each differing step ended its episode
