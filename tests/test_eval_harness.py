"""Tests for the eval harness (rlscape/eval/harness.py)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from rlscape.eval.harness import METRICS, bootstrap_ci, paired_difference, run, save, summarize
from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
TWO_HOURS = {"horizon_ticks": 12_000}


@pytest.fixture(scope="module")
def tables():
    return run(["random", "greedy_wealth"], [0, 1, 2], TWO_HOURS)


def test_bootstrap_ci():
    rng = np.random.default_rng(0)
    assert bootstrap_ci([5.0, 5.0, 5.0], rng) == (5.0, 5.0)
    assert all(np.isnan(bootstrap_ci([1.0], rng)))
    values = np.random.default_rng(1).normal(10, 2, 30)
    low, high = bootstrap_ci(values, np.random.default_rng(0))
    assert low < values.mean() < high and (low, high) == bootstrap_ci(values, np.random.default_rng(0))


def test_run_gives_a_row_per_checkpoint_and_per_episode(tables):
    checkpoints, episodes = tables
    assert list(episodes.policy) == ["random"] * 3 + ["greedy_wealth"] * 3 and list(episodes.seed) == [0, 1, 2] * 2
    assert len(checkpoints) == 6 * 2 and set(checkpoints.hour) == {0, 2}  # the start and the 2-hour checkpoint
    start = checkpoints[checkpoints.hour == 0]
    assert start.total_level.nunique() == start.net_worth.nunique() == 1  # every episode starts fresh
    final = checkpoints[checkpoints.hour == 2].reset_index(drop=True)
    assert (final[list(METRICS)] == episodes[list(METRICS)]).all().all()
    assert (episodes.game_ticks == 12_000).all() and (episodes.decisions > 0).all()


def test_results_depend_only_on_policy_and_seed(tables):
    serial, _ = run(["random"], [1, 2], TWO_HOURS)
    parallel, _ = run(["random"], [1, 2], TWO_HOURS, workers=2)
    pd.testing.assert_frame_equal(serial, parallel)
    same = tables[0][(tables[0].policy == "random") & tables[0].seed.isin([1, 2])].reset_index(drop=True)
    pd.testing.assert_frame_equal(serial, same)


def test_summary_and_paired_difference(tables):
    checkpoints, _ = tables
    summary = summarize(checkpoints)
    assert len(summary) == 2 * 2 * len(METRICS) and (summary.seeds == 3).all()
    row = summary[(summary.policy == "greedy_wealth") & (summary.hour == 2) & (summary.metric == "net_worth")].iloc[0]
    values = checkpoints[(checkpoints.policy == "greedy_wealth") & (checkpoints.hour == 2)].net_worth
    assert row["mean"] == pytest.approx(values.mean()) and row.ci_low <= row["mean"] <= row.ci_high
    diff = paired_difference(checkpoints, "greedy_wealth", "random", "net_worth")
    at_two = diff[diff.hour == 2].iloc[0]
    by_seed = checkpoints[checkpoints.hour == 2].pivot(index="seed", columns="policy", values="net_worth")
    assert at_two["mean"] == pytest.approx((by_seed.greedy_wealth - by_seed.random).mean()) and at_two["mean"] > 0
    assert (paired_difference(checkpoints, "random", "random", "total_xp")["mean"] == 0).all()


def test_save_writes_parquet_and_provenance(tables, tmp_path):
    checkpoints, episodes = tables
    out = save(tmp_path / "run", {"policies": ["random", "greedy_wealth"]}, checkpoints, episodes,
               summarize(checkpoints))
    pd.testing.assert_frame_equal(pd.read_parquet(out / "checkpoints.parquet"), checkpoints)
    meta = json.loads((out / "config.json").read_text(encoding="utf-8"))
    assert len(meta["config_hash"]) == 12 and len(meta["git_sha"]) == 40 and len(meta["server_sha"]) == 40


def test_unknown_policies_are_refused():
    with pytest.raises(ValueError):
        run(["greedy_gp"], [0])
