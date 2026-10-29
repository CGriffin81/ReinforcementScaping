"""Tests for sim v0's combat: drops, kill sampling, gear, fights, death and the gravestone."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat import formulas as f
from rlscape.combat.access import Progress
from rlscape.combat.candidates import enemy_pool, loot_rule
from rlscape.combat.rates import Plan, combat_rates, player_offence
from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.combat import (
    GRAVESTONE_TICKS,
    RESPAWN,
    ReclaimGravestone,
    die,
    fight,
    in_wilderness,
    kill_sequence,
    roll_drops,
)
from rlscape.sim.equipment import fighter_for, wield_best
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
COWHIDE, BONES, RUNE_SCIMITAR, RUNE_PLATEBODY, BRONZE_SWORD, WOODEN_SHIELD = 1739, 526, 1333, 1127, 1277, 1171


def with_levels(state: CharacterState, level: int, *skills: str) -> CharacterState:
    for skill in skills:
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


def cows():
    cow = next(e for e in enemy_pool() if e.npc.id == 81)
    return cow, min(cow.sites, key=lambda s: abs(s.spawn[0] - 3255) + abs(s.spawn[1] - 3255))


@needs_server
def test_drops_follow_the_table_and_skip_placeholders():
    rng = np.random.default_rng(0)
    cow_items = {item for item, _ in roll_drops(gd.drop_tables()[81], rng)}
    assert {BONES, COWHIDE} <= cow_items
    with_rdt = next(t for t in gd.drop_tables().values() if any(e.item_id == 31 for e in t.main))
    seen = {item for _ in range(2000) for item, _ in roll_drops(with_rdt, rng)}
    assert not seen & gd.SPECIAL_DROP_SLOTS
    ranged = next(e for t in gd.drop_tables().values() for e in t.main if e.max_amount > e.min_amount + 1)
    table = gd.DropTable(guaranteed=[ranged])
    amounts = {amount for _ in range(3000) for _, amount in roll_drops(table, rng)}
    assert min(amounts) == ranged.min_amount and max(amounts) == ranged.max_amount - 1  # random(min, max) excludes max


@needs_server
def test_sampled_kills_take_as_long_as_the_rate_model_says():
    cow, _ = cows()
    state = CharacterState.fresh()
    wield_best(state, "melee")
    plan = Plan("melee", f.AGGRESSIVE)
    fighter = fighter_for(state)
    chance, max_hit, speed, _, _ = player_offence(fighter, plan, cow.npc)
    rng = np.random.default_rng(1)
    sampled = np.mean([len(kill_sequence(cow.npc.hitpoints, chance, max_hit, rng)) * speed for _ in range(3000)])
    model = combat_rates(fighter, plan, cow.npc, 0).ticks_per_kill - 6  # without the per-kill overhead
    assert sampled == pytest.approx(model, rel=0.03)


@needs_server
def test_wielding_picks_the_best_wearable_gear():
    state = CharacterState.fresh()
    wield_best(state, "melee")
    assert state.equipment == {3: BRONZE_SWORD, 5: WOODEN_SHIELD}  # the sword beats the slower axe
    state = with_levels(CharacterState.fresh(), 40, "attack", "defence")
    state.inventory.update({RUNE_SCIMITAR: 1, RUNE_PLATEBODY: 1})
    wield_best(state, "melee")
    assert state.equipment[3] == RUNE_SCIMITAR and 4 not in state.equipment  # the platebody needs Dragon Slayer
    state.progress = Progress(quests_complete=frozenset({"DRAGON_SLAYER"}))
    wield_best(state, "melee")
    assert state.equipment[4] == RUNE_PLATEBODY
    ranged = CharacterState.fresh()
    wield_best(ranged, "ranged")
    assert ranged.equipment == {3: 841, 13: 882}  # the shortbow (two-handed: no shield) and bronze arrows
    assert ranged.worn(13) == 25 and 882 not in ranged.inventory


@needs_server
def test_a_trained_fighter_fills_the_inventory_with_hides():
    cow, site = cows()
    state = with_levels(CharacterState.fresh(), 30, "attack", "strength", "defence", "hitpoints")
    state.hp = 30
    result = fight(state, np.random.default_rng(2), 1500, cow, Plan("melee", f.AGGRESSIVE), site, loot_rule("valuable"))
    kills = state.inventory[COWHIDE]  # the valuable loot mode keeps the hide only
    assert result.termination == "inventory_full" and BONES not in state.inventory
    assert state.xp[SKILL_INDEX["strength"]] == XP_FOR_LEVEL[30] + 4 * 8 * kills
    assert state.xp[SKILL_INDEX["hitpoints"]] == pytest.approx(XP_FOR_LEVEL[30] + 1.33 * 8 * kills)


@needs_server
def test_a_fresh_character_runs_out_of_food_and_never_dies_on_cows():
    cow, site = cows()
    for seed in range(50):
        state = CharacterState.fresh()
        result = fight(state, np.random.default_rng(seed), 1500, cow, Plan("melee", f.AGGRESSIVE), site,
                       loot_rule("valuable"))
        assert result.termination == "out_of_food" and state.hp > 0 and result.ticks > 30  # time fought is charged


def test_wilderness_borders():
    assert in_wilderness((3100, 3600, 0)) and in_wilderness((3100, 9950, 0))
    assert not in_wilderness((3222, 3218, 0)) and not in_wilderness((3100, 3500, 0))


@needs_server
def test_death_keeps_three_items_and_leaves_a_gravestone():
    state = CharacterState.fresh()
    state.inventory = {RUNE_SCIMITAR: 1, 1079: 1, 1163: 1, 1201: 1, 995: 500, 1511: 5}
    state.location, state.hp = (3255, 3255, 0), 0
    alch = gd.alchemy_values()
    top3 = sorted([RUNE_SCIMITAR, 1079, 1163, 1201], key=lambda i: alch[i][0], reverse=True)[:3]
    die(state, now=1000)
    assert set(state.inventory) == set(top3)  # the three highest high-alchemy values among the gear
    grave = state.gravestone
    assert grave.tile == (3255, 3255, 0) and grave.expires_at == 1000 + GRAVESTONE_TICKS
    lost = ({RUNE_SCIMITAR, 1079, 1163, 1201} - set(top3)).pop()
    assert grave.items == {lost: 1, 995: 500, 1511: 5}
    assert state.location == RESPAWN and state.hp == state.max_hp()


@needs_server
def test_death_in_the_wilderness_leaves_nothing_to_reclaim():
    state = CharacterState.fresh()
    state.location = (3100, 3600, 0)
    die(state, now=0)
    assert state.gravestone is None


@needs_server
def test_reclaiming_needs_the_walk_to_beat_the_timer():
    sim = Simulator(build_catalog())
    sim.reset(seed=0)
    state = sim.state
    state.inventory = {RUNE_SCIMITAR: 1, 1079: 1, 1201: 1, 1163: 1}
    state.location = (3240, 3240, 0)  # near the respawn point
    die(state, now=state.tick)
    option = ReclaimGravestone()
    assert option.available(state)
    option.run(state, np.random.default_rng(3), 1500)
    assert state.inventory.get(1163) == 1 and state.gravestone is None
    die(state, now=state.tick)
    state.location = (2850, 3430, 0)  # Catherby: far too far to make it in 200 ticks
    assert not option.available(state)
