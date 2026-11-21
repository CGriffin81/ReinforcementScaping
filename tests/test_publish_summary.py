"""Tests for publishing a run's summary (rlscape/eval/publish.py) and for scripts/evaluate.py's --config file."""

from __future__ import annotations

import json
import subprocess
import sys

import pandas as pd
import pytest

from rlscape.eval.harness import REPO, run, save, summarize
from rlscape.eval.publish import PublishError, publish
from rlscape.eval.rollout import MAX_DECISIONS
from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")


@pytest.fixture(scope="module")
def tables():
    return run(["random", "greedy_wealth"], [0, 1], {"horizon_ticks": 12_000})  # 2 game-hours


def a_run(tmp_path, tables, dirty: bool):
    checkpoints, episodes = tables
    out = save(tmp_path / "run", {"policies": ["random", "greedy_wealth"]}, checkpoints, episodes,
               summarize(checkpoints), extra={"script": "scripts/evaluate.py", "argv": ["--config", "c.yaml"]})
    meta = json.loads((out / "config.json").read_text(encoding="utf-8"))
    meta["git_dirty"] = dirty  # as a clean or a dirty tree would have recorded it
    (out / "config.json").write_text(json.dumps(meta), encoding="utf-8")
    return out, meta


def test_a_published_summary_holds_the_runs_tables_and_provenance(tmp_path, tables):
    run_dir, meta = a_run(tmp_path, tables, dirty=False)
    out = publish(run_dir, "e0-test", root=tmp_path / "summary")
    assert sorted(p.name for p in out.iterdir()) == ["README.md", "checkpoints.csv", "config.json", "episodes.csv",
                                                      "summary.csv"]
    assert json.loads((out / "config.json").read_text(encoding="utf-8")) == meta
    for table in ("summary", "checkpoints", "episodes"):
        pd.testing.assert_frame_equal(pd.read_csv(out / f"{table}.csv"), pd.read_parquet(run_dir / f"{table}.parquet"),
                                      check_dtype=False)
    readme = (out / "README.md").read_text(encoding="utf-8")
    summary = pd.read_parquet(run_dir / "summary.parquet")
    level = summary[(summary.hour == 2) & (summary.policy == "greedy_wealth") & (summary.metric == "total_level")]
    assert "## At hour 2: mean [95% bootstrap CI] over 2 seeds" in readme
    assert f"| greedy_wealth | {level['mean'].iloc[0]:,.0f} [" in readme and "| random | " in readme
    assert f"`{meta['git_sha']}` |" in readme and "`uv run python scripts/evaluate.py --config c.yaml`" in readme
    assert "except as marked" not in readme and "Short of hour" not in readme


def test_the_readme_marks_the_policies_whose_episodes_stop_short_of_the_last_hour(tmp_path, tables):
    """As E6b's evaluation did (OQ-91): one of random's two episodes, and both of greedy_wealth's, stop at the cap
    before hour 2, so they have no hour-2 checkpoint. The table is still over the run's 2 seeds, except as marked."""
    checkpoints, episodes = tables
    short = (checkpoints.hour == 2) & ((checkpoints.policy == "greedy_wealth") | (checkpoints.seed == 1))
    checkpoints = checkpoints[~short]
    episodes = episodes.copy()
    capped = (episodes.policy == "greedy_wealth") | (episodes.seed == 1)
    episodes.loc[capped, "decisions"] = MAX_DECISIONS
    out = save(tmp_path / "run", {"policies": ["random", "greedy_wealth"]}, checkpoints, episodes,
               summarize(checkpoints), extra={"script": "scripts/evaluate.py", "argv": ["--config", "c.yaml"]})
    meta = json.loads((out / "config.json").read_text(encoding="utf-8"))
    meta["git_dirty"] = False
    (out / "config.json").write_text(json.dumps(meta), encoding="utf-8")
    readme = (publish(out, "e0-test", root=tmp_path / "summary") / "README.md").read_text(encoding="utf-8")
    assert "| Seeds | 2 |" in readme
    assert "## At hour 2: mean [95% bootstrap CI] over 2 seeds, except as marked" in readme
    assert "| random (1 seed) | " in readme and "| greedy_wealth" not in readme
    assert (f"- `random`: 1 of its 2 episodes stops before hour 2, at the evaluation's cap of {MAX_DECISIONS:,} "
            "decisions; its row is over the 1 seed that reaches it.") in readme
    assert (f"- `greedy_wealth`: all 2 of its episodes stop before hour 2, at the evaluation's cap of "
            f"{MAX_DECISIONS:,} decisions, so it has no row.") in readme


def test_a_dirty_run_or_a_published_name_is_refused(tmp_path, tables):
    run_dir, _ = a_run(tmp_path, tables, dirty=True)
    with pytest.raises(PublishError, match="uncommitted"):
        publish(run_dir, "e0-test", root=tmp_path / "summary")
    out = publish(run_dir, "e0-test", root=tmp_path / "summary", allow_dirty=True)
    assert "not reproducible from this SHA" in (out / "README.md").read_text(encoding="utf-8")
    with pytest.raises(PublishError, match="already published"):
        publish(run_dir, "e0-test", root=tmp_path / "summary", allow_dirty=True)
    publish(run_dir, "e0-test", root=tmp_path / "summary", allow_dirty=True, force=True)


def evaluate(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(REPO / "scripts" / "evaluate.py"), *args], cwd=REPO,
                          capture_output=True, text=True)


def test_evaluate_reads_a_config_file_that_the_command_line_overrides(tmp_path):
    config = tmp_path / "e0.yaml"
    config.write_text(f"policies: [random]\nseeds: 3\nfirst-seed: 5\nhours: 2\nout: {(tmp_path / 'out').as_posix()}\n",
                      encoding="utf-8")
    result = evaluate("--config", str(config), "--seeds", "1")
    assert result.returncode == 0, result.stderr
    meta = json.loads((tmp_path / "out" / "config.json").read_text(encoding="utf-8"))
    assert meta["config"]["policies"] == ["random"] and meta["config"]["seeds"] == [5]  # --seeds 1 overrides 3
    assert meta["config"]["env"]["horizon_ticks"] == 12_000 and meta["argv"] == ["--config", str(config), "--seeds", "1"]


def test_evaluate_refuses_a_config_key_it_doesnt_know(tmp_path):
    config = tmp_path / "bad.yaml"
    config.write_text("policies: [random]\nhorizon: 2\n", encoding="utf-8")
    result = evaluate("--config", str(config))
    assert result.returncode == 2 and "unknown keys ['horizon']" in result.stderr
