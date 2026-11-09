"""Fights, drops and death, with event-level sampling (option catalog §4, env contract §1).

A fight (`fight`) walks to the monster's site, wields the best gear carried (rlscape.sim.equipment), then repeats kills
until the time budget, a full inventory, running out of food, or death:
- the attacks a kill takes are sampled from the server's hit chance and uniform 0..max-hit damage (one vectorised
  draw per kill); the monster attacks every attack_speed ticks of the fight, each hit resolved in turn;
- HP at or below half the maximum means eating (a bite delays the next attack 3 ticks, ConsumableListener) or, with
  no food, retreating: the monster gets ESCAPE_ATTACKS more swings and the option ends out_of_food;
- XP follows CombatSwingHandler: 4 per damage to the style's skill and 1.33 to Hitpoints, for the monster's HP;
  magic also gives the spell's base XP on every cast, hit or splash (MagicSpell.addExperience);
- each kill rolls its drop table (WeightBasedTable.roll) and keeps what the loot mode picks up, PICKUP_TICKS a ground
  item (measured, as the overhead);
- the site has `site.spawns` of the monster, each back `respawn` ticks after it dies: the next kill starts when one
  is there, after the class's OVERHEAD_TICKS_PER_KILL to reach it (both measured, scripts/calibrate_combat.py). Waiting, nothing
  attacks;
- ranged fires one arrow, bolt or thrown weapon per attack from the worn stack (RangeSwingHandler.useAmmo). A shot
  lands under the target with arrow_land_chance (the rest break) and comes back when the loot mode takes that item,
  so with looting only broken shots run the stack down. Ranged fights safespot (rlscape.combat.safespots): a
  monster whose damage isn't trivial is fought from the site's safespot, where it can't attack, and only the
  site's monsters the safespot holds against are fought. The landed shots lie in piles, a PICKUP_TICKS each, picked
  up with the drops between kills, with the walk from the safespot and back; while aggressive monsters guard them
  and aggression hasn't run out (TOLERANCE_TICKS in the region), the fight leaves them until the oldest would go
  (Caleb, OQ-27 (d)). The shots' return is counted at the kill. Magic casts the spell chosen for the fight, paying
  its runes per cast (a worn elemental staff
  stands in for its rune; MagicStaff). Either ends the option out_of_ammo when the stack or the runes run out,
  charging the attacks made. Casting each spell by hand is assumed, at the autocast rate (5 ticks), so magic
  doesn't need a staff (an agent choice; the server's autocast does; checked live, 2026-11-07). Magic safespots as
  ranged does, at range 10, without piles (Caleb, OQ-34);
- away from a safespot, the site's aggressive monsters of other kinds engage the character between kills, until the
  region's tolerance runs out (FightNeighbours, rlscape.combat.neighbours; Caleb, OQ-35 (a)): each is killed, in
  the fight's plan, before the next target (`kill`, the same as a target's, its drops by the loot mode).

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

from rlscape.combat import neighbours as nb
from rlscape.combat import safespots as ss
from rlscape.combat.candidates import PoolEntry, Site, has_special_damage_protection, special_damage_shields
from rlscape.combat.prayers import boosted_swings
from rlscape.combat.rates import (BREATH_CHANCE, DRAGONFIRE_MAX, DRAGONFIRE_NPCS, ESCAPE_ATTACKS, OVERHEAD_TICKS_PER_KILL,
                                  PICKUP_TICKS, POISON_CHANCE, Plan, breath_max, combat_rates, npc_offence,
                                  player_offence)
from rlscape.gamedata import server as gd
from rlscape.sim.energy import MAX_ENERGY
from rlscape.sim.equipment import SHIELD, WEAPON, fighter_for, land_chance, ranged_ready, shot_outcomes, wield_best
from rlscape.sim.health import advance_poison, apply_poison, eat_one, regenerate, retreat_hp
from rlscape.sim.movement import route_ticks, walk
from rlscape.sim.potions import drink_antifire, drink_boosts
from rlscape.sim.options import COMPLETED, DIED, INVENTORY_FULL, OUT_OF_AMMO, OUT_OF_FOOD, Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import TOLERANCE_TICKS, CharacterState

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


def _pick(entries, rng: np.random.Generator) -> gd.DropEntry | None:
    """One weighted pick, or None from an empty table."""
    total = sum(e.weight for e in entries)
    if total <= 0:
        return None
    pick = rng.random() * total
    for entry in entries:
        pick -= entry.weight
        if pick <= 0:
            return entry
    return entries[-1]


def _items(entry: gd.DropEntry, rng: np.random.Generator) -> list[tuple[int, int]]:
    """What a dropped entry gives (WeightBasedTable.convertWeightedItems): its item, or for a sub-table's slot that
    table's pick, as many times as its amount for the herb and uncommon seed slots. "Nothing" and clue scrolls give
    nothing."""
    if not entry.item_id:
        return []
    if not entry.special:
        return [(entry.item_id, _amount(entry, rng))]
    table = gd.sub_tables().get(entry.item_id)
    if table is None:
        return []  # a clue scroll
    out = []
    for _ in range(_amount(entry, rng) if entry.item_id in gd.MULTI_ROLL_SLOTS else 1):
        picked = _pick(table, rng)
        if picked is not None and picked.item_id:
            out.append((picked.item_id, _amount(picked, rng)))
    return out


def roll_drops(table: gd.DropTable | None, rng: np.random.Generator) -> list[tuple[int, int]]:
    """WeightBasedTable.roll: every guaranteed entry, then one weighted pick from each of the main, charm and
    tertiary tables; a sub-table's slot rolls that table (_items)."""
    if table is None:
        return []
    drops = [item for e in table.guaranteed for item in _items(e, rng)]
    for entries in (table.main, table.charm, table.tertiary):
        picked = _pick(entries, rng)
        if picked is not None:
            drops += _items(picked, rng)
    return drops


def kill_sequence(hitpoints: int, chance: float, max_hit: int, rng: np.random.Generator,
                  boosted: tuple[float, int, tuple[bool, ...]] | None = None) -> np.ndarray:
    """Cumulative damage after each attack, up to the one that kills: each attack hits with `chance` for uniform
    0..max_hit. Its length is the number of attacks the kill takes. With `boosted` (chance, max hit, pattern), the
    attacks the pattern marks, repeating from the kill's first, use the boosted chance and max hit: those that get
    the flicked accuracy and damage prayers (rlscape.combat.prayers)."""
    if boosted is not None and all(boosted[2]):
        chance, max_hit, boosted = boosted[0], boosted[1], None
    elif boosted is not None and not any(boosted[2]):
        boosted = None
    parts, done = [], 0
    batch = max(8, ceil(4 * hitpoints / max(chance * max_hit / 2, 0.1)))
    while True:
        if boosted is None:
            damage = np.cumsum((rng.random(batch) < chance) * rng.integers(0, max_hit + 1, batch)) + done
        else:
            pattern = np.array(boosted[2])
            on = pattern[(sum(len(p) for p in parts) + np.arange(batch)) % len(pattern)]
            chances, max_hits = np.where(on, boosted[0], chance), np.where(on, boosted[1], max_hit)
            damage = np.cumsum((rng.random(batch) < chances) * rng.integers(0, max_hits + 1)) + done
        reached = np.flatnonzero(damage >= hitpoints)
        if reached.size:
            parts.append(damage[:reached[0] + 1])
            return np.concatenate(parts)
        parts.append(damage)
        done = int(damage[-1])


def attacks_to_kill(hitpoints: int, chance: float, max_hit: int, rng: np.random.Generator) -> int:
    return len(kill_sequence(hitpoints, chance, max_hit, rng))


def arrow_land_chance(ranged_level: int) -> float:
    """RangeSwingHandler.useAmmo, with no Ava's device: a fired shot lands under the target unless randomize(int(5 x
    (1 + level / 100))) is 0, which breaks it. 4 in 5 at level 1, 8 in 9 at 99 (equipment.land_chance)."""
    return land_chance(ranged_level)


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
                loot: Callable[[int], bool],
                recover: bool = True) -> tuple[int, Callable[[int], None], Callable[[int], int]]:
    """How many of a kill's `attacks` the ammunition or runes allow, a function paying for the first k, and one
    counting the shots among them that landed and are picked back up (`recover`: false where the piles can't be
    walked to)."""
    if plan.combat_class == "magic":
        cost = spell_runes(state, plan.style)

        def pay_runes(k: int) -> None:
            for rune, n in cost.items():
                state.take(rune, n * k)
        return int(min(attacks, casts_held(state, plan.style))), pay_runes, lambda k: 0
    if plan.combat_class == "ranged":
        if not ranged_ready(state):
            return 0, lambda k: None, lambda k: 0
        ranged = gd.ranged_weapons()[state.equipment[WEAPON]]
        if ranged.weapon_type == "DEGRADING":
            return attacks, lambda k: None, lambda k: 0
        slot = ranged.ammo_slot
        back, landed = shot_outcomes(state)  # Ava's device sends some back to the quiver
        if not (recover and loot(state.equipment[slot])):
            landed = 0.0  # left on the ground
        draws = rng.random(attacks)
        lost = np.cumsum(draws >= back + landed)  # the rest come back: to the quiver, or picked up from the piles
        picked = np.cumsum((draws >= back) & (draws < back + landed))

        def pay_ammo(k: int) -> None:
            if k:
                state.use_worn(slot, int(lost[k - 1]))
        # attack i needs a shot left: fewer than the worn stack lost before it
        return (min(attacks, int(np.searchsorted(lost, state.worn(slot))) + 1), pay_ammo,
                lambda k: int(picked[k - 1]) if k else 0)
    return attacks, lambda k: None, lambda k: 0


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
    """DeathTask: keep the 3 most valuable items by high-alchemy value (none while skulled: getContainers); the rest
    go into a gravestone (none in the Wilderness or skulled, GraveController.allowGenerate: lost); respawn at full HP
    at the home location."""
    alch = gd.alchemy_values()
    skulled = now < state.skulled_until
    units = [item for item, amount in state.inventory.items() for _ in range(amount if amount < 100 else 1)]
    units += list(state.equipment.values())  # a worn stack (quiver, thrown weapon) counts as one unit
    kept = sorted(units, key=lambda item: alch.get(item, (0, 0))[0], reverse=True)[:0 if skulled else KEPT_ON_DEATH]
    everything: dict[int, int] = {}
    for container in (state.inventory, {item: state.worn(slot) for slot, item in state.equipment.items()}):
        for item, amount in container.items():
            everything[item] = everything.get(item, 0) + amount
    for item in kept:
        everything[item] -= 1
    lost = {item: amount for item, amount in everything.items() if amount > 0}
    state.gravestone = None if in_wilderness(state.location) or skulled or not lost else Gravestone(
        state.location, lost, now + GRAVESTONE_TICKS)
    state.inventory, state.equipment, state.worn_amounts = {}, {}, {}
    for item in kept:
        state.add(item)
    state.hp, state.location, state.run_energy = state.max_hp(), RESPAWN, MAX_ENERGY  # Player.finalizeDeath
    state.poison_severity = state.poison_clock = state.poison_immune_until = 0  # both timers clear on death
    state.boosts, state.antifire_until = {}, 0  # the stats are restored; the immunity clears
    state.skulled_until = 0  # the skull clears on death (Player.finalizeDeath; Skulled's ClearOnDeath)
    state.region_since = now  # respawned into Lumbridge's region


SWAP_TICKS = 2  # the shield on for a guarded pickup trip, the bow back after (a click each)


def guarded_trip(state: CharacterState, rng: np.random.Generator, npc: gd.Npc, fighter, plan: Plan, guards: int,
                 trip: float, now: int) -> int:
    """A late pickup trip where aggressive monsters guard the arrows (Caleb, 2026-11-07, OQ-33): each guard, taken as
    the target's kind, swings every attack_speed ticks of it. Against a dragon's breath the ranger wears the shield it
    carries for the trip (a bow takes none; SWAP_TICKS) and drinks an antifire dose if it has one: shield and potion,
    no breath at all; the potion alone cuts only a tenth (ContentAPI.calculateDragonfireMaxHit). A guard is any
    aggressive monster whose leash covers the arrows (the export's count), and most don't come: each swings at
    safespots.GUARD_SWINGS_PER_TICK, measured on the server's late trips (the gathering rate, used before, killed
    most band-1 casters at the Black Knights in the sim, none on the server). The hitpoints go; returns the ticks
    the swap and the drink add."""
    extra = 0
    dragon = npc.id in DRAGONFIRE_NPCS
    worn = state.equipment.get(SHIELD) in special_damage_shields(npc)  # with a crossbow, it's on already
    shielded = dragon and (worn or bool(special_damage_shields(npc) & set(state.inventory)))
    if shielded and not worn:
        extra += SWAP_TICKS
    if dragon:
        extra += drink_antifire(state, now)
    antifire = now + extra < state.antifire_until
    npc_chance, npc_max, _, _ = npc_offence(fighter, plan, npc)
    swings = int(rng.poisson(guards * (trip + extra) * ss.GUARD_SWINGS_PER_TICK))
    hits = (rng.random(swings) < npc_chance) * rng.integers(0, npc_max + 1, swings)
    if dragon:
        fire = breath_max(antifire) if shielded else int(DRAGONFIRE_MAX - (0.1 * DRAGONFIRE_MAX if antifire else 0.0))
        hits = np.where(rng.random(swings) < BREATH_CHANCE, rng.integers(0, fire + 1, swings), hits)
    state.hp -= int(hits.sum())
    return extra


def safespot_for(state: CharacterState, plan: Plan, npc: gd.Npc, site: Site,
                 duration: float) -> gd.RangedSafespot | None:
    """The safespot a ranged or magic fight attacks from, the character armed: the site's, if the monster's damage
    isn't trivial over `duration` (the fight would need food) or its special damage isn't guarded against
    (rlscape.combat.safespots); None otherwise, or if the site has none."""
    if not ss.distance_class(plan):
        return None
    unaided = combat_rates(fighter_for(state), plan, npc, 0.0)
    guarded = has_special_damage_protection(npc, state.equipment.get(SHIELD))
    if unaided is None or (guarded and not ss.needs_safespot(unaided, ss.hp_margin(state.hp, state.max_hp()),
                                                             duration)):
        return None
    return ss.safespot(npc.id, site.spawn, plan)


@dataclass
class FightNeighbours:
    """A fight's neighbours that would engage the character (rlscape.combat.neighbours): each spawn engages at
    nb.ENGAGE_PER_TICK while the character is exposed (between kills), until `tolerated_at` ticks into the option.
    With none, nothing here draws from the rng."""

    active: tuple[nb.Neighbour, ...]
    tolerated_at: float  # ticks into the option when the region's tolerance runs out

    @classmethod
    def at(cls, state: CharacterState, npc: gd.Npc, site: Site, spot) -> FightNeighbours:
        """At the site, the character there (its region's tolerance counting from its arrival); none from a
        safespot."""
        if spot is not None:
            return cls((), 0.0)
        active = nb.engaging(nb.site_neighbours(npc.id, site.spawn), state.combat_level())
        return cls(active, state.region_since + nb.TOLERANCE_TICKS - state.tick)

    def engagement(self, rng: np.random.Generator, start: float, length: float) -> tuple[float, nb.Neighbour] | None:
        """The first engagement in an exposed stretch of `length` ticks from `start` ticks into the option: (its
        offset into the stretch, the neighbour); memoryless, so each stretch draws on its own."""
        end = min(start + length, self.tolerated_at)
        if not self.active or end <= start or nb.ENGAGE_PER_TICK <= 0:
            return None
        spawns = np.array([n.spawns for n in self.active], dtype=float)
        t = rng.exponential(1 / (nb.ENGAGE_PER_TICK * spawns.sum()))
        if start + t >= end:
            return None
        return t, self.active[int(rng.choice(len(self.active), p=spawns / spawns.sum()))]


def fight(state: CharacterState, rng: np.random.Generator, budget: int, entry: PoolEntry, plan: Plan, site: Site,
          loot: Callable[[int], bool]) -> OptionResult:
    npc, stackable, kills, neighbour_kills = entry.npc, gd.stackable_items(), 0, 0
    cast_xp = gd.combat_spells()[plan.style].experience if plan.combat_class == "magic" else 0.0

    def done(ticks: int, termination: str, regenerated: bool = True) -> OptionResult:
        detail = {"target": npc.id, "target_name": npc.name, "style": plan.style, "site": site.spawn, "kills": kills,
                  "neighbour_kills": neighbour_kills}
        return OptionResult(ticks, termination, regenerated, detail)

    def poisoned_to_death(ticks: int) -> OptionResult | None:
        """After time passed outside a kill's swings (poison advanced in bulk): the death, if the poison killed."""
        if state.hp > 0:
            return None
        die(state, state.tick + ticks)
        return done(max(ticks, 1), DIED)

    elapsed = walk(state, site.spawn, budget)
    if elapsed is None:
        return done(budget, COMPLETED, regenerated=False)
    regenerate(state, elapsed)
    if (dead := poisoned_to_death(elapsed)) is not None:
        return dead
    wielding = wield_best(state, plan.combat_class, special_damage_shields(entry.npc))  # its anti-dragon shield
    elapsed = min(elapsed + wielding, budget)
    spot = safespot_for(state, plan, npc, site, budget)
    recover = spot is None or spot.walk is not None  # its arrows can be walked to
    trip = ss.trip_ticks(spot)
    supply = min(site.spawns, spot.held) if spot is not None else site.spawns
    ready = [0] * max(supply, 1)  # when each of the site's monsters is next there to fight (ticks into the option)
    piles: list[int] = []  # when each arrow pile not yet picked up was started (ticks into the option)
    waiting, waiting_since = 0, inf  # drops left with them, and since when
    neighbours = FightNeighbours.at(state, npc, site, spot)  # other kinds that engage it (OQ-35)
    tables = gd.drop_tables()

    def kill(target: gd.Npc, drops: gd.DropTable | None, here: int | None) -> tuple[OptionResult | None, float]:
        """One kill of `target` (the fight's monster `here`, or a neighbour with None), its drops and the pickups
        after it: the option's end if it ends in it, and the ticks after it with nothing attacking the character
        (the overhead to the next monster and the pickups), when a neighbour can engage."""
        nonlocal elapsed, kills, neighbour_kills, piles, waiting, waiting_since
        fighter = fighter_for(state)
        chance, max_hit, speed, _, xp_per_damage = player_offence(fighter, plan, target)
        boosted_chance, boosted_max, _, _, _ = player_offence(fighter, plan, target, boosted=True)
        npc_chance, npc_max, _, _ = npc_offence(fighter, plan, target)
        boosted = None
        if (boosted_chance, boosted_max) != (chance, max_hit):
            boosted = (boosted_chance, boosted_max, boosted_swings(int(speed), target.attack_speed))
        dealt = kill_sequence(target.hitpoints, chance, max_hit, rng, boosted)
        possible, pay, landed = _ammunition(state, plan, len(dealt), rng, loot, recover)
        if possible == 0:
            return done(max(elapsed, 1), OUT_OF_AMMO), 0.0

        def charge(attacks: int) -> None:
            """Pay for the attacks made and credit their XP: the damage dealt, capped at the monster's HP, and for
            magic the spell's base XP on every cast."""
            pay(attacks)
            _gain(state, xp_per_damage, min(int(dealt[attacks - 1]), target.hitpoints) if attacks else 0)
            _gain(state, {"magic": cast_xp}, attacks if cast_xp else 0)

        ticks = possible * speed
        swings = int(ticks // target.attack_speed) if spot is None else 0  # stuck chasing, it can't attack
        hits = (rng.random(swings) < npc_chance) * rng.integers(0, npc_max + 1, swings)
        if target.id in DRAGONFIRE_NPCS and spot is None:  # a third of its swings are breath, behind the shield
            elapsed += drink_antifire(state, state.tick + elapsed)
            fire = breath_max(state.tick + elapsed < state.antifire_until)
            hits = np.where(rng.random(swings) < BREATH_CHANCE, rng.integers(0, fire + 1, swings), hits)
        ended, eating, poisoned_to = None, 0, 0  # poisoned_to: ticks into the kill the poison has been advanced to
        for j, hit in enumerate(hits):
            swing_at = (j + 1) * target.attack_speed + eating
            advance_poison(state, swing_at - poisoned_to, state.tick + elapsed + poisoned_to)
            poisoned_to = swing_at
            state.hp -= int(hit)
            if target.poisonous and rng.random() < POISON_CHANCE:
                eating += apply_poison(state, target.poison_amount, state.tick + elapsed + swing_at)  # a dose drunk
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
                fought = min((j + 1) * target.attack_speed + eating, ticks, budget - elapsed)
                charge(min(int(fought // speed), possible))
                elapsed += fought
                regenerate(state, fought, poison=False)
                advance_poison(state, max(fought - poisoned_to, 0))
                if ended == OUT_OF_FOOD and state.hp <= 0:
                    ended = DIED  # the poison went on
                if ended == DIED:
                    die(state, state.tick + elapsed)
                return done(max(elapsed, 1), ended), 0.0
        if possible < len(dealt):
            # the ammunition or runes run out before the kill: charge the attacks made
            fought = min(ticks + eating, budget - elapsed)
            charge(min(int(fought // speed), possible))
            elapsed += fought
            regenerate(state, fought, poison=False)
            advance_poison(state, max(fought - poisoned_to, 0))
            return poisoned_to_death(elapsed) or done(max(elapsed, 1), OUT_OF_AMMO), 0.0
        overhead = OVERHEAD_TICKS_PER_KILL[plan.combat_class]
        step = ticks + eating + overhead
        if elapsed + step > budget:
            regenerate(state, budget - elapsed, poison=False)
            advance_poison(state, max(budget - elapsed - poisoned_to, 0))
            return poisoned_to_death(budget) or done(budget, COMPLETED), 0.0
        if here is not None:
            ready[here] = elapsed + ticks + eating + target.respawn  # it died at the end of the fight
        elapsed += step
        regenerate(state, step, poison=False)
        advance_poison(state, max(step - poisoned_to, 0))
        charge(possible)
        if here is not None:
            kills += 1
        else:
            neighbour_kills += 1
        if (dead := poisoned_to_death(elapsed)) is not None:
            return dead, 0.0  # after the kill, before the loot
        picked = sum(1 for item, amount in roll_drops(drops, rng) if loot(item) and state.add(item, amount))
        if landed(possible):  # this kill's arrows, a pile per PILE_PRIVATE_TICKS of shooting
            piles += [elapsed - step] * ss.piles_per_kill(ticks)
        if picked:
            waiting, waiting_since = waiting + picked, min(waiting_since, elapsed - step)
        # between kills, unless the walk to them would take hits: aggressive monsters guard them and aggression hasn't
        # run out; then just before the oldest would go, the next kill and the walk counted
        safe = spot is None or spot.pickup_threats == 0 or state.region_since + TOLERANCE_TICKS <= state.tick + elapsed
        due = elapsed - min(piles[0] if piles else inf, waiting_since) + step + trip >= ss.GROUND_TICKS
        between = float(overhead)
        if (waiting or piles) and (safe or due):  # a pickup each, after the kill, with the walk to them
            pickup = PICKUP_TICKS * (waiting + len(piles)) + (trip if spot is not None else 0.0)
            if not safe:  # the late trip, guarded: the guards' hits, the shield worn against dragonfire (OQ-33)
                pickup += guarded_trip(state, rng, npc, fighter_for(state), plan, spot.pickup_threats, pickup,
                                       state.tick + elapsed)
                if state.hp <= 0:
                    die(state, state.tick + elapsed)
                    return done(max(elapsed, 1), DIED), 0.0
            pickup = int(ceil(min(pickup, budget - elapsed)))
            piles, waiting, waiting_since = [], 0, inf
            elapsed += pickup
            between += pickup
            regenerate(state, pickup, poison=False)
            advance_poison(state, pickup)
            if (dead := poisoned_to_death(elapsed)) is not None:
                return dead, 0.0
            if elapsed >= budget:
                return done(budget, COMPLETED), 0.0
        if state.free_slots() == 0 and any(loot(i) and i not in stackable for i, _ in (entry.drops.expected_items()
                                                                                       .items() if entry.drops else ())):
            return done(elapsed, INVENTORY_FULL), 0.0
        return None, between

    def fight_back(engaged: tuple[float, nb.Neighbour] | None) -> OptionResult | None:
        """Neighbours that engaged it, one at a time (single combat): each killed before the next target, and another
        can engage in the stretch after it."""
        while engaged is not None:
            if state.hp <= retreat_hp(state) and not eat_one(state):
                return done(max(elapsed, 1), OUT_OF_FOOD)
            neighbour = engaged[1]
            ended, between = kill(neighbour.npc, tables.get(neighbour.npc.id), None)
            if ended is not None:
                return ended
            engaged = neighbours.engagement(rng, elapsed - between, between)
        return None

    while True:
        if state.hp <= retreat_hp(state):
            if not eat_one(state):
                return done(max(elapsed, 1), OUT_OF_FOOD)
            continue
        if (drank := drink_boosts(state, plan.combat_class)) and elapsed + drank >= budget:
            return done(budget, COMPLETED)
        elapsed += drank  # potions, if it carries them (rlscape.sim.potions)
        here = min(range(len(ready)), key=ready.__getitem__)  # the one back first
        if ready[here] > elapsed:  # every one of them is dead: wait for a respawn
            wait_end = min(ready[here], budget)
            engaged = neighbours.engagement(rng, elapsed, wait_end - elapsed)
            if engaged is not None:  # a neighbour engages it while it waits
                regenerate(state, int(engaged[0]))
                elapsed += int(engaged[0])
                if (dead := poisoned_to_death(elapsed)) is not None:
                    return dead
                if (ended := fight_back(engaged)) is not None:
                    return ended
                continue
            if ready[here] >= budget:
                regenerate(state, budget - elapsed)
                return poisoned_to_death(budget) or done(budget, COMPLETED)
            regenerate(state, ready[here] - elapsed)
            elapsed = ready[here]
            if (dead := poisoned_to_death(elapsed)) is not None:
                return dead
            continue  # eat, if the poison brought HP to the retreat point
        ended, between = kill(npc, entry.drops, here)
        if ended is not None:
            return ended
        if (ended := fight_back(neighbours.engagement(rng, elapsed - between, between))) is not None:
            return ended


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
