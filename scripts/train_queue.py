"""Train several experiments from one queue, each run in its own experiment's worktree, keeping the machine's training
runs at --jobs (ROADMAP's finishing plan: E6a, E4, E6b and E5, started in E3's slots as they free).

An experiment is its config's path in its worktree, e.g. `D:/ReinforcementScaping-e4/configs/e4-rnd-exploration.yaml`
(OQ-61: an experiment's branch holds its config and the code only it uses). Each run is trained there by that
worktree's own scripts/train.py and venv, as train.py --jobs would train it:

    <worktree>/.venv/Scripts/python.exe <worktree>/scripts/train.py --config <config> [--variant <v>] --seed <k>

so it records its own branch's provenance, with its output in `<run>.log` beside its directory.

- **Slots.** --jobs is the most training runs on the machine at once, counting the ones this queue didn't start (E3's,
  while it finishes). A training run is a process running scripts/train.py with --seed, read from the process table
  every --poll seconds; its envs' processes aren't counted. A slot must stay free for --settle seconds before the queue
  takes it, so a launcher that starts its next run a few seconds after one ends (train.py --jobs checks every 5 s)
  keeps it.
- **Order** (--order). `seeds`, the default: seed 0 of every experiment and variant, then seed 1, and so on, so every
  experiment has its first seeds early, and about the same number of seeds if the machine is needed before the end.
  `experiments`: each experiment's runs in turn.
- **Resuming.** A run with its run.json is done and is skipped. A run training now is left to finish. A run with a
  directory but no run.json, and not training, was stopped part-way. The queue refuses to start and names the run,
  unless --restart-partial is given: then it trains the run again from the start (train.py --force).
- **Checks first.** Each worktree lists its runs with its own trainer (load_config, variants, run_dir) by `uv run
  --frozen`, one worktree at a time. That checks the config by its branch's own rules, and syncs the worktree's venv
  before any run starts there. The queue refuses a worktree with uncommitted changes (publish_training would refuse
  its runs), unless --allow-dirty is given. It also refuses worktrees on different server commits, since the sim
  reads the server's data.
- **--dry-run** prints the plan and each run's state (waiting, training, partial, done), and starts nothing. It's
  safe to run while a queue trains, to see where it is.

Stopping the queue (its PID) leaves its runs training. Starting it again with the same experiments carries on: it
counts those runs in its slots and skips them.

Usage:
    uv run python scripts/train_queue.py --jobs 4 --dry-run \\
        D:/ReinforcementScaping-e6a/configs/e6a-discount-sweep.yaml \\
        D:/ReinforcementScaping-e4/configs/e4-rnd-exploration.yaml
    uv run python scripts/train_queue.py --jobs 4 <the same configs>
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PureWindowsPath

ORDERS = ("seeds", "experiments")
LIST = """\
import json, sys
from pathlib import Path
from rlscape.agents.training import load_config, run_dir, variants
path = Path(sys.argv[1])
print(json.dumps([[name, seed, str(run_dir(c, path.stem, seed))]
                  for name, c in variants(load_config(path)) for seed in c['seeds']]))
"""  # no double quotes: it's a command-line argument, quoted again on the way through uv on Windows


class QueueError(Exception):
    pass


@dataclass(frozen=True)
class Experiment:
    name: str  # the config's file name (OQ-62)
    config: Path
    worktree: Path
    branch: str
    commit: str
    server: str
    dirty: bool

    @property
    def python(self) -> Path:
        return self.worktree / ".venv" / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")


@dataclass(frozen=True)
class Run:
    experiment: Experiment
    variant: str  # "" without a sweep
    seed: int
    dir: Path
    order: tuple[int, int]  # (variant's index, seed's index) in its experiment

    @property
    def key(self) -> tuple[str, str, int]:
        return self.experiment.name, self.variant, self.seed

    @property
    def label(self) -> str:
        return "/".join(part for part in (self.experiment.name, self.variant, f"seed{self.seed}") if part)

    @property
    def log(self) -> Path:
        return self.dir.parent / f"{self.dir.name}.log"

    def command(self, force: bool) -> list[str]:
        e = self.experiment
        return [str(e.python), str(e.worktree / "scripts" / "train.py"), "--config", str(e.config),
                *(["--variant", self.variant] if self.variant else []), "--seed", str(self.seed),
                *(["--force"] if force else [])]


def say(message: str) -> None:
    print(f"{datetime.now().astimezone():%Y-%m-%d %H:%M:%S %z}  {message}", flush=True)  # %Z is a long name on Windows


# --- the machine's training runs ---------------------------------------------------------------------------------

_TRAIN_ARGS = argparse.ArgumentParser(add_help=False, exit_on_error=False)
_TRAIN_ARGS.add_argument("--config")
_TRAIN_ARGS.add_argument("--seed", action="append")
_TRAIN_ARGS.add_argument("--variant", action="append")


def parse_training(command_line: str) -> tuple[str, tuple[str, ...] | None, tuple[int, ...]] | None:
    """(experiment, variants or None for every one, seeds) of a command line running scripts/train.py with --seed;
    None for anything else, a train.py --jobs launcher included (it trains nothing itself)."""
    try:
        tokens = [token.strip('"') for token in shlex.split(command_line, posix=False)]
    except ValueError:
        return None
    script = next((i for i, token in enumerate(tokens) if PureWindowsPath(token).name == "train.py"), None)
    if script is None:
        return None
    try:
        args, _ = _TRAIN_ARGS.parse_known_args(tokens[script + 1:])
        seeds = tuple(int(seed) for seed in args.seed or ())
    except (argparse.ArgumentError, ValueError):
        return None
    if not args.config or not seeds:
        return None
    return PureWindowsPath(args.config).stem, tuple(args.variant) if args.variant else None, seeds


def command_lines() -> list[str]:
    """Every python and uv process's command line."""
    if platform.system() == "Windows":
        script = ("Get-CimInstance Win32_Process -Filter \"Name like 'python%' or Name = 'uv.exe'\" | "
                  "ForEach-Object { $_.CommandLine }")
        command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]
    else:
        command = ["ps", "-axo", "command="]
    out = subprocess.run(command, capture_output=True, text=True, errors="replace", check=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def training_runs() -> set[tuple[str, tuple[str, ...] | None, tuple[int, ...]]]:
    """The machine's training runs, one each: a run shows as uv's process, its venv's launcher and the interpreter
    that starts, all with one command line."""
    return {parsed for line in command_lines() if (parsed := parse_training(line)) is not None}


def is_training(run: Run, training: set) -> bool:
    name, variant, seed = run.key
    return any(t[0] == name and seed in t[2] and (t[1] is None or variant in t[1]) for t in training)


def state(run: Run, training: set) -> str:
    if (run.dir / "run.json").exists():
        return "done"
    if is_training(run, training):
        return "training"
    return "partial" if run.dir.exists() else "waiting"


# --- the plan ----------------------------------------------------------------------------------------------------

def _git(worktree: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(worktree), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise QueueError(f"git {' '.join(args)} in {worktree}: {result.stderr.strip()}")
    return result.stdout.strip()


def child_env() -> dict[str, str]:
    """This environment, without the venv this queue runs in: each run uses its own worktree's."""
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env["PYTHONUNBUFFERED"] = "1"
    return env


def experiment(config: Path) -> Experiment:
    config = Path(config).resolve()
    if not config.is_file():
        raise QueueError(f"no config {config}")
    worktree = Path(_git(config.parent, "rev-parse", "--show-toplevel")).resolve()
    return Experiment(config.stem, config, worktree, _git(worktree, "rev-parse", "--abbrev-ref", "HEAD"),
                      _git(worktree, "rev-parse", "--short", "HEAD"),
                      _git(worktree / "server", "rev-parse", "--short", "HEAD") if (worktree / "server").exists()
                      else "", bool(_git(worktree, "status", "--porcelain")))


def list_runs(e: Experiment) -> list[Run]:
    """The experiment's runs, by its worktree's own trainer (which syncs the worktree's venv the first time)."""
    result = subprocess.run(["uv", "run", "--frozen", "python", "-c", LIST, str(e.config)], cwd=e.worktree,
                            capture_output=True, text=True, env=child_env())
    if result.returncode != 0:
        raise QueueError(f"{e.name}: listing its runs failed:\n{result.stderr.strip()[-2000:]}")
    listed = json.loads(result.stdout.strip().splitlines()[-1])
    variants = list(dict.fromkeys(variant for variant, _, _ in listed))
    seeds = list(dict.fromkeys(seed for _, seed, _ in listed))
    return [Run(e, variant, int(seed), Path(path), (variants.index(variant), seeds.index(seed)))
            for variant, seed, path in listed]


def ordered(runs: list[Run], experiments: list[Experiment], order: str) -> list[Run]:
    rank = {e.name: i for i, e in enumerate(experiments)}
    if order == "seeds":
        return sorted(runs, key=lambda r: (r.order[1], rank[r.experiment.name], r.order[0]))
    if order == "experiments":
        return sorted(runs, key=lambda r: (rank[r.experiment.name], r.order[0], r.order[1]))
    raise QueueError(f"--order is one of {ORDERS}")


def plan(configs: list[Path], order: str, allow_dirty: bool) -> tuple[list[Experiment], list[Run]]:
    experiments = [experiment(config) for config in configs]
    names = [e.name for e in experiments]
    if len(set(names)) != len(names):
        raise QueueError(f"an experiment is given twice: {names}")
    servers = {e.server for e in experiments}
    if len(servers) > 1:
        raise QueueError("the worktrees are on different server commits: "
                         + ", ".join(f"{e.name} {e.server or 'none'}" for e in experiments))
    dirty = [e.name for e in experiments if e.dirty]
    if dirty and not allow_dirty:
        raise QueueError(f"uncommitted changes in the worktrees of {dirty}: their runs couldn't be published "
                         "(commit them, or --allow-dirty)")
    runs = []
    for e in experiments:
        say(f"{e.name}: listing its runs in {e.worktree} ({e.branch} @ {e.commit}{', dirty' if e.dirty else ''}, "
            f"server {e.server or 'none'})")
        runs += list_runs(e)
    return experiments, ordered(runs, experiments, order)


# --- the queue ---------------------------------------------------------------------------------------------------

@dataclass
class Started:
    run: Run
    process: subprocess.Popen
    log: object


def start(run: Run, force: bool) -> Started:
    run.dir.parent.mkdir(parents=True, exist_ok=True)
    log = open(run.log, "w", encoding="utf-8")
    process = subprocess.Popen(run.command(force), cwd=run.experiment.worktree, stdout=log,
                               stderr=subprocess.STDOUT, env=child_env())
    return Started(run, process, log)


def busy(training: set, own: dict[tuple, Started]) -> int:
    """Slots in use: the process table's runs, and this queue's that aren't on it yet."""
    return len(training) + sum(not is_training(s.run, training) for s in own.values())


def run_queue(runs: list[Run], jobs: int, poll: float = 60.0, settle: float = 30.0, restart_partial: bool = False,
              machine: Callable[[], set] = training_runs) -> list[Run]:
    """Train the runs, `jobs` on the machine at once; returns the ones that failed. `machine` reads the machine's
    training runs (the process table; a test counts only its own)."""
    waiting, own, failed, free_since = list(runs), {}, [], None
    while True:
        for key, s in list(own.items()):
            if s.process.poll() is None:
                continue
            s.log.close()
            del own[key]
            if s.process.returncode == 0 and (s.run.dir / "run.json").exists():
                say(f"{s.run.label}: done")
            else:
                failed.append(s.run)
                say(f"{s.run.label}: failed ({s.process.returncode}), see {s.run.log}")
        try:
            training = machine()
        except (OSError, subprocess.CalledProcessError) as error:  # a failed look starts nothing; the next may work
            say(f"couldn't read the process table ({error}); trying again in {poll:g} s")
            time.sleep(poll)
            continue
        kept = []
        for run in waiting:
            now = state(run, training)
            if now == "done":
                say(f"{run.label}: already done, skipped")
            elif now == "training" and run.key not in own:
                say(f"{run.label}: already training (not started by this queue), left to finish")
            elif now == "partial" and not restart_partial:
                say(f"{run.label}: stopped part-way and not training, skipped (--restart-partial trains it again)")
            else:
                kept.append(run)
        waiting = kept
        if not waiting and not own:
            return failed
        free = jobs - busy(training, own)
        if waiting and free > 0:
            free_since = time.monotonic() if free_since is None else free_since
            if time.monotonic() - free_since >= settle:
                for run in waiting[:free]:
                    partial = state(run, training) == "partial"
                    own[run.key] = start(run, force=partial)
                    say(f"{run.label}: started{' again from the start' if partial else ''} -> {run.dir} "
                        f"(machine: {busy(training, own)} of {jobs})")
                waiting = waiting[free:]
                free_since = None
                continue  # look at the process table again before waiting
        else:
            free_since = None
        time.sleep(poll)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("configs", nargs="+", type=Path, help="each experiment's config, in its worktree")
    parser.add_argument("--jobs", type=int, required=True, help="training runs on the machine at once, all counted")
    parser.add_argument("--order", choices=ORDERS, default="seeds")
    parser.add_argument("--poll", type=float, default=60.0, help="seconds between looks at the process table")
    parser.add_argument("--settle", type=float, default=30.0, help="seconds a slot stays free before it's taken")
    parser.add_argument("--restart-partial", action="store_true", help="train a run stopped part-way again")
    parser.add_argument("--allow-dirty", action="store_true", help="worktrees with uncommitted changes")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and each run's state; start nothing")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs is at least 1")
    try:
        experiments, runs = plan(args.configs, args.order, args.allow_dirty)
    except QueueError as error:
        sys.exit(f"train_queue: {error}")
    training = training_runs()
    states = [state(run, training) for run in runs]
    say(f"{len(runs)} runs from {len(experiments)} experiments, by {args.order}; the machine trains "
        f"{len(training)} now, of --jobs {args.jobs}")
    for i, (run, now) in enumerate(zip(runs, states), 1):
        print(f"  {i:3d}  {now:<9} {run.label}")
    partial = [run.label for run, now in zip(runs, states) if now == "partial"]
    if partial and not args.restart_partial:
        sys.exit(f"train_queue: runs stopped part-way, not training: {partial}; look at them, then "
                 "--restart-partial to train them again from the start")
    if args.dry_run:
        return
    failed = run_queue(runs, args.jobs, args.poll, args.settle, args.restart_partial)
    say(f"the queue is done: {len(failed)} failed" + (f" ({', '.join(r.label for r in failed)})" if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
