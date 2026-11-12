"""The data the analysis reads: every evaluation episode's trace (rlscape/eval/harness.py's decisions table, published
as decisions.csv.gz) and a training run's behaviour from its decision log (rlscape/eval/behaviour.py, published by
publish_training). Real sim episodes and a real (tiny) training run."""

from __future__ import annotations

import json
from collections import Counter

import numpy as np
import pandas as pd
import pytest

from rlscape.eval.harness import run_tables, save, summarize
from rlscape.eval.publish import TRACE_FILE, publish, publish_training
from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
TWO_HOURS = {"horizon_ticks": 12_000}
TINY = {"seeds": [0], "total_decisions": 48, "n_envs": 2, "vec_env": "dummy", "device": "cpu",
        "env": {"hours": 0.25}, "ppo": {"gamma_hr": 0.9, "n_steps": 8, "batch_size": 8, "n_epochs": 1},
        "checkpoint_every": 16, "decision_log": True}


@pytest.fixture(scope="module")
def tables():
    return run_tables(["random", "greedy_wealth"], [0, 1], TWO_HOURS)


def test_an_episodes_trace_is_every_decision_ending_where_the_episode_ends(tables):
    _, episodes, decisions = tables
    for episode in episodes.itertuples():
        trace = decisions[(decisions.policy == episode.policy) & (decisions.seed == episode.seed)]
        assert list(trace.decision) == list(range(episode.decisions))
        assert trace.t1.is_monotonic_increasing and trace.t1.iloc[-1] == episode.game_ticks
        last = trace.iloc[-1]
        assert (last.total_level, last.net_worth) == (episode.total_level, episode.net_worth)
        top, count = episode.top_options.split("; ")[0].rsplit(" ", 1)
        assert Counter(trace.option).most_common(1)[0][1] == int(count) and (trace.option == top).sum() == int(count)
    ended = decisions.groupby(["policy", "seed"], sort=False).termination.agg(lambda t: Counter(t))  # in run order
    assert all(sum(c.values()) == n for c, n in zip(ended, episodes.decisions))  # each decision says why it ended
    assert all(isinstance(t, str) and t for t in decisions.termination)


def test_a_trace_is_the_same_whatever_the_workers(tables):
    assert run_tables(["random", "greedy_wealth"], [1, 0], TWO_HOURS, workers=2)[2].equals(tables[2])


def test_a_published_summary_carries_the_traces_byte_for_byte_the_same_each_time(tables, tmp_path):
    checkpoints, episodes, decisions = tables
    run = save(tmp_path / "run", {"c": 1}, checkpoints, episodes, summarize(checkpoints), decisions=decisions)
    meta = json.loads((run / "config.json").read_text(encoding="utf-8"))
    (run / "config.json").write_text(json.dumps({**meta, "git_dirty": False}), encoding="utf-8")
    out = publish(run, "traced", root=tmp_path / "summary")
    published = pd.read_csv(out / TRACE_FILE)
    pd.testing.assert_frame_equal(published, decisions, check_dtype=False)
    first = (out / TRACE_FILE).read_bytes()
    publish(run, "traced", root=tmp_path / "summary", force=True)
    assert (out / TRACE_FILE).read_bytes() == first  # no timestamp in the gzip: a republished file doesn't diff
    assert f"`{TRACE_FILE}`" in (out / "README.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    pytest.importorskip("rlscape.agents.ppo")
    from rlscape.agents.training import train
    return train(dict(TINY), "behaviour-test", 0, tmp_path_factory.mktemp("behaviour") / "runs" / "seed0")


def test_a_runs_behaviour_adds_up_to_its_decision_log(trained):
    from rlscape.agents.decision_log import read_decisions
    from rlscape.eval.behaviour import read_log, training_behaviour
    tables = training_behaviour(trained)
    bins, options, first = tables["bins"], tables["options"], tables["first"]
    log = read_decisions(trained / "decisions")
    done = json.loads((trained / "run.json").read_text(encoding="utf-8"))
    assert list(bins.bin) == [0, 1, 2] and list(bins.from_step) == [0, 16, 32]  # checkpoint_every's bins
    assert bins.decisions.sum() == done["decisions"] == len(log) and bins.ended.sum() == done["episodes"]
    assert bins.ticks.sum() == log.duration.sum()
    per_bin = options.groupby("bin")[["decisions", "ticks"]].sum()
    assert (per_bin.decisions.to_numpy() == bins.decisions.to_numpy()).all()
    assert (per_bin.ticks.to_numpy() == bins.ticks.to_numpy()).all()
    assert first.set_index("action").step.to_dict() == log.groupby("action").step.min().to_dict()
    catalog = {o["index"]: o["id"] for o in json.loads((trained / "options.json").read_text(encoding="utf-8"))}
    assert all(catalog[a] == o for a, o in zip(first.action, first.option))
    by_hand = np.array([-(p[p > 0] * np.log(p[p > 0])).sum() for p in log.probs])  # each decision's entropy
    assert np.allclose(read_log(trained).entropy.to_numpy(), by_hand, atol=1e-6)
    assert (bins.entropy <= np.log(bins.open) + 1e-6).all()


def test_publishing_training_writes_the_behaviour_tables_with_each_runs_variant_and_seed(trained, tmp_path):
    out = publish_training(trained.parent, "behaviour-test", root=tmp_path, allow_dirty=True)
    bins = pd.read_csv(out / "behaviour_bins.csv")
    options = pd.read_csv(out / "behaviour_options.csv.gz", keep_default_na=False)
    first = pd.read_csv(out / "first_choices.csv.gz", keep_default_na=False)
    assert len(bins) == 3 and (bins.seed == 0).all() and list(options.columns[:3]) == ["variant", "seed", "bin"]
    assert options.decisions.sum() == bins.decisions.sum() and set(first.option) == set(options.option)
