"""kill_cows (Caleb, 2026-11-09: "Add cow killing as a gathering method for crafting supplies. It will use the highest
combat style so as to have faster kills. Bury all normal bones gathered."): Crafting's skilling path that gathers
cowhides by killing cows.

- **The fight:** the class and style the character kills cows fastest with (combat_rates' kills an hour, for each
  class it can fight with, as the combat slots arm it; ties go to the higher level of the skill the style trains).
  It's fought as any fight is (rlscape.sim.combat.fight), at the cow site with the least travel and bank trip (among
  those with two or more cows, or any if none has).
- **The loot:** the hides and the normal bones are picked up. The raw beef is left. Whenever the inventory fills, the
  bones carried are buried (BURY_TICKS a bone, its Prayer XP) and the fight goes on. It ends with the inventory full of
  hides, at the budget, out of food, or at a death.
- **No Crafting XP:** it's a gp path in Crafting's slots, as `pick_flax` is. Its task is the class fought, so a deposit
  keeps that class's kit and banks the hides (the crafting kit would keep them, as it kept picked flax before OQ-52).
"""

from __future__ import annotations

from functools import cache
from math import inf, isfinite

import numpy as np

from rlscape.combat.candidates import COMBAT_CLASSES, PoolEntry, Site, enemy_pool
from rlscape.combat.rates import PICKUP_TICKS, Plan, combat_rates
from rlscape.gamedata import server as gd
from rlscape.sim.combat import fight
from rlscape.sim.equipment import fighter_for
from rlscape.sim.health import foods_held, regenerate, retreat_hp
from rlscape.sim.movement import reachable
from rlscape.sim.options import COMPLETED, INVENTORY_FULL, Option, OptionResult
from rlscape.sim.processing import BURY_TICKS
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.slots import _armed, _attacks_held, _fingerprint, _plans
from rlscape.sim.state import CharacterState
from rlscape.sim.transport import home_ready
from rlscape.travel import travel_ticks

COWHIDE, NORMAL_BONES = 1739, 526


def LOOT(item: int) -> bool:  # noqa: N802 (a loot rule, as fight takes it)
    """The cows' drops it picks up: the hides, and the normal bones to bury."""
    return item in (COWHIDE, NORMAL_BONES)
STYLE_SKILL = {"accurate": "attack", "aggressive": "strength", "defensive": "defence"}  # melee's styles


@cache
def cow_entries() -> tuple[PoolEntry, ...]:
    return tuple(e for e in enemy_pool() if e.npc.name.lower() == "cow")


def _skill_of(plan: Plan) -> str:
    return STYLE_SKILL.get(plan.style, "attack") if plan.combat_class == "melee" else plan.combat_class


def _bury(state: CharacterState, budget: int) -> tuple[int, int]:
    """Bury the normal bones carried, BURY_TICKS each: (bones buried, ticks)."""
    buried, ticks, xp = 0, 0, gd.bone_experience()[NORMAL_BONES]
    prayer = SKILL_INDEX["prayer"]
    while state.inventory.get(NORMAL_BONES, 0) > 0 and ticks + BURY_TICKS <= budget:
        state.take(NORMAL_BONES, 1)
        state.xp[prayer] = min(state.xp[prayer] + xp, MAX_XP)
        buried, ticks = buried + 1, ticks + BURY_TICKS
    return buried, ticks


class KillCows(Option):
    family = "gathering"
    skill = "crafting"
    task = "combat:melee"  # each run sets it to the class it fights with

    def __init__(self) -> None:
        self.id = "kill_cows"
        self._key: tuple | None = None
        self._choice: tuple[PoolEntry, Plan, Site] | None = None

    def choice(self, state: CharacterState) -> tuple[PoolEntry, Plan, Site] | None:
        """(the cow, the plan with the fastest kills, the site), or None if no plan can hurt a cow it can reach."""
        key = _fingerprint(state)
        if key != self._key:
            self._key, self._choice = key, self._choose(state)
        return self._choice

    def _choose(self, state: CharacterState) -> tuple[PoolEntry, Plan, Site] | None:
        best, best_key = None, None
        room = max(state.free_slots(), 1)
        for combat_class in COMBAT_CLASSES:
            armed = _armed(state, combat_class)
            fighter = None
            for plan in _plans(armed, combat_class):
                fighter = fighter or fighter_for(armed)
                attacks = _attacks_held(armed, plan, LOOT)  # unlimited for melee; the runes' casts, the arrows held
                for entry in cow_entries():
                    rates = combat_rates(fighter, plan, entry.npc, 0.0)
                    if rates is None or attacks < room * rates.attacks_per_kill:
                        continue  # it can't kill a load's cows with the ammunition it holds (found 2026-11-09)
                    key = (rates.kills_per_hour, state.level(_skill_of(plan)))
                    if best_key is None or key > best_key:
                        best, best_key = (entry, plan), key
        if best is None:
            return None
        entry, plan = best
        home = home_ready(state)
        sites = [s for e in cow_entries() for s in e.sites if reachable(state, s.spawn)]
        if not sites:
            return None
        busy = [s for s in sites if s.spawns >= 2] or sites
        site = min(busy, key=lambda s: (travel_ticks(state.location, s.spawn, home) + s.bank_trip_ticks, s.spawn))
        entry = next(e for e in cow_entries() if site in e.sites)
        return entry, plan, site

    def available(self, state: CharacterState) -> bool:
        if state.free_slots() == 0:
            return False
        if state.hp <= retreat_hp(state) and not foods_held(state):
            return False  # the fight would retreat before its first swing, as FightSlot masks it
        return self.choice(state) is not None

    def rate(self, state: CharacterState, duration_ticks: int) -> tuple[float, float, float, float]:
        """(0, 0, gp/hr, travel) for the skilling slots: hides at the chosen plan's kills, a pickup each for the hide
        and the bone and the bone's burying a kill, a bank trip a load, after the walk there."""
        choice = self.choice(state)
        if choice is None:
            return 0.0, 0.0, 0.0, inf
        entry, plan, site = choice
        rates = combat_rates(fighter_for(_armed(state, plan.combat_class)), plan, entry.npc, 0.0)
        travel = travel_ticks(state.location, site.spawn, home_ready(state))
        if rates is None or not isfinite(travel) or rates.ticks_per_kill <= 0:
            return 0.0, 0.0, 0.0, inf
        per_kill = rates.ticks_per_kill + 2 * PICKUP_TICKS + BURY_TICKS
        room = max(state.free_slots(), 1)
        loads = max(duration_ticks - travel, 0.0) / (room * per_kill + site.bank_trip_ticks)
        per_hour = 6_000 / duration_ticks
        return 0.0, 0.0, loads * room * gd.item_values().get(COWHIDE, 0) * per_hour, travel

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        entry, plan, site = self.choice(state)
        self.task = f"combat:{plan.combat_class}"
        elapsed, kills, buried, result = 0, 0, 0, None
        while elapsed < budget:
            result = fight(state, rng, budget - elapsed, entry, plan, site, LOOT)
            elapsed += result.ticks
            kills += (result.detail or {}).get("kills", 0)
            b, ticks = _bury(state, budget - elapsed)
            regenerate(state, ticks)
            buried, elapsed = buried + b, elapsed + ticks
            if result.termination != INVENTORY_FULL or b == 0:
                break  # a full inventory of hides, the budget, out of food or a death
        termination = result.termination if result is not None else COMPLETED
        detail = {"path": self.id, "target": entry.npc.id, "style": plan.style, "class": plan.combat_class,
                  "site": site.spawn, "kills": kills, "buried": buried}
        return OptionResult(max(min(elapsed, budget), 1), termination, True, detail)
