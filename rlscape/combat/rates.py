"""Theoretical combat rates (env contract §8): what fighting one NPC with one plan yields per hour.

Expected values from the server's formulas (rlscape.combat.formulas), used for the combat candidate slots and the
retreat-aware danger filter (option catalog §4) and, in the simulator, as the mean of combat outcomes. They are *theoretical*:
the real server measures the actual rates during calibration (E6).

Known simplifications, to refine against calibration data:
- time to kill is the expected number of swings until their damage reaches the NPC's HP, the last hit's overkill
  included (swings_to_kill; Caleb, 2026-11-07), with the flicked and plain swings mixed at random rather than in
  their pattern; the NPC doesn't regenerate;
- a constant per-kill overhead covers finding the next target and walking to it, and each looted drop adds a
  constant pickup time (with_pickups);
- a melee weapon attacks with whichever of stab / slash / crush it has the highest bonus in.

Fights flick prayers (rlscape.combat.prayers): the monster's hits of a style the character can protect itself from
deal nothing, defence prayers count otherwise, and the character's swings get its accuracy and damage prayers
except those next to a monster swing.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import sqrt

import numpy as np

from rlscape.combat import formulas as f
from rlscape.combat.prayers import NO_FLICKS, Flicks, boosted_share
from rlscape.gamedata.server import CRUSH, MAGIC, MAGIC_STRENGTH, MELEE_STRENGTH, RANGED, RANGED_STRENGTH, SLASH, STAB, Npc

TICKS_PER_HOUR = 6000
XP_PER_DAMAGE = 4.0  # CombatSwingHandler EXPERIENCE_MOD for ordinary targets
HP_XP_PER_DAMAGE = 1.33
# Finding and reaching the next target, beyond the fight, per combat class: fitted on the server without looting
# (scripts/calibrate_combat.py; 2026-11-07, with the combat inventory, the 16 cases of combat-20261107-0001.json and
# -0049.json: rats, scorpions, market guards and experiments; melee 0.91 to 1.19, ranged 0.95 to 1.14). Packed rats
# want 1, the experiments' cave about 7. It was 10 and 8 on 2026-11-05, when a bridge character's kills took about
# three clicks each (every character had account uid 0); now about one. Magic is taken as ranged (uncalibrated).
OVERHEAD_TICKS_PER_KILL = {"melee": 3, "ranged": 3, "magic": 3}
# Picking up a drop the loot mode keeps, per drop (a ground item, whatever its amount): the click and the walk to it.
# Fitted on the loot runs with the overhead above, the runner looting between kills attacked or not as the sim does
# (Caleb, 2026-11-07; the ranker's top gp picks, combat-20261107-0357-valuable.json): melee 0.98 to 1.13; ranged 0.90
# to 1.27, two cases outside the gate. Ranged's also covers the walks to its landed arrows, a few piles a kill, taken
# as they land, which the sim recovers with the kill and a cost a drop can't follow (raised for Caleb). Magic, with no
# ammunition to pick up, is taken as melee (uncalibrated).
PICKUP_TICKS = {"melee": 5, "ranged": 18, "magic": 5}
EAT_BELOW_FRACTION = 0.5  # combat options eat below 50% HP and retreat when food runs out (option catalog §4.B)
ESCAPE_ATTACKS = 2  # NPC attacks a retreating character can still take while it disengages; calibrate on the server
# Poison (core.game.system.timer.impl.Poison): a timer that hits every 30 ticks for floor((severity + 4) / 5), the
# severity falling by 1 a hit. A poisonous monster's every swing, hit or miss, poisons with its poison_amount 4 times
# in 10 (the swing handlers' adjustBattleState), so a protection prayer stops its damage but not its poison.
POISON_TICKS = 30
POISON_CHANCE = 0.4
# Dragonfire (DragonfireSwingHandler; ChromaticDragonNPC, MetalDragonNPC): a dragon picks each swing at random from its
# two melee attacks and its breath (MultiSwingHandler), so one in three is breath, and from a distance every one. The
# breath always lands, uniform from 0 to its max, 52, which an anti-dragon shield cuts by 90% and an antifire potion by
# 10% more (ContentAPI.calculateDragonfireMaxHit): 5 behind the shield, 0 with both (the 2009 wiki: "complete
# immunity against dragon fire" for the potion with the shield; super antifire came later). Fights against dragons
# need the shield (the gear check), so the rates take it as worn, and the melee swings as the fighter's prayers meet
# them. The King Black Dragon's other breaths aren't modelled.
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
BREATH_CHANCE = 1 / 3
DRAGONFIRE_MAX = 52


def breath_max(antifire: bool) -> int:
    """The breath's max behind an anti-dragon shield: int(52 - 0.9 x 52) = 5; with an antifire potion, 0."""
    return max(0, int(DRAGONFIRE_MAX - 0.9 * DRAGONFIRE_MAX - (0.1 * DRAGONFIRE_MAX if antifire else 0.0)))


def poison_damage(severity: int) -> int:
    return (severity + 4) // 5


def poison_per_tick(npc) -> float:
    """The poison a fight against the monster deals a tick, once it has taken: its swings poison so often (several
    in each 30 ticks) that the severity stays at the monster's."""
    return poison_damage(npc.poison_amount) / POISON_TICKS if npc.poisonous and npc.poison_amount > 0 else 0.0


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
    poison_per_kill: float = 0.0  # the poison in damage_taken_per_kill (and per hour), which antipoison keeps off
    poison_per_hour: float = 0.0
    breath_per_kill: float = 0.0  # a dragon's breath in it behind the shield, which antifire keeps off
    breath_per_hour: float = 0.0

    def passes_retreat_filter(self, max_hp: int, current_hp: float, food_healing: float, sigmas: float = 2.0,
                              poison_cover: float = 0.0, antifire_cover: float = 0.0) -> bool:
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
        # the shares antipoison and antifire keep off
        damage = (self.damage_taken_per_kill - poison_cover * self.poison_per_kill
                  - antifire_cover * self.breath_per_kill)
        return damage + sigmas * sqrt(self.damage_taken_variance_per_kill) <= budget


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


def npc_max_hit(npc: Npc) -> int:
    """The most one of the NPC's attacks can deal, in its combat style (unprotected)."""
    if npc.combat_style == "melee":
        return f.npc_max_hit(npc.strength, npc.bonuses[MELEE_STRENGTH])
    if npc.combat_style == "ranged":
        return f.npc_max_hit(npc.ranged, npc.bonuses[RANGED_STRENGTH])
    return f.npc_magic_max_hit(npc.magic, npc.bonuses[MAGIC_STRENGTH]) - 1  # the cast rolls 0..max-1


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
    elif npc.combat_style == "ranged":
        chance = f.hit_chance(f.npc_attack_roll(npc.ranged, npc.bonuses[RANGED]),
                              f.player_defence_roll(fighter.defence, player_style, fighter.bonuses[RANGED + 5],
                                                    fl.defence))
    else:
        chance = f.hit_chance(f.npc_attack_roll(npc.magic, npc.bonuses[MAGIC]),
                              f.player_magic_defence_roll(fighter.defence, fighter.magic, player_style,
                                                          fighter.bonuses[MAGIC + 5], fl.defence, fl.magic))
    max_hit = 0 if protected else npc_max_hit(npc)
    mean, variance = f.damage_moments(chance, max_hit)
    return chance, max_hit, mean, variance


_LANDED: dict[int, list[float]] = {}  # max hit -> prefix sums of landed_hits_to_kill, from 0 hitpoints


def landed_hits_to_kill(hitpoints: int, max_hit: int) -> float:
    """The expected number of damaging hits, each uniform from 1 to `max_hit`, until their total reaches `hitpoints`:
    g(h) = 1 + (g(h - 1) + ... + g(h - max_hit)) / max_hit, g(h <= 0) = 0 (the renewal function of the hit), which is
    (1 + 1 / max_hit) ** (h - 1) up to max_hit + 1. Exact, and cached per max hit, a step a hitpoint."""
    if hitpoints <= 0:
        return 0.0
    sums = _LANDED.setdefault(max_hit, [0.0])  # sums[h] = g(1) + ... + g(h)
    while len(sums) <= hitpoints:
        h = len(sums)
        sums.append(sums[-1] + 1.0 + (sums[h - 1] - sums[max(h - 1 - max_hit, 0)]) / max_hit)
    return sums[hitpoints] - sums[hitpoints - 1]


def swings_to_kill(hitpoints: int, kinds: tuple[tuple[float, float, int], ...]) -> float:
    """The expected number of swings until their damage reaches `hitpoints`, overkill and all, as the sim's
    kill_sequence deals it: a swing of each kind (share, hit chance, max hit) hits with the chance for uniform 0 to its
    max hit. Only damaging hits count towards the kill, so it's the damaging hits the kill takes over the chance a
    swing deals damage; with two kinds (the flicked and the plain swings), the hits are weighted by each kind's share
    of the damaging hits."""
    landing = [(share * chance * max_hit / (max_hit + 1), max_hit) for share, chance, max_hit in kinds
               if share > 0 and max_hit > 0]
    rate = sum(p for p, _ in landing)
    return sum(p / rate * landed_hits_to_kill(hitpoints, max_hit) for p, max_hit in landing) / rate


def with_pickups(rates: Rates, pickups_per_kill: float, combat_class: str) -> Rates:
    """The rates with each kill's pickups timed in: `pickups_per_kill` drops picked up, PICKUP_TICKS each, after the
    kill. The hourly rates fall in proportion; the monster's damage doesn't (it's dead), but poison runs on. The
    per-kill damage, which the danger filter reads, stays the fight's: a pickup's poison is a few hundredths of a
    hitpoint. The fast ranker (rlscape.combat.ranking) does the same arithmetic on its arrays."""
    if pickups_per_kill <= 0:
        return rates
    ticks = rates.ticks_per_kill + PICKUP_TICKS[combat_class] * pickups_per_kill
    scale = rates.ticks_per_kill / ticks
    fighting = rates.damage_taken_per_hour - rates.poison_per_hour
    return replace(rates, kills_per_hour=rates.kills_per_hour * scale,
                   xp_per_hour={skill: xp * scale for skill, xp in rates.xp_per_hour.items()},
                   gp_per_hour=rates.gp_per_hour * scale, ticks_per_kill=ticks,
                   damage_taken_per_hour=fighting * scale + rates.poison_per_hour,
                   damage_taken_variance_per_hour=rates.damage_taken_variance_per_hour * scale,
                   breath_per_hour=rates.breath_per_hour * scale)


def site_slowdown(ticks_per_kill, respawn, spawns, overhead: float):
    """How much longer a kill takes at a site than the fight alone allows (1 or more; arrays work too): with `spawns`
    of the monster there, each back `respawn` ticks after it dies, a kill comes at most every (respawn + fighting) /
    spawns ticks, fighting being `ticks_per_kill` less the class's `overhead` (measured on the server: Draynor's two
    market guards, 60 ticks each, hold a fast killer to that)."""
    return np.maximum(1.0, (respawn + ticks_per_kill - overhead) / spawns / ticks_per_kill)


def combat_rates(fighter: Fighter, plan: Plan, npc: Npc, gp_per_kill: float,
                 overhead_ticks: float | None = None) -> Rates | None:
    """Rates for fighting `npc` with `plan`, or None if the plan can't hurt it (immune to the class, or 0 damage)."""
    if npc.protect_style == plan.combat_class:
        return None
    if overhead_ticks is None:
        overhead_ticks = OVERHEAD_TICKS_PER_KILL[plan.combat_class]
    plain_chance, plain_max, speed, plain_mean, xp_per_damage = player_offence(fighter, plan, npc)
    boosted_chance, boosted_max, _, boosted_mean, _ = player_offence(fighter, plan, npc, boosted=True)
    share = boosted_share(int(speed), npc.attack_speed)  # the swings that get the accuracy and damage prayers
    chance = share * boosted_chance + (1 - share) * plain_chance
    mean_damage = share * boosted_mean + (1 - share) * plain_mean
    max_hit = boosted_max if share > 0 else plain_max
    if mean_damage / speed <= 0:
        return None
    ticks_fighting = speed * swings_to_kill(npc.hitpoints, ((share, boosted_chance, boosted_max),
                                                            (1 - share, plain_chance, plain_max)))
    ticks_per_kill = ticks_fighting + overhead_ticks
    kills = TICKS_PER_HOUR / ticks_per_kill
    damage_dealt = kills * npc.hitpoints

    npc_chance, npc_max, npc_mean, npc_variance = npc_offence(fighter, plan, npc)
    npc_attacks_per_kill = ticks_fighting / npc.attack_speed
    npc_attacks_per_hour = kills * npc_attacks_per_kill
    dragon = npc.id in DRAGONFIRE_NPCS
    melee_share = 1 - BREATH_CHANCE if dragon else 1.0  # a dragon's breath swings aren't its melee
    breath = BREATH_CHANCE * breath_max(False) / 2 if dragon else 0.0  # a swing's, on average
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
        damage_taken_per_hour=(npc_attacks_per_hour * (melee_share * npc_mean + breath)
                               + poison_per_tick(npc) * TICKS_PER_HOUR),
        damage_taken_variance_per_hour=npc_attacks_per_hour * melee_share * npc_variance,
        hit_chance=chance,
        max_hit=max_hit,
        npc_hit_chance=npc_chance,
        npc_max_hit=npc_max,
        ticks_per_kill=ticks_per_kill,
        damage_taken_per_kill=(npc_attacks_per_kill * (melee_share * npc_mean + breath)
                               + poison_per_tick(npc) * ticks_per_kill),
        damage_taken_variance_per_kill=npc_attacks_per_kill * melee_share * npc_variance,
        attacks_per_kill=ticks_fighting / speed,
        poison_per_kill=poison_per_tick(npc) * ticks_per_kill,
        poison_per_hour=poison_per_tick(npc) * TICKS_PER_HOUR,
        breath_per_kill=npc_attacks_per_kill * breath,
        breath_per_hour=npc_attacks_per_hour * breath,
    )
