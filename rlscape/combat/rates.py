"""Theoretical combat rates (env contract §8): what fighting one NPC with one plan yields per hour.

Expected values from the server's formulas (rlscape.combat.formulas), used for the combat candidate slots and the
retreat-aware danger filter (option catalog §4) and, in the simulator, as the mean of combat outcomes. They are *theoretical*:
the real server measures the actual rates during calibration (E6).

Known simplifications, to refine against calibration data:
- time to kill is HP / damage-per-tick (no overkill or regeneration of the NPC);
- a constant per-kill overhead covers finding the next target and walking to it;
- a melee weapon attacks with whichever of stab / slash / crush it has the highest bonus in.

Fights flick prayers (rlscape.combat.prayers): the monster's hits of a style the character can protect itself from
deal nothing, defence prayers count otherwise, and the character's swings get its accuracy and damage prayers
except those next to a monster swing.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from rlscape.combat import formulas as f
from rlscape.combat.prayers import NO_FLICKS, Flicks, boosted_share
from rlscape.gamedata.server import CRUSH, MAGIC, MAGIC_STRENGTH, MELEE_STRENGTH, RANGED, RANGED_STRENGTH, SLASH, STAB, Npc

TICKS_PER_HOUR = 6000
XP_PER_DAMAGE = 4.0  # CombatSwingHandler EXPERIENCE_MOD for ordinary targets
HP_XP_PER_DAMAGE = 1.33
OVERHEAD_TICKS_PER_KILL = 6  # finding and reaching the next target; calibrate on the server
EAT_BELOW_FRACTION = 0.5  # combat options eat below 50% HP and retreat when food runs out (option catalog §4.B)
ESCAPE_ATTACKS = 2  # NPC attacks a retreating character can still take while it disengages; calibrate on the server


@dataclass(frozen=True)
class Fighter:
    """The player's side: current levels, summed equipment bonuses and weapon speed."""

    attack: int
    strength: int
    defence: int
    hitpoints: int
    ranged: int
    magic: int
    bonuses: tuple[int, ...]
    weapon_speed: int = 4
    flicks: Flicks = NO_FLICKS  # what the Prayer level gives a fight (rlscape.combat.prayers)


@dataclass(frozen=True)
class Plan:
    """How to fight: the combat class plus a training style (melee / ranged) or a spell (magic)."""

    combat_class: str  # "melee" | "ranged" | "magic"
    style: str  # melee: accurate / aggressive / defensive / controlled; ranged: accurate / rapid / longrange; magic: spell id


@dataclass(frozen=True)
class Rates:
    kills_per_hour: float
    xp_per_hour: dict[str, float]
    gp_per_hour: float
    damage_taken_per_hour: float
    damage_taken_variance_per_hour: float
    hit_chance: float
    max_hit: int
    npc_hit_chance: float
    npc_max_hit: int
    ticks_per_kill: float
    damage_taken_per_kill: float
    damage_taken_variance_per_kill: float
    attacks_per_kill: float  # what a kill costs in arrows or casts

    def passes_retreat_filter(self, max_hp: int, current_hp: float, food_healing: float, sigmas: float = 2.0) -> bool:
        """Retreat-aware danger filter (Caleb, 2026-10-27; option catalog §4.B).

        A combat option eats below half HP and retreats once the food is gone, so the fight never runs on until the
        character dies of slow damage. What can kill it is (1) a burst: the NPC hitting hard enough, between the
        retreat point and getting away, to take it from half HP to zero; or (2) never finishing a kill, so the fight
        is pure loss. The NPC qualifies if neither can happen:
          1. ESCAPE_ATTACKS max hits must stay below the retreat HP (half of max HP);
          2. the damage taken during one kill, plus `sigmas` standard deviations, must fit in the HP above the
             retreat point plus the healing in the food carried.
        """
        retreat_hp = EAT_BELOW_FRACTION * max_hp
        if self.npc_max_hit * ESCAPE_ATTACKS >= retreat_hp:
            return False
        budget = max(current_hp - retreat_hp, 0.0) + food_healing
        return self.damage_taken_per_kill + sigmas * sqrt(self.damage_taken_variance_per_kill) <= budget


def player_offence(fighter: Fighter, plan: Plan, npc: Npc,
                   boosted: bool = False) -> tuple[float, int, float, float, dict[str, float]]:
    """(hit chance, max hit, attack interval in ticks, mean damage per attack, XP per point of damage by skill), for a
    swing with the class's accuracy and damage prayers flicked (`boosted`) or without."""
    fl = fighter.flicks if boosted else NO_FLICKS
    if plan.combat_class == "melee":
        attack_type = max((STAB, SLASH, CRUSH), key=lambda i: fighter.bonuses[i])
        chance = f.hit_chance(f.player_melee_attack_roll(fighter.attack, plan.style, fighter.bonuses[attack_type],
                                                         fl.attack),
                              f.npc_defence_roll(npc.defence, npc.bonuses[attack_type + 5]))
        max_hit = f.player_melee_max_hit(fighter.strength, plan.style, fighter.bonuses[MELEE_STRENGTH], fl.strength)
        speed = fighter.weapon_speed
        if plan.style == f.CONTROLLED:
            xp = {"attack": XP_PER_DAMAGE / 3, "strength": XP_PER_DAMAGE / 3, "defence": XP_PER_DAMAGE / 3}
        else:
            trained = {f.ACCURATE: "attack", f.AGGRESSIVE: "strength", f.DEFENSIVE: "defence"}[plan.style]
            xp = {trained: XP_PER_DAMAGE}
        mean, _ = f.damage_moments(chance, max_hit)
    elif plan.combat_class == "ranged":
        chance = f.hit_chance(f.player_ranged_attack_roll(fighter.ranged, plan.style, fighter.bonuses[RANGED],
                                                          fl.ranged),
                              f.npc_defence_roll(npc.defence, npc.bonuses[RANGED + 5]))
        max_hit = f.player_ranged_max_hit(fighter.ranged, plan.style, fighter.bonuses[RANGED_STRENGTH], fl.ranged)
        speed = fighter.weapon_speed - (1 if plan.style == f.RAPID else 0)
        if plan.style == f.LONGRANGE:
            xp = {"ranged": XP_PER_DAMAGE / 2, "defence": XP_PER_DAMAGE / 2}
        else:
            xp = {"ranged": XP_PER_DAMAGE}
        mean, _ = f.damage_moments(chance, max_hit)
    elif plan.combat_class == "magic":
        chance = f.hit_chance(f.player_magic_attack_roll(fighter.magic, fighter.bonuses[MAGIC], fl.magic),
                              f.npc_defence_roll(npc.magic, npc.bonuses[MAGIC + 5]))
        max_hit = f.spell_max_hit(plan.style)
        speed = f.SPELL_ATTACK_SPEED
        xp = {"magic": XP_PER_DAMAGE}
        mean, _ = f.damage_moments(chance, max_hit)
    else:
        raise ValueError(f"unknown combat class {plan.combat_class!r}")
    xp["hitpoints"] = HP_XP_PER_DAMAGE
    return chance, max_hit, speed, mean, xp


def npc_offence(fighter: Fighter, plan: Plan, npc: Npc) -> tuple[float, int, float, float]:
    """(hit chance, max hit, mean, variance) of one NPC attack on the player. A style the character's protection
    prayer covers deals nothing (Entity.getFormattedHit); otherwise its defence prayers count."""
    player_style = plan.style if plan.combat_class != "magic" else f.ACCURATE
    protected = npc.combat_style in fighter.flicks.protects
    fl = NO_FLICKS if protected else fighter.flicks
    if npc.combat_style == "melee":
        attack_type = npc.melee_attack_type
        chance = f.hit_chance(f.npc_attack_roll(npc.attack, npc.bonuses[attack_type]),
                              f.player_defence_roll(fighter.defence, player_style, fighter.bonuses[attack_type + 5],
                                                    fl.defence))
        max_hit = f.npc_max_hit(npc.strength, npc.bonuses[MELEE_STRENGTH])
    elif npc.combat_style == "ranged":
        chance = f.hit_chance(f.npc_attack_roll(npc.ranged, npc.bonuses[RANGED]),
                              f.player_defence_roll(fighter.defence, player_style, fighter.bonuses[RANGED + 5],
                                                    fl.defence))
        max_hit = f.npc_max_hit(npc.ranged, npc.bonuses[RANGED_STRENGTH])
    else:
        chance = f.hit_chance(f.npc_attack_roll(npc.magic, npc.bonuses[MAGIC]),
                              f.player_magic_defence_roll(fighter.defence, fighter.magic, player_style,
                                                          fighter.bonuses[MAGIC + 5], fl.defence, fl.magic))
        max_hit = f.npc_magic_max_hit(npc.magic, npc.bonuses[MAGIC_STRENGTH]) - 1  # the cast rolls 0..max-1
    if protected:
        max_hit = 0
    mean, variance = f.damage_moments(chance, max_hit)
    return chance, max_hit, mean, variance


def combat_rates(fighter: Fighter, plan: Plan, npc: Npc, gp_per_kill: float,
                 overhead_ticks: float = OVERHEAD_TICKS_PER_KILL) -> Rates | None:
    """Rates for fighting `npc` with `plan`, or None if the plan can't hurt it (immune to the class, or 0 damage)."""
    if npc.protect_style == plan.combat_class:
        return None
    plain_chance, plain_max, speed, plain_mean, xp_per_damage = player_offence(fighter, plan, npc)
    chance, max_hit, _, mean_damage, _ = player_offence(fighter, plan, npc, boosted=True)
    share = boosted_share(int(speed), npc.attack_speed)  # the swings that get the accuracy and damage prayers
    chance = share * chance + (1 - share) * plain_chance
    mean_damage = share * mean_damage + (1 - share) * plain_mean
    max_hit = max_hit if share > 0 else plain_max
    damage_per_tick = mean_damage / speed
    if damage_per_tick <= 0:
        return None
    ticks_fighting = npc.hitpoints / damage_per_tick
    ticks_per_kill = ticks_fighting + overhead_ticks
    kills = TICKS_PER_HOUR / ticks_per_kill
    damage_dealt = kills * npc.hitpoints

    npc_chance, npc_max, npc_mean, npc_variance = npc_offence(fighter, plan, npc)
    npc_attacks_per_kill = ticks_fighting / npc.attack_speed
    npc_attacks_per_hour = kills * npc_attacks_per_kill
    if plan.combat_class == "magic":
        casts = kills * ticks_fighting / speed
        spell_xp = casts * f.SPELLS[plan.style][1]
    else:
        spell_xp = 0.0
    xp = {skill: rate * damage_dealt for skill, rate in xp_per_damage.items()}
    if spell_xp:
        xp["magic"] = xp.get("magic", 0.0) + spell_xp
    return Rates(
        kills_per_hour=kills,
        xp_per_hour=xp,
        gp_per_hour=kills * gp_per_kill,
        damage_taken_per_hour=npc_attacks_per_hour * npc_mean,
        damage_taken_variance_per_hour=npc_attacks_per_hour * npc_variance,
        hit_chance=chance,
        max_hit=max_hit,
        npc_hit_chance=npc_chance,
        npc_max_hit=npc_max,
        ticks_per_kill=ticks_per_kill,
        damage_taken_per_kill=npc_attacks_per_kill * npc_mean,
        damage_taken_variance_per_kill=npc_attacks_per_kill * npc_variance,
        attacks_per_kill=ticks_fighting / speed,
    )
