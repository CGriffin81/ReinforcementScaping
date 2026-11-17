"""Tests for the tooling E2 to E6 share: sweeps (rlscape.agents.training.variants), trained policies in the eval
harness (rlscape/eval/trained.py) and publishing training runs (rlscape.eval.publish.publish_training)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
pytest.importorskip("rlscape.agents.ppo")

from rlscape.agents.training import check_config, run_dir, train, variants  # noqa: E402
from rlscape.eval.harness import run  # noqa: E402
from rlscape.eval.publish import PublishError, publish_training  # noqa: E402

BASE = {"seeds": [0], "total_decisions": 16, "n_envs": 2, "vec_env": "dummy", "device": "cpu",
        "env": {"hours": 0.5}, "ppo": {"gamma_hr": 0.9, "n_steps": 8, "batch_size": 8, "n_epochs": 1},
        "checkpoint_every": 0, "decision_log": False}
SWEEP = {**BASE, "sweep": {"ppo.learning_rate": [1.0e-4, 3.0e-4], "ppo.ent_coef": [0.0, 0.01]}}


def test_a_sweep_is_the_grid_of_its_values_each_a_named_variant():
    grid = variants(SWEEP)
    assert [name for name, _ in grid] == ["learning_rate0.0001_ent_coef0", "learning_rate0.0001_ent_coef0.01",
                                          "learning_rate0.0003_ent_coef0", "learning_rate0.0003_ent_coef0.01"]
    name, config = grid[3]
    assert config["ppo"] == {**BASE["ppo"], "learning_rate": 3.0e-4, "ent_coef": 0.01} and "sweep" not in config
    assert run_dir(config, "e9", 2).parts[-3:] == ("e9", name, "seed2")
    weights = variants({**BASE, "sweep": {"env.reward_weights": [[1.0, 0.0], [0.5, 0.5]]}})
    assert [n for n, _ in weights] == ["reward_weights1-0", "reward_weights0.5-0.5"]
    assert weights[1][1]["env"] == {"hours": 0.5, "reward_weights": [0.5, 0.5]}
    assert variants(BASE) == [("", BASE)]
    for bad in ({"seeds": [1, 2]}, {"ppo.learning_rate": 3e-4}, {"env.horizon": [1]}):
        with pytest.raises(ValueError, match="sweep"):
            check_config({**BASE, "sweep": bad})


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    """Two variants of a 16-decision run, as an experiment's runs."""
    root = tmp_path_factory.mktemp("runs") / "e9"
    for name, config in variants({**BASE, "sweep": {"ppo.ent_coef": [0.0, 0.01]}}):
        train(config, "e9", 0, root / name / "seed0")
    return root


def test_a_trained_policy_plays_in_the_harness_the_same_whatever_its_worker(trained):
    model = trained / "ent_coef0" / "seed0" / "model.zip"
    policies, env = ["random", f"tiny=ppo:{model}"], {"horizon_ticks": 3_000}
    serial, episodes = run(policies, [0, 1, 2], env)
    parallel, _ = run(policies, [2, 0, 1], env, workers=2)
    assert list(episodes.policy.unique()) == ["random", "tiny"] and (episodes.game_ticks == 3_000).all()
    pd.testing.assert_frame_equal(serial, parallel)  # sampled, but seeded by the episode
    with pytest.raises(FileNotFoundError):
        run([f"ppo:{trained / 'missing.zip'}"], [0], env)
    with pytest.raises(ValueError, match="share a label"):
        run([f"a=ppo:{model}", f"a=ppo:{model}"], [0], env)


def test_publishing_training_writes_each_runs_provenance_and_learning_curve(trained, tmp_path):
    out = publish_training(trained, "e9", root=tmp_path, allow_dirty=True)
    runs, curves = pd.read_csv(out / "runs.csv"), pd.read_csv(out / "learning_curves.csv.gz")
    assert list(runs.variant) == ["ent_coef0", "ent_coef0.01"] and (runs.decisions == 16).all()
    assert len(curves) == sum(len(pd.read_parquet(trained / v / "seed0" / "episodes.parquet")) for v in runs.variant)
    assert sorted(p.name for p in (out / "configs").iterdir()) == ["ent_coef0.01_seed0.json", "ent_coef0_seed0.json"]
    assert "| ent_coef0.01 | 1 | 16 |" in (out / "README.md").read_text(encoding="utf-8")
    with pytest.raises(PublishError, match="already published"):
        publish_training(trained, "e9", root=tmp_path, allow_dirty=True)
    meta_path = trained / "ent_coef0" / "seed0" / "config.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta_path.write_text(json.dumps({**meta, "git_dirty": True}), encoding="utf-8")
    with pytest.raises(PublishError, match="uncommitted"):
        publish_training(trained, "e9", root=tmp_path / "other")
