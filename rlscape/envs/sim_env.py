"""SimEnv: the surrogate simulator behind the env contract's Gymnasium interface (env contract §2).

- `reset(seed, options)` starts a fresh character (§1). `options["reward_weights"] = (w_s, w_b)` sets the episode's
  weights; otherwise the env's defaults. Seeding follows Gymnasium: a seed reseeds the env, and later resets
  without one continue from it, so a seeded run of episodes is reproducible.
- `step(action)` runs one option and returns its reward w_s·r_skill + w_b·r_wealth; `info` holds the unweighted pair
  (`reward_vec`) and the rest of §6. A masked action raises instead of being a silent no-op. Episodes end only by
  truncation at the horizon (death doesn't end them, §1).
- `action_masks()` is the mask for the current state, for sb3-contrib's MaskablePPO.
- `option_catalog()` lists the actions in id order.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from rlscape.envs.encoding import ObsEncoder
from rlscape.sim import build_catalog
from rlscape.sim.engine import ACTIVITY_TICKS, HORIZON_TICKS, Simulator
from rlscape.vocabulary import vocabulary as default_vocabulary

DEFAULT_REWARD_WEIGHTS = (0.5, 0.5)


@dataclass(frozen=True)
class OptionSpec:
    action: int
    id: str
    family: str


class SimEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, vocabulary: Iterable[int] | None = None, activity_ticks: int = ACTIVITY_TICKS,
                 horizon_ticks: int = HORIZON_TICKS, reward_weights: tuple[float, float] = DEFAULT_REWARD_WEIGHTS,
                 preference_in_obs: bool = False):
        vocabulary = default_vocabulary() if vocabulary is None else tuple(vocabulary)  # the catalog's V by default
        self.options = build_catalog(vocabulary, activity_ticks)
        self.sim = Simulator(self.options, activity_ticks, horizon_ticks)
        self.encoder = ObsEncoder(self.options, vocabulary, horizon_ticks, preference_in_obs)
        self.default_weights = tuple(reward_weights)
        self.weights = self.default_weights
        self.action_space = spaces.Discrete(len(self.options))
        self.observation_space = spaces.Box(0.0, 1.0, (self.encoder.size,), np.float32)
        self._mask: np.ndarray | None = None

    def reset(self, *, seed: int | None = None, options: dict | None = None) -> tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        self.weights = tuple((options or {}).get("reward_weights", self.default_weights))
        state = self.sim.reset(seed=int(self.np_random.integers(2**63 - 1)))
        return self.observe(), {"game_ticks": state.tick, "total_level": state.total_level(),
                                "total_xp": state.total_xp(), "net_worth": state.net_worth(), "coins": state.coins()}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        result = self.sim.step(int(action))
        r_skill, r_wealth = result.reward_vec
        reward = self.weights[0] * r_skill + self.weights[1] * r_wealth
        return self.observe(), float(reward), result.terminated, result.truncated, result.info

    def action_masks(self) -> np.ndarray:
        return self._mask.copy()

    def option_catalog(self) -> list[OptionSpec]:
        return [OptionSpec(i, o.id, o.family) for i, o in enumerate(self.options)]

    def observe(self) -> np.ndarray:
        """The observation for the current state, refreshing the mask. `reset` and `step` call it; call it yourself
        after editing `sim.state` directly (tests, calibration setup), so the mask matches the state."""
        # The mask first: the combat candidates in the observation reuse the ranking it just made.
        self._mask = self.sim.action_mask()
        return self.encoder.encode(self.sim.state, self._mask, self.weights)
