"""E5's weight-conditioned agent (rlscape/agents/conditioned.py, the trainer and rlscape/eval/trained.py): each
episode draws a weighting, is rewarded by it and shows it; a run is repeatable; a trained agent is evaluated at any
weighting by the harness. Real sim episodes throughout."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
pytest.importorskip("rlscape.agents.ppo")

from rlscape.agents.conditioned import WeightConditioned  # noqa: E402
from rlscape.agents.decision_log import read_decisions  # noqa: E402
from rlscape.agents.training import check_config, train  # noqa: E402
from rlscape.envs.sim_env import SimEnv  # noqa: E402
from rlscape.envs.weights import WEALTH_FACTOR, env_weights  # noqa: E402
from rlscape.eval.harness import run as evaluate  # noqa: E402
from rlscape.eval.trained import TrainedPolicy, preference, split  # noqa: E402

N_OBS = 3_488  # sim v1.2 (env contract v1.44)
CONFIG = {"seeds": [0], "total_decisions": 48, "n_envs": 2, "vec_env": "dummy", "device": "cpu",
          "env": {"hours": 0.25}, "conditioned": {"weights": "uniform"},
          "ppo": {"gamma_hr": 0.9, "n_steps": 8, "batch_size": 8, "n_epochs": 1},
          "checkpoint_every": 48, "decision_log": True}


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    root = tmp_path_factory.mktemp("e5")
    return train(dict(CONFIG), "e5-test", 0, root / "a"), train(dict(CONFIG), "e5-test", 0, root / "b")


def test_each_episode_draws_a_weighting_is_rewarded_by_it_and_shows_it():
    env, plain = WeightConditioned(SimEnv(horizon_ticks=1_500)), SimEnv(horizon_ticks=1_500)
    obs, info = env.reset(seed=7)
    u = np.array(info["preference"])
    assert 0 <= u[0] <= 1 and u.sum() == pytest.approx(1) and obs.shape == (N_OBS + 2,) and np.allclose(obs[-2:], u)
    assert env.unwrapped.weights == pytest.approx(env_weights(u))
    plain.reset(seed=7, options={"reward_weights": env_weights(u)})  # the same episode, unconditioned
    rng, done = np.random.default_rng(0), False
    while not done:
        action = int(rng.choice(np.flatnonzero(plain.action_masks())))
        obs, reward, terminated, truncated, _ = env.step(action)
        plain_obs, plain_reward, *_ = plain.step(action)
        assert reward == pytest.approx(plain_reward)  # rewarded by its own weighting
        assert np.allclose(obs[:-2], plain_obs) and np.allclose(obs[-2:], u)  # and shown it throughout
        done = terminated or truncated
    draws = {round(u[0], 9)} | {round(env.reset()[1]["preference"][0], 9) for _ in range(3)}
    assert len(draws) == 4  # a fresh weighting each episode
    again = WeightConditioned(SimEnv(horizon_ticks=1_500))
    assert again.reset(seed=7)[1]["preference"] == info["preference"]  # the same seed, the same draws


def test_a_conditioned_run_is_repeatable_and_logs_each_episodes_weighting(runs):
    a, b = (read_decisions(r / "decisions") for r in runs)
    shares = np.stack(a.obs.to_numpy())[:, -2:]
    assert np.allclose(shares.sum(axis=1), 1) and len(np.unique(np.round(shares[:, 0], 6))) > 1
    reward = shares[:, 0] * a.r_skill + shares[:, 1] * WEALTH_FACTOR * a.r_wealth
    assert np.allclose(a.reward, reward, atol=1e-4)  # each decision rewarded by its episode's weighting
    assert (a.action == b.action).all() and np.allclose(np.stack(b.obs.to_numpy())[:, -2:], shares)


def test_a_trained_agent_is_evaluated_at_a_given_weighting(runs):
    model = runs[0] / "model.zip"
    spec = f"e5/seed0@0.25=ppo:{model}@0.25"
    assert split(spec) == ("e5/seed0@0.25", model) and np.allclose(preference(spec), [0.25, 0.75])
    assert preference(f"x=ppo:{model}") is None
    with pytest.raises(ValueError, match="skill share"):
        preference(f"x=ppo:{model}@1.5")
    assert TrainedPolicy(spec).model.observation_space.shape == (N_OBS + 2,)
    checkpoints, episodes = evaluate([spec, f"e5/seed0@1=ppo:{model}@1"], [0], {"horizon_ticks": 1_500}, workers=1)
    assert sorted(episodes.policy) == ["e5/seed0@0.25", "e5/seed0@1"] and (episodes.decisions > 0).all()


def test_a_conditioned_config_sets_no_weights_of_its_own():
    check_config(dict(CONFIG))
    with pytest.raises(ValueError, match="sets none"):
        check_config({**CONFIG, "env": {"normalised_weights": [0.5, 0.5]}})
    with pytest.raises(ValueError, match="conditioned.weights"):
        check_config({**CONFIG, "conditioned": {"weights": "dirichlet"}})
