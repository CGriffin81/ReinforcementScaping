"""The combat-rate model (rlscape.combat.rates.combat_rates) over many monsters at once, with numpy (Caleb, 2026-11-08,
OQ-7 (a)): the fast ranker's columns for a fighter and plan in one pass, not one Python call per monster.

`combat_rates` stays the reference: every expression here is its own, in the same order, on arrays of the monsters'
stats (NpcArrays, built once per monster list), so the columns are the scalar model's (tests/test_vector_rates.py
checks every monster for many fighters and plans). Where the scalar model returns None (the monster is immune to the
class, or the plan deals nothing) the columns are NaN. Fighter-side quantities (attack rolls, max hits, defence rolls)
are scalars; the monster-side ones are arrays; landed_hits_to_kill comes from the scalar model's own cache, one call
per distinct hitpoints.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from rlscape.combat import formulas as f
from rlscape.combat.prayers import NO_FLICKS, boosted_share
from rlscape.combat.rates import (BREATH_CHANCE, DRAGONFIRE_NPCS, HP_XP_PER_DAMAGE, OVERHEAD_TICKS_PER_KILL,
                                  TICKS_PER_HOUR, Fighter, Plan, breath_max, landed_hits_to_kill, npc_max_hit,
                                  player_offence, poison_per_tick)
from rlscape.gamedata.server import CRUSH, MAGIC, MELEE_STRENGTH, RANGED, RANGED_STRENGTH, SLASH, STAB, Npc

STYLES = ("melee", "ranged", "magic")


class NpcArrays:
    """The stats of a list of monsters, as arrays, for vector_rates."""

    def __init__(self, npcs: Sequence[Npc]):
        self.npcs = tuple(npcs)
        n = len(self.npcs)
        bonuses = np.array([npc.bonuses for npc in self.npcs], dtype=np.int64).reshape(n, 15)
        level = lambda name: np.array([getattr(npc, name) for npc in self.npcs], dtype=np.int64)  # noqa: E731
        defence, magic = level("defence"), level("magic")
        self.hitpoints = level("hitpoints")
        self.attack_speed = level("attack_speed")
        self.protect_style = np.array([npc.protect_style or "" for npc in self.npcs])
        self.style = np.array([npc.combat_style for npc in self.npcs])
        # f.npc_defence_roll against each attack type a player swings with (their bonus index + 5)
        self.defence_roll = {i: (defence + 9) * (bonuses[:, i + 5] + 64) for i in (STAB, SLASH, CRUSH, RANGED)}
        self.defence_roll[MAGIC] = (magic + 9) * (bonuses[:, MAGIC + 5] + 64)
        # npc_offence's attack roll in the monster's own style, and its melee attack type
        self.melee_type = np.array([npc.melee_attack_type for npc in self.npcs], dtype=np.int64)
        attack, ranged = level("attack"), level("ranged")
        rows = np.arange(n)
        self.attack_roll = np.where(self.style == "melee", (attack + 9) * (bonuses[rows, self.melee_type] + 64),
                                    np.where(self.style == "ranged", (ranged + 9) * (bonuses[:, RANGED] + 64),
                                             (magic + 9) * (bonuses[:, MAGIC] + 64)))
        self.max_hit = np.array([npc_max_hit(npc) for npc in self.npcs], dtype=np.int64)  # unprotected
        self.poison_per_tick = np.array([poison_per_tick(npc) for npc in self.npcs])
        self.dragon = np.array([npc.id in DRAGONFIRE_NPCS for npc in self.npcs], dtype=bool)
        self.speeds = tuple(sorted(set(int(s) for s in self.attack_speed)))
        self.distinct_hitpoints = np.unique(self.hitpoints)


def _hit_chance(attack_roll, defence_roll):
    """f.hit_chance, on arrays."""
    attack_roll, defence_roll = np.asarray(attack_roll, dtype=float), np.asarray(defence_roll, dtype=float)
    return np.where(attack_roll > defence_roll, 1 - (defence_roll + 2) / (2 * (attack_roll + 1)),
                    attack_roll / (2 * (defence_roll + 1)))


def _python_sum(values: list[np.ndarray]):
    """Python's sum() of floats, element by element: since 3.12 it adds with Neumaier's compensation (CPython's
    builtin_sum), which the scalar model's sum(xp_per_hour.values()) gets, to the last bit."""
    total, compensation = 0.0, 0.0
    for x in values:
        t = total + x
        compensation = compensation + np.where(np.abs(total) >= np.abs(x), (total - t) + x, (x - t) + total)
        total = t
    return np.where((compensation != 0) & np.isfinite(compensation), total + compensation, total)


def _landed(arrays: NpcArrays, max_hit: int) -> np.ndarray:
    """landed_hits_to_kill(hitpoints, max_hit) per monster, from the scalar model's cache."""
    if max_hit <= 0:
        return np.zeros(len(arrays.npcs))
    values = {int(h): landed_hits_to_kill(int(h), max_hit) for h in arrays.distinct_hitpoints}
    return np.array([values[int(h)] for h in arrays.hitpoints])


@dataclass(frozen=True)
class RateColumns:
    """combat_rates' outputs the fast ranker reads, per monster (NaN where it returns None)."""

    kills_per_hour: np.ndarray
    xp_per_hour: np.ndarray  # total over the skills, as sum(xp_per_hour.values())
    ticks_per_kill: np.ndarray
    damage_per_kill: np.ndarray
    damage_per_hour: np.ndarray
    poison_per_kill: np.ndarray
    breath_per_kill: np.ndarray
    damage_sd_per_kill: np.ndarray
    npc_max_hit: np.ndarray
    attacks_per_kill: np.ndarray


def vector_rates(fighter: Fighter, plan: Plan, arrays: NpcArrays, overhead_ticks: float | None = None) -> RateColumns:
    """combat_rates(fighter, plan, npc, 0.0) for every monster in `arrays`, as columns."""
    if overhead_ticks is None:
        overhead_ticks = OVERHEAD_TICKS_PER_KILL[plan.combat_class]
    n = len(arrays.npcs)
    # player_offence: the fighter's side is the same for every monster; only the defence roll differs
    plain_rolls = _player_rolls(fighter, plan, boosted=False)
    boosted_rolls = _player_rolls(fighter, plan, boosted=True)
    plain_chance = _hit_chance(plain_rolls[0], arrays.defence_roll[plain_rolls[1]])
    boosted_chance = _hit_chance(boosted_rolls[0], arrays.defence_roll[boosted_rolls[1]])
    plain_max, boosted_max, speed = plain_rolls[2], boosted_rolls[2], plain_rolls[3]
    plain_mean = plain_chance * f.mean_uniform(plain_max)
    boosted_mean = boosted_chance * f.mean_uniform(boosted_max)
    by_speed = {s: boosted_share(int(speed), s) for s in arrays.speeds}
    share = np.array([by_speed[int(s)] for s in arrays.attack_speed])
    chance = share * boosted_chance + (1 - share) * plain_chance
    mean_damage = share * boosted_mean + (1 - share) * plain_mean
    valid = (arrays.protect_style != plan.combat_class) & ~(mean_damage / speed <= 0)
    # swings_to_kill: the damaging hits, each kind's weighted by its share of them
    p_boosted = np.where((share > 0) & (boosted_max > 0), share * boosted_chance * boosted_max / (boosted_max + 1), 0.0)
    p_plain = np.where((1 - share > 0) & (plain_max > 0),
                       (1 - share) * plain_chance * plain_max / (plain_max + 1), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        rate = 0 + p_boosted + p_plain
        swings = (0 + np.where(p_boosted > 0, p_boosted / rate * _landed(arrays, boosted_max), 0.0)
                  + np.where(p_plain > 0, p_plain / rate * _landed(arrays, plain_max), 0.0)) / rate
        ticks_fighting = speed * swings
        ticks_per_kill = ticks_fighting + overhead_ticks
        kills = TICKS_PER_HOUR / ticks_per_kill
        damage_dealt = kills * arrays.hitpoints
        # npc_offence
        npc_chance, npc_max = _npc_offence(fighter, plan, arrays)
        npc_mean = npc_chance * f.mean_uniform(npc_max)
        npc_variance = npc_chance * f.second_moment_uniform(npc_max) - npc_mean * npc_mean
        npc_attacks_per_kill = ticks_fighting / arrays.attack_speed
        npc_attacks_per_hour = kills * npc_attacks_per_kill
        melee_share = np.where(arrays.dragon, 1 - BREATH_CHANCE, 1.0)
        breath = np.where(arrays.dragon, BREATH_CHANCE * breath_max(False) / 2, 0.0)
        spell_xp = kills * ticks_fighting / speed * f.SPELLS[plan.style][1] if plan.combat_class == "magic" else 0.0
        _, _, _, _, xp_per_damage = player_offence(fighter, plan, arrays.npcs[0]) if n else (0, 0, 0, 0, {})
        values = []
        for skill, per_damage in xp_per_damage.items():  # the scalar model's dict, in its order
            value = per_damage * damage_dealt
            if skill == "magic" and plan.combat_class == "magic":
                value = value + spell_xp
            values.append(value)
        xp = _python_sum(values)
        poison = arrays.poison_per_tick
        columns = RateColumns(
            kills_per_hour=kills,
            xp_per_hour=xp * np.ones(n),
            ticks_per_kill=ticks_per_kill,
            damage_per_kill=npc_attacks_per_kill * (melee_share * npc_mean + breath) + poison * ticks_per_kill,
            damage_per_hour=npc_attacks_per_hour * (melee_share * npc_mean + breath) + poison * TICKS_PER_HOUR,
            poison_per_kill=poison * ticks_per_kill,
            breath_per_kill=npc_attacks_per_kill * breath,
            damage_sd_per_kill=np.sqrt(npc_attacks_per_kill * melee_share * npc_variance),
            npc_max_hit=npc_max.astype(float),
            attacks_per_kill=ticks_fighting / speed)
    nan = np.where(valid, 0.0, np.nan)  # NaN where combat_rates is None
    return RateColumns(**{name: getattr(columns, name) + nan for name in RateColumns.__dataclass_fields__})


def _player_rolls(fighter: Fighter, plan: Plan, boosted: bool) -> tuple[int, int, int, float]:
    """player_offence's fighter side: (attack roll, the bonus index of the monster's defence it's against, max hit,
    attack interval)."""
    fl = fighter.flicks if boosted else NO_FLICKS
    if plan.combat_class == "melee":
        attack_type = max((STAB, SLASH, CRUSH), key=lambda i: fighter.bonuses[i])
        roll = f.player_melee_attack_roll(fighter.attack, plan.style, fighter.bonuses[attack_type], fl.attack)
        max_hit = f.player_melee_max_hit(fighter.strength, plan.style, fighter.bonuses[MELEE_STRENGTH], fl.strength)
        return roll, attack_type, max_hit, fighter.weapon_speed
    if plan.combat_class == "ranged":
        roll = f.player_ranged_attack_roll(fighter.ranged, plan.style, fighter.bonuses[RANGED], fl.ranged)
        max_hit = f.player_ranged_max_hit(fighter.ranged, plan.style, fighter.bonuses[RANGED_STRENGTH], fl.ranged)
        return roll, RANGED, max_hit, fighter.weapon_speed - (1 if plan.style == f.RAPID else 0)
    if plan.combat_class == "magic":
        roll = f.player_magic_attack_roll(fighter.magic, fighter.bonuses[MAGIC], fl.magic)
        return roll, MAGIC, f.spell_max_hit(plan.style), f.SPELL_ATTACK_SPEED
    raise ValueError(f"unknown combat class {plan.combat_class!r}")


def _npc_offence(fighter: Fighter, plan: Plan, arrays: NpcArrays) -> tuple[np.ndarray, np.ndarray]:
    """npc_offence's hit chance and max hit per monster: the player's defence roll by the monster's style (and melee
    attack type), without the defence prayer against a style the protection prayer covers."""
    player_style = plan.style if plan.combat_class != "magic" else f.ACCURATE
    chance = np.zeros(len(arrays.npcs))
    protected = np.zeros(len(arrays.npcs), dtype=bool)
    for style in STYLES:
        rows = arrays.style == style
        if not rows.any():
            continue
        covered = style in fighter.flicks.protects
        fl = NO_FLICKS if covered else fighter.flicks
        protected[rows] = covered
        if style == "melee":
            rolls = {t: f.player_defence_roll(fighter.defence, player_style, fighter.bonuses[t + 5], fl.defence)
                     for t in (STAB, SLASH, CRUSH)}
            defence = np.array([rolls[int(t)] for t in arrays.melee_type[rows]])
        elif style == "ranged":
            defence = f.player_defence_roll(fighter.defence, player_style, fighter.bonuses[RANGED + 5], fl.defence)
        else:
            defence = f.player_magic_defence_roll(fighter.defence, fighter.magic, player_style,
                                                  fighter.bonuses[MAGIC + 5], fl.defence, fl.magic)
        chance[rows] = _hit_chance(arrays.attack_roll[rows], defence)
    return chance, np.where(protected, 0, arrays.max_hit)
