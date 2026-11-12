"""Walking time for RQ5's click-ahead bound (OQ-1 (C′), OQ-87 (a), Caleb, 2026-11-12): a counter on the sim's walks,
installed by the evaluation harness, so each evaluation decision's trace has the ticks it spent walking and the part
of them that's the walker's measured overhead (rlscape.travel.overhead: starting a walk, and the pauses between its
clicks), the most a perfect click-ahead could save.

The sim's code is unchanged: `install` wraps, in this process, the three ways the sim walks, and each wrapper calls
the original with the same arguments and returns what it returns, so an episode is the same with the counter as
without (tests/test_walking.py):
- `rlscape.sim.movement.walk`, which every option's trips take (the fastest route, transports included). Its
  `_timed_route`, which `route_ticks` also calls for estimates, is counted only inside a walk. A walk that runs out
  of budget (None) took no time and counts nothing.
- `rlscape.sim.abyss._walk`, the Abyss's outer and inner rings (timed as walks are, with the overhead).
- `rlscape.sim.runecrafting._walk_inside`, the walks inside a rune altar's ruins (timed without an overhead).

`walk` is imported by name into the modules that use it, so each module's binding is replaced. The counter counts
every walk in the process, so `rlscape.eval.rollout.play` reads it around `env.step` alone, after the policy has
acted: a greedy policy's lookahead runs options on copies of the state, walks and all. Counted per walk:
- `walk_ticks`: the ticks on foot (a route's ticks less its transports');
- `walk_overhead_ticks`: the overhead of its steps;
- `transport_ticks`: its teleports' and boats' ticks.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

FIELDS = ("walk_ticks", "walk_overhead_ticks", "transport_ticks")


@dataclass
class Counter:
    walk_ticks: float = 0.0
    walk_overhead_ticks: float = 0.0
    transport_ticks: float = 0.0
    walks: int = 0

    def snapshot(self) -> tuple[float, float, float]:
        return self.walk_ticks, self.walk_overhead_ticks, self.transport_ticks


COUNTER: Counter | None = None  # this process's, once installed


def install() -> Counter:
    """Wrap the sim's walks in this process (once); returns the counter."""
    global COUNTER
    if COUNTER is not None:
        return COUNTER
    from rlscape.sim import abyss, movement, runecrafting
    from rlscape.travel import overhead

    counter = Counter()
    real_walk, real_timed_route = movement.walk, movement._timed_route
    real_abyss_walk, real_inside = abyss._walk, runecrafting._walk_inside
    inside_walk: list = []  # the walk in progress: [(on-foot ticks, overhead, transport ticks)] once timed

    def timed_route(state, planned):
        ticks, energy = real_timed_route(state, planned)
        if inside_walk:
            inside_walk[-1] = (ticks - planned.fixed, overhead(sum(tiles for tiles, _ in planned.legs)),
                               planned.fixed)
        return ticks, energy

    def walk(state, destination, budget, elapsed=0):
        inside_walk.append(None)
        try:
            taken = real_walk(state, destination, budget, elapsed)
        finally:
            timed = inside_walk.pop()
        if taken is not None and timed is not None:
            foot, lost, transport = timed
            counter.walk_ticks += taken - transport  # walk() rounds the route's ticks up
            counter.walk_overhead_ticks += lost
            counter.transport_ticks += transport
            counter.walks += 1
        return taken

    def abyss_walk(state, steps):
        taken = real_abyss_walk(state, steps)
        counter.walk_ticks += taken
        counter.walk_overhead_ticks += overhead(steps)
        counter.walks += 1
        return taken

    def walk_inside(state, leg):
        taken = real_inside(state, leg)
        counter.walk_ticks += taken
        counter.walks += 1
        return taken

    movement._timed_route = timed_route  # walk() looks it up in the module at call time
    abyss._walk, runecrafting._walk_inside = abyss_walk, walk_inside
    for name, module in list(sys.modules.items()):
        if name.startswith("rlscape.") and getattr(module, "walk", None) is real_walk:
            module.walk = walk
    COUNTER = counter
    return counter
