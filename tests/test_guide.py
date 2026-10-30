"""Tests for the scripted-guide baseline draft (rlscape/baselines/guide.py)."""

from __future__ import annotations

import pytest

from rlscape.baselines.guide import ScriptedGuidePolicy, fishing_method, mining_method, woodcutting_method
from rlscape.envs import SimEnv
from rlscape.eval import play
from rlscape.gamedata import server as gd
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")


def at_level(skill: str, level: int) -> CharacterState:
    state = CharacterState.fresh()
    state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


def test_methods_follow_the_2009_guides_breakpoints():
    assert [woodcutting_method(n) for n in (1, 14, 15, 40, 41, 60)] == ["wc_logs"] * 2 + ["wc_oak"] * 2 + ["wc_willow"] * 2
    assert mining_method(at_level("mining", 14)) in ("mine_copper", "mine_tin")
    assert mining_method(at_level("mining", 15)) == "mine_iron"
    assert fishing_method(at_level("fishing", 19)) == "fish_shrimp" and fishing_method(at_level("fishing", 20)) == "fish_fly"


def test_a_guided_episode_is_deterministic_and_balanced():
    env = SimEnv(horizon_ticks=6 * 6_000)
    first, second = play(env, ScriptedGuidePolicy(), seed=4), play(env, ScriptedGuidePolicy(), seed=4)
    assert first.options == second.options and first.net_worth == second.net_worth
    assert first.decisions < 600  # no loops (each was thousands of decisions)
    state = env.sim.state
    combat = [state.level(s) for s in ("attack", "strength", "defence")]
    assert min(combat) > 1 and max(combat) - min(combat) <= 5  # together, though one 15-minute fight gains several
    assert all(state.level(s) > 1 for s in ("woodcutting", "mining", "fishing"))
