"""Runecrafting (sim v1; Caleb, 2026-11-08, OQ-2: "Runecrafting should add runes and essence"; Choice H: the tiaras
are in). The spec is docs/sim-v1-skills-draft.md §5, the server's data rlscape.gamedata.runecrafting.

Essence isn't mined (Caleb, 2026-11-08: "Rune essence is very cheap and mining it yourself will almost always be seen
as a time waste"): a character buys it, or takes it from drops.

The ruins:
- `rc_<rune>` (RunecraftAtRuins): at the nearest bank, bank everything but the essence and the way in, take out a load
  of essence; walk to the ruins; enter them, which lands the character beside the altar; walk to it and craft every
  essence carried at once (RuneCraftPulse); walk to the portal, which leaves by the ruins; again. The way in is the
  rune's tiara, worn (MysteriousRuinListener.handleTiaraOrStaff), when the character has one: it's put on at the bank,
  and the trip carries 28 essence. Otherwise the talisman, used on the ruins, carried, and 27 essence.
- Air to body take rune essence or pure, one kind a click (getEssenceItem: rune essence first), so a load is one kind,
  rune essence first; the rest take pure only.
- Law's ruins are on Entrana, whose monks refuse weapons and armour (the travel model's boat rule), so its path banks
  the worn ones too (a tiara isn't either).
- The runes: the nine whose ruins the travel model reaches (RC_RUNES). Cosmic's ruins are in Zanaris, which it doesn't:
  the cosmic altar is reached only by the Abyss's rift (Caleb, OQ-45 (a)). Death's altar is the Abyss's too, and astral
  and blood stay out (OQ-39).
- `make_tiara_<rune>` (MakeTiaraAtRuins): a plain tiara and the rune's talisman, used on its altar, make the rune's
  tiara for Runecrafting XP (TalismanEnchantingListener), one at a time, the talisman used up. A load is 14 pairs.
  The GE sells the tiaras themselves for 45 gp or so in January 2009 (water's 3,204), well under a talisman and a
  plain tiara, so the path is for the XP. A tiara takes 8 ticks (measured).
- Inside the ruins, the walk from the landing to the altar and from the altar to the portal is the pathfinder's steps
  on the server (debug_nearby, 2026-11-08), run as a step every half tick with run energy (walk_plan), with none of the
  start-of-walk overhead walks outside have: the clicks inside follow each other. Entering, crafting and leaving are
  measured on the server (scripts/calibrate_runecrafting.py, 2026-11-08), as is a tiara's making. Chaos's maze is an
  estimate, to measure.

The Abyss and its pouches come next (the draft's §5).
"""

from __future__ import annotations

from copy import copy
from functools import cache
from math import inf, isfinite

from rlscape.gamedata import runecrafting as rcd
from rlscape.gamedata import server as gd
from rlscape.sim.crafting import AtStation
from rlscape.sim.economy import bank_notes, banked_or_noted, nearest_bank
from rlscape.sim.energy import RUN_TILES, walk_plan
from rlscape.sim.movement import reachable, route_ticks
from rlscape.sim.options import COMPLETED, INPUTS_EXHAUSTED, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import COINS, INVENTORY_SLOTS, CharacterState
from rlscape.travel import BANKING_TICKS, LEVEL_CHANGE_TICKS, travel_ticks

TICKS_PER_HOUR = 6000
RC_RUNES = ("air", "mind", "water", "earth", "fire", "body", "chaos", "nature", "law")
# (steps from the landing to the altar, changes of plane; steps from beside the altar to the portal, changes): the
# pathfinder's on the server (debug_nearby, 2026-11-08). Chaos's altar is at the foot of a maze three floors down from
# the landing (2275, 4847, 3): an estimate, to measure.
INSIDE = {"air": ((4, 0), (4, 0)), "mind": ((12, 0), (12, 0)), "water": ((2, 0), (16, 0)),
          "earth": ((10, 0), (11, 0)), "fire": ((15, 0), (9, 0)), "body": ((5, 0), (5, 0)),
          "chaos": ((30, 3), (30, 3)), "nature": ((5, 0), (5, 0)), "law": ((12, 0), (13, 0))}
# Measured on the server (scripts/calibrate_runecrafting.py, 2026-11-08; 8 ruins, 2 runs each, run on):
ENTER_TICKS = 1  # beyond the walk to the ruins (whose timing has a start overhead): the talisman's 3-tick script
CRAFT_TICKS = 3  # the altar clicked, beside it, to the runes (RuneCraftPulse's first pulse)
PORTAL_TICKS = 5  # the runes to standing outside, beyond the walk: the altar's lock ending, the portal and its teleport
TIARA_TICKS = 8  # a tiara each, measured at the air altar (7.85; scripts/calibrate_runecrafting.py --tiaras): the
# enchanting script's 2-tick wait, then its 3-tick lock, which drops the next click until it's over
TIARA_LOAD = INVENTORY_SLOTS // 2  # 14 pairs of a plain tiara and a talisman
HAT = 0  # EquipmentContainer's hat slot, where a tiara is worn
# Coins a trip carries for its fares: nature's ruins are reached from Draynor's bank by the Karamja boat, 30 gp each
# way (the travel model's nearest bank to them; Shilo Village's walls keep its bank further, 535 ticks)
FARE_COINS = {"nature": 60}


def essence_kinds(rune: rcd.Rune) -> tuple[int, ...]:
    """The essence a rune's altar takes, in the order getEssenceItem crafts it."""
    return (rcd.PURE_ESSENCE,) if rune.pure_only else (rcd.RUNE_ESSENCE, rcd.PURE_ESSENCE)


def tiara_of(rune: str) -> int:
    return rcd.tiaras()[rune][0]


def inputs() -> frozenset[int]:
    """What a Runecrafting path carries or wears: essence, and for the runes it crafts (RC_RUNES) the talismans and
    tiaras, and plain tiaras."""
    talismans = rcd.talismans()
    return frozenset({rcd.RUNE_ESSENCE, rcd.PURE_ESSENCE, rcd.PLAIN_TIARA,
                      *(talismans[rune] for rune in RC_RUNES), *(tiara_of(rune) for rune in RC_RUNES)})


def _walk_inside(state: CharacterState, leg: tuple[int, int]) -> int:
    """Walk a leg inside a ruin, with run energy (walk_plan, which counts the changes of plane); the ticks taken."""
    ticks, energy = walk_plan(state, [leg])
    state.run_energy = energy
    return round(ticks)


def _inside_walks(rune: str) -> float:
    (to_altar, up), (to_portal, down) = INSIDE[rune]
    return (to_altar + to_portal) / RUN_TILES + (up + down) * LEVEL_CHANGE_TICKS


def inside_ticks(rune: str) -> float:
    """The ticks inside the ruins a trip, run energy full: entering, the walks, crafting and leaving."""
    return ENTER_TICKS + CRAFT_TICKS + PORTAL_TICKS + _inside_walks(rune)


@cache
def _bank_ticks_from(tile: tuple[int, int, int]) -> float:
    """The estimated ticks from a tile to the bank nearest it (rlscape.travel's estimate)."""
    return min((travel_ticks(tile, (b.x, b.y, b.plane)) for b in gd.banks()), default=inf)


def _arms(state: CharacterState) -> list[tuple[int, int]]:
    """The worn items Entrana's monks refuse (the travel model's rule: equipment with combat bonuses)."""
    items = gd.items()
    return [(slot, item) for slot, item in state.equipment.items()
            if item in items and items[item].equipment_slot is not None and any(items[item].bonuses)]


def _unarmed_copy(state: CharacterState) -> CharacterState:
    """The character as law's path takes it to Entrana: carrying only its runecrafting items, the arms banked."""
    probe = copy(state)
    probe.inventory = {i: n for i, n in state.inventory.items() if i in inputs() or i == COINS}
    probe.equipment = dict(state.equipment)
    for slot, _ in _arms(state):
        del probe.equipment[slot]
    return probe


def _held(state: CharacterState, item: int) -> int:
    """Carried, banked, noted or worn."""
    worn = sum(1 for i in state.equipment.values() if i == item)
    return state.inventory.get(item, 0) + banked_or_noted(state, item) + worn


def _bank(state: CharacterState, item: int, amount: int | None = None) -> None:
    amount = state.inventory.get(item, 0) if amount is None else amount
    if amount > 0:
        state.take(item, amount)
        state.bank[item] = state.bank.get(item, 0) + amount


def _withdraw(state: CharacterState, item: int, amount: int) -> None:
    take = min(amount, state.bank.get(item, 0))
    if take > 0:
        state.take(item, take, state.bank)
        state.add(item, take)


class RunecraftAtRuins(AtStation):
    """rc_<rune>: banked or carried essence crafted at the rune's altar, a load at a time, with its tiara worn or its
    talisman."""

    family = "gathering"
    task = "runecrafting"
    skill = "runecrafting"
    prefix = "rc"

    def __init__(self, rune: str):
        self.rune, self.id = rcd.runes()[rune], f"{self.prefix}_{rune}"
        self.ruins, self.talisman, self.tiara = rcd.ruins()[rune], rcd.talismans()[rune], tiara_of(rune)
        self.station_kind = f"ruins:{rune}"

    def allowed(self, state: CharacterState) -> bool:
        return state.level("runecrafting") >= self.rune.level

    def fare(self) -> int:
        return FARE_COINS.get(self.rune.name, 0)

    def _way_in(self, state: CharacterState) -> bool:
        return _held(state, self.tiara) > 0 or _held(state, self.talisman) > 0

    def held_units(self, state: CharacterState) -> int:
        """Essence the altar takes, carried, banked or noted, if a way in and the fares are held too."""
        if not self._way_in(state) or state.coins() < self.fare():
            return 0
        return sum(state.inventory.get(e, 0) + banked_or_noted(state, e) for e in essence_kinds(self.rune))

    def station(self, state: CharacterState) -> gd.Station | None:
        """The ruins, if the character can get there as the path goes: for law, without the worn arms it banks; with
        the fares it takes."""
        probe = _unarmed_copy(state) if self.rune.name == "law" else state
        if self.fare() and probe.inventory.get(COINS, 0) < self.fare():
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

    def _keep(self) -> set[int]:
        return {*essence_kinds(self.rune), self.talisman, self.tiara, *((COINS,) if self.fare() else ())}

    def _prepare(self, state: CharacterState) -> None:
        """At the booth: bank everything the path doesn't use (law: the worn arms too) and take out the fares."""
        bank_notes(state, [*self._keep(), rcd.PLAIN_TIARA])
        keep = self._keep()
        for item in [i for i in state.inventory if i not in keep]:
            _bank(state, item)
        short = self.fare() - state.inventory.get(COINS, 0)
        if short > 0 and state.bank.get(COINS, 0) >= short:
            _withdraw(state, COINS, short)
        if self.rune.name == "law":
            for slot, item in _arms(state):
                del state.equipment[slot]
                state.bank[item] = state.bank.get(item, 0) + 1

    def _wear_tiara(self, state: CharacterState) -> bool:
        """Put the rune's tiara on if it's held and not worn (what was on the head goes to the bank); whether it's
        worn."""
        if state.equipment.get(HAT) == self.tiara:
            return True
        if state.inventory.get(self.tiara, 0):
            state.take(self.tiara)
        elif state.bank.get(self.tiara, 0):
            state.take(self.tiara, 1, state.bank)
        else:
            return False
        old = state.equipment.get(HAT)
        if old is not None:
            state.bank[old] = state.bank.get(old, 0) + 1
        state.equipment[HAT] = self.tiara
        return True

    def _restock(self, state: CharacterState) -> None:
        """At the booth: wear the tiara, or take out the talisman, then a load of one kind of essence, the first the
        altar takes that's held."""
        self._prepare(state)
        if self._wear_tiara(state):
            _bank(state, self.talisman)  # the tiara lets it in: the slot carries essence
        elif state.inventory.get(self.talisman, 0) == 0:
            _withdraw(state, self.talisman, 1)
        else:
            _bank(state, self.talisman, state.inventory[self.talisman] - 1)
        kinds = essence_kinds(self.rune)
        kind = next((e for e in kinds if state.inventory.get(e, 0) + state.bank.get(e, 0) > 0), kinds[0])
        for other in kinds:  # one kind a load: the other goes back
            if other != kind:
                _bank(state, other)
        _withdraw(state, kind, state.free_slots())

    def _entering(self, state: CharacterState) -> bool:
        return state.equipment.get(HAT) == self.tiara or state.inventory.get(self.talisman, 0) > 0

    def _loaded(self, state: CharacterState) -> bool:
        return self._entering(state) and any(state.inventory.get(e, 0) > 0 for e in essence_kinds(self.rune))

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

    def _cycle(self, load: int) -> float:
        return 2 * _bank_ticks_from(self.ruins.base) + BANKING_TICKS + inside_ticks(self.rune.name)

    def rate(self, state: CharacterState, duration_ticks: int) -> tuple[float, float, float, float]:
        """(Runecrafting XP/hr, 0, gp/hr, travel) for the skilling slots: loads between the ruins and the bank nearest
        them, as many as the essence held makes, after the walk to the nearest bank. Its gp is the runes over the
        essence."""
        held, values, r = self.held_units(state), gd.item_values(), self.rune
        room = INVENTORY_SLOTS - (0 if _held(state, self.tiara) else 1)
        load = max(min(held, room), 1)
        bank = nearest_bank(state)
        travel = travel_ticks(state.location, (bank.x, bank.y, bank.plane)) + BANKING_TICKS
        cycle = self._cycle(load)
        loads = min(held / load, max(duration_ticks - travel, 0.0) / cycle) if isfinite(cycle) else 0.0
        per_hour = loads * load * TICKS_PER_HOUR / duration_ticks
        essence = next((e for e in essence_kinds(r) if state.inventory.get(e, 0) + banked_or_noted(state, e) > 0),
                       essence_kinds(r)[0])
        gain = r.per_essence(state.level("runecrafting")) * values.get(r.item, 0) - values.get(essence, 0)
        return per_hour * r.experience, 0.0, per_hour * gain, travel


class MakeTiaraAtRuins(RunecraftAtRuins):
    """make_tiara_<rune>: plain tiaras and the rune's talismans, used on its altar a pair at a time, into its tiaras."""

    prefix = "make_tiara"

    def allowed(self, state: CharacterState) -> bool:
        return True  # TalismanEnchantingListener asks no level, nor do the ruins

    def held_units(self, state: CharacterState) -> int:
        """Pairs of a plain tiara and a talisman, carried, banked or noted, if the fares are held too."""
        if state.coins() < self.fare():
            return 0
        return min(state.inventory.get(item, 0) + banked_or_noted(state, item)
                   for item in (rcd.PLAIN_TIARA, self.talisman))

    def _keep(self) -> set[int]:
        return {rcd.PLAIN_TIARA, self.talisman, *((COINS,) if self.fare() else ())}

    def _restock(self, state: CharacterState) -> None:
        """At the booth: a load of pairs (a talisman also lets the character in)."""
        self._prepare(state)
        pairs = min(TIARA_LOAD, *(state.inventory.get(i, 0) + state.bank.get(i, 0)
                                  for i in (rcd.PLAIN_TIARA, self.talisman)))
        for item in (rcd.PLAIN_TIARA, self.talisman):
            extra = state.inventory.get(item, 0) - pairs
            if extra > 0:
                _bank(state, item, extra)
            else:
                _withdraw(state, item, -extra)

    def _loaded(self, state: CharacterState) -> bool:
        return state.inventory.get(rcd.PLAIN_TIARA, 0) > 0 and state.inventory.get(self.talisman, 0) > 0

    def _work(self, state: CharacterState, budget: int) -> OptionResult:
        """Enter, walk to the altar, make a tiara of each pair carried, walk to the portal, leave."""
        (to_altar, to_portal), xp = INSIDE[self.rune.name], rcd.tiaras()[self.rune.name][1]
        elapsed = ENTER_TICKS + _walk_inside(state, to_altar)
        crafting = SKILL_INDEX["runecrafting"]
        while state.inventory.get(rcd.PLAIN_TIARA, 0) > 0 and state.inventory.get(self.talisman, 0) > 0:
            if elapsed + TIARA_TICKS > budget:
                return OptionResult(budget, COMPLETED)
            elapsed += TIARA_TICKS
            state.take(rcd.PLAIN_TIARA)
            state.take(self.talisman)
            state.add(self.tiara)
            state.xp[crafting] = min(state.xp[crafting] + xp, MAX_XP)
        elapsed += _walk_inside(state, to_portal) + PORTAL_TICKS
        state.location = self.ruins.base
        return OptionResult(min(elapsed, budget), INPUTS_EXHAUSTED)

    def _cycle(self, load: int) -> float:
        return (2 * _bank_ticks_from(self.ruins.base) + BANKING_TICKS + ENTER_TICKS + _inside_walks(self.rune.name)
                + load * TIARA_TICKS + PORTAL_TICKS)

    def rate(self, state: CharacterState, duration_ticks: int) -> tuple[float, float, float, float]:
        """(Runecrafting XP/hr, 0, gp/hr, travel): loads of pairs between the ruins and the bank nearest them. Its gp is
        the tiaras over the plain tiaras and talismans, a loss at 2009 prices."""
        held, values = self.held_units(state), gd.item_values()
        load = max(min(held, TIARA_LOAD), 1)
        bank = nearest_bank(state)
        travel = travel_ticks(state.location, (bank.x, bank.y, bank.plane)) + BANKING_TICKS
        cycle = self._cycle(load)
        loads = min(held / load, max(duration_ticks - travel, 0.0) / cycle) if isfinite(cycle) else 0.0
        per_hour = loads * load * TICKS_PER_HOUR / duration_ticks
        gain = values.get(self.tiara, 0) - values.get(rcd.PLAIN_TIARA, 0) - values.get(self.talisman, 0)
        return per_hour * rcd.tiaras()[self.rune.name][1], 0.0, per_hour * gain, travel


def runecrafting_paths() -> list[RunecraftAtRuins]:
    return [*(RunecraftAtRuins(rune) for rune in RC_RUNES), *(MakeTiaraAtRuins(rune) for rune in RC_RUNES)]
