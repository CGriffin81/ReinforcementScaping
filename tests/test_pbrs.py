"""E6b's potential-based shaping (rlscape/agents/pbrs.py) and the trainer with it: Φ moves only with what the
character could earn, it's 0 at the episode's end, the shaping telescopes as Ng et al.'s does, and it's logged apart
from the env's reward. Real sim states throughout."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
pytest.importorskip("rlscape.agents.ppo")

from rlscape.agents.decision_log import read_decisions  # noqa: E402
from rlscape.agents.pbrs import GatheringIncome, PBRSShaping, Potential, annuity  # noqa: E402
from rlscape.agents.smdp import option_discounts  # noqa: E402
from rlscape.agents.training import check_config, train  # noqa: E402
from rlscape.envs.sim_env import SimEnv  # noqa: E402
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL  # noqa: E402
from rlscape.sim.state import CharacterState  # noqa: E402

CONFIG = {"seeds": [0], "total_decisions": 32, "n_envs": 2, "vec_env": "dummy", "device": "cpu",
          "env": {"hours": 0.5, "reward_weights": [0.5, 0.5]},
          "ppo": {"gamma_hr": 0.9, "n_steps": 8, "batch_size": 8, "n_epochs": 1},
          "pbrs": {"potential": "gathering_income"}, "checkpoint_every": 32, "decision_log": True}


@pytest.fixture(scope="module")
def income():
    return GatheringIncome()


def with_level(skill: str, level: int) -> CharacterState:
    state = CharacterState.fresh()
    state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


def test_the_income_moves_with_levels_and_unlocks_not_with_place_pack_or_fighting(income):
    fresh = income(CharacterState.fresh())
    assert fresh > 0
    assert income(with_level("thieving", 40)) > fresh  # an investment: a gathering level that opens a better method
    moved, packed, fighter = CharacterState.fresh(), CharacterState.fresh(), with_level("attack", 40)
    moved.location = (3222, 3218, 0)
    packed.inventory = {1511: 20}  # logs filling the pack
    assert income(moved) == income(packed) == income(fighter) == fresh


def test_the_potential_is_zero_at_the_end_and_discounts_the_time_left(income):
    potential, state = Potential(0.99, 120_000, income), CharacterState.fresh()
    assert potential(state, 2.0) == pytest.approx(2.0 * income(state) / 100_000 * annuity(20, 0.99))
    state.tick = 120_000
    assert potential(state, 2.0) == 0.0
    assert annuity(20, 1.0) == 20 and 0 < annuity(20, 0.99) < 20 and annuity(0, 0.99) == 0.0


def test_the_shaping_telescopes_and_is_kept_apart():
    """Over a whole episode the discounted shaping sums to −Φ(s₀), Ng et al.'s identity, so it can't change which
    policy is best; each step's reward is the env's plus F."""
    shaped, plain = PBRSShaping(SimEnv(horizon_ticks=3_000), 0.9), SimEnv(horizon_ticks=3_000)
    _, info = shaped.reset(seed=3)
    plain.reset(seed=3)
    phi0, rng, total, discount, done = info["potential"], np.random.default_rng(3), 0.0, 1.0, False
    assert phi0 > 0
    while not done:
        action = int(rng.choice(np.flatnonzero(shaped.get_wrapper_attr("action_masks")())))
        _, reward, terminated, truncated, info = shaped.step(action)
        _, plain_reward, *_ = plain.step(action)
        assert info["reward_extrinsic"] == pytest.approx(plain_reward) and reward == pytest.approx(
            plain_reward + info["r_shaping"])
        total += discount * info["r_shaping"]
        discount *= float(option_discounts(np.array([info["duration"]]), 0.9)[0])
        done = terminated or truncated
    assert info["potential"] == 0.0 and total == pytest.approx(-phi0, rel=1e-9, abs=1e-9)


def test_a_run_with_pbrs_logs_the_shaping_apart(tmp_path):
    run = train(dict(CONFIG), "e6b-test", 0, tmp_path / "run")
    log = read_decisions(run / "decisions")
    assert np.allclose(log.reward, 0.5 * log.r_skill + 0.5 * log.r_wealth + log.r_shaping, atol=1e-4)
    assert (log.r_shaping != 0).any() and (log.r_intrinsic == 0).all()
    episodes = pd.read_parquet(run / "episodes.parquet")
    first = log[(log.env == episodes.iloc[0].env) & (log.episode == 0)]
    assert episodes.iloc[0].r_shaping == pytest.approx(first.r_shaping.sum(), rel=1e-4)


def test_a_pbrs_section_must_name_a_known_potential():
    check_config(dict(CONFIG))
    with pytest.raises(ValueError, match="potential"):
        check_config({**CONFIG, "pbrs": {"potential": "net_worth"}})
    with pytest.raises(ValueError, match="unknown pbrs keys"):
        check_config({**CONFIG, "pbrs": {"potential": "gathering_income", "scale": 2}})
