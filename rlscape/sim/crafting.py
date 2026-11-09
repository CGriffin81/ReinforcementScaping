"""Crafting (sim v1; Caleb, 2026-11-08, OQ-2: "crafting should include leather armor, dragonhide armor, spinning, and
gems"; studded leather, snakeskin and jewellery left out). The spec is docs/sim-v1-skills-draft.md §2.

This module has the crafts made at a bank (rlscape.gamedata.server.crafting_recipes): gems cut with a chisel, and
leather and dragonhide armour sewn with a needle and thread. Each runs as its pulse does: the first unit
`first_ticks` after it starts, then one every `stage_ticks` (a gem a tick; a piece of armour every 5 ticks), after the
clicks that start it (`start_ticks`, measured on the server; `craft_ticks` has the whole time). Like fletching's, the
pulses are cleared by any walk or new action, so crafting is an activity of its own.

Thread (LeatherCrafting.decayThread): every sewn item uses a charge of the reel, and when the charges run out a thread
is taken from the inventory and the reel starts again at 5. The charges are saved on the character
(`CharacterState.thread_charges`). Every item needs a thread in the inventory as it starts, so with T threads held and
c charges left, a run makes at most c + 5 (T - 1) items (thread_capacity).

The paths (`cut_<gem>`, `craft_<item>`; CraftAtBank), as Fletching's are: at the nearest bank, take out the tool, the
thread and a load of the recipe's inputs, craft them, bank the products, and again, until the inputs (banked or
carried) or the time run out. The inputs come from the bank: drops, or the GE's (Choice A: the agent buys them).

Two kinds of path work between a bank and a station (AtStation): take a load from the nearest bank, walk to the
nearest usable station, work it, and again, banking at the bank nearest the station:
- `tan_<leather>` (TanAtTanner; TanningProduct): hides into leather at a tanner, for a fee a hide (1 gp for soft
  leather, 3 for hard, 20 for dragon leather) and no XP, so they're gp paths. The tanning is one interface click.
- `spin_wool`, `spin_flax` (SpinAtWheel; SpinningPulse): wool into balls of wool, flax into bowstrings, one every 4
  ticks (`++ticks % 4`; the 2-tick rate needs a Seers' Village diary).

Picking flax (PickFlax; FieldPickingPlugin; OQ-38, Choice B (a)): in the field south of Seers' Village, a pick every
2 ticks, no XP. A plant gives 4 to 9 picks and is gone for 30 ticks (its charge, re-rolled each pick). It's a
gathering method as trees are (rlscape.sim.gathering), and its paths (rlscape.sim.skilling) are `pick_flax` (kept,
ending at a full inventory) and `pick_flax_spin` (spun at the nearest wheel, Seers' Village's, ending at a full
inventory of bowstrings, as fishing's cooking paths end).
"""

from __future__ import annotations

from functools import cache
from math import inf, isfinite

import numpy as np

from rlscape.combat.access import parse_requirement
from rlscape.gamedata import server as gd
from rlscape.sim.economy import bank_notes, bank_trip, banked_or_noted, nearest_bank
from rlscape.sim.gathering import Site, gather_depleting
from rlscape.sim.movement import reachable, route_ticks, walk
from rlscape.sim.options import COMPLETED, INPUTS_EXHAUSTED, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import COINS, INVENTORY_SLOTS, CharacterState
from rlscape.travel import BANKING_TICKS, travel_ticks

THREAD_CHARGES = 5  # LeatherCrafting.decayThread: a reel of thread every 5 items
TAN_TICKS = 5  # beside the tanner: Trade, then the tanning interface's Tan All, to the leather (measured, 2026-11-08)
SPIN_FIRST = SPIN_TICKS = 4  # SpinningPulse: a product at every 4th pulse
# The clicks before a batch's first stage, measured on the server (scripts/calibrate_crafting.py, 2026-11-08, every
# case exact): the tool used on the input (or the wheel's Spin) and the how-many's button. 3 ticks with a skill dialogue
# or an interface (gems, soft leather, spinning); 4 with LeatherCraftDialogue (hard leather and dragonhide), whose
# dragonhide how-many has no All: "Make 10", clicked again every DRAGON_BATCH items, for the same again.
MAKE_START_TICKS = 3
LEATHER_DIALOGUE_START_TICKS = 4
DRAGON_BATCH = 10
PICK_TICKS = 2  # FieldPickingPlugin: "delay:picking" is 2 ticks for flax (3 for other plants)
FLAX_RESPAWN = 30  # PickingPlant.FLAX's respawn, in ticks
FLAX_CHARGE_ROLL = (2, 8)  # handleFlaxPick: the plant goes once its picks pass 1 + RandomFunction.random(2, 8)
FLAX = 1779
SEERS_FLAX = Site((2743, 3445, 0), 48, "found on the server (debug_nearby, 2026-11-08): 48 flax plants in "
                  "(2737-2750, 3438-3452), south of Seers' Village")


def inputs() -> frozenset[int]:
    """Everything a crafting path uses: the recipes' inputs, the tools and thread, the hides tanned and what's spun."""
    recipes = gd.crafting_recipes().values()
    return frozenset({item for r in recipes for item, _ in r.inputs} | {r.tool for r in recipes} | {gd.THREAD}
                     | {r.hide for r in gd.tanning_recipes().values()}
                     | {r.need for r in gd.spinning_recipes().values()})


def start_ticks(recipe: gd.CraftRecipe) -> int:
    hard = recipe.kind == "dragonhide" or recipe.inputs[0][0] == gd.HARD_LEATHER
    return LEATHER_DIALOGUE_START_TICKS if hard else MAKE_START_TICKS


def craft_ticks(recipe: gd.CraftRecipe, units: int) -> int:
    """Ticks from the first click to the `units`-th item, as the server takes them: the start, the first stage, a stage
    an item after it, and for dragonhide the start and a first stage again every DRAGON_BATCH items."""
    if units <= 0:
        return 0
    batches = -(-units // DRAGON_BATCH) if recipe.kind == "dragonhide" else 1
    return (batches * start_ticks(recipe) + recipe.first_ticks + (units - 1) * recipe.stage_ticks
            + (batches - 1) * (recipe.first_ticks - recipe.stage_ticks))


def spin_ticks(units: int) -> int:
    """Ticks from the wheel's Spin to the `units`-th product (the start, then SpinningPulse's every 4th pulse)."""
    return MAKE_START_TICKS + SPIN_FIRST + (units - 1) * SPIN_TICKS if units > 0 else 0


def thread_capacity(threads: int, charges: int) -> int:
    """Items the threads held and the reel's charges sew (decayThread): c + 5 (T - 1), and none without a thread. A
    reel with no charges left (its last item was sewn without a thread to take) sews one more, then takes a thread."""
    return max(charges, 1) + THREAD_CHARGES * (threads - 1) if threads > 0 else 0


class Craft(Option):
    """Craft one recipe from what the inventory holds, where the character stands."""

    family = "processing"
    task = "crafting"

    def __init__(self, recipe: gd.CraftRecipe):
        self.recipe = recipe
        self.id = f"craft_{recipe.name}"

    def units(self, state: CharacterState) -> int:
        units = min(state.inventory.get(item, 0) // amount for item, amount in self.recipe.inputs)
        if self.recipe.thread:
            units = min(units, thread_capacity(state.inventory.get(gd.THREAD, 0), state.thread_charges))
        return units

    def allowed(self, state: CharacterState) -> bool:
        return state.level("crafting") >= self.recipe.level

    def available(self, state: CharacterState) -> bool:
        return self.allowed(state) and state.inventory.get(self.recipe.tool, 0) > 0 and self.units(state) > 0

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        r, crafting, made = self.recipe, SKILL_INDEX["crafting"], 0
        while self.units(state) > 0:
            if craft_ticks(r, made + 1) > budget:
                return OptionResult(budget, COMPLETED)
            for item, amount in r.inputs:
                state.take(item, amount)
            state.add(r.product)
            state.xp[crafting] = min(state.xp[crafting] + r.experience, MAX_XP)
            if r.thread:
                state.thread_charges -= 1
                if state.thread_charges <= 0 and state.inventory.get(gd.THREAD, 0) > 0:
                    state.take(gd.THREAD)
                    state.thread_charges = THREAD_CHARGES
            made += 1
        return OptionResult(max(craft_ticks(r, made), 1), INPUTS_EXHAUSTED)


class CraftAtBank(Option):
    """A Crafting path: craft one recipe from banked or carried inputs at the nearest bank, a load at a time."""

    family = "gathering"
    task = "crafting"
    skill = "crafting"

    def __init__(self, recipe: gd.CraftRecipe):
        self.recipe = recipe
        self.id = f"{'cut' if recipe.kind == 'gem' else 'craft'}_{recipe.name}"
        self.craft = Craft(recipe)

    def held_units(self, state: CharacterState) -> int:
        """Units the inputs carried, banked and noted make, and the thread held sews."""
        units = min((state.inventory.get(item, 0) + banked_or_noted(state, item)) // amount
                    for item, amount in self.recipe.inputs)
        if self.recipe.thread:
            threads = state.inventory.get(gd.THREAD, 0) + banked_or_noted(state, gd.THREAD)
            units = min(units, thread_capacity(threads, state.thread_charges))
        return units

    def available(self, state: CharacterState) -> bool:
        tool = self.recipe.tool
        if not (self.craft.allowed(state) and (state.inventory.get(tool, 0) > 0 or state.bank.get(tool, 0) > 0)
                and self.held_units(state) > 0):
            return False  # the cheap checks first: most states hold no crafting inputs
        bank = nearest_bank(state)
        return reachable(state, (bank.x, bank.y, bank.plane))

    def load_size(self) -> int:
        """Units one inventory takes, beside the tool and the thread (which stacks)."""
        slots = sum(amount for _, amount in self.recipe.inputs)
        return (INVENTORY_SLOTS - 1 - (1 if self.recipe.thread else 0)) // slots

    def _restock(self, state: CharacterState) -> None:
        """At the booth: bank everything but the tool, the thread and the inputs, then take out the tool, all the
        thread and a load."""
        r = self.recipe
        keep = {item for item, _ in r.inputs} | {r.tool} | ({gd.THREAD} if r.thread else set())
        bank_notes(state, [*(item for item, _ in r.inputs), gd.THREAD])
        for item in [i for i in state.inventory if i not in keep]:
            state.bank[item] = state.bank.get(item, 0) + state.inventory.pop(item)
        if state.inventory.get(r.tool, 0) == 0 and state.bank.get(r.tool, 0) > 0:
            state.take(r.tool, 1, state.bank)
            state.add(r.tool)
        if r.thread and state.bank.get(gd.THREAD, 0) > 0:
            threads = state.bank[gd.THREAD]
            state.take(gd.THREAD, threads, state.bank)
            state.add(gd.THREAD, threads)
        held = {item: state.inventory.get(item, 0) for item, _ in r.inputs}
        room = state.free_slots() + sum(held.values())
        units = min(self.held_units(state), room // sum(a for _, a in r.inputs))
        for item, amount in r.inputs:
            take = min(max(units * amount - held[item], 0), state.bank.get(item, 0))
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


@cache
def path_recipes() -> tuple[gd.CraftRecipe, ...]:
    return tuple(gd.crafting_recipes().values())


def crafting_paths() -> list[CraftAtBank]:
    return [CraftAtBank(r) for r in path_recipes()]


def usable_station(state: CharacterState, kind: str,
                   origin: tuple[int, int, int] | None = None) -> gd.Station | None:
    """The station of this kind with the shortest route from where the character stands (or the travel estimate from
    `origin`), among those whose requirement it meets (levels and items too, unlike processing's) and that it can
    reach."""
    progress = state.access_progress()
    open_ = [s for s in gd.stations()
             if s.kind == kind and (not s.requires or parse_requirement(s.requires).met(progress))]
    ticks = {s.name: route_ticks(state, s.tile) for s in open_}
    if origin is not None:
        ticks = {s.name: travel_ticks(origin, s.tile) if isfinite(ticks[s.name]) else inf for s in open_}
    best = min(open_, key=lambda s: ticks[s.name], default=None)
    return best if best is not None and isfinite(ticks[best.name]) else None


class AtStation(Option):
    """A path between the nearest bank and a station: at the bank, bank what the path doesn't use and take out a
    load; walk to the nearest usable station; work through the load; again."""

    family = "gathering"
    task = "crafting"
    skill = "crafting"
    station_kind = ""

    def held_units(self, state: CharacterState) -> int:
        raise NotImplementedError

    def allowed(self, state: CharacterState) -> bool:
        return True

    def _restock(self, state: CharacterState) -> None:
        raise NotImplementedError

    def _loaded(self, state: CharacterState) -> bool:
        raise NotImplementedError

    def _work(self, state: CharacterState, budget: int) -> OptionResult:
        raise NotImplementedError

    def station(self, state: CharacterState) -> gd.Station | None:
        """The station the path works at from where the character stands; a subclass can pick its own."""
        return usable_station(state, self.station_kind)

    def available(self, state: CharacterState) -> bool:
        bank = nearest_bank(state)
        return (self.allowed(state) and self.held_units(state) > 0 and reachable(state, (bank.x, bank.y, bank.plane))
                and self.station(state) is not None)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed, detail = 0, {"path": self.id}
        while True:
            trip = bank_trip(state, budget - elapsed)
            if trip is None:
                return OptionResult(budget, COMPLETED, detail=detail)
            elapsed += trip
            self._restock(state)
            station = self.station(state)
            if not self._loaded(state) or station is None:
                return OptionResult(max(elapsed, 1), INPUTS_EXHAUSTED, detail=detail)
            walked = walk(state, station.tile, budget - elapsed, elapsed)
            if walked is None:
                return OptionResult(budget, COMPLETED, detail=detail)
            elapsed += walked
            worked = self._work(state, budget - elapsed)
            elapsed += worked.ticks
            if worked.termination == COMPLETED or elapsed >= budget:
                return OptionResult(budget, COMPLETED, detail=detail)


def _bank_all_but(state: CharacterState, keep: set[int]) -> None:
    for item in [i for i in state.inventory if i not in keep]:
        state.bank[item] = state.bank.get(item, 0) + state.inventory.pop(item)


def _withdraw(state: CharacterState, item: int, amount: int) -> None:
    take = min(amount, state.bank.get(item, 0))
    if take > 0:
        state.take(item, take, state.bank)
        state.add(item, take)


class TanAtTanner(AtStation):
    """tan_<leather>: hides into leather at a tanner, a load at a time, paying the fee."""

    station_kind = "tanner"

    def __init__(self, recipe: gd.TanRecipe):
        self.recipe, self.id = recipe, f"tan_{recipe.name}"

    def held_units(self, state: CharacterState) -> int:
        r = self.recipe
        hides = state.inventory.get(r.hide, 0) + banked_or_noted(state, r.hide)
        return min(hides, state.coins() // r.fee)

    def _restock(self, state: CharacterState) -> None:
        r = self.recipe
        bank_notes(state, [r.hide])
        _bank_all_but(state, {r.hide, COINS})
        room = state.free_slots() + state.inventory.get(r.hide, 0) - (0 if COINS in state.inventory else 1)
        hides = min(room, state.inventory.get(r.hide, 0) + state.bank.get(r.hide, 0), state.coins() // r.fee)
        _withdraw(state, COINS, max(hides * r.fee - state.inventory.get(COINS, 0), 0))
        _withdraw(state, r.hide, max(hides - state.inventory.get(r.hide, 0), 0))

    def _loaded(self, state: CharacterState) -> bool:
        return state.inventory.get(self.recipe.hide, 0) > 0 and state.inventory.get(COINS, 0) >= self.recipe.fee

    def _work(self, state: CharacterState, budget: int) -> OptionResult:
        """TanningProduct.tan: every hide carried that the coins carried pay for, at once."""
        r = self.recipe
        if TAN_TICKS > budget:
            return OptionResult(budget, COMPLETED)
        hides = min(state.inventory.get(r.hide, 0), state.inventory.get(COINS, 0) // r.fee)
        state.take(COINS, hides * r.fee)
        state.take(r.hide, hides)
        state.add(r.product, hides)
        return OptionResult(TAN_TICKS, INPUTS_EXHAUSTED)


class Spin(Option):
    """Spin what the inventory holds at the wheel the character stands by (SpinningPulse)."""

    family = "processing"
    task = "crafting"

    def __init__(self, recipe: gd.SpinRecipe):
        self.recipe, self.id = recipe, f"spin_{recipe.name}"

    def allowed(self, state: CharacterState) -> bool:
        return state.level("crafting") >= self.recipe.level

    def available(self, state: CharacterState) -> bool:
        return self.allowed(state) and state.inventory.get(self.recipe.need, 0) > 0

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        r, crafting, made = self.recipe, SKILL_INDEX["crafting"], 0
        while state.inventory.get(r.need, 0) > 0:
            if spin_ticks(made + 1) > budget:
                return OptionResult(budget, COMPLETED)
            state.take(r.need)
            state.add(r.product)
            state.xp[crafting] = min(state.xp[crafting] + r.experience, MAX_XP)
            made += 1
        return OptionResult(max(spin_ticks(made), 1), INPUTS_EXHAUSTED)


class SpinAtWheel(AtStation):
    """spin_wool, spin_flax: banked or carried wool or flax spun at the nearest wheel, a load at a time."""

    station_kind = "spinning_wheel"

    def __init__(self, recipe: gd.SpinRecipe):
        self.recipe, self.id, self.spin = recipe, f"spin_{recipe.name}", Spin(recipe)

    def allowed(self, state: CharacterState) -> bool:
        return self.spin.allowed(state)

    def held_units(self, state: CharacterState) -> int:
        return state.inventory.get(self.recipe.need, 0) + banked_or_noted(state, self.recipe.need)

    def _restock(self, state: CharacterState) -> None:
        need = self.recipe.need
        bank_notes(state, [need])
        _bank_all_but(state, {need})
        _withdraw(state, need, state.free_slots())

    def _loaded(self, state: CharacterState) -> bool:
        return state.inventory.get(self.recipe.need, 0) > 0

    def _work(self, state: CharacterState, budget: int) -> OptionResult:
        return self.spin.run(state, np.random.default_rng(0), budget)


def flax_plant_goes(picks: int, rng: np.random.Generator) -> bool:
    """handleFlaxPick: after its `picks`-th pick, a plant goes if picks - 1 passed RandomFunction.random(2, 8) (2 to
    7), drawn afresh: never before the 4th pick, always at the 9th."""
    return picks - 1 > int(rng.integers(*FLAX_CHARGE_ROLL))


def mean_flax_picks() -> float:
    """The picks a plant gives on average: P(it goes at pick k | it lasted) = (k - 3) / 6 for k = 4..9."""
    lasted, mean = 1.0, 0.0
    for k in range(4, 10):
        goes = min((k - 3) / 6, 1.0)
        mean += k * lasted * goes
        lasted *= 1 - goes
    return mean


class PickFlax(Option):
    """pick_flax's gathering: flax in Seers' Village's field until the inventory is full. No XP.

    Its task is `flax`, whose kit is nothing (Caleb, 2026-11-09, OQ-52): the flax is the product, so `bank_deposit`
    banks it, or `spin_flax` spins it at Crafting 10. Under the crafting task the kit kept it as spinning's input, so
    a picker couldn't bank its load."""

    family = "gathering"
    task = "flax"

    def __init__(self, site: Site = SEERS_FLAX):
        self.id, self.site, self.tile = "pick_flax", site, site.tile

    def available(self, state: CharacterState) -> bool:
        return state.free_slots() > 0 and reachable(state, self.tile)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        picks = [0]  # on the plant being picked

        def goes() -> bool:
            picks[0] += 1
            if flax_plant_goes(picks[0], rng):
                picks[0] = 0
                return True
            return False

        return gather_depleting(state, rng, budget, self.site, PICK_TICKS, chance=lambda: 1.0,
                                collect=lambda: state.add(FLAX), depletes=goes, respawn=FLAX_RESPAWN)


class SpinFlaxAtWheel(Option):
    """pick_flax_spin's processing: walk to the nearest wheel and spin the flax carried."""

    family = "processing"
    task = "crafting"

    def __init__(self):
        self.id, self.spin = "spin_flax_carried", Spin(gd.spinning_recipes()["flax"])

    def available(self, state: CharacterState) -> bool:
        return self.spin.available(state) and usable_station(state, "spinning_wheel") is not None

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        station = usable_station(state, "spinning_wheel")
        walked = walk(state, station.tile, budget)
        if walked is None:
            return OptionResult(budget, COMPLETED)
        spun = self.spin.run(state, rng, budget - walked)
        return OptionResult(min(walked + spun.ticks, budget), spun.termination)


def station_paths() -> list[AtStation]:
    return [*(TanAtTanner(r) for r in gd.tanning_recipes().values()),
            *(SpinAtWheel(r) for r in gd.spinning_recipes().values())]
