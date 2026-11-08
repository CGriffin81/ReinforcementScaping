"""Skilling slots (option catalog §2; Caleb, 2026-10-30/31): like the combat slots, each gathering skill offers its
best paths by XP/hr and by gp/hr at the current levels, gear and position, as actions, with their rates in the
observation. Agents choose a path, not a fixed method.

A path is a gathering method plus what happens to its produce (Caleb: "pair gathering skills with their processing
counterpart"):
- kept, to bank or sell later (the gathering option alone, ending at a full inventory as before);
- or processed by the skill's counterpart where sim v0 has it: woodcutting's logs burned (Firemaking) or cut with a
  knife (Fletching) where they're chopped, fishing's catch cooked (Cooking), mining's iron smelted (Smithing).
Thieving has no counterpart: its paths are the targets and stalls. Fletching (Caleb, 2026-10-31) has its own paths
too, one per recipe, worked at a bank from banked or carried inputs (rlscape.sim.fletching), and so does Crafting
(sim v1, Caleb, 2026-11-08; rlscape.sim.crafting): gems, leather and dragonhide armour at a bank, tanning and
spinning between a bank and a station, and flax picked in Seers' Village's field, kept or spun.

Processing paths gather until the inventory is full, process what they gathered, and gather again while the
processing freed room (burning does, and so does cutting arrow shafts, which stack; cooking and cutting bows don't,
so those paths end at a full inventory; smelting iron frees about half).

Each skill has K_XP slots ranked by XP/hr and K_GP by gp/hr. A path in an XP slot doesn't also fill a gp slot; the
next best takes its place, as in combat. Rates are an analytic model of the same mechanics the paths run (the
gathering, thieving and processing modules), over an option of D ticks, the way the combat ranker values fights:
- at the site: the time per unit (log, ore, fish, success), its XP and its value (data/prices_v2.csv), and the
  processing's time, XP and value;
- the inventory cycle: units per trip (the slots a deposit leaves after keeping the task's kit, over the slots a
  unit takes), and the round trip to the nearest bank (processing paths: to the range or furnace and back);
- travel to the site from where the character stands, taken out of the D ticks.
Bait and the stalls' guards are counted; hitpoints aren't (a path whose thieving the character can't sustain is
masked, as before). The constants the paths use are the modules' own, all to calibrate on the server.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, replace
from functools import cache, lru_cache
from math import ceil

import numpy as np

from rlscape.combat.access import parse_requirement
from rlscape.gamedata import server as gd
from rlscape.sim.engine import ACTIVITY_TICKS
from rlscape.sim.fishing import AFTER_CATCH_TICKS, FIRST_ATTEMPT_TICKS
from rlscape.sim.fishing import ATTEMPT_TICKS as FISH_TICKS
from rlscape.sim.crafting import (FLAX, FLAX_RESPAWN, PICK_TICKS, SPIN_FIRST, SPIN_TICKS, TAN_TICKS, THREAD_CHARGES,
                                   AtStation, CraftAtBank, PickFlax, SpinAtWheel, SpinFlaxAtWheel, TanAtTanner,
                                   crafting_paths, mean_flax_picks, station_paths, usable_station)
from rlscape.sim.economy import nearest_bank
from rlscape.sim.fishing import Fishing, fishing_options
from rlscape.sim.fletching import FIRST_TICK as FLETCH_FIRST
from rlscape.sim.fletching import FletchAtBank, FletchLogs, fletching_paths
from rlscape.sim.gathering import respawn_ticks, site_offsets
from rlscape.sim.kits import kit
from rlscape.sim.mining import ATTEMPT_TICKS as MINE_TICKS
from rlscape.sim.mining import Mining, best_pickaxe, mine_chance, mining_options
from rlscape.sim.options import COMPLETED, INVENTORY_FULL, Option, OptionResult
from rlscape.sim.processing import (CHAIN_TICKS, FIRST_TICK, LIGHT_TICKS, RANGE_TICKS, SMELT_TICKS, TINDERBOX,
                                    BurnLogs, Cook, Smelt, light_chance)
from rlscape.sim.slots import _fingerprint
from rlscape.sim.state import INVENTORY_SLOTS, CharacterState
from rlscape.sim.thieving import (ATTEMPT_OVERHEAD_TICKS, FLEE_TICKS, STEAL_TICKS, SUCCESS_TICKS, Pickpocket,
                                  StealFromStall, pickpocket_chance, pickpocket_options, stall_options)
from rlscape.sim.transport import home_ready
from rlscape.sim.woodcutting import AFTER_LOG_TICKS, FELL_CHANCE, SWING_TICKS, Woodcutting, best_hatchet, chop_chance, \
    skill_success_chance, woodcutting_options
from rlscape.travel import BANKING_TICKS, travel_ticks

SKILLS = ("woodcutting", "fishing", "mining", "thieving", "fletching", "crafting")
PROCESSED_BY = {"woodcutting": "firemaking", "fishing": "cooking", "mining": "smithing"}
K_XP = K_GP = 2  # Caleb, 2026-10-31: 2 by XP + 2 by gp per skill
TICKS_PER_HOUR = 6000
IRON_ORE, IRON_SMELT_SUCCESS = 440, 0.5  # SmeltingPulse: iron succeeds on nextBool()


class Path(Option):
    """A gathering method and, optionally, the processing of what it gathers."""

    family = "gathering"

    def __init__(self, skill: str, gather: Option, process: Option | None = None, suffix: str = ""):
        self.skill, self.gather, self.process = skill, gather, process
        self.id = gather.id + suffix
        self.task = gather.task

    def available(self, state: CharacterState) -> bool:
        return self.gather.available(state) and (self.process is None or self._can_process(state))

    def _can_process(self, state: CharacterState) -> bool:
        if isinstance(self.process, BurnLogs):
            return state.holds(TINDERBOX) and state.level("firemaking") >= gd.log_types()[self.gather.tree.reward][0]
        if isinstance(self.process, FletchLogs):
            return state.inventory.get(gd.KNIFE, 0) > 0 and self.process.recipe(state) is not None
        if isinstance(self.process, Cook):
            return bool(_cookable_fish(self.gather, state)) and nearest(state.progress, "range",
                                                                         _site(self.gather)) is not None
        if isinstance(self.process, SpinFlaxAtWheel):
            return self.process.spin.allowed(state) and usable_station(state, "spinning_wheel",
                                                                       _site(self.gather)) is not None
        return state.level("smithing") >= gd.smelted_bars()["IRON"].level and bool(
            nearest(state.progress, "furnace", _site(self.gather)))

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        if self.process is None:
            result = self.gather.run(state, rng, budget)
            return replace(result, detail={**(result.detail or {}), "path": self.id})
        elapsed, termination = 0, COMPLETED
        while elapsed < budget:
            gathered = self.gather.run(state, rng, budget - elapsed)
            elapsed += gathered.ticks
            termination = gathered.termination
            if termination != INVENTORY_FULL or elapsed >= budget or not self.process.available(state):
                break
            processed = self.process.run(state, rng, budget - elapsed)
            elapsed += processed.ticks
            termination = INVENTORY_FULL if elapsed < budget else COMPLETED
            if state.free_slots() == 0 or not self.gather.available(state):
                break
        return OptionResult(min(elapsed, budget), termination if elapsed < budget else COMPLETED,
                            detail={"path": self.id})


def _site(gather: Option) -> tuple[int, int, int]:
    """Where a gathering method works: its site, fishing spot or target."""
    if isinstance(gather, Fishing):
        return gather.start
    return gather.site.tile if isinstance(gather, (Woodcutting, Mining)) else gather.tile


@cache
def _stations(kind: str) -> tuple[gd.Station, ...]:
    return tuple(s for s in gd.stations() if s.kind == kind)


def nearest(progress, kind: str, tile: tuple[int, int, int]) -> gd.Station | None:
    """The usable station of a kind nearest a tile, by the travel estimate."""
    usable = [s for s in _stations(kind) if not s.requires or parse_requirement(s.requires).met(progress)]
    return min(usable, key=lambda s: travel_ticks(tile, s.tile), default=None)


@cache
def _nearest_bank_ticks(tile: tuple[int, int, int]) -> float:
    return min(travel_ticks(tile, (b.x, b.y, b.plane)) for b in gd.banks())


def _cookable_fish(gather: Fishing, state: CharacterState) -> list[gd.Cookable]:
    cookables, level = gd.cookables(), state.level("cooking")
    return [cookables[f.item] for f in gather.catch_odds(state)[0] if f.item in cookables
            and cookables[f.item].level <= level]


def path_options() -> list[Path]:
    """Every path, by skill: each gathering method kept, then processed where its skill pairs with one."""
    burn, cook, smelt = BurnLogs("burn_logs"), Cook("cook_fish"), Smelt("smelt_iron", "IRON")
    paths: list[Path] = []
    for option in woodcutting_options():
        paths += [Path("woodcutting", option), Path("woodcutting", option, burn, "_burn"),
                  Path("woodcutting", option, FletchLogs(option.tree.reward), "_fletch")]
    for option in fishing_options():
        paths += [Path("fishing", option), Path("fishing", option, cook, "_cook")]
    for option in mining_options():
        paths.append(Path("mining", option))
        if option.rock.reward == IRON_ORE:
            paths.append(Path("mining", option, smelt, "_smelt"))
    paths += [Path("thieving", option) for option in (*pickpocket_options(), *stall_options())]
    flax = PickFlax()
    paths += [Path("crafting", flax), Path("crafting", flax, SpinFlaxAtWheel(), "_spin")]
    return [*paths, *fletching_paths(), *crafting_paths(), *station_paths()]


@dataclass(frozen=True)
class PathRate:
    """A path's value over an option, per hour of it: travel, bank trips and processing included."""

    gather_xp: float  # XP/hr in the gathering skill
    process_xp: float  # XP/hr in its processing counterpart
    gp: float  # value/hr of what the path leaves (data/prices_v2.csv), bait used up taken off
    travel: float  # ticks to the site

    @property
    def xp(self) -> float:
        return self.gather_xp + self.process_xp


@dataclass(frozen=True)
class _Unit:
    """One unit of a gathering method at its site: the ticks it takes, its XP, its value, the slots it takes."""

    ticks: float
    xp: float
    value: float
    slots: float


def _mean_amount(a: int, b: int) -> float:
    """The mean of RandomFunction.random(a, b), whose upper bound is excluded."""
    return float(a) if a == b else (min(a, b) + max(a, b) - 1) / 2


REPLAYS = 32  # sampled loads per depleting-site rate, under a fixed seed


@lru_cache(maxsize=8192)
def _depleting(chance: float, attempt_ticks: int, fall: float, respawn: int, resources: int, load: int,
               first: int = 0, between: int = 3, after_success: int = 0) -> float:
    """Ticks per unit over one load of `load` units at a site of `resources` that each deplete with chance `fall`
    and respawn after `respawn` ticks, with the site's offsets (rlscape.sim.gathering.site_offsets) and the ticks
    the attempt after a success waits. A resource that rarely depletes (a tree falls 1 in 8) costs the move to
    another now and then. One that always does (rocks, normal trees) is replayed REPLAYS times under
    rlscape.sim.gathering's rules, sampling the attempts: whether the site runs out (and the move is skipped while
    the character waits for a regrowth) depends on how the attempts fall, so the mean time isn't enough."""
    if fall < 1:
        return (first + load * (attempt_ticks / chance + fall * between) + (load - 1) * after_success) / load
    rng, total = np.random.default_rng(0), 0.0
    for _ in range(REPLAYS):
        standing, regrowing, elapsed, extra = resources, [], float(first), 0
        for attempts in rng.geometric(chance, size=load):
            while regrowing and regrowing[0] <= elapsed:
                heapq.heappop(regrowing)
                standing += 1
            if standing == 0:
                elapsed = heapq.heappop(regrowing)
                standing = 1
            elapsed += extra + attempts * attempt_ticks
            extra = after_success
            standing -= 1
            heapq.heappush(regrowing, elapsed + respawn)
            if standing > 0:
                elapsed += between
        total += elapsed
    return total / (REPLAYS * load)


def _unit(path: Path, state: CharacterState, load: int) -> _Unit | None:
    """One unit of the path's gathering, averaged over a load of `load` units."""
    values, stackable, g = gd.item_values(), gd.stackable_items(), path.gather
    if isinstance(g, Woodcutting):
        tree, p = g.tree, chop_chance(g.tree, best_hatchet(state), state.level("woodcutting"))
        fall = 0.0 if not tree.depletes else 1.0 if tree.always_falls else FELL_CHANCE
        respawn = respawn_ticks(tree.respawn_min, tree.respawn_max)
        first, between = site_offsets(g.site, SWING_TICKS)
        return _Unit(_depleting(round(p, 3), SWING_TICKS, fall, respawn, g.site.resources, load, first, between,
                                AFTER_LOG_TICKS), tree.experience, values.get(tree.reward, 0), 1.0)
    if isinstance(g, Mining):
        rock, p = g.rock, mine_chance(g.rock, best_pickaxe(state), state.level("mining"))
        if p <= 0:
            return None
        respawn = respawn_ticks(rock.respawn_min, rock.respawn_max)
        first, between = site_offsets(g.site, MINE_TICKS)
        return _Unit(_depleting(round(p, 3), MINE_TICKS, 1.0, respawn, g.site.resources, load, first, between),
                     rock.experience, values.get(rock.reward, 0), 1.0)
    if isinstance(g, Fishing):
        fish, weights, p_any = g.catch_odds(state)
        if p_any <= 0:
            return None
        bait = values.get(g.method.bait[0], 0) if g.method.bait else 0
        ticks = FISH_TICKS / p_any + (AFTER_CATCH_TICKS * (load - 1) + FIRST_ATTEMPT_TICKS - FISH_TICKS) / load
        return _Unit(ticks, float(np.dot(weights, [f.experience for f in fish])),
                     float(np.dot(weights, [values.get(f.item, 0) for f in fish])) - bait, 1.0)
    if isinstance(g, Pickpocket):
        target, p = g.target, pickpocket_chance(g.target, state.level("thieving"))
        loot = [(l, 1.0) for l in g.guaranteed] + [(l, float(w)) for l, w in zip(g.weighted, g.weights)
                                                   if l.item != gd.CLUE_SLOT_EASY]
        value = sum(w * _mean_amount(l.min_amount, l.max_amount) * values.get(l.item, 0) for l, w in loot)
        slots = sum(w for l, w in loot if l.item not in stackable)
        per_attempt = p * SUCCESS_TICKS + (1 - p) * target.stun_ticks + ATTEMPT_OVERHEAD_TICKS
        return _Unit(per_attempt / p, target.experience, value, slots) if p > 0 else None
    if isinstance(g, StealFromStall):
        stall, n = g.stall, g.notice
        ticks = (1 - n) * (STEAL_TICKS + stall.restock_ticks) + n * (STEAL_TICKS + FLEE_TICKS)
        value = float(np.mean([values.get(item, 0) * amount for item, amount in stall.rewards]))
        return _Unit(ticks / (1 - n), stall.experience, value, 1.0)
    if isinstance(g, PickFlax):
        first, between = site_offsets(g.site, PICK_TICKS)
        return _Unit(_depleting(1.0, PICK_TICKS, 1 / mean_flax_picks(), FLAX_RESPAWN, g.site.resources, load, first,
                                between), 0.0, values.get(FLAX, 0), 1.0)
    raise TypeError(f"no rate model for {type(g).__name__}")


def _process(path: Path, state: CharacterState, unit: _Unit, units: float) -> tuple[float, float, float, float]:
    """(ticks, XP, value, slots left per unit) for processing `units` gathered units, the trips it needs included;
    value replaces the units' own."""
    site = _site(path.gather)
    if isinstance(path.process, BurnLogs):
        log_level, xp = gd.log_types()[path.gather.tree.reward]
        first = LIGHT_TICKS / max(light_chance(state.level("firemaking"), log_level), 1e-9)
        return first + (units - 1) * CHAIN_TICKS, units * xp, 0.0, 0.0
    values = gd.item_values()
    if isinstance(path.process, FletchLogs):
        recipe = path.process.recipe(state)
        stacks = recipe.product in gd.stackable_items()
        return (FLETCH_FIRST + (units - 1) * recipe.stage_ticks, units * recipe.experience,
                units * recipe.per_unit * values.get(recipe.product, 0), 0.0 if stacks else 1.0)
    if isinstance(path.process, SpinFlaxAtWheel):
        r = path.process.spin.recipe
        to_wheel = travel_ticks(site, usable_station(state, "spinning_wheel", site).tile)
        return (2 * to_wheel + SPIN_FIRST + (units - 1) * SPIN_TICKS, units * r.experience,
                units * values.get(r.product, 0), 1.0)
    if isinstance(path.process, Cook):
        fish, weights, _ = path.gather.catch_odds(state)
        cookables, level, xp, value = gd.cookables(), state.level("cooking"), 0.0, 0.0
        for f, w in zip(fish, weights):
            c = cookables.get(f.item)
            if c is None or c.level > level:
                value += w * values.get(f.item, 0)
                continue
            ok = skill_success_chance(*c.range, level)
            xp += w * ok * c.experience
            value += w * (ok * values.get(c.cooked, 0) + (1 - ok) * values.get(c.burnt, 0))
        to_range = travel_ticks(site, nearest(state.progress, "range", site).tile)
        return 2 * to_range + FIRST_TICK + units * RANGE_TICKS, units * float(xp), units * float(value), 1.0
    bar = gd.smelted_bars()["IRON"]
    to_furnace = travel_ticks(site, nearest(state.progress, "furnace", site).tile)
    return (2 * to_furnace + units * SMELT_TICKS, units * IRON_SMELT_SUCCESS * bar.experience,
            units * IRON_SMELT_SUCCESS * values.get(bar.product, 0), IRON_SMELT_SUCCESS)


def _fletch_rate(path: FletchAtBank, state: CharacterState, duration_ticks: int) -> PathRate:
    """A Fletching path: loads of the recipe at the nearest bank, as many as the inputs held make, within the
    option. Its gp is what the products are worth over what the inputs were."""
    r, values = path.recipe, gd.item_values()
    held, size = path.held_units(state), path.load_size()
    load = max(min(held, size) if size is not None else held, 1)
    load_ticks = FLETCH_FIRST + (ceil(load / r.units_per_stage) - 1) * r.stage_ticks + BANKING_TICKS
    bank = nearest_bank(state)
    travel = travel_ticks(state.location, (bank.x, bank.y, bank.plane), home_ready(state)) + BANKING_TICKS
    loads = min(held / load, max(duration_ticks - travel, 0.0) / load_ticks)
    per_hour = loads * load * TICKS_PER_HOUR / duration_ticks
    gain = r.per_unit * values.get(r.product, 0) - sum(n * values.get(item, 0) for item, n in r.inputs)
    return PathRate(per_hour * r.experience, 0.0, per_hour * gain, travel)


def _craft_rate(path: CraftAtBank, state: CharacterState, duration_ticks: int) -> PathRate:
    """A Crafting path, as a Fletching one: loads of the recipe at the nearest bank, as many as the inputs and thread
    held make, within the option. Its gp is what the products are worth over the inputs and the thread used (a reel
    every THREAD_CHARGES items)."""
    r, values = path.recipe, gd.item_values()
    held = path.held_units(state)
    load = max(min(held, path.load_size()), 1)
    load_ticks = r.first_ticks + (load - 1) * r.stage_ticks + BANKING_TICKS
    bank = nearest_bank(state)
    travel = travel_ticks(state.location, (bank.x, bank.y, bank.plane), home_ready(state)) + BANKING_TICKS
    loads = min(held / load, max(duration_ticks - travel, 0.0) / load_ticks)
    per_hour = loads * load * TICKS_PER_HOUR / duration_ticks
    thread = values.get(gd.THREAD, 0) / THREAD_CHARGES if r.thread else 0.0
    gain = values.get(r.product, 0) - sum(n * values.get(item, 0) for item, n in r.inputs) - thread
    return PathRate(per_hour * r.experience, 0.0, per_hour * gain, travel)


def _station_rate(path: AtStation, state: CharacterState, duration_ticks: int) -> PathRate | None:
    """A tanning or spinning path: loads between the station nearest the character and the bank nearest it, as many as
    the inputs held make, within the option, after the walk to the nearest bank. Tanning's gp is the leather over the
    hide and the fee; spinning's the product over its input."""
    station, values = usable_station(state, path.station_kind), gd.item_values()
    if station is None:
        return None
    held = path.held_units(state)
    if isinstance(path, TanAtTanner):
        r = path.recipe
        load, work, xp = INVENTORY_SLOTS - 1, float(TAN_TICKS), 0.0
        gain = values.get(r.product, 0) - values.get(r.hide, 0) - r.fee
    else:
        r = path.recipe
        load, xp = INVENTORY_SLOTS, r.experience
        gain = values.get(r.product, 0) - values.get(r.need, 0)
        work = None
    load = max(min(held, load), 1)
    if work is None:
        work = SPIN_FIRST + (load - 1) * SPIN_TICKS
    load_ticks = work + 2 * _nearest_bank_ticks(station.tile) + BANKING_TICKS
    bank = nearest_bank(state)
    travel = travel_ticks(state.location, (bank.x, bank.y, bank.plane), home_ready(state)) + BANKING_TICKS
    loads = min(held / load, max(duration_ticks - travel, 0.0) / load_ticks)
    per_hour = loads * load * TICKS_PER_HOUR / duration_ticks
    return PathRate(per_hour * xp, 0.0, per_hour * gain, travel)


def path_rate(path: Path, state: CharacterState, duration_ticks: int = ACTIVITY_TICKS) -> PathRate | None:
    """The path's XP/hr and gp/hr over an option of `duration_ticks`, or None if the model can't value it. A path's
    XP is in its own skill and, for a processing path, its counterpart."""
    if isinstance(path, FletchAtBank):
        return _fletch_rate(path, state, duration_ticks)
    if isinstance(path, CraftAtBank):
        return _craft_rate(path, state, duration_ticks)
    if isinstance(path, AtStation):
        return _station_rate(path, state, duration_ticks)
    keep = kit(state, path.task)
    room = INVENTORY_SLOTS - sum(1 if i in gd.stackable_items() else n for i, n in state.inventory.items()
                                 if i in keep)
    unit = _unit(path, state, max(room, 1))
    if unit is None or unit.ticks <= 0:
        return None
    site = _site(path.gather)
    travel = travel_ticks(state.location, site, home_ready(state))
    bank_trip = 2 * _nearest_bank_ticks(site) + BANKING_TICKS
    if path.process is None:
        if unit.slots > 0:  # the inventory fills: a bank trip per load
            units = room / unit.slots
            cycle = units * unit.ticks + bank_trip
        else:
            units, cycle = TICKS_PER_HOUR / unit.ticks, TICKS_PER_HOUR
        gather_xp, process_xp, value = units * unit.xp, 0.0, units * unit.value
    else:
        units = float(room)
        ticks, process_xp, value, slots_left = _process(path, state, unit, units)
        cycle = units * unit.ticks + ticks + (bank_trip * slots_left if slots_left else 0.0)
        gather_xp = units * unit.xp
    share = max(duration_ticks - travel, 0.0) / duration_ticks * TICKS_PER_HOUR / cycle
    return PathRate(gather_xp * share, process_xp * share, value * share, travel)


@dataclass(frozen=True)
class SkillCandidate:
    path: Path
    rate: PathRate


class SkillingSlots:
    """Each skill's K_XP + K_GP best available paths, recomputed when the state changes (as CombatSlots are)."""

    def __init__(self, duration_ticks: int = ACTIVITY_TICKS):
        self.duration_ticks = duration_ticks
        self.paths = path_options()
        self._key: tuple | None = None
        self._slots: dict[str, list[SkillCandidate | None]] = {}

    def candidate(self, state: CharacterState, skill: str, index: int) -> SkillCandidate | None:
        """Slot `index` of a skill: 0..K_XP-1 by XP/hr, then K_GP by gp/hr; None if empty."""
        key = _fingerprint(state)
        if key != self._key:
            self._rank(state)
            self._key = key
        return self._slots[skill][index]

    def _rank(self, state: CharacterState) -> None:
        self._slots = {}
        for skill in SKILLS:
            open_ = [SkillCandidate(p, r) for p in self.paths if p.skill == skill and p.available(state)
                     and (r := path_rate(p, state, self.duration_ticks)) is not None]
            by_xp = sorted((c for c in open_ if c.rate.xp > 0), key=lambda c: -c.rate.xp)[:K_XP]  # XP-less paths: gp only
            taken = {c.path.id for c in by_xp}
            by_gp = [c for c in sorted(open_, key=lambda c: -c.rate.gp) if c.path.id not in taken][:K_GP]
            self._slots[skill] = ([*by_xp, *[None] * (K_XP - len(by_xp))]
                                  + [*by_gp, *[None] * (K_GP - len(by_gp))])


class SkillSlot(Option):
    """skill_<skill>_xp<n> / _gp<n>: run the path the slot holds now."""

    family = "gathering"

    def __init__(self, slots: SkillingSlots, skill: str, index: int):
        self.slots, self.skill, self.index = slots, skill, index
        kind, n = ("xp", index + 1) if index < K_XP else ("gp", index - K_XP + 1)
        self.id = f"skill_{skill}_{kind}{n}"
        self.task: str | None = None  # the path's, once one has run (the engine records it after `run`)

    def available(self, state: CharacterState) -> bool:
        return self.slots.candidate(state, self.skill, self.index) is not None

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        path = self.slots.candidate(state, self.skill, self.index).path
        self.task = path.task
        return path.run(state, rng, budget)


def skilling_options(duration_ticks: int = ACTIVITY_TICKS) -> list[SkillSlot]:
    """Catalog §2: each skill in SKILLS × (K_XP + K_GP) slots."""
    slots = SkillingSlots(duration_ticks)
    return [SkillSlot(slots, skill, i) for skill in SKILLS for i in range(K_XP + K_GP)]


def slot_holding(options: list[Option], state: CharacterState, path_id: str) -> str | None:
    """The id of the skilling slot that holds a path right now, if any does."""
    return next((o.id for o in options if isinstance(o, SkillSlot)
                 and (c := o.slots.candidate(state, o.skill, o.index)) is not None and c.path.id == path_id), None)
