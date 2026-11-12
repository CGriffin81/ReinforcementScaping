"""Normalised reward weights (OQ-67, Caleb, 2026-11-10): E3 to E6 give their weights in units of E1's best 20-hour gain
on each objective, and this turns them into SimEnv's weights.

SimEnv's reward is w_s·r_skill + w_b·r_wealth, with r_skill in levels and r_wealth = Δ net worth / 100,000 gp (env
contract §4). At that scale a level outweighs 100,000 gp: E1's greedy GP/hr gains 1.89M gp in 20 hours, worth 18.9,
less than random's 185 levels, so (.5, .5) and even (.25, .75) reward skill only (E2's agents learned nothing else).

**The units** are the ideal point of E1's baselines on sim v1.2 (`results/summary/e1-baselines/episodes.csv`, the
mean over its 30 seeds of each policy's 20-hour reward sum; E1 rerun on 2026-11-11 after OQ-75):
- skill: the guide's 323.87 levels (`SKILL_UNIT`), the same as on v1.1;
- wealth: greedy GP/hr's 1,763,863 gp, 17.64 in r_wealth (`WEALTH_UNIT`); 18.90 on v1.1, before the fletch slot
  drew greedy GP/hr to arrow shafts at times.

**The conversion** keeps a level worth u_s: normalised weights (u_s, u_b) on the simplex give env weights
(u_s, u_b·SKILL_UNIT/WEALTH_UNIT), so the env's reward is SKILL_UNIT times
u_s·(r_skill/SKILL_UNIT) + u_b·(r_wealth/WEALTH_UNIT). The normalised (.5, .5) is env (.5, 9.18). Rescaling a
reward term picks the same policies as moving the weights, so this changes no sim: it's where the weights sit. The
normalised (.5, .5) was env (.5, 8.57) on v1.1; on v1.2 it's (.5, 9.18).

Not yet handled: E5's observation shows SimEnv's weights (`preference_in_obs`), which this leaves unnormalised.
"""

from __future__ import annotations

from collections.abc import Sequence

SKILL_UNIT = 323.86592398083445   # levels: the guide's mean 20-hour r_skill in E1 (sim v1.2, as on v1.1)
WEALTH_UNIT = 17.638633333333416  # r_wealth (100,000 gp): greedy GP/hr's mean 20-hour r_wealth in E1 (sim v1.2)
WEALTH_FACTOR = SKILL_UNIT / WEALTH_UNIT  # about 18.36 (17.13 on v1.1): an env w_b per normalised u_b
E1_SUMMARY = "results/summary/e1-baselines/episodes.csv"


def _pair(weights: Sequence[float]) -> tuple[float, float]:
    pair = tuple(float(w) for w in weights)
    if len(pair) != 2 or min(pair) < 0:
        raise ValueError(f"weights must be two non-negative numbers, not {list(weights)}")
    return pair


def env_weights(normalised: Sequence[float]) -> tuple[float, float]:
    """SimEnv's (w_s, w_b) for normalised weights (u_s, u_b), which must sum to 1."""
    u_s, u_b = _pair(normalised)
    if abs(u_s + u_b - 1) > 1e-9:
        raise ValueError(f"normalised weights must sum to 1, not {u_s + u_b:g} ({[u_s, u_b]})")
    return u_s, u_b * WEALTH_FACTOR


def normalised_weights(env: Sequence[float]) -> tuple[float, float]:
    """The normalised (u_s, u_b), summing to 1, that SimEnv's (w_s, w_b) stand for."""
    w_s, w_b = _pair(env)
    u_b = w_b / WEALTH_FACTOR
    if w_s + u_b == 0:
        raise ValueError("weights (0, 0) stand for no objective")
    return w_s / (w_s + u_b), u_b / (w_s + u_b)
