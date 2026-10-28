"""Fishing options, ported from the server's FishingListener, FishingOption.rollFish and FishingNPC.

Server mechanics (content/global/skill/fishing and gather/fishing):
- an attempt every 5 ticks; each attempt goes through the method's fish in order, skipping those above the level,
  and catches the first whose roll passes Fish.getSuccessChance (linear in level). If none passes, nothing.
  (Lure fishing: rainbow fish only with stripy feathers, the others only without.)
- each catch needs a free slot and uses one bait (feathers for lure fishing);
- the spot moves every random(200, 390) ticks to one of its FishSpots tiles; the angler walks after it.

Sampling: the attempts until any catch are one geometric draw with p = 1 - prod(1 - p_i); which fish is one
categorical draw with the server's sequential weights p_i * prod_{j<i}(1 - p_j). Geometric waits are memoryless, so
after a spot move the wait is simply drawn again. Spot tiles come from the server's FishSpots.
"""

from __future__ import annotations

from math import ceil

import numpy as np

from rlscape.gamedata import server as gd
from rlscape.sim.options import COMPLETED, INPUTS_EXHAUSTED, INVENTORY_FULL, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import CharacterState
from rlscape.travel import travel_ticks

ATTEMPT_TICKS = 5  # delayClock(player, Clocks.SKILLING, 5)
SPOT_MOVE_TICKS = (200, 390)  # FishingNPC.getRandomDelay: RandomFunction.random(200, 390), upper bound excluded
STRIPY_FEATHER = 10087


class Fishing(Option):
    family = "gathering"

    def __init__(self, option_id: str, method: str, spots: str):
        self.id = option_id
        self.method = gd.fishing_methods()[method]
        self.spots = gd.fish_spot_locations()[spots]

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
        spot = self.spots[0]
        elapsed = ceil(travel_ticks(state.location, spot))
        if elapsed >= budget:
            return OptionResult(budget, COMPLETED)
        state.location = spot
        next_move = elapsed + int(rng.integers(0, rng.integers(*SPOT_MOVE_TICKS)))  # partway through a cycle
        fishing = SKILL_INDEX["fishing"]
        while True:
            if state.free_slots() == 0:
                return OptionResult(elapsed, INVENTORY_FULL)
            if not self._has_bait(state):
                return OptionResult(elapsed, INPUTS_EXHAUSTED)
            fish, weights, p_any = self.catch_odds(state)
            catch_at = elapsed + int(rng.geometric(p_any)) * ATTEMPT_TICKS
            if next_move < min(catch_at, budget):
                new_spot = self.spots[rng.integers(len(self.spots))]
                elapsed = min(next_move + ceil(travel_ticks(spot, new_spot)), budget)
                spot = state.location = new_spot
                next_move = elapsed + int(rng.integers(*SPOT_MOVE_TICKS))
                continue
            if catch_at > budget:
                return OptionResult(budget, COMPLETED)
            elapsed = catch_at
            caught = fish[rng.choice(len(fish), p=weights)]
            state.add(caught.item)
            state.xp[fishing] = min(state.xp[fishing] + caught.experience, MAX_XP)
            for bait in self.method.bait:
                if state.inventory.get(bait, 0) > 0:
                    state.inventory[bait] -= 1
                    if state.inventory[bait] == 0:
                        del state.inventory[bait]
                    break


# Catalog §2: the method (FishingOption) and the spot group (FishSpots) for each option.
SITES = {
    "fish_shrimp": ("SMALL_NET", "DRAYNOR"),
    "fish_fly": ("LURE", "BARBARIAN"),
    "fish_lobster": ("LOBSTER_CAGE", "CATHERBY"),
}


def fishing_options() -> list[Fishing]:
    return [Fishing(option_id, method, spots) for option_id, (method, spots) in SITES.items()]
