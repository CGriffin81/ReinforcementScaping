"""Play one episode with a policy and collect what the env contract reports (§4 metrics, §6 info).

The eval harness (ROADMAP week 2: any policy × N seeds, parquet, bootstrap CIs) builds on this.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from rlscape.baselines.policies import Policy
from rlscape.envs.sim_env import SimEnv


@dataclass
class Episode:
    policy: str
    seed: int
    decisions: int = 0
    game_ticks: int = 0
    reward: float = 0.0  # undiscounted sum of the weighted reward
    reward_vec: tuple[float, float] = (0.0, 0.0)  # undiscounted sums of (r_skill, r_wealth)
    total_level: int = 0
    total_xp: float = 0.0  # each skill's XP up to level 99's
    net_worth: float = 0.0
    checkpoints: dict[int, dict] = field(default_factory=dict)  # hour -> {"total_level", "total_xp", "net_worth"}
    options: Counter = field(default_factory=Counter)  # option id -> times chosen
    terminations: Counter = field(default_factory=Counter)


def play(env: SimEnv, policy: Policy, seed: int, options: dict | None = None,
         max_decisions: int = 100_000) -> Episode:
    """One episode from `env.reset(seed)`. The policy is reset with the same seed; it never shares the env's random
    numbers, so a policy's lookahead can't change the episode it's playing."""
    obs, info = env.reset(seed=seed, options=options)
    policy.reset(seed)
    episode = Episode(policy.name, seed, total_level=info["total_level"], total_xp=info["total_xp"],
                      net_worth=info["net_worth"])
    skill = wealth = 0.0
    for _ in range(max_decisions):
        obs, reward, terminated, truncated, info = env.step(policy.act(env, obs))
        episode.decisions += 1
        episode.reward += reward
        skill, wealth = skill + info["reward_vec"][0], wealth + info["reward_vec"][1]
        episode.options[info["option"]["id"]] += 1
        episode.terminations[info["termination"]] += 1
        episode.checkpoints.update(info.get("checkpoints", {}))
        if terminated or truncated:
            break
    episode.reward_vec = (skill, wealth)
    episode.game_ticks, episode.total_level = info["game_ticks"], info["total_level"]
    episode.total_xp, episode.net_worth = info["total_xp"], info["net_worth"]
    return episode
