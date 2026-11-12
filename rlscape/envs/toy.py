"""E2's rung 1 (OQ-65 (1), Caleb, 2026-11-09): a synthetic three-option SMDP with an exact optimum, to check that SMDP
MaskablePPO (γ_hr^τ discounting, masking) learns a delayed-payoff investment before it's trusted on the sim.

An episode is 20 game-hours (HORIZON ticks, as the sim's). Each decision is one of three options:
- **work** (15 game-minutes) pays (1 + √k) an hour worked, k being the trainings done;
- **train** (15 game-minutes) pays nothing and adds one to k. It's masked at K_MAX;
- **idle** (1 game-minute) pays nothing.

An option the horizon cuts short takes the ticks left (work's pay pro rata), as in the sim. Training costs working time
now and pays back over what's left, so the best policy trains first and then works. With γ_hr 0.99 it trains 22 times
(`optimum`), for a return about four times always working's. The observation is the elapsed share of the horizon and
k / K_MAX. `info` has the duration (the SMDP buffer reads it) and the reward.
"""

from __future__ import annotations

from functools import cache

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from rlscape.agents.smdp import TICKS_PER_HOUR

HORIZON = 20 * TICKS_PER_HOUR
WORK, TRAIN, IDLE = 0, 1, 2
OPTIONS = ("work", "train", "idle")
TICKS = (1_500, 1_500, 100)
K_MAX = 40
UNIT = 100  # every duration is a whole number of these, so the optimum's table is exact


def pay(k: int) -> float:
    """Work's pay an hour after k trainings."""
    return 1.0 + float(np.sqrt(k))


def step_of(t: int, k: int, action: int) -> tuple[int, int, float]:
    """(ticks taken, k after, reward) of `action` at tick t with k trainings: the horizon cuts it short."""
    ticks = min(TICKS[action], HORIZON - t)
    if action == WORK:
        return ticks, k, pay(k) * ticks / TICKS_PER_HOUR
    if action == TRAIN:
        return ticks, k + 1, 0.0
    return ticks, k, 0.0


class ToyEnv(gym.Env):
    def __init__(self):
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(0.0, 1.0, (2,), np.float32)
        self.t = self.k = 0

    def _obs(self) -> np.ndarray:
        return np.array([self.t / HORIZON, self.k / K_MAX], dtype=np.float32)

    def action_masks(self) -> np.ndarray:
        return np.array([True, self.k < K_MAX, True])

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.t = self.k = 0
        return self._obs(), {}

    def step(self, action: int):
        if not self.action_masks()[action]:
            raise ValueError(f"{OPTIONS[action]} is masked")
        ticks, self.k, reward = step_of(self.t, self.k, int(action))
        self.t += ticks
        truncated = self.t >= HORIZON
        return self._obs(), reward, False, truncated, {"duration": ticks, "option": OPTIONS[action]}


def discount(ticks: int, gamma_hr: float) -> float:
    return gamma_hr ** (ticks / TICKS_PER_HOUR)


@cache
def _table(gamma_hr: float) -> tuple[np.ndarray, np.ndarray]:
    """V[t / UNIT, k], the best discounted return from tick t with k trainings, and the best action there."""
    n = HORIZON // UNIT
    value, best = np.zeros((n + 1, K_MAX + 1)), np.zeros((n + 1, K_MAX + 1), dtype=int)
    for i in range(n - 1, -1, -1):
        for k in range(K_MAX + 1):
            choices = []
            for action in (WORK, TRAIN, IDLE):
                if action == TRAIN and k >= K_MAX:
                    choices.append(-np.inf)
                    continue
                ticks, k2, reward = step_of(i * UNIT, k, action)
                choices.append(reward + discount(ticks, gamma_hr) * value[i + ticks // UNIT, k2])
            best[i, k] = int(np.argmax(choices))
            value[i, k] = choices[best[i, k]]
    return value, best


def optimum(gamma_hr: float) -> dict:
    """The optimal policy from the start: its discounted and undiscounted returns and how many times it trains."""
    value, best = _table(gamma_hr)
    t = k = 0
    undiscounted, trainings = 0.0, 0
    while t < HORIZON:
        action = int(best[t // UNIT, k])
        ticks, k, reward = step_of(t, k, action)
        undiscounted += reward
        trainings += action == TRAIN
        t += ticks
    return {"discounted": float(value[0, 0]), "undiscounted": undiscounted, "trainings": trainings}


def returns_of(actions: list[int], gamma_hr: float) -> dict:
    """An episode's discounted and undiscounted returns and trainings, from its actions."""
    t = k = 0
    discounted = undiscounted = 0.0
    for action in actions:
        ticks, k, reward = step_of(t, k, action)
        discounted += discount(t, gamma_hr) * reward
        undiscounted += reward
        t += ticks
    return {"discounted": discounted, "undiscounted": undiscounted, "trainings": sum(a == TRAIN for a in actions)}
