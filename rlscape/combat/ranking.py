"""A fast candidate ranker with the same results as candidates.select_candidates (the reference).

The ranking runs every decision, because the combat slots are part of the action mask and the observation, so it
has to be cheap. What makes it slow in the reference is recomputing, for every monster, things that rarely change:
its expected loot (per loot mode) and its fighting rates (per fighter and plan). Here those are cached, the fighting
rates computed for every monster at once (rlscape.combat.vector_rates, the scalar model's to the last bit; OQ-7 (a)),
and what does change from step to step is vectorised over every site of every monster with numpy:
- walking time from the character to each site, and the share of the option left for fighting after bank trips,
  capped by how long the ammunition or runes last;
- the access table (cached per progress), the special-damage gear check (cached per shield), and
  the retreat-aware filter (per HP and food);
- the best site per monster, the best plan per monster, one entry per monster name, then the k best by XP/hr and
  the k best by gp/hr.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from rlscape.combat.access import Progress, can_reach
from rlscape.combat.candidates import (
    ANTI_DRAGON_SHIELD,
    DRAGONFIRE_NPCS,
    SLAYER_GEAR_NPCS,
    TIE_DECIMALS,
    UNKILLABLE_NPCS,
    Candidate,
    Character,
    PoolEntry,
    has_special_damage_protection,
    special_damage_shields,
    loot_per_kill,
    loot_rule,
    pickups_per_kill,
)
from rlscape.combat import neighbours as nb
from rlscape.combat import safespots as ss
from rlscape.combat.candidates import Neighbours, neighbour_kills, site_rates
from rlscape.combat.rates import (EAT_BELOW_FRACTION, ESCAPE_ATTACKS, OVERHEAD_TICKS_PER_KILL, PICKUP_TICKS, REGEN_TICKS,
                                  TICKS_PER_HOUR, Fighter, Plan, Rates, combat_rates, site_slowdown)
from rlscape.combat.vector_rates import NpcArrays, RateColumns, vector_rates
from rlscape.gamedata import server as gd
from rlscape.travel import UNDERGROUND_Y_OFFSET, Destinations


class _LazyRates:
    """The scalar Rates (rates.combat_rates, or None) per monster, computed when one is asked for: the ranker reads
    its vectorised columns, and only the candidates it picks need these."""

    def __init__(self, npcs: tuple, plan: Plan, fighters: tuple[Fighter, ...]):
        self.npcs, self.plan, self.fighters, self._done = npcs, plan, fighters, {}

    def __getitem__(self, i: int) -> Rates | None:
        i = int(i)
        if i not in self._done:
            self._done[i] = combat_rates(self.fighters[i], self.plan, self.npcs[i], 0.0)
        return self._done[i]

    def __len__(self) -> int:
        return len(self.npcs)


@dataclass(frozen=True)
class _PlanRates:
    """Per-monster arrays for one fighter and plan, NaN where the plan can't hurt the monster."""

    kills_per_hour: np.ndarray
    xp_per_hour: np.ndarray  # total XP/hr
    ticks_per_kill: np.ndarray
    damage_per_kill: np.ndarray
    damage_per_hour: np.ndarray
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
        # each site's safespot for each range (rlscape.combat.safespots): usable, the walk to the arrows and back,
        # whether there's a way there, and the monsters it holds against
        self.spots = {}
        for tiles_range, plan in ((ss.RANGE_TILES, Plan("ranged", "accurate")),
                                  (ss.LONGRANGE_TILES, Plan("ranged", "longrange")),
                                  (ss.MAGIC_TILES, Plan("magic", "wind_strike"))):  # (any spell: the range is 10)
            found = [ss.safespot(e.npc.id, s.spawn, plan) for e in pool for s in e.sites]
            self.spots[tiles_range] = (np.array([s is not None for s in found], dtype=bool),
                                       np.array([ss.trip_ticks(s) for s in found], dtype=float),
                                       np.array([s is not None and s.walk is not None for s in found], dtype=bool),
                                       np.array([s.held if s is not None else 0 for s in found], dtype=float),
                                       np.array([s is not None and s.pickup_threats > 0 for s in found], dtype=bool))
        # per monster: the shields that guard against its special damage (candidates.special_damage_shields)
        self.special_shields = [special_damage_shields(e.npc) for e in pool]
        # each site's neighbours (rlscape.combat.neighbours), one row per site and neighbour kind: the site, the
        # neighbour (an index into nb_npcs), its level and spawns; and each site's map region
        rows = [(k, n) for k, (e, s) in enumerate((e, s) for e in pool for s in e.sites)
                for n in nb.site_neighbours(e.npc.id, s.spawn)]
        self.nb_npcs = tuple(sorted({n.npc.id: n.npc for _, n in rows}.values(), key=lambda npc: npc.id))
        index = self.nb_position = {npc.id: i for i, npc in enumerate(self.nb_npcs)}
        self.nb_site = np.array([k for k, _ in rows], dtype=int)
        self.nb_index = np.array([index[n.npc.id] for _, n in rows], dtype=int)
        self.nb_level = np.array([n.level for _, n in rows], dtype=float)
        self.nb_spawns = np.array([n.spawns for _, n in rows], dtype=float)
        self.site_region = (tiles[:, 0] // nb.REGION_TILES, tiles[:, 1] // nb.REGION_TILES, tiles[:, 2])
        # the monsters' stats as arrays, for the vectorised rates
        self.pool_arrays = NpcArrays([e.npc for e in pool])
        self.nb_arrays = NpcArrays(self.nb_npcs)

    # --- cached, slowly changing inputs ------------------------------------------------------------------------------

    @lru_cache(maxsize=256)
    def _plan_rates(self, fighter: Fighter, plan: Plan) -> _PlanRates:
        """The pool's rates for a fighter and plan, vectorised (rlscape.combat.vector_rates, the scalar model's to the
        last bit; Caleb, OQ-7 (a)); the scalar Rates only for the monsters asked for."""
        return self._columns(vector_rates(fighter, plan, self.pool_arrays),
                             _LazyRates(tuple(e.npc for e in self.pool), plan, (fighter,) * len(self.pool)))

    @lru_cache(maxsize=64)
    def _shielded_rates(self, fighter: Fighter, shielded: Fighter, plan: Plan) -> _PlanRates:
        """_plan_rates for `fighter`, but the dragonfire monsters' for `shielded`, the fighter wearing its anti-dragon
        shield (as the fight would against them)."""
        base, armed = vector_rates(fighter, plan, self.pool_arrays), vector_rates(shielded, plan, self.pool_arrays)
        mixed = RateColumns(**{name: np.where(self.dragonfire, getattr(armed, name), getattr(base, name))
                               for name in RateColumns.__dataclass_fields__})
        fighters = tuple(shielded if dragon else fighter for dragon in self.dragonfire)
        return self._columns(mixed, _LazyRates(tuple(e.npc for e in self.pool), plan, fighters))

    @staticmethod
    def _columns(c: RateColumns, rates) -> _PlanRates:
        return _PlanRates(c.kills_per_hour, c.xp_per_hour, c.ticks_per_kill, c.damage_per_kill, c.damage_per_hour,
                          c.poison_per_kill, c.breath_per_kill, c.damage_sd_per_kill, c.npc_max_hit,
                          c.attacks_per_kill, rates)

    @lru_cache(maxsize=64)
    def _loot(self, mode: str, vocabulary: frozenset[int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Per monster: gp, new inventory slots and pickups per kill, as the loot rule keeps its drops."""
        rule = loot_rule(mode, vocabulary)
        stats = [loot_per_kill(e.drops, rule) for e in self.pool]
        return (np.array([g for g, _ in stats]), np.array([s for _, s in stats]),
                np.array([pickups_per_kill(e.drops, rule) for e in self.pool]))

    @lru_cache(maxsize=256)
    def _neighbour_rates(self, fighter: Fighter, plan: Plan) -> _PlanRates:
        """_plan_rates for the neighbours (nb_npcs)."""
        return self._columns(vector_rates(fighter, plan, self.nb_arrays),
                             _LazyRates(self.nb_npcs, plan, (fighter,) * len(self.nb_npcs)))

    @lru_cache(maxsize=64)
    def _neighbour_loot(self, mode: str, vocabulary: frozenset[int]) -> tuple[np.ndarray, np.ndarray]:
        """Per neighbour: gp and pickups per kill, as the loot rule keeps its drops."""
        rule, tables = loot_rule(mode, vocabulary), gd.drop_tables()
        return (np.array([loot_per_kill(tables.get(npc.id), rule)[0] for npc in self.nb_npcs]),
                np.array([pickups_per_kill(tables.get(npc.id), rule) for npc in self.nb_npcs]))

    @lru_cache(maxsize=64)
    def _neighbour_fightable(self, shield_id: int | None) -> np.ndarray:
        """Per neighbour: the gear guards its special damage, and it's no monster the reference rules out by kind."""
        return np.array([has_special_damage_protection(npc, shield_id) and npc.name not in SLAYER_GEAR_NPCS
                         and npc.id not in UNKILLABLE_NPCS for npc in self.nb_npcs], dtype=bool)

    def _neighbour_kills(self, fighter: Fighter, plan: Plan, shield_id: int | None, gp: np.ndarray,
                         pickup_ticks: np.ndarray, retreat: float, budget: float,
                         character: Character) -> tuple[np.ndarray, ...]:
        """Per neighbour, its kill in the plan (candidates.neighbour_kills): usable, ticks, XP, gp, damage."""
        r = self._neighbour_rates(fighter, plan)
        with np.errstate(invalid="ignore"):
            harmless = ((r.npc_max_hit * ESCAPE_ATTACKS < retreat)
                        & (r.damage_per_kill - character.poison_cover * r.poison_per_kill
                           - character.antifire_cover * r.breath_per_kill + 2.0 * r.damage_sd_per_kill <= budget))
        usable = ~np.isnan(r.kills_per_hour) & harmless & self._neighbour_fightable(shield_id)
        xp = r.xp_per_hour * (r.ticks_per_kill / TICKS_PER_HOUR)
        return usable, r.ticks_per_kill + pickup_ticks, xp, gp, r.damage_per_kill

    def _neighbour_load(self, kills: tuple[tuple[np.ndarray, ...], tuple[np.ndarray, ...] | None], exposed: np.ndarray,
                        share: np.ndarray, combat_level: int) -> tuple[np.ndarray, ...]:
        """Per site, the neighbour fights per target kill (nb.with_neighbours): their ticks, XP and gp, and whether
        an engaging one can't be fought (the site is none then). `kills` is the neighbours' kills for the fighter,
        and for its shielded self at dragonfire targets (or None)."""
        n = len(self.site_entry)
        rows = (combat_level <= 2 * self.nb_level) & (share[self.nb_site] > 0)
        site, index = self.nb_site[rows], self.nb_index[rows]
        plain, shielded = kills
        dragon = self.dragonfire[self.site_entry[site]] if shielded is not None else np.zeros(len(site), dtype=bool)
        pick = lambda j: np.where(dragon, shielded[j][index], plain[j][index]) if shielded is not None \
            else plain[j][index]  # noqa: E731
        usable = pick(0).astype(bool)
        engaged = share[site] * nb.ENGAGE_PER_TICK * self.nb_spawns[rows] * exposed[site]
        with np.errstate(invalid="ignore"):
            load = [np.bincount(site, weights=np.where(usable, engaged * pick(j), 0.0), minlength=n) for j in (1, 2, 3)]
        bad = np.bincount(site, weights=(~usable).astype(float), minlength=n) > 0
        return (*load, bad)

    @lru_cache(maxsize=1024)
    def _access(self, progress: Progress) -> np.ndarray:
        """Each site reachable (no Slayer levels: Caleb, OQ-32)."""
        reach = np.array([can_reach(self.pool[i].npc.name, (int(x), int(y), int(z)), progress)
                          for i, x, y, z in zip(self.site_entry, self.site_x,
                                                np.where(self.site_under, self.site_y + UNDERGROUND_Y_OFFSET,
                                                         self.site_y), self.site_plane)])
        return reach

    @lru_cache(maxsize=64)
    def _shields_ok(self, shields: frozenset[int]) -> np.ndarray:
        """Per monster: no special damage, or a shield against it among `shields`."""
        return np.array([not s or bool(s & shields) for s in self.special_shields])

    @lru_cache(maxsize=64)
    def _protected(self, shield_id: int | None) -> np.ndarray:
        return np.array([has_special_damage_protection(e.npc, shield_id) for e in self.pool])

    def rates(self, fighter: Fighter, plan: Plan) -> tuple[Rates | None, ...]:
        """The raw fighting rates per pool entry for one fighter and plan (None where the plan can't hurt the monster),
        from the same cache the ranking uses."""
        return self._plan_rates(fighter, plan).rates

    # --- per decision ------------------------------------------------------------------------------------------------

    @lru_cache(maxsize=8)
    def _travel(self, location: tuple[int, int, int], home: bool) -> np.ndarray:
        """rlscape.travel.travel_ticks from `location` to every site (cached: each class's ranking asks the same)."""
        ticks = self.destinations.ticks_from(location, home)
        ticks.setflags(write=False)  # shared by the cache
        return ticks

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
        reach = self._access(character.progress)
        protected = self._protected(character.shield_id)
        travel = self._travel(character.location, character.home_teleport)
        can_go = self.destinations.reachable(character.reach)  # the character's ways there now
        walk_share = np.maximum(duration_ticks - travel, 0.0) / duration_ticks
        retreat = EAT_BELOW_FRACTION * character.max_hp
        budget = max(character.current_hp - retreat, 0.0) + character.food_healing
        margin = ss.hp_margin(character.current_hp, character.max_hp)
        nb_loot_gp, nb_loot_pickups = self._neighbour_loot(character.loot_mode, vocabulary)
        nb_pickup_ticks = PICKUP_TICKS * nb_loot_pickups  # as neighbour_kills times them
        # per site, the share of the option before aggression runs out there (nb.aggression_ticks)
        here = (character.location[0] // nb.REGION_TILES, character.location[1] // nb.REGION_TILES,
                character.location[2])
        same = (self.site_region[0] == here[0]) & (self.site_region[1] == here[1]) & (self.site_region[2] == here[2])
        aggression = np.minimum(np.where(same, max(float(character.tolerance_left), 0.0), float(nb.TOLERANCE_TICKS))
                                / duration_ticks, 1.0)
        rule = loot_rule(character.loot_mode, vocabulary)
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
            overhead = OVERHEAD_TICKS_PER_KILL[combat_class]
            se = self.site_entry
            ranged = combat_class == "ranged"
            distance = ss.distance_class(Plan(combat_class, ""))  # ranged or magic: it can safespot (OQ-34)
            # the neighbours' kills per plan, for the fighter and, at dragonfire targets, its shielded self
            neighbour_kills_of = [
                (self._neighbour_kills(fighter, plan, character.shield_id, nb_loot_gp, nb_pickup_ticks, retreat,
                                       budget, character),
                 None if shielded is None else self._neighbour_kills(shielded, plan, ANTI_DRAGON_SHIELD, nb_loot_gp,
                                                                     nb_pickup_ticks, retreat, budget, character))
                for plan in class_plans]
            for p, r in enumerate(plan_rates):
                # a ranger or caster does without the special-damage gear from a safespot (site_rates)
                valid = (guarded | distance) & ~np.isnan(r.kills_per_hour)
                harmless = ((r.npc_max_hit * ESCAPE_ATTACKS < retreat)
                            & (r.damage_per_kill - character.poison_cover * r.poison_per_kill
                               - character.antifire_cover * r.breath_per_kill  # less what antipoison and antifire keep off
                               + 2.0 * r.damage_sd_per_kill <= budget))
                with np.errstate(divide="ignore", invalid="ignore"):
                    fighting_ticks = np.maximum(r.ticks_per_kill - overhead, 0.0)
                    items = pickups[se]  # each kill's pickups, and a ranger's arrow piles and walk (site_rates)
                    trip = np.zeros(len(se))
                    supply = self.site_spawns
                    harmless_at = harmless[se]
                    spotted = np.zeros(len(se), dtype=bool)
                    if distance:
                        ok, walk_ticks, walkable, held, guarded_piles = self.spots[ss.style_range(class_plans[p])]
                        # guarded arrows are fetched late with the shield worn: one carried (Caleb, OQ-33)
                        shielded_trip = self._shields_ok(character.shields_carried)[se]
                        ok = ok & (~guarded_piles | shielded_trip | guarded[se])  # (worn: a crossbow's)
                        # it would need food (safespots.needs_safespot), or the gear can't guard it; NaN: False
                        needs = ((r.damage_per_hour * duration_ticks / TICKS_PER_HOUR - duration_ticks / REGEN_TICKS
                                  > margin) | ~guarded)[se]
                        spotted = needs & ok
                        if ranged and character.arrow_piles:  # casting leaves no piles
                            piles = np.maximum(1.0, np.ceil(fighting_ticks / ss.PILE_PRIVATE_TICKS))[se]
                            items = items + np.where(spotted & ~walkable, 0.0, piles)
                        trip = np.where(spotted & (items > 0), walk_ticks, 0.0)
                        supply = np.where(spotted, np.minimum(self.site_spawns, held), self.site_spawns)
                        harmless_at = np.where(needs, spotted, harmless_at)  # from a safespot it does no harm
                    extra = PICKUP_TICKS * items + trip
                    ticks = r.ticks_per_kill[se] + extra  # a kill with its pickups, as rates.with_pickups has it
                    # where a site runs out of monsters, kills come slower (site_slowdown), as in the reference
                    slow = site_slowdown(ticks, self.respawn[se], supply, overhead + extra)
                    # away from a safespot, the neighbours' fights per kill, while aggression lasts (site_rates)
                    exposed = nb.exposed_per_kill(overhead + extra, ticks, slow)
                    nb_ticks, nb_xp, nb_gp, nb_bad = self._neighbour_load(neighbour_kills_of[p], exposed,
                                                                          np.where(spotted, 0.0, aggression),
                                                                          character.combat_level)
                    nb_ticks, nb_xp, nb_gp = (np.where(nb_ticks > 0, v, 0.0) for v in (nb_ticks, nb_xp, nb_gp))
                    ticks = ticks + nb_ticks
                    slow = np.where(nb_ticks > 0, site_slowdown(ticks, self.respawn[se], supply,
                                                                overhead + extra + nb_ticks), slow)
                    scale = r.ticks_per_kill[se] / ticks
                    hourly = TICKS_PER_HOUR / ticks
                    fight_ticks = np.where(slots_per_kill[se] > 0, character.free_slots / slots_per_kill[se] * ticks,
                                           np.inf)
                    site_fight = fight_ticks * slow
                    fighting = np.where(np.isinf(site_fight), 1.0,
                                        np.where(site_fight > 0, site_fight / (site_fight + self.site_trip), 0.0))
                    ammo_share = character.attacks_held / r.attacks_per_kill[se] * ticks / duration_ticks
                    share = np.where(reach & can_go & valid[se] & harmless_at & ~nb_bad,
                                     np.minimum(fighting * walk_share, ammo_share * slow) / slow, -np.inf)
                    kills = r.kills_per_hour[se] * scale  # as with_pickups and with_neighbours scale them
                    # the site where it's killed fastest over the option, as the reference picks
                    _, site_index = self._best_site(np.where(share > -np.inf, np.round(kills * share, TIE_DECIMALS),
                                                             -np.inf))
                    at = np.maximum(site_index, 0)
                    site_share = np.where(site_index >= 0, share[at], -np.inf)
                    ok = valid & (site_share > -np.inf)
                    xp_at = r.xp_per_hour[se] * scale + nb_xp * hourly  # per site, the neighbours' added
                    gp_at = r.kills_per_hour[se] * gp_per_kill[se] * scale + nb_gp * hourly
                    values = {"xp": np.where(ok, np.round(xp_at[at] * site_share, TIE_DECIMALS), -np.inf),
                              "gp": np.where(ok, np.round(gp_at[at] * site_share, TIE_DECIMALS), -np.inf)}
                first_valid = np.where(ok & (first_valid == n), np.arange(n), first_valid)
                for key, v in values.items():
                    better = ok & (v > best[key])
                    best[key][better], pick[key][better] = v[better], p
                    site_of[key][better], share_of[key][better] = at[better], site_share[better]
            winners = {}
            for key in ("xp", "gp"):
                winners[key] = self._per_name(best[key], first_valid)
            xp_slots = winners["xp"][:k]
            taken = set(self.name_codes[xp_slots])
            gp_slots = [i for i in winners["gp"] if self.name_codes[i] not in taken][:k]
            def neighbours(i: int, plan: Plan) -> Neighbours:
                """The reference's neighbours for the chosen candidate (candidates.evaluate), from the cached
                neighbour rates and loot."""
                dragon = shielded is not None and bool(self.dragonfire[i])
                armed, shield = (shielded, ANTI_DRAGON_SHIELD) if dragon else (fighter, character.shield_id)
                cached = self._neighbour_rates(armed, plan).rates
                return Neighbours(neighbour_kills(self.pool[i], armed, plan, character, rule, shield,
                                                  rates_of=lambda npc: cached[self.nb_position[npc.id]],
                                                  loot_of=lambda npc: (float(nb_loot_gp[self.nb_position[npc.id]]),
                                                                       float(nb_loot_pickups[self.nb_position[npc.id]]))),
                                  character.combat_level, character.location, character.tolerance_left,
                                  duration_ticks)

            out[combat_class] = [
                self._candidate(i, class_plans[pick[key][i]], plan_rates[pick[key][i]], site_of[key][i],
                                share_of[key][i], travel, gp_per_kill, pickups, character.arrow_piles, guarded,
                                margin, duration_ticks, character.shields_carried,
                                neighbours(i, class_plans[pick[key][i]]))
                for key, slots in (("xp", xp_slots), ("gp", gp_slots)) for i in slots]
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
                   gp_per_kill: np.ndarray, pickups: np.ndarray, arrow_piles: bool, protected: np.ndarray,
                   margin: float, duration: float, shields: frozenset[int], neighbours: Neighbours) -> Candidate:
        entry, fight = self.pool[i], rates.rates[i]
        site = entry.sites[int(site_index - self.segment_starts[i])]
        r, _ = site_rates(entry, plan, fight, site, float(pickups[i]), arrow_piles, bool(protected[i]), margin,
                          duration, shields, neighbours)
        scale = fight.ticks_per_kill / r.ticks_per_kill
        # the fight's rates were taken without gp, so r's gp is the neighbours' alone
        return Candidate(entry, plan, site, r, r.kills_per_hour * share,
                         {skill: xp * share for skill, xp in r.xp_per_hour.items()},
                         (fight.kills_per_hour * gp_per_kill[i] * scale + r.gp_per_hour) * share,
                         float(travel[site_index]))
