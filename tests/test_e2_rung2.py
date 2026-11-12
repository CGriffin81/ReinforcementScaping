"""E2's rung 2 analysis (scripts/e2_rung2.py): the ranking, the paired differences, and the committed summary."""

from __future__ import annotations

import importlib.util

import numpy as np
import pandas as pd
import pytest

from rlscape.eval.harness import METRICS, REPO


@pytest.fixture(scope="module")
def rung2():
    spec = importlib.util.spec_from_file_location("e2_rung2", REPO / "scripts" / "e2_rung2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def table(rewards: dict[str, list[float]]) -> pd.DataFrame:
    rows = [{"policy": p, "seed": s, "reward": r, **{m: r * 2 for m in METRICS}}
            for p, values in rewards.items() for s, r in enumerate(values)]
    return pd.DataFrame(rows)


def test_ranks_variants_over_their_runs_and_pairs_by_seed(rung2):
    t = table({"random": [1, 2, 3, 4], "scripted_guide": [5, 5, 5, 5],
               "a/seed0": [3, 4, 5, 6], "a/seed1": [2, 3, 4, 5],    # variant a: +1.5 over random, mean 4.0
               "b/seed0": [9, 1, 9, 1], "b/seed1": [1, 1, 1, 1]})  # variant b: mean 3.0
    ranked = rung2.variants(t)
    assert ranked.variant.tolist() == ["a", "b"]
    assert ranked.reward.tolist() == [4.0, 3.0] and ranked.runs.tolist() == [2, 2]
    diffs = rung2.paired(t, np.random.default_rng(0))
    row = diffs[(diffs.policy == "a/seed0") & (diffs.against == "random") & (diffs.measure == "reward")].iloc[0]
    assert row.mean_difference == 2.0 and row.ci_low == row.ci_high == 2.0  # the same +2 on every seed
    assert set(diffs.against) == {"random", "scripted_guide"} and set(diffs.measure) == {"reward", *METRICS}


def test_outcomes_take_the_last_checkpoint(rung2):
    episodes = pd.DataFrame({"policy": ["p", "p"], "seed": [0, 1], "reward": [1.0, 2.0]})
    checkpoints = pd.DataFrame([{"policy": "p", "seed": s, "hour": h, **{m: 10 * h + s for m in METRICS}}
                                for s in (0, 1) for h in (0, 2, 20)])
    out = rung2.outcomes(episodes, checkpoints)
    assert out.total_level.tolist() == [200, 201] and out.reward.tolist() == [1.0, 2.0]


def test_the_committed_summary_is_what_the_script_writes(rung2, tmp_path, monkeypatch):
    """Rerunning the analysis on the committed evaluation reproduces the committed rung2/ files."""
    summary = REPO / "results" / "summary" / "e2-ppo-sanity-ladder"
    if not (summary / "rung2" / "variants.csv").exists():
        pytest.skip("E2's summary isn't published")
    for name in ("episodes.csv", "checkpoints.csv", "config.json"):
        (tmp_path / name).write_bytes((summary / name).read_bytes())
    monkeypatch.setattr(rung2, "SUMMARY", tmp_path)
    rung2.main()
    for name in ("variants.csv", "paired.csv", "README.md"):
        assert (tmp_path / "rung2" / name).read_text(encoding="utf-8") == \
            (summary / "rung2" / name).read_text(encoding="utf-8"), name
