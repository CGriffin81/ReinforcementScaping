"""Worn gear: a fighter's bonuses come from what's worn, and a combat option first wields the best gear the character
carries for its combat class. Wielding automatically is an agent choice, reversible and listed for Caleb's review, in
the spirit of the server picking the best axe or pickaxe by itself.

Rules from the server: an item can be worn if the character meets its equip requirements (item configs) and any
quest lock (ItemQuestRequirementListener, e.g. Dragon Slayer for rune platebodies); a two-handed weapon leaves the
shield slot empty. Skill ids in the requirements are the server's, which match rlscape.sim.skills.SKILLS.
"""

from __future__ import annotations

from rlscape.combat.rates import Fighter
from rlscape.gamedata import server as gd
from rlscape.sim.skills import SKILLS
from rlscape.sim.state import CharacterState

WEAPON, SHIELD = 3, 5  # EquipmentContainer slots
ARMOUR_SLOTS = (0, 1, 2, 4, 7, 9, 10, 12)  # hat, cape, amulet, chest, legs, hands, feet, ring
WIELD_TICKS = 1  # per item put on; calibrate
UNARMED_SPEED = 4


def can_wear(state: CharacterState, item: int) -> bool:
    definition = gd.items().get(item)
    if definition is None or definition.equipment_slot is None:
        return False
    if any(state.level(SKILLS[skill]) < level for skill, level in definition.requirements.items()):
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


def defence_score(item: int) -> float:
    return sum(gd.items()[item].bonuses[5:10])


def _put_on(state: CharacterState, slot: int, item: int) -> None:
    old = state.equipment.get(slot)
    state.take(item)
    state.equipment[slot] = item
    if old is not None:
        state.add(old)


def wield_best(state: CharacterState, combat_class: str) -> int:
    """Wield the best weapon for the class and the best armour per slot from the inventory; the ticks it takes."""
    items, worn = gd.items(), 0
    weapons = [i for i in state.inventory if can_wear(state, i) and items[i].equipment_slot == WEAPON
               and weapon_score(i, combat_class) > 0]
    current = state.equipment.get(WEAPON)
    best = max(weapons, key=lambda i: weapon_score(i, combat_class), default=None)
    if best is not None and (current is None or weapon_score(best, combat_class) > weapon_score(current, combat_class)):
        if items[best].two_handed and SHIELD in state.equipment:
            if state.free_slots() >= 1 or current is None:
                state.add(state.equipment.pop(SHIELD))
            else:
                best = None
        if best is not None:
            _put_on(state, WEAPON, best)
            worn += 1
    two_handed = WEAPON in state.equipment and items[state.equipment[WEAPON]].two_handed
    for slot in ARMOUR_SLOTS + (() if two_handed else (SHIELD,)):
        options = [i for i in state.inventory if can_wear(state, i) and items[i].equipment_slot == slot]
        best = max(options, key=defence_score, default=None)
        if best is not None and (slot not in state.equipment or defence_score(best) > defence_score(state.equipment[slot])):
            _put_on(state, slot, best)
            worn += 1
    return worn * WIELD_TICKS


def fighter_for(state: CharacterState) -> Fighter:
    """The fighter as currently equipped: levels plus the summed bonuses of everything worn."""
    items = gd.items()
    bonuses = tuple(map(sum, zip(gd.NO_BONUSES, *(items[i].bonuses for i in state.equipment.values()))))
    weapon = state.equipment.get(WEAPON)
    speed = (items[weapon].attack_speed or UNARMED_SPEED) if weapon is not None else UNARMED_SPEED
    return Fighter(state.level("attack"), state.level("strength"), state.level("defence"), state.level("hitpoints"),
                   state.level("ranged"), state.level("magic"), bonuses, speed)
