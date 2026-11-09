"""Aggressive monsters near a site, and those of another kind near a fight (Caleb, 2026-11-07, OQ-35 (a)).

On the server (AggressiveBehavior, AggressiveHandler, Region): an aggressive monster picks a character within reach
of it whose combat level is at most twice its own, unless the character has spent TOLERANCE_TICKS in that map region
(64 by 64 tiles; the rl fork counts game ticks). Outside multi-combat areas it can't pick one that's "in combat",
swung at within the last 17 ticks (`Entity.inCombat`, the fork's combat-time). A site's aggressors are the aggressive
monsters spawned within SITE_REACH tiles of its tile, one per spawn (`site_aggressors`); the gathering sites' model
(rlscape.sim.aggression) and the fights' share them.

A fight's neighbours are its site's aggressors of another kind than the target (`site_neighbours`). While nothing
attacks the character, between kills (the overhead to the next monster, its pickups, a wait for a respawn), each
spawn of one whose level would pick the character engages at ENGAGE_PER_TICK until the region's tolerance runs out.
In single combat the character must kill it before attacking the next target, so each engagement is a kill of that
monster in the fight's plan: its time, damage, XP and drops, in place of target kills. The sim's fight samples them
(rlscape.sim.combat); both rankers count their expected value per target kill (`with_neighbours`;
rlscape.combat.candidates and rlscape.combat.ranking). A site where an engaging neighbour can't be hurt by the plan, or
fails the danger filter, is no site for the fight while aggression lasts. From a usable safespot none reaches the
character (its threats count every kind), so they don't apply there.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from functools import cache

from rlscape.combat.rates import TICKS_PER_HOUR, Rates
from rlscape.gamedata import server as gd

TOLERANCE_TICKS = 1000  # Region.TOLERANCE_TICKS (the fork counts game ticks): then its aggressive monsters leave it alone
SITE_REACH = 10  # tiles from a site's tile to an aggressor's spawn (Draynor's wizards spawn 8 from the willows)
REGION_TILES = 64  # a map region's side (Location.getRegionId: x >> 6, y >> 6)
# Engagements a tick per neighbour spawn, while the character is exposed (between kills) before tolerance. Fitted to
# the server at the animated spades' possessed pickaxe (2026-11-07, band 61 magic, 7 runs: 3.7 pickaxe kills a
# 1,500-tick run; the sim's fight matches at 0.045), and measured there directly: 29 engagements in 622 ticks with
# nothing attacking the character, 0.047 (m002-magic-safespots-neighbours)
ENGAGE_PER_TICK = 0.045


@dataclass(frozen=True)
class Aggressor:
    npc: gd.Npc
    level: int  # the combat level the server compares with the character's (the NPC definition's)


@cache
def site_aggressors(tile: tuple[int, int, int]) -> tuple[Aggressor, ...]:
    """The aggressive monsters spawned within SITE_REACH tiles of a site's tile, one per spawn. Only attackable ones
    with a combat level: the config marks some others aggressive (a Draynor banker), which never pick anyone."""
    npcs, definitions, out = gd.npcs(), gd.npc_definitions(), []
    for npc_id, spawns in gd.spawns().items():
        npc, definition = npcs.get(npc_id), definitions.get(npc_id)
        if npc is None or not npc.aggressive or definition is None or not definition.attackable \
                or definition.combat_level <= 0:
            continue
        for x, y, z in spawns:
            if z == tile[2] and max(abs(x - tile[0]), abs(y - tile[1])) <= SITE_REACH:
                out.append(Aggressor(npc, definitions[npc_id].combat_level))
    return tuple(out)


@dataclass(frozen=True)
class Neighbour:
    npc: gd.Npc
    level: int
    spawns: int  # its spawns within SITE_REACH


@cache
def site_neighbours(target: int, tile: tuple[int, int, int]) -> tuple[Neighbour, ...]:
    """A fight's neighbours at a site: its aggressors of another kind (NPC id) than the target, by id."""
    counts = Counter(a.npc.id for a in site_aggressors(tile) if a.npc.id != target)
    by_id = {a.npc.id: a for a in site_aggressors(tile)}
    return tuple(Neighbour(by_id[i].npc, by_id[i].level, n) for i, n in sorted(counts.items()))


def engaging(neighbours: tuple[Neighbour, ...], combat_level: int) -> tuple[Neighbour, ...]:
    """The neighbours that would pick a character of `combat_level` (at most twice theirs)."""
    return tuple(n for n in neighbours if combat_level <= 2 * n.level)


def region_of(tile: tuple[int, int, int]) -> tuple[int, int]:
    return tile[0] // REGION_TILES, tile[1] // REGION_TILES


def aggression_ticks(site: tuple[int, int, int], location: tuple[int, int, int], tolerance_left: float) -> float:
    """The ticks of a fight at `site` before its region's tolerance runs out: a whole TOLERANCE_TICKS if the walk there
    enters another region (tolerance starts again), else what's left of the character's (`tolerance_left`)."""
    if region_of(site) != region_of(location) or site[2] != location[2]:
        return float(TOLERANCE_TICKS)
    return max(float(tolerance_left), 0.0)


def exposed_per_kill(between_kills: float, ticks_per_kill: float, slowdown: float) -> float:
    """A target kill's ticks with nothing attacking the character: `between_kills` (the overhead to the next monster
    and the pickups) and the wait for a respawn where the site runs short (ticks_per_kill times slowdown - 1)."""
    return between_kills + ticks_per_kill * (slowdown - 1.0)


@dataclass(frozen=True)
class NeighbourKill:
    """One neighbour kill in the fight's plan: its ticks (with the overhead and its pickups), XP, gp and damage."""

    ticks: float
    xp: dict[str, float]
    gp: float
    damage: float  # taken in it, poison and breath included
    poison: float
    breath: float
    variance: float  # of the damage taken


def neighbour_kill(rates: Rates, gp_per_kill: float, pickup_ticks: float) -> NeighbourKill:
    """A neighbour's kill from its own fighting rates (rlscape.combat.rates.combat_rates, gp aside) and loot."""
    per_kill = rates.ticks_per_kill / TICKS_PER_HOUR
    return NeighbourKill(rates.ticks_per_kill + pickup_ticks,
                         {skill: xp * per_kill for skill, xp in rates.xp_per_hour.items()}, gp_per_kill,
                         rates.damage_taken_per_kill, rates.poison_per_kill, rates.breath_per_kill,
                         rates.damage_taken_variance_per_kill)


def with_neighbours(rates: Rates, engagements: list[tuple[float, NeighbourKill]]) -> Rates:
    """The rates with each target kill's neighbour fights timed in: (expected engagements per target kill, the kill)
    for each neighbour. The target's hourly rates fall in proportion and the neighbours' are added; kills_per_hour
    stays the target's. The per-kill damage the danger filter reads stays the target's (each neighbour passes it on its
    own). The fast ranker (rlscape.combat.ranking) does the same arithmetic on its arrays."""
    extra = sum(e * k.ticks for e, k in engagements)
    if extra <= 0:
        return rates
    ticks = rates.ticks_per_kill + extra
    scale, hourly = rates.ticks_per_kill / ticks, TICKS_PER_HOUR / ticks
    xp = {skill: value * scale for skill, value in rates.xp_per_hour.items()}
    for e, k in engagements:
        for skill, value in k.xp.items():
            xp[skill] = xp.get(skill, 0.0) + e * value * hourly
    added = lambda field: sum(e * getattr(k, field) for e, k in engagements) * hourly  # noqa: E731
    return replace(rates, kills_per_hour=rates.kills_per_hour * scale, xp_per_hour=xp,
                   gp_per_hour=rates.gp_per_hour * scale + added("gp"), ticks_per_kill=ticks,
                   damage_taken_per_hour=rates.damage_taken_per_hour * scale + added("damage"),
                   damage_taken_variance_per_hour=rates.damage_taken_variance_per_hour * scale + added("variance"),
                   poison_per_hour=rates.poison_per_hour * scale + added("poison"),
                   breath_per_hour=rates.breath_per_hour * scale + added("breath"))
