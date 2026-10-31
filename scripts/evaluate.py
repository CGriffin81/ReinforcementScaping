"""Evaluate policies on the simulator over many seeds (the eval harness, rlscape/eval/harness.py).

Writes checkpoints.parquet, episodes.parquet, summary.parquet and config.json to the output directory, and prints
each policy's metrics at the last checkpoint with bootstrap 95% CIs.

Usage:
    uv run python scripts/evaluate.py --policies random greedy_xp greedy_wealth --seeds 10 --workers 8
    uv run python scripts/evaluate.py --policies random --seeds 5 --hours 4 --out results/smoke
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from rlscape.envs.sim_env import DEFAULT_REWARD_WEIGHTS
from rlscape.eval.harness import POLICIES, REPO, run, save, summarize
from rlscape.sim.engine import ACTIVITY_TICKS, TICKS_PER_HOUR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--policies", nargs="+", default=["random", "greedy_xp", "greedy_wealth"],
                        choices=sorted(POLICIES))
    parser.add_argument("--seeds", type=int, default=10, help="seeds 0 .. N-1")
    parser.add_argument("--first-seed", type=int, default=0)
    parser.add_argument("--hours", type=float, default=20.0, help="the horizon in game-hours")
    parser.add_argument("--activity-minutes", type=float, default=ACTIVITY_TICKS / 100, help="D, the option length")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--out", type=Path, default=None, help="default: results/eval/<UTC time>")
    args = parser.parse_args()

    seeds = list(range(args.first_seed, args.first_seed + args.seeds))
    env_kwargs = {"horizon_ticks": round(args.hours * TICKS_PER_HOUR),
                  "activity_ticks": round(args.activity_minutes * 100)}
    config = {"backend": "sim", "policies": args.policies, "seeds": seeds, "env": env_kwargs,
              "reward_weights": list(DEFAULT_REWARD_WEIGHTS)}
    out = args.out or REPO / "results" / "eval" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    started = time.perf_counter()
    checkpoints, episodes = run(args.policies, seeds, env_kwargs, args.workers)
    summary = summarize(checkpoints)
    save(out, config, checkpoints, episodes, summary)
    print(f"{len(episodes)} episodes in {time.perf_counter() - started:.0f}s -> {out}", file=sys.stderr)

    last = summary[summary.hour == summary.hour.max()]
    print(f"\nAt hour {last.hour.max()} ({len(seeds)} seeds; mean [95% CI]):")
    for policy in args.policies:
        rows = last[last.policy == policy].set_index("metric")
        cells = [f"{m} {rows.loc[m, 'mean']:,.0f} [{rows.loc[m, 'ci_low']:,.0f}, {rows.loc[m, 'ci_high']:,.0f}]"
                 for m in rows.index]
        print(f"  {policy:14s} " + "; ".join(cells))


if __name__ == "__main__":
    main()
