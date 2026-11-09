"""SMDP GAE and PBRS (rlscape.agents.smdp) against hand-computed returns (ROADMAP week 3: "SMDP rollout buffer,
unit-tested against hand-computed returns")."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.agents.smdp import TICKS_PER_HOUR, option_discounts, pbrs_bonus, smdp_gae

HALF_HOUR, HOUR, QUARTER = TICKS_PER_HOUR // 2, TICKS_PER_HOUR, TICKS_PER_HOUR // 4


def column(*xs: float) -> np.ndarray:
    return np.array(xs, dtype=np.float64)[:, None]  # (T, 1): one env


def test_a_decision_is_discounted_by_gamma_per_game_hour():
    assert option_discounts(np.array([0, HOUR, HALF_HOUR]), 0.81) == pytest.approx([1.0, 0.81, 0.9])
    with pytest.raises(ValueError):
        option_discounts(np.array([HOUR]), 0.0)
    with pytest.raises(ValueError):
        option_discounts(np.array([-1]), 0.9)


def test_lambda_one_gives_the_episodes_discounted_returns():
    """Rewards 1, 2, 3 over options of half an hour, an hour and a quarter, γ_hr 0.5, the episode ending at the last:
    R2 = 3, R1 = 2 + 0.5·3 = 3.5, R0 = 1 + 0.5^0.5·3.5."""
    rewards, durations = column(1, 2, 3), column(HALF_HOUR, HOUR, QUARTER)
    values, dones = column(0.4, -1.0, 2.0), column(False, False, True)
    advantages, returns = smdp_gae(rewards, values, durations, dones, np.array([99.0]), 0.5, 1.0)
    expected = column(1 + 0.5 ** 0.5 * 3.5, 3.5, 3.0)
    assert returns == pytest.approx(expected) and advantages == pytest.approx(expected - values)


def test_lambda_zero_gives_the_one_step_td_errors():
    rewards, durations = column(1, 2), column(HOUR, HALF_HOUR)
    values, dones = column(0.5, 1.5), column(False, False)
    advantages, _ = smdp_gae(rewards, values, durations, dones, np.array([4.0]), 0.81, 0.0)
    assert advantages == pytest.approx(column(1 + 0.81 * 1.5 - 0.5, 2 + 0.9 * 4.0 - 1.5))


def test_a_cut_rollout_bootstraps_and_an_episode_end_does_not_leak():
    """The last decision bootstraps from last_values with its own discount; an episode that ended at decision 0
    takes nothing from decision 1, which belongs to the next episode."""
    rewards, durations = column(1, 2), column(HOUR, HOUR)
    values, dones = column(10.0, 0.0), column(True, False)
    advantages, returns = smdp_gae(rewards, values, durations, dones, np.array([5.0]), 0.5, 0.95)
    assert returns[1, 0] == pytest.approx(2 + 0.5 * 5.0)  # bootstrapped
    assert returns[0, 0] == pytest.approx(1.0)  # ended: no value or advantage from the next episode
    assert advantages[0, 0] == pytest.approx(1.0 - 10.0)


def test_envs_are_independent_and_equal_durations_are_standard_gae():
    """Two envs with the same durations everywhere: the same as standard GAE with γ = γ_hr^τ, each env alone."""
    rng = np.random.default_rng(0)
    rewards, values = rng.normal(size=(6, 2)), rng.normal(size=(6, 2))
    dones = np.zeros((6, 2), dtype=bool)
    dones[2, 1] = True
    last = rng.normal(size=2)
    advantages, _ = smdp_gae(rewards, values, np.full((6, 2), HALF_HOUR), dones, last, 0.64, 0.9)
    gamma, lam = 0.8, 0.9  # 0.64 ** 0.5
    for env in range(2):
        running, expected = 0.0, np.zeros(6)
        for t in reversed(range(6)):
            next_value, keep = (last[env] if t == 5 else values[t + 1, env]), 1.0 - dones[t, env]
            delta = rewards[t, env] + gamma * next_value * keep - values[t, env]
            running = delta + gamma * lam * keep * running
            expected[t] = running
        assert advantages[:, env] == pytest.approx(expected)


def test_shapes_and_lambda_are_checked():
    with pytest.raises(ValueError):
        smdp_gae(column(1, 2), column(0, 0), column(HOUR), column(False, False), np.array([0.0]), 0.9, 0.95)
    with pytest.raises(ValueError):
        smdp_gae(column(1), column(0), column(HOUR), column(False), np.array([0.0]), 0.9, 1.5)


def test_pbrs_telescopes_to_minus_the_first_potential():
    """F = γ^τ Φ(s′) − Φ(s) with Φ(terminal) = 0: over an episode, Σ_t (γ^{τ_0+...+τ_{t-1}}) F_t = −Φ(s_0), whatever
    the potentials and durations, so shaping can't change which policy is best (Ng et al. 1999)."""
    rng = np.random.default_rng(1)
    phi = rng.normal(size=5)
    durations = rng.integers(0, 3 * HOUR, size=4)
    dones = np.array([False, False, False, True])
    bonus = pbrs_bonus(phi[:-1], phi[1:], durations, dones, 0.7)
    weights = np.concatenate([[1.0], np.cumprod(option_discounts(durations, 0.7))[:-1]])
    assert float(weights @ bonus) == pytest.approx(-phi[0])
