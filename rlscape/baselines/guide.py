"""The scripted-guide baseline (E1; env contract decision 17): a new player following the RuneScape Wiki's training
guides as they stood in January 2009, the month the GE prices are frozen at. Draft for Caleb's review
(`docs/scripted-guide-draft.md`); E1 doesn't use it until he has.

The guides say how to train each skill: the method at each level, and the tool or gear tier to use. They don't say
how to split time between skills, so the schedule is Claude's proposal (marked SCHEDULE below):
- **Schedule:** train the lowest of Attack, Strength, Defence, Woodcutting, Mining and Fishing next, one option at a
  time; ties go to that order.
- **Woodcutting** ([22]): normal trees to 14, oaks 15–40, willows from 41 (the guide says not to start yews at 60).
- **Mining** ([25]): copper and tin to 14, alternately (the guide's clay and essence aren't in sim v0); iron from 15,
  "the best ore for experience".
- **Fishing** ([23]): the small net to 19 (shrimp, then anchovies); fly fishing from 20, the fastest method at every
  level, with a fly rod and feathers bought for it.
- **Melee** ([24]):
  - each stat is trained only with its own style (accurate, aggressive, defensive); the guide leaves the order to the
    player. If no fight allows a stat's style (the danger filter), the turn passes to the next skill in the schedule.
  - monsters come from the guide's list for the trained stat's level band; the agent's 3 + 3 melee slots are
    searched for one, otherwise the top XP slot is fought
  - the scimitar is the weapon (the fastest F2P weapon)
  - armour is the best tier the Defence level allows
  - drops are picked up (the `valuable` loot mode keeps cowhides and bones, which the guide says to collect)
- **Gear and tools:** upgrades are bought on the GE in this order, as the calibration characters do (env contract
  §7): the tool for the skill being trained, then the scimitar, then armour, helm to kiteshield. Each takes the best
  tier that's both an upgrade and affordable, moving up a tier at a time as the guides do.
  Gear banked by a deposit is withdrawn before a fight.
- **Funding upgrades** (the guides fund gear by selling cowhides and logs): when an upgrade can't be afforded, sell
  what's carried if it pays for it at GE prices, or take banked produce out to sell (`bank_withdraw_for_sale`) if
  that would. What's carried for sale means vocabulary produce (neither gear nor kept when banking, so nothing bought
  for use is sold) and banknotes.
- **A full inventory:** cook raw fish while fewer than FOOD pieces of food are held (the fishing guide cooks fish
  "for food"), then bank. A deposit keeps only the last task's kit (rlscape.sim.kits), so before a gathering skill
  the guide takes its tool back out (`bank_withdraw_for_<task>`) if it isn't held.
"""

from __future__ import annotations

import numpy as np

from rlscape.envs.sim_env import SimEnv
from rlscape.gamedata import server as gd
from rlscape.sim.buying import ARMOUR, AXES, PICKAXES, SCIMITARS, BankWithdrawForSale, is_upgrade, usable
from rlscape.sim.economy import kept_on_deposit
from rlscape.sim.slots import K
from rlscape.sim.state import CharacterState
from rlscape.vocabulary import vocabulary

FLY_ROD, FEATHERS, FEATHER_REORDER = 309, 314, 50
FOOD = 10  # pieces of food to keep; raw fish are cooked only below it
KIT_WITHDRAWAL = {"fish_shrimp": "bank_withdraw_for_fish_shrimp", "fish_fly": "bank_withdraw_for_fish_fly"}
COMBAT = ("attack", "strength", "defence")
SKILLS = (*COMBAT, "woodcutting", "mining", "fishing")  # SCHEDULE: the lowest of these is trained next
STYLE = {"attack": "accurate", "strength": "aggressive", "defence": "defensive"}
# Free-to-play melee training, January 2009 ([24]): monsters by the trained stat's level.
MELEE_BANDS = (
    (15, {"goblin", "cow", "cow calf", "chicken", "man", "woman", "seagull", "monk", "highwayman", "mugger"}),
    (30, {"cockroach drone", "barbarian", "al-kharid warrior", "minotaur", "dark warrior", "dark wizard", "wizard",
          "scorpion"}),
    (45, {"hill giant", "zombie", "hobgoblin", "skeleton"}),
    (55, {"moss giant", "black knight", "white knight", "deadly red spider", "al-kharid warrior"}),
    (75, {"ice warrior", "ice giant", "white knight", "cockroach worker", "catablepon", "zombie"}),
    (99, {"flesh crawler", "ankou", "lesser demon", "greater demon", "ice giant", "ice warrior", "giant spider",
          "cockroach soldier"}),
)


def woodcutting_method(level: int) -> str:
    return "wc_logs" if level < 15 else "wc_oak" if level < 41 else "wc_willow"


def mining_method(state: CharacterState) -> str:
    if state.level("mining") >= 15:
        return "mine_iron"
    copper, tin = (state.bank.get(i, 0) + state.inventory.get(i, 0) for i in (436, 438))
    return "mine_copper" if copper <= tin else "mine_tin"


def fishing_method(state: CharacterState) -> str:
    return "fish_fly" if state.level("fishing") >= 20 else "fish_shrimp"


class ScriptedGuidePolicy:
    name = "scripted_guide"

    def __init__(self) -> None:
        self.vocabulary = frozenset(vocabulary())
        self.last: str | None = None  # the previous option id

    def reset(self, seed: int | None) -> None:  # deterministic: nothing to seed
        self.last = None

    def act(self, env: SimEnv, obs: np.ndarray) -> int:
        state, mask = env.sim.state, env.action_masks()
        ids = {o.id: i for i, o in enumerate(env.options)}
        allowed = lambda option_id: option_id in ids and bool(mask[ids[option_id]])
        order = sorted(SKILLS, key=lambda s: (state.level(s), SKILLS.index(s)))  # SCHEDULE: lowest first
        action = next((ids[o] for o in self._plan(env, state, order, allowed) if allowed(o)), None)
        if action is None:
            action = int(np.flatnonzero(mask)[0])  # nothing in the plan is possible: the first allowed action
        self.last = env.options[action].id
        return action

    def _plan(self, env: SimEnv, state: CharacterState, order: list[str], allowed):
        """Option ids in order of preference; the first allowed one is taken. Logistics (upgrades, a full
        inventory) are decided for the skill due next, then each skill is tried in schedule order: a combat stat
        only with its own style, so a style no fight allows passes the turn to the next skill."""
        skill = order[0]
        if self.last == "bank_withdraw_gear_melee":
            yield from (f for s in COMBAT for f in self._fights(env, state, s))  # wear it before it's banked again
        prices, coins = gd.ge_prices_2009(), state.coins()
        roles = self._upgrades(state, skill)
        # per role, the best tier that's affordable; the guides move up a tier at a time ("mithril if you can
        # afford it")
        yield from (f"buy_ge_{best}" for tiers in roles if (best := next((i for i in tiers if prices[i] <= coins),
                                                                          None)) is not None)
        shortfall = min((prices[i] - coins for tiers in roles for i in tiers if prices[i] > coins), default=None)
        if shortfall is not None:  # fund the next upgrade, at GE prices
            carried = self._carried_for_sale(state)
            if sum(prices.get(i, 0) * n for i, n in carried.items()) >= shortfall:
                yield from (f"sell_ge_{item}" for item in sorted(carried, key=lambda i: -prices.get(i, 0) * carried[i]))
            banked = sum(prices.get(i, 0) * state.bank[i] for i in BankWithdrawForSale.produce(state))
            if sum(prices.get(i, 0) * n for i, n in carried.items()) + banked >= shortfall:
                yield "bank_withdraw_for_sale"
        if state.free_slots() == 0:
            if sum(state.inventory[i] for i in state.inventory if i in gd.food_healing()) < FOOD:
                yield "cook_fish"
            yield "bank_deposit"  # keeps the last task's kit (rlscape.sim.kits)
        for next_skill in order:
            if next_skill in COMBAT:
                fights = list(self._fights(env, state, next_skill))
                if any(allowed(f) for f in fights):  # withdraw gear only for a fight that can start
                    yield "bank_withdraw_gear_melee"
                yield from fights
            else:
                method = self._method(state, next_skill)
                yield method
                yield KIT_WITHDRAWAL.get(method, f"bank_withdraw_for_{next_skill}")  # its tool from the bank
                if next_skill == "fishing":
                    yield "fish_shrimp"  # no fly rod or feathers yet
                    yield "bank_withdraw_for_fish_shrimp"
        yield "bank_deposit"

    def _produce(self, item: int) -> bool:
        """Produce the guide sells from its inventory: vocabulary items that are neither gear nor kept when banking
        (tools, food, ammunition, runes), so it never sells what it bought to use."""
        definition = gd.items().get(item)
        return (item in self.vocabulary and not kept_on_deposit(item)
                and (definition is None or definition.equipment_slot is None))

    def _carried_for_sale(self, state: CharacterState) -> dict[int, int]:
        """Vocabulary item -> units carried to sell: its produce, and any banknotes (bank_withdraw_for_sale's)."""
        unnoted, out = gd.unnoted_ids(), {}
        for item, amount in state.inventory.items():
            real = unnoted.get(item, item)
            if real in self.vocabulary and (real != item or self._produce(item)):
                out[real] = out.get(real, 0) + amount
        return out

    @staticmethod
    def _method(state: CharacterState, skill: str) -> str:
        """The guide's method for a gathering skill at the character's level."""
        if skill == "woodcutting":
            return woodcutting_method(state.level("woodcutting"))
        return mining_method(state) if skill == "mining" else fishing_method(state)

    def _upgrades(self, state: CharacterState, skill: str) -> list[list[int]]:
        """The GE buys the guides call for now, by role in priority order (the skill's tool, the scimitar, then
        armour): each role's usable upgrades, best tier first."""
        chains: list[tuple[int, ...]] = [{"woodcutting": AXES, "mining": PICKAXES}.get(skill, ())]
        if skill == "fishing" and state.level("fishing") >= 20:
            chains += [(FLY_ROD,)] + ([(FEATHERS,)] if state.inventory.get(FEATHERS, 0) < FEATHER_REORDER else [])
        chains += [SCIMITARS, *(ARMOUR[piece::4] for piece in range(4))]  # helm, body, legs, kiteshield
        roles = [[i for i in reversed(chain) if usable(state, i) and (i == FEATHERS or is_upgrade(state, i))]
                 for chain in chains]
        return [tiers for tiers in roles if tiers]

    def _fights(self, env: SimEnv, state: CharacterState, skill: str):
        """The trained stat's style on the melee slots holding a monster from the guide's band for its level, then
        on the top XP slot."""
        band = next(names for top, names in MELEE_BANDS if state.level(skill) <= top)
        slots = next(o.slots for o in env.options if o.family == "combat")
        matching = [i for i in range(2 * K) if (c := slots.candidate(state, "melee", i)) is not None
                    and c.entry.npc.name.lower() in band]
        for index in [*matching, 0]:
            yield f"fight_melee_{'xp' if index < K else 'gp'}{index % K + 1}_{STYLE[skill]}"
