"""Tests for the combat candidate pipeline: retreat-aware filter, travel, loot, pool cleaning and the gear check."""

from __future__ import annotations

import pytest

from rlscape.combat import formulas as f
from rlscape.combat.candidates import (
    ANTI_DRAGON_SHIELD,
    Character,
    enemy_pool,
    evaluate,
    loot_per_kill,
    loot_rule,
    travel_ticks,
)
from rlscape.combat.rates import Fighter, Plan, Rates, combat_rates
from rlscape.gamedata import server as gd

needs_data = pytest.mark.skipif(not (gd.SERVER_CONFIGS.exists() and gd.NPC_DEFINITIONS.exists()),
                                reason="server submodule or data/npc_definitions.csv missing")


def rates_with(npc_max_hit: int, damage_per_kill: float, variance_per_kill: float) -> Rates:
    return Rates(kills_per_hour=1, xp_per_hour={}, gp_per_hour=0, damage_taken_per_hour=0,
                 damage_taken_variance_per_hour=0, hit_chance=0.5, max_hit=1, npc_hit_chance=0.5,
                 npc_max_hit=npc_max_hit, ticks_per_kill=10, damage_taken_per_kill=damage_per_kill,
                 damage_taken_variance_per_kill=variance_per_kill, attacks_per_kill=5)


def test_retreat_filter_rejects_a_burst_from_half_hp():
    # max HP 10 -> retreat at 5; two max hits of 3 reach 6 >= 5
    assert not rates_with(3, 0.1, 0.0).passes_retreat_filter(max_hp=10, current_hp=10, food_healing=100)
    assert rates_with(2, 0.1, 0.0).passes_retreat_filter(max_hp=10, current_hp=10, food_healing=100)


def test_retreat_filter_needs_one_affordable_kill():
    # budget = (10 - 5) + 8 = 13; mean 9 + 2 * sqrt(4) = 13 passes, mean 10 doesn't
    assert rates_with(1, 9, 4).passes_retreat_filter(max_hp=10, current_hp=10, food_healing=8)
    assert not rates_with(1, 10, 4).passes_retreat_filter(max_hp=10, current_hp=10, food_healing=8)


def test_travel_counts_plane_and_underground_changes():
    assert travel_ticks((3200, 3200, 0), (3215, 3200, 0)) == pytest.approx(15 * 1.3 / 1.5)
    surface_to_dungeon = travel_ticks((3100, 3500, 0), (3100, 3500 + 6400, 0))
    assert surface_to_dungeon == pytest.approx(12)  # same column, one level change


@needs_data
def test_loot_rule_keeps_stackables_and_valuables_only_when_asked():
    cow_drops = gd.drop_tables()[81]  # bones 75, cowhide 116, raw beef 59 at prices_v2
    gp_all, slots_all = loot_per_kill(cow_drops, loot_rule("all"))
    gp_valuable, slots_valuable = loot_per_kill(cow_drops, loot_rule("valuable"))
    assert slots_all == pytest.approx(3) and slots_valuable == pytest.approx(1)  # only the 116 gp hide is >= 100
    assert gp_valuable == pytest.approx(gd.item_values()[1739])
    assert loot_per_kill(cow_drops, loot_rule("none")) == (0.0, 0.0)


@needs_data
def test_pool_drops_unattackable_placeholder_and_unkillable_npcs():
    names = {e.npc.name for e in enemy_pool()}
    ids = {e.npc.id for e in enemy_pool()}
    assert "Cow" in names
    assert "Master Farmer" not in names  # no "Attack" option in the cache
    assert 1935 not in ids  # Ice troll with placeholder stats
    assert not any("dummy" in n.lower() for n in names)


@needs_data
def test_dragons_need_the_anti_dragon_shield():
    green = next(e for e in enemy_pool() if e.npc.id == 941)
    strong = Fighter(99, 99, 99, 99, 1, 1, gd.items()[1333].bonuses, 4)
    plan = Plan("melee", f.AGGRESSIVE)
    loot = loot_rule("valuable")
    unshielded = Character((3100, 3500, 0), 99, 99, 1000, 20, shield_id=1201)
    shielded = Character((3100, 3500, 0), 99, 99, 1000, 20, shield_id=ANTI_DRAGON_SHIELD)
    assert evaluate(green, strong, plan, unshielded, 1500, loot) is None
    assert evaluate(green, strong, plan, shielded, 1500, loot) is not None


@needs_data
def test_fresh_character_can_fight_cows_under_the_retreat_aware_filter():
    starter = tuple(map(sum, zip(gd.items()[1277].bonuses, gd.items()[1171].bonuses)))
    fresh = Fighter(1, 1, 1, 10, 1, 1, starter, 4)
    cow = gd.npcs()[81]
    rates = combat_rates(fresh, Plan("melee", f.AGGRESSIVE), cow, gp_per_kill=0)
    assert rates.passes_retreat_filter(max_hp=10, current_hp=10, food_healing=8)
