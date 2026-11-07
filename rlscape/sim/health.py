"""Hitpoints: regeneration over time, eating, and the retreat rule options share (option catalog §4.B).

- Regeneration, from the server's SkillRestore timer: one HP every 101 ticks (`ticksSinceLastRestore++ >= 100`)
  on a fixed cycle that keeps running across options; nothing above the maximum. Rapid Heal and the regen bracelet
  aren't in scope.
- Eating, from ConsumableListener: a bite heals Consumables' amount, and the next bite can follow 2 ticks later.
- The rule options follow: eat when HP is at or below half of the maximum; once the food runs out, stop.
  Cheaper food is eaten first.
- Poison, from the server's Poison timer (rlscape.combat.rates has its rule): a hit every 30 ticks of its own cycle,
  which keeps running across options until it wears off; a stronger poison raises the severity of the one running.
  A hit that leaves HP at or below the retreat point is eaten through, by the same rule, while food lasts (an agent
  choice: a player would eat). It can kill; the fight or the engine handles the death. Death clears it
  (TimerFlag.ClearOnDeath).
- Antipoison (Caleb, 2026-11-06), from the server's ANTIPOISON and SUPER_ANTIP potions (AddTimerEffect,
  PoisonImmunity): a dose cures the poison and makes the character immune for 150 ticks (90 s), or 600 (6 minutes)
  for the super; another dose restarts the immunity. A dose leaves the next in its slot, the last an empty vial
  (Potion.consume). The rule options follow (an agent choice): drink when a poison takes hold, or carries on from
  before, while a dose is carried; the super antipoison first (cheaper a tick of immunity: 253 gp a dose for 600
  ticks against 96 for 150), and of each the emptiest potion first.
"""

from __future__ import annotations

from rlscape.combat.rates import EAT_BELOW_FRACTION, POISON_TICKS, poison_damage
from rlscape.gamedata import server as gd
from rlscape.sim.state import CharacterState

REGEN_TICKS = 101  # SkillRestore: the counter check `++ >= 100` fires every 101 ticks
SUPER_ANTIPOISON = (2448, 181, 183, 185)  # 4 doses to 1
ANTIPOISON = (2446, 175, 177, 179)
VIAL = 229
ANTIPOISON_DOSES = SUPER_ANTIPOISON + ANTIPOISON
IMMUNITY_TICKS = {**dict.fromkeys(SUPER_ANTIPOISON, 600), **dict.fromkeys(ANTIPOISON, 150)}
DRINK_ORDER = SUPER_ANTIPOISON[::-1] + ANTIPOISON[::-1]
DRINK_TICKS = 2  # like a bite (ConsumableListener); calibrate
EAT_TICKS = 2  # ConsumableListener: NEXT_EAT = now + 2; calibrate


def regenerate(state: CharacterState, ticks: int, poison: bool = True) -> None:
    """Advance the regeneration cycle by `ticks`, and the poison on the character too unless the caller has."""
    state.regen_counter += ticks
    heals, state.regen_counter = divmod(state.regen_counter, REGEN_TICKS)
    state.hp = min(state.max_hp(), state.hp + heals)
    if heals and state.boosts:  # SkillRestore's cycle lowers potion boosts too, by 1 (rlscape.sim.potions)
        state.boosts = {skill: b - heals for skill, b in state.boosts.items() if b > heals}
    if poison:
        advance_poison(state, ticks)


def drink_antipoison(state: CharacterState, now: int) -> bool:
    """Drink the next antipoison dose (DRINK_ORDER), if one is carried: the poison goes, the immunity starts."""
    item = next((i for i in DRINK_ORDER if state.inventory.get(i)), None)
    if item is None:
        return False
    potion = SUPER_ANTIPOISON if item in SUPER_ANTIPOISON else ANTIPOISON
    state.take(item)
    following = potion.index(item) + 1
    state.add(potion[following] if following < len(potion) else VIAL)  # into the slot the dose leaves
    state.poison_severity = state.poison_clock = 0
    state.poison_immune_until = now + IMMUNITY_TICKS[item]
    return True


def apply_poison(state: CharacterState, severity: int, now: int) -> int:
    """ContentAPI.applyPoison at tick `now`: nothing while immune; else a dose, if one is carried, cures it at once;
    else a new poison starts its 30-tick cycle, and a stronger one raises the severity of the one running. The ticks
    the drinking takes."""
    if severity <= 0 or now < state.poison_immune_until:
        return 0
    if drink_antipoison(state, now):
        return DRINK_TICKS
    if state.poison_severity == 0:
        state.poison_clock = 0
    state.poison_severity = max(state.poison_severity, severity)
    return 0


def poison_cover(state: CharacterState, ticks: float) -> float:
    """The share of the next `ticks` the antipoison carried (and any immunity running) keeps poison off, for the
    combat ranking's damage: each dose covers its immunity."""
    if ticks <= 0:
        return 1.0
    covered = max(state.poison_immune_until - state.tick, 0)
    for item, amount in state.inventory.items():
        if item in IMMUNITY_TICKS:
            potion = SUPER_ANTIPOISON if item in SUPER_ANTIPOISON else ANTIPOISON
            covered += IMMUNITY_TICKS[item] * (len(potion) - potion.index(item)) * amount  # its doses left
    return min(covered / ticks, 1.0)


def advance_poison(state: CharacterState, ticks: int, now: int | None = None) -> None:
    """The poison's hits over `ticks` (from tick `now`, by default the state's), eating through any that leaves HP
    at or below the retreat point. A poison running on from before is drunk away first, if a dose is carried."""
    if state.poison_severity > 0 and ticks > 0:
        drink_antipoison(state, state.tick if now is None else now)
    while state.poison_severity > 0 and ticks > 0:
        step = POISON_TICKS - state.poison_clock
        if ticks < step:
            state.poison_clock += ticks
            return
        ticks -= step
        state.poison_clock = 0
        state.hp -= poison_damage(state.poison_severity)
        state.poison_severity -= 1
        if 0 < state.hp <= retreat_hp(state):
            eat_one(state)


def foods_held(state: CharacterState) -> list[tuple[int, int]]:
    """(heal, item) for the food in the inventory, cheapest first."""
    heals = gd.food_healing()
    return sorted((heals[item], item) for item in state.inventory if item in heals)


def food_healing_held(state: CharacterState) -> int:
    heals = gd.food_healing()
    return sum(heals[item] * amount for item, amount in state.inventory.items() if item in heals)


def retreat_hp(state: CharacterState) -> float:
    return EAT_BELOW_FRACTION * state.max_hp()


def eat_one(state: CharacterState) -> bool:
    """Eat the cheapest food held; False if there is none."""
    foods = foods_held(state)
    if not foods:
        return False
    heal, item = foods[0]
    state.inventory[item] -= 1
    if state.inventory[item] == 0:
        del state.inventory[item]
    state.hp = min(state.max_hp(), state.hp + heal)
    return True
