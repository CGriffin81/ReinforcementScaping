"""Play one episode with a policy and collect what the env contract reports (§4 metrics, §6 info).

The eval harness (ROADMAP week 2: any policy × N seeds, parquet, bootstrap CIs) builds on this.

An episode keeps a trace, a row per decision (TRACE): its number, the game tick it ended at, its option and why it
ended, and the total level and net worth after it. The analysis reads time allocation, milestones and when an
activity is taken up from it, so the evaluation needn't be run again for a new question.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from rlscape.baselines.policies import Policy
from rlscape.envs.sim_env import SimEnv

TRACE = ("decision", "t1", "option", "termination", "total_level", "net_worth")


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
    start: dict = field(default_factory=dict)  # {"total_level", "total_xp", "net_worth"} at reset
    checkpoints: dict[int, dict] = field(default_factory=dict)  # hour -> {"total_level", "total_xp", "net_worth"}
    options: Counter = field(default_factory=Counter)  # option id -> times chosen
    terminations: Counter = field(default_factory=Counter)
    trace: list[tuple] = field(default_factory=list)  # a TRACE row per decision


def play(env: SimEnv, policy: Policy, seed: int, options: dict | None = None,
         max_decisions: int = 100_000) -> Episode:
    """One episode from `env.reset(seed)`. The policy is reset with the same seed; it never shares the env's random
    numbers, so a policy's lookahead can't change the episode it's playing."""
    obs, info = env.reset(seed=seed, options=options)
    policy.reset(seed)
    start = {key: info[key] for key in ("total_level", "total_xp", "net_worth")}
    episode = Episode(policy.name, seed, start=start, **start)
    skill = wealth = 0.0
    for _ in range(max_decisions):
        obs, reward, terminated, truncated, info = env.step(policy.act(env, obs))
        episode.decisions += 1
        episode.reward += reward
        skill, wealth = skill + info["reward_vec"][0], wealth + info["reward_vec"][1]
        episode.options[info["option"]["id"]] += 1
        episode.terminations[info["termination"]] += 1
        episode.checkpoints.update(info.get("checkpoints", {}))
        episode.trace.append((episode.decisions - 1, int(info["game_ticks"]), info["option"]["id"],
                              str(info["termination"]), int(info["total_level"]), float(info["net_worth"])))
        if terminated or truncated:
            break
    episode.reward_vec = (skill, wealth)
    episode.game_ticks, episode.total_level = info["game_ticks"], info["total_level"]
    episode.total_xp, episode.net_worth = info["total_xp"], info["net_worth"]
    return episode
