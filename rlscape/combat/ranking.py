"""A fast candidate ranker with the same results as candidates.select_candidates (the reference).

The ranking runs every decision, because the combat slots are part of the action mask and the observation, so it
has to be cheap. What makes it slow in the reference is recomputing, for every monster, things that rarely change:
its expected loot (per loot mode) and its fighting rates (per fighter and plan). Here those are cached, and what does
change from step to step is vectorised over every site of every monster with numpy:
- walking time from the character to each site, and the share of the option left for fighting after bank trips,
  capped by how long the ammunition or runes last;
- the access table and Slayer levels (cached per progress), the special-damage gear check (cached per shield), and
  the retreat-aware filter (per HP and food);
- the best site per monster, the best plan per monster, one entry per monster name, then the k best by XP/hr and
  the k best by gp/hr.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from rlscape.combat.access import Progress, can_reach, meets_slayer_level
from rlscape.combat.candidates import (
    DRAGONFIRE_NPCS,
    TIE_DECIMALS,
    Candidate,
    Character,
    PoolEntry,
    has_special_damage_protection,
    loot_per_kill,
    loot_rule,
    pickups_per_kill,
)
from rlscape.combat.rates import (EAT_BELOW_FRACTION, ESCAPE_ATTACKS, OVERHEAD_TICKS_PER_KILL, PICKUP_TICKS, Fighter,
                                  Plan, Rates, combat_rates, site_slowdown, with_pickups)
from rlscape.travel import UNDERGROUND_Y_OFFSET, Destinations


@dataclass(frozen=True)
class _PlanRates:
    """Per-monster arrays for one fighter and plan, NaN where the plan can't hurt the monster."""

    kills_per_hour: np.ndarray
    xp_per_hour: np.ndarray  # total XP/hr
    ticks_per_kill: np.ndarray
    damage_per_kill: np.ndarray
    poison_per_kill: np.ndarray
    breath_per_kill: np.ndarray
    damage_sd_per_kill: np.ndarray
    npc_max_hit: np.ndarray
    attacks_per_kill: np.ndarray
    rates: tuple  # the scalar Rates (or None) per monster, to build the chosen Candidates


class CandidateRanker:
    def __init__(self, pool: tuple[PoolEntry, ...]):
        self.pool = pool
        names = [e.npc.name for e in pool]
        self.name_codes = np.unique(names, return_inverse=True)[1]
        site_entry, tiles, trips, supply = [], [], [], []
        for i, entry in enumerate(pool):
            for site in entry.sites:
                site_entry.append(i)
                tiles.append(site.spawn)
                trips.append(site.bank_trip_ticks)
                supply.append(site.spawns)
        self.site_entry = np.array(site_entry)
        self.site_spawns = np.array(supply, dtype=float)
        self.respawn = np.array([e.npc.respawn for e in pool], dtype=float)
        tiles = np.array(tiles)
        self.site_x, self.site_plane = tiles[:, 0], tiles[:, 2]
        self.site_under = tiles[:, 1] >= UNDERGROUND_Y_OFFSET
        self.site_y = np.where(self.site_under, tiles[:, 1] - UNDERGROUND_Y_OFFSET, tiles[:, 1])
        self.site_trip = np.array(trips, dtype=float)
        self.destinations = Destinations([tuple(int(v) for v in t) for t in tiles])
        self.segment_starts = np.flatnonzero(np.r_[True, np.diff(self.site_entry) != 0])
        self.dragonfire = np.array([e.npc.id in DRAGONFIRE_NPCS for e in pool])

    # --- cached, slowly changing inputs ------------------------------------------------------------------------------

    @lru_cache(maxsize=256)
    def _plan_rates(self, fighter: Fighter, plan: Plan) -> _PlanRates:
        return self._columns(tuple(combat_rates(fighter, plan, e.npc, 0.0) for e in self.pool))

    @lru_cache(maxsize=64)
    def _shielded_rates(self, fighter: Fighter, shielded: Fighter, plan: Plan) -> _PlanRates:
        """_plan_rates for `fighter`, but the dragonfire monsters' for `shielded`, the fighter wearing its anti-dragon
        shield (as the fight would against them)."""
        base = self._plan_rates(fighter, plan).rates
        return self._columns(tuple(combat_rates(shielded, plan, e.npc, 0.0) if dragon else r
                                   for e, dragon, r in zip(self.pool, self.dragonfire, base)))

    @staticmethod
    def _columns(rates: tuple) -> _PlanRates:
        nan = float("nan")
        col = lambda f: np.array([f(r) if r is not None else nan for r in rates])  # noqa: E731
        return _PlanRates(col(lambda r: r.kills_per_hour), col(lambda r: sum(r.xp_per_hour.values())),
                          col(lambda r: r.ticks_per_kill), col(lambda r: r.damage_taken_per_kill),
                          col(lambda r: r.poison_per_kill), col(lambda r: r.breath_per_kill),
                          col(lambda r: np.sqrt(r.damage_taken_variance_per_kill)), col(lambda r: r.npc_max_hit),
                          col(lambda r: r.attacks_per_kill), rates)

    @lru_cache(maxsize=64)
    def _loot(self, mode: str, vocabulary: frozenset[int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Per monster: gp, new inventory slots and pickups per kill, as the loot rule keeps its drops."""
        rule = loot_rule(mode, vocabulary)
        stats = [loot_per_kill(e.drops, rule) for e in self.pool]
        return (np.array([g for g, _ in stats]), np.array([s for _, s in stats]),
                np.array([pickups_per_kill(e.drops, rule) for e in self.pool]))

    @lru_cache(maxsize=1024)
    def _access(self, progress: Progress) -> tuple[np.ndarray, np.ndarray]:
        """(monster passes its Slayer level, site reachable)."""
        slayer = np.array([meets_slayer_level(e.npc.id, progress) for e in self.pool])
        reach = np.array([can_reach(self.pool[i].npc.name, (int(x), int(y), int(z)), progress)
                          for i, x, y, z in zip(self.site_entry, self.site_x,
                                                np.where(self.site_under, self.site_y + UNDERGROUND_Y_OFFSET,
                                                         self.site_y), self.site_plane)])
        return slayer, reach

    @lru_cache(maxsize=64)
    def _protected(self, shield_id: int | None) -> np.ndarray:
        return np.array([has_special_damage_protection(e.npc, shield_id) for e in self.pool])

    def rates(self, fighter: Fighter, plan: Plan) -> tuple[Rates | None, ...]:
        """The raw fighting rates per pool entry for one fighter and plan (None where the plan can't hurt the monster),
        from the same cache the ranking uses."""
        return self._plan_rates(fighter, plan).rates

    # --- per decision ------------------------------------------------------------------------------------------------

    def _travel(self, location: tuple[int, int, int], home: bool) -> np.ndarray:
        """rlscape.travel.travel_ticks from `location` to every site."""
        return self.destinations.ticks_from(location, home)

    def _best_site(self, share: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Per monster: the best site's share and its index (the first best, as max() picks)."""
        best = np.maximum.reduceat(share, self.segment_starts)
        is_best = share == best[self.site_entry]
        first = np.full(len(self.pool), -1)
        hits = np.flatnonzero(is_best)
        first[self.site_entry[hits[::-1]]] = hits[::-1]  # reversed, so the first index per monster wins
        return best, first

    def select(self, plans: dict[str, tuple[Fighter, list[Plan]]], character: Character, duration_ticks: float,
               k: int = 3, vocabulary: frozenset[int] = frozenset(),
               dragonfire: dict[str, Fighter] | None = None) -> dict[str, list[Candidate]]:
        """candidates.select_candidates, with the same results, fast (`dragonfire` as there)."""
        gp_per_kill, slots_per_kill, pickups = self._loot(character.loot_mode, vocabulary)
        slayer, reach = self._access(character.progress)
        protected = self._protected(character.shield_id)
        travel = self._travel(character.location, character.home_teleport)
        can_go = self.destinations.reachable(character.reach)  # the character's ways there now
        walk_share = np.maximum(duration_ticks - travel, 0.0) / duration_ticks
        retreat = EAT_BELOW_FRACTION * character.max_hp
        budget = max(character.current_hp - retreat, 0.0) + character.food_healing
        out: dict[str, list[Candidate]] = {}
        n = len(self.pool)
        for combat_class, (fighter, class_plans) in plans.items():
            best = {key: np.full(n, -np.inf) for key in ("xp", "gp")}
            pick = {key: np.full(n, -1) for key in ("xp", "gp")}  # plan index of the best value
            site_of = {key: np.zeros(n, dtype=int) for key in ("xp", "gp")}
            share_of = {key: np.zeros(n) for key in ("xp", "gp")}
            first_valid = np.full(n, n)  # the reference's tie order: names in the order first seen valid in the pool
            shielded = (dragonfire or {}).get(combat_class)
            if shielded is None:
                plan_rates, guarded = [self._plan_rates(fighter, plan) for plan in class_plans], protected
            else:
                plan_rates = [self._shielded_rates(fighter, shielded, plan) for plan in class_plans]
                guarded = protected | self.dragonfire
            extra = PICKUP_TICKS[combat_class] * pickups  # each kill's pickups (rates.with_pickups)
            for p, r in enumerate(plan_rates):
                valid = (slayer & guarded & ~np.isnan(r.kills_per_hour)
                         & (r.npc_max_hit * ESCAPE_ATTACKS < retreat)
                         & (r.damage_per_kill - character.poison_cover * r.poison_per_kill
                            - character.antifire_cover * r.breath_per_kill  # less what antipoison and antifire keep off
                            + 2.0 * r.damage_sd_per_kill <= budget))
                with np.errstate(divide="ignore", invalid="ignore"):
                    ticks = r.ticks_per_kill + extra  # a kill with its pickups, as rates.with_pickups has it
                    scale = r.ticks_per_kill / ticks
                    fight_ticks = np.where(slots_per_kill > 0, character.free_slots / slots_per_kill * ticks, np.inf)
                    # where a site runs out of monsters, kills come slower (site_slowdown), as in the reference
                    slow = site_slowdown(ticks[self.site_entry], self.respawn[self.site_entry], self.site_spawns,
                                         OVERHEAD_TICKS_PER_KILL[combat_class] + extra[self.site_entry])
                    site_fight = fight_ticks[self.site_entry] * slow
                    fighting = np.where(np.isinf(site_fight), 1.0,
                                        np.where(site_fight > 0, site_fight / (site_fight + self.site_trip), 0.0))
                    ammo_share = character.attacks_held / r.attacks_per_kill * ticks / duration_ticks
                    share = np.where(reach & can_go & valid[self.site_entry],
                                     np.minimum(fighting * walk_share, ammo_share[self.site_entry] * slow) / slow,
                                     -np.inf)
                    site_share, site_index = self._best_site(share)
                    ok = valid & (site_share > -np.inf)
                    values = {"xp": np.where(ok, np.round(r.xp_per_hour * scale * site_share, TIE_DECIMALS), -np.inf),
                              "gp": np.where(ok, np.round(r.kills_per_hour * gp_per_kill * scale * site_share,
                                                          TIE_DECIMALS), -np.inf)}
                first_valid = np.where(ok & (first_valid == n), np.arange(n), first_valid)
                for key, v in values.items():
                    better = ok & (v > best[key])
                    best[key][better], pick[key][better] = v[better], p
                    site_of[key][better], share_of[key][better] = site_index[better], site_share[better]
            winners = {}
            for key in ("xp", "gp"):
                winners[key] = self._per_name(best[key], first_valid)
            xp_slots = winners["xp"][:k]
            taken = set(self.name_codes[xp_slots])
            gp_slots = [i for i in winners["gp"] if self.name_codes[i] not in taken][:k]
            out[combat_class] = (
                [self._candidate(i, class_plans[pick["xp"][i]], plan_rates[pick["xp"][i]], site_of["xp"][i],
                                 share_of["xp"][i], travel, gp_per_kill, pickups) for i in xp_slots]
                + [self._candidate(i, class_plans[pick["gp"][i]], plan_rates[pick["gp"][i]], site_of["gp"][i],
                                   share_of["gp"][i], travel, gp_per_kill, pickups) for i in gp_slots])
        return out

    def _per_name(self, values: np.ndarray, first_valid: np.ndarray) -> np.ndarray:
        """The best monster per name (the first of equals in pool order), sorted best first; ties go to the name first
        seen valid in the pool, as in the reference."""
        order = np.lexsort((np.arange(len(values)), -values, self.name_codes))
        is_first = np.r_[True, self.name_codes[order][1:] != self.name_codes[order][:-1]]
        winners = order[is_first]
        winners = winners[values[winners] > -np.inf]
        name_first = np.full(self.name_codes.max() + 1, len(values))
        np.minimum.at(name_first, self.name_codes, first_valid)
        return winners[np.lexsort((name_first[self.name_codes[winners]], -values[winners]))]

    def _candidate(self, i: int, plan: Plan, rates: _PlanRates, site_index: int, share: float, travel: np.ndarray,
                   gp_per_kill: np.ndarray, pickups: np.ndarray) -> Candidate:
        entry, fight = self.pool[i], rates.rates[i]
        r = with_pickups(fight, float(pickups[i]), plan.combat_class)
        scale = fight.ticks_per_kill / r.ticks_per_kill
        site = entry.sites[int(site_index - self.segment_starts[i])]
        return Candidate(entry, plan, site, r, r.kills_per_hour * share,
                         {skill: xp * share for skill, xp in r.xp_per_hour.items()},
                         fight.kills_per_hour * gp_per_kill[i] * scale * share, float(travel[site_index]))
