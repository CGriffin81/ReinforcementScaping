"""Barbarian Fishing (sim v1; Caleb, 2026-11-08: an Agility training method, OQ-2 Choice D; the barbarian rod on the GE
at 1,000 gp, OQ-41). The spec is docs/sim-v1-skills-draft.md §3. The server's gather/fishing/barbfishing:

- BarbFishingPulse needs Fishing 48, Agility 15 and Strength 15, a barbarian rod in the inventory, a free slot and
  bait (fish offcuts, feathers, fishing bait, roe or caviar, used up in that order). Its first try comes 6 ticks after
  the click (the pulse's first call only sets its delay to 5), then one every 5. A try goes through leaping trout
  (Fishing 48), salmon (58, Strength and Agility 30) and sturgeon (70, Strength and Agility 45), in that order, and
  catches the first whose roll passes Fish.getSuccessChance at the Fishing level, so trout come first at every level.
  A catch uses one bait and gives the fish's Fishing XP and 5, 6 or 7 Agility and Strength XP.
- The pulse fishes a placeholder spot (`NPC(FISHING_SPOT_2722)`), not the one clicked, so the spots' moves
  (SpotManager: every 400 to 2,000 ticks) don't stop it: it goes on until the inventory is full or the bait is gone.

The path `barb_fish` (BarbFish) walks to Otto's Grotto, clicks a spot, and fishes until the inventory is full, the bait
runs out or the option's time is up, as fishing's paths do (catalog §1: the agent banks or drops the fish). It ranks in
both the Fishing and the Agility slots by its XP in each, as two instances of the one path. The leaping fish stay misc
(Choice I: nothing uses them, since cutting them for roe and caviar is Cooking's and out).
"""

from __future__ import annotations

import numpy as np

from rlscape.gamedata import server as gd
from rlscape.sim.movement import reachable, walk
from rlscape.sim.options import COMPLETED, INPUTS_EXHAUSTED, INVENTORY_FULL, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import INVENTORY_SLOTS, CharacterState
from rlscape.sim.transport import home_ready
from rlscape.travel import BANKING_TICKS, travel_ticks

ROD = 11323  # Items.BARBARIAN_ROD_11323
BAITS = (11334, 314, 313, 11324, 11326)  # BarbFishingPulse.baits: offcuts, feathers, fishing bait, roe, caviar
# The fish in the order the pulse tries them, with the Strength and Agility each needs and the XP each gives in both
LEAPING = (("LEAPING_TROUT", 0, 5.0), ("LEAPING_SALMON", 30, 6.0), ("LEAPING_STURGEON", 45, 7.0))
GROTTO = (2500, 3509, 0)  # a spot's tile at Otto's Grotto (SpotManager.locations), beside the Barbarian Outpost
FIRST_TRY_TICKS = 6  # the pulse's first call sets its delay to 5: the first try comes 6 ticks after the click
TRY_TICKS = 5
TICKS_PER_HOUR = 6000


class BarbFish(Option):
    """barb_fish: Barbarian Fishing at Otto's Grotto, to a full inventory. `skill` is the ranking it's in."""

    family = "gathering"
    task = "barbfishing"

    def __init__(self, skill: str = "fishing"):
        self.skill, self.id = skill, "barb_fish"

    @staticmethod
    def has_bait(state: CharacterState) -> bool:
        return any(state.inventory.get(b, 0) > 0 for b in BAITS)

    def available(self, state: CharacterState) -> bool:
        return (state.level("fishing") >= 48 and state.level("agility") >= 15 and state.level("strength") >= 15
                and state.inventory.get(ROD, 0) > 0 and self.has_bait(state) and state.free_slots() > 0
                and reachable(state, GROTTO))

    @staticmethod
    def catch_odds(state: CharacterState) -> tuple[list[tuple[gd.FishType, float]], np.ndarray, float]:
        """The fish a try can catch (each with its Agility and Strength XP), the chance of each given a catch, and the
        chance of any catch."""
        level, low = state.level("fishing"), min(state.level("strength"), state.level("agility"))
        fish, weights, miss = [], [], 1.0
        for name, needs, xp in LEAPING:
            f = gd.fish_types()[name]
            if f.level > level or low < needs:
                continue
            p = min(max(f.success_chance(level), 0.0), 1.0)
            fish.append((f, xp))
            weights.append(miss * p)
            miss *= 1 - p
        return fish, np.array(weights) / (1 - miss), 1 - miss

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed = walk(state, GROTTO, budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED)
        fishing, agility, strength = SKILL_INDEX["fishing"], SKILL_INDEX["agility"], SKILL_INDEX["strength"]
        lead = FIRST_TRY_TICKS - TRY_TICKS
        while True:
            if state.free_slots() == 0:
                return OptionResult(elapsed, INVENTORY_FULL)
            if not self.has_bait(state):
                return OptionResult(elapsed, INPUTS_EXHAUSTED)
            fish, weights, p_any = self.catch_odds(state)
            catch_at = elapsed + lead + int(rng.geometric(p_any)) * TRY_TICKS
            if catch_at > budget:
                return OptionResult(budget, COMPLETED)
            elapsed, lead = catch_at, 0
            caught, xp = fish[rng.choice(len(fish), p=weights)]
            bait = next(b for b in BAITS if state.inventory.get(b, 0) > 0)
            state.take(bait)
            state.add(caught.item)
            state.xp[fishing] = min(state.xp[fishing] + caught.experience, MAX_XP)
            state.xp[agility] = min(state.xp[agility] + xp, MAX_XP)
            state.xp[strength] = min(state.xp[strength] + xp, MAX_XP)

    def rate(self, state: CharacterState, duration_ticks: int) -> tuple[float, float, float, float]:
        """(XP/hr in the ranking's skill, 0, gp/hr, travel), as the fishing paths are valued
        (rlscape.sim.skilling.path_rate): loads of the inventory's room, a bank trip from the grotto each, within the
        option after the walk there."""
        from rlscape.sim.kits import kit  # imported here: kits imports the skilling paths' modules
        from rlscape.sim.skilling import _nearest_bank_ticks

        keep = kit(state, self.task)
        room = INVENTORY_SLOTS - sum(1 if i in gd.stackable_items() else n for i, n in state.inventory.items()
                                     if i in keep)
        fish, weights, p_any = self.catch_odds(state)
        if room <= 0 or p_any <= 0:
            return 0.0, 0.0, 0.0, float("inf")
        values = gd.item_values()
        catch_ticks = TRY_TICKS / p_any
        xp = float(np.dot(weights, [f.experience if self.skill == "fishing" else a for f, a in fish]))
        bait = next((b for b in BAITS if state.inventory.get(b, 0) > 0), BAITS[1])
        gp = float(np.dot(weights, [values.get(f.item, 0) for f, _ in fish])) - values.get(bait, 0)
        travel = travel_ticks(state.location, GROTTO, home_ready(state))
        cycle = FIRST_TRY_TICKS - TRY_TICKS + room * catch_ticks + 2 * _nearest_bank_ticks(GROTTO) + BANKING_TICKS
        share = max(duration_ticks - travel, 0.0) / duration_ticks * TICKS_PER_HOUR / cycle
        return room * xp * share, 0.0, room * gp * share, travel


def barbfishing_paths() -> list[BarbFish]:
    """The path in each of its rankings: Fishing's and Agility's."""
    return [BarbFish("fishing"), BarbFish("agility")]
