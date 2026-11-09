"""The agility courses (sim v1; Caleb, 2026-11-08, OQ-2 Choice D: the Gnome Stronghold, the Barbarian Outpost and the
Wilderness; the Agility Pyramid and Brimhaven left out), from the server's course handlers in
content/global/skill/agility: each obstacle in lap order, its XP, whether it can fail and how, and the lap bonus.

A lap (AgilityCourse): every obstacle flags its index as it's passed; flagging the last index with every flag set
gives the lap bonus and clears the flags. An index past the course's size isn't flagged (setObstacleFlag), so the
Barbarian Outpost's third low wall gives its XP but isn't part of the lap. A failed obstacle flags nothing.

Failing (AgilityHandler.hasFailed(player, level, failChance)): it fails when (1 + Agility - level) / 100 times one
uniform draw is at most failChance times another, and never more than 69 levels above `level` (fail_chance). The hit
on a fall is AgilityCourse.getHitAmount (a twelfth of the hitpoints left, at least 2), or for the Wilderness's
stepping stones 26% of them, as each handler has it.

The obstacles' ids, options and tiles were checked on the server (debug_nearby, 2026-11-08). The times aren't here:
they're measured on the server (scripts/measure_agility.py).
"""

from __future__ import annotations

from dataclasses import dataclass

TWELFTH = "twelfth"  # AgilityCourse.getHitAmount: lifepoints / 12, at least 2
LAVA = "lava"  # WildernessCourse.handleSteppingStones: (lifepoints * 0.26).toInt()


@dataclass(frozen=True)
class Obstacle:
    name: str  # the scenery's name, as a click finds it
    ids: tuple[int, ...]
    option: str
    xp: float
    flag: int | None  # the course index it flags (None: not part of the lap check)
    fail: tuple[int, float] | None = None  # hasFailed's (level, failChance)
    hit: str | None = None  # how a fall hurts (TWELFTH, LAVA)
    level: int = 0  # its own Agility requirement
    at: tuple[int, int] | None = None  # the tile, where it shares its id with another of the course's
    resume: int | None = None  # the obstacle a lap goes on from after a fall here (None: this one again)
    inert_fail: bool = False  # a fail does nothing: the character stands where it was, and clicks again
    pit: tuple[int, int, int] | None = None  # the pit a fall drops into, whose aggressive monsters attack (OQ-46)


@dataclass(frozen=True)
class Course:
    key: str
    name: str
    level: int  # to do a lap
    lap_bonus: float
    start: tuple[int, int, int]  # where a lap's first obstacle is clicked from
    obstacles: tuple[Obstacle, ...]
    entry: Obstacle | None = None  # crossed once to get onto the course (not part of a lap)
    approach: tuple[int, int, int] | None = None  # where the entry is clicked from

    @property
    def lap_xp(self) -> float:
        return sum(o.xp for o in self.obstacles) + self.lap_bonus


GNOME = Course("gnome", "Gnome Stronghold", 1, 39.0, (2474, 3436, 0), (  # GnomeStrongholdCourse: 7 flags
    Obstacle("Log balance", (2295,), "Walk-across", 7.5, 0),
    Obstacle("Obstacle net", (2285,), "Climb-over", 7.5, 1),
    Obstacle("Tree branch", (35970,), "Climb", 5.0, 2),
    Obstacle("Balancing rope", (2312,), "Walk-on", 7.5, 3),
    Obstacle("Tree branch", (2314, 2315), "Climb-down", 5.0, 4),
    Obstacle("Obstacle net", (2286,), "Climb-over", 7.5, 5),
    Obstacle("Obstacle pipe", (4058, 154), "Squeeze-through", 7.5, 6),
))

# BarbarianOutpostCourse: 6 flags. The course is entered by the outpost's pipe (PipeShortcut: Agility 35), and
# its gate (2115, 2116) needs the Barcrawl, which `spawn` completes.
BARBARIAN = Course("barbarian", "Barbarian Outpost", 35, 46.2, (2551, 3554, 0), (
    # a fail does nothing: AgilityHandler.fail plays out only with an animation, and the swing passes none, so the
    # character stands at the rope and clicks again (the pit below, 2549, 9951, is never reached; seen on the server)
    Obstacle("Ropeswing", (2282,), "Swing-on", 22.0, 0, (1, 0.1), inert_fail=True),
    Obstacle("Log balance", (2294,), "Walk-across", 13.5, 1, (1, 0.5), TWELFTH),  # into the water
    Obstacle("Obstacle net", (20211,), "Climb-over", 8.0, 2),
    # a fall lands west of the net, which can't be climbed from that side: the lap goes on at the walls, without the
    # ledge's flag, so without its bonus (measured, 2026-11-08)
    Obstacle("Balancing ledge", (2302,), "Walk-across", 22.0, 3, (1, 0.3), TWELFTH, resume=5),
    Obstacle("Ladder", (3205,), "Climb-down", 0.0, None),  # off the ledge's platform
    Obstacle("Crumbling wall", (1948,), "Climb-over", 13.5, 4, at=(2536, 3553)),
    Obstacle("Crumbling wall", (1948,), "Climb-over", 13.5, 5, at=(2539, 3553)),  # the lap's last flag
    Obstacle("Crumbling wall", (1948,), "Climb-over", 13.5, None, at=(2542, 3553)),  # flag 6: past the course's size
), entry=Obstacle("Obstacle pipe", (20210,), "Squeeze-through", 0.0, None, level=35), approach=(2552, 3561, 0))
# (PipeShortcut configures 10 XP for the pipe, but AgilityShortcut never gives a shortcut's XP and the pipe's walk passes
# none: no XP, checked on the server, 2026-11-08)

# WildernessCourse: 5 flags. Entered from the south through the door and over the ridge (Agility 52, 15 XP; it can
# fail into the wolf pit).
WILDERNESS = Course("wilderness", "Wilderness", 52, 499.0, (3004, 3937, 0), (
    Obstacle("Obstacle pipe", (2288,), "Squeeze-through", 12.5, 0, level=49, at=(3004, 3938)),
    Obstacle("Ropeswing", (2283,), "Swing-on", 20.0, 1, (1, 0.1), inert_fail=True),  # as the Barbarian swing's
    Obstacle("Stepping stone", (37704,), "Cross", 20.0, 2, (1, 0.3), LAVA),  # into the lava
    # onto the spikes in a pit below, among aggressive skeletons (level 25), climbed out by its ladder (OQ-46)
    Obstacle("Log balance", (2297,), "Walk-across", 20.0, 3, (1, 0.5), TWELFTH, pit=(2998, 10345, 0)),
    Obstacle("Rocks", (2328,), "Climb", 0.0, 4),
), entry=Obstacle("Door", (2309,), "Open", 15.0, None, (1, 0.3), TWELFTH, level=52), approach=(2998, 3916, 0))

COURSES = {c.key: c for c in (GNOME, BARBARIAN, WILDERNESS)}


def fail_chance(agility: int, level: int, chance: float) -> float:
    """AgilityHandler.hasFailed's chance: a = (1 + agility - level) / 100; it fails when a U1 <= chance U2 for two
    uniform draws, so 1 - a / (2 chance) when a <= chance, else chance / (2 a); never more than 69 levels above."""
    diff = agility - level
    if diff > 69:
        return 0.0
    a = (1 + diff) * 0.01
    if a <= 0:
        return 1.0
    return 1 - a / (2 * chance) if a <= chance else chance / (2 * a)


def fall_hit(hitpoints: int, hit: str | None) -> int:
    """The damage a fall deals at `hitpoints` left."""
    if hit == TWELFTH:
        return max(hitpoints // 12, 2)
    if hit == LAVA:
        return int(hitpoints * 0.26)
    return 0
