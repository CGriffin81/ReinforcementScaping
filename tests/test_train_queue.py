"""scripts/train_queue.py: one queue for several experiments' runs, each trained by its own worktree's trainer, with
every training run on the machine counted in its slots. Real (tiny) training runs and real processes."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
import uuid
from pathlib import Path

import pytest
import yaml

from rlscape.eval.harness import REPO
from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
pytest.importorskip("rlscape.agents.ppo")

SCRIPT = REPO / "scripts" / "train_queue.py"
TINY = {"seeds": [0, 1], "total_decisions": 16, "n_envs": 1, "vec_env": "dummy", "device": "cpu",
        "env": {"hours": 0.25}, "ppo": {"gamma_hr": 0.9, "n_steps": 8, "batch_size": 8, "n_epochs": 1},
        "checkpoint_every": 0, "decision_log": False}
E3_RUN = ("e3-reward-weight-sweep", ("normalised_weights0.75-0.25",), (3,))
# Command lines as the process table showed them on 2026-11-11, E3 training (paths shortened where they don't matter)
LINES = {
    r'"C:\Python314\Scripts\uv.exe" run --frozen python scripts/train.py '
    r'--config configs/e3-reward-weight-sweep.yaml --jobs 4': None,  # train.py --jobs: a launcher, training nothing
    r'D:\ReinforcementScaping-runs\.venv\Scripts\python.exe D:\ReinforcementScaping-runs\scripts\train.py '
    r'--config configs\e3-reward-weight-sweep.yaml --variant normalised_weights0.75-0.25 --seed 3': E3_RUN,
    r'"C:\Users\Caleb\AppData\Roaming\uv\python\cpython-3.12.14-windows-x86_64-none\python.exe" '
    r'D:\ReinforcementScaping-runs\scripts\train.py --config configs\e3-reward-weight-sweep.yaml '
    r'--variant normalised_weights0.75-0.25 --seed 3': E3_RUN,  # the interpreter the venv's launcher starts
    r'"C:\uv\python\cpython-3.12.14\python.exe" "-B" "-c" "from multiprocessing.spawn import spawn_main; '
    r'spawn_main(parent_pid=21440, pipe_handle=1736)" "--multiprocessing-fork"': None,  # one of a run's envs
    r'"D:\ReinforcementScaping\.venv\Scripts\python.exe" scripts/train_queue.py --jobs 4 D:/x/configs/e4.yaml': None,
    'uv run python scripts/train.py --config "D:/My Runs/configs/e4-rnd-exploration.yaml" --seed 0 --seed 2':
        ("e4-rnd-exploration", None, (0, 2)),  # every variant of seeds 0 and 2, in turn
}


@pytest.fixture(scope="module")
def tq():
    spec = importlib.util.spec_from_file_location("train_queue", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["train_queue"] = module  # dataclasses look their module up
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def config(tmp_path):
    """A tiny experiment's config in this worktree (the queue finds an experiment's worktree from its config), its
    runs under tmp_path. runs/ is git-ignored, so the config doesn't change the tree."""
    folder = REPO / "runs" / f"queue-test-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True)
    path = folder / "queue-test.yaml"
    path.write_text(yaml.safe_dump({**TINY, "out": str(tmp_path / "runs")}), encoding="utf-8")
    yield path
    shutil.rmtree(folder)


def test_a_training_run_is_known_by_its_command_line_whichever_process_shows_it(tq):
    for line, expected in LINES.items():
        assert tq.parse_training(line) == expected, line
    runs = {tq.parse_training(line) for line in LINES} - {None}
    assert len(runs) == 2  # E3's run shows three times, as one


def test_the_order_takes_each_seed_of_every_experiment_or_each_experiment_in_turn(tq):
    experiments = [tq.Experiment(name, Path(f"{name}.yaml"), Path("."), "", "", "", False) for name in ("a", "b")]
    runs = [tq.Run(e, variant, seed, Path(e.name) / variant / f"seed{seed}", (v, seed))
            for e, variants in zip(experiments, (["x", "y"], [""])) for v, variant in enumerate(variants)
            for seed in (0, 1)]
    by_seeds = [r.label for r in tq.ordered(runs, experiments, "seeds")]
    assert by_seeds == ["a/x/seed0", "a/y/seed0", "b/seed0", "a/x/seed1", "a/y/seed1", "b/seed1"]
    by_experiments = [r.label for r in tq.ordered(runs, experiments, "experiments")]
    assert by_experiments == ["a/x/seed0", "a/x/seed1", "a/y/seed0", "a/y/seed1", "b/seed0", "b/seed1"]


def cli(*args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=REPO, env=env)


def test_the_queue_waits_for_a_run_it_did_not_start_trains_its_own_one_at_a_time_and_resumes(tq, config, tmp_path):
    # Another experiment's run, on the machine before the queue: a process running a train.py with --seed. The queue
    # counts only these two experiments' runs here, since whatever else trains on the machine (E3) would hold the slot.
    def ours():
        return {run for run in tq.training_runs() if run[0] in ("queue-test", "e9-other")}

    ended = tmp_path / "ended"
    other = tmp_path / "e9" / "scripts" / "train.py"
    other.parent.mkdir(parents=True)
    other.write_text(textwrap.dedent(f"""\
        import time
        time.sleep(6)
        open({str(ended)!r}, "w").write(repr(time.time()))
        """), encoding="utf-8")
    process = subprocess.Popen([sys.executable, str(other), "--config", "configs/e9-other.yaml", "--seed", "0"])
    try:
        deadline = time.monotonic() + 30
        while not any(run[0] == "e9-other" for run in tq.training_runs()):
            assert time.monotonic() < deadline, "the other run never showed on the process table"
            time.sleep(0.5)
        experiments, runs = tq.plan([config], "seeds", allow_dirty=True)
        assert experiments[0].worktree == REPO.resolve() and [r.label for r in runs] == ["queue-test/seed0",
                                                                                         "queue-test/seed1"]
        assert [tq.state(r, tq.training_runs()) for r in runs] == ["waiting", "waiting"]
        assert tq.run_queue(runs, jobs=1, poll=0.5, settle=1.0, machine=ours) == []
    finally:
        process.kill()
    first, second = (r.dir for r in runs)
    assert (first / "run.json").exists() and (second / "run.json").exists() and runs[0].log.exists()
    began = {d: (d / "config.json").stat().st_mtime for d in (first, second)}
    assert began[first] >= float(ended.read_text())  # after the other run had left its slot
    assert began[second] >= (first / "run.json").stat().st_mtime  # one at a time
    meta = json.loads((first / "config.json").read_text(encoding="utf-8"))
    assert meta["name"] == "queue-test" and meta["seed"] == 0 and meta["git_sha"]  # the worktree's own provenance

    assert tq.run_queue(runs, jobs=1, poll=0.5, settle=0.0, machine=ours) == []  # again: both done, nothing started
    assert (first / "config.json").stat().st_mtime == began[first]

    (second / "run.json").unlink()  # seed 1 stopped part-way
    refused = cli("--jobs", "1", "--allow-dirty", "--dry-run", str(config))
    assert refused.returncode == 1 and "queue-test/seed1" in refused.stderr and "--restart-partial" in refused.stderr
    assert tq.run_queue(runs, jobs=1, poll=0.5, settle=0.0, machine=ours) == []
    assert not (second / "run.json").exists()  # skipped: it's partial
    assert tq.run_queue(runs, jobs=1, poll=0.5, settle=0.0, restart_partial=True, machine=ours) == []
    assert (second / "run.json").exists() and (first / "config.json").stat().st_mtime == began[first]
    shown = cli("--jobs", "1", "--allow-dirty", "--dry-run", str(config))
    assert shown.returncode == 0, shown.stderr
    assert [line.split()[1:] for line in shown.stdout.splitlines() if line.startswith("  ")] == \
        [["done", "queue-test/seed0"], ["done", "queue-test/seed1"]]


def test_the_queue_refuses_a_dirty_worktree_without_allow_dirty(tq, config):
    if not tq.experiment(config).dirty:
        pytest.skip("this worktree has no uncommitted changes")
    with pytest.raises(tq.QueueError, match="uncommitted changes"):
        tq.plan([config], "seeds", allow_dirty=False)
