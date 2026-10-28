"""The loop shared by gathering options whose resources deplete and respawn (trees, rocks).

At a site with N resources of one kind, the character walks there, then repeats: wait for the attempts until the
next success (one geometric draw), collect, and maybe deplete the resource (then walk to another standing one, or
wait for the first to respawn). It stops at a full inventory or when the time budget runs out. The success chance
is re-read after every success, so a level-up mid-option takes effect at once.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass
from math import ceil

import numpy as np

from rlscape.sim.options import COMPLETED, INVENTORY_FULL, OptionResult
from rlscape.sim.state import CharacterState
from rlscape.travel import travel_ticks

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


def gather_depleting(state: CharacterState, rng: np.random.Generator, budget: int, site: Site, attempt_ticks: int,
                     chance: Callable[[], float], collect: Callable[[], None], depletes: Callable[[], bool],
                     respawn: int) -> OptionResult:
    """Run one gathering option at a depleting site. `chance` is the per-attempt success probability, `collect`
    adds the reward and XP, `depletes` says whether this success used the resource up."""
    elapsed = ceil(travel_ticks(state.location, site.tile))
    if elapsed >= budget:
        return OptionResult(budget, COMPLETED)
    state.location = site.tile
    standing, regrowing = site.resources, []  # regrowing: ticks (from the option's start) when depleted ones return
    while True:
        while regrowing and regrowing[0] <= elapsed:
            heapq.heappop(regrowing)
            standing += 1
        if state.free_slots() == 0:
            return OptionResult(elapsed, INVENTORY_FULL)
        if standing == 0:
            if regrowing[0] >= budget:
                return OptionResult(budget, COMPLETED)
            elapsed = regrowing[0]
            continue
        attempts = int(rng.geometric(chance()))
        if elapsed + attempts * attempt_ticks > budget:
            return OptionResult(budget, COMPLETED)
        elapsed += attempts * attempt_ticks
        collect()
        if depletes():
            standing -= 1
            heapq.heappush(regrowing, elapsed + respawn)
            if standing > 0:
                elapsed = min(elapsed + WALK_BETWEEN_RESOURCES, budget)
