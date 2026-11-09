"""Tests for sim v0's ranged and magic fights: the server data they come from, ranged kits and worn stacks, arrows
used and recovered, runes per cast, and the spell's base XP."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat import formulas as f
from rlscape.combat.candidates import enemy_pool, loot_rule
from rlscape.combat.rates import Plan
from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.combat import (
    _ammunition,
    arrow_land_chance,
    best_spell,
    casts_held,
    die,
    fight,
)
from rlscape.sim.equipment import AMMO, WEAPON, fighter_for, ranged_kits, wield_best
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
SHORTBOW, BRONZE_ARROW, IRON_ARROW, BRONZE_DART = 841, 882, 884, 806
AIR, WATER, EARTH, FIRE, MIND = 556, 555, 557, 554, 558
STAFF_OF_FIRE, BRONZE_SWORD, WOODEN_SHIELD = 1387, 1277, 1171


def with_levels(state: CharacterState, level: int, *skills: str) -> CharacterState:
    for skill in skills:
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.hp = state.max_hp()
    return state


def cows():
    cow = next(e for e in enemy_pool() if e.npc.id == 81)
    return cow, min(cow.sites, key=lambda s: abs(s.spawn[0] - 3255) + abs(s.spawn[1] - 3255))


@needs_server
def test_spells_staves_and_ranged_weapons_come_from_the_server():
    spells = gd.combat_spells()
    assert {name: (s.level, s.experience) for name, s in spells.items()} == \
           {name: (level, xp) for name, (level, xp, _, _) in f.SPELLS.items()}
    assert spells["wind_strike"].runes == {MIND: 1, AIR: 1}
    assert spells["fire_strike"].runes == {MIND: 1, FIRE: 3, AIR: 2}
    # their spellbook buttons (SpellBook.MODERN.register's first argument), which a cast on an NPC sends
    assert {name: s.button for name, s in spells.items() if name.startswith("wind_") or name == "fire_wave"} == \
           {"wind_strike": 1, "wind_bolt": 10, "wind_blast": 24, "wind_wave": 45, "fire_wave": 55}
    assert len({s.button for s in spells.values()}) == len(spells)
    assert STAFF_OF_FIRE in gd.staff_runes()[FIRE] and 1381 in gd.staff_runes()[AIR]  # staff of air
    weapons = gd.ranged_weapons()
    assert BRONZE_ARROW in weapons[SHORTBOW].ammunition and weapons[SHORTBOW].ammo_slot == AMMO
    assert weapons[BRONZE_DART].ammunition == (BRONZE_DART,) and weapons[BRONZE_DART].ammo_slot == WEAPON
    assert not weapons[4214].drop_ammo  # the crystal bow's "0" is false, as Kotlin's toBoolean reads it


def test_arrows_land_more_often_at_higher_levels():
    assert arrow_land_chance(1) == pytest.approx(4 / 5)
    assert arrow_land_chance(20) == pytest.approx(5 / 6)
    assert arrow_land_chance(99) == pytest.approx(8 / 9)


@needs_server
def test_the_best_kit_is_worn_whole_and_stacks_top_up():
    state = CharacterState.fresh()
    state.inventory[IRON_ARROW] = 10
    assert (SHORTBOW, IRON_ARROW) in ranged_kits(state)
    worth = state.net_worth()
    wield_best(state, "ranged")
    assert state.equipment[AMMO] == IRON_ARROW and state.worn(AMMO) == 10  # iron arrows hit harder
    assert state.net_worth() == pytest.approx(worth)  # a worn stack still counts in full
    darts = CharacterState.fresh()
    darts.inventory = {BRONZE_DART: 5}
    darts.equipment, darts.worn_amounts = {WEAPON: BRONZE_DART}, {WEAPON: 10}
    wield_best(darts, "ranged")
    assert darts.worn(WEAPON) == 15 and BRONZE_DART not in darts.inventory  # thrown: the weapon is its own stack
    darts.equipment[AMMO], darts.worn_amounts[AMMO] = BRONZE_ARROW, 20
    assert fighter_for(darts).bonuses[gd.RANGED_STRENGTH] == gd.items()[BRONZE_DART].bonuses[gd.RANGED_STRENGTH]


@needs_server
def test_a_two_handed_weapon_is_not_wielded_without_room_for_what_comes_off():
    state = CharacterState.fresh()
    wield_best(state, "melee")  # sword and shield on
    state.inventory = {SHORTBOW: 1, BRONZE_ARROW: 25, **{1511 + i: 1 for i in range(26)}}  # 28 slots used
    before = (dict(state.equipment), dict(state.inventory))
    wield_best(state, "ranged")
    assert (state.equipment, state.inventory) == before  # nothing goes on, and nothing is lost


@needs_server
def test_shots_that_land_come_back_only_when_the_loot_mode_takes_arrows():
    state = CharacterState.fresh()
    state.inventory[BRONZE_ARROW] = 10_000
    wield_best(state, "ranged")
    plan, rng = Plan("ranged", f.RAPID), np.random.default_rng(0)
    possible, pay, _ = _ammunition(state, plan, 20_000, rng, loot_rule("valuable"))
    assert possible == 20_000
    pay(possible)
    assert 10_025 - state.worn(AMMO) == pytest.approx(20_000 / 5, rel=0.05)  # 1 in 5 breaks at level 1
    possible, pay, _ = _ammunition(state, plan, 20_000, rng, loot_rule("none"))
    stack = state.worn(AMMO)
    assert possible == stack  # every shot is gone
    pay(possible)
    assert AMMO not in state.equipment


@needs_server
def test_a_ranged_fight_ends_out_of_ammo_and_trains_ranged():
    cow, site = cows()
    state = with_levels(CharacterState.fresh(), 20, "hitpoints")
    state.inventory[BRONZE_ARROW] = 5
    result = fight(state, np.random.default_rng(1), 1500, cow, Plan("ranged", f.RAPID), site, loot_rule("none"))
    assert result.termination == "out_of_ammo" and AMMO not in state.equipment and result.detail["style"] == "rapid"
    ranged_xp = state.xp[SKILL_INDEX["ranged"]]
    damage = ranged_xp / 4
    max_hit = f.player_ranged_max_hit(1, f.RAPID, gd.items()[BRONZE_ARROW].bonuses[gd.RANGED_STRENGTH])
    assert damage <= 5 * max_hit  # 5 shots at most
    assert state.xp[SKILL_INDEX["hitpoints"]] == pytest.approx(XP_FOR_LEVEL[20] + 1.33 * damage)


@needs_server
def test_spell_choice_follows_level_runes_and_staff():
    state = CharacterState.fresh()
    assert best_spell(state) == "wind_strike" and casts_held(state, "wind_strike") == 15  # 15 mind runes
    with_levels(state, 13, "magic")
    assert best_spell(state) == "earth_strike"  # 4 earth runes: fire strike needs fire runes
    state.equipment[WEAPON] = STAFF_OF_FIRE
    assert best_spell(state) == "fire_strike" and casts_held(state, "fire_strike") == 12  # 25 air / 2 a cast
    state.inventory.pop(MIND)
    assert best_spell(state) is None


@needs_server
def test_a_magic_fight_pays_runes_per_cast_and_gives_base_xp_on_every_cast():
    cow, site = cows()
    state = with_levels(CharacterState.fresh(), 40, "hitpoints")
    state.inventory[2309] = 10  # bread (it doesn't stack: 27 slots used): no retreat before the runes run out
    result = fight(state, np.random.default_rng(2), 1500, cow, Plan("magic", "wind_strike"), site, loot_rule("none"))
    assert result.termination == "out_of_ammo" and MIND not in state.inventory and state.inventory[AIR] == 10
    damage = (state.xp[SKILL_INDEX["hitpoints"]] - XP_FOR_LEVEL[40]) / 1.33
    assert state.xp[SKILL_INDEX["magic"]] == pytest.approx(15 * 5.5 + 4 * damage)  # 15 casts, hit or splash


@needs_server
def test_death_puts_a_worn_stack_in_the_gravestone():
    state = CharacterState.fresh()
    wield_best(state, "ranged")
    state.location = (3255, 3255, 0)
    die(state, now=0)
    assert state.gravestone.items.get(BRONZE_ARROW) == 25 and state.worn_amounts == {}


@needs_server
def test_ranged_and_magic_slots_fight_from_the_simulator():
    sim = Simulator(build_catalog())
    ids = [o.id for o in sim.options]
    sim.reset(seed=5)
    info = sim.step(ids.index("fight_ranged_xp1")).info
    assert info["option"]["style"] in (f.ACCURATE, f.RAPID, f.LONGRANGE) and "ranged" in info["xp_gained"]
    assert not {"attack", "strength", "magic"} & set(info["xp_gained"])
    sim.reset(seed=5)
    info = sim.step(ids.index("fight_magic_gp1")).info
    assert info["option"]["style"] == "wind_strike" and info["xp_gained"]["magic"] >= 5.5
