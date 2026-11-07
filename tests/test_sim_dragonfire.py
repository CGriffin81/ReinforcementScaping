"""The anti-dragon shield (Caleb, 2026-11-06: bought on the GE): fights against dragonfire monsters put it on, the
ranking rates those monsters for the character wearing it, the buy is open until one is held, and deposits and the
gear withdrawals keep it with the fighting kit."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat import formulas as f
from rlscape.combat.candidates import (
    ANTI_DRAGON_SHIELD,
    DRAGONFIRE_NPCS,
    DRAGONFIRE_PROTECTION,
    Character,
    enemy_pool,
    evaluate,
    loot_rule,
    select_candidates,
)
from rlscape.combat.ranking import CandidateRanker
from rlscape.combat.rates import Fighter, Plan
from rlscape.gamedata import server as gd
from rlscape.sim.buying import BuyGE, gear_to_withdraw
from rlscape.sim.combat import fight
from rlscape.sim.equipment import SHIELD, wield_best
from rlscape.sim.kits import kit
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
GREEN_DRAGON, RUNE_KITESHIELD, RUNE_SCIMITAR, RUNE_PLATEBODY, MAPLE_SHORTBOW = 941, 1201, 1333, 1127, 853
MELEE_GEAR = (RUNE_SCIMITAR, RUNE_PLATEBODY, 1163, 1079)  # with the rune full helm and platelegs


def strong(level: int = 80) -> CharacterState:
    state = CharacterState.fresh()
    for skill in ("attack", "strength", "defence", "hitpoints", "ranged", "magic"):
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.hp = level
    state.inventory = {item: 1 for item in (*MELEE_GEAR, RUNE_KITESHIELD, ANTI_DRAGON_SHIELD)}
    state.inventory[385] = 20  # sharks
    return state


def bonuses(*items: int) -> tuple[int, ...]:
    return tuple(map(sum, zip(*(gd.items()[i].bonuses for i in items))))


def green_dragons():
    dragon = next(e for e in enemy_pool() if e.npc.id == GREEN_DRAGON)
    return dragon, dragon.sites[0]


@needs_server
def test_wielding_puts_the_anti_dragon_shield_on_only_against_dragonfire():
    state = strong()
    wield_best(state, "melee")
    assert state.equipment[SHIELD] == RUNE_KITESHIELD  # the most defence
    wield_best(state, "melee", DRAGONFIRE_PROTECTION)
    assert state.equipment[SHIELD] == ANTI_DRAGON_SHIELD and RUNE_KITESHIELD in state.inventory


@needs_server
def test_a_carried_shield_makes_dragons_candidates_rated_wearing_it():
    dragon, _ = green_dragons()
    level, food = 80, 20 * 20
    plain = Fighter(level, level, level, level, 1, 1, bonuses(*MELEE_GEAR, RUNE_KITESHIELD), 4)
    shielded = Fighter(level, level, level, level, 1, 1, bonuses(*MELEE_GEAR, ANTI_DRAGON_SHIELD), 4)
    character = Character(dragon.sites[0].spawn, level, level, food, 20, RUNE_KITESHIELD, "valuable")
    plan, loot = Plan("melee", f.AGGRESSIVE), loot_rule("valuable")
    assert evaluate(dragon, plain, plan, character, 1500, loot) is None  # no dragonfire protection worn
    candidate = evaluate(dragon, shielded, plan, character, 1500, loot, ANTI_DRAGON_SHIELD)
    assert candidate is not None and candidate.gp_per_hour > 0
    plans = {"melee": (plain, [plan])}
    for dragonfire in (None, {"melee": shielded}):
        fast = CandidateRanker(enemy_pool()).select(plans, character, 1500, k=20, dragonfire=dragonfire)["melee"]
        reference = select_candidates(enemy_pool(), plans, character, 1500, k=20, dragonfire=dragonfire)["melee"]
        assert [(c.entry.npc.id, round(c.gp_per_hour, 6)) for c in fast] == [
            (c.entry.npc.id, round(c.gp_per_hour, 6)) for c in reference]
        assert any(c.entry.npc.id in DRAGONFIRE_NPCS for c in reference) == (dragonfire is not None)


@needs_server
def test_a_fight_against_green_dragons_wears_the_anti_dragon_shield():
    dragon, site = green_dragons()
    state = strong()
    state.location = site.spawn
    fight(state, np.random.default_rng(0), 300, dragon, Plan("melee", f.AGGRESSIVE), site, loot_rule("valuable"))
    assert state.equipment[SHIELD] == ANTI_DRAGON_SHIELD


@needs_server
def test_the_shield_is_bought_until_one_is_held():
    state = CharacterState.fresh()
    state.inventory = {COINS: 1_000}
    assert BuyGE(ANTI_DRAGON_SHIELD).available(state)  # no requirements to wear; the starter's wooden shield is no rival
    state.bank[ANTI_DRAGON_SHIELD] = 1
    assert not BuyGE(ANTI_DRAGON_SHIELD).available(state)


@needs_server
def test_deposits_and_gear_withdrawals_keep_the_shield_with_the_fighting_kit():
    state = strong()
    assert ANTI_DRAGON_SHIELD in kit(state, "combat:melee")
    state.inventory = {MAPLE_SHORTBOW: 1, ANTI_DRAGON_SHIELD: 1, 890: 100}  # adamant arrows
    assert ANTI_DRAGON_SHIELD not in kit(state, "combat:ranged")  # the shortbow is two-handed
    state = strong()
    del state.inventory[ANTI_DRAGON_SHIELD]
    state.bank[ANTI_DRAGON_SHIELD] = 1
    assert ANTI_DRAGON_SHIELD in gear_to_withdraw(state, "melee")
    state.inventory[ANTI_DRAGON_SHIELD] = 1
    assert ANTI_DRAGON_SHIELD not in gear_to_withdraw(state, "melee")  # one is carried

