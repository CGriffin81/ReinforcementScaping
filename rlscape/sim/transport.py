"""Teleports and boats in the sim's walks (rlscape.gamedata.transports; Caleb, 2026-11-01): who can use one from
where, and what using it takes.

A teleport needs its quests, its Magic level and runes (a worn elemental staff stands in for its rune, as in fights),
or its item: jewellery at any charge worn or carried (a charge is used: the item becomes the next charge, and the
last crumbles or is left uncharged), a tablet or the seed pod carried (used up). The home teleport is free, once
every 30 minutes (Caleb, 2026-11-01). It can't be used deeper in the Wilderness than its limit. A boat needs its quests and fare, and Entrana's monks turn away
anyone carrying or wearing weapons or armour (approximated: an item worn in a slot with any combat bonus; the
server's ItemDefinition.isAllowedOnEntrana).
"""

from __future__ import annotations

from functools import cache

from rlscape.gamedata import server as gd
from rlscape.gamedata.transports import (ABYSS_SKULL_TICKS, HOME_COOLDOWN_TICKS, Transport, jewellery, transports,
                                         wilderness_level)
from rlscape.sim.equipment import WEAPON
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import COINS, CharacterState


@cache
def teleports() -> tuple[Transport, ...]:
    return tuple(t for t in transports() if t.start is None)


@cache
def boats() -> tuple[Transport, ...]:
    return tuple(t for t in transports() if t.start is not None)


@cache
def next_charge() -> dict[int, int | None]:
    """A charged jewellery item -> what it becomes after a teleport (None: it crumbles)."""
    out: dict[int, int | None] = {}
    for _, _, crumbles, ids in jewellery().values():
        for i, item in enumerate(ids):
            out[item] = ids[i + 1] if i + 1 < len(ids) else None
    return out


def home_ready(state: CharacterState, elapsed: int = 0) -> bool:
    """Whether the home teleport can be cast `elapsed` ticks into the current step (30 minutes after the last)."""
    return state.tick + elapsed >= state.home_teleport_ready


def held(state: CharacterState, item: int) -> bool:
    return state.inventory.get(item, 0) > 0 or item in state.equipment.values()


def _runes_needed(state: CharacterState, runes: tuple[tuple[int, int], ...]) -> dict[int, int]:
    staff, staves = state.equipment.get(WEAPON), gd.staff_runes()
    return {rune: n for rune, n in runes if staff not in staves.get(rune, ())}


def _armed(state: CharacterState) -> bool:
    """Carrying or wearing a weapon or armour, as Entrana's monks see it (approximated: equipment with combat
    bonuses)."""
    items = gd.items()
    return any(item in items and items[item].equipment_slot is not None and any(items[item].bonuses)
               for item in (*state.inventory, *state.equipment.values()))


def can_use(state: CharacterState, transport: Transport, origin: tuple[int, int, int], coins: int) -> bool:
    """Whether the character can take the transport from `origin` (a teleport) or its boarding tile (a boat), with
    `coins` to spend."""
    if transport.quests and not set(transport.quests) <= state.progress.quests_complete:
        return False
    if transport.start is None and wilderness_level(origin) > transport.wilderness_limit:
        return False
    if transport.magic and state.level("magic") < transport.magic:
        return False
    if any(state.boosted(skill) < level for skill, level in transport.skills):
        return False
    if transport.runes and any(state.inventory.get(rune, 0) < n
                               for rune, n in _runes_needed(state, transport.runes).items()):
        return False
    if transport.items:
        if transport.consumed and not any(state.inventory.get(i, 0) > 0 for i in transport.items):
            return False
        if not transport.consumed and not any(held(state, i) for i in transport.items):
            return False
    if transport.coins > coins:
        return False
    return not (transport.no_arms and _armed(state))


@cache
def _teleport_skills() -> tuple[str, ...]:
    """The skills, Magic aside, a teleport needs a level in (its quest's own requirement)."""
    return tuple(sorted({skill for t in teleports() for skill, _ in t.skills}))


@cache
def _teleport_items() -> frozenset[int]:
    return frozenset(i for t in teleports() for i in (*t.items, *(rune for rune, _ in t.runes)))


_usable: dict[tuple, tuple[Transport, ...]] = {}


def usable_teleports(state: CharacterState) -> tuple[Transport, ...]:
    """The teleports the character can use from anywhere outside the Wilderness (callers check its depth and
    whether the home teleport is ready), remembered by what decides it: the teleport items and runes held, what's
    worn, quests, Magic and the other levels a teleport needs."""
    relevant = _teleport_items()
    key = (tuple(sorted((i, n) for i, n in state.inventory.items() if i in relevant)),
           tuple(sorted(state.equipment.items())), state.progress.quests_complete, state.level("magic"),
           tuple(state.boosted(skill) for skill in _teleport_skills()))
    if key not in _usable:
        if len(_usable) > 100_000:
            _usable.clear()
        _usable[key] = tuple(t for t in teleports() if can_use(state, t, (0, 0, 0), 0))
    return _usable[key]


def _take(state: CharacterState, item: int) -> None:
    state.inventory[item] -= 1
    if state.inventory[item] == 0:
        del state.inventory[item]


def use(state: CharacterState, transport: Transport, at: int) -> None:
    """Pay for the transport, taken at tick `at`, and take what it gives: runes, a charge, the item or the fare, the
    home teleport's cooldown (from the teleport); its XP."""
    if transport.kind == "home":
        state.home_teleport_ready = at + transport.ticks + HOME_COOLDOWN_TICKS
    if transport.kind == "abyss":  # the Mage of Zamorak's teleport skulls (AbyssPlugin.teleport; the prayer drain: OQ-48)
        state.skulled_until = at + transport.ticks + ABYSS_SKULL_TICKS
    for rune, n in _runes_needed(state, transport.runes).items():
        for _ in range(n):
            _take(state, rune)
    if transport.items and transport.kind == "jewellery":
        # the piece closest to running out goes first, as a player keeps the full ones
        item = max((i for i in transport.items if held(state, i)), key=transport.items.index)
        after = next_charge()[item]
        slot = next((s for s, worn in state.equipment.items() if worn == item), None)
        if slot is not None:
            if after is None:
                del state.equipment[slot]
            else:
                state.equipment[slot] = after
        else:
            _take(state, item)
            if after is not None:
                state.add(after)
    elif transport.items and transport.consumed:
        _take(state, next(i for i in transport.items if state.inventory.get(i, 0) > 0))
    if transport.coins:
        state.inventory[COINS] -= transport.coins
        if state.inventory[COINS] == 0:
            del state.inventory[COINS]
    for skill, xp in transport.xp:
        i = SKILL_INDEX[skill]
        state.xp[i] = min(state.xp[i] + xp, MAX_XP)
