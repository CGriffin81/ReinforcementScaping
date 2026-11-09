"""Herblore (sim v1; Caleb, 2026-11-08, OQ-2: "Herblore should add herbs and potions"; Choice E (a): the 21 standard
potions; Choice F (a): grinding). The spec is docs/sim-v1-skills-draft.md §4. Druidic Ritual is complete from the start.

From content/global/skill/herblore (rlscape.gamedata.server: herbs, herblore_potions, grindings):
- Cleaning a grimy herb (HerbCleanListener): an item option, for the herb's XP from its level; it locks the player a
  tick, so a person cleans one a tick (CLEAN_TICKS), the first a tick after the first click (CLEAN_FIRST).
- An unfinished potion (HerblorePulse, from a vial of water): the clean herb into the vial, no XP, one a tick after
  the how-many (UNF_FIRST, UNF_TICKS); a lone one takes SINGLE_TICKS and opens no how-many.
- A finished potion: the secondary into the unfinished potion, for the potion's XP, the first SINGLE_TICKS after the
  how-many, then one every FINISH_TICKS (the pulse waits 3 ticks between); the product has three doses.
- Grinding (GrindItemPlugin): a pestle and mortar on the whole ingredient (a unicorn horn, a chocolate bar, a desert
  goat horn, a blue dragon scale, a bird's nest) makes the dust, one every GRIND_TICKS, no XP.
Each how-many batch starts with START_TICKS of clicks (the item used on the other, the how-many's All). The times
are measured on the server (scripts/calibrate_herblore.py, 2026-11-08): every stage and load within 1.00.

The paths, at the nearest bank, as Crafting's are:
- `clean_<herb>` (15; CleanAtBank): take out a load of the grimy herb, clean it, bank it, again.
- `potion_<potion>` (21; PotionAtBank): take out a load and make the potions, a unit at a time from what's there:
  an unfinished potion, or a vial of water and the herb (clean, or grimy and cleaned first, for its XP); and the
  secondary, or its whole ingredient ground first, with a pestle and mortar taken out for it (Choice F (a)). The stages
  run in order on the load: grind, clean, the unfinished potions, the finished ones. The inputs come from the bank:
  drops, or the GE's (Choice A: the agent buys them).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

import numpy as np

from rlscape.gamedata import server as gd
from rlscape.sim.economy import bank_notes, bank_trip, banked_or_noted, nearest_bank
from rlscape.sim.movement import reachable
from rlscape.sim.options import COMPLETED, INPUTS_EXHAUSTED, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import INVENTORY_SLOTS, CharacterState
from rlscape.travel import BANKING_TICKS

CLEAN_TICKS = 1  # HerbCleanListener: lock(player, 1), a herb a click
CLEAN_FIRST = 1  # the first click's tick (measured, scripts/calibrate_herblore.py, 2026-11-08: 28 herbs in 29 ticks)
UNF_FIRST = UNF_TICKS = 1  # HerblorePulse's delay for a batch of unfinished potions
SINGLE_TICKS = 4  # HerblorePulse: a lone unfinished potion, or a finished one, after the pulse's 3-tick wait
FINISH_TICKS = 3  # HerblorePulse: setDelay(3) between finished potions
GRIND_FIRST = GRIND_TICKS = 2  # GrindItemPlugin's SkillPulse: setDelay(2)
START_TICKS = 3  # a how-many batch's clicks (measured, scripts/calibrate_herblore.py, 2026-11-08: every stage exact)


def clean_ticks(units: int) -> int:
    """Cleaning `units` grimy herbs, a click a tick."""
    return CLEAN_FIRST + units * CLEAN_TICKS if units > 0 else 0


def batch_ticks(units: int, first: int, every: int) -> int:
    """A how-many batch of `units`: START_TICKS of clicks, the first after `first`, then one every `every`."""
    return START_TICKS + first + (units - 1) * every if units > 0 else 0


def unfinished_ticks(units: int) -> int:
    return SINGLE_TICKS if units == 1 else batch_ticks(units, UNF_FIRST, UNF_TICKS)


def finished_ticks(units: int) -> int:
    return SINGLE_TICKS if units == 1 else batch_ticks(units, SINGLE_TICKS, FINISH_TICKS)


def grind_ticks(units: int) -> int:
    return batch_ticks(units, GRIND_FIRST, GRIND_TICKS)


@cache
def whole_of() -> dict[int, int]:
    """A dust -> the whole ingredient it's ground from."""
    return {dust: whole for whole, dust in gd.grindings().items()}


@cache
def herb_by_clean() -> dict[int, gd.Herb]:
    return {h.clean: h for h in gd.herbs().values()}


def inputs() -> frozenset[int]:
    """Everything a Herblore path uses: the herbs grimy and clean, vials of water, the unfinished potions, the
    secondaries and their whole ingredients, and the pestle and mortar."""
    potions = gd.herblore_potions().values()
    wholes = {whole_of()[p.secondary] for p in potions if p.secondary in whole_of()}
    return frozenset({h.grimy for h in gd.herbs().values()} | {h.clean for h in gd.herbs().values()}
                     | {p.unfinished for p in potions} | {p.secondary for p in potions} | wholes
                     | {gd.VIAL_OF_WATER, gd.PESTLE_AND_MORTAR})


def _held(state: CharacterState, item: int, banked: bool) -> int:
    return state.inventory.get(item, 0) + (banked_or_noted(state, item) if banked else 0)


def _add_xp(state: CharacterState, xp: float) -> None:
    herblore = SKILL_INDEX["herblore"]
    state.xp[herblore] = min(state.xp[herblore] + xp, MAX_XP)


class CleanAtBank(Option):
    """clean_<herb>: the grimy herb, banked or carried, cleaned at the nearest bank a load at a time."""

    family = "gathering"
    task = "herblore"
    skill = "herblore"

    def __init__(self, herb: gd.Herb):
        self.herb, self.id = herb, f"clean_{herb.name}"

    def held_units(self, state: CharacterState) -> int:
        return _held(state, self.herb.grimy, True)

    def available(self, state: CharacterState) -> bool:
        if state.level("herblore") < self.herb.level or self.held_units(state) <= 0:
            return False
        bank = nearest_bank(state)
        return reachable(state, (bank.x, bank.y, bank.plane))

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        h, detail = self.herb, {"path": self.id}
        elapsed = bank_trip(state, budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED, detail=detail)
        while True:
            bank_notes(state, [h.grimy])
            _deposit_all_but(state, set())
            _withdraw(state, h.grimy, INVENTORY_SLOTS)
            units = state.inventory.get(h.grimy, 0)
            if units == 0:
                return OptionResult(max(elapsed, 1), INPUTS_EXHAUSTED, detail=detail)
            done = min(units, max(budget - elapsed - CLEAN_FIRST, 0) // CLEAN_TICKS)
            state.take(h.grimy, done)
            state.add(h.clean, done)
            _add_xp(state, done * h.experience)
            elapsed += clean_ticks(done)
            if done < units or elapsed + BANKING_TICKS > budget:
                return OptionResult(budget, COMPLETED, detail=detail)
            elapsed += BANKING_TICKS


def _deposit_all_but(state: CharacterState, keep: set[int]) -> None:
    for item in [i for i in state.inventory if i not in keep]:
        state.bank[item] = state.bank.get(item, 0) + state.inventory.pop(item)


def _withdraw(state: CharacterState, item: int, amount: int) -> int:
    take = min(amount, state.bank.get(item, 0))
    if take > 0:
        state.take(item, take, state.bank)
        state.add(item, take)
    return take


@dataclass(frozen=True)
class Sources:
    """What makes a potion's units: the unfinished potions; the vials and herbs (clean, and grimy it can clean); the
    secondaries, and the whole ingredients a pestle and mortar can grind."""

    unfinished: int
    vials: int
    clean: int
    grimy: int
    secondary: int
    whole: int

    def units(self) -> int:
        bases = self.unfinished + min(self.vials, self.clean + self.grimy)
        return min(bases, self.secondary + self.whole)


class PotionAtBank(Option):
    """potion_<potion>: the potion made at the nearest bank from banked or carried inputs, a load at a time."""

    family = "gathering"
    task = "herblore"
    skill = "herblore"

    def __init__(self, potion: gd.Potion):
        self.potion, self.id = potion, f"potion_{potion.name}"
        self.herb = herb_by_clean()[potion.herb]
        self.whole = whole_of().get(potion.secondary)

    def allowed(self, state: CharacterState) -> bool:
        return state.level("herblore") >= self.potion.level

    def sources(self, state: CharacterState, banked: bool) -> Sources:
        p, level = self.potion, state.level("herblore")
        pestle = _held(state, gd.PESTLE_AND_MORTAR, banked) > 0
        return Sources(
            unfinished=_held(state, p.unfinished, banked), vials=_held(state, gd.VIAL_OF_WATER, banked),
            clean=_held(state, p.herb, banked),
            grimy=_held(state, self.herb.grimy, banked) if level >= self.herb.level else 0,
            secondary=_held(state, p.secondary, banked),
            whole=_held(state, self.whole, banked) if self.whole is not None and pestle else 0)

    def held_units(self, state: CharacterState) -> int:
        return self.sources(state, True).units()

    def available(self, state: CharacterState) -> bool:
        if not self.allowed(state) or self.held_units(state) <= 0:
            return False  # the cheap checks first: most states hold no herblore inputs
        bank = nearest_bank(state)
        return reachable(state, (bank.x, bank.y, bank.plane))

    def _restock(self, state: CharacterState) -> int:
        """At the booth: bank everything, then take out the pestle and mortar if a whole ingredient will be ground,
        and as many units as fit: each an unfinished potion, else a vial and a herb (clean before grimy); and a
        secondary, else its whole ingredient. Returns the units taken out."""
        p, h = self.potion, self.herb
        bank_notes(state, [p.unfinished, gd.VIAL_OF_WATER, p.herb, h.grimy, p.secondary,
                           *((self.whole,) if self.whole else ())])
        _deposit_all_but(state, set())
        level, bank = state.level("herblore"), state.bank
        grinds = self.whole is not None and bank.get(self.whole, 0) > 0 and bank.get(gd.PESTLE_AND_MORTAR, 0) > 0 \
            and bank.get(p.secondary, 0) < self.held_units(state)
        if grinds:
            _withdraw(state, gd.PESTLE_AND_MORTAR, 1)
        room, units = state.free_slots(), 0
        while True:
            if bank.get(p.unfinished, 0) > 0:
                base, slots = [(p.unfinished, 1)], 1
            elif bank.get(gd.VIAL_OF_WATER, 0) > 0 and bank.get(p.herb, 0) > 0:
                base, slots = [(gd.VIAL_OF_WATER, 1), (p.herb, 1)], 2
            elif bank.get(gd.VIAL_OF_WATER, 0) > 0 and level >= h.level and bank.get(h.grimy, 0) > 0:
                base, slots = [(gd.VIAL_OF_WATER, 1), (h.grimy, 1)], 2
            else:
                break
            if bank.get(p.secondary, 0) > 0:
                second = p.secondary
            elif grinds and bank.get(self.whole, 0) > 0:
                second = self.whole
            else:
                break
            if slots + 1 > room:
                break
            for item, n in (*base, (second, 1)):
                _withdraw(state, item, n)
            room, units = room - slots - 1, units + 1
        return units

    def mix(self, state: CharacterState, budget: int) -> OptionResult:
        """Make the potions the inventory holds the inputs for, stage by stage: grind, clean, the unfinished potions,
        the finished ones."""
        p, h, inv, elapsed = self.potion, self.herb, state.inventory, 0
        units = self.sources(state, False).units()
        # grind what the units need beyond the dust carried
        if self.whole is not None and inv.get(gd.PESTLE_AND_MORTAR, 0):
            n = min(inv.get(self.whole, 0), max(units - inv.get(p.secondary, 0), 0))
            if n:
                elapsed += grind_ticks(n)
                state.take(self.whole, n)
                state.add(p.secondary, n)
        # clean the grimy herbs the units need beyond the unfinished potions and clean herbs carried
        need = max(min(units, inv.get(gd.VIAL_OF_WATER, 0) + inv.get(p.unfinished, 0)) - inv.get(p.unfinished, 0)
                   - inv.get(p.herb, 0), 0)
        n = min(need, inv.get(h.grimy, 0)) if state.level("herblore") >= h.level else 0
        if n:
            elapsed += clean_ticks(n)
            state.take(h.grimy, n)
            state.add(p.herb, n)
            _add_xp(state, n * h.experience)
        n = min(inv.get(gd.VIAL_OF_WATER, 0), inv.get(p.herb, 0), max(units - inv.get(p.unfinished, 0), 0))
        if n and state.level("herblore") >= p.unfinished_level:
            elapsed += unfinished_ticks(n)
            state.take(gd.VIAL_OF_WATER, n)
            state.take(p.herb, n)
            state.add(p.unfinished, n)
        n = min(inv.get(p.unfinished, 0), inv.get(p.secondary, 0))
        if elapsed + finished_ticks(n) > budget:  # cut short: the finished potions that fit
            n = 0 if elapsed + SINGLE_TICKS > budget else 1 + max(budget - elapsed - START_TICKS - SINGLE_TICKS, 0) \
                // FINISH_TICKS
            n = min(n, inv.get(p.unfinished, 0), inv.get(p.secondary, 0))
            self._finish(state, n)
            return OptionResult(budget, COMPLETED)
        self._finish(state, n)
        return OptionResult(max(elapsed + finished_ticks(n), 1), INPUTS_EXHAUSTED)

    def _finish(self, state: CharacterState, n: int) -> None:
        p = self.potion
        if n > 0:
            state.take(p.unfinished, n)
            state.take(p.secondary, n)
            state.add(p.product, n)
            _add_xp(state, n * p.experience)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        detail = {"path": self.id}
        elapsed = bank_trip(state, budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED, detail=detail)
        while True:
            if self._restock(state) == 0:
                return OptionResult(max(elapsed, 1), INPUTS_EXHAUSTED, detail=detail)
            mixed = self.mix(state, budget - elapsed)
            elapsed += mixed.ticks
            if mixed.termination == COMPLETED or elapsed + BANKING_TICKS > budget:
                return OptionResult(budget, COMPLETED, detail=detail)
            elapsed += BANKING_TICKS


def load_ticks(potion: gd.Potion, units: int, grimy: bool, ground: bool, unfinished: bool) -> int:
    """A load of `units` potions' time at the bank (the rate model's): the stages it needs, then the banking."""
    if units <= 0:
        return BANKING_TICKS
    ticks = grind_ticks(units) if ground else 0
    if not unfinished:
        ticks += (clean_ticks(units) if grimy else 0) + unfinished_ticks(units)
    return ticks + finished_ticks(units) + BANKING_TICKS


def herblore_paths() -> list[Option]:
    return [*(CleanAtBank(h) for h in gd.herbs().values()),
            *(PotionAtBank(p) for p in gd.herblore_potions().values())]
