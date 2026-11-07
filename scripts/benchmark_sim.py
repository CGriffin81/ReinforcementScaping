"""Benchmark: how many decisions per second the simulator makes (ROADMAP week 2; env contract §7's target is at least
20k decisions per second across the training workers).

Each worker process runs SimEnv episodes of masked random actions for a fixed wall-clock time, starting a new episode
at the horizon. A decision is one `step` plus the `action_masks` that chose it, as an agent's rollout makes them; the
observation comes with the step. Workers start together, so the total is what that many cores give at once.

Usage:
    uv run python scripts/benchmark_sim.py [--seconds 60] [--workers 1 4 16]
"""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]


def worker(seed: int, seconds: float) -> dict[str, float]:
    from rlscape.envs import SimEnv  # imported here so the parent only pays for it once per worker

    env = SimEnv()
    rng = np.random.default_rng(seed)
    env.reset(seed=seed)
    decisions, episodes, game_ticks = 0, 0, 0
    start = time.perf_counter()
    while time.perf_counter() - start < seconds:
        _, _, _, truncated, info = env.step(int(rng.choice(np.flatnonzero(env.action_masks()))))
        decisions += 1
        game_ticks += info["duration"]
        if truncated:
            episodes += 1
            env.reset()
    elapsed = time.perf_counter() - start
    return {"decisions": decisions, "seconds": elapsed, "episodes": episodes, "game_ticks": game_ticks}


def run(workers: int, seconds: float) -> dict[str, float]:
    with ProcessPoolExecutor(workers) as pool:
        results = list(pool.map(worker, range(workers), [seconds] * workers))
    decisions = sum(r["decisions"] for r in results)
    return {
        "workers": workers,
        "decisions_per_second": decisions / max(r["seconds"] for r in results),
        "per_worker": decisions / sum(r["seconds"] for r in results),
        "decisions": decisions,
        "episodes_finished": sum(r["episodes"] for r in results),
        "game_hours_per_second": sum(r["game_ticks"] for r in results) / 6000 / max(r["seconds"] for r in results),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 4, 16])
    args = parser.parse_args()
    rows = []
    for n in args.workers:
        r = run(n, args.seconds)
        rows.append(r)
        print(f"{n:3d} workers: {r['decisions_per_second']:8.0f} decisions/s ({r['per_worker']:.0f} per worker), "
              f"{r['game_hours_per_second']:.1f} game-hours/s, {r['episodes_finished']} episodes")
    out = REPO / "results" / "benchmark" / f"sim-speed-{datetime.now():%Y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"seconds": args.seconds, "cpu_count": os.cpu_count(), "runs": rows}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
