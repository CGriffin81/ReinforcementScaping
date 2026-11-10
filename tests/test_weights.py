"""Normalised reward weights (rlscape/envs/weights.py, OQ-67): the units are E1's, the conversion keeps a level worth
u_s, and train.py's configs take them, on the real sim."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rlscape.envs.weights import E1_SUMMARY, SKILL_UNIT, WEALTH_FACTOR, WEALTH_UNIT, env_weights, normalised_weights
from rlscape.eval.harness import REPO
from rlscape.gamedata import server as gd


def test_the_units_are_e1s_best_20_hour_gains():
    """The guide's mean r_skill and greedy GP/hr's mean r_wealth over E1's 30 seeds, each the best of the four."""
    means = pd.read_csv(REPO / E1_SUMMARY).groupby("policy")[["r_skill", "r_wealth"]].mean()
    assert means.r_skill.idxmax() == "scripted_guide" and means.r_wealth.idxmax() == "greedy_wealth"
    assert means.r_skill.max() == pytest.approx(SKILL_UNIT, rel=1e-12)
    assert means.r_wealth.max() == pytest.approx(WEALTH_UNIT, rel=1e-12)


def test_the_conversion_keeps_a_level_worth_u_s_and_round_trips():
    assert env_weights([1, 0]) == (1.0, 0.0)
    assert env_weights([0.5, 0.5]) == pytest.approx((0.5, 8.5674), abs=1e-4)
    assert env_weights([0, 1]) == pytest.approx((0.0, WEALTH_FACTOR))
    for u in ([1, 0], [0.75, 0.25], [0.5, 0.5], [0.25, 0.75], [0, 1]):
        assert normalised_weights(env_weights(u)) == pytest.approx(tuple(u))
    # the ideal point's two gains weigh the same at (.5, .5): the guide's levels and greedy GP/hr's gp
    w_s, w_b = env_weights([0.5, 0.5])
    assert w_s * SKILL_UNIT == pytest.approx(w_b * WEALTH_UNIT)


@pytest.mark.parametrize("bad", [[0.5, 0.6], [1.2, -0.2], [1.0], [0.5, 0.25, 0.25]])
def test_weights_off_the_simplex_are_refused(bad):
    with pytest.raises(ValueError):
        env_weights(bad)


@pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
def test_configs_take_normalised_weights_and_the_env_rewards_by_them():
    pytest.importorskip("rlscape.agents.ppo")
    from rlscape.agents.training import check_config, env_kwargs, variants
    from rlscape.envs.sim_env import SimEnv

    base = {"seeds": [0], "total_decisions": 32, "n_envs": 1, "ppo": {"gamma_hr": 0.99}}
    config = check_config({**base, "env": {"normalised_weights": [0.5, 0.5]}})
    assert env_kwargs(config)["reward_weights"] == env_weights([0.5, 0.5])
    with pytest.raises(ValueError, match="not both"):
        check_config({**base, "env": {"normalised_weights": [0.5, 0.5], "reward_weights": [0.5, 0.5]}})
    with pytest.raises(ValueError, match="sum to 1"):
        check_config({**base, "env": {"normalised_weights": [0.5, 0.4]}})
    swept = variants({**base, "sweep": {"env.normalised_weights": [[1.0, 0.0], [0.75, 0.25]]}})
    assert [name for name, _ in swept] == ["normalised_weights1-0", "normalised_weights0.75-0.25"]
    assert env_kwargs(swept[1][1])["reward_weights"] == env_weights([0.75, 0.25])

    env, rng, wealth_moved = SimEnv(**env_kwargs(config)), np.random.default_rng(0), False
    env.reset(seed=0)
    for _ in range(40):  # random options, until net worth has moved at least once
        _, reward, _, _, info = env.step(int(rng.choice(np.flatnonzero(env.action_masks()))))
        r_skill, r_wealth = info["reward_vec"]
        assert reward == pytest.approx(0.5 * r_skill + 0.5 * WEALTH_FACTOR * r_wealth)
        wealth_moved |= r_wealth != 0
    assert wealth_moved
