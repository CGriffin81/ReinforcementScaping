"""RND's exploration bonus (rlscape/agents/rnd.py) and the trainer with it (E4): the bonus is added to the env's reward
and logged apart, familiar states stop paying, and a run is repeatable. Real sim states throughout."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
pytest.importorskip("rlscape.agents.ppo")

from stable_baselines3.common.vec_env import DummyVecEnv  # noqa: E402

from rlscape.agents.decision_log import read_decisions  # noqa: E402
from rlscape.agents.rnd import RNDReward, check_rnd  # noqa: E402
from rlscape.agents.training import check_config, train  # noqa: E402
from rlscape.envs.sim_env import SimEnv  # noqa: E402

FEATURES = ["skills", "total_level", "wealth", "inventory", "bank", "equipment", "region", "access"]
CONFIG = {"seeds": [0], "total_decisions": 48, "n_envs": 2, "vec_env": "dummy", "device": "cpu",
          "env": {"hours": 0.5, "reward_weights": [0.5, 0.5]},
          "ppo": {"gamma_hr": 0.9, "n_steps": 8, "batch_size": 8, "n_epochs": 1},
          "rnd": {"coef": 0.5, "features": FEATURES, "batch_size": 8},
          "checkpoint_every": 48, "decision_log": True}


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    root = tmp_path_factory.mktemp("rnd")
    return train(dict(CONFIG), "e4-test", 0, root / "a"), train(dict(CONFIG), "e4-test", 0, root / "b")


def test_the_bonus_is_added_to_the_reward_and_logged_apart(runs):
    log = read_decisions(runs[0] / "decisions")
    extrinsic = 0.5 * log.r_skill + 0.5 * log.r_wealth
    assert np.allclose(log.reward, extrinsic + log.r_intrinsic, atol=1e-5)
    first = log.step < 16  # the first rollout (8 steps of 2 envs) only fills RND's input statistics
    assert (log.r_intrinsic[first] == 0).all() and (log.r_intrinsic[~first] != 0).all()
    episodes = pd.read_parquet(runs[0] / "episodes.parquet")  # the learning curve keeps the env's reward
    first_episode = log[(log.env == episodes.iloc[0].env) & (log.episode == 0)]
    assert episodes.iloc[0].reward == pytest.approx(extrinsic[first_episode.index].sum(), rel=1e-4)
    assert episodes.iloc[0].r_intrinsic == pytest.approx(first_episode.r_intrinsic.sum(), rel=1e-4)


def test_a_run_with_rnd_is_repeatable(runs):
    a, b = (read_decisions(r / "decisions") for r in runs)
    pd.testing.assert_series_equal(a.action, b.action)
    pd.testing.assert_series_equal(a.r_intrinsic, b.r_intrinsic)


def states(n_steps: int, seed: int = 0) -> tuple[DummyVecEnv, list[np.ndarray]]:
    """Real observations of two envs taking random allowed options."""
    vec = DummyVecEnv([lambda: SimEnv(horizon_ticks=3_000) for _ in range(2)])
    vec.seed(seed)
    obs, rng, seen = vec.reset(), np.random.default_rng(seed), []
    for _ in range(n_steps):
        seen.append(obs)
        masks = np.stack(vec.env_method("action_masks"))
        obs, *_ = vec.step(np.array([rng.choice(np.flatnonzero(m)) for m in masks]))
    return vec, seen


def test_familiar_states_stop_paying_and_new_ones_still_do():
    vec, seen = states(24)
    parts = vec.get_attr("encoder", indices=[0])[0].parts
    rnd = RNDReward(vec, parts, FEATURES, coef=1.0, seed=0, rollout=8, batch_size=8)
    index = rnd.index
    familiar, later = np.concatenate(seen[:8])[:, index], np.concatenate(seen[16:])[:, index]
    rnd.pending = [familiar]
    rnd.train_predictor()
    before = rnd.errors(familiar).mean()
    for _ in range(30):
        rnd.pending = [familiar]
        rnd.train_predictor()
    after = rnd.errors(familiar).mean()
    assert after < 0.5 * before  # the states it keeps seeing stop paying
    assert rnd.errors(later).mean() > 2 * after  # states it hasn't trained on still do


def bonuses(centre: bool) -> np.ndarray:
    """The bonuses of 40 steps of two envs taking random allowed options, after the first rollout's."""
    vec = DummyVecEnv([lambda: SimEnv(horizon_ticks=3_000) for _ in range(2)])
    vec.seed(1)
    rnd = RNDReward(vec, vec.get_attr("encoder", indices=[0])[0].parts, FEATURES, coef=0.5, seed=0, rollout=8,
                    centre=centre, batch_size=8)
    rnd.reset()
    rng, out = np.random.default_rng(1), []
    for _ in range(40):
        masks = np.stack(rnd.env_method("action_masks"))
        _, _, _, infos = rnd.step(np.array([rng.choice(np.flatnonzero(m)) for m in masks]))
        out.append([info["r_intrinsic"] for info in infos])
    return np.array(out[8:]).ravel()


def test_a_centred_bonus_averages_about_zero_and_burdas_is_positive():
    centred, plain = bonuses(True), bonuses(False)
    assert abs(centred.mean()) < 0.5 * centred.std() and (centred < 0).any() and (centred > 0).any()
    assert (plain > 0).all() and plain.mean() > 2 * abs(centred.mean())


def test_an_rnd_section_with_an_unknown_key_or_part_is_refused():
    check_config(dict(CONFIG))
    with pytest.raises(ValueError, match="unknown rnd keys"):
        check_config({**CONFIG, "rnd": {**CONFIG["rnd"], "beta": 1.0}})
    with pytest.raises(ValueError, match="coef"):
        check_rnd({"coef": 0, "features": FEATURES})
    with pytest.raises(ValueError, match="features"):
        check_rnd({"coef": 1.0})
    vec, _ = states(1)
    with pytest.raises(ValueError, match="aren't parts"):
        RNDReward(vec, vec.get_attr("encoder", indices=[0])[0].parts, ["skills", "levels"], coef=1.0, seed=0,
                  rollout=8)
