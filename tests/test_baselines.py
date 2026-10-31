"""Tests for the E1 baselines (rlscape.baselines) and the episode rollout (rlscape.eval)."""

from __future__ import annotations

from copy import deepcopy

import pytest

from rlscape.baselines import GreedyPolicy, RandomPolicy, e1_baselines
from rlscape.envs import SimEnv
from rlscape.eval import play
from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
HOUR = 6_000
COPPER_ORE = 436


@pytest.fixture(scope="module")
def env():
    return SimEnv(horizon_ticks=HOUR)


def test_random_repeats_by_seed(env):
    first, second = play(env, RandomPolicy(), seed=3), play(env, RandomPolicy(), seed=3)
    assert first.options == second.options and first.net_worth == second.net_worth and first.decisions > 5


def test_greedy_takes_its_best_estimate(env):
    obs, _ = env.reset(seed=0)
    policy = GreedyPolicy("skill")
    policy.reset(0)
    rates = policy.estimates(env)
    policy.reset(0)  # the same lookahead samples again
    action = policy.act(env, obs)
    assert rates[action] == max(rates.values()) > 0
    assert all(env.options[a].family != "loot" for a in rates)


def test_greedy_lookahead_leaves_the_episode_untouched(env):
    env.reset(seed=1)
    state, rng = deepcopy(env.sim.state), deepcopy(env.sim.rng.bit_generator.state)
    GreedyPolicy("wealth").estimates(env)
    assert env.sim.state == state and env.sim.rng.bit_generator.state == rng


def test_greedy_banks_when_nothing_pays(env):
    env.reset(seed=0)
    env.sim.state.inventory = {COPPER_ORE: 28}  # full: no gathering, no loot; selling at the GE only swaps value
    obs = env.observe()
    policy = GreedyPolicy("wealth")
    policy.reset(0)
    assert max(policy.estimates(env).values()) <= 0
    policy.reset(0)
    assert env.options[policy.act(env, obs)].id == "bank_deposit"


@pytest.mark.parametrize("objective", ["skill", "wealth"])
def test_greedy_beats_random_on_its_own_objective(env, objective):
    index = 0 if objective == "skill" else 1
    greedy, random = play(env, GreedyPolicy(objective), seed=0), play(env, RandomPolicy(), seed=0)
    assert greedy.reward_vec[index] > random.reward_vec[index] > -1


def test_play_collects_the_contracts_checkpoints():
    episode = play(SimEnv(horizon_ticks=4 * HOUR), RandomPolicy(), seed=5)
    assert episode.game_ticks == 4 * HOUR and sorted(episode.checkpoints) == [2, 4]
    assert episode.checkpoints[4]["total_level"] == episode.total_level
    assert episode.checkpoints[4]["total_xp"] == episode.total_xp > episode.checkpoints[2]["total_xp"] > 1_154
    assert episode.reward == pytest.approx(0.5 * episode.reward_vec[0] + 0.5 * episode.reward_vec[1])


def test_e1_uses_raw_xp_net_worth_and_the_reviewed_guide():
    assert [p.name for p in e1_baselines()] == ["random", "greedy_xp", "greedy_wealth", "scripted_guide"]
