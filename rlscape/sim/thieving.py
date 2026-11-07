"""Pickpocketing, ported from the server's ThievingListeners and Pickpockets with event-level sampling.

Server mechanics (content/global/skill/thieving):
- an attempt needs the target's Thieving level and WeightBasedTable.canRoll: the guaranteed items all fit, or the
  inventory isn't full;
- it succeeds if randomDouble(1, 100) <= getSkillSuccessChance(low, high, level): a uniform on [1, 100) against the
  target's percentage;
- a success rolls the target's table (every guaranteed item, then one weighted pick with P = weight / total) and adds
  each item; what doesn't fit is lost (Container.add). Then the experience, and a 2-tick lock (player.lock(2));
- a failure stuns for the target's stunTime and hits for RandomFunction.random(min, max).

Amounts are WeightedItem.getItem's RandomFunction.random(min, max), upper bound excluded. The H.A.M. tables' easy-clue
slot gives nothing, as clue slots do in combat drops (gd.SPECIAL_DROP_SLOTS): treasure trails aren't modelled.

Sampling: the successes before the next failure are one geometric draw, so each event is a run of successes ended
by a failure. The loot is rolled per success, and canRoll is checked before each attempt. HP is checked after every
failure: eat at or below the retreat point (half of the maximum) or at or below the target's largest hit, so a
failure never kills; stop once the food runs out (rlscape.sim.health). The option applies hitpoint regeneration
itself, because HP matters inside it.

Sites (option catalog §2): each target's server spawn nearest the Lumbridge spawn point, outside the Wilderness and
outside every access-table area. LEFT_OUT lists the targets without an option, and why.

Stalls, from the server's Stall and StallThiefPulse, in the Ardougne market:
- a steal needs the stall's Thieving level, a free inventory slot and no fight; it resolves on the pulse's third tick;
- 4 in 15 steals (RandomFunction.random(15) < 4) are noticed if a guard (NPC 32 or 2236) is within 8 tiles on each
  axis; that guard attacks and the steal fails. The market's guards spawn near every stall;
- otherwise the steal takes one of the stall's rewards, picked uniformly, gives the experience, and empties the stall
  for its restock time (baker 4 ticks ... gem 300), so the next steal waits for it.
When noticed, the character runs off and comes back (Caleb, 2026-10-30), taking the guard's swings while it
disengages (ESCAPE_ATTACKS, as a combat retreat does) and FLEE_TICKS away; both are overheads to measure on the
server. It eats before a steal if the guard's worst escape could take it to 0. Each stall's tile is its merchant's
spawn, an estimate of where a thief stands; verify on the server. Ardougne's spice stall (object 2564) isn't in the
server's Stall table, so it can't be stolen from there.
"""

from __future__ import annotations

import numpy as np

from rlscape.combat import formulas as f
from rlscape.combat.access import rules_at
from rlscape.combat.rates import ESCAPE_ATTACKS, Plan, npc_offence
from rlscape.gamedata import server as gd
from rlscape.sim.combat import in_wilderness
from rlscape.sim.equipment import fighter_for
from rlscape.sim.health import EAT_TICKS, eat_one, foods_held, regenerate, retreat_hp
from rlscape.sim.movement import reachable, walk
from rlscape.sim.options import COMPLETED, INVENTORY_FULL, OUT_OF_FOOD, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import SPAWN, CharacterState
from rlscape.sim.woodcutting import skill_success_chance
from rlscape.travel import travel_ticks

SUCCESS_TICKS = 2  # player.lock(2) after a successful pickpocket
# Measured beyond the lock or stun, per attempt: the click on a target that moves about, and its walk (2026-11-06,
# scripts/calibrate_thieving.py at Lumbridge's men, bands 1 and 31: 0.41 to 0.46 in 4 runs)
ATTEMPT_OVERHEAD_TICKS = 0.44
STEAL_TICKS = 3  # StallThiefPulse.reward: the steal resolves when ++ticks % 3 == 0, on a 1-tick pulse
NOTICE_CHANCE = 4 / 15  # StallThiefPulse.success: RandomFunction.random(15) < 4
NOTICE_RANGE = 8  # RegionManager.getLocalNPCs(location, 8): within 8 tiles on each axis
STALL_GUARDS = (32, 2236)  # the NPCs StallThiefPulse.success checks: Guard and Market Guard
FLEE_TICKS = 20  # running out of the noticing guard's reach and back to the stall; estimate, calibrate on the server

# Option id -> Pickpockets constant, in level order (catalog §2).
PICKPOCKET_TARGETS = {
    "pickpocket_men": "MAN",
    "pickpocket_farmers": "FARMER",
    "pickpocket_ham_women": "FEMALE_HAM_MEMBER",
    "pickpocket_ham_men": "MALE_HAM_MEMBER",
    "pickpocket_warriors": "WARRIOR",
    "pickpocket_master_farmers": "MASTER_FARMER",
    "pickpocket_guards": "GUARD",
    "pickpocket_fremenniks": "FREMENNIK_CITIZEN",
    "pickpocket_desert_bandits": "DESERT_BANDIT",
    "pickpocket_knights": "KNIGHT_OF_ADROUGNE",
    "pickpocket_watchmen": "YANILLE_WATCHMAN",
    "pickpocket_menaphite_thugs": "MENAPHITE_THUG",
    "pickpocket_paladins": "PALADIN",
    "pickpocket_gnomes": "GNOME",
    "pickpocket_heroes": "HERO",
}
LEFT_OUT = {
    "ROGUE": "spawns only in the Wilderness (Rogues' Castle), where the sim doesn't model the monsters around a "
             "non-combat option",
    "CAVE_GOBLIN": "Dorgesh-Kaan: outside the travel model's map, and behind Death to the Dorgeshuun",
    "BEARDED_BANDIT": "no spawns on the server",
}


def pickpocket_chance(target: gd.PickpocketTarget, level: int) -> float:
    """P(randomDouble(1, 100) <= getSkillSuccessChance(low, high, level))."""
    threshold = 100.0 * skill_success_chance(target.low, target.high, level)
    return min(max((threshold - 1.0) / 99.0, 0.0), 1.0)


def server_random(rng: np.random.Generator, a: int, b: int) -> int:
    """RandomFunction.random(a, b): min(a, b) + nextInt(|b - a|), so the upper bound is excluded; a when equal."""
    n = abs(b - a)
    return min(a, b) + (int(rng.integers(n)) if n else 0)


def largest_random(a: int, b: int) -> int:
    """The largest value RandomFunction.random(a, b) returns."""
    return max(a, b) - 1 if a != b else a


def nearest_spawn(npc_ids: tuple[int, ...], origin: tuple[int, int, int]) -> tuple[int, int, int]:
    """The spawn nearest `origin`, outside the Wilderness and every access-table area."""
    spawns, npcs = gd.spawns(), gd.npcs()
    open_spawns = [tile for npc in npc_ids for tile in spawns.get(npc, ())
                   if not in_wilderness(tile) and not rules_at(npcs[npc].name if npc in npcs else "", tile)]
    return min(open_spawns, key=lambda tile: travel_ticks(origin, tile))


class Pickpocket(Option):
    family = "gathering"
    task = "thieving"

    def __init__(self, option_id: str, target: str, tile: tuple[int, int, int]):
        self.id = option_id
        self.target = gd.pickpocket_targets()[target]
        self.tile = tile
        self.guaranteed = tuple(loot for loot in self.target.loot if loot.always)
        self.weighted = tuple(loot for loot in self.target.loot if not loot.always)
        weights = np.array([loot.weight for loot in self.weighted])
        self.weights = weights / weights.sum() if self.weighted else weights
        self.largest_hit = largest_random(self.target.stun_damage_min, self.target.stun_damage_max)

    def can_roll(self, state: CharacterState) -> bool:
        """WeightBasedTable.canRoll: the guaranteed items all fit, or the inventory isn't full."""
        free, stackable = state.free_slots(), gd.stackable_items()
        needed = sum(0 if loot.item in stackable and loot.item in state.inventory else
                     1 if loot.item in stackable else loot.max_amount for loot in self.guaranteed)
        return (bool(self.guaranteed) and needed <= free) or free > 0

    def eat_below(self, state: CharacterState) -> float:
        """Eat at or below this HP: the retreat point, or the target's largest hit if that is higher."""
        return max(retreat_hp(state), self.largest_hit)

    def available(self, state: CharacterState) -> bool:
        return (state.level("thieving") >= self.target.level and self.can_roll(state)
                and (state.hp > self.eat_below(state) or bool(foods_held(state))) and reachable(state, self.tile))

    def _succeed(self, state: CharacterState, rng: np.random.Generator, successes: int) -> int:
        """Up to `successes` successful attempts, each needing canRoll first; returns how many were made."""
        picks = rng.choice(len(self.weighted), size=successes, p=self.weights) if self.weighted else ()
        made = 0
        for i in range(successes):
            if not self.can_roll(state):
                break
            for loot in self.guaranteed:
                state.add(loot.item, server_random(rng, loot.min_amount, loot.max_amount))
            if self.weighted:
                loot = self.weighted[picks[i]]
                if loot.item != gd.CLUE_SLOT_EASY:
                    state.add(loot.item, server_random(rng, loot.min_amount, loot.max_amount))
            made += 1
        thieving = SKILL_INDEX["thieving"]
        state.xp[thieving] = min(state.xp[thieving] + self.target.experience * made, MAX_XP)
        return made

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed = walk(state, self.tile, budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED)
        regenerate(state, elapsed)
        target = self.target
        while True:
            if state.hp <= self.eat_below(state):
                if not eat_one(state):
                    return OptionResult(elapsed, OUT_OF_FOOD, regenerated=True)
                step = min(EAT_TICKS, budget - elapsed)
                elapsed += step
                regenerate(state, step)
                if elapsed >= budget:
                    return OptionResult(budget, COMPLETED, regenerated=True)
                continue
            if not self.can_roll(state):
                return OptionResult(elapsed, INVENTORY_FULL, regenerated=True)
            p = pickpocket_chance(target, state.level("thieving"))
            left = budget - elapsed
            success_ticks = SUCCESS_TICKS + ATTEMPT_OVERHEAD_TICKS
            successes = int(rng.geometric(1 - p)) - 1 if p < 1 else left  # successes before the next failure
            if round(successes * success_ticks + target.stun_ticks + ATTEMPT_OVERHEAD_TICKS) > left:
                successes = min(successes, int(left // success_ticks))
                made = self._succeed(state, rng, successes)
                if made < successes:
                    step = round(made * success_ticks)
                    regenerate(state, step)
                    return OptionResult(elapsed + step, INVENTORY_FULL, regenerated=True)
                regenerate(state, left)
                return OptionResult(budget, COMPLETED, regenerated=True)
            made = self._succeed(state, rng, successes)
            if made < successes:  # the inventory filled: the next attempt never happens
                step = round(made * success_ticks)
                regenerate(state, step)
                return OptionResult(elapsed + step, INVENTORY_FULL, regenerated=True)
            step = round(successes * success_ticks + target.stun_ticks + ATTEMPT_OVERHEAD_TICKS)
            elapsed += step
            regenerate(state, step)
            state.hp -= server_random(rng, target.stun_damage_min, target.stun_damage_max)
            if state.hp <= 0:
                raise RuntimeError("a pickpocket failure killed the character; the eating rule should prevent it")


def pickpocket_options() -> list[Pickpocket]:
    """Catalog §2: one option per target in PICKPOCKET_TARGETS, at its site."""
    targets = gd.pickpocket_targets()
    return [Pickpocket(option_id, name, nearest_spawn(targets[name].npc_ids, SPAWN))
            for option_id, name in PICKPOCKET_TARGETS.items()]


# Option id -> (Stall constant, the stall's merchant NPC, whose Ardougne market spawn is the stall's tile).
STALLS = {
    "steal_bakers_stall": ("BAKER_STALL", 571),
    "steal_silk_stall": ("SILK_STALL", 574),
    "steal_fur_stall": ("FUR_STALL", 573),
    "steal_silver_stall": ("SILVER_STALL", 569),
    "steal_gem_stall": ("GEM_STALL", 570),
}
ARDOUGNE_MARKET = (2662, 3305, 0)


def guarded(tile: tuple[int, int, int]) -> bool:
    """A stall guard spawns within NOTICE_RANGE of the tile."""
    return any(abs(x - tile[0]) <= NOTICE_RANGE and abs(y - tile[1]) <= NOTICE_RANGE and plane == tile[2]
               for npc in STALL_GUARDS for x, y, plane in gd.spawns().get(npc, ()))


class StealFromStall(Option):
    family = "gathering"
    task = "thieving"

    def __init__(self, option_id: str, stall: str, tile: tuple[int, int, int]):
        self.id = option_id
        self.stall = gd.stalls()[stall]
        self.tile = tile
        self.notice = NOTICE_CHANCE if guarded(tile) else 0.0
        self.guard = gd.npcs()[STALL_GUARDS[0]]

    def _escape_hits(self, state: CharacterState) -> tuple[float, int]:
        """The noticing guard's hit chance and max hit against the character as equipped."""
        chance, max_hit, _, _ = npc_offence(fighter_for(state), Plan("melee", f.ACCURATE), self.guard)
        return chance, max_hit

    def eat_below(self, state: CharacterState) -> float:
        """Eat at or below this HP: the retreat point, or the most an escape can take, if that is higher."""
        return max(retreat_hp(state), ESCAPE_ATTACKS * self._escape_hits(state)[1] if self.notice else 0)

    def available(self, state: CharacterState) -> bool:
        return (state.level("thieving") >= self.stall.level and state.free_slots() > 0
                and (state.hp > self.eat_below(state) or bool(foods_held(state))) and reachable(state, self.tile))

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        elapsed = walk(state, self.tile, budget)
        if elapsed is None:
            return OptionResult(budget, COMPLETED)
        regenerate(state, elapsed)
        stall, thieving, steals = self.stall, SKILL_INDEX["thieving"], 0

        def done(ticks: int, termination: str) -> OptionResult:
            return OptionResult(ticks, termination, True, {"stall": stall.name, "steals": steals})

        while True:
            if state.hp <= self.eat_below(state):
                if not eat_one(state):
                    return done(elapsed, OUT_OF_FOOD)
                step = min(EAT_TICKS, budget - elapsed)
                elapsed += step
                regenerate(state, step)
                if elapsed >= budget:
                    return done(budget, COMPLETED)
                continue
            if state.free_slots() == 0:
                return done(elapsed, INVENTORY_FULL)
            if elapsed + STEAL_TICKS > budget:
                regenerate(state, budget - elapsed)
                return done(budget, COMPLETED)
            if rng.random() < self.notice:  # a guard attacks: run off, taking its swings, and come back
                chance, max_hit = self._escape_hits(state)
                state.hp -= int(((rng.random(ESCAPE_ATTACKS) < chance) * rng.integers(0, max_hit + 1,
                                                                                     ESCAPE_ATTACKS)).sum())
                if state.hp <= 0:
                    raise RuntimeError("a guard's escape hits killed the character; the eating rule should prevent it")
                step = min(STEAL_TICKS + FLEE_TICKS, budget - elapsed)
            else:
                item, amount = stall.rewards[int(rng.integers(len(stall.rewards)))]
                state.add(item, amount)
                state.xp[thieving] = min(state.xp[thieving] + stall.experience, MAX_XP)
                steals += 1
                step = min(STEAL_TICKS + stall.restock_ticks, budget - elapsed)  # then the stall restocks
            elapsed += step
            regenerate(state, step)
            if elapsed >= budget:
                return done(budget, COMPLETED)


def stall_options() -> list[StealFromStall]:
    """Catalog §2: one option per stall in STALLS, at its merchant's Ardougne market spawn."""
    spawns = gd.spawns()
    return [StealFromStall(option_id, stall, min(spawns[merchant], key=lambda t: travel_ticks(ARDOUGNE_MARKET, t)))
            for option_id, (stall, merchant) in STALLS.items()]
