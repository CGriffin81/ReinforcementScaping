"""Inventory and alchemy options (option catalog §5–§6): banking, dropping and alchemy.

These run once: walk if needed, then the transaction. The per-item actions (drop_<item>, high_alch_<item>, ...) are
built for whatever item vocabulary *V* is passed in; the catalog's V is still to be checked by Caleb, so until then
the catalog carries only the "misc" actions, which act on every item outside V.

Mechanics:
- bank_deposit: walk to the nearest bank (data/banks.csv) and deposit everything except tools, food, ammunition,
  runes and fishing bait (the catalog's list, with bait counted as an activity's ammunition). Banknotes go in as
  their items. Banking costs BANKING_TICKS (rlscape.travel; calibrate).
- bank_deposit_worn: walk to the nearest bank and bank the worn gear (the banker's "deposit worn items",
  BankDepositDialogue), keeping what bank_deposit keeps, so a worn axe or pickaxe stays on. Lighter, the character
  runs further on its energy (rlscape.sim.energy).
- bank_withdraw_for_<activity>: walk to the nearest bank and withdraw what one processing activity needs, up to a
  full inventory: its tool if it isn't held (hammer, tinderbox), then its inputs in the right proportions. Banknotes
  of the inputs held (from GE buys) are banked first, as a player would at the booth.
- drop_<item> / drop_misc: drop every unit; dropped items leave net worth (env contract §4). DROP_TICKS a unit, a
  stack at once; calibrate.
- alchemy (ModernListeners.alchemize): low alchemy needs Magic 21, 3 fire runes and a nature rune and gives 31 XP;
  high alchemy needs Magic 55, 5 fire runes and a nature rune and gives 65 XP. A fire staff (MagicStaff.FIRE_RUNE)
  stands in for the fire runes. Each cast turns one item into its alchemy value in coins and takes 5 ticks
  (setDelay(player, 5)). Coins can't be alched; only items the server lets you alch (tradeable ones) are.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from rlscape.gamedata import server as gd
from rlscape.sim.kits import GATHERING_TOOLS, kit
from rlscape.sim.energy import weight
from rlscape.sim.movement import reachable, route_ticks, toll_exempt, walk
from rlscape.sim.options import COMPLETED, INPUTS_EXHAUSTED, Option, OptionResult
from rlscape.sim.processing import HAMMER, TINDERBOX
from rlscape.sim.shops import PLAYER_STOCK, set_stock, stock
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import COINS, CharacterState
from rlscape.sim.transport import home_ready, usable_teleports
from rlscape.sim.woodcutting import best_tool
from rlscape.travel import BANKING_TICKS

DROP_TICKS = 1  # per unit dropped (a stack drops at once); calibrate
ALCH_TICKS = 5  # ModernListeners.alchemize: setDelay(player, 5)
NATURE_RUNE, FIRE_RUNE = 561, 554
AMMO_SLOT = 13  # EquipmentContainer.SLOT_ARROWS
WEAPON_SLOT = 3  # EquipmentContainer.SLOT_WEAPON
ALCHEMY = {True: (55, 5, 65.0), False: (21, 3, 31.0)}  # high?: (Magic level, fire runes, XP), ModernListeners


def kept_on_deposit(item: int) -> bool:
    """Tools, food, potions (any dose: OQ-25), ammunition, runes and fishing bait stay in the inventory when banking."""
    items, tools = gd.items(), {t.item for t in gd.skilling_tools().values()}
    fishing = {m.tool for m in gd.fishing_methods().values()} | {b for m in gd.fishing_methods().values() for b in m.bait}
    definition = items.get(item)
    from rlscape.sim.potions import DOSES  # imported here: potions imports health, which the economy's users import
    return (item in tools or item in fishing or item in (HAMMER, TINDERBOX, gd.KNIFE) or item in gd.food_healing()
            or item in DOSES
            or (definition is not None and (definition.equipment_slot == AMMO_SLOT
                                            or definition.name.lower().endswith(" rune"))))


def is_misc(item: int, vocabulary: frozenset[int]) -> bool:
    """Outside V, and not something the misc actions should ever touch (coins, or what banking keeps)."""
    return item not in vocabulary and item != COINS and not kept_on_deposit(item)


_NEAREST_BANK: dict[tuple, gd.Bank] = {}
NEAREST_BANK_CACHE = 4096


def nearest_bank(state: CharacterState) -> gd.Bank:
    """The bank with the shortest walk. Every option that banks asks, and a mask asks once per Fletching path, so it's
    cached on everything route_ticks depends on: the tile, the coins carried (the Al Kharid toll, the Shantay pass,
    fares), whether Prince Ali Rescue waives the toll, run energy, weight and Agility, the teleports it can use and
    whether the home teleport is ready, and quests (boats). Not whether Entrana's monks would let it board: that only
    matters on Entrana, which has no bank."""
    key = (state.location, state.inventory.get(COINS, 0), toll_exempt(state), state.run_energy, weight(state),
           state.level("agility"), usable_teleports(state), home_ready(state), state.progress.quests_complete)
    bank = _NEAREST_BANK.get(key)
    if bank is None:
        if len(_NEAREST_BANK) >= NEAREST_BANK_CACHE:
            _NEAREST_BANK.clear()
        bank = _NEAREST_BANK[key] = min(gd.banks(), key=lambda b: route_ticks(state, (b.x, b.y, b.plane)))
    return bank


def bank_trip(state: CharacterState, budget: int) -> int | None:
    """Walk to the nearest bank and open it; the ticks taken, or None if the budget runs out first."""
    bank = nearest_bank(state)
    walked = walk(state, (bank.x, bank.y, bank.plane), budget)
    if walked is None or walked + BANKING_TICKS > budget:
        return None
    return walked + BANKING_TICKS


def bank_notes(state: CharacterState, items: Iterable[int]) -> None:
    """At the booth: bank the banknotes held of these items, which go in as the items."""
    noted = gd.noted_ids()
    for item in items:
        note = noted.get(item)
        if note in state.inventory:
            amount = state.inventory[note]
            state.take(note, amount)
            state.bank[item] = state.bank.get(item, 0) + amount


def banked_or_noted(state: CharacterState, item: int) -> int:
    """Units in the bank, plus banknotes held that a withdrawal banks first."""
    return state.bank.get(item, 0) + state.inventory.get(gd.noted_ids().get(item), 0)


def note_slots(state: CharacterState, items: Iterable[int]) -> int:
    """Inventory slots that banking these items' banknotes frees."""
    noted = gd.noted_ids()
    return sum(1 for item in items if noted.get(item) in state.inventory)


class BankDeposit(Option):
    family = "inventory"

    def __init__(self, option_id: str = "bank_deposit"):
        self.id = option_id

    def available(self, state: CharacterState) -> bool:
        keep = kit(state, state.task)
        return any(item not in keep for item in state.inventory)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        ticks = bank_trip(state, budget)
        if ticks is None:
            return OptionResult(budget, COMPLETED)
        keep, unnoted = kit(state, state.task), gd.unnoted_ids()
        for item, amount in list(state.inventory.items()):
            if item not in keep:
                state.take(item, amount)
                real = unnoted.get(item, item)
                state.bank[real] = state.bank.get(real, 0) + amount
        return OptionResult(ticks, COMPLETED)


class BankWithdrawKit(Option):
    """bank_withdraw_for_<task> for a gathering task: walk to the nearest bank and take out its kit (rlscape.sim.kits):
    for woodcutting and mining, the best axe or pickaxe the level allows, if none as good is held (woodcutting also
    a tinderbox and a knife, if not held); for a fishing method, its tool and all of its bait or feathers."""

    family = "inventory"

    def __init__(self, key: str, task: str):
        self.id, self.kit_task = f"bank_withdraw_for_{key}", task

    def _wanted(self, state: CharacterState) -> list[tuple[int, int]]:
        """(item, amount) to take out of the bank."""
        kind, _, method = self.kit_task.partition(":")
        if kind in GATHERING_TOOLS:
            priority, held = GATHERING_TOOLS[kind], best_tool(state, GATHERING_TOOLS[kind], kind)
            rank = lambda tool: priority.index(tool.name)  # SkillingTool's order: best first
            best = next((tool for tool in _banked_tools(state, kind) if held is None or rank(tool) < rank(held)), None)
            wanted = [(best.item, 1)] if best is not None else []
            if kind == "woodcutting":  # the chop-and-burn and chop-and-fletch paths' tinderbox and knife
                wanted += [(tool, 1) for tool in (TINDERBOX, gd.KNIFE)
                           if not state.holds(tool) and state.bank.get(tool, 0) > 0]
            return wanted
        fishing = gd.fishing_methods()[method]
        wanted = [(fishing.tool, 1)] if not state.inventory.get(fishing.tool) and state.bank.get(fishing.tool) else []
        return wanted + [(bait, state.bank[bait]) for bait in fishing.bait if state.bank.get(bait, 0) > 0]

    def available(self, state: CharacterState) -> bool:
        wanted = self._wanted(state)
        new_slots = sum(1 for item, _ in wanted if item not in state.inventory)
        return bool(wanted) and new_slots <= state.free_slots()

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        ticks = bank_trip(state, budget)
        if ticks is None:
            return OptionResult(budget, COMPLETED)
        for item, amount in self._wanted(state):
            added = state.add(item, amount)
            if added:
                state.take(item, added, state.bank)
        return OptionResult(ticks, COMPLETED)


def _banked_tools(state: CharacterState, skill: str) -> list[gd.SkillingTool]:
    """Banked tools for a gathering skill that its level allows, best first."""
    tools, level = gd.skilling_tools(), state.level(skill)
    return [tools[name] for name in GATHERING_TOOLS[skill]
            if level >= tools[name].level and state.bank.get(tools[name].item, 0) > 0]


GATHERING_KITS = {"woodcutting": "woodcutting", "mining": "mining", "fish_shrimp": "fishing:SMALL_NET",
                  "fish_fly": "fishing:LURE", "fish_lobster": "fishing:LOBSTER_CAGE"}  # withdrawal key -> task


class BankDepositWorn(Option):
    family = "inventory"

    def __init__(self, option_id: str = "bank_deposit_worn"):
        self.id = option_id

    def available(self, state: CharacterState) -> bool:
        return any(not kept_on_deposit(item) for item in state.equipment.values())

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        ticks = bank_trip(state, budget)
        if ticks is None:
            return OptionResult(budget, COMPLETED)
        for slot, item in list(state.equipment.items()):
            if not kept_on_deposit(item):
                state.bank[item] = state.bank.get(item, 0) + state.worn(slot)
                del state.equipment[slot]
                state.worn_amounts.pop(slot, None)
        return OptionResult(ticks, COMPLETED)


def _raw_foods() -> frozenset[int]:
    foods = gd.food_healing()
    return frozenset(raw for raw, c in gd.cookables().items() if c.cooked in foods)


# activity -> (tools to have, inputs). Inputs are either fixed proportions ((item, amount), ...) or a set of
# interchangeable items (any of them, one slot each).
WITHDRAW_RECIPES = {
    "smelt_bronze": ((), ((436, 1), (438, 1))),
    "smelt_iron": ((), ((440, 1),)),
    "smelt_steel": ((), ((453, 2), (440, 1))),
    "smith_bronze": ((HAMMER,), ((2349, 1),)),
    "smith_iron": ((HAMMER,), ((2351, 1),)),
    "smith_steel": ((HAMMER,), ((2353, 1),)),
    "smith_mithril": ((HAMMER,), ((2359, 1),)),
    "cook_fish": ((TINDERBOX,), "raw_food"),
    "burn_logs": ((TINDERBOX,), "logs"),
    "bury_bones": ((), "bones"),
}


class BankWithdraw(Option):
    family = "inventory"

    def __init__(self, activity: str):
        self.id = f"bank_withdraw_for_{activity}"
        self.activity = activity
        self.tools, self.inputs = WITHDRAW_RECIPES[activity]

    def _interchangeable(self) -> frozenset[int]:
        return {"raw_food": _raw_foods(), "logs": frozenset(gd.log_types()),
                "bones": frozenset(gd.bone_experience())}[self.inputs]

    def _input_items(self) -> frozenset[int]:
        return self._interchangeable() if isinstance(self.inputs, str) else frozenset(i for i, _ in self.inputs)

    def _usable(self, state: CharacterState, item: int) -> bool:
        """Whether the level lets the activity use an interchangeable input (logs to burn, raw food to cook)."""
        if self.inputs == "logs":
            return gd.log_types()[item][0] <= state.level("firemaking")
        if self.inputs == "raw_food":
            return gd.cookables()[item].level <= state.level("cooking")
        return True

    def available(self, state: CharacterState) -> bool:
        if isinstance(self.inputs, str):
            in_bank = any(banked_or_noted(state, item) > 0 and self._usable(state, item)
                          for item in self._interchangeable())
            need = 1
        else:
            in_bank = all(banked_or_noted(state, item) >= amount for item, amount in self.inputs)
            need = sum(amount for _, amount in self.inputs)
        missing_tools = sum(1 for tool in self.tools if not state.holds(tool))
        tools_ok = all(state.holds(tool) or state.bank.get(tool, 0) > 0 for tool in self.tools)
        free = state.free_slots() + note_slots(state, self._input_items())
        return in_bank and tools_ok and free >= need + missing_tools

    def _withdraw(self, state: CharacterState, item: int, amount: int) -> None:
        state.take(item, amount, state.bank)
        state.add(item, amount)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        ticks = bank_trip(state, budget)
        if ticks is None:
            return OptionResult(budget, COMPLETED)
        bank_notes(state, self._input_items())
        for tool in self.tools:
            if not state.holds(tool) and state.bank.get(tool, 0) > 0:
                self._withdraw(state, tool, 1)
        if isinstance(self.inputs, str):
            if self.activity == "cook_fish" and not any(item in gd.log_types() for item in state.inventory):
                log = next((item for item in gd.log_types() if state.bank.get(item, 0) > 0), None)
                if log is not None and state.free_slots() > 1:
                    self._withdraw(state, log, 1)  # one log makes the fire to cook on (rlscape.sim.processing.Cook)
            usable = (i for i in self._interchangeable() if self._usable(state, i))  # the level allows it
            for item in sorted(usable, key=lambda i: -gd.item_values().get(i, 0)):
                take = min(state.bank.get(item, 0), state.free_slots())
                if take:
                    self._withdraw(state, item, take)
        else:
            per_unit = sum(amount for _, amount in self.inputs)
            units = min([state.free_slots() // per_unit] + [state.bank[item] // amount for item, amount in self.inputs])
            for item, amount in self.inputs:
                self._withdraw(state, item, units * amount)
        return OptionResult(ticks, COMPLETED)


def _drop(state: CharacterState, item: int) -> int:
    """Drop every unit of an item; the ticks it takes."""
    amount = state.inventory[item]
    state.take(item, amount)
    state.dropped[item] = state.dropped.get(item, 0) + amount
    return DROP_TICKS if item in gd.stackable_items() else DROP_TICKS * amount


class Drop(Option):
    family = "inventory"

    def __init__(self, item: int):
        self.id = f"drop_{item}"
        self.item = item

    def available(self, state: CharacterState) -> bool:
        return state.inventory.get(self.item, 0) > 0

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        return OptionResult(min(_drop(state, self.item), budget), COMPLETED)


class DropMisc(Option):
    family = "inventory"

    def __init__(self, vocabulary: frozenset[int]):
        self.id = "drop_misc"
        self.vocabulary = vocabulary

    def available(self, state: CharacterState) -> bool:
        return any(is_misc(item, self.vocabulary) for item in state.inventory)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        ticks = sum(_drop(state, item) for item in [i for i in state.inventory if is_misc(i, self.vocabulary)])
        return OptionResult(min(max(ticks, 1), budget), COMPLETED)


def can_cast_alchemy(state: CharacterState, high: bool) -> bool:
    level, fire_runes, _ = ALCHEMY[high]
    staff = state.equipment.get(WEAPON_SLOT) in gd.fire_staves()
    return (state.level("magic") >= level and state.inventory.get(NATURE_RUNE, 0) >= 1
            and (staff or state.inventory.get(FIRE_RUNE, 0) >= fire_runes))


def alchable(item: int) -> bool:
    return item != COINS and item in gd.alchemy_values()


class Alch(Option):
    """Cast high or low alchemy on every unit of the target items, one cast at a time."""

    family = "alchemy"

    def __init__(self, high: bool, item: int | None = None, vocabulary: frozenset[int] = frozenset()):
        self.high, self.item, self.vocabulary = high, item, vocabulary
        kind = "high_alch" if high else "low_alch"
        self.id = f"{kind}_{item}" if item is not None else f"{kind}_misc"

    def _targets(self, state: CharacterState) -> list[int]:
        if self.item is not None:
            return [self.item] if state.inventory.get(self.item, 0) > 0 and alchable(self.item) else []
        return [i for i in state.inventory if alchable(i) and is_misc(i, self.vocabulary)]

    def available(self, state: CharacterState) -> bool:
        return can_cast_alchemy(state, self.high) and bool(self._targets(state))

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        _, fire_runes, xp = ALCHEMY[self.high]
        magic, elapsed = SKILL_INDEX["magic"], 0
        while True:
            targets = self._targets(state)
            if not targets or not can_cast_alchemy(state, self.high):
                return OptionResult(max(elapsed, 1), INPUTS_EXHAUSTED)
            if elapsed + ALCH_TICKS > budget:
                return OptionResult(budget, COMPLETED)
            item = targets[0]
            coins = gd.alchemy_values()[item][0 if self.high else 1]
            if coins and COINS not in state.inventory and state.inventory[item] > 1 and state.free_slots() == 0:
                return OptionResult(max(elapsed, 1), INPUTS_EXHAUSTED)  # "Not enough space in your inventory!"
            elapsed += ALCH_TICKS
            state.take(item)
            if coins:
                state.add(COINS, coins)
            state.take(NATURE_RUNE)
            if state.equipment.get(WEAPON_SLOT) not in gd.fire_staves():
                state.take(FIRE_RUNE, fire_runes)
            state.xp[magic] = min(state.xp[magic] + xp, MAX_XP)


PICKUP_TICKS = 1  # taking an item off the ground; calibrate


class TakeSpawn(Option):
    """take_<item>: walk to the nearest reachable spawn of an item (the server's ground spawns) and pick it up.
    Offered while none is held anywhere and a slot is free. The knife's (Caleb, 2026-10-31: "a knife spawn in
    Lumbridge Castle, which is very convenient for a fresh starting character") are in and beside Lumbridge Castle.
    The respawn (80 ticks for the knife) isn't tracked: with one held the action is masked, and getting rid of it
    first takes longer than that."""

    family = "inventory"

    def __init__(self, item: int, name: str):
        self.id, self.item = f"take_{name}", item

    def _nearest(self, state: CharacterState) -> tuple[int, int, int] | None:
        tiles = [tile for tile, _ in gd.ground_spawns(self.item) if reachable(state, tile)]
        return min(tiles, key=lambda tile: route_ticks(state, tile), default=None)

    def available(self, state: CharacterState) -> bool:
        return not state.holds(self.item) and self.item not in state.bank and state.free_slots() > 0 and bool(
            gd.ground_spawns(self.item))

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        tile = self._nearest(state)
        walked = None if tile is None else walk(state, tile, budget)
        if walked is None or walked + PICKUP_TICKS > budget:
            return OptionResult(budget, COMPLETED)
        state.add(self.item)
        return OptionResult(walked + PICKUP_TICKS, COMPLETED)


def inventory_options(vocabulary: Iterable[int] = ()) -> list[Option]:
    """Catalog §5–§6 for a given vocabulary: the deposits, the processing withdrawals, drops, and alchemy. With an
    empty vocabulary only the misc actions exist."""
    v = frozenset(vocabulary)
    return [BankDeposit(), BankDepositWorn(), *(BankWithdraw(activity) for activity in WITHDRAW_RECIPES),
            *(BankWithdrawKit(key, task) for key, task in GATHERING_KITS.items()), TakeSpawn(gd.KNIFE, "knife"),
            *(Drop(item) for item in sorted(v)), DropMisc(v),
            *(Alch(True, item) for item in sorted(v)), *(Alch(False, item) for item in sorted(v)),
            Alch(True, vocabulary=v), Alch(False, vocabulary=v)]


# --- Selling (option catalog §7) -------------------------------------------------------------------------------------

GE_TILE = (3164, 3487, 0)  # the GE bank tile in data/banks.csv (ScriptAPI's GE tile is 3165, 3487)
GE_TICKS = 8  # placing a sell offer and collecting the coins; calibrate
STORE_TICKS = 3  # opening the shop and selling; calibrate
OVERSTOCK_STEP = 0.03  # Shop.getGPSell: value * 0.03 off per unit of overstock, at most 10 units


def _real(item: int) -> int:
    return gd.unnoted_ids().get(item, item)


def _item_and_note(item: int) -> list[int]:
    """A per-item sell action sells the item and its banknotes (from GE buys or bank_withdraw_for_sale)."""
    note = gd.noted_ids().get(item)
    return [item] if note is None else [item, note]


def store_sale_value(item: int, units: int, already_overstocked: int = 0) -> int:
    """Shop.sell for coins: the first unit at getGPSell's price, each further one with one more unit of overstock.
    `already_overstocked` is the store's stock of the item less its normal amount (rlscape.sim.shops; the player
    stock's normal is 0); below normal, a unit sells at the full price. Never below 1 coin a unit."""
    real = _real(item)
    base, value = gd.alchemy_values().get(real, (0, 0))[1], gd.item_base_values().get(real, 0)
    return sum(max(round(base - value * OVERSTOCK_STEP * min(max(already_overstocked + k, 0), 10)), 1)
               for k in range(units))


def general_store(name: str) -> gd.Shop:
    """The shops.json entry for a general store in data/stations.csv."""
    return next(s for s in gd.shops().values() if s.title == f"{name} General Store")


class SellGE(Option):
    """Walk to the GE and sell every unit of the targets; the frozen buyer pays the 2009 price for items that have
    one (GE-blocked items never sell)."""

    family = "selling"

    def __init__(self, item: int | None = None, vocabulary: frozenset[int] = frozenset()):
        self.item, self.vocabulary = item, vocabulary
        self.id = f"sell_ge_{item}" if item is not None else "sell_ge_misc"

    def _targets(self, state: CharacterState) -> list[int]:
        prices = gd.ge_prices_2009()
        candidates = _item_and_note(self.item) if self.item is not None else [
            i for i in state.inventory if is_misc(_real(i), self.vocabulary)]
        return [i for i in candidates if state.inventory.get(i, 0) > 0 and _real(i) in prices]

    def available(self, state: CharacterState) -> bool:
        return bool(self._targets(state))

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        walked = walk(state, GE_TILE, budget)
        if walked is None or walked + GE_TICKS > budget:
            return OptionResult(budget, COMPLETED)
        prices = gd.ge_prices_2009()
        for item in self._targets(state):
            amount = state.inventory[item]
            state.take(item, amount)
            state.add(COINS, prices[_real(item)] * amount)
        return OptionResult(walked + GE_TICKS, COMPLETED)


class SellStore(Option):
    """Walk to the nearest general store and sell every unit of the targets at low-alchemy value minus overstock.
    The overstock is the store's tracked stock (rlscape.sim.shops): its own stock for items it sells, otherwise the
    player stock all general stores share."""

    family = "selling"

    def __init__(self, item: int | None = None, vocabulary: frozenset[int] = frozenset()):
        self.item, self.vocabulary = item, vocabulary
        self.id = f"sell_store_{item}" if item is not None else "sell_store_misc"

    def _targets(self, state: CharacterState) -> list[int]:
        tradeable = gd.alchemy_values()
        candidates = _item_and_note(self.item) if self.item is not None else [
            i for i in state.inventory if is_misc(_real(i), self.vocabulary)]
        return [i for i in candidates if state.inventory.get(i, 0) > 0 and _real(i) in tradeable]

    def available(self, state: CharacterState) -> bool:
        return bool(self._targets(state))

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        store = min((s for s in gd.stations() if s.kind == "general_store"), key=lambda s: route_ticks(state, s.tile))
        walked = walk(state, store.tile, budget)
        if walked is None or walked + STORE_TICKS > budget:
            return OptionResult(budget, COMPLETED)
        shop, now = general_store(store.name), state.tick + walked
        for item in self._targets(state):
            amount, real = state.inventory[item], _real(item)
            key = shop.id if real in shop.stock else PLAYER_STOCK
            normal = shop.stock[real][0] if key == shop.id else 0
            held = stock(state, key, real, now)
            state.take(item, amount)
            state.add(COINS, store_sale_value(item, amount, held - normal))
            set_stock(state, key, real, held + amount, now)
        return OptionResult(walked + STORE_TICKS, COMPLETED)


def selling_options(vocabulary: Iterable[int] = ()) -> list[Option]:
    """Catalog §7 for a given vocabulary; with an empty vocabulary only the misc actions exist."""
    v = frozenset(vocabulary)
    return [*(SellGE(item) for item in sorted(v)), SellGE(vocabulary=v),
            *(SellStore(item) for item in sorted(v)), SellStore(vocabulary=v)]
