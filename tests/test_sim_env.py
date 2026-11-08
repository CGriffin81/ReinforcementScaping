"""Tests for SimEnv and the observation encoder (env contract §2, §3, §6)."""

from __future__ import annotations

from math import log1p

import numpy as np
import pytest

from rlscape.envs import DEFAULT_REWARD_WEIGHTS, SimEnv
from rlscape.envs.encoding import REGIONS, item_roles, region_of
from rlscape.gamedata import server as gd
from rlscape.sim.energy import weight
from rlscape.sim.state import CharacterState

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
LOGS, RAW_LOBSTER, RUNE_BODY, RUNE_AXE = 1511, 377, 1127, 1359


@pytest.fixture(scope="module")
def env():
    return SimEnv()


def part(env: SimEnv, obs: np.ndarray, name: str) -> np.ndarray:
    return obs[env.encoder.parts[name]]


def random_run(env: SimEnv, seed: int, steps: int, policy_seed: int = 0) -> tuple[list[np.ndarray], list[float]]:
    obs, _ = env.reset(seed=seed)
    rng, observations, rewards = np.random.default_rng(policy_seed), [obs], []
    for _ in range(steps):
        obs, reward, terminated, truncated, _ = env.step(int(rng.choice(np.flatnonzero(env.action_masks()))))
        observations.append(obs)
        rewards.append(reward)
        if truncated:
            break
    return observations, rewards


def test_spaces_and_catalog_line_up(env):
    obs, info = env.reset(seed=0)
    assert env.observation_space.contains(obs) and obs.dtype == np.float32
    catalog = env.option_catalog()
    assert len(catalog) == env.action_space.n and [s.action for s in catalog] == list(range(env.action_space.n))
    assert len({s.id for s in catalog}) == len(catalog)
    slices = list(env.encoder.parts.values())
    assert slices[0].start == 0 and slices[-1].stop == env.encoder.size == len(env.encoder.names)
    assert all(a.stop == b.start for a, b in zip(slices, slices[1:]))
    assert info["game_ticks"] == 0 and info["coins"] == 25  # the starter kit's 25 coins in the bank


def test_a_fresh_observation_reads_the_starting_character(env):
    obs, _ = env.reset(seed=0)
    fresh = CharacterState.fresh()
    assert list(part(env, obs, "time")) == [0.0, 1.0]
    assert list(part(env, obs, "hitpoints_prayer")) == [1.0, 1.0]
    assert part(env, obs, "run_energy_weight") == pytest.approx([1.0, weight(fresh) / 100])
    assert part(env, obs, "inventory")[-1] == pytest.approx(fresh.free_slots() / 28)
    assert env.encoder.names[env.encoder.parts["region"]][np.argmax(part(env, obs, "region"))] == "lumbridge"
    assert list(part(env, obs, "loot_mode")) == [0.0, 1.0, 0.0, 0.0]  # "valuable", the default
    assert "quests" not in env.encoder.parts  # every quest is complete from the start, so it would be constant
    assert np.array_equal(part(env, obs, "mask"), env.action_masks())
    skills = dict(zip(env.encoder.names[env.encoder.parts["skills"]], part(env, obs, "skills")))
    assert skills["hitpoints_level"] == pytest.approx(10 / 99) and skills["attack_level"] == pytest.approx(1 / 99)
    assert "farming_level" not in skills and "slayer_level" in skills


def test_the_same_seed_gives_the_same_trajectory():
    first, second = SimEnv(), SimEnv()
    obs_a, rewards_a = random_run(first, seed=7, steps=25)
    obs_b, rewards_b = random_run(second, seed=7, steps=25)
    assert rewards_a == rewards_b and all(np.array_equal(a, b) for a, b in zip(obs_a, obs_b))
    # a reset without a seed continues the seeded stream, so it repeats too
    assert np.array_equal(first.reset()[0], second.reset()[0])
    first.step(int(np.flatnonzero(first.action_masks())[0]))
    second.step(int(np.flatnonzero(second.action_masks())[0]))
    assert first.sim.state.tick == second.sim.state.tick


def test_the_reward_is_the_weighted_pair(env):
    for weights in [(1.0, 0.0), (0.2, 0.8)]:
        env.reset(seed=3, options={"reward_weights": weights})
        mask = env.action_masks()
        action = next(s.action for s in env.option_catalog() if s.id == "skill_woodcutting_xp1")
        assert mask[action]
        _, reward, _, _, info = env.step(action)
        r_skill, r_wealth = info["reward_vec"]
        assert r_skill > 0 and reward == pytest.approx(weights[0] * r_skill + weights[1] * r_wealth)
    env.reset(seed=3)
    assert env.weights == DEFAULT_REWARD_WEIGHTS  # back to the defaults when the options don't set them


def test_a_masked_action_raises(env):
    env.reset(seed=0)
    masked = int(np.flatnonzero(~env.action_masks())[0])
    with pytest.raises(ValueError):
        env.step(masked)


def test_episodes_end_only_by_truncation_at_the_horizon():
    env = SimEnv(horizon_ticks=3_000)
    env.reset(seed=1)
    rng = np.random.default_rng(1)
    for _ in range(500):
        obs, _, terminated, truncated, info = env.step(int(rng.choice(np.flatnonzero(env.action_masks()))))
        assert not terminated
        if truncated:
            break
    assert truncated and info["game_ticks"] == 3_000 and list(part(env, obs, "time")) == [1.0, 0.0]


def test_the_observation_shows_how_long_until_the_home_teleport_is_ready(env):
    """Caleb, 2026-11-08, OQ-15: the ticks left on its 30-minute cooldown, over the cooldown; 0 when ready."""
    from rlscape.gamedata.transports import HOME_COOLDOWN_TICKS
    env.reset(seed=0)
    state = env.sim.state
    reading = lambda: float(part(env, env.encoder.encode(state, env.sim.action_mask()), "home_teleport")[0])  # noqa: E731
    assert reading() == 0.0  # a fresh character's is ready
    state.home_teleport_ready = state.tick + HOME_COOLDOWN_TICKS // 2
    assert reading() == pytest.approx(0.5)
    state.home_teleport_ready = state.tick + HOME_COOLDOWN_TICKS
    assert reading() == pytest.approx(1.0)
    state.home_teleport_ready = state.tick - 10
    assert reading() == 0.0


def test_the_preference_part_is_only_there_for_the_e4_agent(env):
    conditioned = SimEnv(preference_in_obs=True)
    obs, _ = conditioned.reset(seed=0, options={"reward_weights": (0.3, 0.7)})
    assert part(conditioned, obs, "preference") == pytest.approx([0.3, 0.7])
    assert conditioned.encoder.size == env.encoder.size + 2 and "preference" not in env.encoder.parts


def test_vocabulary_items_get_inventory_and_bank_features():
    env = SimEnv(vocabulary=(RAW_LOBSTER, LOGS))
    env.reset(seed=0)
    env.sim.state.inventory[LOGS] = 5
    env.sim.state.bank[RAW_LOBSTER] = 120
    obs = env.encoder.encode(env.sim.state, env.sim.action_mask())
    names = dict(zip(env.encoder.names, obs))
    assert names["inv_Logs"] == pytest.approx(log1p(5) / log1p(28)) and names["inv_Raw lobster"] == 0.0
    assert names["bank_Raw lobster"] == pytest.approx(log1p(120) / log1p(10_000))


def test_equipment_tiers_and_regions():
    assert ("body", 7) in item_roles(RUNE_BODY)
    assert ("melee_weapon", 7) in item_roles(RUNE_AXE) and any(role == "axe" for role, _ in item_roles(RUNE_AXE))
    names = list(REGIONS) + ["elsewhere"]
    assert names[region_of((3212, 3424, 0))] == "varrock" and names[region_of((3165, 3489, 0))] == "grand_exchange"
    assert names[region_of((2612, 3093, 0))] == "elsewhere"  # Yanille
    assert names[region_of((3094, 9893, 0))] == "edgeville"  # the dungeon under Edgeville


def test_candidate_features_follow_the_slots(env):
    obs, _ = env.reset(seed=0)
    features = part(env, obs, "combat_candidates").reshape(-1, 5)
    names = env.encoder.names[env.encoder.parts["combat_candidates"]][::5]
    mask = dict(zip((s.id for s in env.option_catalog()), env.action_masks()))
    for name, row in zip(names, features):
        slot = name.removesuffix("_xp_per_hour")  # e.g. "ranged_xp1"
        if not slot.startswith("melee"):  # ranged and magic slots have one action each
            assert row[4] == mask[f"fight_{slot}"]
        assert row[4] in (0.0, 1.0) and (row[4] == 1.0 or not row[:4].any())
    assert features[0, 4] == 1.0 and features[0, 0] > 0  # a fresh character has a melee target
