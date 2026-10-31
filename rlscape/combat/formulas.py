"""Combat formulas ported from the 2009Scape fork's swing handlers (core/game/node/entity/combat).

Each function names the server method it mirrors. Prayers enter as `prayer`, the bonus of the prayer flicked for
that roll (rlscape.combat.prayers). Set effects, skillcape perks, salve amulets and slayer gear multiply rolls by 1.0
for the characters this project models, so they are left out; add them here, against the server code, if an option
starts using them.
"""

from __future__ import annotations

from math import floor

# WeaponInterface style bonuses to the effective level.
ACCURATE, AGGRESSIVE, DEFENSIVE, CONTROLLED = "accurate", "aggressive", "defensive", "controlled"
RAPID, LONGRANGE = "rapid", "longrange"


def prayer_boosted(level: int, prayer: float) -> int:
    """floor(L + bonus x L): every swing handler's step for a prayer's SkillBonus on the effective level."""
    return int(floor(level + prayer * level))


def hit_chance(attack_roll: float, defence_roll: float) -> float:
    """CombatSwingHandler.isAccurateImpact."""
    if attack_roll > defence_roll:
        return 1 - (defence_roll + 2) / (2 * (attack_roll + 1))
    return attack_roll / (2 * (defence_roll + 1))


# --- players ---------------------------------------------------------------------------------------------------

def player_melee_attack_roll(attack_level: int, style: str, attack_bonus: int, prayer: float = 0.0) -> int:
    """MeleeSwingHandler.calculateAccuracy (Player)."""
    effective = prayer_boosted(attack_level, prayer) + (3 if style == ACCURATE else 1 if style == CONTROLLED else 0) + 8
    return int(floor(effective) * (attack_bonus + 64))


def player_melee_max_hit(strength_level: int, style: str, strength_bonus: int, prayer: float = 0.0) -> int:
    """MeleeSwingHandler.calculateHit (Player); damage then rolls uniformly in 0..max."""
    style_bonus = 3 if style == AGGRESSIVE else 1 if style == CONTROLLED else 0
    effective = floor(prayer_boosted(strength_level, prayer) + style_bonus + 8)
    return int(floor(0.5 + effective * (strength_bonus + 64) / 640.0))


def player_ranged_attack_roll(ranged_level: int, style: str, ranged_bonus: int, prayer: float = 0.0) -> int:
    """RangeSwingHandler.calculateAccuracy (Player)."""
    effective = prayer_boosted(ranged_level, prayer) + (3 if style == ACCURATE else 0) + 8
    return int(floor(effective) * (ranged_bonus + 64))


def player_ranged_max_hit(ranged_level: int, style: str, ranged_strength: int, prayer: float = 0.0) -> int:
    """RangeSwingHandler.calculateHit (Player); damage then rolls uniformly in 0..max. The ranged prayers raise it
    too."""
    effective = floor(prayer_boosted(ranged_level, prayer) + (3 if style == ACCURATE else 0) + 8)
    return int(floor(0.5 + effective * (ranged_strength + 64) / 640.0))


def player_magic_attack_roll(magic_level: int, magic_bonus: int, prayer: float = 0.0) -> int:
    """MagicSwingHandler.calculateAccuracy (Player)."""
    return int(floor(prayer_boosted(magic_level, prayer) + 8) * (magic_bonus + 64))


def player_defence_roll(defence_level: int, style: str, defence_bonus: int, prayer: float = 0.0) -> int:
    """MeleeSwingHandler / RangeSwingHandler.calculateDefence (Player victim). defence_bonus is the bonus against
    the attacker's attack type (index + 5)."""
    style_bonus = 3 if style in (DEFENSIVE, LONGRANGE) else 1 if style == CONTROLLED else 0
    return int(prayer_boosted(defence_level, prayer) + style_bonus + 8) * (defence_bonus + 64)


def player_magic_defence_roll(defence_level: int, magic_level: int, style: str, magic_defence_bonus: int,
                              defence_prayer: float = 0.0, magic_prayer: float = 0.0) -> int:
    """MagicSwingHandler.calculateDefence (Player victim): 30% Defence, 70% Magic, each with its prayer."""
    style_bonus = 3 if style in (DEFENSIVE, LONGRANGE) else 1 if style == CONTROLLED else 0
    effective = ((prayer_boosted(defence_level, defence_prayer) + style_bonus) * 0.3
                 + prayer_boosted(magic_level, magic_prayer) * 0.7 + 8)
    return int(effective) * (magic_defence_bonus + 64)


# Modern spellbook combat spells: (level, base XP, element base). SpellType.getImpactAmount gives the max hit
# from the element base (air 1, water 2, earth 3, fire 4); the cast then rolls 0..max (MagicSwingHandler).
SPELLS = {
    "wind_strike": (1, 5.5, "strike", 1), "water_strike": (5, 7.5, "strike", 2),
    "earth_strike": (9, 9.5, "strike", 3), "fire_strike": (13, 11.5, "strike", 4),
    "wind_bolt": (17, 13.5, "bolt", 1), "water_bolt": (23, 16.5, "bolt", 2),
    "earth_bolt": (29, 19.5, "bolt", 3), "fire_bolt": (35, 22.5, "bolt", 4),
    "wind_blast": (41, 25.5, "blast", 1), "water_blast": (47, 28.5, "blast", 2),
    "earth_blast": (53, 31.5, "blast", 3), "fire_blast": (59, 34.5, "blast", 4),
    "wind_wave": (62, 36.0, "wave", 1), "water_wave": (65, 37.5, "wave", 2),
    "earth_wave": (70, 40.0, "wave", 3), "fire_wave": (75, 42.5, "wave", 4),
}
SPELL_ATTACK_SPEED = 5  # ticks per cast


def spell_max_hit(spell: str) -> int:
    """SpellType.getImpactAmount for the modern elemental spells."""
    _, _, kind, element = SPELLS[spell]
    return {"strike": 2 * element, "bolt": 8 + element, "blast": 12 + element, "wave": 16 + element}[kind]


# --- NPCs ------------------------------------------------------------------------------------------------------

def npc_attack_roll(level: int, attack_bonus: int) -> int:
    """Melee/Range/MagicSwingHandler.calculateAccuracy (NPC): (level + 9) * (bonus + 64)."""
    return (level + 9) * (attack_bonus + 64)


def npc_defence_roll(level: int, defence_bonus: int) -> int:
    """calculateDefence (NPC victim). Melee and ranged use Defence; magic uses the NPC's Magic level."""
    return (level + 9) * (defence_bonus + 64)


def npc_max_hit(strength_level: int, strength_bonus: int) -> int:
    """MeleeSwingHandler / RangeSwingHandler.calculateHit (NPC); damage rolls 0..max."""
    return int(floor(0.5 + (strength_level + 9) * (strength_bonus + 64) / 640.0))


def npc_magic_max_hit(magic_level: int, magic_bonus: int) -> int:
    """DefaultCombatSpell.getMaximumImpact fed through MagicSwingHandler.calculateHit (NPC). The cast rolls 0..max-1."""
    return 1 + int(14 + magic_level + magic_bonus / 8 + magic_level * magic_bonus * 0.016865) // 10


# --- expected damage -------------------------------------------------------------------------------------------

def mean_uniform(max_hit: int) -> float:
    return max_hit / 2


def second_moment_uniform(max_hit: int) -> float:
    """E[X^2] for X uniform on 0..max_hit."""
    return max_hit * (2 * max_hit + 1) / 6


def damage_moments(chance: float, max_hit: int) -> tuple[float, float]:
    """Mean and variance of one attack's damage: it hits with `chance`, then rolls uniformly in 0..max_hit."""
    mean = chance * mean_uniform(max_hit)
    return mean, chance * second_moment_uniform(max_hit) - mean * mean
