"""Tests for the scripted-guide baseline draft (rlscape/baselines/guide.py)."""

from __future__ import annotations

import pytest

from rlscape.baselines.guide import (SKILLS, ScriptedGuidePolicy, fishing_method, fletching_methods, guide_spell,
                                     mining_method, smithing_metals, thieving_methods, woodcutting_method)
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
    assert [woodcutting_method(n) for n in (1, 14, 15, 29, 30, 60)] == ["wc_logs"] * 2 + ["wc_oak"] * 2 + ["wc_willow"] * 2
    assert mining_method(at_level("mining", 14)) in ("mine_copper", "mine_tin")
    assert mining_method(at_level("mining", 15)) == "mine_iron"
    assert fishing_method(at_level("fishing", 19)) == "fish_shrimp_swamp"  # combat 3: Draynor's wizards would attack
    assert fishing_method(at_level("fishing", 20)) == "fish_fly"
    fighter = at_level("fishing", 19)
    for skill in ("attack", "strength", "defence"):
        fighter.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[20])
    assert fighter.combat_level() > 14 and fishing_method(fighter) == "fish_shrimp"
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
    assert fletching_methods(24) == ["wc_logs_fletch"]
    assert fletching_methods(42)[:2] == ["fletch_willow_longbow_u", "wc_willow_fletch"]
    assert fletching_methods(70)[0] == "fletch_string_yew_longbow" and fletching_methods(70)[-1] == "wc_logs_fletch"


def test_a_stint_trains_the_lowest_skill_to_the_next_multiple_of_5():
    policy, state = ScriptedGuidePolicy(), at_level("thieving", 1)
    for skill in SKILLS:
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[12])
    state.xp[SKILL_INDEX["cooking"]] = float(XP_FOR_LEVEL[7])
    assert policy.schedule(state)[0] == "cooking" and policy.stint == ("cooking", 10)
    state.xp[SKILL_INDEX["cooking"]] = float(XP_FOR_LEVEL[9])
    state.xp[SKILL_INDEX["mining"]] = float(XP_FOR_LEVEL[8])  # now lower, but the stint goes on
    assert policy.schedule(state)[:2] == ["cooking", "mining"]
    state.xp[SKILL_INDEX["cooking"]] = float(XP_FOR_LEVEL[10])
    assert policy.schedule(state)[0] == "mining" and policy.stint == ("mining", 10)


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
    # every skill trained. Prayer, the slowest, ends at 3 (220 XP, 56 short of 4): its stints bury a third fewer bones
    # since burying was measured at 3 ticks a bone, not 2 (2026-11-07; 342 XP before)
    assert levels["prayer"] >= 3 and min(v for s, v in levels.items() if s != "prayer") >= 4
    assert levels["thieving"] >= 15 and levels["smithing"] >= 10
