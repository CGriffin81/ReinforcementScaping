"""Combat candidate slots (option catalog §4): which monsters the agent is offered, recomputed every decision.

Pipeline for each decision:
  1. the enemy pool: every spawned NPC whose cache definition offers "Attack" and whose config stats are believable
     against its cache combat level (`enemy_pool`);
  2. per pool entry and combat class: the access table (rlscape.combat.access: only the sites the character can reach
     count; no Slayer levels, Caleb, 2026-11-07, OQ-32), the gear check for special damage, the loot the current loot mode keeps, the
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

from rlscape.combat.access import Progress, can_reach, start_progress
from rlscape.combat import neighbours as nb
from rlscape.combat import safespots as ss
from rlscape.combat.rates import (DRAGONFIRE_NPCS, OVERHEAD_TICKS_PER_KILL, PICKUP_TICKS, Fighter, Plan, Rates,
                                  combat_rates, site_slowdown, unharmed, with_pickups)
from rlscape.gamedata import server as gd
from rlscape.travel import BANKING_TICKS, EVERYWHERE, Reach, travel_ticks, travel_ticks_from_many

# Special damage (option catalog §4.B), from the server's NPC classes and ContentAPI.hasDragonfireShieldProtection.
ANTI_DRAGON_SHIELD, DRAGONFIRE_SHIELDS, ELEMENTAL_SHIELD, MIND_SHIELD = 1540, frozenset({11283, 11284}), 2890, 9731
DRAGONFIRE_PROTECTION = DRAGONFIRE_SHIELDS | {ANTI_DRAGON_SHIELD}
WYVERN_PROTECTION = DRAGONFIRE_SHIELDS | {ELEMENTAL_SHIELD, MIND_SHIELD}

# Training dummies can't be killed: CombatSwingHandler.adjustBattleState fully restores 4474 and 7891 and gives 0.1x XP.
UNKILLABLE_NPCS = frozenset({4474, 7891})

# Slayer monsters that need Slayer gear the sim doesn't model (none of it is in *V*), never offered. With Slayer levels
# dropped (Caleb, 2026-11-07, OQ-32) nothing else keeps them out. The server's rules: hits do nothing without a nose
# peg (aberrant spectres), earmuffs (banshees), a face mask (dust devils) or a leaf-bladed weapon (turoths, kurasks);
# a rock hammer, a bag of salt or an ice cooler finishes gargoyles, rockslugs and desert lizards; a lit bug lantern
# for harpie bug swarms; a witchwood icon, a mirror shield and insulated boots guard against cave horrors, basilisks
# and cockatrices, and killerwatts (the slayer package's NPC classes and behaviours).
SLAYER_GEAR_NPCS = frozenset({"Aberrant spectre", "Banshee", "Dust devil", "Turoth", "Kurask", "Gargoyle", "Rockslug",
                              "Desert Lizard", "Lizard", "Small Lizard", "Harpie Bug Swarm", "Cave horror", "Basilisk",
                              "Cockatrice", "Killerwatt"})

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
    # The animated spades in the Abandoned Mine's first floor, by the server's own zone (AbandonedMineZones.kt's
    # ZoneBorders) (Caleb, 2026-11-08, OQ-42): one that a character who has since left dealt more than half its
    # hitpoints can't be killed there, and stays alive at 0 (the zone throws on the null killer). The possessed
    # pickaxe beside them stays a target and an aggressor, and the spades in the Chaos Tunnels stay targets.
    (5414, (3395, 9609, 3448, 9664, 0)),
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
        if npc.id in UNKILLABLE_NPCS or "dummy" in npc.name.lower() or npc.name in SLAYER_GEAR_NPCS:
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
    arrow_piles: bool = True  # a ranged plan's shots land and the loot mode picks them up (rlscape.combat.safespots)
    shields_carried: frozenset[int] = frozenset()  # shields in the inventory: worn for a guarded pickup trip (OQ-33)
    combat_level: int = 3  # which aggressive monsters would pick it (rlscape.combat.neighbours)
    tolerance_left: float = nb.TOLERANCE_TICKS  # ticks until its own region's aggressive monsters leave it alone


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


@dataclass(frozen=True)
class Neighbours:
    """What a fight's neighbours need (rlscape.combat.neighbours): each one's kill in the plan (None: the plan can't
    hurt it, or it fails the danger filter), the character's combat level and location, its tolerance left, and the
    option's duration."""

    kills: dict[int, nb.NeighbourKill | None]
    combat_level: int
    location: tuple[int, int, int]
    tolerance_left: float
    duration: float

    def engagements(self, entry: PoolEntry, site: Site) -> list[tuple[nb.Neighbour, float]] | None:
        """The site's engaging neighbours with the share of the option before tolerance runs out there (as a
        multiplier of their rate); [] if none would engage; None if one can't be fought."""
        share = min(nb.aggression_ticks(site.spawn, self.location, self.tolerance_left) / self.duration, 1.0)
        engaged = nb.engaging(nb.site_neighbours(entry.npc.id, site.spawn), self.combat_level) if share > 0 else ()
        if any(self.kills.get(n.npc.id) is None for n in engaged):
            return None
        return [(n, share) for n in engaged]


def site_rates(entry: PoolEntry, plan: Plan, fought: Rates, site: Site, pickups: float, arrow_piles: bool,
               protected: bool, hp_margin: float, duration: float,
               shields_carried: frozenset[int] = frozenset(),
               neighbours: Neighbours | None = None) -> tuple[Rates, int] | None:
    """A monster's rates at one site, with each kill's pickups timed in, and the site's supply of it; None if the plan
    can't be fought there. A ranged or magic plan whose monster's damage isn't trivial over the option's `duration`
    with `hp_margin` above the retreat point (safespots.needs_safespot), or whose special damage the gear doesn't guard
    against (`protected` false: a bow takes no shield), needs the site's safespot, from which it takes none and fights
    only the monsters it holds against (Caleb: OQ-27 (d), and for magic OQ-34); a ranger's arrows land in piles,
    picked up with the drops after each kill, with the walk from the safespot and back (rlscape.combat.safespots).
    Away from a safespot, `neighbours` times in the fights with the site's aggressive monsters of other kinds
    (rlscape.combat.neighbours; Caleb, OQ-35 (a)); a site where one can't be fought is none."""
    overhead = OVERHEAD_TICKS_PER_KILL[plan.combat_class]
    spot = None
    if ss.distance_class(plan) and (not protected or ss.needs_safespot(fought, hp_margin, duration)):
        spot = ss.safespot(entry.npc.id, site.spawn, plan)
        if spot is None or (spot.pickup_threats and not protected
                            and not special_damage_shields(entry.npc) & shields_carried):
            return None  # guarded arrows are fetched late, a shield worn (or put on) for the trip (Caleb, OQ-33)
    piles = 0
    if plan.combat_class == "ranged" and arrow_piles and (spot is None or spot.walk is not None):
        piles = ss.piles_per_kill(ss.fighting_ticks(fought, overhead))
    items = pickups + piles
    extra = PICKUP_TICKS * items + (ss.trip_ticks(spot) if items > 0 else 0.0)  # as with_pickups adds them
    rates = with_pickups(unharmed(fought) if spot is not None else fought, items,
                         ss.trip_ticks(spot) if items > 0 else 0.0)
    if spot is None and neighbours is not None:
        engaged = neighbours.engagements(entry, site)
        if engaged is None:
            return None
        if engaged:
            slow = float(site_slowdown(rates.ticks_per_kill, entry.npc.respawn, site.spawns, overhead + extra))
            exposed = nb.exposed_per_kill(overhead + extra, rates.ticks_per_kill, slow)
            rates = nb.with_neighbours(rates, [(share * nb.ENGAGE_PER_TICK * n.spawns * exposed,
                                                neighbours.kills[n.npc.id]) for n, share in engaged])
    return rates, (min(site.spawns, spot.held) if spot is not None else site.spawns)


def neighbour_kills(entry: PoolEntry, fighter: Fighter, plan: Plan, character: Character, loot: Callable[[int], bool],
                    shield: int | None, rates_of: Callable[[gd.Npc], Rates | None] | None = None,
                    loot_of: Callable[[gd.Npc], tuple[float, float]] | None = None) -> dict[int, nb.NeighbourKill | None]:
    """Each engaging neighbour's kill at the monster's sites, in the plan, the fighter as armed (None: the plan can't
    hurt it, the gear doesn't guard its special damage, it's beyond the server data's believable stats or a monster
    needing Slayer gear, or it fails the danger filter). `rates_of` and `loot_of`, if given, are the fast ranker's
    cached combat_rates (gp aside) and (gp, pickups) per kill for a neighbour, the same numbers."""
    out: dict[int, nb.NeighbourKill | None] = {}
    drops = gd.drop_tables()
    for site in entry.sites:
        for n in nb.engaging(nb.site_neighbours(entry.npc.id, site.spawn), character.combat_level):
            if n.npc.id in out:
                continue
            table = drops.get(n.npc.id)
            gp, pickups = loot_of(n.npc) if loot_of else (loot_per_kill(table, loot)[0], pickups_per_kill(table, loot))
            fought = rates_of(n.npc) if rates_of else combat_rates(fighter, plan, n.npc, gp)
            usable = (fought is not None and has_special_damage_protection(n.npc, shield)
                      and n.npc.name not in SLAYER_GEAR_NPCS and n.npc.id not in UNKILLABLE_NPCS
                      and fought.passes_retreat_filter(character.max_hp, character.current_hp, character.food_healing,
                                                       poison_cover=character.poison_cover,
                                                       antifire_cover=character.antifire_cover))
            out[n.npc.id] = nb.neighbour_kill(fought, gp, PICKUP_TICKS * pickups) if usable else None
    return out


def evaluate(entry: PoolEntry, fighter: Fighter, plan: Plan, character: Character, duration_ticks: float,
             loot: Callable[[int], bool], shield_id: int | None = None) -> Candidate | None:
    """One monster, one plan: None if access, the gear check or the danger filter rules it out everywhere. `shield_id`,
    if given, is the shield the fighter wears in place of the character's. No Slayer levels (Caleb, OQ-32)."""
    sites = [s for s in entry.sites if can_reach(entry.npc.name, s.spawn, character.progress)
             and character.reach.allows(s.spawn)]
    shield = character.shield_id if shield_id is None else shield_id
    protected = has_special_damage_protection(entry.npc, shield)  # a ranger or caster can do without, from a safespot
    if not sites or not (protected or ss.distance_class(plan)):
        return None
    gp_per_kill, slots_per_kill = loot_per_kill(entry.drops, loot)
    fought = combat_rates(fighter, plan, entry.npc, gp_per_kill)
    if fought is None:
        return None
    pickups = pickups_per_kill(entry.drops, loot)
    overhead = OVERHEAD_TICKS_PER_KILL[plan.combat_class]
    neighbours = Neighbours(neighbour_kills(entry, fighter, plan, character, loot, shield), character.combat_level,
                            character.location, character.tolerance_left, duration_ticks)
    options = []
    for site in sites:
        got = site_rates(entry, plan, fought, site, pickups, character.arrow_piles, protected,
                         ss.hp_margin(character.current_hp, character.max_hp), duration_ticks,
                         character.shields_carried, neighbours)
        if got is not None and got[0].passes_retreat_filter(character.max_hp, character.current_hp,
                                                            character.food_healing,
                                                            poison_cover=character.poison_cover,
                                                            antifire_cover=character.antifire_cover):
            options.append((site, *got))
    if not options:
        return None

    def share_at(site: Site, rates: Rates, spawns: int) -> float:
        # kills come slower where the site runs out of monsters (site_slowdown): the inventory and the ammunition
        # last that much longer, and the rate is that much lower
        slow = float(site_slowdown(rates.ticks_per_kill, entry.npc.respawn, spawns,
                                   overhead + rates.ticks_per_kill - fought.ticks_per_kill))
        fight_ticks = character.free_slots / slots_per_kill * rates.ticks_per_kill if slots_per_kill > 0 else None
        fill = None if fight_ticks is None else fight_ticks * slow
        fighting = 1.0 if fill is None else (fill / (fill + site.bank_trip_ticks) if fill > 0 else 0.0)
        walking = max(duration_ticks - travel_ticks(character.location, site.spawn, character.home_teleport),
                      0.0) / duration_ticks
        ammo_share = character.attacks_held / rates.attacks_per_kill * rates.ticks_per_kill / duration_ticks
        return min(fighting * walking, ammo_share * slow) / slow  # the option ends when the ammunition does

    # the site where it's killed fastest over the option: its share of the option times the kill rate there (the same
    # at every site unless a ranged fight's pickup walks differ)
    shares = [share_at(*option) for option in options]
    # the first best, compared rounded (as monsters are: an ammunition cap makes every site's equal, and float noise
    # in the neighbours' arithmetic would decide)
    best = max(range(len(options)), key=lambda i: _tie(options[i][1].kills_per_hour * shares[i]))
    site, rates, _ = options[best]
    share = shares[best]
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
