"""The vectorised combat-rate model gives the scalar model's numbers (rlscape.combat.vector_rates; Caleb, OQ-7 (a))."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat import formulas as f
from rlscape.combat.candidates import enemy_pool
from rlscape.combat.prayers import Flicks
from rlscape.combat.rates import Fighter, Plan, combat_rates
from rlscape.combat.vector_rates import NpcArrays, vector_rates
from rlscape.gamedata import server as gd

needs_data = pytest.mark.skipif(not (gd.SERVER_CONFIGS.exists() and gd.NPC_DEFINITIONS.exists()),
                                reason="server submodule or data/npc_definitions.csv missing")

FLICKING = Flicks(attack=0.15, strength=0.15, defence=0.15, ranged=0.15, magic=0.15,
                  protects=frozenset({"melee", "ranged", "magic"}))
SOME = Flicks(attack=0.05, strength=0.05, defence=0.05, ranged=0.05, magic=0.05, protects=frozenset({"melee"}))


def fighters():
    items = gd.items()
    starter = tuple(map(sum, zip(*(items[i].bonuses for i in (1277, 1171)))))  # bronze sword, wooden shield
    rune = tuple(map(sum, zip(*(items[i].bonuses for i in (1333, 1201, 1127, 1079, 1163)))))
    caster = tuple(map(sum, zip(*(items[i].bonuses for i in (1387, 4089, 4091, 4093)))))  # staff of fire, mystic
    yield Fighter(1, 1, 1, 10, 1, 1, starter, 4)
    yield Fighter(30, 25, 20, 30, 1, 1, starter, 4, SOME)
    yield Fighter(61, 61, 61, 61, 61, 61, rune, 4, FLICKING)
    yield Fighter(99, 99, 99, 99, 99, 99, rune, 5)
    yield Fighter(40, 40, 40, 40, 40, 75, caster, 5, FLICKING)


PLANS = [Plan("melee", s) for s in (f.ACCURATE, f.AGGRESSIVE, f.DEFENSIVE, f.CONTROLLED)] + \
        [Plan("ranged", s) for s in (f.ACCURATE, f.RAPID, f.LONGRANGE)] + \
        [Plan("magic", s) for s in ("wind_strike", "fire_bolt", "fire_wave")]


def scalar_columns(fighter: Fighter, plan: Plan, npcs) -> dict[str, np.ndarray]:
    """What the fast ranker took from the scalar model before (ranking._columns)."""
    nan = float("nan")
    rates = [combat_rates(fighter, plan, npc, 0.0) for npc in npcs]
    col = lambda get: np.array([get(r) if r is not None else nan for r in rates])  # noqa: E731
    return {"kills_per_hour": col(lambda r: r.kills_per_hour), "xp_per_hour": col(lambda r: sum(r.xp_per_hour.values())),
            "ticks_per_kill": col(lambda r: r.ticks_per_kill), "damage_per_kill": col(lambda r: r.damage_taken_per_kill),
            "damage_per_hour": col(lambda r: r.damage_taken_per_hour), "poison_per_kill": col(lambda r: r.poison_per_kill),
            "breath_per_kill": col(lambda r: r.breath_per_kill),
            "damage_sd_per_kill": col(lambda r: np.sqrt(r.damage_taken_variance_per_kill)),
            "npc_max_hit": col(lambda r: r.npc_max_hit), "attacks_per_kill": col(lambda r: r.attacks_per_kill)}


@needs_data
@pytest.mark.parametrize("plan", PLANS, ids=lambda p: f"{p.combat_class}-{p.style}")
def test_the_vectorised_rates_are_the_scalar_models_for_every_monster(plan):
    npcs = [e.npc for e in enemy_pool()]
    arrays = NpcArrays(npcs)
    for fighter in fighters():
        vector = vector_rates(fighter, plan, arrays)
        for name, expected in scalar_columns(fighter, plan, npcs).items():
            # to the last bit, None (NaN) in the same places: the fast ranker's ties break as the reference's
            np.testing.assert_array_equal(getattr(vector, name), expected, err_msg=f"{fighter} {plan} {name}")
