"""Train SMDP MaskablePPO on the simulator from one experiment's config (rlscape/agents/training.py).

Each seed in the config is a run, in `<out>/seed<k>/` (default `runs/<name>/`, git-ignored). A run holds its
provenance, checkpoints, TensorBoard logs, its learning curve and the decision log. `<name>` is the config's file
name, the experiment's name (OQ-62).

`--jobs N` trains N seeds at once, each in its own process (this script again, with `--seed`), its output in
`<out>/seed<k>.log`. On this machine four runs of 4 envs make about twice the decisions of one run of 16
(2026-11-09: 467 against 226 a second, the envs alone, warm): the envs of a run step together, so each step waits for
the slowest.

Usage:
    uv run python scripts/train.py --config configs/e2-ppo-sanity-ladder.yaml --jobs 4   # every seed, 4 at a time
    uv run python scripts/train.py --config configs/e2-ppo-sanity-ladder.yaml --seed 3
    uv run python scripts/train.py --config configs/e2-ppo-sanity-ladder.yaml --seed 0 \\
        --total-decisions 2000 --out runs/smoke --force                                    # a quick check
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from rlscape.agents.training import load_config, run_dir, train


def run_in_parallel(args: argparse.Namespace, seeds: list[int], config: dict) -> int:
    """Each seed in its own process, `args.jobs` at a time; the number of runs that failed."""
    waiting, running, failed = list(seeds), {}, 0
    base = [sys.executable, str(Path(__file__).resolve()), "--config", str(args.config)]
    if args.total_decisions is not None:
        base += ["--total-decisions", str(args.total_decisions)]
    if args.force:
        base.append("--force")
    while waiting or running:
        while waiting and len(running) < args.jobs:
            seed = waiting.pop(0)
            run = run_dir(config, args.config.stem, seed)
            run.parent.mkdir(parents=True, exist_ok=True)
            log = open(run.parent / f"seed{seed}.log", "w", encoding="utf-8")
            running[seed] = (subprocess.Popen([*base, "--seed", str(seed)], stdout=log, stderr=subprocess.STDOUT),
                             log)
            print(f"seed {seed}: started -> {run}", flush=True)
        time.sleep(5)
        for seed, (process, log) in list(running.items()):
            if process.poll() is not None:
                log.close()
                del running[seed]
                failed += process.returncode != 0
                print(f"seed {seed}: {'done' if process.returncode == 0 else f'failed ({process.returncode})'}",
                      flush=True)
    return failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--seed", type=int, action="append", help="a seed to run (repeatable); default: the config's")
    parser.add_argument("--jobs", type=int, default=1, help="seeds to train at once, each in its own process")
    parser.add_argument("--total-decisions", type=int, help="override the config's, for a quick check")
    parser.add_argument("--out", type=Path, help="the run's directory (one seed only)")
    parser.add_argument("--force", action="store_true", help="replace a run that exists")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.total_decisions is not None:
        config["total_decisions"] = args.total_decisions
    seeds = args.seed or list(config["seeds"])
    if args.out is not None and len(seeds) != 1:
        parser.error("--out takes one seed")
    if args.jobs > 1 and len(seeds) > 1:
        if args.out is not None:
            parser.error("--jobs writes each seed to the config's out")
        sys.exit(1 if run_in_parallel(args, seeds, config) else 0)
    for seed in seeds:
        print(train(config, args.config.stem, seed, args.out, args.force, sys.argv[1:]))


if __name__ == "__main__":
    main()
