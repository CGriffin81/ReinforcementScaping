"""Tests for training (rlscape/agents/training.py, scripts/train.py) and the decision logger
(rlscape/agents/decision_log.py), on a short real run on the sim."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
pytest.importorskip("rlscape.agents.ppo")

from rlscape.agents.decision_log import read_decisions, unpack_mask  # noqa: E402
from rlscape.agents.ppo import SMDPMaskablePPO  # noqa: E402
from rlscape.agents.training import check_config, train  # noqa: E402

N_ACTIONS = 2_294  # sim v1.2 (env contract v1.44): woodcutting's fletch slot
CONFIG = {"seeds": [0], "total_decisions": 32, "n_envs": 2, "vec_env": "dummy", "device": "cpu",
          "env": {"hours": 0.5, "reward_weights": [0.5, 0.5]},
          "ppo": {"gamma_hr": 0.9, "n_steps": 8, "batch_size": 8, "n_epochs": 1},
          "checkpoint_every": 16, "decision_log": True}


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    root = tmp_path_factory.mktemp("train")
    return train(dict(CONFIG), "e0-test", 0, root / "a"), train(dict(CONFIG), "e0-test", 0, root / "b")


def test_a_run_writes_its_provenance_checkpoints_curves_and_model(runs):
    run = runs[0]
    meta = json.loads((run / "config.json").read_text(encoding="utf-8"))
    assert meta["seed"] == 0 and len(meta["git_sha"]) == 40 and len(meta["config_hash"]) == 12
    assert meta["env_kwargs"] == {"horizon_ticks": 3_000, "reward_weights": [0.5, 0.5]}
    options = json.loads((run / "options.json").read_text(encoding="utf-8"))
    assert len(options) == N_ACTIONS and options[0]["index"] == 0 and {"id", "family"} <= options[0].keys()
    assert sorted(p.name for p in (run / "checkpoints").iterdir()) == ["ppo_16_steps.zip", "ppo_32_steps.zip"]
    assert any((run / "tb").rglob("events.out.tfevents*"))
    assert json.loads((run / "run.json").read_text(encoding="utf-8"))["decisions"] == 32
    model = SMDPMaskablePPO.load(run / "model.zip", device="cpu")
    assert model.decision_logger is None and model.gamma_hr == 0.9


def test_every_decision_is_logged_with_what_the_policy_saw_and_chose(runs):
    log = read_decisions(runs[0] / "decisions")
    assert len(log) == 32 and list(log.step[:4]) == [0, 0, 2, 2] and set(log.env) == {0, 1}
    for row in log.itertuples():
        mask = unpack_mask(row.mask, N_ACTIONS)
        available = np.flatnonzero(mask)
        assert mask[row.action] and len(row.probs) == len(available) == mask.sum()
        assert sum(row.probs) == pytest.approx(1.0, abs=1e-5)
        assert row.probs[int(np.searchsorted(available, row.action))] == pytest.approx(np.exp(row.log_prob), rel=1e-4)
        assert len(row.obs) == 3_488 and np.isfinite(row.value) and row.duration >= 0
        assert json.loads(row.option)["action"] == row.action
    for _, env in log.groupby("env"):  # each env's decisions are numbered within its episodes
        starts = np.r_[0, np.flatnonzero(env.done.to_numpy()[:-1]) + 1]
        assert (env.decision.to_numpy()[starts] == 0).all() and env.episode.is_monotonic_increasing


def test_the_learning_curve_matches_the_decision_log(runs):
    log, episodes = read_decisions(runs[0] / "decisions"), pd.read_parquet(runs[0] / "episodes.parquet")
    finished = log[log.done]
    assert len(episodes) == len(finished) > 0
    assert list(episodes.total_level) == list(finished.total_level)
    first = episodes.iloc[0]
    rows = log[(log.env == first.env) & (log.episode == 0)]
    assert first.decisions == len(rows) and first.r_skill == pytest.approx(rows.r_skill.sum(), rel=1e-5)
    assert first.game_ticks == 3_000  # the half-hour horizon
    # without a training wrapper, nothing is added to the env's reward (rlscape.agents.training's REWARD_PARTS)
    assert (log.r_intrinsic == 0).all() and (log.r_shaping == 0).all()
    assert (episodes.r_intrinsic == 0).all() and (episodes.r_shaping == 0).all()
    assert np.allclose(log.reward, 0.5 * log.r_skill + 0.5 * log.r_wealth, atol=1e-6)


def test_the_same_config_and_seed_give_the_same_run(runs):
    a, b = (read_decisions(r / "decisions") for r in runs)
    pd.testing.assert_series_equal(a.action, b.action)
    pd.testing.assert_series_equal(a.value, b.value)
    pd.testing.assert_frame_equal(pd.read_parquet(runs[0] / "episodes.parquet"),
                                  pd.read_parquet(runs[1] / "episodes.parquet"))


def test_a_config_with_an_unknown_key_or_a_number_as_text_is_refused():
    with pytest.raises(ValueError, match="unknown keys"):
        check_config({**CONFIG, "gamma": 0.99})
    with pytest.raises(ValueError, match="env keys"):
        check_config({**CONFIG, "env": {"horizon": 2}})
    with pytest.raises(ValueError, match="3.0e-4"):
        check_config({**CONFIG, "ppo": {"learning_rate": "3e-4"}})
    with pytest.raises(FileExistsError):
        train(dict(CONFIG), "e0-test", 0, out=__import__("pathlib").Path(__file__).parent)
