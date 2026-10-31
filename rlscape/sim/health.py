"""Hitpoints: regeneration over time, eating, and the retreat rule options share (option catalog §4.B).

- Regeneration, from the server's SkillRestore timer: one HP every 101 ticks (`ticksSinceLastRestore++ >= 100`)
  on a fixed cycle that keeps running across options; nothing above the maximum. Rapid Heal and the regen bracelet
  aren't in scope.
- Eating, from ConsumableListener: a bite heals Consumables' amount, and the next bite can follow 2 ticks later.
- The rule options follow: eat when HP is at or below half of the maximum; once the food runs out, stop.
  Cheaper food is eaten first.
"""

from __future__ import annotations

from rlscape.combat.rates import EAT_BELOW_FRACTION
from rlscape.gamedata import server as gd
from rlscape.sim.state import CharacterState

REGEN_TICKS = 101  # SkillRestore: the counter check `++ >= 100` fires every 101 ticks
EAT_TICKS = 2  # ConsumableListener: NEXT_EAT = now + 2; calibrate


def regenerate(state: CharacterState, ticks: int) -> None:
    """Advance the regeneration cycle by `ticks`."""
    state.regen_counter += ticks
    heals, state.regen_counter = divmod(state.regen_counter, REGEN_TICKS)
    state.hp = min(state.max_hp(), state.hp + heals)


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
