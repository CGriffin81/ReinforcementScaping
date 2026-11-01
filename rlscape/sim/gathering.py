"""The loop shared by gathering options whose resources deplete and respawn (trees, rocks).

At a site with N resources of one kind, the character walks there, then repeats: wait for the attempts until the
next success (one geometric draw), collect, and maybe deplete the resource (then walk to another standing one, or
wait for the first to respawn). It stops at a full inventory or when the time budget runs out. The success chance
is re-read after every success, so a level-up mid-option takes effect at once.

The time between attempts is the server's skilling delay. What the code can't say is measured on the server
(scripts/calibrate.py) and kept with the site: the ticks from reaching the site's tile to the first attempt, and from
a resource running out to the first attempt on the next. Sites not yet measured keep WALK_BETWEEN_RESOURCES and
start at once.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from rlscape.sim.aggression import Exposure, SiteExposure
from rlscape.sim.movement import walk
from rlscape.sim.options import COMPLETED, DIED, INVENTORY_FULL, OptionResult
from rlscape.sim.state import CharacterState

MAX_PLAYERS = 2000  # ServerConstants.MAX_PLAYERS
PLAYERS_ONLINE = 1  # the RL character alone: ambient bots are off for calibration and E6 (env contract §7)
WALK_BETWEEN_RESOURCES = 3  # ticks to the next standing tree or rock at the same spot; calibrate


def respawn_ticks(respawn_min: int, respawn_max: int, players: int = PLAYERS_ONLINE) -> int:
    """WoodcuttingNode / MiningNode.getRespawnDuration: from min towards max as the server fills up."""
    return int(respawn_min + (respawn_max - respawn_min) / (MAX_PLAYERS / players))


@dataclass(frozen=True)
class Site:
    tile: tuple[int, int, int]
    resources: int  # trees or rocks of this kind at the spot
    source: str  # where the tile and the count come from
    first_attempt: int | None = None  # measured: ticks from reaching the tile to the first attempt
    next_attempt: int | None = None  # measured: ticks from a resource running out to the first attempt on the next
    exposure: SiteExposure | None = None  # measured, where aggressive monsters reach it (rlscape.sim.aggression)


def site_offsets(site: Site, attempt_ticks: int) -> tuple[int, int]:
    """The ticks a load starts with and a move to the next resource adds, counting each attempt as `attempt_ticks`
    long: the site's measured times less one attempt, or 0 and WALK_BETWEEN_RESOURCES where it isn't measured."""
    first = 0 if site.first_attempt is None else site.first_attempt - attempt_ticks
    between = WALK_BETWEEN_RESOURCES if site.next_attempt is None else site.next_attempt - attempt_ticks
    return first, between


def gather_depleting(state: CharacterState, rng: np.random.Generator, budget: int, site: Site, attempt_ticks: int,
                     chance: Callable[[], float], collect: Callable[[], None], depletes: Callable[[], bool],
                     respawn: int, after_success: int = 0) -> OptionResult:
    """Run one gathering option at a depleting site. `chance` is the per-attempt success probability, `collect`
    adds the reward and XP, `depletes` says whether this success used the resource up, and `after_success` is the
    extra ticks the attempt after a success waits (woodcutting: 1, measured).

    An attempt is counted as `attempt_ticks` long, ending in its roll; a site's measured times are from the event to
    the roll, so they come in less one attempt. Aggressive monsters at the site attack while the character gathers
    or waits there (rlscape.sim.aggression)."""
    elapsed = walk(state, site.tile, budget)
    if elapsed is None:
        return OptionResult(budget, COMPLETED)
    exposure = Exposure.at(state, site.tile, rng, site.exposure)

    def done(ticks: int, termination: str) -> OptionResult:
        return OptionResult(ticks, termination, exposure.finish(ticks))

    first, between = site_offsets(site, attempt_ticks)
    elapsed += first
    standing, regrowing = site.resources, []  # regrowing: ticks (from the option's start) when depleted ones return
    extra = 0  # the after_success ticks still owed: they delay the next attempt, if there is one
    while True:
        while regrowing and regrowing[0] <= elapsed:
            heapq.heappop(regrowing)
            standing += 1
        if state.free_slots() == 0:
            return done(elapsed, INVENTORY_FULL)
        if standing == 0:
            if regrowing[0] >= budget:
                return done(budget, COMPLETED)
            away = exposure.gather(elapsed, regrowing[0])
            if away is None:
                return done(max(exposure.died_at, 1), DIED)
            elapsed = regrowing[0] + away
            if exposure.abandoned or elapsed > budget:
                return done(min(elapsed, budget), COMPLETED)
            continue
        attempts = int(rng.geometric(chance()))
        if elapsed + extra + attempts * attempt_ticks > budget:
            return done(budget, COMPLETED)
        away = exposure.gather(elapsed, elapsed + extra + attempts * attempt_ticks)
        if away is None:
            return done(max(exposure.died_at, 1), DIED)
        elapsed += extra + attempts * attempt_ticks + away
        if exposure.abandoned or elapsed > budget:
            return done(min(elapsed, budget), COMPLETED)
        collect()
        extra = after_success
        if depletes():
            standing -= 1
            heapq.heappush(regrowing, elapsed + respawn)
            if standing > 0:
                elapsed = min(elapsed + between, budget)
