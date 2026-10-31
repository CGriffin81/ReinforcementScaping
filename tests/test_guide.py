"""Tests for the scripted-guide baseline draft (rlscape/baselines/guide.py)."""

from __future__ import annotations

import pytest

from rlscape.baselines.guide import (SKILLS, ScriptedGuidePolicy, fishing_method, guide_spell, mining_method,
                                     smithing_metals, thieving_methods, woodcutting_method)
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
    first = {level: thieving_methods(level)[0] for level in (1, 4, 5, 19, 20, 34, 35, 37, 38, 54, 55, 64, 65, 99)}
    assert first == {1: "pickpocket_men", 4: "pickpocket_men", 5: "steal_bakers_stall", 19: "steal_bakers_stall",
                     20: "steal_silk_stall", 34: "steal_silk_stall", 35: "steal_fur_stall", 37: "steal_fur_stall",
                     38: "pickpocket_master_farmers", 54: "pickpocket_master_farmers", 55: "pickpocket_knights",
                     64: "pickpocket_knights", 65: "pickpocket_menaphite_thugs", 99: "pickpocket_menaphite_thugs"}
    assert thieving_methods(65)[1:] == ["pickpocket_knights", "pickpocket_master_farmers", "steal_fur_stall",
                                        "steal_silk_stall", "steal_bakers_stall", "pickpocket_men"]  # fallbacks
    assert [guide_spell(n).name for n in (1, 9, 13, 16, 17, 35, 99)] == [
        "wind_strike", "earth_strike", "fire_strike", "fire_strike", "wind_bolt", "fire_bolt", "fire_bolt"]
    assert smithing_metals(14) == ("bronze",) and smithing_metals(15) == ("iron", "bronze")


def test_a_guided_episode_is_deterministic_and_balanced():
    env = SimEnv(horizon_ticks=6 * 6_000)
    first, second = play(env, ScriptedGuidePolicy(), seed=4), play(env, ScriptedGuidePolicy(), seed=4)
    assert first.options == second.options and first.net_worth == second.net_worth
    assert first.decisions < 300  # no loops (each was thousands of decisions)
    state = env.sim.state
    combat = [state.level(s) for s in ("attack", "strength", "defence")]
    assert min(combat) > 1 and max(combat) - min(combat) <= 5  # together, though one 15-minute fight gains several
    assert all(state.level(s) > 1 for s in SKILLS)  # every scheduled skill gets trained


def test_a_long_guided_episode_trains_every_skill_without_loops():
    env = SimEnv()  # 20 game-hours
    episode = play(env, ScriptedGuidePolicy(), seed=0)
    assert episode.decisions < 1_000  # the loops found while widening it ran to thousands
    levels = {s: env.sim.state.level(s) for s in SKILLS}
    assert min(levels.values()) >= 5 and levels["thieving"] >= 15 and levels["smithing"] >= 10
