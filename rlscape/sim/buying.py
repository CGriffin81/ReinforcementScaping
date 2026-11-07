"""Buying (option catalog §8): one action per item and source, and the bank withdrawals for bought gear and food.
Q1–Q9 below are Caleb's buying decisions of 2026-10-29 and 30, in docs/decision-log.md.

Sources, from the server:
- buy_ge_<item>: the GE's frozen seller (GrandExchange.buyFromFrozenSeller) fills a buy at once, at the 2009 price,
  from unlimited supply and with no buy limit. The fork's ge_collect hands it over as a player collects it (Q2):
  more than one of an item that has a banknote comes as banknotes; a single item or a stack (runes, arrows, bait,
  feathers) comes as itself; a single item comes as a banknote when there is no room for it.
- buy_shop_<item>: the one shop the catalog lists for the item (rlscape.sim.shops for stock and prices). Items land in
  the inventory as items, up to the stock and the free slots.

How a buy works:
- Amount (Q1): as many as the coins allow, up to the item's lot (Q1, and the lots Caleb set on 2026-10-29).
- Paying: coins in the inventory pay first. If they're short, the trip starts with a bank stop to withdraw the rest.
  The GE has bankers beside it, so there the stop costs only the banking.
- Timing: the walk, then GE_TICKS at the GE or STORE_TICKS at a shop (the selling constants; calibrate).
- Mask (Q4): the character can afford one unit (coins in the inventory and the bank, and the bank's can reach the
  inventory: onto coins carried or into a free slot), can use the item now (wear
  requirements and quest locks; a tool's skill level; arrows' Ranged level), it's an upgrade over anything held for
  its role (gear, tools, bows and weapons only), there's room (a free slot, unless it stacks onto one held) and, at
  a shop, it's in stock.

Withdrawals (Q3a, Q6):
- bank_withdraw_gear_<class>: walk to the nearest bank and take out the gear that beats what the character carries
  for a combat class: the weapon (ranged: with its ammunition), then armour, the biggest defence gain first. Fights
  still wield from the inventory (rlscape.sim.equipment.wield_best).
- bank_withdraw_<food>: walk to the nearest bank and take out one GE food tier, filling the free slots.

Agent choices (reversible, for Caleb's review):
- "Held", for the upgrade check, means usable now, wherever it is (worn, in the inventory or the bank). A fishing
  tool, the hammer or a staff counts as an upgrade unless the same item is held.
- The coins withdrawn are exactly the shortfall (plus the Al Kharid toll if the last leg crosses the gate). A shop
  trip's bank stop is the bank with the shortest walk overall.
- The withdrawals bank the banknotes held of what they withdraw first, as a player would at the booth.
- No shield is withdrawn behind a two-handed weapon.
"""

from __future__ import annotations

from math import inf

import numpy as np

from rlscape.combat.candidates import ANTI_DRAGON_SHIELD, DRAGONFIRE_PROTECTION
from rlscape.gamedata import server as gd
from rlscape.sim.economy import (GE_TICKS, GE_TILE, STORE_TICKS, bank_notes, bank_trip, banked_or_noted,
                                 kept_on_deposit)
from rlscape.sim.equipment import (
    ARMOUR_SLOTS,
    AVAS_DEVICES,
    CAPE,
    SHIELD,
    WEAPON,
    best_device,
    can_wear,
    defence_score,
    hinders,
    kit_score,
    leaves_off,
    ranged_kits,
    weapon_score,
)
from rlscape.sim.mining import PICKAXE_PRIORITY
from rlscape.sim.movement import TOLL, pays_toll, route_ticks, walk
from rlscape.sim.options import COMPLETED, Option, OptionResult
from rlscape.sim.potions import ANTIFIRE, FOUR_DOSES
from rlscape.sim.processing import HAMMER
from rlscape.sim.shops import affordable_units, purchase_cost, set_stock, stock, unit_price
from rlscape.sim.state import COINS, CharacterState
from rlscape.sim.woodcutting import HATCHET_PRIORITY
from rlscape.travel import BANKING_TICKS, travel_ticks

AXES = (1349, 1353, 1355, 1357, 1359)  # iron, steel, mithril, adamant, rune
PICKAXES = (1267, 1269, 1273, 1271, 1275)  # iron, steel, mithril, adamant, rune
FISHING_TOOLS = (307, 309, 311, 301)  # fishing rod, fly fishing rod, harpoon, lobster pot
BAIT_AND_FEATHERS = (313, 314)
SCIMITARS = (1323, 1325, 1329, 1331, 1333)  # iron, steel, mithril, adamant, rune
ARMOUR = (1153, 1115, 1067, 1191,  # iron full helm, platebody, platelegs, kiteshield
          1157, 1119, 1069, 1193,  # steel
          1159, 1121, 1071, 1197,  # mithril
          1161, 1123, 1073, 1199,  # adamant
          1163, 1127, 1079, 1201)  # rune (the platebody needs Dragon Slayer)
SHORTBOWS = (843, 849, 853)  # oak, willow, maple
ARROWS = (882, 884, 886, 888, 890)  # bronze, iron, steel, mithril, adamant
RUNES = (556, 555, 557, 554, 558, 562, 560, 561)  # air, water, earth, fire, mind, chaos, death, nature
STAVES = (1381, 1383, 1385, 1387)  # staff of air, water, earth, fire
FOOD_TIERS = (355, 361, 7946, 385)  # mackerel (heals 6), tuna (10), monkfish (16), shark (20)
BREAD = 2309
# raw trout, lobster, swordfish; oak, willow, maple, yew logs; iron, steel, mithril bars
PROCESSING_INPUTS = (335, 377, 371, 1521, 1519, 1517, 1515, 2351, 2353, 2359)
# Fletching's (Caleb, 2026-10-31): a knife; bowstrings; arrowtips, dart tips and unfinished bolts, bronze to rune.
KNIFE = 946
FLETCHING_INPUTS = (1777, 39, 40, 41, 42, 43, 44, 819, 820, 821, 822, 823, 824, 9375, 9377, 9378, 9379, 9380, 9381)

# Quest gear (Caleb, 2026-11-06, OQ-24): the dragon dagger and longsword (Lost City) as a melee tier above rune, and the
# four Fremennik helms (the Fremennik Trials) as helms. Their own groups: the scripted guide climbs SCIMITARS and ARMOUR.
DRAGON_WEAPONS = (1215, 1305)  # dragon dagger, dragon longsword
FREMENNIK_HELMS = (3751, 3749, 3755, 3753)  # berserker, archer, farseer, warrior
# Antipoison (Caleb, 2026-11-06): the four-dose potions, one a buy, so each comes as a potion, not a banknote
ANTIPOISONS = (2448, 2446)  # super antipoison(4), antipoison(4)
# Combat potions and antifire (Caleb, 2026-11-06; rlscape.sim.potions): the four-dose ones, one a buy
COMBAT_POTIONS = FOUR_DOSES + (ANTIFIRE[0],)
# shops.json ids. Zeke's is listed twice (135 and 150); Shops.startup maps the shopkeeper to the later one.
BOBS, NURMOFS, GERRANTS, LUMBRIDGE_STORE, ZEKES, LOWES, AUBURYS, ZAFFS, WYDINS = 54, 124, 144, 25, 150, 47, 114, 140, 77

# Ava's devices (Caleb, 2026-11-07; equipment.AVAS_DEVICES): the GE sells them at the prices he set, 2,500 and 10,000
# gp (scripts/build_price_tables.py), so the agent needn't learn Draynor Manor. The accumulator outranks the attractor
# and needs Ranged 50.

# The anti-dragon shield (Caleb, 2026-11-06): on the GE, once Duke Horacio's alone. Fights against dragonfire monsters
# put it on (equipment.wield_best's `protect`).
GE_ITEMS = (AXES + PICKAXES + FISHING_TOOLS + BAIT_AND_FEATHERS + (HAMMER,) + SCIMITARS + ARMOUR + SHORTBOWS + ARROWS
            + RUNES + STAVES + FOOD_TIERS + PROCESSING_INPUTS + (KNIFE,) + FLETCHING_INPUTS + (ANTI_DRAGON_SHIELD,)
            + DRAGON_WEAPONS + FREMENNIK_HELMS + ANTIPOISONS + COMBAT_POTIONS + AVAS_DEVICES)
SHOP_ITEMS = {**dict.fromkeys(AXES[:2], BOBS), **dict.fromkeys(PICKAXES, NURMOFS),
              **dict.fromkeys(FISHING_TOOLS + BAIT_AND_FEATHERS, GERRANTS), HAMMER: LUMBRIDGE_STORE,
              **dict.fromkeys(SCIMITARS[:3], ZEKES), **dict.fromkeys(SHORTBOWS + ARROWS, LOWES),
              **dict.fromkeys(RUNES[:7], AUBURYS), **dict.fromkeys(STAVES, ZAFFS), BREAD: WYDINS}
LOTS = {**dict.fromkeys(ARROWS + RUNES, 100), **dict.fromkeys(BAIT_AND_FEATHERS, 200),
        **dict.fromkeys(FOOD_TIERS + (BREAD,), 100),
        **dict.fromkeys(PROCESSING_INPUTS + FLETCHING_INPUTS, 1_000)}  # 1 for the rest
# role -> how the upgrade check compares; items without a role (consumables) have no upgrade check
ROLES = {**dict.fromkeys(AXES, "axe"), **dict.fromkeys(PICKAXES, "pickaxe"),
         **dict.fromkeys(SCIMITARS + DRAGON_WEAPONS, "melee"), **dict.fromkeys(SHORTBOWS, "ranged"),
         **dict.fromkeys(ARMOUR + FREMENNIK_HELMS, "armour"),
         **dict.fromkeys(FISHING_TOOLS + (HAMMER, KNIFE, ANTI_DRAGON_SHIELD) + STAVES, "unique"),
         **dict.fromkeys(AVAS_DEVICES, "ava")}
TOOL_CHAINS = {"axe": (HATCHET_PRIORITY, "woodcutting"), "pickaxe": (PICKAXE_PRIORITY, "mining")}
GEAR_CLASSES = ("melee", "ranged", "magic")


def _tool_rank(item: int, role: str, state: CharacterState) -> int | None:
    """An axe's or pickaxe's place in SkillingTool's priority (0 is best), or None if the level doesn't allow it."""
    priority, skill = TOOL_CHAINS[role]
    tools = gd.skilling_tools()
    return next((rank for rank, name in enumerate(priority)
                 if tools[name].item == item and state.level(skill) >= tools[name].level), None)


def usable(state: CharacterState, item: int) -> bool:
    role = ROLES.get(item)
    if role in TOOL_CHAINS:
        return _tool_rank(item, role, state) is not None
    if role in ("melee", "ranged", "armour", "ava") or item in STAVES or item in ARROWS:
        return can_wear(state, item)
    return True


def held_items(state: CharacterState) -> set[int]:
    """Everything the character has, worn, in the inventory (banknotes as their items) or in the bank."""
    unnoted = gd.unnoted_ids()
    return {unnoted.get(i, i) for i in (*state.inventory, *state.bank)} | set(state.equipment.values())


def is_upgrade(state: CharacterState, item: int) -> bool:
    """Better than anything held, and usable now, for the item's role."""
    role, held, items = ROLES.get(item), held_items(state), gd.items()
    if role is None:
        return True
    if role == "unique":
        return item not in held
    if role == "ava":  # an attractor while neither is held, the accumulator while it isn't
        return AVAS_DEVICES.index(item) > max((AVAS_DEVICES.index(i) for i in held if i in AVAS_DEVICES), default=-1)
    if role in TOOL_CHAINS:
        rank, ranks = _tool_rank(item, role, state), [r for i in held if (r := _tool_rank(i, role, state)) is not None]
        return rank is not None and rank < min(ranks, default=len(TOOL_CHAINS[role][0]))
    slot = items[item].equipment_slot
    rivals = [i for i in held if i in items and items[i].equipment_slot == slot and can_wear(state, i)]
    if role == "armour":
        return defence_score(item) > max(map(defence_score, rivals), default=float("-inf"))
    return weapon_score(item, role) > max((weapon_score(i, role) for i in rivals), default=0.0)


def _room_for(state: CharacterState, landing: int) -> bool:
    return state.free_slots() > 0 or (landing in gd.stackable_items() and landing in state.inventory)


def ge_landing(state: CharacterState, item: int, units: int) -> int:
    """What a GE buy arrives as: a banknote for more than one of a notable item, or for one with no room."""
    note = gd.noted_ids().get(item)
    if note is not None and item not in gd.stackable_items() and (units > 1 or state.free_slots() == 0):
        return note
    return item


def can_pay(state: CharacterState, price: int) -> bool:
    """The coins for one unit can reach the inventory: they're carried, or the bank's can be withdrawn onto the coins
    carried or into a free slot."""
    carried = state.inventory.get(COINS, 0)
    return carried >= price or (state.coins() >= price and (carried > 0 or state.free_slots() > 0))


def _withdraw_coins(state: CharacterState, amount: int) -> None:
    """Withdraw up to `amount` coins, as far as the bank and a slot for them allow."""
    added = state.add(COINS, min(amount, state.bank.get(COINS, 0))) if amount > 0 else 0
    if added:
        state.take(COINS, added, state.bank)


class BuyGE(Option):
    family = "buying"

    def __init__(self, item: int):
        self.id = f"buy_ge_{item}"
        self.item, self.lot = item, LOTS.get(item, 1)
        self.price = gd.ge_prices_2009()[item]

    def _units(self, state: CharacterState) -> int:
        return min(self.lot, state.coins() // self.price)

    def available(self, state: CharacterState) -> bool:
        units = self._units(state)
        return (units > 0 and can_pay(state, self.price) and usable(state, self.item) and is_upgrade(state, self.item)
                and _room_for(state, ge_landing(state, self.item, units)))

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        walked = walk(state, GE_TILE, budget)
        if walked is None:
            return OptionResult(budget, COMPLETED)
        units = self._units(state)  # the walk may have paid the toll
        short = units * self.price - state.inventory.get(COINS, 0)
        ticks = walked + GE_TICKS + (BANKING_TICKS if short > 0 else 0)
        if ticks > budget:
            return OptionResult(budget, COMPLETED)
        _withdraw_coins(state, short)
        units = min(units, state.inventory.get(COINS, 0) // self.price)
        if units > 0:
            state.take(COINS, units * self.price)  # the offer takes the coins, which can free their slot
            if not state.add(ge_landing(state, self.item, units), units):
                state.add(COINS, units * self.price)  # no room after all (the mask makes this rare): nothing bought
        return OptionResult(ticks, COMPLETED)


class BuyShop(Option):
    family = "buying"

    def __init__(self, item: int):
        self.id = f"buy_shop_{item}"
        self.item, self.lot, self.shop = item, LOTS.get(item, 1), SHOP_ITEMS[item]
        self.tile = gd.shops()[self.shop].tile()

    def _room(self, state: CharacterState) -> int:
        if self.item in gd.stackable_items():
            return self.lot if _room_for(state, self.item) else 0
        return state.free_slots()

    def available(self, state: CharacterState) -> bool:
        in_stock = stock(state, self.shop, self.item, state.tick)
        normal = gd.shops()[self.shop].stock[self.item][0]
        price = unit_price(self.item, normal, in_stock)
        return (in_stock > 0 and can_pay(state, price) and self._room(state) > 0
                and usable(state, self.item) and is_upgrade(state, self.item))

    def _toll(self, state: CharacterState, origin: tuple[int, int, int]) -> int:
        return TOLL if pays_toll(state, origin, self.tile) else 0

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed, in_stock = 0, stock(state, self.shop, self.item, state.tick)
        units = affordable_units(self.shop, self.item, in_stock, min(self.lot, self._room(state)), state.coins())
        cost = purchase_cost(self.shop, self.item, in_stock, units)
        if state.inventory.get(COINS, 0) < cost + self._toll(state, state.location):
            bank = min(gd.banks(), key=lambda b: route_ticks(state, (b.x, b.y, b.plane))
                       + travel_ticks((b.x, b.y, b.plane), self.tile))
            walked = walk(state, (bank.x, bank.y, bank.plane), budget)
            if walked is None or walked + BANKING_TICKS > budget:
                return OptionResult(budget, COMPLETED)
            elapsed = walked + BANKING_TICKS
            _withdraw_coins(state, cost + self._toll(state, state.location) - state.inventory.get(COINS, 0))
        walked = walk(state, self.tile, budget - elapsed, elapsed)
        if walked is None or elapsed + walked + STORE_TICKS > budget:
            return OptionResult(budget, COMPLETED)
        elapsed += walked + STORE_TICKS
        now = state.tick + elapsed
        in_stock = stock(state, self.shop, self.item, now)
        # Shop.buy caps the amount by the room before taking the coins, so a coin stack's slot doesn't count as free
        units = affordable_units(self.shop, self.item, in_stock, min(self.lot, self._room(state)),
                                 state.inventory.get(COINS, 0))
        if units > 0:
            state.take(COINS, purchase_cost(self.shop, self.item, in_stock, units))
            state.add(self.item, units)
            set_stock(state, self.shop, self.item, in_stock - units, now)
        return OptionResult(elapsed, COMPLETED)


def gear_to_withdraw(state: CharacterState, combat_class: str) -> list[int]:
    """Bank items that beat what the character carries or wears for a combat class, in the order they're taken: the
    weapon (ranged: the weapon and ammunition of the best kit) first, for magic every banked rune (a deposit for
    another task banks them), then armour, the biggest defence gain first (for magic, none that hinders it), then an
    anti-dragon shield if none is carried, for the fights against dragonfire monsters (not behind a two-handed
    weapon). Only what the character can wear."""
    items, carried = gd.items(), set(state.inventory) | set(state.equipment.values())
    bank = frozenset(i for i in state.bank if i in items and can_wear(state, i))
    out: list[int] = []
    if combat_class == "ranged":
        best = max(ranged_kits(state, bank), key=lambda kit: kit_score(*kit), default=None)
        now = max(ranged_kits(state), key=lambda kit: kit_score(*kit), default=None)
        if best is not None and (now is None or kit_score(*best) > kit_score(*now)):
            out += [part for part in dict.fromkeys(best) if part in bank and part not in carried]
        weapon = (best if out else now or (None,))[0]
    else:
        def score(i: int) -> float:
            return weapon_score(i, combat_class)
        best = max((i for i in bank if items[i].equipment_slot == WEAPON and score(i) > 0), key=score, default=None)
        now = max((i for i in carried if i in items and items[i].equipment_slot == WEAPON and can_wear(state, i)),
                  key=score, default=None)
        if best is not None and (now is None or score(best) > score(now)):
            out.append(best)
        weapon = out[0] if out else now
        if combat_class == "magic":
            out += sorted(i for i in state.bank if i in gd.rune_ids().values())
    two_handed = weapon is not None and items[weapon].two_handed
    device = combat_class == "ranged" and best_device(carried | bank) is not None
    gains = []
    for slot in ARMOUR_SLOTS + (() if two_handed else (SHIELD,)):
        if slot == CAPE and device:  # a ranged fight wears its best device (equipment.wield_best): first out
            pick, now = best_device(bank), best_device(carried)
            if pick is not None and (now is None or AVAS_DEVICES.index(pick) > AVAS_DEVICES.index(now)):
                gains.append((inf, pick))
            continue
        best = max((i for i in bank if items[i].equipment_slot == slot and not leaves_off(i, combat_class, device)),
                   key=defence_score, default=None)
        worn = max((defence_score(i) for i in carried if i in items and items[i].equipment_slot == slot
                    and can_wear(state, i) and not leaves_off(i, combat_class, device)), default=None)
        if best is not None and defence_score(best) > (0 if worn is None else worn):
            gains.append((defence_score(best) - (worn or 0), best))
    out += [item for _, item in sorted(gains, reverse=True)]
    guards = sorted(i for i in bank & DRAGONFIRE_PROTECTION if not hinders(i, combat_class))
    if guards and not two_handed and not carried & DRAGONFIRE_PROTECTION and guards[0] not in out:
        out.append(guards[0])
    return out


class BankWithdrawGear(Option):
    family = "inventory"

    def __init__(self, combat_class: str):
        self.id = f"bank_withdraw_gear_{combat_class}"
        self.combat_class = combat_class

    def available(self, state: CharacterState) -> bool:
        return state.free_slots() > 0 and bool(gear_to_withdraw(state, self.combat_class))

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        ticks = bank_trip(state, budget)
        if ticks is None:
            return OptionResult(budget, COMPLETED)
        for item in gear_to_withdraw(state, self.combat_class):
            amount = state.bank[item] if item in gd.stackable_items() else 1
            if not _room_for(state, item):
                break
            state.take(item, amount, state.bank)
            state.add(item, amount)
        return OptionResult(ticks, COMPLETED)


class BankWithdrawFood(Option):
    family = "inventory"

    def __init__(self, food: int):
        self.id = f"bank_withdraw_{food}"
        self.food = food

    def available(self, state: CharacterState) -> bool:
        notes = state.inventory.get(gd.noted_ids()[self.food], 0)
        return banked_or_noted(state, self.food) > 0 and (state.free_slots() > 0 or notes > 0)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        ticks = bank_trip(state, budget)
        if ticks is None:
            return OptionResult(budget, COMPLETED)
        bank_notes(state, (self.food,))
        take = min(state.bank.get(self.food, 0), state.free_slots())
        if take:
            state.take(self.food, take, state.bank)
            state.add(self.food, take)
        return OptionResult(ticks, COMPLETED)


class BankWithdrawAnyFood(Option):
    """bank_withdraw_food: walk to the nearest bank and take out food into the free slots, the best healing first,
    whatever it is (cooked catches as well as the four GE tiers). A deposit banks food unless the task is a fight or
    thieving (rlscape.sim.kits), so this brings it back for one."""

    family = "inventory"

    def __init__(self, option_id: str = "bank_withdraw_food"):
        self.id = option_id

    def available(self, state: CharacterState) -> bool:
        heals = gd.food_healing()
        return state.free_slots() > 0 and any(banked_or_noted(state, food) > 0 for food in heals)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        ticks = bank_trip(state, budget)
        if ticks is None:
            return OptionResult(budget, COMPLETED)
        heals = gd.food_healing()
        bank_notes(state, tuple(heals))
        for food in sorted((f for f in heals if state.bank.get(f, 0) > 0), key=lambda f: -heals[f]):
            take = min(state.bank[food], state.free_slots())
            if take == 0:
                break
            state.take(food, take, state.bank)
            state.add(food, take)
        return OptionResult(ticks, COMPLETED)


class BankWithdrawForSale(Option):
    """bank_withdraw_for_sale (Caleb, 2026-10-30): walk to the nearest bank and take out produce to sell, as
    banknotes (the bank's withdraw-as-note setting), so each item's whole stack fits in one slot; the most valuable
    stacks first, up to the free slots. The sell actions then sell the banknotes.

    Produce is what bank_deposit banks (so not tools, food, ammunition or runes), apart from the gear the character
    would take out to fight (gear_to_withdraw, for each class), and apart from items that neither note nor stack,
    which would need a slot each."""

    family = "inventory"

    def __init__(self, option_id: str = "bank_withdraw_for_sale"):
        self.id = option_id

    @staticmethod
    def produce(state: CharacterState) -> list[int]:
        """The banked items this takes out, in the order it takes them."""
        keep = {item for combat_class in GEAR_CLASSES for item in gear_to_withdraw(state, combat_class)}
        notes, stackable, values = gd.noted_ids(), gd.stackable_items(), gd.item_values()
        items = [i for i in state.bank if i != COINS and not kept_on_deposit(i) and i not in keep
                 and (i in notes or i in stackable)]
        return sorted(items, key=lambda i: (-values.get(i, 0) * state.bank[i], i))

    def available(self, state: CharacterState) -> bool:
        notes = gd.noted_ids()
        return any(state.free_slots() > 0 or notes.get(i, i) in state.inventory for i in self.produce(state))

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        ticks = bank_trip(state, budget)
        if ticks is None:
            return OptionResult(budget, COMPLETED)
        notes = gd.noted_ids()
        for item in self.produce(state):
            added = state.add(notes.get(item, item), state.bank[item])  # a stack: all of it or none
            if added:
                state.take(item, added, state.bank)
        return OptionResult(ticks, COMPLETED)


def buying_options() -> list[Option]:
    """Catalog §8: the GE buys, the shop buys, then the gear and food withdrawals and the withdrawal for sale."""
    return [*(BuyGE(item) for item in GE_ITEMS), *(BuyShop(item) for item in SHOP_ITEMS),
            *(BankWithdrawGear(c) for c in GEAR_CLASSES), *(BankWithdrawFood(food) for food in FOOD_TIERS),
            BankWithdrawAnyFood(), BankWithdrawForSale()]
