"""Unit tests for the combat formulas and rate model, against values worked out by hand from the server code."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat import formulas as f
from rlscape.combat.rates import OVERHEAD_TICKS_PER_KILL, Fighter, Plan, combat_rates
from rlscape.gamedata.server import Npc

BRONZE_SWORD = (4, 3, -2, 0, 0, 0, 2, 1, 0, 0, 0, 5, 0, 0, 0)
WOODEN_SHIELD = (0, 0, 0, 0, 0, 4, 5, 3, 1, 4, 0, 0, 0, 0, 0)
STARTER_MELEE = tuple(a + b for a, b in zip(BRONZE_SWORD, WOODEN_SHIELD))
COW = Npc(id=81, name="Cow", hitpoints=8, attack=1, strength=1, defence=1, ranged=1, magic=1, bonuses=(0,) * 15,
          attack_speed=5, combat_style="melee", protect_style=None, aggressive=False, poisonous=False)


def test_hit_chance_both_branches():
    assert f.hit_chance(1000, 500) == pytest.approx(1 - 502 / 2002)
    assert f.hit_chance(500, 1000) == pytest.approx(500 / 2002)


def test_player_melee_rolls_and_max_hits():
    assert f.player_melee_attack_roll(1, f.ACCURATE, 4) == (1 + 3 + 8) * (4 + 64)
    assert f.player_melee_max_hit(1, f.AGGRESSIVE, 5) == 1
    assert f.player_melee_max_hit(99, f.AGGRESSIVE, 0) == 11  # known: 99 Strength, no bonus
    assert f.player_melee_max_hit(99, f.AGGRESSIVE, 44) == 19  # known: 99 Strength, rune scimitar


def test_npc_rolls_and_max_hits():
    assert f.npc_defence_roll(1, 0) == 640
    assert f.npc_attack_roll(1, 0) == 640
    assert f.npc_max_hit(1, 0) == 1
    assert f.npc_magic_max_hit(1, 0) == 2


def test_spell_max_hits_follow_spell_type():
    assert [f.spell_max_hit(s) for s in ("wind_strike", "fire_strike", "wind_bolt", "fire_bolt", "fire_blast", "fire_wave")] \
        == [2, 8, 9, 12, 16, 20]


def test_damage_moments_uniform_after_hit():
    mean, variance = f.damage_moments(0.5, 2)
    assert mean == pytest.approx(0.5)
    assert variance == pytest.approx(0.5 * (2 * 5 / 6) - 0.25)


def test_fresh_character_against_a_cow():
    fresh = Fighter(attack=1, strength=1, defence=1, hitpoints=10, ranged=1, magic=1, bonuses=STARTER_MELEE)
    rates = combat_rates(fresh, Plan("melee", f.AGGRESSIVE), COW, gp_per_kill=250)
    # attack roll (1+0+8)*(4+64) = 612 vs cow defence (1+9)*64 = 640 -> 612 / 1282
    assert rates.hit_chance == pytest.approx(612 / 1282)
    assert rates.max_hit == 1
    ticks_fighting = 8 / (612 / 1282 * 0.5 / 4)
    assert rates.ticks_per_kill == pytest.approx(ticks_fighting + OVERHEAD_TICKS_PER_KILL["melee"])
    assert rates.kills_per_hour == pytest.approx(6000 / (ticks_fighting + OVERHEAD_TICKS_PER_KILL["melee"]))
    assert rates.xp_per_hour["strength"] == pytest.approx(4 * 8 * rates.kills_per_hour)
    assert rates.gp_per_hour == pytest.approx(250 * rates.kills_per_hour)
    # cow attack 640 vs player defence (1+0+8)*(4+64) = 612 -> 1 - 614/1282
    assert rates.npc_hit_chance == pytest.approx(1 - 614 / 1282)


def test_immune_npc_yields_no_rates():
    ghost_like = Npc(**{**COW.__dict__, "protect_style": "melee"})
    fresh = Fighter(attack=1, strength=1, defence=1, hitpoints=10, ranged=1, magic=1, bonuses=STARTER_MELEE)
    assert combat_rates(fresh, Plan("melee", f.ACCURATE), ghost_like, gp_per_kill=0) is None


@pytest.mark.parametrize("hitpoints,chance,max_hit,flicked", [
    (2, 0.9, 15, None),  # a one-hit kill, mostly: HP / damage a tick said a quarter of a swing
    (8, 0.9, 15, None),
    (45, 0.75, 20, None),
    (250, 0.8, 40, None),
    (8, 0.9, 13, (0.95, 15, (4, 6))),  # flicked swings in their pattern (4-tick weapon, 6-tick monster)
    (100, 0.6, 25, (0.66, 28, (5, 4))),
])
def test_the_kill_time_counts_the_last_hits_overkill_as_the_sims_kills_do(hitpoints, chance, max_hit, flicked):
    """Caleb, 2026-11-07: the expected swings to a kill (rates.swings_to_kill) against the sim's kill_sequence, sampled."""
    from rlscape.combat.prayers import boosted_swings
    from rlscape.combat.rates import swings_to_kill
    from rlscape.sim.combat import kill_sequence

    rng = np.random.default_rng(0)
    boosted = None if flicked is None else (flicked[0], flicked[1], boosted_swings(*flicked[2]))
    sampled = np.mean([len(kill_sequence(hitpoints, chance, max_hit, rng, boosted)) for _ in range(20_000)])
    if boosted is None:
        kinds = ((1.0, chance, max_hit),)
    else:
        share = sum(boosted[2]) / len(boosted[2])
        kinds = ((share, boosted[0], boosted[1]), (1 - share, chance, max_hit))
    assert swings_to_kill(hitpoints, kinds) == pytest.approx(sampled, rel=0.015)
