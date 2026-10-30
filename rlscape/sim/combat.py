"""Fights, drops and death, with event-level sampling (option catalog §4, env contract §1).

A fight (`fight`) walks to the monster's site, wields the best gear carried (rlscape.sim.equipment), then repeats kills
until the time budget, a full inventory, running out of food, or death:
- the attacks a kill takes are sampled from the server's hit chance and uniform 0..max-hit damage (one vectorised
  draw per kill); the monster attacks every attack_speed ticks of the fight, each hit resolved in turn;
- HP at or below half the maximum means eating (a bite delays the next attack 3 ticks, ConsumableListener) or, with
  no food, retreating: the monster gets ESCAPE_ATTACKS more swings and the option ends out_of_food;
- XP follows CombatSwingHandler: 4 per damage to the style's skill and 1.33 to Hitpoints, for the monster's HP;
  magic also gives the spell's base XP on every cast, hit or splash (MagicSpell.addExperience);
- each kill rolls its drop table (WeightBasedTable.roll) and keeps what the loot mode picks up;
- ranged fires one arrow, bolt or thrown weapon per attack from the worn stack (RangeSwingHandler.useAmmo). A shot
  lands under the target with arrow_land_chance (the rest break) and is picked straight back up when the loot mode
  takes that item, so with looting only broken shots run the stack down. The pick-up time is in the per-kill
  overhead (calibrate). Magic casts the spell chosen for the fight, paying its runes per cast (a worn elemental staff
  stands in for its rune; MagicStaff). Either ends the option out_of_ammo when the stack or the runes run out,
  charging the attacks made. Casting each spell by hand is assumed, at the autocast rate (5 ticks), so magic
  doesn't need a staff (an agent choice; the server's autocast does).

Death (DeathTask, GraveController, GraveType): the character respawns at rl.conf's home_location with full run energy
(Player.finalizeDeath); the 3 most valuable items by high-alchemy value are kept (no skull in training; Protect Item
isn't modelled); outside the Wilderness the rest goes into a gravestone for 200 ticks, which reclaim_gravestone
recovers by walking back in time; in the Wilderness the rest is lost. Items in a gravestone aren't counted in net worth until recovered.

A kill still in progress when the time budget runs out earns nothing and uses no ammunition. The candidate-slot
actions that start fights are in rlscape.sim.slots.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import ceil, inf

import numpy as np

from rlscape.combat.candidates import PoolEntry, Site
from rlscape.combat.rates import ESCAPE_ATTACKS, OVERHEAD_TICKS_PER_KILL, Plan, npc_offence, player_offence
from rlscape.gamedata import server as gd
from rlscape.sim.energy import MAX_ENERGY
from rlscape.sim.equipment import WEAPON, fighter_for, ranged_ready, wield_best
from rlscape.sim.health import eat_one, regenerate, retreat_hp
from rlscape.sim.movement import route_ticks, walk
from rlscape.sim.options import COMPLETED, DIED, INVENTORY_FULL, OUT_OF_AMMO, OUT_OF_FOOD, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import CharacterState

RESPAWN = (3222, 3218, 0)  # rl.conf: home_location = "3222,3218,0"
GRAVESTONE_TICKS = 200  # GraveType.MEM_PLAQUE, the free gravestone: 2 minutes
KEPT_ON_DEATH = 3  # DeathTask.getContainers: 3, none when skulled, +1 with Protect Item
EAT_DELAY_TICKS = 3  # ConsumableListener: delayAttack(player, 3)
# WildernessZone's borders: the surface, part of the Edgeville dungeon, and three dungeon regions (12192, 12193,
# 11937 as ZoneBorders.forRegion).
WILDERNESS = ((2944, 3525, 3400, 3975), (3070, 9924, 3135, 10002), (3008, 10240, 3071, 10303),
              (3008, 10304, 3071, 10367), (2944, 10304, 3007, 10367))


def in_wilderness(tile: tuple[int, int, int]) -> bool:
    return any(x1 <= tile[0] <= x2 and y1 <= tile[1] <= y2 for x1, y1, x2, y2 in WILDERNESS)


def _amount(entry: gd.DropEntry, rng: np.random.Generator) -> int:
    """WeightedItem.getItem: RandomFunction.random(min, max), upper bound excluded."""
    return entry.min_amount if entry.max_amount <= entry.min_amount else int(rng.integers(entry.min_amount,
                                                                                           entry.max_amount))


def roll_drops(table: gd.DropTable | None, rng: np.random.Generator) -> list[tuple[int, int]]:
    """WeightBasedTable.roll: every guaranteed entry, then one weighted pick from each of the main, charm and
    tertiary tables. "Nothing" and the sub-table placeholders (rare drop table, gems, herbs, seeds, clues) give
    nothing, as gd.SPECIAL_DROP_SLOTS explains."""
    if table is None:
        return []
    drops = [(e.item_id, _amount(e, rng)) for e in table.guaranteed if e.item_id and not e.special]
    for entries in (table.main, table.charm, table.tertiary):
        total = sum(e.weight for e in entries)
        if total > 0:
            pick = rng.random() * total
            for entry in entries:
                pick -= entry.weight
                if pick <= 0:
                    if entry.item_id and not entry.special:
                        drops.append((entry.item_id, _amount(entry, rng)))
                    break
    return drops


def kill_sequence(hitpoints: int, chance: float, max_hit: int, rng: np.random.Generator) -> np.ndarray:
    """Cumulative damage after each attack, up to the one that kills: each attack hits with `chance` for uniform
    0..max_hit. Its length is the number of attacks the kill takes."""
    parts, done = [], 0
    batch = max(8, ceil(4 * hitpoints / max(chance * max_hit / 2, 0.1)))
    while True:
        damage = np.cumsum((rng.random(batch) < chance) * rng.integers(0, max_hit + 1, batch)) + done
        reached = np.flatnonzero(damage >= hitpoints)
        if reached.size:
            parts.append(damage[:reached[0] + 1])
            return np.concatenate(parts)
        parts.append(damage)
        done = int(damage[-1])


def attacks_to_kill(hitpoints: int, chance: float, max_hit: int, rng: np.random.Generator) -> int:
    return len(kill_sequence(hitpoints, chance, max_hit, rng))


def arrow_land_chance(ranged_level: int) -> float:
    """RangeSwingHandler.useAmmo: a fired shot lands under the target unless randomize(int(5 × (1 + level / 100)))
    is 0, which breaks it (Ava's devices aren't modelled). 4 in 5 at level 1, 8 in 9 at 99."""
    return 1 - 1 / int(5 * (1.0 + ranged_level * 0.01))


def spell_runes(state: CharacterState, spell: str) -> dict[int, int]:
    """The runes one cast takes from the inventory: the spell's, less any the worn staff stands in for."""
    staff, staves = state.equipment.get(WEAPON), gd.staff_runes()
    return {rune: n for rune, n in gd.combat_spells()[spell].runes.items() if staff not in staves.get(rune, ())}


def casts_held(state: CharacterState, spell: str) -> float:
    """How many casts the runes in the inventory pay for (unlimited if a staff stands in for them all)."""
    return min((state.inventory.get(rune, 0) // n for rune, n in spell_runes(state, spell).items()), default=inf)


def best_spell(state: CharacterState) -> str | None:
    """The highest-level elemental spell the Magic level allows and the runes held pay for at least once. Max hits
    rise with spell level, so it's also the strongest."""
    castable = [s for s in gd.combat_spells().values()
                if s.level <= state.level("magic") and casts_held(state, s.name) >= 1]
    return max(castable, key=lambda s: s.level).name if castable else None


def _ammunition(state: CharacterState, plan: Plan, attacks: int, rng: np.random.Generator,
                loot: Callable[[int], bool]) -> tuple[int, Callable[[int], None]]:
    """How many of a kill's `attacks` the ammunition or runes allow, and a function paying for the first k."""
    if plan.combat_class == "magic":
        cost = spell_runes(state, plan.style)

        def pay_runes(k: int) -> None:
            for rune, n in cost.items():
                state.take(rune, n * k)
        return int(min(attacks, casts_held(state, plan.style))), pay_runes
    if plan.combat_class == "ranged":
        if not ranged_ready(state):
            return 0, lambda k: None
        ranged = gd.ranged_weapons()[state.equipment[WEAPON]]
        if ranged.weapon_type == "DEGRADING":
            return attacks, lambda k: None
        slot = ranged.ammo_slot
        if ranged.drop_ammo and loot(state.equipment[slot]):  # landed shots come straight back
            lost = np.cumsum(rng.random(attacks) >= arrow_land_chance(state.level("ranged")))
        else:
            lost = np.arange(1, attacks + 1)

        def pay_ammo(k: int) -> None:
            if k:
                state.use_worn(slot, int(lost[k - 1]))
        # attack i needs a shot left: fewer than the worn stack lost before it
        return min(attacks, int(np.searchsorted(lost, state.worn(slot))) + 1), pay_ammo
    return attacks, lambda k: None


def _gain(state: CharacterState, xp_per_damage: dict[str, float], damage: float) -> None:
    for skill, rate in xp_per_damage.items():
        i = SKILL_INDEX[skill]
        state.xp[i] = min(state.xp[i] + rate * damage, MAX_XP)


@dataclass
class Gravestone:
    tile: tuple[int, int, int]
    items: dict[int, int]
    expires_at: int  # game tick


def die(state: CharacterState, now: int) -> None:
    """DeathTask: keep the 3 most valuable items by high-alchemy value; the rest go into a gravestone (or are lost in
    the Wilderness); respawn at full HP at the home location."""
    alch = gd.alchemy_values()
    units = [item for item, amount in state.inventory.items() for _ in range(amount if amount < 100 else 1)]
    units += list(state.equipment.values())  # a worn stack (quiver, thrown weapon) counts as one unit
    kept = sorted(units, key=lambda item: alch.get(item, (0, 0))[0], reverse=True)[:KEPT_ON_DEATH]
    everything: dict[int, int] = {}
    for container in (state.inventory, {item: state.worn(slot) for slot, item in state.equipment.items()}):
        for item, amount in container.items():
            everything[item] = everything.get(item, 0) + amount
    for item in kept:
        everything[item] -= 1
    lost = {item: amount for item, amount in everything.items() if amount > 0}
    state.gravestone = None if in_wilderness(state.location) or not lost else Gravestone(state.location, lost,
                                                                                         now + GRAVESTONE_TICKS)
    state.inventory, state.equipment, state.worn_amounts = {}, {}, {}
    for item in kept:
        state.add(item)
    state.hp, state.location, state.run_energy = state.max_hp(), RESPAWN, MAX_ENERGY  # Player.finalizeDeath


def fight(state: CharacterState, rng: np.random.Generator, budget: int, entry: PoolEntry, plan: Plan, site: Site,
          loot: Callable[[int], bool]) -> OptionResult:
    npc, stackable, kills = entry.npc, gd.stackable_items(), 0
    cast_xp = gd.combat_spells()[plan.style].experience if plan.combat_class == "magic" else 0.0

    def done(ticks: int, termination: str, regenerated: bool = True) -> OptionResult:
        detail = {"target": npc.id, "target_name": npc.name, "style": plan.style, "site": site.spawn, "kills": kills}
        return OptionResult(ticks, termination, regenerated, detail)

    elapsed = walk(state, site.spawn, budget)
    if elapsed is None:
        return done(budget, COMPLETED, regenerated=False)
    regenerate(state, elapsed)
    wielding = wield_best(state, plan.combat_class)
    elapsed = min(elapsed + wielding, budget)
    while True:
        if state.hp <= retreat_hp(state):
            if not eat_one(state):
                return done(max(elapsed, 1), OUT_OF_FOOD)
            continue
        fighter = fighter_for(state)
        chance, max_hit, speed, _, xp_per_damage = player_offence(fighter, plan, npc)
        npc_chance, npc_max, _, _ = npc_offence(fighter, plan, npc)
        dealt = kill_sequence(npc.hitpoints, chance, max_hit, rng)
        possible, pay = _ammunition(state, plan, len(dealt), rng, loot)
        if possible == 0:
            return done(max(elapsed, 1), OUT_OF_AMMO)

        def charge(attacks: int) -> None:
            """Pay for the attacks made and credit their XP: the damage dealt, capped at the monster's HP, and for
            magic the spell's base XP on every cast."""
            pay(attacks)
            _gain(state, xp_per_damage, min(int(dealt[attacks - 1]), npc.hitpoints) if attacks else 0)
            _gain(state, {"magic": cast_xp}, attacks if cast_xp else 0)

        ticks = possible * speed
        swings = int(ticks // npc.attack_speed)
        hits = (rng.random(swings) < npc_chance) * rng.integers(0, npc_max + 1, swings)
        ended, eating = None, 0
        for j, hit in enumerate(hits):
            state.hp -= int(hit)
            if state.hp > 0 and state.hp <= retreat_hp(state):
                if eat_one(state):
                    eating += EAT_DELAY_TICKS
                    continue
                escape = (rng.random(ESCAPE_ATTACKS) < npc_chance) * rng.integers(0, npc_max + 1, ESCAPE_ATTACKS)
                state.hp -= int(escape.sum())
                ended = OUT_OF_FOOD
            if state.hp <= 0:
                ended = DIED
            if ended:
                # the fight stops at this monster swing: charge the time and the damage dealt so far
                fought = min((j + 1) * npc.attack_speed + eating, ticks, budget - elapsed)
                charge(min(int(fought // speed), possible))
                elapsed += fought
                regenerate(state, fought)
                if ended == DIED:
                    die(state, state.tick + elapsed)
                return done(max(elapsed, 1), ended)
        if possible < len(dealt):
            # the ammunition or runes run out before the kill: charge the attacks made
            fought = min(ticks + eating, budget - elapsed)
            charge(min(int(fought // speed), possible))
            elapsed += fought
            regenerate(state, fought)
            return done(max(elapsed, 1), OUT_OF_AMMO)
        step = ticks + eating + OVERHEAD_TICKS_PER_KILL
        if elapsed + step > budget:
            regenerate(state, budget - elapsed)
            return done(budget, COMPLETED)
        elapsed += step
        regenerate(state, step)
        charge(possible)
        kills += 1
        for item, amount in roll_drops(entry.drops, rng):
            if loot(item):
                state.add(item, amount)
        if state.free_slots() == 0 and any(loot(i) and i not in stackable for i, _ in (entry.drops.expected_items()
                                                                                       .items() if entry.drops else ())):
            return done(elapsed, INVENTORY_FULL)


class ReclaimGravestone(Option):
    """After a death outside the Wilderness: walk back and take everything from the gravestone, if the walk fits in its
    remaining time. Items that don't fit in the inventory are left behind."""

    family = "inventory"

    def __init__(self, option_id: str = "reclaim_gravestone"):
        self.id = option_id

    def available(self, state: CharacterState) -> bool:
        grave = state.gravestone
        return grave is not None and state.tick + route_ticks(state, grave.tile) < grave.expires_at

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        grave = state.gravestone
        walked = walk(state, grave.tile, min(budget, grave.expires_at - state.tick))
        if walked is None:
            return OptionResult(min(budget, max(grave.expires_at - state.tick, 1)), COMPLETED)
        for item, amount in grave.items.items():
            state.add(item, amount)
        state.gravestone = None
        return OptionResult(max(walked, 1), COMPLETED)
