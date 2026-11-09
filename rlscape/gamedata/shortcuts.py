"""The Agility shortcuts the travel model takes (sim v1; OQ-16 (a), Caleb, 2026-11-08: "Agility shortcuts with Agility",
added where the ranker would send a character), from the handlers in content/global/skill/agility/shortcuts. Each is
a pair of one-way links: where it's clicked from, the scenery, the option, where it lands, and the Agility it needs.
None of these can fail (each uses AgilityShortcut's constructor without a fail chance).

Chosen (Claude's choice, reversible) as the server's shortcuts whose two ends the travel map's planner joins only by a
long walk round, in places the sim travels: Falador's west wall (202 steps round, against 2 across), the log balances
by the coal trucks (242), Rellekka (216) and Ardougne (91), the stepping stone over the River Lum west of Varrock (157),
the Al Kharid pit (73) and the fence by Varrock's lumberyard (56). Left out: those into areas the sim doesn't travel
(Tirannwn's logs, Karamja's jungle and Shilo, the lighthouse's basalt rocks, the Trollheim climbs Caleb left out), the
dungeons' (the planner has no underground map) and the grapples (a mithril grapple and a crossbow).

The times are measured on the server (scripts/measure_shortcuts.py, results/calibration/shortcuts-20261108-2246-i5.json:
3 runs each way, every one the same): the click, from the start tile, to standing idle on the far end. A stepping
stone jumps a tile every 2 ticks. In a trip, a shortcut also costs TRIP_TICKS.
"""

from __future__ import annotations

from dataclasses import dataclass

# What a shortcut costs a trip beyond its own ticks: the approach and the click (2, on the server's trips from a couple
# of steps short) and the walk on's start, which the sim's walk overhead counts once a route. Fitted, as the boats'
# boarding was, on scripts/validate_travel.py's shortcut trips (the server's trips over the sim's, 2 to 6 ticks
# longer, mean 3.4; results/calibration/travel-validation-20261108-2247-i5.json).
TRIP_TICKS = 3


@dataclass(frozen=True)
class ShortcutLink:
    key: str
    ids: tuple[int, ...]  # the scenery clicked
    option: str
    start: tuple[int, int, int]  # where it's clicked from
    end: tuple[int, int, int]  # where it lands
    level: int  # Agility
    name: str  # the scenery's name, as a click finds it
    ticks: int  # measured: the click to standing on the far side, able to walk on
    xp: float = 0.0  # Agility XP it gives (measured: only the log balances' handler gives its XP)


LINKS = (
    # CrumblingWallShortcut: from inside (x >= 2936) to outside, or the reverse
    ShortcutLink("falador_wall_out", (11844,), "Climb-over", (2936, 3355, 0), (2934, 3355, 0), 5, "Crumbling wall", 4),
    ShortcutLink("falador_wall_in", (11844,), "Climb-over", (2934, 3355, 0), (2936, 3355, 0), 5, "Crumbling wall", 4),
    # LogBalanceShortcut, which gives its XP
    ShortcutLink("coal_trucks_log_east", (2296,), "Walk-across", (2598, 3477, 0), (2603, 3477, 0), 20, "Log balance", 7,
                 5.0),
    ShortcutLink("coal_trucks_log_west", (2296,), "Walk-across", (2603, 3477, 0), (2598, 3477, 0), 20, "Log balance", 7,
                 5.0),
    ShortcutLink("rellekka_log_north", (9322, 9324), "Walk-across", (2722, 3592, 0), (2722, 3596, 0), 48, "Log balance",
                 6, 1.0),
    ShortcutLink("rellekka_log_south", (9322, 9324), "Walk-across", (2722, 3596, 0), (2722, 3592, 0), 48, "Log balance",
                 6, 1.0),
    ShortcutLink("ardougne_log_west", (35997, 35999), "Walk-across", (2602, 3336, 0), (2598, 3336, 0), 33, "Log balance",
                 6, 1.0),
    ShortcutLink("ardougne_log_east", (35997, 35999), "Walk-across", (2598, 3336, 0), (2602, 3336, 0), 33, "Log balance",
                 6, 1.0),
    # SteppingStoneShortcut
    ShortcutLink("lum_stone_east", (9315,), "Jump-onto", (3149, 3363, 0), (3154, 3363, 0), 31, "Stepping stone", 13),
    ShortcutLink("lum_stone_west", (9315,), "Jump-onto", (3154, 3363, 0), (3149, 3363, 0), 31, "Stepping stone", 13),
    # AlKharidPitShortcut: 9332 lands east, 9331 west
    ShortcutLink("al_kharid_pit_east", (9332,), "Climb", (3303, 3315, 0), (3307, 3315, 0), 38, "Rocks", 6),
    ShortcutLink("al_kharid_pit_west", (9331,), "Climb", (3307, 3315, 0), (3303, 3315, 0), 38, "Rocks", 6),
    # FenceJumpShortcut: from the south it lands at 3335, from the north at 3334
    ShortcutLink("lumberyard_fence_north", (9300,), "Jump-over", (3240, 3331, 0), (3240, 3335, 0), 13, "Fence", 5),
    ShortcutLink("lumberyard_fence_south", (9300,), "Jump-over", (3240, 3338, 0), (3240, 3334, 0), 13, "Fence", 5),
)
