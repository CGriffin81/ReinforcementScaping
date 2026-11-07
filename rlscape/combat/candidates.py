"""Combat candidate slots (option catalog §4): which monsters the agent is offered, recomputed every decision.

Pipeline for each decision:
  1. the enemy pool: every spawned NPC whose cache definition offers "Attack" and whose config stats are believable
     against its cache combat level (`enemy_pool`);
  2. per pool entry and combat class: the Slayer level and the access table (rlscape.combat.access: only the sites the
     character can reach count), the gear check for special damage, the loot the current loot mode keeps, the
     theoretical rates (rlscape.combat.rates), the retreat-aware danger filter, and the inventory cycle (fighting
     until the drops fill the free slots, then the round trip to the nearest bank);
  3. per combat class: the 3 best monsters by XP/hr and the 3 best by gp/hr (`select_candidates`).

Travel times (rlscape.travel) use straight-line tile distance with a detour factor and an assumed running speed, and the bank list is
curated (data/banks.csv). All are marked for calibration on the server.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from math import floor, inf
from typing import Callable

from rlscape.combat.access import Progress, can_reach, meets_slayer_level, start_progress
from rlscape.combat.rates import (DRAGONFIRE_NPCS, OVERHEAD_TICKS_PER_KILL, PICKUP_TICKS, Fighter, Plan, Rates,
                                  combat_rates, site_slowdown, with_pickups)
from rlscape.gamedata import server as gd
from rlscape.travel import BANKING_TICKS, EVERYWHERE, Reach, travel_ticks, travel_ticks_from_many

# Special damage (option catalog §4.B), from the server's NPC classes and ContentAPI.hasDragonfireShieldProtection.
ANTI_DRAGON_SHIELD, DRAGONFIRE_SHIELDS, ELEMENTAL_SHIELD, MIND_SHIELD = 1540, frozenset({11283, 11284}), 2890, 9731
DRAGONFIRE_PROTECTION = DRAGONFIRE_SHIELDS | {ANTI_DRAGON_SHIELD}
WYVERN_PROTECTION = DRAGONFIRE_SHIELDS | {ELEMENTAL_SHIELD, MIND_SHIELD}

# Training dummies can't be killed: CombatSwingHandler.adjustBattleState fully restores 4474 and 7891 and gives 0.1x XP.
UNKILLABLE_NPCS = frozenset({4474, 7891})

# Hazards: monsters never offered as targets where they spawn in the area (x1, y1, x2, y2, plane), though they stay in
# the world: the aggressive ones still attack a character near them (rlscape.sim.aggression reads every spawn).
HAZARDS = (
    # Taverley dungeon's two Black Knights east of the lesser demons (Caleb, 2026-11-05): on the server the attack
    # click does nothing, with no message (scripts/calibrate_combat.py: four cases, no XP). The dungeon's other
    # Black Knights, by the jail, fight as usual (checked live) and stay targets (Caleb, 2026-11-06).
    (178, (2936, 9796, 2945, 9815, 0)),
    # The four moss giants west of the Fishing Guild (Caleb, 2026-11-06): the attack click does nothing there
    # either (scripts/probe_drops.py: no kill in 2,000 ticks; spawns 2551-2560, 3400-3411). The goblins beside
    # them aren't in it, and the other moss giants stay targets.
    (112, (2545, 3394, 2566, 3417, 0)),
)


# Areas out of the project (x1, y1, x2, y2, plane): no monster there is a target, as with the hazards.
IGNORED_AREAS = (
    # The Yanille Agility Dungeon (Caleb, 2026-11-06: "Ignore the yanille dungeon for this project"), by the server's
    # own zone (YanilleAgilityDungeon.kt's ZoneBorders). Its inner room, the chaos druids' with Salarin the Twisted,
    # is past a pile of rubble that takes Agility 67, and Salarin, whom only the strike spells hurt, holds a
    # character there in single combat.
    (2544, 9481, 2631, 9587, 0),
)


def is_hazard(npc_id: int, tile: tuple[int, int, int]) -> bool:
    """Not a target at this spawn: a hazard there, or in an area out of the project."""
    return (any(npc_id == hazard and x1 <= tile[0] <= x2 and y1 <= tile[1] <= y2 and tile[2] == z
                for hazard, (x1, y1, x2, y2, z) in HAZARDS)
            or any(x1 <= tile[0] <= x2 and y1 <= tile[1] <= y2 and tile[2] == z
                   for x1, y1, x2, y2, z in IGNORED_AREAS))

LOOT_MODES = ("all", "valuable", "vocabulary", "none")
VALUABLE_GP = 100
COMBAT_CLASSES = ("melee", "ranged", "magic")


def config_combat_level(npc: gd.Npc) -> int:
    """The combat level npc_configs.json's stats imply (the 2009 formula, prayer 0)."""
    base = 0.25 * (npc.defence + npc.hitpoints)
    style = max(0.325 * (npc.attack + npc.strength), 0.325 * floor(1.5 * npc.ranged), 0.325 * floor(1.5 * npc.magic))
    return floor(base + style)


def stats_believable(npc: gd.Npc, definition: gd.NpcDefinition) -> bool:
    """Config stats much weaker than the cache combat level are placeholders (many NPCs carry attack / strength /
    defence 1 and 10 HP). The server fights with them, so leaving those NPCs in would let the agent farm, say,
    level-90 zombies with level-10 stats. Calibrated on the data: flags 124 of 1,184 attackable spawned NPCs."""
    return config_combat_level(npc) >= definition.combat_level / 2 - 2


@dataclass(frozen=True)
class Site:
    """One place an NPC spawns (one per 64x64 map region), with the nearest bank to it."""

    spawn: tuple[int, int, int]
    bank: gd.Bank
    bank_trip_ticks: float  # walk to the bank, bank, walk back
    spawns: int = 1  # of the same NPC within SITE_RADIUS of the spawn, itself included: what the site can supply


@dataclass(frozen=True)
class PoolEntry:
    npc: gd.Npc
    definition: gd.NpcDefinition
    sites: tuple[Site, ...]
    drops: gd.DropTable | None


@cache
def enemy_pool(members: bool = True) -> tuple[PoolEntry, ...]:
    """Every NPC the agent could fight, as far as server data can tell (see the module docstring for what's next)."""
    definitions, drops = gd.npc_definitions(), gd.drop_tables()
    spawns = {npc_id: [s for s in tiles if not is_hazard(npc_id, tuple(s))] for npc_id, tiles in gd.spawns().items()}
    spawns = {npc_id: tiles for npc_id, tiles in spawns.items() if tiles}  # the spawns it can be fought at
    bank_list = [b for b in gd.banks() if members or not b.members]
    eligible = []
    for npc in gd.npcs().values():
        definition = definitions.get(npc.id)
        if npc.id not in spawns or definition is None or not definition.attackable:
            continue
        if npc.id in UNKILLABLE_NPCS or "dummy" in npc.name.lower():
            continue
        if not stats_believable(npc, definition):
            continue
        eligible.append((npc, definition))
    # every spawn's trip to every bank, a search from each bank (one per spawn would take minutes)
    tiles = sorted({tuple(spawn) for npc, _ in eligible for spawn in spawns[npc.id]})
    to_bank = {b: dict(zip(tiles, travel_ticks_from_many(tiles, (b.x, b.y, b.plane)))) for b in bank_list}
    pool = []
    for npc, definition in eligible:
        by_region: dict[tuple[int, int, int], Site] = {}
        for spawn in spawns[npc.id]:
            region = (spawn[0] >> 6, spawn[1] >> 6, spawn[2])
            trip, bank = min(((to_bank[b][tuple(spawn)], b) for b in bank_list), key=lambda t: t[0])
            nearby = sum(s[2] == spawn[2] and max(abs(s[0] - spawn[0]), abs(s[1] - spawn[1])) <= SITE_RADIUS
                         for s in spawns[npc.id])
            site = Site(spawn, bank, 2 * trip + BANKING_TICKS, nearby)
            if region not in by_region or site.bank_trip_ticks < by_region[region].bank_trip_ticks:
                by_region[region] = site
        pool.append(PoolEntry(npc, definition, tuple(by_region.values()), drops.get(npc.id)))
    return tuple(pool)


SITE_RADIUS = 15  # tiles: the monsters a character fighting at a spawn picks from (an agent choice, calibrated)


def loot_rule(mode: str, vocabulary: frozenset[int] = frozenset()) -> Callable[[int], bool]:
    """What a loot mode picks up (option catalog §4.D). Stackables (coins, runes, arrows, ...) cost no new slot."""
    values, stackable = gd.item_values(), gd.stackable_items()
    if mode == "all":
        return lambda item: True
    if mode == "valuable":
        return lambda item: item in stackable or item in vocabulary or values.get(item, 0) >= VALUABLE_GP
    if mode == "vocabulary":
        return lambda item: item in stackable or item in vocabulary
    if mode == "none":
        return lambda item: False
    raise ValueError(f"unknown loot mode {mode!r}")


def loot_per_kill(drops: gd.DropTable | None, loot: Callable[[int], bool]) -> tuple[float, float]:
    """(gp, new inventory slots) per kill for the items the loot rule keeps."""
    if drops is None:
        return 0.0, 0.0
    values, stackable = gd.item_values(), gd.stackable_items()
    gp = slots = 0.0
    for item, count in drops.expected_items().items():
        if loot(item):
            gp += count * values.get(item, 0)
            if item not in stackable:
                slots += count
    return gp, slots


def pickups_per_kill(drops: gd.DropTable | None, loot: Callable[[int], bool]) -> float:
    """The drops per kill the loot rule picks up, a pickup each (rates.with_pickups times them)."""
    if drops is None:
        return 0.0
    return sum(count for item, count in drops.expected_items(stacks=True).items() if loot(item))


def special_damage_shields(npc: gd.Npc) -> frozenset[int]:
    """The shields that protect against the monster's special damage; empty when it has none."""
    if npc.id in DRAGONFIRE_NPCS:
        return DRAGONFIRE_PROTECTION
    if "wyvern" in npc.name.lower():
        return WYVERN_PROTECTION
    return frozenset()


def has_special_damage_protection(npc: gd.Npc, shield_id: int | None) -> bool:
    """The gear check for special damage (Caleb's addition to the danger filter)."""
    shields = special_damage_shields(npc)
    return not shields or shield_id in shields


@dataclass(frozen=True)
class Character:
    """What the candidate ranking needs to know about the character right now."""

    location: tuple[int, int, int]
    max_hp: int
    current_hp: float
    food_healing: float  # total healing of the food in the inventory
    free_slots: int
    shield_id: int | None
    loot_mode: str = "valuable"
    # quests, items held and levels, for the access table; default: a new character's (every quest complete)
    progress: Progress = field(default_factory=start_progress)
    attacks_held: float = inf  # the shots or casts the ammunition or runes allow, for the class being ranked
    home_teleport: bool = True  # the home teleport is ready (a fresh character's is)
    reach: Reach = EVERYWHERE  # where it can get to now (rlscape.sim.movement.reach); default: anywhere some way goes
    poison_cover: float = 0.0  # the share of the option the antipoison carried keeps poison off (rlscape.sim.health)
    antifire_cover: float = 0.0  # the share the antifire carried keeps a dragon's breath off (rlscape.sim.potions)


@dataclass(frozen=True)
class Candidate:
    entry: PoolEntry
    plan: Plan
    site: Site  # where to fight it, chosen for the best rate from the character's location
    rates: Rates  # raw fighting rates, before banking and travel
    kills_per_hour: float  # over the option's duration, with bank trips and the walk there
    xp_per_hour: dict[str, float]
    gp_per_hour: float
    travel_ticks: float  # from the character's location to the monster

    @property
    def total_xp_per_hour(self) -> float:
        return sum(self.xp_per_hour.values())


def evaluate(entry: PoolEntry, fighter: Fighter, plan: Plan, character: Character, duration_ticks: float,
             loot: Callable[[int], bool], shield_id: int | None = None) -> Candidate | None:
    """One monster, one plan: None if access, the gear check or the danger filter rules it out. `shield_id`, if
    given, is the shield the fighter wears in place of the character's."""
    if not meets_slayer_level(entry.npc.id, character.progress):
        return None
    sites = [s for s in entry.sites if can_reach(entry.npc.name, s.spawn, character.progress)
             and character.reach.allows(s.spawn)]
    shield = character.shield_id if shield_id is None else shield_id
    if not sites or not has_special_damage_protection(entry.npc, shield):
        return None
    gp_per_kill, slots_per_kill = loot_per_kill(entry.drops, loot)
    rates = combat_rates(fighter, plan, entry.npc, gp_per_kill)
    pickups = pickups_per_kill(entry.drops, loot)
    rates = rates and with_pickups(rates, pickups, plan.combat_class)
    if rates is None or not rates.passes_retreat_filter(character.max_hp, character.current_hp, character.food_healing,
                                                        poison_cover=character.poison_cover,
                                                        antifire_cover=character.antifire_cover):
        return None
    fight_ticks = character.free_slots / slots_per_kill * rates.ticks_per_kill if slots_per_kill > 0 else None
    ammo_share = character.attacks_held / rates.attacks_per_kill * rates.ticks_per_kill / duration_ticks

    def share_at(site: Site) -> float:
        # kills come slower where the site runs out of monsters (site_slowdown): the inventory and the ammunition
        # last that much longer, and the rate is that much lower
        slow = float(site_slowdown(rates.ticks_per_kill, entry.npc.respawn, site.spawns,
                                   OVERHEAD_TICKS_PER_KILL[plan.combat_class]
                                   + PICKUP_TICKS[plan.combat_class] * pickups))
        fill = None if fight_ticks is None else fight_ticks * slow
        fighting = 1.0 if fill is None else (fill / (fill + site.bank_trip_ticks) if fill > 0 else 0.0)
        walking = max(duration_ticks - travel_ticks(character.location, site.spawn, character.home_teleport),
                      0.0) / duration_ticks
        return min(fighting * walking, ammo_share * slow) / slow  # the option ends when the ammunition does

    site = max(sites, key=share_at)
    share = share_at(site)
    return Candidate(entry, plan, site, rates, rates.kills_per_hour * share,
                     {skill: xp * share for skill, xp in rates.xp_per_hour.items()}, rates.gp_per_hour * share,
                     travel_ticks(character.location, site.spawn, character.home_teleport))


# Rates are compared rounded, so equal ones (an ammunition cap gives many) tie in both rankers, which compute them in
# different orders (float noise in the last bit decided which won)
TIE_DECIMALS = 6


def _tie(value: float) -> float:
    return round(value, TIE_DECIMALS)


def select_candidates(pool: tuple[PoolEntry, ...], plans: dict[str, tuple[Fighter, list[Plan]]], character: Character,
                      duration_ticks: float, k: int = 3, vocabulary: frozenset[int] = frozenset(),
                      dragonfire: dict[str, Fighter] | None = None) -> dict[str, list[Candidate]]:
    """For each available combat class: the k best monsters by XP/hr, then the k best by gp/hr (option catalog §4.A).

    `plans` maps a class to the fighter as equipped for it and the plans to consider (melee: its training styles;
    ranged: e.g. rapid; magic: the best spell the runes allow). A class missing from `plans` is unavailable (no bow
    and arrows, no runes). Monsters are ranked by their best plan, and different NPC ids sharing a name count as one
    monster, so the slots name distinct monsters.

    `dragonfire` maps a class to its fighter wearing an anti-dragon shield the character carries, where the class's
    own gear has no dragonfire protection: the fight puts that shield on against dragonfire monsters
    (equipment.wield_best's `protect`), so they're ranked for it.
    """
    loot = loot_rule(character.loot_mode, vocabulary)
    out: dict[str, list[Candidate]] = {}
    for combat_class, (fighter, class_plans) in plans.items():
        shielded = (dragonfire or {}).get(combat_class)
        best: dict[str, tuple[Candidate, Candidate]] = {}  # name -> (best by XP, best by gp)
        for entry in pool:
            for plan in class_plans:
                if shielded is not None and entry.npc.id in DRAGONFIRE_NPCS:
                    candidate = evaluate(entry, shielded, plan, character, duration_ticks, loot, ANTI_DRAGON_SHIELD)
                else:
                    candidate = evaluate(entry, fighter, plan, character, duration_ticks, loot)
                if candidate is None:
                    continue
                name = entry.npc.name
                by_xp, by_gp = best.get(name, (candidate, candidate))
                if _tie(candidate.total_xp_per_hour) > _tie(by_xp.total_xp_per_hour):
                    by_xp = candidate
                if _tie(candidate.gp_per_hour) > _tie(by_gp.gp_per_hour):
                    by_gp = candidate
                best[name] = (by_xp, by_gp)
        xp_slots = sorted((pair[0] for pair in best.values()), key=lambda c: _tie(c.total_xp_per_hour), reverse=True)[:k]
        taken = {c.entry.npc.name for c in xp_slots}
        gp_slots = sorted((pair[1] for name, pair in best.items() if name not in taken),
                          key=lambda c: _tie(c.gp_per_hour), reverse=True)[:k]
        out[combat_class] = xp_slots + gp_slots
    return out
