"""Pickpocketing, ported from the server's ThievingListeners and Pickpockets with event-level sampling.

Server mechanics (content/global/skill/thieving):
- an attempt succeeds if randomDouble(1, 100) <= getSkillSuccessChance(low, high, level): a uniform on [1, 100)
  against the target's percentage;
- a success gives the target's loot and experience, then a 2-tick lock (player.lock(2));
- a failure stuns for the target's stunTime (5 ticks for men) and hits for RandomFunction.random(min, max).

Sampling: the successes before the next failure are one geometric draw, so each event is a run of successes ended
by a failure. HP is checked after every failure: eat at or below half of the maximum, stop once the food runs out
(rlscape.sim.health). The option applies hitpoint regeneration itself, because HP matters inside it.

Only loot that always drops a fixed amount of a stackable item is supported (men: 3 coins); targets with weighted or
non-stackable loot come later. The site is the server's Man spawn nearest the Lumbridge spawn point.
"""

from __future__ import annotations

import numpy as np

from rlscape.gamedata import server as gd
from rlscape.sim.health import EAT_TICKS, eat_one, foods_held, regenerate, retreat_hp
from rlscape.sim.movement import walk
from rlscape.sim.options import COMPLETED, INVENTORY_FULL, OUT_OF_FOOD, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import SPAWN, CharacterState
from rlscape.sim.woodcutting import skill_success_chance
from rlscape.travel import travel_ticks

SUCCESS_TICKS = 2  # player.lock(2) after a successful pickpocket


def pickpocket_chance(target: gd.PickpocketTarget, level: int) -> float:
    """P(randomDouble(1, 100) <= getSkillSuccessChance(low, high, level))."""
    threshold = 100.0 * skill_success_chance(target.low, target.high, level)
    return min(max((threshold - 1.0) / 99.0, 0.0), 1.0)


def server_random(rng: np.random.Generator, a: int, b: int) -> int:
    """RandomFunction.random(a, b): min(a, b) + nextInt(|b - a|), so the upper bound is excluded; a when equal."""
    n = abs(b - a)
    return min(a, b) + (int(rng.integers(n)) if n else 0)


def nearest_spawn(npc_ids: tuple[int, ...], origin: tuple[int, int, int]) -> tuple[int, int, int]:
    spawns = gd.spawns()
    return min((tile for npc in npc_ids for tile in spawns.get(npc, ())), key=lambda tile: travel_ticks(origin, tile))


class Pickpocket(Option):
    family = "gathering"
    task = "thieving"

    def __init__(self, option_id: str, target: str, tile: tuple[int, int, int]):
        self.id = option_id
        self.target = gd.pickpocket_targets()[target]
        self.tile = tile
        stackable = gd.stackable_items()
        if not all(loot.always and loot.min_amount == loot.max_amount and loot.item in stackable
                   for loot in self.target.loot):
            raise NotImplementedError(f"{target}: only fixed, always-dropping, stackable loot is modelled so far")

    def _room_for_loot(self, state: CharacterState) -> bool:
        new_stacks = sum(1 for loot in self.target.loot if loot.item not in state.inventory)
        return state.free_slots() >= new_stacks

    def available(self, state: CharacterState) -> bool:
        return (state.level("thieving") >= self.target.level and self._room_for_loot(state)
                and (state.hp > retreat_hp(state) or bool(foods_held(state))))

    def _take(self, state: CharacterState, successes: int) -> None:
        for loot in self.target.loot:
            state.add(loot.item, loot.min_amount * successes)
        thieving = SKILL_INDEX["thieving"]
        state.xp[thieving] = min(state.xp[thieving] + self.target.experience * successes, MAX_XP)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed = walk(state, self.tile, budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED)
        regenerate(state, elapsed)
        target = self.target
        while True:
            if state.hp <= retreat_hp(state):
                if not eat_one(state):
                    return OptionResult(elapsed, OUT_OF_FOOD, regenerated=True)
                step = min(EAT_TICKS, budget - elapsed)
                elapsed += step
                regenerate(state, step)
                if elapsed >= budget:
                    return OptionResult(budget, COMPLETED, regenerated=True)
                continue
            if not self._room_for_loot(state):
                return OptionResult(elapsed, INVENTORY_FULL, regenerated=True)
            p = pickpocket_chance(target, state.level("thieving"))
            left = budget - elapsed
            successes = int(rng.geometric(1 - p)) - 1 if p < 1 else left  # successes before the next failure
            if successes * SUCCESS_TICKS + target.stun_ticks > left:
                self._take(state, min(successes, left // SUCCESS_TICKS))
                regenerate(state, left)
                return OptionResult(budget, COMPLETED, regenerated=True)
            self._take(state, successes)
            step = successes * SUCCESS_TICKS + target.stun_ticks
            elapsed += step
            regenerate(state, step)
            state.hp -= server_random(rng, target.stun_damage_min, target.stun_damage_max)
            if state.hp <= 0:
                raise RuntimeError("a pickpocket failure would kill the character; death isn't modelled yet")


def pickpocket_options() -> list[Pickpocket]:
    """Catalog §2: pickpocket_men in Lumbridge."""
    return [Pickpocket("pickpocket_men", "MAN", nearest_spawn(gd.pickpocket_targets()["MAN"].npc_ids, SPAWN))]
