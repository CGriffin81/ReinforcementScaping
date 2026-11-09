"""Essence pouches in the sim (Caleb, OQ-40 (c): as the server gives them; rlscape.sim.pouches), against the server's
PouchManager.kt and what scripts/measure_abyss.py --pouches saw on it."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import runecrafting as rcd
from rlscape.gamedata import server as gd
from rlscape.sim import abyss, pouches
from rlscape.sim.runecrafting import AbyssRunecraft, RunecraftAtRuins
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
SMALL, MEDIUM, LARGE, GIANT = 5509, 5510, 5512, 5514
ALL = {SMALL: 1, MEDIUM: 1, LARGE: 1, GIANT: 1}


def character(inventory: dict[int, int] | None = None, bank: dict[int, int] | None = None,
              **levels: int) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory, state.bank, state.equipment = dict(inventory or {}), dict(bank or {}), {}
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.hp = state.max_hp()
    return state


@needs_server
def test_the_pouches_are_the_servers():
    """PouchManager.kt's RCPouch(capacity, charges, level) and its decay steps."""
    p = rcd.pouches()
    assert [(i, x.capacity, x.charges, x.level, x.decay) for i, x in p.items()] == [
        (SMALL, 3, 3, 1, 0), (MEDIUM, 6, 264, 25, 1), (LARGE, 9, 186, 50, 2), (GIANT, 12, 140, 75, 3)]
    assert p[MEDIUM].decayed == 5511 and p[SMALL].decayed is None


@needs_server
def test_a_medium_pouch_decays_on_its_44th_fill_as_on_the_server():
    """Measured: 264 essence go in 6 at a time; the 44th fill finds the charges out, so the capacity falls to 5, the
    next decay is 45 away, and that fill puts in 5."""
    state = character({MEDIUM: 1, rcd.PURE_ESSENCE: 27}, runecrafting=99)
    seen = []
    for n in range(1, 45):
        put = pouches.fill(state, MEDIUM)
        seen.append((n, pouches.capacity(state, MEDIUM), pouches.charges(state, MEDIUM), put))
        assert pouches.empty(state, MEDIUM) == put
    assert seen[-3:] == [(42, 6, 12, 6), (43, 6, 6, 6), (44, 5, 45, 5)]
    assert pouches.decayed(state)
    pouches.repair(state)
    assert (pouches.capacity(state, MEDIUM), pouches.charges(state, MEDIUM)) == (6, 264) and not pouches.decayed(state)


@needs_server
def test_a_pouch_worn_to_nothing_disappears_and_its_kind_starts_afresh():
    state = character({LARGE: 1, rcd.PURE_ESSENCE: 20}, runecrafting=99)
    state.pouches[LARGE] = (1, 1)  # one decay from nothing
    assert pouches.fill(state, LARGE) == 0
    assert LARGE not in state.inventory and LARGE not in state.pouches and state.inventory[rcd.PURE_ESSENCE] == 20


@needs_server
def test_a_fill_takes_the_kind_held_more_of_needs_the_level_and_an_empty_needs_free_slots():
    """RunePouchPlugin: the majority kind, nothing when equal; PouchManager: one kind a pouch, the level checked by
    the paths (fillable); withdrawFromPouch: as many as the free slots take."""
    state = character({SMALL: 1, rcd.RUNE_ESSENCE: 2, rcd.PURE_ESSENCE: 2})
    assert pouches.fill(state, SMALL) == 0  # equal
    state.inventory[rcd.PURE_ESSENCE] = 5
    assert pouches.fill(state, SMALL) == 3 and state.pouch_essence[SMALL] == (rcd.PURE_ESSENCE, 3)
    assert pouches.fillable(character({GIANT: 1}, runecrafting=74)) == []
    assert pouches.fillable(character({GIANT: 1, MEDIUM: 1}, {SMALL: 1}, runecrafting=75)) == [SMALL, MEDIUM, GIANT]
    full = character({SMALL: 1, rcd.PURE_ESSENCE: 27})
    full.pouch_essence[SMALL] = (rcd.PURE_ESSENCE, 3)
    assert pouches.empty(full, SMALL) == 0 and full.pouch_essence[SMALL] == (rcd.PURE_ESSENCE, 3)  # no free slot


@needs_server
def test_an_abyssal_kill_can_drop_the_next_pouch_lacked_and_no_other_kill_draws():
    """AbyssalNPC.finalizeDeath: 12 in 750, the next pouch the character lacks, small to giant (inventory, bank,
    equipment); a kill of anything else doesn't touch the rng."""
    rng = np.random.default_rng(0)
    state = character({}, {SMALL: 1})
    drops = [pouches.drop(state, 2264, rng) for _ in range(5000)]
    got = [d for d in drops if d is not None]
    assert set(got) == {MEDIUM} and 50 < len(got) < 110  # about 80
    before = rng.bit_generator.state
    assert pouches.drop(state, 81, rng) is None and rng.bit_generator.state == before
    every = character(ALL)  # holding all four, nothing more drops
    assert all(pouches.drop(every, 2263, np.random.default_rng(s)) is None for s in range(200))


@needs_server
def test_a_ruins_trip_fills_its_pouches_and_crafts_them_too():
    """rc_air with all four at Runecrafting 99: the pouches out of the bank, the load filling them in two rounds (23
    essence, then the giant's last 7) and the slots topped up after each; inside, the first craft, the lock, four
    empties and the second craft: 53 essence a trip."""
    path = RunecraftAtRuins("air")
    state = character({}, {**ALL, rcd.PURE_ESSENCE: 500, rcd.talismans()["air"]: 1}, runecrafting=99)
    path._restock(state)
    carried = state.inventory.get(rcd.PURE_ESSENCE, 0) + sum(a for _, a in state.pouch_essence.values())
    assert carried == 28 - 4 - 1 + 30 and all(state.inventory.get(i) == 1 for i in ALL)
    state.location = path.ruins.base
    result = path._work(state, 10_000)
    assert state.inventory.get(556) == carried * rcd.runes()["air"].per_essence(99) and not state.pouch_essence
    plain = character({}, {rcd.PURE_ESSENCE: 500, rcd.talismans()["air"]: 1}, runecrafting=99)
    path._restock(plain)
    plain.location = path.ruins.base
    # two rounds of filling (the first load's 23 essence leave the giant short), and inside two of emptying and
    # crafting (the first craft frees 22 slots for the pouches' 30)
    extra = (pouches.FILL_TICKS * 5 + 2 * pouches.REWITHDRAW_TICKS + 5 * pouches.EMPTY_TICKS
             + 2 * (pouches.LOCK_TICKS + pouches.CRAFT_AGAIN_TICKS))
    assert result.ticks == path._work(plain, 10_000).ticks + extra


@needs_server
def test_an_abyss_trip_with_a_decayed_pouch_goes_by_the_dark_mage():
    state = character({}, {MEDIUM: 1, rcd.PURE_ESSENCE: 500, 379: 50}, runecrafting=99, hitpoints=99, defence=99,
                      agility=99)
    state.pouches[MEDIUM] = (5, 45)
    path = AbyssRunecraft("nature")
    result = path.run(state, np.random.default_rng(0), 600)
    assert result.detail["trips"] >= 1 and not pouches.decayed(state)
    fresh = character({}, {}, runecrafting=99, hitpoints=99, defence=99, agility=99)
    direct = abyss.cross(fresh, np.random.default_rng(3), "nature")
    other = character({}, {}, runecrafting=99, hitpoints=99, defence=99, agility=99)
    detour = abyss.cross(other, np.random.default_rng(3), "nature", repair=True)
    assert detour.ticks > direct.ticks  # the same draws, the walk by him and his repair added


@needs_server
def test_the_observation_shows_each_pouchs_capacity():
    from rlscape.envs.sim_env import SimEnv
    env = SimEnv()
    env.reset(seed=0)
    state = env.sim.state
    part = lambda: list(env.encoder.encode(state, env.sim.action_mask())[env.encoder.parts["pouches"]])  # noqa: E731
    assert part() == [1.0, 0.0, 0.0, 0.0]  # the small pouch, in the bank from the start
    state.bank[MEDIUM] = 1
    state.pouches[MEDIUM] = (3, 27)
    assert part() == pytest.approx([1.0, 0.5, 0.0, 0.0])
