"""Barbarian Fishing in the sim (sim v1): BarbFishingPulse's fish, levels, XP and bait, and its two rankings."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim.barbfishing import BAITS, GROTTO, ROD, BarbFish, barbfishing_paths
from rlscape.sim.kits import kit
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
FEATHER, OFFCUTS, TROUT, SALMON, STURGEON = 314, 11334, 11328, 11330, 11332


def character(inventory: dict[int, int], fishing: int = 48, agility: int = 15, strength: int = 15) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory = dict(inventory)
    for skill, level in (("fishing", fishing), ("agility", agility), ("strength", strength)):
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.location = GROTTO
    return state


@needs_server
def test_a_try_goes_through_trout_salmon_and_sturgeon_in_order_at_their_levels():
    """Each fish needs its Fishing level, and salmon and sturgeon their Strength and Agility (30, 45)."""
    fish, weights, p_any = BarbFish.catch_odds(character({}))
    assert [f.item for f, _ in fish] == [TROUT] and p_any == pytest.approx(gd.fish_types()["LEAPING_TROUT"]
                                                                          .success_chance(48))
    fish, _, _ = BarbFish.catch_odds(character({}, fishing=70, agility=29, strength=99))
    assert [f.item for f, _ in fish] == [TROUT]  # Agility 29: no salmon or sturgeon
    fish, weights, p_any = BarbFish.catch_odds(character({}, fishing=70, agility=45, strength=45))
    assert [f.item for f, _ in fish] == [TROUT, SALMON, STURGEON]
    p = [gd.fish_types()[n].success_chance(70) for n in ("LEAPING_TROUT", "LEAPING_SALMON", "LEAPING_STURGEON")]
    assert weights * p_any == pytest.approx([p[0], (1 - p[0]) * p[1], (1 - p[0]) * (1 - p[1]) * p[2]])


@needs_server
def test_a_load_trains_fishing_agility_and_strength_and_uses_a_bait_a_fish():
    state = character({ROD: 1, OFFCUTS: 3, FEATHER: 100})
    before = {s: state.xp[SKILL_INDEX[s]] for s in ("fishing", "agility", "strength")}
    result = BarbFish().run(state, np.random.default_rng(0), 10_000)
    # 28 slots: the rod and the feathers, and the offcuts' slot once they're used up
    assert result.termination == "inventory_full" and state.inventory[TROUT] == 26
    gained = {s: state.xp[SKILL_INDEX[s]] - before[s] for s in before}
    assert gained == {"fishing": pytest.approx(26 * 50.0), "agility": pytest.approx(26 * 5.0),
                      "strength": pytest.approx(26 * 5.0)}
    assert OFFCUTS not in state.inventory and state.inventory[FEATHER] == 100 - 23  # offcuts first, then feathers


@needs_server
def test_it_needs_the_rod_bait_and_its_levels_and_ranks_in_two_skills():
    assert BarbFish().available(character({ROD: 1, FEATHER: 10}))
    assert not BarbFish().available(character({FEATHER: 10}))  # no rod
    assert not BarbFish().available(character({ROD: 1}))  # no bait
    assert not BarbFish().available(character({ROD: 1, FEATHER: 10}, fishing=47))
    assert not BarbFish().available(character({ROD: 1, FEATHER: 10}, agility=14))
    fishing, agility = barbfishing_paths()
    state = character({ROD: 1, FEATHER: 500})
    assert (fishing.skill, agility.skill) == ("fishing", "agility") and fishing.id == agility.id == "barb_fish"
    f, a = fishing.rate(state, 6000), agility.rate(state, 6000)
    assert f[0] == pytest.approx(10 * a[0]) and f[2] == a[2]  # 50 Fishing XP a trout to 5 Agility
    assert kit(state, "barbfishing") == {ROD, FEATHER} and set(BAITS) >= {FEATHER, OFFCUTS}
