"""Agility (sim v1; Caleb, 2026-11-08, OQ-2: "Agility should add course laps"; Choice D: the Gnome Stronghold, the
Barbarian Outpost and the Wilderness). The spec is docs/sim-v1-skills-draft.md §3.

The paths, `agility_<course>` (AgilityLaps): walk to the course, cross its entry once if it has one (the Barbarian
Outpost's pipe, Agility 35; the Wilderness course's door and ridge, Agility 52), then run laps until the option's time
is up, as rlscape.gamedata.agility has the courses: each obstacle's XP as it's passed, and the lap bonus at the lap's
last flag. An obstacle that can fail is rolled at the character's Agility as it stands (AgilityHandler.hasFailed;
`fail_chance`), again after each fall; a fall hits (a twelfth of the hitpoints left, or 26% in the lava) and costs its
measured recovery, and the lap goes on from the obstacle the course resumes at (the Barbarian ledge's falls skip to
the walls, so that lap has no bonus).

The times are the server's (scripts/measure_agility.py, 2026-11-08): each obstacle's ticks from its click to the next
one's as laps run (the last's to the next lap's first click, so the walk round is in it), the first obstacle's from the
course's start tile, each fall's ticks from its click to the next click, and the entry's.

Hitpoints, as thieving's (rlscape.sim.thieving): it eats at or below the retreat point, or the course's largest fall
hit if that's higher, and stops when it has no food left then. The Gnome Stronghold can't fail, so it never eats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import inf, isfinite

import numpy as np

from rlscape.gamedata.agility import COURSES, Course, Obstacle, fail_chance, fall_hit
from rlscape.sim.health import EAT_TICKS, eat_one, foods_held, regenerate, retreat_hp
from rlscape.sim.movement import reachable, walk
from rlscape.sim.options import COMPLETED, OUT_OF_FOOD, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import CharacterState
from rlscape.sim.transport import home_ready
from rlscape.travel import travel_ticks

TICKS_PER_HOUR = 6000


@dataclass(frozen=True)
class CourseTimes:
    """A course's measured times, in ticks (scripts/measure_agility.py)."""

    obstacles: tuple[float, ...]  # each obstacle's, click to the next click, as laps run
    first: float  # the lap's first obstacle's, clicked from the course's start tile
    falls: dict[int, float]  # a failing obstacle's fall: its click to the next click
    entry: float = 0.0  # the entry's, from its approach tile to the first obstacle's click
    entry_fall: float = 0.0  # a fall on the entry (the Wilderness ridge into the wolf pit), to the next try's click
    # the extra ticks of an obstacle's success after a fall (the retry's walk from where the fall left it), at the
    # obstacle tried again, or where a fall's lap resumes
    after_fall: dict[int, float] = field(default_factory=dict)


# Measured on the server at 50 ms ticks, 2026-11-08 (results/calibration/agility-20261108-*.json)
TIMES = {
    # 10 laps at Agility 1, every lap 74 ticks (gnome-a1)
    "gnome": CourseTimes((18, 7, 6, 12, 6, 8, 17), 11, {}),
    # 33 laps at Agility 15, 35 and 75 (barbarian-a15, -a35, -a75): the rope swing's fail does nothing (8.4 ticks to
    # the next click, which then starts at the rope: 4 fewer), a log fall swims out and walks back (28.1, and the
    # retry's walk 3 more), a ledge fall goes on at the walls (20, and the first wall's walk 5 more)
    # (barbarian-entry: the pipe from its north end, 7 ticks to the rope's click)
    "barbarian": CourseTimes((9, 17, 6, 9, 6, 9, 6, 9), 5, {0: 8.4, 1: 28.1, 3: 20.0}, 7,
                             after_fall={0: -4, 1: 3, 5: 5}),
    # 33 laps at Agility 52 and 99 (wilderness-a52, -a99): the rope swing's fail does nothing (8 ticks), a fall into the
    # lava 27, one onto the log's spikes 105.6 (the pit's ladder up and back round), and the retry's walk 6 more. The
    # entry (wilderness-entry-a52): 19 ticks over the ridge to the pipe's click; a fall into the wolf pit about 40 (one
    # run of three falls, rough: two other runs never found the way out, to measure again)
    "wilderness": CourseTimes((16, 7, 17, 20, 15), 11, {1: 8.0, 2: 27.0, 3: 105.6}, 19, 40,
                              after_fall={1: -2, 3: 6}),
}


class AgilityLaps(Option):
    """agility_<course>: laps of an agility course until the option's time is up."""

    family = "gathering"
    task = "agility"
    skill = "agility"

    def __init__(self, course: Course):
        self.course, self.times, self.id = course, TIMES[course.key], f"agility_{course.key}"

    @property
    def tile(self) -> tuple[int, int, int]:
        """Where the path walks to: the entry's approach, or the course's start."""
        return self.course.approach or self.course.start

    def level_needed(self) -> int:
        return max(self.course.level, self.course.entry.level if self.course.entry else 0)

    def largest_hit(self, state: CharacterState) -> int:
        """The most a fall on this course can take at full hitpoints."""
        hits = [o.hit for o in (*self.course.obstacles, self.course.entry) if o is not None and o.fail]
        return max((fall_hit(state.max_hp(), h) for h in hits), default=0)

    def eat_below(self, state: CharacterState) -> float:
        """Eat at or below this HP: the retreat point, or the largest fall hit if that is higher; never on a course
        that can't fail."""
        largest = self.largest_hit(state)
        return max(retreat_hp(state), largest) if largest else 0.0

    def available(self, state: CharacterState) -> bool:
        return (state.level("agility") >= self.level_needed() and reachable(state, self.tile)
                and (state.hp > self.eat_below(state) or bool(foods_held(state))))

    def _attempt(self, state: CharacterState, rng: np.random.Generator, o: Obstacle) -> bool:
        """Roll one try at the obstacle: True if it's passed."""
        if o.fail is None:
            return True
        return rng.random() >= fail_chance(state.level("agility"), *o.fail)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        course, times, agility = self.course, self.times, SKILL_INDEX["agility"]
        elapsed = walk(state, self.tile, budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED)
        regenerate(state, elapsed)
        last_flag = max(o.flag for o in course.obstacles if o.flag is not None)

        def gain(xp: float) -> None:
            state.xp[agility] = min(state.xp[agility] + xp, MAX_XP)

        def spend(ticks: float) -> bool:
            """Advance the clock; False once the option's time is up."""
            nonlocal elapsed
            step = int(round(ticks))
            if elapsed + step > budget:
                regenerate(state, budget - elapsed)
                elapsed = budget
                return False
            elapsed += step
            regenerate(state, step)
            return True

        def fed() -> bool:
            """Eat while at or below the eating point; False when there's no food left then."""
            while state.hp <= self.eat_below(state):
                if not eat_one(state):
                    return False
                if not spend(EAT_TICKS):
                    return True
            return True

        if course.entry is not None:
            if not fed():
                return OptionResult(elapsed, OUT_OF_FOOD, regenerated=True)
            while not self._attempt(state, rng, course.entry):  # the ridge into the wolf pit, then again
                state.hp -= fall_hit(state.hp, course.entry.hit)
                if not spend(times.entry_fall) or not fed():
                    return self._end(state, elapsed, budget)
            if not spend(times.entry):
                return self._end(state, elapsed, budget)
            gain(course.entry.xp)
        state.location = course.start
        i, first, bonus, extra_at = 0, True, True, None
        while True:
            o = course.obstacles[i]
            if o.fail is not None and not fed():
                return OptionResult(elapsed, OUT_OF_FOOD, regenerated=True)
            if not self._attempt(state, rng, o):
                state.hp -= fall_hit(state.hp, o.hit)
                if not spend(times.falls[i]):
                    return self._end(state, elapsed, budget)
                if o.resume is not None:  # the lap goes on further along, without this obstacle's flag
                    i, bonus = o.resume, False
                extra_at = i
                continue
            ticks = times.first if first and i == 0 else times.obstacles[i]
            if extra_at == i:
                ticks, extra_at = ticks + times.after_fall.get(i, 0.0), None
            first = False
            if not spend(ticks):  # the XP comes as the obstacle's done
                return self._end(state, elapsed, budget)
            gain(o.xp)
            if o.flag == last_flag:
                if bonus:
                    gain(course.lap_bonus)
                bonus = True  # the flags are cleared either way (AgilityCourse.finish)
            i = (i + 1) % len(course.obstacles)

    def _end(self, state: CharacterState, elapsed: int, budget: int) -> OptionResult:
        if elapsed >= budget:
            return OptionResult(budget, COMPLETED, regenerated=True)
        return OptionResult(elapsed, OUT_OF_FOOD, regenerated=True)

    def expected_rate(self, state: CharacterState) -> tuple[float, float]:
        """XP and ticks of an average lap at the character's Agility now: each failing obstacle's expected falls
        (p / (1 - p)) times its fall, and a resuming fall's lost obstacles and bonus as their chance."""
        course, times, level = self.course, self.times, state.level("agility")
        last_flag = max(o.flag for o in course.obstacles if o.flag is not None)
        xp = ticks = 0.0
        keep = 1.0  # the chance the lap gets this far without a resuming fall
        skipped: dict[int, float] = {}
        resumed: dict[int, float] = {}  # the chance a lap resumes at an obstacle after a fall
        for i, o in enumerate(course.obstacles):
            reach = 1.0 - skipped.get(i, 0.0)
            p = fail_chance(level, *o.fail) if o.fail else 0.0
            ticks += resumed.get(i, 0.0) * times.after_fall.get(i, 0.0)
            if o.resume is None:
                falls = p / (1 - p) if p < 1 else 1e6
                ticks += reach * (falls * times.falls.get(i, 0.0) + times.obstacles[i]
                                  + p * times.after_fall.get(i, 0.0))  # the success after a first fall
                xp += reach * o.xp
            else:  # one try: a fall skips to `resume`
                ticks += reach * (p * times.falls.get(i, 0.0) + (1 - p) * times.obstacles[i])
                xp += reach * (1 - p) * o.xp
                for j in range(i + 1, o.resume):
                    skipped[j] = skipped.get(j, 0.0) + reach * p
                resumed[o.resume] = resumed.get(o.resume, 0.0) + reach * p
                keep *= 1 - reach * p
            if o.flag == last_flag:
                xp += keep * course.lap_bonus
        return xp, ticks


    def rate(self, state: CharacterState, duration_ticks: int) -> tuple[float, float, float, float]:
        """(Agility XP/hr, 0, gp/hr, travel) for the skilling slots: laps at the expected rate at the Agility now,
        after the walk there and the entry. No gp: food eaten isn't counted against it."""
        entry = self.course.entry
        p = fail_chance(state.level("agility"), *entry.fail) if entry is not None and entry.fail else 0.0
        travel = (travel_ticks(state.location, self.tile, home_ready(state)) + self.times.entry
                  + p / (1 - p) * self.times.entry_fall)
        lap_xp, lap_ticks = self.expected_rate(state)
        if not isfinite(travel) or lap_ticks <= 0:
            return 0.0, 0.0, 0.0, inf
        laps = max(duration_ticks - travel, 0.0) / lap_ticks
        per_hour = TICKS_PER_HOUR / duration_ticks
        return (laps * lap_xp + (entry.xp if entry else 0.0)) * per_hour, 0.0, 0.0, travel


def agility_paths() -> list[AgilityLaps]:
    return [AgilityLaps(c) for key, c in COURSES.items() if key in TIMES]
