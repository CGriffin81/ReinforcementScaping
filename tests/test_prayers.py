"""Tests for prayer flicking in fights (rlscape.combat.prayers), against the server's PrayerType and swing handlers and
the live tests (scripts/prayer_flick_test.py, scripts/prayer_offence_test.py)."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat import formulas as f
from rlscape.combat.candidates import enemy_pool, loot_rule
from rlscape.combat.prayers import NO_FLICKS, boosted_share, boosted_swings, flicks
from rlscape.combat.rates import Fighter, Plan, combat_rates, npc_offence
from rlscape.gamedata import server as gd
from rlscape.sim.combat import fight, kill_sequence
from rlscape.sim.equipment import fighter_for
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.PRAYER_TYPE.exists(), reason="server submodule missing")


def cow_and_site():
    cow = next(e for e in enemy_pool() if e.npc.id == 81)
    return cow, min(cow.sites, key=lambda s: abs(s.spawn[0] - 3255) + abs(s.spawn[1] - 3255))


@needs_server
def test_the_prayers_follow_prayer_type():
    p = gd.prayers()
    assert (p["ULTIMATE_STRENGTH"].level, p["ULTIMATE_STRENGTH"].bonuses) == (31, (("strength", 0.15),))
    assert (p["EAGLE_EYE"].level, p["MYSTIC_MIGHT"].level, p["PROTECT_FROM_MELEE"].level) == (44, 45, 43)
    assert (p["PIETY"].defence_level, p["PIETY"].quest, p["THICK_SKIN"].quest) == (70, "KINGS_RANSOM", None)


@needs_server
def test_a_fight_flicks_the_best_prayers_the_levels_allow():
    assert flicks(1) == flicks(1).__class__(defence=0.05)  # Thick Skin only
    at_31 = flicks(31)
    assert (at_31.attack, at_31.strength, at_31.defence, at_31.ranged, at_31.magic) == (0.1, 0.15, 0.15, 0.1, 0.1)
    assert not at_31.protects and flicks(43).protects == {"melee", "ranged", "magic"}
    assert flicks(70, 70).strength == 0.15  # Piety needs King's Ransom
    assert flicks(70, 70, frozenset({"KINGS_RANSOM"})).strength == 0.23


def test_offensive_flicks_skip_swings_next_to_a_monster_swing():
    assert boosted_swings(4, 6) == (True, True, True)  # both speeds even: never adjacent
    assert boosted_swings(4, 5) == (True, False, True, True, False)  # swings at 4 and 16 meet the monster's 5 and 15
    assert boosted_share(5, 5) == 1.0 and boosted_share(4, 4) == 1.0


def test_a_strength_prayer_raises_the_max_hit_as_measured_live():
    """Strength 60, unarmed and accurate: 7, and 8 with Ultimate Strength flicked (prayer_offence_test)."""
    assert f.player_melee_max_hit(60, f.ACCURATE, 0) == 7
    assert f.player_melee_max_hit(60, f.ACCURATE, 0, 0.15) == 8
    assert f.prayer_boosted(60, 0.15) == 69


@needs_server
def test_a_protected_style_deals_nothing_and_defence_prayers_count_otherwise():
    cow, _ = cow_and_site()
    plain = Fighter(10, 10, 10, 10, 1, 1, gd.NO_BONUSES)
    unprotected = Fighter(10, 10, 10, 10, 1, 1, gd.NO_BONUSES, flicks=flicks(42))
    protected = Fighter(10, 10, 10, 10, 1, 1, gd.NO_BONUSES, flicks=flicks(43))
    melee = Plan("melee", f.ACCURATE)
    assert npc_offence(protected, melee, cow.npc)[1:] == (0, 0.0, 0.0)
    assert npc_offence(unprotected, melee, cow.npc)[0] < npc_offence(plain, melee, cow.npc)[0]  # Steel Skin
    assert combat_rates(protected, melee, cow.npc, 0.0).damage_taken_per_hour == 0
    assert combat_rates(protected, melee, cow.npc, 0.0).kills_per_hour > combat_rates(plain, melee, cow.npc,
                                                                                     0.0).kills_per_hour


def test_a_kill_with_every_swing_boosted_samples_the_boosted_rolls():
    boosted = kill_sequence(50, 0.6, 8, np.random.default_rng(0), (0.7, 9, (True, True)))
    assert np.array_equal(boosted, kill_sequence(50, 0.7, 9, np.random.default_rng(0)))
    mixed = kill_sequence(50, 0.6, 8, np.random.default_rng(0), (0.7, 9, (True, False)))
    assert mixed[-1] >= 50 and np.all(np.diff(mixed) >= 0)


@needs_server
def test_a_character_with_protect_from_melee_takes_nothing_from_cows():
    cow, site = cow_and_site()
    state = CharacterState.fresh()
    state.xp[SKILL_INDEX["prayer"]] = float(XP_FOR_LEVEL[43])
    assert fighter_for(state).flicks.protects >= {"melee"} and fighter_for(CharacterState.fresh()).flicks != NO_FLICKS
    result = fight(state, np.random.default_rng(0), 1500, cow, Plan("melee", f.AGGRESSIVE), site, loot_rule("valuable"))
    assert state.hp == 10 and result.termination != "out_of_food" and result.detail["kills"] > 0
