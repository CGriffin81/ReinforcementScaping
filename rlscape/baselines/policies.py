"""E1 baselines (ROADMAP week 2): a masked random policy and greedy policies.

A policy is reset with a seed at the start of each episode and asked for an action with the environment in hand.
Baselines read the simulator's state through it; a learned policy would use only the observation and the mask.

- **Random:** uniform over the actions the mask allows.
- **Greedy:** one-step lookahead on expected rates at the current state. Each allowed option is run `samples` times
  on a copy of the character, with the policy's own random numbers, and scored by its mean gain per mean game tick:
  - `skill`: r_skill, the gain in Σ (level + progress to the next level), the quantity total level tracks;
  - `wealth`: the gain in net worth, r_wealth's numerator (GP/hr);
  - `xp`: raw experience summed over skills (XP/hr), each skill counted up to level 99's XP, as total XP is
    reported.
  E1 uses `xp` and `wealth` (Caleb, 2026-10-30: raw XP, because some levels are breakpoints worth climbing to, and a
  level-based measure would undervalue the higher skills that reach them). `skill` stays for comparison.
  It takes the best positive rate. When no option gains anything (a full inventory, say), it banks if it can, as a
  player would, and otherwise takes the least bad option. Loot-mode actions are never chosen: they gain nothing
  themselves, so a greedy policy can't value them, and switching modes back and forth would waste decisions.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Protocol

import numpy as np

from rlscape.envs.sim_env import SimEnv
from rlscape.sim.engine import WEALTH_SCALE, Simulator

OBJECTIVES = ("skill", "wealth", "xp")
FALLBACK = "bank_deposit"


class Policy(Protocol):
    name: str

    def reset(self, seed: int | None) -> None: ...

    def act(self, env: SimEnv, obs: np.ndarray) -> int: ...


class RandomPolicy:
    name = "random"

    def __init__(self) -> None:
        self.rng = np.random.default_rng()

    def reset(self, seed: int | None) -> None:
        self.rng = np.random.default_rng(seed)

    def act(self, env: SimEnv, obs: np.ndarray) -> int:
        return int(self.rng.choice(np.flatnonzero(env.action_masks())))


def e1_baselines() -> list[Policy]:
    """E1's baselines: masked random, greedy XP/hr (raw XP) and greedy GP/hr (net worth). The scripted guide joins
    once Caleb has reviewed it."""
    return [RandomPolicy(), GreedyPolicy("xp"), GreedyPolicy("wealth")]


class GreedyPolicy:
    def __init__(self, objective: str, samples: int = 2):
        if objective not in OBJECTIVES:
            raise ValueError(f"objective must be one of {OBJECTIVES}")
        self.objective, self.samples = objective, samples
        self.name = f"greedy_{objective}"
        self.rng = np.random.default_rng()

    def reset(self, seed: int | None) -> None:
        self.rng = np.random.default_rng(seed)

    def estimates(self, env: SimEnv) -> dict[int, float]:
        """Action -> expected gain per game tick, for every allowed action greedy considers."""
        sim, mask = env.sim, env.action_masks()
        lookahead = Simulator(sim.options, sim.activity_ticks, sim.horizon_ticks)
        out = {}
        for action in np.flatnonzero(mask):
            if sim.options[action].family == "loot":
                continue
            gained = ticks = 0.0
            for _ in range(self.samples):
                lookahead.state, lookahead.rng = deepcopy(sim.state), self.rng
                result = lookahead.step(int(action))
                gained += self._gain(result, sim.state)
                ticks += result.info["duration"]
            out[int(action)] = gained / ticks
        return out

    def act(self, env: SimEnv, obs: np.ndarray) -> int:
        rates = self.estimates(env)
        best = max(rates, key=lambda a: (rates[a], -a))  # ties go to the lowest action id
        if rates[best] > 0:
            return best
        fallback = next((a for a in rates if env.options[a].id == FALLBACK), None)
        return best if fallback is None else fallback

    def _gain(self, result, before) -> float:
        if self.objective == "skill":
            return result.reward_vec[0]
        if self.objective == "wealth":
            return result.reward_vec[1] * WEALTH_SCALE  # gp
        return result.info["total_xp"] - before.total_xp()
