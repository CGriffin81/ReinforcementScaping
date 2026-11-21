"""The weight-conditioned PPO's environment (E5, RQ3's second half; ROADMAP's finishing plan: "weights drawn each
episode and given in the observation"; Caleb, 2026-11-10, OQ-74).

`WeightConditioned` wraps one SimEnv. At each episode's start it draws a weighting in normalised units (OQ-67): the
skill share u from U[0, 1] and the wealth share 1 − u (OQ-74 (a)), so every weighting between E3's five is trained on.
The env is reset with that weighting's reward weights (rlscape.envs.weights.env_weights), and the observation gets
(u, 1 − u) appended, so one policy learns to act for whichever it's given.

- **The preference features are the normalised shares, in [0, 1] like the rest of the observation**, appended after
  SimEnv's own 3,482. SimEnv's `preference_in_obs` would put its raw reward weights there (up to 17.1 for wealth), and
  changing its encoder would change the frozen env; so it stays off.
- **Seeded:** the draws come from a generator seeded by the env's first reset (sb3 seeds each env with the run's seed
  plus its index), so a run is repeatable.
- **Evaluated** with `TrainedPolicy` given a preference (`<label>=ppo:<model.zip>@<u>`, rlscape.eval.trained), which
  appends the same two features to a plain SimEnv's observation.
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from rlscape.envs.weights import env_weights

DISTRIBUTIONS = ("uniform",)
KEYS = {"weights"}
SEED_SALT = 0xE5  # the draws' generator differs from the env's own, seeded alike


def check_conditioned(conditioned: dict) -> None:
    unknown = sorted(set(conditioned) - KEYS)
    if unknown:
        raise ValueError(f"config: unknown conditioned keys {unknown}; known: {sorted(KEYS)}")
    if conditioned.get("weights") not in DISTRIBUTIONS:
        raise ValueError(f"config: conditioned.weights must be one of {DISTRIBUTIONS}")


def with_preference(obs: np.ndarray, preference: np.ndarray) -> np.ndarray:
    """The observation with the normalised weighting (u_skill, u_wealth) appended."""
    return np.concatenate([np.asarray(obs, dtype=np.float32), np.asarray(preference, dtype=np.float32)])


class WeightConditioned(gym.Wrapper):
    """A SimEnv with a weighting drawn each episode, rewarded by it and shown it (the module's docstring)."""

    def __init__(self, env: gym.Env, weights: str = "uniform"):
        super().__init__(env)
        check_conditioned({"weights": weights})
        self.weights = weights
        low, high = env.observation_space.low, env.observation_space.high
        self.observation_space = spaces.Box(np.r_[low, 0.0, 0.0].astype(np.float32),
                                            np.r_[high, 1.0, 1.0].astype(np.float32), dtype=np.float32)
        self.rng = np.random.default_rng(SEED_SALT)
        self.preference = np.array([0.5, 0.5], dtype=np.float32)

    def draw(self) -> np.ndarray:
        u = float(self.rng.uniform(0.0, 1.0))
        return np.array([u, 1.0 - u], dtype=np.float64)

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        if seed is not None:
            self.rng = np.random.default_rng([seed, SEED_SALT])
        preference = self.draw()
        obs, info = self.env.reset(seed=seed, options={**(options or {}),
                                                        "reward_weights": env_weights(preference)})
        self.preference = preference.astype(np.float32)
        return with_preference(obs, self.preference), {**info, "preference": preference.tolist()}

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        return (with_preference(obs, self.preference), reward, terminated, truncated,
                {**info, "preference": self.preference.tolist()})


def conditioned_sim_env(weights: str, **sim_env_kwargs) -> WeightConditioned:
    """A training env for SubprocVecEnv's factories: SimEnv with E5's per-episode weighting."""
    from rlscape.envs.sim_env import SimEnv
    return WeightConditioned(SimEnv(**sim_env_kwargs), weights)
