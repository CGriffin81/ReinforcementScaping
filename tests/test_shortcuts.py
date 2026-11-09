"""The Agility shortcuts in the travel model (sim v1, OQ-16 (a)): ported from their handlers, taken at their level."""

from __future__ import annotations

import pytest

from rlscape.gamedata import server as gd
from rlscape.gamedata.shortcuts import LINKS
from rlscape.gamedata.transports import transports
from rlscape.sim.movement import route, route_ticks, walk
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
SHORTCUTS = gd.SERVER_CONTENT / "global" / "skill" / "agility" / "shortcuts"
FILES = {"falador_wall": "CrumblingWallShortcut.java", "coal_trucks_log": "LogBalanceShortcut.java",
         "rellekka_log": "LogBalanceShortcut.java", "ardougne_log": "LogBalanceShortcut.java",
         "lum_stone": "SteppingStoneShortcut.kt", "al_kharid_pit": "AlKharidPitShortcut.java",
         "lumberyard_fence": "FenceJumpShortcut.java"}
OUTSIDE_FALADOR, FALADOR_WEST_BANK = (2930, 3355, 0), (2946, 3368, 0)


def character(agility: int, at: tuple[int, int, int]) -> CharacterState:
    state = CharacterState.fresh()
    state.xp[SKILL_INDEX["agility"]] = float(XP_FOR_LEVEL[agility])
    state.location = at
    return state


@needs_server
def test_each_link_is_its_handlers_scenery_and_level():
    for link in LINKS:
        text = (SHORTCUTS / FILES[next(k for k in FILES if link.key.startswith(k))]).read_text(encoding="utf-8")
        assert all(str(i) in text for i in link.ids), link.key
        assert f", {link.level}" in text or f"{link.level})" in text, (link.key, link.level)
    assert {t.id for t in transports() if t.kind == "shortcut"} == {f"shortcut:{link.key}" for link in LINKS}


@needs_server
def test_falador_s_west_wall_is_taken_from_agility_5():
    """Into Falador from outside its west wall: round by the gate at Agility 4, over the crumbling wall at 5."""
    low, high = character(4, OUTSIDE_FALADOR), character(5, OUTSIDE_FALADOR)
    assert not route(low, FALADOR_WEST_BANK).transports
    assert [t.id for t in route(high, FALADOR_WEST_BANK).transports] == ["shortcut:falador_wall_in"]
    assert route_ticks(high, FALADOR_WEST_BANK) < route_ticks(low, FALADOR_WEST_BANK) / 3


@needs_server
def test_a_log_balance_gives_its_xp_on_the_way():
    """The coal trucks' log balance (Agility 20, 5 XP): a walk across it gives the XP, as the server's handler does."""
    link = next(link for link in LINKS if link.key == "coal_trucks_log_east")
    state = character(20, link.start)
    before = state.xp[SKILL_INDEX["agility"]]
    assert walk(state, link.end, 10_000) is not None and state.location == link.end
    assert state.xp[SKILL_INDEX["agility"]] - before == pytest.approx(5.0)
