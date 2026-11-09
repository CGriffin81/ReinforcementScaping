"""Agility in the sim (sim v1): the courses as the server's handlers have them, the fall chance, and the laps."""

from __future__ import annotations

import re
from dataclasses import replace

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.gamedata.agility import BARBARIAN, COURSES, GNOME, WILDERNESS, fail_chance, fall_hit
from rlscape.sim.agility import TIMES, AgilityLaps
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
AGILITY = gd.SERVER_CONTENT / "global" / "skill" / "agility"
FILES = {"gnome": "GnomeStrongholdCourse.kt", "barbarian": "BarbarianOutpostCourse.kt", "wilderness": "WildernessCourse.kt"}
LOBSTER = 379


def character(agility: int = 1, food: int = 0, **levels: int) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory = {LOBSTER: food} if food else {}
    for skill, level in {"agility": agility, **levels}.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.hp = state.max_hp()
    return state


def test_the_fall_chance_is_the_servers_two_draws():
    """AgilityHandler.hasFailed: (1 + Agility - level) / 100 times a uniform draw at most failChance times another."""
    rng = np.random.default_rng(0)
    for agility, chance in ((1, 0.1), (15, 0.5), (35, 0.3), (52, 0.1), (70, 0.5)):
        a = (1 + agility - 1) * 0.01
        drawn = np.mean(a * rng.random(200_000) <= rng.random(200_000) * chance)
        assert fail_chance(agility, 1, chance) == pytest.approx(drawn, abs=0.005)
    assert fail_chance(71, 1, 0.5) == 0.0  # 70 levels above: never
    assert fall_hit(99, "twelfth") == 8 and fall_hit(10, "twelfth") == 2 and fall_hit(50, "lava") == 13


@needs_server
@pytest.mark.parametrize("key", sorted(COURSES))
def test_each_course_is_its_handlers(key):
    """The lap bonus and the number of flags (AgilityCourse(player, size, bonus)), each obstacle's ids in the handler,
    and its XP among the handler's."""
    course, text = COURSES[key], (AGILITY / FILES[key]).read_text(encoding="utf-8")
    size, bonus = re.search(r"AgilityCourse\(player, (\d+), ([\d.]+)\)", text).groups()
    flags = [o.flag for o in course.obstacles if o.flag is not None]
    assert float(bonus) == course.lap_bonus and sorted(flags) == list(range(int(size)))
    for o in course.obstacles:
        if o.flag is None and not o.xp:
            continue  # not the course's own (the Barbarian ledge's ladder: ClimbActionHandler)
        assert all(str(i) in text for i in o.ids), o.name
        if o.xp:
            assert f"{o.xp}" in text or f"{o.xp:.2f}" in text, (o.name, o.xp)
    assert GNOME.lap_xp == 86.5 and BARBARIAN.lap_xp == pytest.approx(152.2) and WILDERNESS.lap_xp == 571.5


@needs_server
def test_gnome_laps_never_fall_and_give_86_5_a_lap():
    path = AgilityLaps(GNOME)
    state = character()
    state.location = GNOME.start
    before = state.xp[SKILL_INDEX["agility"]]
    times = TIMES["gnome"]
    laps = 10
    budget = round(times.first + sum(times.obstacles) * laps - times.obstacles[0] + times.first) + 1
    result = path.run(state, np.random.default_rng(0), budget)
    assert result.termination == "completed" and state.hp == state.max_hp()
    assert state.xp[SKILL_INDEX["agility"]] - before == pytest.approx(laps * 86.5)


@needs_server
@pytest.mark.parametrize("key,agility", [("gnome", 1), ("barbarian", 35), ("barbarian", 60), ("wilderness", 52),
                                         ("wilderness", 80)])
def test_the_laps_average_what_the_slots_rank_them_by(key, agility):
    """The lap loop's XP/hr over many runs from the course's start matches expected_rate's, the slots' model of it."""
    if key not in TIMES:
        pytest.skip(f"{key} not measured yet")
    course = replace(COURSES[key], entry=None, approach=None)  # laps alone, from the start
    path = AgilityLaps(course)
    xp_per_tick = []
    for seed in range(40):
        state = character(agility, food=28, hitpoints=99)
        state.location = course.start
        before = state.xp[SKILL_INDEX["agility"]]
        result = path.run(state, np.random.default_rng(seed), 3_000)
        xp_per_tick.append((state.xp[SKILL_INDEX["agility"]] - before) / result.ticks)
    lap_xp, lap_ticks = path.expected_rate(character(agility))
    assert np.mean(xp_per_tick) == pytest.approx(lap_xp / lap_ticks, rel=0.05)
