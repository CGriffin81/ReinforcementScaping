"""Processing options (option catalog §3), ported from the server's skill pulses with event-level sampling.

Each option walks to the nearest suitable station (or works where the character stands), then turns inventory inputs
into outputs one action at a time, until the inputs run out (inputs_exhausted) or the time budget does (completed).
Every action is one sampled event.

Server mechanics:
- smelting (SmeltingPulse, smelting.Bar): a bar every 5 ticks at a furnace; the ores are used either way; iron
  succeeds half the time (nextBool); experience only on success.
- smithing (SmithingPulse, Bars, SmithingType, BarType): with a hammer at an anvil, an item 4 ticks after the
  previous one (after a first tick); each item uses its type's bars and gives the bar type's experience per bar.
  The option makes the "best" item the level and bars allow: the most bars per item (the most experience per action),
  then the most valuable per bar. Leftover bars go into the next best item that fits.
- cooking (StandardCookingPulse, CookableItems, CookingRewrite): an item every 4 ticks on a fire or 5 on a range
  (after a first tick); burnt if randomDouble(100) > getSkillSuccessChance(low, high, level), with the fire's or the
  range's bounds. Most food cooks on any fire, so with a tinderbox and a log the option lights one where the
  character stands (the firemaking roll, the log's experience, a fire lasting Log.life ticks) and cooks there; bread
  dough, cake and barley need a range (CookingRewrite), as does everything when no fire can be made. The Lumbridge
  castle range (object 114) needs Cook's Assistant and has its own bounds. Experience only if the food isn't burnt.
  Anything CookableItems turns into food is cooked: fish, meat, bread.
- firemaking (FireMakingPulse, firemaking.Log): with a tinderbox, a light attempt every 3 ticks that succeeds if
  ceil((L*50 - req*15) / req / 3 * 4) >= random(99), with L = level + 1; then a step aside. A log lit within 2 ticks
  of the last fire lights at once (setLastFire = now + 2), so after the first log each one in the line costs only the
  step and the next use (CHAIN_TICKS, to calibrate).
- burying bones (BoneBuryListener, Bones): a bone every 2 ticks.

Stations come from data/stations.csv: some tiles from server code, the rest estimates to verify.
"""

from __future__ import annotations

from math import ceil

import numpy as np

from rlscape.combat.access import parse_requirement
from rlscape.gamedata import server as gd
from rlscape.sim.movement import route_ticks, walk
from rlscape.sim.options import COMPLETED, INPUTS_EXHAUSTED, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import CharacterState
from rlscape.sim.woodcutting import skill_success_chance

HAMMER, TINDERBOX = 2347, 590
SMELT_TICKS = 5  # SmeltingPulse: a bar when ++ticks % 5 == 0
SMITH_TICKS = 4  # SmithingPulse: setDelay(4)
RANGE_TICKS = 5  # StandardCookingPulse: 5 on a range, 4 on a fire
FIRE_TICKS = 4
RANGE_ONLY = frozenset({2307, 1889, 6006})  # CookingRewrite: bread dough, uncooked cake, barley
FIRST_TICK = 1  # smithing and cooking pulses spend their first tick setting the delay
LIGHT_TICKS = 3  # FireMakingPulse: an attempt when ++ticks % 3 == 0
CHAIN_TICKS = 2  # one step plus the next log's use, inside the 2-tick relight window; calibrate
BURY_TICKS = 2  # BoneBuryListener: delayClock(SKILLING, 2)
QUEST_LOCKED_TYPES = {"TYPE_DART_TIP": "THE_TOURIST_TRAP", "TYPE_CLAWS": "DEATH_PLATEAU"}  # SmithingPulse checks


def nearest_station(state: CharacterState, kind: str) -> gd.Station | None:
    """The usable station of this kind with the shortest walk (the Al Kharid toll counted in the route)."""
    reachable = [s for s in gd.stations() if s.kind == kind
                 and (not s.requires or parse_requirement(s.requires).met(state.progress))]
    return min(reachable, key=lambda s: route_ticks(state, s.tile), default=None)


def _walk_to(state: CharacterState, station: gd.Station, budget: int) -> int | None:
    """Walk to the station; the ticks it took, or None if the budget ran out on the way."""
    return walk(state, station.tile, budget)


def _remove(state: CharacterState, item: int, amount: int = 1) -> None:
    state.inventory[item] -= amount
    if state.inventory[item] == 0:
        del state.inventory[item]


def _gain(state: CharacterState, skill: str, xp: float) -> None:
    i = SKILL_INDEX[skill]
    state.xp[i] = min(state.xp[i] + xp, MAX_XP)


class Smelt(Option):
    family = "processing"

    def __init__(self, option_id: str, bar: str):
        self.id = option_id
        self.bar = gd.smelted_bars()[bar]

    def _has_ores(self, state: CharacterState) -> bool:
        return all(state.inventory.get(item, 0) >= amount for item, amount in self.bar.ores)

    def available(self, state: CharacterState) -> bool:
        return (state.level("smithing") >= self.bar.level and self._has_ores(state)
                and nearest_station(state, "furnace") is not None)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed = _walk_to(state, nearest_station(state, "furnace"), budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED)
        while True:
            if not self._has_ores(state):
                return OptionResult(elapsed, INPUTS_EXHAUSTED)
            if elapsed + SMELT_TICKS > budget:
                return OptionResult(budget, COMPLETED)
            elapsed += SMELT_TICKS
            for item, amount in self.bar.ores:
                _remove(state, item, amount)
            if self.bar.name != "IRON" or rng.random() < 0.5:  # SmeltingPulse.success: iron is nextBool()
                state.add(self.bar.product)
                _gain(state, "smithing", self.bar.experience)


class Smith(Option):
    family = "processing"

    def __init__(self, option_id: str, bar_type: str):
        self.id = option_id
        bar = gd.smelted_bars()[bar_type].product
        self.items = [s for s in gd.smithables().values() if s.bar == bar]
        self.bar = bar

    def best_item(self, state: CharacterState) -> gd.Smithable | None:
        level, held, values = state.level("smithing"), state.inventory.get(self.bar, 0), gd.item_values()
        fits = [s for s in self.items if s.level <= level and s.bars <= held
                and (s.kind not in QUEST_LOCKED_TYPES or QUEST_LOCKED_TYPES[s.kind] in state.progress.quests_complete)]
        return max(fits, key=lambda s: (s.bars, values.get(s.product, 0) * s.amount / s.bars), default=None)

    def available(self, state: CharacterState) -> bool:
        return (state.inventory.get(HAMMER, 0) > 0 and self.best_item(state) is not None
                and nearest_station(state, "anvil") is not None)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed = _walk_to(state, nearest_station(state, "anvil"), budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED)
        elapsed = min(elapsed + FIRST_TICK, budget)
        while True:
            item = self.best_item(state)
            if item is None:
                return OptionResult(elapsed, INPUTS_EXHAUSTED)
            if elapsed + SMITH_TICKS > budget:
                return OptionResult(budget, COMPLETED)
            elapsed += SMITH_TICKS
            _remove(state, self.bar, item.bars)
            state.add(item.product, item.amount)
            _gain(state, "smithing", item.experience_per_bar * item.bars)


class Cook(Option):
    """Cooks on a fire it lights where the character stands when it can (a tinderbox and a log it can light), the way
    players cooked their catch on the spot; range-only food (bread dough, cake, barley), or everything when no fire
    can be made, goes to the nearest range."""

    family = "processing"

    def __init__(self, option_id: str):
        self.id = option_id
        foods = gd.food_healing()
        self.cookables = {raw: c for raw, c in gd.cookables().items() if c.cooked in foods}

    def _next_raw(self, state: CharacterState, on_fire: bool = False) -> gd.Cookable | None:
        level = state.level("cooking")
        return next((c for raw, c in self.cookables.items() if state.inventory.get(raw, 0) > 0 and c.level <= level
                     and not (on_fire and raw in RANGE_ONLY)), None)

    def _fire_log(self, state: CharacterState) -> int | None:
        """The cheapest log the character can light, if it has a tinderbox."""
        if state.inventory.get(TINDERBOX, 0) == 0:
            return None
        level, logs, values = state.level("firemaking"), gd.log_types(), gd.item_values()
        lightable = [item for item in state.inventory if item in logs and logs[item][0] <= level]
        return min(lightable, key=lambda item: (values.get(item, 0), logs[item][0]), default=None)

    def available(self, state: CharacterState) -> bool:
        can_fire = self._fire_log(state) is not None and self._next_raw(state, on_fire=True) is not None
        return self._next_raw(state) is not None and (can_fire or nearest_station(state, "range") is not None)

    def _cook_one(self, state: CharacterState, rng: np.random.Generator, food: gd.Cookable,
                  bounds: tuple[int, int]) -> None:
        _remove(state, food.raw)
        if rng.random() < skill_success_chance(*bounds, state.level("cooking")):
            state.add(food.cooked)
            _gain(state, "cooking", food.experience)
        else:
            state.add(food.burnt)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed = 0
        log = self._fire_log(state)
        if log is not None and self._next_raw(state, on_fire=True) is not None:
            log_level, xp = gd.log_types()[log]
            elapsed = LIGHT_TICKS * int(rng.geometric(light_chance(state.level("firemaking"), log_level)))
            if elapsed >= budget:
                return OptionResult(budget, COMPLETED)
            _remove(state, log)
            _gain(state, "firemaking", xp)
            fire_out = elapsed + gd.log_fire_ticks()[log]  # 180+ ticks: one fire outlasts a full inventory
            elapsed = min(elapsed + FIRST_TICK, budget)
            while (food := self._next_raw(state, on_fire=True)) is not None:
                if elapsed + FIRE_TICKS > budget:
                    return OptionResult(budget, COMPLETED)
                if elapsed + FIRE_TICKS > fire_out:
                    break
                elapsed += FIRE_TICKS
                self._cook_one(state, rng, food, food.fire)
            if self._next_raw(state) is None:
                return OptionResult(elapsed, INPUTS_EXHAUSTED)
        station = nearest_station(state, "range")
        walked = None if station is None else _walk_to(state, station, budget - elapsed)
        if walked is None:
            return OptionResult(max(elapsed, 1) if station is None else budget,
                                INPUTS_EXHAUSTED if station is None else COMPLETED)
        elapsed = min(elapsed + walked + FIRST_TICK, budget)
        while True:
            food = self._next_raw(state)
            if food is None:
                return OptionResult(elapsed, INPUTS_EXHAUSTED)
            if elapsed + RANGE_TICKS > budget:
                return OptionResult(budget, COMPLETED)
            elapsed += RANGE_TICKS
            self._cook_one(state, rng, food, food.lumbridge_range if station.object == 114 else food.range)


def light_chance(level: int, log_level: int) -> float:
    """FireMakingPulse.success: P(ceil((L*50 - req*15) / req / 3 * 4) >= random(99)), with L = level + 1."""
    threshold = ceil(((level + 1) * 50 - log_level * 15) / log_level / 3 * 4)
    return min(max((threshold + 1) / 99, 0.0), 1.0)  # random(99) is uniform on 0..98


class BurnLogs(Option):
    family = "processing"

    def __init__(self, option_id: str):
        self.id = option_id

    def _next_log(self, state: CharacterState) -> tuple[int, int, float] | None:
        level, logs = state.level("firemaking"), gd.log_types()
        return next(((item, *logs[item]) for item in state.inventory if item in logs and logs[item][0] <= level),
                    None)

    def available(self, state: CharacterState) -> bool:
        return state.inventory.get(TINDERBOX, 0) > 0 and self._next_log(state) is not None

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed, chained = 0, False  # fires are lit where the character stands
        while True:
            log = self._next_log(state)
            if log is None:
                return OptionResult(elapsed, INPUTS_EXHAUSTED)
            item, log_level, xp = log
            step = CHAIN_TICKS if chained else LIGHT_TICKS * int(rng.geometric(
                light_chance(state.level("firemaking"), log_level)))
            if elapsed + step > budget:
                return OptionResult(budget, COMPLETED)
            elapsed += step
            _remove(state, item)
            _gain(state, "firemaking", xp)
            chained = True


class BuryBones(Option):
    family = "processing"

    def __init__(self, option_id: str):
        self.id = option_id

    def _next_bone(self, state: CharacterState) -> int | None:
        bones = gd.bone_experience()
        return next((item for item in state.inventory if item in bones), None)

    def available(self, state: CharacterState) -> bool:
        return self._next_bone(state) is not None

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed = 0
        while True:
            bone = self._next_bone(state)
            if bone is None:
                return OptionResult(elapsed, INPUTS_EXHAUSTED)
            if elapsed + BURY_TICKS > budget:
                return OptionResult(budget, COMPLETED)
            elapsed += BURY_TICKS
            _remove(state, bone)
            _gain(state, "prayer", gd.bone_experience()[bone])


def processing_options() -> list[Option]:
    """Catalog §3, in order."""
    return [Smelt("smelt_bronze", "BRONZE"), Smelt("smelt_iron", "IRON"), Smelt("smelt_steel", "STEEL"),
            Smith("smith_bronze", "BRONZE"), Smith("smith_iron", "IRON"), Smith("smith_steel", "STEEL"),
            Smith("smith_mithril", "MITHRIL"),
            Cook("cook_fish"), BurnLogs("burn_logs"), BuryBones("bury_bones")]
