"""SMDP returns and advantages (ROADMAP §3, "SMDP discounting"; CLAUDE.md: "Use γ^τ, with τ in game time, in GAE and
in PBRS").

Options run for different lengths of game time, so one discount a decision would discount a 2-minute bank trip as
much as a 40-minute woodcutting trip. Here the discount is set per game-hour (γ_hr, e.g. 0.5, 0.9 or 0.99, the E5
sweep's values), and a decision that took τ game-hours is discounted by γ_hr^τ. The env reports τ in ticks as
`info["duration"]` (env contract §4; a game-hour is TICKS_PER_HOUR = 6,000 ticks).

GAE (Schulman et al. 2016) with that discount, over a rollout of T decisions in each of N envs:
    d_t = γ_hr^(τ_t / 6000) · (1 − done_t)
    δ_t = r_t + d_t · V(s_{t+1}) − V(s_t)
    A_t = δ_t + λ · d_t · A_{t+1}
    R_t = A_t + V(s_t)            (the value target)
with V(s_T) the bootstrap value after the rollout's last decision. `done_t` is the episode ending at decision t
(terminated or truncated alike, as sb3's buffers have it; a time limit's value is bootstrapped by the caller, as
sb3 does, through r_t).

Two choices (Claude's, reversible, for Caleb's review):
- λ applies once per decision, not per game-hour: it trades bias for variance over the decisions a return spans.
- An option's reward is taken at its start, undiscounted within the option (the env reports the option's total, as
  the plan has it: δ_t = r_t + γ^τ V(s′) − V(s)). Discounting it within the option would need the reward's timing.

The decision floor (2026-11-15, the collapse diagnosis; Caleb's test): with `floor_ticks` m, a decision is discounted
as if it took at least m ticks, γ_hr^(max(τ, m) / 6000). Without it, an option that changes nothing and takes a tick
costs a policy only that tick of game time, about 0.01 reward at γ_hr 0.9, less than the critic's error; PPO then
chose between looping such options and acting on noise. With the floor, a loop costs about V·(1 − γ_hr^(m/6000)) a
decision. It changes the objective only for options shorter than m. PBRS takes the same floor, so that its shaping
stays the agent's own discount.

This module is the math, in numpy, for the rollout buffer that MaskablePPO will use (a subclass of sb3-contrib's
`MaskableRolloutBuffer` storing τ), and for PBRS's γ^τ.
"""

from __future__ import annotations

import numpy as np

TICKS_PER_HOUR = 6_000  # 600 ms ticks: a game-hour


def option_discounts(durations: np.ndarray, gamma_hr: float, floor_ticks: float = 0.0) -> np.ndarray:
    """γ_hr^τ for each decision, τ its duration in game-hours (`durations` in ticks), or at least `floor_ticks`."""
    if not 0.0 < gamma_hr <= 1.0:
        raise ValueError(f"gamma_hr must be in (0, 1], not {gamma_hr}")
    if floor_ticks < 0:
        raise ValueError(f"floor_ticks can't be negative, not {floor_ticks}")
    durations = np.asarray(durations, dtype=np.float64)
    if (durations < 0).any():
        raise ValueError("durations can't be negative")
    return np.power(gamma_hr, np.maximum(durations, floor_ticks) / TICKS_PER_HOUR)


def smdp_gae(rewards: np.ndarray, values: np.ndarray, durations: np.ndarray, dones: np.ndarray,
             last_values: np.ndarray, gamma_hr: float, gae_lambda: float,
             floor_ticks: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Advantages and value targets for a rollout of shape (T, N): T decisions in each of N envs.

    `dones[t]` is True where the episode ended at decision t (so nothing after it is bootstrapped into it), and
    `last_values` (N,) is V of the state after decision T − 1 (ignored where dones[T − 1])."""
    rewards, values = np.asarray(rewards, dtype=np.float64), np.asarray(values, dtype=np.float64)
    dones, last_values = np.asarray(dones, dtype=bool), np.asarray(last_values, dtype=np.float64)
    if not rewards.shape == values.shape == dones.shape == np.shape(durations):
        raise ValueError("rewards, values, durations and dones must share one (T, N) shape")
    if not 0.0 <= gae_lambda <= 1.0:
        raise ValueError(f"gae_lambda must be in [0, 1], not {gae_lambda}")
    discount = option_discounts(durations, gamma_hr, floor_ticks) * ~dones
    next_values = np.concatenate([values[1:], last_values[None]], axis=0)
    deltas = rewards + discount * next_values - values
    advantages = np.zeros_like(rewards)
    running = np.zeros(rewards.shape[1:])
    for t in reversed(range(rewards.shape[0])):
        running = deltas[t] + gae_lambda * discount[t] * running
        advantages[t] = running
    return advantages, advantages + values


def pbrs_bonus(phi: np.ndarray, phi_next: np.ndarray, durations: np.ndarray, dones: np.ndarray,
               gamma_hr: float, floor_ticks: float = 0.0) -> np.ndarray:
    """Potential-based shaping in an SMDP (ROADMAP §3, "PBRS in an SMDP"): F = γ_hr^τ · Φ(s′) − Φ(s), with Φ of a
    terminal state 0, so the agent's own discount keeps the optimal policy (Ng et al. 1999)."""
    phi_next = np.where(np.asarray(dones, dtype=bool), 0.0, np.asarray(phi_next, dtype=np.float64))
    return option_discounts(durations, gamma_hr, floor_ticks) * phi_next - np.asarray(phi, dtype=np.float64)
