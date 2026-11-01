"""Fishing options, ported from the server's FishingListener, FishingOption.rollFish and FishingNPC.

Server mechanics (content/global/skill/fishing and gather/fishing):
- an attempt every 5 ticks; each attempt goes through the method's fish in order, skipping those above the level,
  and catches the first whose roll passes Fish.getSuccessChance (linear in level). If none passes, nothing.
  Measured (scripts/calibrate.py, 2026-10-31): the first attempt comes 2 ticks after the click beside the spot, and
  the attempt after a catch 6 ticks later, not 5.
  (Lure fishing: rainbow fish only with stripy feathers, the others only without.)
- each catch needs a free slot and uses one bait (feathers for lure fishing);
- every random(200, 390) ticks the spot picks one of its group's FishSpots tiles at random and moves there, unless an
  NPC is on it (another spot, or itself): so with n spots on a group's t tiles, a move happens with chance 1 - n/t
  (Draynor's two spots on two tiles never move). When it moves, the angler walks to a spot again.

The angler starts on the group's first tile with a spot of the method's kind at spawn. A group's tiles beyond
LOCAL_TILES of that are elsewhere (Lumbridge Swamp's group has one by Lumbridge Castle): a spot that moves there
leaves, and the angler takes another nearby, so the sim's moves pick among the local tiles.

Sampling: the attempts until any catch are one geometric draw with p = 1 - prod(1 - p_i); which fish is one
categorical draw with the server's sequential weights p_i * prod_{j<i}(1 - p_j). Geometric waits are memoryless, so
after a spot move the wait is simply drawn again, from a first attempt as at the start. Spot tiles come from the server's FishSpots.
"""

from __future__ import annotations

from math import ceil

import numpy as np

from rlscape.gamedata import server as gd
from rlscape.sim.aggression import Exposure, SiteExposure
from rlscape.sim.movement import walk
from rlscape.sim.options import COMPLETED, DIED, INPUTS_EXHAUSTED, INVENTORY_FULL, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import CharacterState
from rlscape.travel import travel_ticks

ATTEMPT_TICKS = 5  # delayClock(player, Clocks.SKILLING, 5)
FIRST_ATTEMPT_TICKS = 2  # measured: from the click beside a spot to the first attempt
AFTER_CATCH_TICKS = 1  # measured: the attempt after a catch comes 6 ticks later (507 of 532 catches)
SPOT_MOVE_TICKS = (200, 390)  # FishingNPC.getRandomDelay: RandomFunction.random(200, 390), upper bound excluded
STRIPY_FEATHER = 10087
LOCAL_TILES = 20


class Fishing(Option):
    family = "gathering"

    def __init__(self, option_id: str, method: str, spots: str, exposure: SiteExposure | None = None):
        self.id = option_id
        self.exposure = exposure  # measured, where aggressive monsters reach the spots
        self.method = gd.fishing_methods()[method]
        self.task = f"fishing:{method}"
        group = gd.fish_spot_locations()[spots]
        kind = {tuple(t) for i in gd.fishing_spot_ids()[method] for t in gd.spawns().get(i, ())}
        self.start = next((t for t in group if t in kind), group[0])
        self.spots = tuple(t for t in group
                           if max(abs(t[0] - self.start[0]), abs(t[1] - self.start[1])) <= LOCAL_TILES)
        self.move_chance = 1 - gd.fish_spot_counts()[spots] / len(set(group))

    def _has_bait(self, state: CharacterState) -> bool:
        return not self.method.bait or any(state.inventory.get(b, 0) > 0 for b in self.method.bait)

    def available(self, state: CharacterState) -> bool:
        return (state.level("fishing") >= self.method.level and state.inventory.get(self.method.tool, 0) > 0
                and self._has_bait(state) and state.free_slots() > 0)

    def catch_odds(self, state: CharacterState) -> tuple[list[gd.FishType], np.ndarray, float]:
        """The fish an attempt can catch, the chance of each given a catch, and the chance of any catch."""
        level, stripy = state.level("fishing"), state.inventory.get(STRIPY_FEATHER, 0) > 0
        fish = [f for f in (gd.fish_types()[name] for name in self.method.fish) if f.level <= level
                and (self.method.name != "LURE" or stripy == (f.name == "RAINBOW_FISH"))]
        weights, miss = [], 1.0
        for f in fish:
            p = min(max(f.success_chance(level), 0.0), 1.0)
            weights.append(miss * p)
            miss *= 1 - p
        return fish, np.array(weights) / (1 - miss), 1 - miss

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        spot = self.start
        elapsed = walk(state, spot, budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED)
        exposure = Exposure.at(state, spot, rng, self.exposure)  # aggressive monsters (rlscape.sim.aggression)

        def done(ticks: int, termination: str) -> OptionResult:
            return OptionResult(ticks, termination, exposure.finish(ticks))

        next_move = elapsed + int(rng.integers(0, rng.integers(*SPOT_MOVE_TICKS)))  # partway through a cycle
        fishing = SKILL_INDEX["fishing"]
        lead = FIRST_ATTEMPT_TICKS - ATTEMPT_TICKS  # from now to the first attempt, less one attempt
        while True:
            if state.free_slots() == 0:
                return done(elapsed, INVENTORY_FULL)
            if not self._has_bait(state):
                return done(elapsed, INPUTS_EXHAUSTED)
            fish, weights, p_any = self.catch_odds(state)
            catch_at = elapsed + lead + int(rng.geometric(p_any)) * ATTEMPT_TICKS
            if next_move < min(catch_at, budget):
                if rng.random() >= self.move_chance:  # the tile it picked has an NPC on it: it stays
                    next_move += int(rng.integers(*SPOT_MOVE_TICKS))
                    continue
                new_spot = self.spots[rng.integers(len(self.spots))]
                elapsed = min(next_move + ceil(travel_ticks(spot, new_spot)), budget)
                spot = state.location = new_spot
                next_move = elapsed + int(rng.integers(*SPOT_MOVE_TICKS))
                lead = FIRST_ATTEMPT_TICKS - ATTEMPT_TICKS
                continue
            if catch_at > budget:
                return done(budget, COMPLETED)
            away = exposure.gather(elapsed, catch_at)
            if away is None:
                return done(max(exposure.died_at, 1), DIED)
            elapsed = catch_at + away
            if exposure.abandoned or elapsed > budget:
                return done(min(elapsed, budget), COMPLETED)
            lead = AFTER_CATCH_TICKS
            caught = fish[rng.choice(len(fish), p=weights)]
            state.add(caught.item)
            state.xp[fishing] = min(state.xp[fishing] + caught.experience, MAX_XP)
            for bait in self.method.bait:
                if state.inventory.get(bait, 0) > 0:
                    state.inventory[bait] -= 1
                    if state.inventory[bait] == 0:
                        del state.inventory[bait]
                    break


# Catalog §2: the method (FishingOption) and the spot group (FishSpots) for each option, and where aggressive monsters
# reach the spots, their measured attack rate (per monster, a tick), flee time and chase (scripts/calibrate.py).
SITES = {
    # the Dark wizards, for a level-3 fisher (2026-11-01, 40 traced runs): 80 engagements in 8,833 unengaged ticks
    # fishing (two wizards), a cast every 5 ticks, 1.49 damaging hits per run away (0.466 of attacks deal damage),
    # 26 ticks running away and 34 back
    "fish_shrimp": ("SMALL_NET", "DRAYNOR", SiteExposure(flee_ticks=60, chase=3.19, engage_rate=1 / 221, cadence=5)),
    "fish_shrimp_swamp": ("SMALL_NET", "LUMBRIDGE_SWAMP"),  # Caleb, 2026-11-01: beside Draynor's, away from its wizards
    "fish_fly": ("LURE", "BARBARIAN"),
    "fish_lobster": ("LOBSTER_CAGE", "CATHERBY"),
}


def fishing_options() -> list[Fishing]:
    return [Fishing(option_id, *site) for option_id, site in SITES.items()]
