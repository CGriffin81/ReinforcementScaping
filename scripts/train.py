"""Train SMDP MaskablePPO on the simulator from one experiment's config (rlscape/agents/training.py).

Each seed in the config is a run, and in a sweep each (variant, seed): `<out>/[<variant>/]seed<k>/` (default
`runs/<name>/`, git-ignored). A run holds its provenance, checkpoints, TensorBoard logs, its learning curve and the
decision log. `<name>` is the config's file name, the experiment's name (OQ-62).

`--jobs N` trains N runs at once, each in its own process (this script again, with `--variant` and `--seed`), its
output in `<out>/[<variant>/]seed<k>.log`. On this machine four runs of 4 envs make about twice the decisions of one
run of 16 (2026-11-09: 467 against 226 a second, the envs alone, warm): the envs of a run step together, so each step
waits for the slowest.

Usage:
    uv run python scripts/train.py --config configs/e2-ppo-sanity-ladder.yaml --jobs 4   # every run, 4 at a time
    uv run python scripts/train.py --config configs/e2-ppo-sanity-ladder.yaml --variant <variant> --seed 3
    uv run python scripts/train.py --config configs/e2-ppo-sanity-ladder.yaml --seed 0 \\
        --total-decisions 2000 --out runs/smoke --force                                    # a quick check
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from rlscape.agents.training import load_config, run_dir, train, variants


def run_in_parallel(args: argparse.Namespace, tasks: list[tuple[str, dict, int]]) -> int:
    """Each (variant, seed) in its own process, `args.jobs` at a time; the number of runs that failed."""
    waiting, running, failed = list(tasks), {}, 0
    base = [sys.executable, str(Path(__file__).resolve()), "--config", str(args.config)]
    if args.total_decisions is not None:
        base += ["--total-decisions", str(args.total_decisions)]
    if args.force:
        base.append("--force")
    while waiting or running:
        while waiting and len(running) < args.jobs:
            variant, config, seed = waiting.pop(0)
            run = run_dir(config, args.config.stem, seed)
            run.parent.mkdir(parents=True, exist_ok=True)
            log = open(run.parent / f"seed{seed}.log", "w", encoding="utf-8")
            command = [*base, *(["--variant", variant] if variant else []), "--seed", str(seed)]
            running[(variant, seed)] = (subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT), log)
            print(f"{variant or 'run'} seed {seed}: started -> {run}", flush=True)
        time.sleep(5)
        for key, (process, log) in list(running.items()):
            if process.poll() is not None:
                log.close()
                del running[key]
                failed += process.returncode != 0
                outcome = "done" if process.returncode == 0 else f"failed ({process.returncode})"
                print(f"{key[0] or 'run'} seed {key[1]}: {outcome}", flush=True)
    return failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--seed", type=int, action="append", help="a seed to run (repeatable); default: the config's")
    parser.add_argument("--variant", action="append", help="a sweep's variant to run (repeatable); default: all")
    parser.add_argument("--jobs", type=int, default=1, help="runs to train at once, each in its own process")
    parser.add_argument("--total-decisions", type=int, help="override the config's, for a quick check")
    parser.add_argument("--out", type=Path, help="the run's directory (one run only)")
    parser.add_argument("--force", action="store_true", help="replace a run that exists")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.total_decisions is not None:
        config["total_decisions"] = args.total_decisions
    chosen = variants(config)
    if args.variant:
        unknown = sorted(set(args.variant) - {name for name, _ in chosen})
        if unknown:
            parser.error(f"unknown variants {unknown}; the sweep's: {[name for name, _ in chosen]}")
        chosen = [(name, c) for name, c in chosen if name in args.variant]
    seeds = args.seed or list(config["seeds"])
    tasks = [(name, c, seed) for name, c in chosen for seed in seeds]
    if args.out is not None and len(tasks) != 1:
        parser.error("--out takes one run")
    if args.jobs > 1 and len(tasks) > 1:
        if args.out is not None:
            parser.error("--jobs writes each run to the config's out")
        sys.exit(1 if run_in_parallel(args, tasks) else 0)
    for _, c, seed in tasks:
        print(train(c, args.config.stem, seed, args.out, args.force, sys.argv[1:]))


if __name__ == "__main__":
    main()
