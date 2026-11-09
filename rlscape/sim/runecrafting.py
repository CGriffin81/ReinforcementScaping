"""Runecrafting (sim v1; Caleb, 2026-11-08, OQ-2: "Runecrafting should add runes and essence"; OQ-38's Choice G (b):
essence is mined and crafted by separate paths). The spec is docs/sim-v1-skills-draft.md §5, the server's data
rlscape.gamedata.runecrafting.

Part 1, here: the essence and the ruins.
- `mine_essence` (MineEssence, a Mining path): to the nearest wizard who teleports to the essence mine
  (EssenceTeleport.Wizard: Aubury in Varrock, Cromperty in East Ardougne, Distentor in Yanille; Sedridor's basement is
  off the travel map), his Teleport to one of the mine's seven landing spots at random, a walk to the nearest essence
  rock, and mining to a full inventory. Essence mining always succeeds: an essence every getDelay ticks by the pickaxe
  (rune 2 to bronze 7), plus the tick every mining script's wait adds (rlscape.sim.mining), the first a wait after the
  click; 5 Mining XP each; pure essence from Mining 30 (MiningListener.calculateReward). Then the mine's portal back to
  the wizard. It ends there, at a full inventory, as gathering paths do (catalog §1: activities don't bank).
- `rc_<rune>` (RunecraftAtRuins): at the nearest bank, bank everything but the essence and the talisman, take out the
  talisman and a load of essence; walk to the ruins; use the talisman on them (MysteriousRuinListener), which lands the
  character beside the altar; walk to it and craft every essence carried at once (RuneCraftPulse); walk to the portal,
  which leaves by the ruins; again. Air to body take rune essence or pure, one kind a click (getEssenceItem: rune
  essence first), so a load is one kind, rune essence first; the rest take pure only. Law's ruins are on Entrana, whose
  monks refuse weapons and armour (the travel model's boat rule), so its path banks the worn ones too. The runes: the
  nine whose ruins the travel model reaches (RC_RUNES). Cosmic's ruins are in Zanaris, which it doesn't (OQ-45);
  death's are reached by the Abyss's rift, and astral and blood stay out (OQ-39).
- Inside the ruins, the walk from the landing to the altar and from the altar to the portal is the pathfinder's steps
  on the server (debug_nearby, 2026-11-08), walked with run energy as walks outside are. Entering, crafting and leaving,
  the wizard's teleport and the mine's portal are estimates, to be measured on the server, as is chaos's maze.

The tiaras, the inputs in V, the Abyss and its pouches come next (the draft's §5 and §6).
"""

from __future__ import annotations

from functools import cache
from math import inf, isfinite

import numpy as np

from rlscape.gamedata import runecrafting as rcd
from rlscape.gamedata import server as gd
from rlscape.sim.crafting import AtStation
from rlscape.sim.economy import bank_notes, banked_or_noted, nearest_bank
from rlscape.sim.mining import best_pickaxe
from rlscape.sim.movement import reachable, route_ticks, timed, walk
from rlscape.sim.options import COMPLETED, INPUTS_EXHAUSTED, INVENTORY_FULL, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import COINS, INVENTORY_SLOTS, CharacterState
from rlscape.travel import BANKING_TICKS, LEVEL_CHANGE_TICKS, RUN_TILES_PER_TICK, overhead, travel_ticks

TICKS_PER_HOUR = 6000
RC_RUNES = ("air", "mind", "water", "earth", "fire", "body", "chaos", "nature", "law")
# (tiles from the landing to the altar, changes of plane; tiles from the altar to the portal, changes): the
# pathfinder's steps on the server (debug_nearby, 2026-11-08); altar to portal is the tiles between them. Chaos's altar
# is at the foot of a maze three floors down from the landing (2275, 4847, 3): an estimate, to measure.
INSIDE = {"air": ((4, 0), (5, 0)), "mind": ((12, 0), (13, 0)), "water": ((2, 0), (12, 0)),
          "earth": ((10, 0), (11, 0)), "fire": ((15, 0), (9, 0)), "body": ((5, 0), (6, 0)),
          "chaos": ((30, 3), (30, 3)), "nature": ((5, 0), (6, 0)), "law": ((12, 0), (14, 0))}
ENTER_TICKS = 3  # the talisman used on the ruins, to landing inside (estimate; to measure)
CRAFT_TICKS = 4  # the altar clicked: RuneCraftPulse locks the character 4 ticks (to measure)
PORTAL_TICKS = 3  # the portal clicked, to standing by the ruins (estimate; to measure)
TELEPORT_TICKS = 5  # the wizard's Teleport: EssenceTeleport locks 4 ticks and lands on the second pulse (to measure)
MINE_PORTAL_TICKS = 3  # the mine's portal, back to the wizard (estimate; to measure)
SCRIPT_WAIT_EXTRA = 1  # a mining script's wait is a tick longer than its delay (rlscape.sim.mining)
# EssenceTeleport.LOCATIONS -> (steps to the nearest essence rock, tiles from that rock to its nearest portal), from the
# pathfinder on the server (debug_nearby, 2026-11-08)
MINE_WALKS = {(2911, 4832, 0): (20, 6), (2913, 4837, 0): (17, 7), (2930, 4850, 0): (1, 7), (2894, 4811, 0): (1, 4),
              (2896, 4845, 0): (3, 6), (2922, 4820, 0): (6, 6), (2931, 4813, 0): (1, 6)}
SURFACE_WIZARDS = ("aubury", "cromperty", "distentor")  # Sedridor's (3107, 9573) is underground, off the travel map
# Coins a trip carries for its fares: nature's ruins are reached from Draynor's bank by the Karamja boat, 30 gp each
# way (the travel model's nearest bank to them; Shilo Village's walls keep its bank further, 535 ticks)
FARE_COINS = {"nature": 60}


def essence_kinds(rune: rcd.Rune) -> tuple[int, ...]:
    """The essence a rune's altar takes, in the order getEssenceItem crafts it."""
    return (rcd.PURE_ESSENCE,) if rune.pure_only else (rcd.RUNE_ESSENCE, rcd.PURE_ESSENCE)


def inputs() -> frozenset[int]:
    """What a Runecrafting path carries: essence and the talismans."""
    return frozenset({rcd.RUNE_ESSENCE, rcd.PURE_ESSENCE, *rcd.talismans().values()})


def _walk_estimate(tiles: float, changes: int = 0) -> float:
    return tiles / RUN_TILES_PER_TICK + overhead(tiles) + changes * LEVEL_CHANGE_TICKS


def _walk_inside(state: CharacterState, leg: tuple[int, int]) -> int:
    """Walk a leg inside a ruin or the mine, with run energy; the ticks taken."""
    ticks, energy = timed(state, [leg])  # walk_plan counts the changes of plane
    state.run_energy = energy
    return round(ticks)


def inside_ticks(rune: str) -> float:
    """The estimated ticks inside the ruins a trip: entering, the walks, crafting and leaving."""
    (to_altar, up), (to_portal, down) = INSIDE[rune]
    return ENTER_TICKS + _walk_estimate(to_altar, up) + CRAFT_TICKS + _walk_estimate(to_portal, down) + PORTAL_TICKS


@cache
def _bank_ticks_from(tile: tuple[int, int, int]) -> float:
    """The estimated ticks from a tile to the bank nearest it (rlscape.travel's estimate)."""
    return min((travel_ticks(tile, (b.x, b.y, b.plane)) for b in gd.banks()), default=inf)


def _arms(state: CharacterState) -> list[tuple[str, int]]:
    """The worn items Entrana's monks refuse (the travel model's rule: equipment with combat bonuses)."""
    items = gd.items()
    return [(slot, item) for slot, item in state.equipment.items()
            if item in items and items[item].equipment_slot is not None and any(items[item].bonuses)]


class RunecraftAtRuins(AtStation):
    """rc_<rune>: banked or carried essence crafted at the rune's altar, a load at a time, with its talisman."""

    family = "gathering"
    task = "runecrafting"
    skill = "runecrafting"

    def __init__(self, rune: str):
        self.rune, self.id = rcd.runes()[rune], f"rc_{rune}"
        self.ruins, self.talisman = rcd.ruins()[rune], rcd.talismans()[rune]
        self.station_kind = f"ruins:{rune}"

    def allowed(self, state: CharacterState) -> bool:
        return state.level("runecrafting") >= self.rune.level

    def _has_talisman(self, state: CharacterState) -> bool:
        return state.inventory.get(self.talisman, 0) > 0 or banked_or_noted(state, self.talisman) > 0

    def fare(self) -> int:
        return FARE_COINS.get(self.rune.name, 0)

    def held_units(self, state: CharacterState) -> int:
        """Essence the altar takes, carried, banked or noted, if a talisman and the fares are held too."""
        if not self._has_talisman(state) or state.coins() < self.fare():
            return 0
        return sum(state.inventory.get(e, 0) + banked_or_noted(state, e) for e in essence_kinds(self.rune))

    def station(self, state: CharacterState) -> gd.Station | None:
        """The ruins, if the character can get there as the path goes: for law, without the worn arms it banks; with
        the fares it takes."""
        probe = _unarmed_copy(state) if self.rune.name == "law" else state
        if self.fare() and probe.inventory.get(COINS, 0) < self.fare():
            from copy import copy
            probe = copy(probe)
            probe.inventory = {**probe.inventory, COINS: self.fare()}
        tile = self.ruins.base
        return gd.Station(self.station_kind, self.rune.name, tile, None, "") if isfinite(route_ticks(probe, tile)) \
            else None

    def available(self, state: CharacterState) -> bool:
        if not (self.allowed(state) and self.held_units(state) > 0):
            return False  # the cheap checks first: most states hold no essence
        bank = nearest_bank(state)
        return reachable(state, (bank.x, bank.y, bank.plane)) and self.station(state) is not None

    def _restock(self, state: CharacterState) -> None:
        """At the booth: bank everything but the essence and the talisman (law: the worn arms too), then take out the
        talisman and a load of one kind of essence, the first the altar takes that's held."""
        kinds = essence_kinds(self.rune)
        bank_notes(state, [*kinds, self.talisman])
        keep = {*kinds, self.talisman, *((COINS,) if self.fare() else ())}
        for item in [i for i in state.inventory if i not in keep]:
            state.bank[item] = state.bank.get(item, 0) + state.inventory.pop(item)
        short = self.fare() - state.inventory.get(COINS, 0)
        if short > 0 and state.bank.get(COINS, 0) >= short:
            state.take(COINS, short, state.bank)
            state.add(COINS, short)
        if self.rune.name == "law":
            for slot, item in _arms(state):
                del state.equipment[slot]
                state.bank[item] = state.bank.get(item, 0) + 1
        if state.inventory.get(self.talisman, 0) == 0 and state.bank.get(self.talisman, 0) > 0:
            state.take(self.talisman, 1, state.bank)
            state.add(self.talisman)
        kind = next((e for e in kinds if state.inventory.get(e, 0) + state.bank.get(e, 0) > 0), kinds[0])
        for other in kinds:  # one kind a load: the other goes back
            if other != kind and state.inventory.get(other, 0):
                state.bank[other] = state.bank.get(other, 0) + state.inventory.pop(other)
        take = min(state.free_slots(), state.bank.get(kind, 0))
        if take > 0:
            state.take(kind, take, state.bank)
            state.add(kind, take)

    def _loaded(self, state: CharacterState) -> bool:
        return state.inventory.get(self.talisman, 0) > 0 and any(state.inventory.get(e, 0) > 0
                                                                 for e in essence_kinds(self.rune))

    def _work(self, state: CharacterState, budget: int) -> OptionResult:
        """Enter, walk to the altar, craft the essence carried (one kind: getEssenceItem), walk to the portal, leave."""
        r, (to_altar, to_portal) = self.rune, INSIDE[self.rune.name]
        elapsed = ENTER_TICKS + _walk_inside(state, to_altar) + CRAFT_TICKS
        if elapsed > budget:
            return OptionResult(budget, COMPLETED)
        essence = next(e for e in essence_kinds(r) if state.inventory.get(e, 0) > 0)
        amount = state.inventory[essence]
        state.take(essence, amount)
        state.add(r.item, amount * r.per_essence(state.level("runecrafting")))
        crafting = SKILL_INDEX["runecrafting"]
        state.xp[crafting] = min(state.xp[crafting] + amount * r.experience, MAX_XP)
        elapsed += _walk_inside(state, to_portal) + PORTAL_TICKS
        state.location = self.ruins.base
        return OptionResult(min(elapsed, budget), INPUTS_EXHAUSTED)

    def rate(self, state: CharacterState, duration_ticks: int) -> tuple[float, float, float, float]:
        """(Runecrafting XP/hr, 0, gp/hr, travel) for the skilling slots: loads between the ruins and the bank nearest
        them, as many as the essence held makes, after the walk to the nearest bank. Its gp is the runes over the
        essence."""
        held, values, r = self.held_units(state), gd.item_values(), self.rune
        load = max(min(held, INVENTORY_SLOTS - 1), 1)
        bank = nearest_bank(state)
        travel = travel_ticks(state.location, (bank.x, bank.y, bank.plane)) + BANKING_TICKS
        cycle = 2 * _bank_ticks_from(self.ruins.base) + BANKING_TICKS + inside_ticks(r.name)
        loads = min(held / load, max(duration_ticks - travel, 0.0) / cycle) if isfinite(cycle) else 0.0
        per_hour = loads * load * TICKS_PER_HOUR / duration_ticks
        essence = next((e for e in essence_kinds(r) if state.inventory.get(e, 0) + banked_or_noted(state, e) > 0),
                       essence_kinds(r)[0])
        gain = r.per_essence(state.level("runecrafting")) * values.get(r.item, 0) - values.get(essence, 0)
        return per_hour * r.experience, 0.0, per_hour * gain, travel


def _unarmed_copy(state: CharacterState) -> CharacterState:
    """The character as law's path takes it to Entrana: carrying only its essence and talisman, the arms banked."""
    from copy import copy
    probe = copy(state)
    probe.inventory = {i: n for i, n in state.inventory.items() if i in inputs() or i == COINS}
    probe.equipment = dict(state.equipment)
    for slot, _ in _arms(state):
        del probe.equipment[slot]
    return probe


class MineEssence(Option):
    """mine_essence: to the nearest wizard, his teleport to the essence mine, mining to a full inventory, and the portal
    back to him."""

    family = "gathering"
    task = "mining"
    skill = "mining"

    def __init__(self):
        self.id = "mine_essence"

    def wizard(self, state: CharacterState) -> tuple[str, tuple[int, int, int]] | None:
        """The nearest wizard the character can reach: ranked by the travel estimate, the route planned only for the
        nearest (and the next if it can't be reached), as route planning is what a mask check costs."""
        wizards = rcd.essence_wizards()
        for name in sorted(SURFACE_WIZARDS, key=lambda n: travel_ticks(state.location, wizards[n][0])):
            if reachable(state, wizards[name][0]):
                return name, wizards[name][0]
        return None

    def available(self, state: CharacterState) -> bool:
        return state.free_slots() > 0 and best_pickaxe(state) is not None and self.wizard(state) is not None

    def essence(self, state: CharacterState) -> int:
        return rcd.PURE_ESSENCE if state.level("mining") >= rcd.PURE_ESSENCE_MINING else rcd.RUNE_ESSENCE

    def essence_ticks(self, state: CharacterState) -> int:
        tool = best_pickaxe(state)
        return rcd.essence_delays().get(tool.name, 4) + SCRIPT_WAIT_EXTRA

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        found = self.wizard(state)
        if found is None:
            return OptionResult(1, COMPLETED)
        _, home = found
        elapsed = walk(state, home, budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED)
        landings = rcd.essence_landings()
        to_rock, to_portal = MINE_WALKS[landings[rng.integers(len(landings))]]
        elapsed += TELEPORT_TICKS + _walk_inside(state, (to_rock, 0))
        mining, each, essence = SKILL_INDEX["mining"], self.essence_ticks(state), self.essence(state)
        while state.free_slots() > 0:
            if elapsed + each > budget:
                return OptionResult(budget, COMPLETED)
            elapsed += each
            state.add(essence)
            state.xp[mining] = min(state.xp[mining] + rcd.ESSENCE_XP, MAX_XP)
        elapsed += _walk_inside(state, (to_portal, 0)) + MINE_PORTAL_TICKS
        state.location = home
        return OptionResult(min(elapsed, budget), INVENTORY_FULL)

    def rate(self, state: CharacterState, duration_ticks: int) -> tuple[float, float, float, float]:
        """(Mining XP/hr, 0, gp/hr, travel): a load a trip, the mean of the landings' walks, and a bank trip from the
        wizard and back between loads."""
        found = self.wizard(state)
        if found is None or best_pickaxe(state) is None:
            return 0.0, 0.0, 0.0, inf
        _, home = found
        room = max(state.free_slots(), 1)
        walks = list(MINE_WALKS.values())
        inside = (TELEPORT_TICKS + sum(_walk_estimate(a) + _walk_estimate(b) for a, b in walks) / len(walks)
                  + MINE_PORTAL_TICKS)
        cycle = inside + room * self.essence_ticks(state) + 2 * _bank_ticks_from(home) + BANKING_TICKS
        travel = travel_ticks(state.location, home)
        units = max(duration_ticks - travel, 0.0) / cycle * room
        per_hour = units * TICKS_PER_HOUR / duration_ticks
        return per_hour * rcd.ESSENCE_XP, 0.0, per_hour * gd.item_values().get(self.essence(state), 0), travel


def runecrafting_paths() -> list[RunecraftAtRuins]:
    return [RunecraftAtRuins(rune) for rune in RC_RUNES]
