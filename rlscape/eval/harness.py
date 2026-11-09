"""The eval harness (ROADMAP week 2): any policy × N seeds gives metrics at every 2-hour checkpoint, written to
parquet with bootstrap 95% confidence intervals.

- `run(policies, seeds, env_kwargs, workers)` plays every (policy, seed) episode, in worker processes when
  `workers` > 1 (each builds its env once), and returns two tables:
  - **checkpoints:** one row per (policy, seed, hour) with total level, total XP and net worth (env contract §4).
    Hour 0 is the fresh character; then every checkpoint the episode crossed (2, 4, …, 20).
  - **episodes:** one row per (policy, seed): decisions, game ticks, the undiscounted reward sums, final metrics,
    deaths, the most chosen options, and wall time.
- `summarize(checkpoints)`: per (policy, hour, metric), the mean over seeds with a percentile-bootstrap 95% CI.
- `paired_difference(checkpoints, a, b, metric)`: per hour, policy a minus policy b on the same seeds. Episodes with
  the same seed start the same way, so the difference is paired; its CI is a bootstrap over seeds too.
- `save(out_dir, ...)` writes the tables as parquet, plus `config.json`: the run's config, its hash, the git SHAs of
  this repo and the server submodule (and whether the tree had uncommitted changes), package versions, and any
  `extra` provenance (scripts/evaluate.py adds its command line). `extra` isn't hashed: the hash names what was run,
  not how it was asked for. `started` is `provenance()` taken when the run began (evaluate.py takes it), so a tree
  changed or committed during a long run doesn't change what's recorded; without it, it's taken at the save.

An episode's result depends only on its policy and seed, never on the number of workers.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import time
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from rlscape.baselines import GreedyPolicy, Policy, RandomPolicy
from rlscape.baselines.guide import ScriptedGuidePolicy
from rlscape.envs.sim_env import SimEnv
from rlscape.eval.rollout import play

REPO = Path(__file__).resolve().parents[2]
METRICS = ("total_level", "total_xp", "net_worth")
POLICIES: dict[str, Callable[[], Policy]] = {
    "random": RandomPolicy,
    "greedy_xp": lambda: GreedyPolicy("xp"),
    "greedy_wealth": lambda: GreedyPolicy("wealth"),
    "greedy_skill": lambda: GreedyPolicy("skill"),
    "scripted_guide": ScriptedGuidePolicy,  # reviewed by Caleb, 2026-10-31 (docs/scripted-guide-draft.md)
}
N_BOOT = 10_000

_env: SimEnv | None = None  # one per worker process


def _init(env_kwargs: dict) -> None:
    global _env
    _env = SimEnv(**env_kwargs)


def _episode(policy_name: str, seed: int) -> tuple[list[dict], dict]:
    started = time.perf_counter()
    episode = play(_env, POLICIES[policy_name](), seed)
    rows = [{"policy": policy_name, "seed": seed, "hour": 0, **episode.start}]
    rows += [{"policy": policy_name, "seed": seed, "hour": hour, **values}
             for hour, values in sorted(episode.checkpoints.items())]
    summary = {
        "policy": policy_name, "seed": seed, "decisions": episode.decisions, "game_ticks": episode.game_ticks,
        "reward": episode.reward, "r_skill": episode.reward_vec[0], "r_wealth": episode.reward_vec[1],
        "total_level": episode.total_level, "total_xp": episode.total_xp, "net_worth": episode.net_worth,
        "deaths": episode.terminations.get("died", 0),
        "top_options": "; ".join(f"{o} {n}" for o, n in episode.options.most_common(5)),
        "wall_seconds": time.perf_counter() - started,
    }
    return rows, summary


def run(policies: Sequence[str], seeds: Iterable[int], env_kwargs: dict | None = None,
        workers: int = 1) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Play every (policy, seed) episode; returns (checkpoints, episodes), sorted by policy then seed."""
    unknown = [p for p in policies if p not in POLICIES]
    if unknown:
        raise ValueError(f"unknown policies {unknown}; known: {sorted(POLICIES)}")
    env_kwargs = env_kwargs or {}
    tasks = [(policy, seed) for policy in policies for seed in seeds]
    if workers <= 1:
        _init(env_kwargs)
        results = [_episode(*task) for task in tasks]
    else:
        with ProcessPoolExecutor(workers, initializer=_init, initargs=(env_kwargs,)) as pool:
            results = list(pool.map(_episode, *zip(*tasks)))
    checkpoints = pd.DataFrame([row for rows, _ in results for row in rows])
    episodes = pd.DataFrame([summary for _, summary in results])
    return (_in_order(checkpoints, policies, ["policy", "seed", "hour"]),
            _in_order(episodes, policies, ["policy", "seed"]))


def _in_order(table: pd.DataFrame, policies: Sequence[str], columns: list[str]) -> pd.DataFrame:
    """Sorted by `columns`, with policies in the order they were asked for rather than alphabetical."""
    rank = {policy: i for i, policy in enumerate(policies)}
    return table.sort_values(columns, key=lambda c: c.map(rank) if c.name == "policy" else c, ignore_index=True)


def bootstrap_ci(values: Sequence[float], rng: np.random.Generator, n_boot: int = N_BOOT) -> tuple[float, float]:
    """Percentile-bootstrap 95% CI of the mean; NaN with fewer than 2 values."""
    x = np.asarray(values, dtype=float)
    if len(x) < 2:
        return float("nan"), float("nan")
    means = x[rng.integers(0, len(x), size=(n_boot, len(x)))].mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return float(low), float(high)


def summarize(checkpoints: pd.DataFrame, n_boot: int = N_BOOT, seed: int = 0) -> pd.DataFrame:
    """One row per (policy, hour, metric): seeds, mean, the CI, and the standard deviation over seeds."""
    rng, rows = np.random.default_rng(seed), []
    for (policy, hour), group in checkpoints.groupby(["policy", "hour"], sort=False):
        for metric in METRICS:
            values = group[metric].to_numpy(dtype=float)
            low, high = bootstrap_ci(values, rng, n_boot)
            rows.append({"policy": policy, "hour": hour, "metric": metric, "seeds": len(values),
                         "mean": values.mean(), "ci_low": low, "ci_high": high,
                         "std": values.std(ddof=1) if len(values) > 1 else float("nan")})
    return pd.DataFrame(rows)


def paired_difference(checkpoints: pd.DataFrame, a: str, b: str, metric: str, n_boot: int = N_BOOT,
                      seed: int = 0) -> pd.DataFrame:
    """Per hour: the mean of (a − b) over the seeds both policies ran, with its CI."""
    pivot = checkpoints[checkpoints.policy.isin([a, b])].pivot_table(index=["hour", "seed"], columns="policy",
                                                                      values=metric).dropna()
    rng, rows = np.random.default_rng(seed), []
    for hour, group in pivot.groupby(level="hour"):
        diff = (group[a] - group[b]).to_numpy()
        low, high = bootstrap_ci(diff, rng, n_boot)
        rows.append({"hour": hour, "metric": metric, "a": a, "b": b, "seeds": len(diff), "mean": diff.mean(),
                     "ci_low": low, "ci_high": high})
    return pd.DataFrame(rows)


def _git(*args: str, cwd: Path = REPO) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def provenance() -> dict:
    return {
        "git_sha": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "server_sha": _git("rev-parse", "HEAD", cwd=REPO / "server"),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }


def config_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()[:12]


def save(out_dir: Path, config: dict, checkpoints: pd.DataFrame, episodes: pd.DataFrame,
         summary: pd.DataFrame, extra: dict | None = None, started: dict | None = None) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoints.to_parquet(out_dir / "checkpoints.parquet", index=False)
    episodes.to_parquet(out_dir / "episodes.parquet", index=False)
    summary.to_parquet(out_dir / "summary.parquet", index=False)
    meta = {"config": config, "config_hash": config_hash(config), **(started or provenance()), **(extra or {})}
    (out_dir / "config.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    return out_dir
