"""The fast candidate ranker must give exactly the reference ranking (candidates.select_candidates)."""

from __future__ import annotations

import warnings
from math import inf

import pytest

from rlscape.combat import formulas as f
from rlscape.combat.candidates import Character, enemy_pool, select_candidates
from rlscape.combat.ranking import CandidateRanker
from rlscape.combat.rates import Fighter, Plan
from rlscape.gamedata import server as gd

needs_data = pytest.mark.skipif(not (gd.SERVER_CONFIGS.exists() and gd.NPC_DEFINITIONS.exists()),
                                reason="server submodule or data/npc_definitions.csv missing")


def plans_for(level: int, bonuses: tuple[int, ...]) -> dict:
    fighter = Fighter(level, level, level, max(10, level), level, level, bonuses, 4)
    return {"melee": (fighter, [Plan("melee", s) for s in (f.ACCURATE, f.AGGRESSIVE, f.DEFENSIVE)]),
            "ranged": (fighter, [Plan("ranged", f.RAPID)]), "magic": (fighter, [Plan("magic", "fire_strike")])}


def summary(candidates) -> list:
    return [(c.entry.npc.id, round(float(c.total_xp_per_hour), 6), round(float(c.gp_per_hour), 6), c.site.spawn,
             c.plan.style) for c in candidates]


@needs_data
@pytest.mark.parametrize("level,location,mode,food,attacks", [
    (1, (3222, 3218, 0), "valuable", 8, inf),
    (30, (3212, 3424, 0), "all", 120, inf),
    (60, (2809, 3436, 0), "valuable", 200, inf),
    (90, (3093, 3493, 0), "none", 300, inf),  # every gp/hr is 0: ties must break as in the reference
    (45, (3087, 9900, 0), "vocabulary", 60, inf),  # underground
    (75, (2650, 3300, 0), "valuable", 0, inf),  # no food: the retreat filter bites
    (1, (3222, 3218, 0), "valuable", 8, 15),  # the starter runes: 15 casts cap every candidate's fighting time
    (40, (3212, 3424, 0), "all", 100, 300),  # a few hundred arrows: the cap bites only for the slow kills
])
def test_fast_ranking_equals_the_reference(level, location, mode, food, attacks):
    items = gd.items()
    bonuses = tuple(map(sum, zip(*(items[i].bonuses for i in ((1277, 1171) if level == 1 else (1333, 1201, 1127))))))
    plans = plans_for(level, bonuses)
    character = Character(location, max(10, level), max(10, level), food, 20, 1201, mode, attacks_held=attacks)
    pool = enemy_pool()
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # no NaN or division warnings from the vectorised path
        fast = CandidateRanker(pool).select(plans, character, 1500)
    reference = select_candidates(pool, plans, character, 1500)
    for combat_class in plans:
        assert summary(fast[combat_class]) == summary(reference[combat_class])
