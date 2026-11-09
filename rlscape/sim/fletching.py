"""Fletching (Caleb, 2026-10-31: "include fletching as a major skill to level"), brought forward from sim v1.

The recipes are the server's (rlscape.gamedata.server.fletching_recipes): cutting logs with a knife into arrow shafts
or unstrung bows, stringing bows, headless arrows, arrows, darts (after The Tourist Trap) and bolts. Each runs as
its craft script does: units_per_stage units every stage_ticks ticks, after a first tick.

All of them are queued scripts on 2009Scape, which any walk or new action clears (MovementPulse and
PulseManager.run call removeWeakScripts and removeNormalScripts). Checked live on 2026-10-31: a walk stopped log
cutting after 2 logs and dart making after 2 stages. So fletching is an activity of its own, never done on the way
somewhere and never "free" between other actions.

Two kinds of path use it (rlscape.sim.skilling):
- woodcutting's chop-and-fletch paths (`wc_<tree>_fletch`): chop until the inventory is full, then cut the logs
  where they were chopped (FletchLogs): normal logs into arrow shafts, which stack, so the chopping goes on (the 2009
  Fletching article's way to train 1-35); other logs into the best bow (u) the level allows, which ends the path at
  a full inventory.
- Fletching's own paths (`fletch_<recipe>`, FletchAtBank): at the nearest bank, take out a recipe's inputs, craft
  them, bank the products, and again, until the inputs (banked or carried) or the time run out. The inputs come from
  the bank: woodcutting's logs, or the GE's (logs, bowstrings, arrowtips, dart tips, unfinished bolts, feathers).
  A bow is strung only where the strung bow is worth more than the unstrung bow and the bowstring (Caleb), at
  data/prices_v2.csv's values: maple, yew and magic longbows and yew shortbows.
"""

from __future__ import annotations

from functools import cache

import numpy as np

from rlscape.gamedata import server as gd
from rlscape.sim.economy import bank_notes, bank_trip, banked_or_noted, nearest_bank
from rlscape.sim.movement import reachable
from rlscape.sim.options import COMPLETED, INPUTS_EXHAUSTED, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import CharacterState
from rlscape.travel import BANKING_TICKS

FIRST_TICK = 1  # every fletching craft script's initialDelay
NORMAL_LOGS = 1511


def worth_stringing(recipe: gd.FletchRecipe) -> bool:
    """Caleb: string a bow only if the strung bow is worth more than the unstrung bow and the bowstring."""
    values = gd.item_values()
    return values.get(recipe.product, 0) > sum(values.get(item, 0) * n for item, n in recipe.inputs)


@cache
def path_recipes() -> tuple[gd.FletchRecipe, ...]:
    """The recipes Fletching's own paths make: all but the bows not worth stringing."""
    return tuple(r for r in gd.fletching_recipes().values() if r.kind != "string" or worth_stringing(r))


def inputs() -> frozenset[int]:
    """Everything a fletching recipe uses."""
    return frozenset(item for r in gd.fletching_recipes().values() for item, _ in r.inputs)


class Fletch(Option):
    """Craft one recipe from what the inventory holds, where the character stands."""

    family = "processing"
    task = "fletching"

    def __init__(self, recipe: gd.FletchRecipe):
        self.recipe = recipe
        self.id = f"fletch_{recipe.name}"

    def units(self, state: CharacterState) -> int:
        return min(state.inventory.get(item, 0) // amount for item, amount in self.recipe.inputs)

    def allowed(self, state: CharacterState) -> bool:
        """The level and the quest (darts) allow it."""
        r = self.recipe
        return state.level("fletching") >= r.level and (r.quest is None or r.quest in state.progress.quests_complete)

    def available(self, state: CharacterState) -> bool:
        tool = self.recipe.tool
        return self.allowed(state) and (tool is None or state.inventory.get(tool, 0) > 0) and self.units(state) > 0

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        r, fletching, elapsed = self.recipe, SKILL_INDEX["fletching"], FIRST_TICK
        while (units := min(self.units(state), r.units_per_stage)) > 0:
            if elapsed > budget:
                return OptionResult(budget, COMPLETED)
            for item, amount in r.inputs:
                state.take(item, units * amount)
            state.add(r.product, units * r.per_unit)
            state.xp[fletching] = min(state.xp[fletching] + units * r.experience, MAX_XP)
            elapsed += r.stage_ticks
        return OptionResult(min(elapsed - r.stage_ticks, budget), INPUTS_EXHAUSTED)


def wood_recipe(log: int, level: int) -> gd.FletchRecipe | None:
    """What a chop-and-fletch path cuts its logs into: arrow shafts from normal logs, otherwise the best bow (u) the
    Fletching level allows."""
    recipes = gd.fletching_recipes()
    if log == NORMAL_LOGS:
        return recipes["arrow_shaft"]
    cut = [r for r in recipes.values() if r.kind == "cut" and r.inputs[0][0] == log and r.level <= level]
    return max(cut, key=lambda r: r.level, default=None)


class FletchLogs(Option):
    """A chop-and-fletch path's processing: cut the carried logs of its tree with the knife."""

    family = "processing"
    task = "fletching"

    def __init__(self, log: int):
        self.log, self.id = log, "fletch_logs"

    def recipe(self, state: CharacterState) -> gd.FletchRecipe | None:
        return wood_recipe(self.log, state.level("fletching"))

    def available(self, state: CharacterState) -> bool:
        recipe = self.recipe(state)
        return recipe is not None and Fletch(recipe).available(state)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        return Fletch(self.recipe(state)).run(state, rng, budget)


class FletchAtBank(Option):
    """A Fletching path: craft one recipe from banked or carried inputs at the nearest bank, a load at a time."""

    family = "gathering"
    task = "fletching"
    skill = "fletching"

    def __init__(self, recipe: gd.FletchRecipe):
        self.recipe = recipe
        self.id = f"fletch_{recipe.name}"
        self.craft = Fletch(recipe)

    def held_units(self, state: CharacterState) -> int:
        """Units the inputs carried, banked and noted make."""
        return min((state.inventory.get(item, 0) + banked_or_noted(state, item)) // amount
                   for item, amount in self.recipe.inputs)

    def available(self, state: CharacterState) -> bool:
        tool = self.recipe.tool
        if not (self.craft.allowed(state) and (tool is None or state.holds(tool) or state.bank.get(tool, 0) > 0)
                and self.held_units(state) > 0):
            return False  # the cheap checks first: most states hold no fletching inputs (the mask speed-up)
        bank = nearest_bank(state)
        return reachable(state, (bank.x, bank.y, bank.plane))

    def load_size(self) -> int | None:
        """Units one inventory takes, or None if the inputs all stack (then everything held is one load)."""
        stackable = gd.stackable_items()
        slots = sum(amount for item, amount in self.recipe.inputs if item not in stackable)
        if not slots:
            return None
        return (28 - (1 if self.recipe.tool else 0)) // slots

    def _restock(self, state: CharacterState) -> None:
        """At the booth: bank everything but the tool and the inputs, then take out the tool and a load."""
        r, keep = self.recipe, {item for item, _ in self.recipe.inputs} | ({self.recipe.tool} - {None})
        bank_notes(state, [item for item, _ in r.inputs])
        for item in [i for i in state.inventory if i not in keep]:
            state.bank[item] = state.bank.get(item, 0) + state.inventory.pop(item)
        if r.tool is not None and r.tool not in state.inventory and state.bank.get(r.tool, 0) > 0:
            state.take(r.tool, 1, state.bank)
            state.add(r.tool)
        size, stackable = self.load_size(), gd.stackable_items()
        units = self.held_units(state)
        if size is not None:
            room = state.free_slots() + sum(state.inventory.get(i, 0) for i, _ in r.inputs if i not in stackable)
            units = min(units, room // sum(a for i, a in r.inputs if i not in stackable))
        for item, amount in r.inputs:
            take = min(max(units * amount - state.inventory.get(item, 0), 0), state.bank.get(item, 0))
            if take:
                state.take(item, take, state.bank)
                state.add(item, take)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed = bank_trip(state, budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED)
        while True:
            self._restock(state)
            if not self.craft.available(state):
                return OptionResult(max(elapsed, 1), INPUTS_EXHAUSTED, detail={"path": self.id})
            crafted = self.craft.run(state, rng, budget - elapsed)
            elapsed += crafted.ticks
            if crafted.termination == COMPLETED or elapsed + BANKING_TICKS > budget:
                return OptionResult(budget, COMPLETED, detail={"path": self.id})
            elapsed += BANKING_TICKS


def fletching_paths() -> list[FletchAtBank]:
    return [FletchAtBank(r) for r in path_recipes()]
