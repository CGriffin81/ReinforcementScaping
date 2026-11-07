"""Combat potions and antifire (Caleb, 2026-11-06; rlscape.sim.potions), and a dragon's breath (rlscape.combat.rates):
a dose boosts by the server's SkillEffect and wears off a level every 101 ticks; fights drink to keep the boost up;
behind an anti-dragon shield the breath hits up to 5 on a third of a dragon's swings, and with antifire, nothing."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat import formulas as f
from rlscape.combat.candidates import enemy_pool, loot_rule
from rlscape.combat.rates import Plan, breath_max, combat_rates
from rlscape.gamedata import server as gd
from rlscape.sim.combat import die, fight
from rlscape.sim.equipment import fighter_for, wield_best
from rlscape.sim.health import VIAL, regenerate
from rlscape.sim.kits import kit
from rlscape.sim.economy import is_misc
from rlscape.sim.potions import (ANTIFIRE_TICKS, antifire_cover, dose_boost, doses_held, drink, drink_antifire,
                                  drink_boosts)
from rlscape.vocabulary import vocabulary
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
SUPER_STRENGTH_4, SUPER_STRENGTH_3, SUPER_STRENGTH_1, STRENGTH_4 = 2440, 157, 161, 113
ANTIFIRE_4, ANTIFIRE_1, GREEN_DRAGON, ANTI_DRAGON_SHIELD, SHARK = 2452, 2458, 941, 1540, 385


def at(level: int) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory.clear()
    for skill in ("attack", "strength", "defence", "hitpoints", "prayer", "ranged", "magic"):
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.hp = level
    return state


def test_a_dose_boosts_by_the_servers_formula_tops_up_and_wears_off():
    state = at(60)
    state.inventory = {SUPER_STRENGTH_4: 1}
    drink(state, SUPER_STRENGTH_4)
    assert dose_boost("super_strength", 60) == 14 == state.boosts["strength"]  # int(5 + 0.15 x 60)
    assert state.boosted("strength") == 74 and state.inventory == {SUPER_STRENGTH_3: 1}
    assert fighter_for(state).strength == 74
    regenerate(state, 101 * 4)  # SkillRestore: a level every 101 ticks
    assert state.boosts["strength"] == 10
    state.inventory = {SUPER_STRENGTH_1: 1}
    drink(state, SUPER_STRENGTH_1)
    assert state.boosts["strength"] == 14 and state.inventory == {VIAL: 1}  # back to a dose's, no higher
    die(state, 0)
    assert state.boosts == {}


def test_fights_drink_the_best_potion_once_the_boost_is_half_gone():
    state = at(60)
    state.inventory = {SUPER_STRENGTH_4: 1, STRENGTH_4: 1}
    assert drink_boosts(state, "melee") == 2 and state.boosts["strength"] == 14  # the super first
    assert drink_boosts(state, "melee") == 0  # not half gone yet
    state.boosts["strength"] = 7
    drink_boosts(state, "melee")
    assert state.boosts["strength"] == 14 and state.inventory[STRENGTH_4] == 1
    assert drink_boosts(state, "ranged") == 0  # no ranging potion: a strength potion is no use to it
    assert STRENGTH_4 in kit(state, "combat:melee") and STRENGTH_4 not in kit(state, "combat:ranged")


@needs_server
def test_potions_raise_a_fights_rates():
    cow = next(e for e in enemy_pool() if e.npc.id == 81)
    site = min(cow.sites, key=lambda s: abs(s.spawn[0] - 3255) + abs(s.spawn[1] - 3255))
    xp = {}
    for potions in (0, 2):
        state = at(40)
        state.inventory = {1333: 1, **({SUPER_STRENGTH_4: potions} if potions else {})}
        state.location = site.spawn
        fight(state, np.random.default_rng(0), 1500, cow, Plan("melee", f.AGGRESSIVE), site, loot_rule("none"))
        xp[potions] = state.xp[SKILL_INDEX["strength"]]
    assert xp[2] > xp[0]


def test_the_breath_behind_the_shield_and_with_antifire():
    assert breath_max(False) == 5 and breath_max(True) == 0  # 52, less 90% (shield) and 10% more (antifire)
    state = at(80)
    state.inventory = {ANTIFIRE_4: 1, ANTIFIRE_1: 1}
    assert drink_antifire(state, 100) == 2 and state.antifire_until == 100 + ANTIFIRE_TICKS
    assert ANTIFIRE_1 not in state.inventory  # the emptiest first: it left a vial
    assert drink_antifire(state, 200) == 0  # still immune
    state.tick = 100
    assert antifire_cover(state, 1500) == pytest.approx(min((600 + 4 * 600) / 1500, 1.0))


@needs_server
def test_a_shielded_dragon_fight_takes_only_breath_and_antifire_stops_it():
    dragon = next(e for e in enemy_pool() if e.npc.id == GREEN_DRAGON)
    site = dragon.sites[0]
    lost = {}
    for antifire in (0, 3):
        state = at(80)  # Prayer 80: the dragon's melee is flicked away
        state.inventory = {1333: 1, 1127: 1, 1163: 1, 1079: 1, ANTI_DRAGON_SHIELD: 1, SHARK: 20,
                           **({ANTIFIRE_4: antifire} if antifire else {})}
        state.location = site.spawn
        fight(state, np.random.default_rng(0), 1500, dragon, Plan("melee", f.AGGRESSIVE), site, loot_rule("none"))
        lost[antifire] = 20 - state.inventory.get(SHARK, 0)
    assert lost[0] > 0 and lost[3] == 0
    state = at(80)
    state.inventory = {1333: 1, 1127: 1, 1163: 1, 1079: 1, ANTI_DRAGON_SHIELD: 1}
    wield_best(state, "melee", frozenset({ANTI_DRAGON_SHIELD}))
    rates = combat_rates(fighter_for(state), Plan("melee", f.AGGRESSIVE), dragon.npc, 0.0)
    assert rates.damage_taken_per_kill == pytest.approx(rates.breath_per_kill) and rates.breath_per_kill > 0


@needs_server
def test_lower_doses_are_misc_but_stay_consumable_and_counted():
    """OQ-25 (Caleb): only four-dose potions are in V; the lower doses are drunk, kept and counted, never sold off."""
    v = frozenset(vocabulary())
    assert SUPER_STRENGTH_4 in v and SUPER_STRENGTH_3 not in v
    assert not is_misc(SUPER_STRENGTH_3, v) and not is_misc(SUPER_STRENGTH_1, v)  # the misc actions leave them be
    state = at(60)
    state.inventory = {SUPER_STRENGTH_3: 2, SUPER_STRENGTH_4: 1}
    state.bank = {SUPER_STRENGTH_1: 3}
    assert doses_held(state.inventory, "super_strength") == 10 and doses_held(state.bank, "super_strength") == 3
    drink_boosts(state, "melee")
    assert state.inventory[SUPER_STRENGTH_3] == 1  # the emptiest drunk first, a lower dose
