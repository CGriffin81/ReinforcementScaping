"""Worn gear: a fighter's bonuses come from what's worn, and a combat option first wields the best gear the character
carries for its combat class. Wielding automatically is an agent choice, reversible and listed for Caleb's review, in
the spirit of the server picking the best axe or pickaxe by itself.

Rules from the server: an item can be worn if the character meets its equip requirements (item configs) and any
quest lock (ItemQuestRequirementListener, e.g. Dragon Slayer for rune platebodies); a two-handed weapon leaves the
shield slot empty. Skill ids in the requirements are the server's, which match rlscape.sim.skills.SKILLS.

Ranged (ranged_weapon_configs.json, RangeSwingHandler): a bow or crossbow fires the ammunition in the quiver, and only
the ammunition it lists; a thrown weapon (darts, knives, thrown axes) is its own ammunition, a stack in the weapon
slot; a crystal bow needs none. The best kit is the pair with the highest damage per tick. Stacks (arrows, bolts,
thrown weapons) go on whole and top up a worn stack of the same item. The dark bow (two arrows and two hits per
attack) and chinchompas (multi-target) aren't modelled and are never wielded for a ranged fight.

Ava's devices (Caleb, 2026-11-07, OQ-28): worn in ranged fights only, as the cape, and with their attraction off (the
server's spawn switches it off), so a device saves ammunition and adds its bonuses, nothing more. A ranged fight
wears the best device carried over any other cape. The accumulator needs Ranged 50 to wear (the fork's item config).
Agent choice (reversible): a ranger wearing a device leaves off chest armour that would stop it
(gd.ava_interfering_items), as magic leaves off metal.
"""

from __future__ import annotations

from rlscape.combat.prayers import flicks
from rlscape.combat.rates import Fighter
from rlscape.gamedata import server as gd
from rlscape.sim.skills import SKILLS
from rlscape.sim.state import CharacterState

WEAPON, SHIELD, AMMO = 3, 5, 13  # EquipmentContainer slots
CAPE, CHEST = 1, 4
ARMOUR_SLOTS = (0, 1, 2, 4, 7, 9, 10, 12)  # hat, cape, amulet, chest, legs, hands, feet, ring
WIELD_TICKS = 1  # per item put on; calibrate
UNARMED_SPEED = 4
UNMODELLED_RANGED = frozenset({"DOUBLE_SHOT", "CHINCHOMPA"})

# Ava's devices, and RangeSwingHandler.getDropRate's rule for them
AVAS_ATTRACTOR, AVAS_ACCUMULATOR = 10498, 10499
AVAS_DEVICES = (AVAS_ATTRACTOR, AVAS_ACCUMULATOR)  # the accumulator outranks the attractor
AVA_CATCH = 0.8  # random(100) < 80: the shot goes back to the quiver ...
AVA_DROP_RATE = 0.33  # ... and otherwise its land roll is a third as wide
AVA_EXCLUDED_WEAPONS = frozenset({10033, 10034})  # chinchompas
BOLT_RACK = 4740


def can_wear(state: CharacterState, item: int) -> bool:
    definition = gd.items().get(item)
    if definition is None or definition.equipment_slot is None:
        return False
    # a requirement on a skill the sim doesn't have (the cache gives index 24 on a few items) can't be met
    if any(skill >= len(SKILLS) or state.level(SKILLS[skill]) < level for skill, level in definition.requirements.items()):
        return False
    quest = gd.equip_quest_locks().get(item)
    return quest is None or quest in state.progress.quests_complete


def weapon_score(item: int, combat_class: str) -> float:
    """Proportional to damage per tick: the server's attack rolls scale with (attack bonus + 64) and melee max hits
    with (strength bonus + 64), all divided by the weapon's attack speed. Zero if the weapon gives the class nothing."""
    definition = gd.items()[item]
    b, speed = definition.bonuses, definition.attack_speed or UNARMED_SPEED
    if combat_class == "melee":
        attack = max(b[gd.STAB], b[gd.SLASH], b[gd.CRUSH])
        return (attack + 64) * (b[gd.MELEE_STRENGTH] + 64) / speed if attack > 0 or b[gd.MELEE_STRENGTH] > 0 else 0.0
    bonus = b[gd.RANGED] if combat_class == "ranged" else b[gd.MAGIC]
    return (bonus + 64) / speed if bonus > 0 else 0.0


def kit_score(weapon: int, ammo: int | None) -> float:
    """A ranged kit's damage per tick, up to a constant: (ranged attack + 64)(ranged strength + 64) / speed, the
    strength coming from the ammunition (a thrown weapon's own, a crystal bow's own)."""
    items = gd.items()
    attack = items[weapon].bonuses[gd.RANGED] + (items[ammo].bonuses[gd.RANGED] if ammo not in (None, weapon) else 0)
    strength = items[weapon if ammo is None else ammo].bonuses[gd.RANGED_STRENGTH]
    return (attack + 64) * (strength + 64) / (items[weapon].attack_speed or UNARMED_SPEED)


def ranged_kits(state: CharacterState, also: frozenset[int] = frozenset()) -> list[tuple[int, int | None]]:
    """(weapon, ammunition) pairs the character can fire with, from what it carries or wears (plus `also`)."""
    weapons, held = gd.ranged_weapons(), set(state.inventory) | set(state.equipment.values()) | also
    kits: list[tuple[int, int | None]] = []
    for weapon in sorted(held):
        ranged = weapons.get(weapon)
        if ranged is None or ranged.weapon_type in UNMODELLED_RANGED or not can_wear(state, weapon):
            continue
        if ranged.weapon_type == "DEGRADING":
            kits.append((weapon, None))
        elif ranged.ammo_slot == WEAPON:
            kits.append((weapon, weapon))
        else:
            kits += [(weapon, ammo) for ammo in ranged.ammunition if ammo in held and can_wear(state, ammo)]
    return kits


def ranged_ready(state: CharacterState) -> bool:
    """A ranged weapon is worn, with ammunition it fires (or one that needs none)."""
    ranged = gd.ranged_weapons().get(state.equipment.get(WEAPON))
    if ranged is None or ranged.weapon_type in UNMODELLED_RANGED:
        return False
    return ranged.weapon_type == "DEGRADING" or state.equipment.get(ranged.ammo_slot) in ranged.ammunition


MAGIC_ATTACK = 3  # index of the magic attack bonus in an item's bonuses


def hinders(item: int, combat_class: str) -> bool:
    """Armour a class leaves off: for magic, anything that lowers magic attack (metal armour). Worn, an iron set's
    penalty leaves a low-level caster no target worth fighting. Ava's devices outside ranged fights (Caleb)."""
    if item in AVAS_DEVICES:
        return combat_class != "ranged"
    return combat_class == "magic" and gd.items()[item].bonuses[MAGIC_ATTACK] < 0


def leaves_off(item: int, combat_class: str, device: bool) -> bool:
    """`hinders`, and for a ranged fight with Ava's device (`device`), chest armour that would stop it."""
    return hinders(item, combat_class) or (device and combat_class == "ranged"
                                            and item in gd.ava_interfering_items())


def best_device(items) -> int | None:
    """The best of Ava's devices among `items`."""
    return max((i for i in items if i in AVAS_DEVICES), key=AVAS_DEVICES.index, default=None)


def land_chance(ranged_level: int, rate: float = 1.0) -> float:
    """RangeSwingHandler.useAmmo: a fired shot lands under the target unless randomize(int(5 x (1 + level / 100) x
    rate)) is 0, which breaks it; randomize(n) is always 0 for n below 2. `rate` is getDropRate's: 1, or
    AVA_DROP_RATE for a shot Ava's device didn't catch."""
    n = int(5 * (1.0 + ranged_level * 0.01) * rate)
    return 1 - 1 / n if n >= 1 else 0.0


def shot_outcomes(state: CharacterState) -> tuple[float, float]:
    """A ranged shot's chances of going back to the quiver and of landing under the target, as the character is
    equipped (RangeSwingHandler.getDropRate and useAmmo); the rest break. With no device, nothing goes back. A worn
    device (not with chinchompas or a bolt rack) catches 80% of shots; the rest land on its narrower roll. The
    attractor's land; the accumulator gathers them back into the quiver too (the fork: Caleb, 2026-11-07, OQ-28 (i)).
    Interfering chest armour stops only the 80% catch, whose shots then land on the normal roll, as the server has
    it. Shots land only from weapons that drop their ammunition."""
    weapon, level = gd.ranged_weapons()[state.equipment[WEAPON]], state.level("ranged")
    land = land_chance(level) if weapon.drop_ammo else 0.0
    device = state.equipment.get(CAPE)
    if (device not in AVAS_DEVICES or state.equipment.get(WEAPON) in AVA_EXCLUDED_WEAPONS
            or state.equipment.get(AMMO) == BOLT_RACK):
        return 0.0, land
    if state.equipment.get(CHEST) in gd.ava_interfering_items():
        caught, landed = 0.0, AVA_CATCH * land
    else:
        caught, landed = AVA_CATCH, 0.0
    missed = (1 - AVA_CATCH) * (land_chance(level, AVA_DROP_RATE) if weapon.drop_ammo else 0.0)
    return (caught + missed, landed) if device == AVAS_ACCUMULATOR else (caught, landed + missed)


def defence_score(item: int) -> float:
    return sum(gd.items()[item].bonuses[5:10])


def _put_on(state: CharacterState, slot: int, item: int) -> None:
    """Move an item from the inventory into a slot, the whole stack if it stacks. What was there goes back to the
    inventory, unless it's the same item, whose worn stack is topped up. Taking the item out frees the slot the old
    one needs, so it always fits."""
    stack = item in gd.stackable_items()
    amount = state.inventory[item] if stack else 1
    old, old_amount = state.equipment.get(slot), state.worn(slot)
    state.take(item, amount)
    if old == item:
        amount += old_amount
    elif old is not None:
        state.add(old, old_amount)
    state.equipment[slot] = item
    if stack:
        state.worn_amounts[slot] = amount
    else:
        state.worn_amounts.pop(slot, None)


def _wield_weapon(state: CharacterState, weapon: int) -> bool:
    """Put on a weapon from the inventory; a two-handed one takes the shield off too. False, changing nothing, if
    the inventory has no room for what comes off."""
    two_handed = gd.items()[weapon].two_handed and SHIELD in state.equipment
    coming_off = (state.equipment.get(WEAPON, weapon) != weapon) + two_handed
    if coming_off > state.free_slots() + 1:  # the weapon leaving the inventory frees its slot
        return False
    _put_on(state, WEAPON, weapon)
    if two_handed:
        state.add(state.equipment.pop(SHIELD))
    return True


def wield_best(state: CharacterState, combat_class: str, protect: frozenset[int] = frozenset()) -> int:
    """Wield the best weapon (ranged: weapon and ammunition) for the class and the best armour per slot from the
    inventory; the ticks it takes. For magic, armour that hinders it is taken off (room allowing) and not put on.
    `protect`: shields against the monster's special damage (candidates.special_damage_shields). If the character
    carries one and wears none, it wears the best of them in place of the best shield by defence."""
    items, worn = gd.items(), 0
    if combat_class == "ranged":
        kits = ranged_kits(state)
        if kits:
            weapon, ammo = max(kits, key=lambda kit: kit_score(*kit))
            if weapon in state.inventory and _wield_weapon(state, weapon):
                worn += 1
            if ammo not in (None, weapon) and ammo in state.inventory and state.equipment.get(WEAPON) == weapon:
                _put_on(state, AMMO, ammo)
                worn += 1
    else:
        weapons = [i for i in state.inventory if can_wear(state, i) and items[i].equipment_slot == WEAPON
                   and weapon_score(i, combat_class) > 0]
        current = state.equipment.get(WEAPON)
        best = max(weapons, key=lambda i: weapon_score(i, combat_class), default=None)
        if best is not None and (current is None
                                 or weapon_score(best, combat_class) > weapon_score(current, combat_class)):
            worn += _wield_weapon(state, best)
    two_handed = WEAPON in state.equipment and items[state.equipment[WEAPON]].two_handed
    for slot in ARMOUR_SLOTS + (() if two_handed else (SHIELD,)):
        device = state.equipment.get(CAPE) in AVAS_DEVICES  # the cape comes before the chest
        if (slot in state.equipment and leaves_off(state.equipment[slot], combat_class, device)
                and state.free_slots() > 0):
            state.add(state.equipment.pop(slot))
            worn += 1
        options = [i for i in state.inventory if can_wear(state, i) and items[i].equipment_slot == slot
                   and not leaves_off(i, combat_class, device)]
        if slot == CAPE and combat_class == "ranged":
            pick = best_device(options + [state.equipment.get(CAPE)])
            if pick is not None:  # a ranged fight wears its best device over any other cape
                if state.equipment.get(CAPE) != pick:
                    _put_on(state, slot, pick)
                    worn += 1
                continue
        if slot == SHIELD and state.equipment.get(SHIELD) not in protect and any(i in protect for i in options):
            _put_on(state, slot, max((i for i in options if i in protect), key=defence_score))
            worn += 1
            continue
        best = max(options, key=defence_score, default=None)
        if best is not None and (slot not in state.equipment or defence_score(best) > defence_score(state.equipment[slot])):
            _put_on(state, slot, best)
            worn += 1
    return worn * WIELD_TICKS


def fighter_for(state: CharacterState) -> Fighter:
    """The fighter as currently equipped: levels (as potions boost them) plus the summed bonuses of everything worn,
    and the prayers its levels and quests give a fight. A thrown weapon ignores the quiver's ranged strength
    (RangeSwingHandler.calculateHit)."""
    items = gd.items()
    bonuses = list(map(sum, zip(gd.NO_BONUSES, *(items[i].bonuses for i in state.equipment.values()))))
    weapon = state.equipment.get(WEAPON)
    ranged = gd.ranged_weapons().get(weapon)
    if ranged is not None and ranged.ammo_slot != AMMO and AMMO in state.equipment:
        bonuses[gd.RANGED_STRENGTH] -= items[state.equipment[AMMO]].bonuses[gd.RANGED_STRENGTH]
    speed = (items[weapon].attack_speed or UNARMED_SPEED) if weapon is not None else UNARMED_SPEED
    return Fighter(state.boosted("attack"), state.boosted("strength"), state.boosted("defence"),
                   state.level("hitpoints"), state.boosted("ranged"), state.boosted("magic"), tuple(bonuses), speed,
                   flicks(state.level("prayer"), state.level("defence"), state.progress.quests_complete))
