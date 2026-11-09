"""The skilling slots' rate model prices a gathering site's aggressive monsters (rlscape.sim.aggression.gathering_share,
2026-11-08): the share of the option's XP per tick its own run keeps, with the aggressors against without them."""

from __future__ import annotations

import pytest

from rlscape.gamedata import server as gd
from rlscape.sim.aggression import _SHARES, gathering_share, no_aggression
from rlscape.sim.skilling import SkillingSlots, _site, path_options, path_rate
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")


def character(**levels: int) -> CharacterState:
    state = CharacterState.fresh()
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.hp = state.max_hp()
    return state


def paths() -> dict:
    return {p.id: p for p in path_options()}


@needs_server
def test_a_fresh_character_keeps_about_half_the_willows_rate_and_a_strong_one_all_of_it():
    """The Dark wizards there pick a character of combat level 14 or under (twice their 7): a fresh woodcutter is
    attacked, runs away and back, and keeps about half its XP per tick; at combat 34 none picks it."""
    willow, fresh = paths()["wc_willow"], character(woodcutting=30)
    share = gathering_share(willow.gather, fresh, _site(willow.gather), "woodcutting")
    assert 0.2 < share < 0.8
    strong = character(woodcutting=30, attack=30, strength=30, defence=30, hitpoints=30)
    assert gathering_share(willow.gather, strong, _site(willow.gather), "woodcutting") == 1.0
    burn = paths()["wc_willow_burn"]
    with no_aggression():
        before, before_burn = path_rate(willow, fresh), path_rate(burn, fresh)
    assert path_rate(willow, fresh).xp == pytest.approx(before.xp * share)
    assert path_rate(burn, fresh).xp == pytest.approx(before_burn.xp * share)  # the same gathering, burned after


@needs_server
def test_no_aggression_leaves_the_cache_alone():
    willow, fresh = paths()["wc_willow"], character(woodcutting=30)
    _SHARES.clear()
    with no_aggression():
        assert gathering_share(willow.gather, fresh, _site(willow.gather), "woodcutting") == 1.0
    assert not _SHARES
    assert gathering_share(willow.gather, fresh, _site(willow.gather), "woodcutting") < 1.0 and len(_SHARES) == 1


@needs_server
def test_a_fresh_fisher_ranks_the_swamps_shrimp_above_draynors():
    """Draynor's Dark wizards kill a level-3 fisher on about half its runs away (decision log, 2026-11-01), so its
    shrimp now rank below Lumbridge Swamp's, which nothing guards."""
    fresh = character()
    ids = [c.path.id for i in range(4) if (c := SkillingSlots().candidate(fresh, "fishing", i)) is not None]
    assert ids.index("fish_shrimp_swamp") < ids.index("fish_shrimp")
    assert path_rate(paths()["fish_shrimp"], fresh).xp < path_rate(paths()["fish_shrimp_swamp"], fresh).xp
