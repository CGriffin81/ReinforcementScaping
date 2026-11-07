"""Poison (the server's Poison timer; rlscape.combat.rates has the rule): a hit every 30 ticks for
floor((severity + 4) / 5), the severity falling by 1 a hit; a poisonous monster's swings poison 4 times in 10, hit or
miss, so a protection prayer stops their damage but not their poison."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat import formulas as f
from rlscape.combat.candidates import enemy_pool, loot_rule
from rlscape.combat.rates import Plan, combat_rates, poison_damage
from rlscape.gamedata import server as gd
from rlscape.sim.combat import die, fight
from rlscape.sim.equipment import fighter_for, wield_best
from rlscape.sim.health import VIAL, advance_poison, apply_poison, poison_cover, regenerate
from rlscape.sim.kits import kit
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
POISON_SPIDER, LOBSTER = 134, 379
SUPER_4, SUPER_3, SUPER_1, ANTI_4 = 2448, 181, 185, 2446


def strong(level: int) -> CharacterState:
    state = CharacterState.fresh()
    for skill in ("attack", "strength", "defence", "hitpoints", "prayer"):
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.hp = level
    state.inventory = {1333: 1, 1127: 1, 1163: 1, 1079: 1, 1201: 1}  # rune
    return state


def test_poison_hits_every_30_ticks_and_weakens():
    state = strong(99)
    apply_poison(state, 30, 0)
    advance_poison(state, 29)
    assert state.hp == 99  # the first hit comes 30 ticks in
    advance_poison(state, 1 + 4 * 30)
    assert state.hp == 99 - 5 * poison_damage(30) and state.poison_severity == 25  # 6 five times
    apply_poison(state, 20, 0)  # weaker than what's running: nothing changes
    assert state.poison_severity == 25
    advance_poison(state, 10_000)
    assert state.poison_severity == 0 and state.hp == 99 - sum(poison_damage(s) for s in range(30, 0, -1))


def test_regeneration_carries_the_poison_and_death_clears_it():
    state = strong(99)
    apply_poison(state, 10, 0)
    regenerate(state, 30)
    assert state.hp == 99 - poison_damage(10) and state.poison_severity == 9
    die(state, 0)
    assert state.poison_severity == 0


@needs_server
def test_a_poisoned_fighter_eats_through_poison_its_prayer_cant_stop():
    spider = next(e for e in enemy_pool() if e.npc.id == POISON_SPIDER)
    assert spider.npc.poisonous and spider.npc.poison_amount == 30
    state = strong(91)
    state.inventory[LOBSTER] = 15
    site = next(s for s in spider.sites if s.spawn == (3089, 9943, 0))  # the calibration case's (Edgeville dungeon)
    state.location = site.spawn
    result = fight(state, np.random.default_rng(0), 1500, spider, Plan("melee", f.AGGRESSIVE), site,
                   loot_rule("none"))
    # Protect from Melee flicks its swings to nothing (rlscape.combat.prayers), but the poison keeps coming
    assert result.termination == "out_of_food" and LOBSTER not in state.inventory and state.poison_severity > 0
    wield_best(state, "melee")
    rates = combat_rates(fighter_for(state), Plan("melee", f.AGGRESSIVE), spider.npc, 0.0)
    assert rates.damage_taken_per_kill == pytest.approx(poison_damage(30) / 30 * rates.ticks_per_kill)


def test_an_antipoison_dose_cures_and_keeps_poison_off_for_its_immunity():
    state = strong(99)
    state.inventory.update({SUPER_4: 1, ANTI_4: 1})
    assert apply_poison(state, 30, 1000) == 2  # drunk at once: the super first, the ticks it takes
    assert state.poison_severity == 0 and state.poison_immune_until == 1600 and state.inventory[SUPER_3] == 1
    assert apply_poison(state, 30, 1599) == 0 and state.poison_severity == 0  # still immune
    state.inventory = {SUPER_1: 1}
    apply_poison(state, 30, 1600)
    assert state.inventory == {VIAL: 1} and state.poison_immune_until == 2200  # the last dose leaves a vial
    state.inventory, state.poison_immune_until = {}, 0
    apply_poison(state, 30, 3000)
    assert state.poison_severity == 30  # no dose: poisoned
    state.inventory = {ANTI_4: 1}
    state.tick = 3000
    advance_poison(state, 10)  # one carried from before is drunk away
    assert state.poison_severity == 0 and state.poison_immune_until == 3150


@needs_server
def test_antipoison_saves_the_food_and_the_ranking_counts_it():
    spider = next(e for e in enemy_pool() if e.npc.id == POISON_SPIDER)
    site = next(s for s in spider.sites if s.spawn == (3089, 9943, 0))
    eaten = {}
    for doses in (0, 3):
        state = strong(91)
        state.inventory.update({LOBSTER: 15, **({SUPER_4: doses} if doses else {})})
        state.location = site.spawn
        fight(state, np.random.default_rng(0), 1500, spider, Plan("melee", f.AGGRESSIVE), site, loot_rule("none"))
        eaten[doses] = 15 - state.inventory.get(LOBSTER, 0)
    assert eaten[3] < eaten[0] / 3  # 12 doses cover 7,200 ticks: Protect from Melee takes the rest
    state = strong(91)
    state.inventory[SUPER_4] = 1
    assert poison_cover(state, 1500) == 1.0  # its 4 doses cover 2,400 ticks
    state.inventory = {SUPER_1: 1}
    assert poison_cover(state, 1500) == pytest.approx(600 / 1500)
    assert kit(state, "combat:melee") == {SUPER_1}  # the deposit keeps it with the fighting kit
