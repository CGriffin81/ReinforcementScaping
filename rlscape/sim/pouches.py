"""Essence pouches (sim v1, Runecrafting; Caleb, 2026-11-08, OQ-40 (c): as the server gives them). The server's
PouchManager.kt and RunePouchPlugin.kt; rlscape.gamedata.runecrafting.pouches.

- Four pouches, small to giant, holding 3, 6, 9 and 12 essence, fillable from Runecrafting 1, 25, 50 and 75.
- The server keeps one state for each kind, not each item (PouchManager.pouches): the capacity now and the essence
  left before the next decay. The sim keeps it on the state (`CharacterState.pouches`, only the kinds not as new) and
  keeps the base item only: a decayed pouch's item (the next id on the server) is the same pouch here.
- Fill (RunePouchPlugin): the kind of essence the inventory holds more of, as much as the pouch has room for. The
  medium, large and giant count it against their charges; once they run out, the capacity falls by 1, 2 or 3, the
  next decay comes 9 x the new capacity later, and that fill puts in at most the new capacity. A pouch whose capacity
  reaches 0 disappears, and its kind's state starts afresh. The small pouch never decays.
- Empty: back into the inventory, as much as its free slots take.
- Repair (the Dark Mage in the Abyss's centre, DarkMageDialogue): every kind back as new, free.
- A drop (AbyssalNPC.finalizeDeath): each kill of an abyssal leech, guardian or walker by the character has a 12 in
  750 chance of the next pouch it lacks (small, medium, large, giant, counting the inventory, bank and equipment).
A trip fills its pouches at the bank and empties them inside the altar the same trip, so the essence in them is the
state's only between those two (`CharacterState.pouch_essence`).

Times (measured on the server, scripts/measure_abyss.py --pouches, 2026-11-09): a Fill or an Empty a tick each; the
altar locks the character LOCK_TICKS after a craft, dropping clicks; a second Craft-rune beside it gives its runes
CRAFT_AGAIN_TICKS after the click.
"""

from __future__ import annotations

import numpy as np

from rlscape.gamedata import runecrafting as rcd
from rlscape.sim.state import CharacterState

FILL_TICKS = 1  # a Fill, clicked as the last took (measured: 1, every pouch)
EMPTY_TICKS = 1  # an Empty (measured: 1)
LOCK_TICKS = 2  # after a craft, the altar's lock: clicks 1 and 2 ticks after the runes were dropped, the third taken
CRAFT_AGAIN_TICKS = 2  # beside the altar, the second Craft-rune to its runes (measured: 2)
REWITHDRAW_TICKS = 1  # at the booth, the second withdrawal of essence into the slots the pouches emptied
DROP_CHANCE = 12 / 750  # AbyssalNPC.finalizeDeath: RandomFunction.random(750) < 12
ABYSSAL = (2263, 2264, 2265)  # leech, guardian, walker


def capacity(state: CharacterState, item: int) -> int:
    p = rcd.pouches()[item]
    return state.pouches.get(item, (p.capacity, p.charges))[0]


def charges(state: CharacterState, item: int) -> int:
    p = rcd.pouches()[item]
    return state.pouches.get(item, (p.capacity, p.charges))[1]


def held(state: CharacterState, item: int) -> bool:
    """Carried, banked or worn (Player.hasItem), as a drop counts it."""
    return state.inventory.get(item, 0) > 0 or state.bank.get(item, 0) > 0 or item in state.equipment.values()


def fillable(state: CharacterState) -> list[int]:
    """The pouches the character has whose Runecrafting level it has, small to giant."""
    level = state.level("runecrafting")
    return [i for i, p in rcd.pouches().items() if held(state, i) and level >= p.level]


def decayed(state: CharacterState) -> bool:
    """Whether any pouch it has holds less than new: the Dark Mage would repair it."""
    return any(capacity(state, i) < p.capacity for i, p in rcd.pouches().items() if held(state, i))


def fill(state: CharacterState, item: int) -> int:
    """PouchManager.addToPouch for the kind of essence the inventory holds more of: the essence put in."""
    rune, pure = state.inventory.get(rcd.RUNE_ESSENCE, 0), state.inventory.get(rcd.PURE_ESSENCE, 0)
    if rune == pure:
        return 0  # RunePouchPlugin: nothing when they're equal
    essence = rcd.RUNE_ESSENCE if rune > pure else rcd.PURE_ESSENCE
    held_kind, held_amount = state.pouch_essence.get(item, (essence, 0))
    if held_amount and held_kind != essence:
        return 0  # one kind of essence a pouch
    p, cap, left = rcd.pouches()[item], capacity(state, item), charges(state, item)
    amount = min(state.inventory[essence], cap - held_amount)
    if amount <= 0:
        return 0
    if p.decay:
        left -= amount
        if left <= 0:
            cap -= p.decay
            if cap <= 0:  # it disappears; its kind starts afresh
                state.take(item)
                state.pouches.pop(item, None)
                state.pouch_essence.pop(item, None)
                return 0
            left, held_amount = 9 * cap, 0  # remakeContainer: a fresh container, what was in it gone
            amount = min(amount, cap)
    if (cap, left) == (p.capacity, p.charges):
        state.pouches.pop(item, None)
    else:
        state.pouches[item] = (cap, left)
    state.take(essence, amount)
    state.pouch_essence[item] = (essence, held_amount + amount)
    return amount


def empty(state: CharacterState, item: int) -> int:
    """PouchManager.withdrawFromPouch: the essence back in the inventory, as its free slots take."""
    essence, amount = state.pouch_essence.get(item, (0, 0))
    amount = min(amount, state.free_slots())
    if amount <= 0:
        return 0
    state.add(essence, amount)
    left = state.pouch_essence[item][1] - amount
    if left:
        state.pouch_essence[item] = (essence, left)
    else:
        del state.pouch_essence[item]
    return amount


def repair(state: CharacterState) -> None:
    """The Dark Mage's repair: every kind back as new (PouchManager.repair), the essence in them kept."""
    state.pouches.clear()


def drop(state: CharacterState, npc_id: int, rng: np.random.Generator) -> int | None:
    """A kill's pouch, if it drops one: the next the character lacks, small to giant."""
    if npc_id not in ABYSSAL or rng.random() >= DROP_CHANCE:
        return None
    return next((i for i in rcd.pouches() if not held(state, i)), None)
