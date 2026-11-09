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
    pickups_per_kill,
    loot_rule,
    travel_ticks,
)
from rlscape.combat.rates import Fighter, Plan, Rates, combat_rates
from rlscape.gamedata import server as gd
from rlscape.travel import overhead, path

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
    steps = path((3200, 3200, 0), (3215, 3200, 0))[0]  # the planned walk (rlscape.travel)
    assert travel_ticks((3200, 3200, 0), (3215, 3200, 0)) == pytest.approx(steps / 1.5 + overhead(steps))
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
    # a pickup a drop, whatever its amount (rates.with_pickups times them)
    assert pickups_per_kill(cow_drops, loot_rule("all")) == pytest.approx(3, abs=0.1)  # and, rarely, a stackable
    assert pickups_per_kill(cow_drops, loot_rule("valuable")) == pytest.approx(1, abs=0.1)
    assert pickups_per_kill(cow_drops, loot_rule("none")) == 0.0


@needs_data
def test_pool_drops_unattackable_placeholder_and_unkillable_npcs():
    names = {e.npc.name for e in enemy_pool()}
    ids = {e.npc.id for e in enemy_pool()}
    assert "Cow" in names
    assert "Master Farmer" not in names  # no "Attack" option in the cache
    assert 1935 not in ids  # Ice troll with placeholder stats
    assert not any("dummy" in n.lower() for n in names)


@needs_data
def test_hazards_are_never_targets_there_but_still_aggressors():
    """Taverley dungeon's Black Knights east of the lesser demons, the moss giants west of the Fishing Guild and the
    Abandoned Mine's animated spades: no site there, though the monsters' other sites stay; and the aggression model
    still counts them by a site near them."""
    from rlscape.sim.aggression import site_aggressors

    knights = next(e for e in enemy_pool() if e.npc.id == 178)
    spawns = {s.spawn for s in knights.sites}
    assert (2895, 9710, 0) in spawns and not any(9796 <= y <= 9815 for _, y, _ in spawns)
    assert sum(a.npc.id == 178 for a in site_aggressors((2940, 9806, 0))) == 2
    giants = next(e for e in enemy_pool() if e.npc.id == 112)  # west of the Fishing Guild (Caleb, 2026-11-06)
    spawns = {s.spawn for s in giants.sites}
    assert (2825, 3249, 0) in spawns and not any(2545 <= x <= 2566 and 3394 <= y <= 3417 for x, y, _ in spawns)
    spades = next(e for e in enemy_pool() if e.npc.id == 5414)  # the Abandoned Mine's (Caleb, 2026-11-08, OQ-42)
    assert [s.spawn for s in spades.sites] == [(3182, 5447, 0)]  # the Chaos Tunnels' stay
    pickaxes = next(e for e in enemy_pool() if e.npc.id == 5413)
    assert (3423, 9658, 0) in {s.spawn for s in pickaxes.sites}  # beside the mine's spades: still a target


@needs_data
def test_the_yanille_dungeon_is_out_of_the_project():
    """Caleb, 2026-11-06: no monster in the Yanille Agility Dungeon is a target; the same monsters elsewhere are."""
    inside = [(e.npc.name, s.spawn) for e in enemy_pool() for s in e.sites
              if 2544 <= s.spawn[0] <= 2631 and 9481 <= s.spawn[1] <= 9587 and s.spawn[2] == 0]
    assert inside == []
    druids = next(e for e in enemy_pool() if e.npc.id == 2547)
    assert [s.spawn for s in druids.sites] == [(3116, 9926, 0)]  # Edgeville dungeon's
    assert not any(e.npc.id == 205 for e in enemy_pool())  # Salarin the Twisted spawns only there


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
