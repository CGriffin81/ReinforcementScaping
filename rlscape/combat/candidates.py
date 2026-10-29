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

from dataclasses import dataclass
from functools import cache
from math import floor, inf
from typing import Callable

from rlscape.combat.access import Progress, can_reach, meets_slayer_level
from rlscape.combat.rates import Fighter, Plan, Rates, combat_rates
from rlscape.gamedata import server as gd
from rlscape.travel import BANKING_TICKS, travel_ticks

# Special damage (option catalog §4.B), from the server's NPC classes and ContentAPI.hasDragonfireShieldProtection.
DRAGONFIRE_NPCS = frozenset({
    941, 4677, 4678, 4679, 4680,  # green dragons      (ChromaticDragonNPC)
    55, 4681, 4682, 4683, 4684,   # blue dragons
    53, 4669, 4670, 4671, 4672,   # red dragons
    54, 4673, 4674, 4675, 4676,   # black dragons
    8629,                         # lava dragon
    1590, 1591, 1592, 3590,       # bronze / iron / steel dragons (MetalDragonNPC)
    50,                           # King Black Dragon  (KingBlackDragonNPC)
    742,                          # Elvarg             (ElvargNPC)
})
ANTI_DRAGON_SHIELD, DRAGONFIRE_SHIELDS, ELEMENTAL_SHIELD, MIND_SHIELD = 1540, frozenset({11283, 11284}), 2890, 9731
DRAGONFIRE_PROTECTION = DRAGONFIRE_SHIELDS | {ANTI_DRAGON_SHIELD}
WYVERN_PROTECTION = DRAGONFIRE_SHIELDS | {ELEMENTAL_SHIELD, MIND_SHIELD}

# Training dummies can't be killed: CombatSwingHandler.adjustBattleState fully restores 4474 and 7891 and gives 0.1x XP.
UNKILLABLE_NPCS = frozenset({4474, 7891})

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


@dataclass(frozen=True)
class PoolEntry:
    npc: gd.Npc
    definition: gd.NpcDefinition
    sites: tuple[Site, ...]
    drops: gd.DropTable | None


@cache
def enemy_pool(members: bool = True) -> tuple[PoolEntry, ...]:
    """Every NPC the agent could fight, as far as server data can tell (see the module docstring for what's next)."""
    definitions, drops, spawns = gd.npc_definitions(), gd.drop_tables(), gd.spawns()
    bank_list = [b for b in gd.banks() if members or not b.members]
    pool = []
    for npc in gd.npcs().values():
        definition = definitions.get(npc.id)
        if npc.id not in spawns or definition is None or not definition.attackable:
            continue
        if npc.id in UNKILLABLE_NPCS or "dummy" in npc.name.lower():
            continue
        if not stats_believable(npc, definition):
            continue
        by_region: dict[tuple[int, int, int], Site] = {}
        for spawn in spawns[npc.id]:
            region = (spawn[0] >> 6, spawn[1] >> 6, spawn[2])
            trip, bank = min(((travel_ticks(spawn, (b.x, b.y, b.plane)), b) for b in bank_list), key=lambda t: t[0])
            site = Site(spawn, bank, 2 * trip + BANKING_TICKS)
            if region not in by_region or site.bank_trip_ticks < by_region[region].bank_trip_ticks:
                by_region[region] = site
        pool.append(PoolEntry(npc, definition, tuple(by_region.values()), drops.get(npc.id)))
    return tuple(pool)


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


def has_special_damage_protection(npc: gd.Npc, shield_id: int | None) -> bool:
    """The gear check for special damage (Caleb's addition to the danger filter)."""
    if npc.id in DRAGONFIRE_NPCS:
        return shield_id in DRAGONFIRE_PROTECTION
    if "wyvern" in npc.name.lower():
        return shield_id in WYVERN_PROTECTION
    return True


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
    progress: Progress = Progress()  # quests, items held and levels, for the access table; default: fresh
    attacks_held: float = inf  # the shots or casts the ammunition or runes allow, for the class being ranked


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
             loot: Callable[[int], bool]) -> Candidate | None:
    """One monster, one plan: None if access, the gear check or the danger filter rules it out."""
    if not meets_slayer_level(entry.npc.id, character.progress):
        return None
    sites = [s for s in entry.sites if can_reach(entry.npc.name, s.spawn, character.progress)]
    if not sites or not has_special_damage_protection(entry.npc, character.shield_id):
        return None
    gp_per_kill, slots_per_kill = loot_per_kill(entry.drops, loot)
    rates = combat_rates(fighter, plan, entry.npc, gp_per_kill)
    if rates is None or not rates.passes_retreat_filter(character.max_hp, character.current_hp, character.food_healing):
        return None
    fight_ticks = character.free_slots / slots_per_kill * rates.ticks_per_kill if slots_per_kill > 0 else None
    ammo_share = character.attacks_held / rates.attacks_per_kill * rates.ticks_per_kill / duration_ticks

    def share_at(site: Site) -> float:
        fighting = 1.0 if fight_ticks is None else (fight_ticks / (fight_ticks + site.bank_trip_ticks) if fight_ticks > 0 else 0.0)
        walking = max(duration_ticks - travel_ticks(character.location, site.spawn), 0.0) / duration_ticks
        return min(fighting * walking, ammo_share)  # the option ends when the ammunition does

    site = max(sites, key=share_at)
    share = share_at(site)
    return Candidate(entry, plan, site, rates, rates.kills_per_hour * share,
                     {skill: xp * share for skill, xp in rates.xp_per_hour.items()}, rates.gp_per_hour * share,
                     travel_ticks(character.location, site.spawn))


def select_candidates(pool: tuple[PoolEntry, ...], plans: dict[str, tuple[Fighter, list[Plan]]], character: Character,
                      duration_ticks: float, k: int = 3,
                      vocabulary: frozenset[int] = frozenset()) -> dict[str, list[Candidate]]:
    """For each available combat class: the k best monsters by XP/hr, then the k best by gp/hr (option catalog §4.A).

    `plans` maps a class to the fighter as equipped for it and the plans to consider (melee: its training styles;
    ranged: e.g. rapid; magic: the best spell the runes allow). A class missing from `plans` is unavailable (no bow
    and arrows, no runes). Monsters are ranked by their best plan, and different NPC ids sharing a name count as one
    monster, so the slots name distinct monsters.
    """
    loot = loot_rule(character.loot_mode, vocabulary)
    out: dict[str, list[Candidate]] = {}
    for combat_class, (fighter, class_plans) in plans.items():
        best: dict[str, tuple[Candidate, Candidate]] = {}  # name -> (best by XP, best by gp)
        for entry in pool:
            for plan in class_plans:
                candidate = evaluate(entry, fighter, plan, character, duration_ticks, loot)
                if candidate is None:
                    continue
                name = entry.npc.name
                by_xp, by_gp = best.get(name, (candidate, candidate))
                if candidate.total_xp_per_hour > by_xp.total_xp_per_hour:
                    by_xp = candidate
                if candidate.gp_per_hour > by_gp.gp_per_hour:
                    by_gp = candidate
                best[name] = (by_xp, by_gp)
        xp_slots = sorted((pair[0] for pair in best.values()), key=lambda c: c.total_xp_per_hour, reverse=True)[:k]
        taken = {c.entry.npc.name for c in xp_slots}
        gp_slots = sorted((pair[1] for name, pair in best.items() if name not in taken),
                          key=lambda c: c.gp_per_hour, reverse=True)[:k]
        out[combat_class] = xp_slots + gp_slots
    return out
