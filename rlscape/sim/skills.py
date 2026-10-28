"""Skills, experience and levels as the server defines them (core/game/node/entity/skill/Skills.java)."""

from __future__ import annotations

from bisect import bisect_right
from math import floor

# Skills.SKILL_NAME, in the server's order; arrays of per-skill values use this index.
SKILLS = ("attack", "defence", "strength", "hitpoints", "ranged", "prayer", "magic", "cooking", "woodcutting",
          "fletching", "fishing", "firemaking", "crafting", "smithing", "mining", "herblore", "agility", "thieving",
          "slayer", "farming", "runecrafting", "hunter", "construction", "summoning")
SKILL_INDEX = {name: i for i, name in enumerate(SKILLS)}
MAX_LEVEL = 99
MAX_XP = 200_000_000


def _experience_by_level(level: int) -> int:
    """Skills.getExperienceByLevel, line for line."""
    points = output = 0
    for lvl in range(1, level + 1):
        points += floor(lvl + 300.0 * 2.0 ** (lvl / 7.0))
        if lvl >= level:
            return output
        output = floor(points / 4)
    return output


XP_FOR_LEVEL = tuple(_experience_by_level(level) for level in range(MAX_LEVEL + 1))  # index = level; [1] = 0


def level_for_xp(xp: float) -> int:
    return min(bisect_right(XP_FOR_LEVEL, xp, lo=1) - 1, MAX_LEVEL)


def progress(xp: float) -> float:
    """Fractional progress from the current level to the next; 0 at level 99."""
    level = level_for_xp(xp)
    if level >= MAX_LEVEL:
        return 0.0
    return (xp - XP_FOR_LEVEL[level]) / (XP_FOR_LEVEL[level + 1] - XP_FOR_LEVEL[level])


def skill_measure(xp) -> float:
    """Σ over all 24 skills of (level + fractional progress): the quantity r_skill rewards changes in (env contract
    §4)."""
    return sum(level_for_xp(x) + progress(x) for x in xp)
