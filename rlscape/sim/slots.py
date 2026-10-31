"""The combat candidate slots and the actions on them (option catalog §4.A and §4.D).

Every decision, the candidate ranker (rlscape.combat.ranking) picks for each combat class the 3 best monsters by
XP/hr and then the 3 best by gp/hr, for the character as it is right now. One CombatSlots object does that once per
state and serves all 30 slot actions, both their mask entries and their runs (and, later, the observation's
candidate features):
- the fighter is the character as it will be after the fight's own wielding step for that class
  (equipment.wield_best, run on a copy), so the ranking sees the gear the fight will use;
- the access table sees state.access_progress(): quests, items held, levels and coins;
- a candidate's share of the option is capped by how long the ammunition or runes last (_attacks_held);
- the ranking is cached on a fingerprint of everything it reads, so the 30 mask entries cost one ranking, and the
  run that follows a mask check fights exactly the candidate the mask showed.

Actions, with ids fight_<class>_<xp|gp><n>[_<style>]:
- melee: 6 slots × 3 training styles (accurate → Attack, aggressive → Strength, defensive → Defence). A slot's
  monster is ranked by its best style. A style is masked if it fails the retreat-aware filter (§4.B) on its own,
  because the filter is what makes starting a fight safe (an agent choice; reversible);
- ranged: 6 slots, ranked by the best of the accurate, rapid and longrange styles; open while the character has a
  ranged kit (equipment.ranged_kits);
- magic: 6 slots for the best spell the Magic level and runes allow (combat.best_spell); open while there is one.

A slot is also masked while HP is at or below the retreat point with no food held: the fight would retreat before
its first swing, so the action would do nothing but pass a tick (found by the scripted guide, 2026-10-30).

Loot modes (loot_<mode>) set what fights pick up. Setting one takes LOOT_MODE_TICKS. The current mode is masked, so
the action is never a no-op.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from functools import cache
from math import inf

import numpy as np

from rlscape.combat import formulas as f
from rlscape.combat.candidates import COMBAT_CLASSES, LOOT_MODES, Candidate, Character, enemy_pool, loot_rule
from rlscape.combat.ranking import CandidateRanker
from rlscape.combat.rates import Plan
from rlscape.gamedata import server as gd
from rlscape.sim.combat import arrow_land_chance, best_spell, casts_held, fight
from rlscape.sim.engine import ACTIVITY_TICKS
from rlscape.sim.equipment import SHIELD, WEAPON, fighter_for, ranged_ready, wield_best
from rlscape.sim.health import food_healing_held, foods_held, retreat_hp
from rlscape.sim.movement import reachable
from rlscape.sim.options import COMPLETED, Option, OptionResult
from rlscape.sim.state import CharacterState

K = 3  # monsters per list: 3 by XP/hr, then 3 by gp/hr
MELEE_STYLES = (f.ACCURATE, f.AGGRESSIVE, f.DEFENSIVE)
RANGED_STYLES = (f.ACCURATE, f.RAPID, f.LONGRANGE)
LOOT_MODE_TICKS = 1  # changing a setting; the engine needs at least one tick per decision


@cache
def shared_ranker() -> CandidateRanker:
    """One ranker per process, so its caches (rates per fighter, loot per mode, access per progress) are shared by
    every simulator."""
    return CandidateRanker(enemy_pool())


@cache
def _pool_index() -> dict[int, int]:
    """NPC id -> position in the ranker's pool (one entry per NPC id)."""
    return {entry.npc.id: i for i, entry in enumerate(shared_ranker().pool)}


def _fingerprint(state: CharacterState) -> tuple:
    """Everything the ranking reads from the state."""
    return (state.tick, state.location, state.hp, tuple(state.xp), tuple(state.inventory.items()),
            tuple(state.equipment.items()), tuple(state.worn_amounts.items()), tuple(state.bank.items()),
            state.loot_mode, state.progress)


class CombatSlots:
    def __init__(self, vocabulary: Iterable[int] = (), duration_ticks: int = ACTIVITY_TICKS):
        self.vocabulary = frozenset(vocabulary)
        self.duration_ticks = duration_ticks
        self._key: tuple | None = None
        self._slots: dict[str, list[Candidate]] = {}
        self._styles: list[frozenset[str]] = []  # per melee slot: the styles that pass the filter on their own

    def candidate(self, state: CharacterState, combat_class: str, index: int,
                  style: str | None = None) -> Candidate | None:
        """The candidate in a slot, or None if the slot is empty (or the style fails the filter)."""
        key = _fingerprint(state)
        if key != self._key:
            self._rank(state)
            self._key = key
        slots = self._slots.get(combat_class, [])
        if index >= len(slots) or (style is not None and style not in self._styles[index]):
            return None
        return slots[index]

    def loot(self, state: CharacterState):
        return loot_rule(state.loot_mode, self.vocabulary)

    def _rank(self, state: CharacterState) -> None:
        """Rank each class for the character armed for it: its own gear, shield and free slots."""
        ranker, progress, food = shared_ranker(), state.access_progress(), food_healing_held(state)
        self._slots, self._styles, fighters = {}, [], {}
        for combat_class in COMBAT_CLASSES:
            armed = replace(state, inventory=dict(state.inventory), equipment=dict(state.equipment),
                            worn_amounts=dict(state.worn_amounts))
            wield_best(armed, combat_class)
            plans = _plans(armed, combat_class)
            if not plans:
                continue
            fighters[combat_class] = fighter = fighter_for(armed)
            character = Character(state.location, state.max_hp(), state.hp, food, armed.free_slots(),
                                  armed.equipment.get(SHIELD), state.loot_mode, progress,
                                  _attacks_held(armed, plans[0], self.loot(state)))
            self._slots[combat_class] = ranker.select({combat_class: (fighter, plans)}, character, self.duration_ticks,
                                                      K, self.vocabulary)[combat_class]
        fighter = fighters["melee"]
        for candidate in self._slots["melee"]:
            i = _pool_index()[candidate.entry.npc.id]
            self._styles.append(frozenset(
                s for s in MELEE_STYLES
                if (r := ranker.rates(fighter, Plan("melee", s))[i]) is not None
                and r.passes_retreat_filter(state.max_hp(), state.hp, food)))


def _attacks_held(armed: CharacterState, plan: Plan, loot) -> float:
    """The attacks the armed character's ammunition allows, in expectation: casts the runes pay for; worn arrows,
    bolts or thrown weapons, stretched by the shots that land and are picked back up (as rlscape.sim.combat fights
    them); unlimited for melee and crystal bows."""
    if plan.combat_class == "magic":
        return casts_held(armed, plan.style)
    if plan.combat_class == "ranged":
        ranged = gd.ranged_weapons()[armed.equipment[WEAPON]]
        if ranged.weapon_type == "DEGRADING":
            return inf
        stack, ammo = armed.worn(ranged.ammo_slot), armed.equipment[ranged.ammo_slot]
        recovered = arrow_land_chance(armed.level("ranged")) if ranged.drop_ammo and loot(ammo) else 0.0
        return stack / (1 - recovered)
    return inf


def _plans(armed: CharacterState, combat_class: str) -> list[Plan]:
    """The plans a class is ranked with, for the character as armed for it; none if it can't fight that way."""
    if combat_class == "melee":
        return [Plan("melee", s) for s in MELEE_STYLES]
    if combat_class == "ranged":
        return [Plan("ranged", s) for s in RANGED_STYLES] if ranged_ready(armed) else []
    spell = best_spell(armed)
    return [Plan("magic", spell)] if spell else []


class FightSlot(Option):
    """Fight the monster in one candidate slot, at the site the ranking chose, until the time budget, a full
    inventory, running out of food, or death (rlscape.sim.combat.fight)."""

    family = "combat"

    def __init__(self, slots: CombatSlots, combat_class: str, index: int, style: str | None = None):
        self.slots, self.combat_class, self.index, self.style = slots, combat_class, index, style
        self.task = f"combat:{combat_class}"
        self.id = f"fight_{combat_class}_{'xp' if index < K else 'gp'}{index % K + 1}" + (f"_{style}" if style else "")

    def available(self, state: CharacterState) -> bool:
        if state.hp <= retreat_hp(state) and not foods_held(state):
            return False  # the fight would retreat before its first swing (rlscape.sim.combat.fight)
        candidate = self.slots.candidate(state, self.combat_class, self.index, self.style)
        return candidate is not None and reachable(state, candidate.site.spawn)  # a desert site needs a Shantay pass

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        candidate = self.slots.candidate(state, self.combat_class, self.index, self.style)
        plan = Plan(self.combat_class, self.style) if self.style else candidate.plan
        return fight(state, rng, budget, candidate.entry, plan, candidate.site, self.slots.loot(state))


class SetLootMode(Option):
    family = "loot"

    def __init__(self, mode: str):
        self.mode, self.id = mode, f"loot_{mode}"

    def available(self, state: CharacterState) -> bool:
        return state.loot_mode != self.mode

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        state.loot_mode = self.mode
        return OptionResult(LOOT_MODE_TICKS, COMPLETED)


def combat_options(vocabulary: Iterable[int] = (), duration_ticks: int = ACTIVITY_TICKS) -> list[Option]:
    """The 30 slot actions (melee slot by slot, each with its 3 styles; then ranged; then magic), then the 4 loot
    modes. All slot actions share one CombatSlots."""
    slots = CombatSlots(vocabulary, duration_ticks)
    fights: list[Option] = []
    for combat_class in COMBAT_CLASSES:
        for index in range(2 * K):
            styles = MELEE_STYLES if combat_class == "melee" else (None,)
            fights += [FightSlot(slots, combat_class, index, style) for style in styles]
    return fights + [SetLootMode(mode) for mode in LOOT_MODES]
