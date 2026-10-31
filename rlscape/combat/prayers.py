"""Prayer flicking in fights (Caleb, 2026-10-31, OQ-3: "We're going to automatically flick prayers, including the
accuracy and damage options available"; defence prayers only "unless an enemy has multiple damage types or the agent
does not have access to the protection prayer associated").

How it works on 2009Scape (checked live: scripts/prayer_flick_test.py, scripts/prayer_offence_test.py):
- Prayer.tick drains only on the second tick in a row with any prayer on. A prayer that's on only in the ticks
  that need it, and off the next, never drains.
- Prayers act when a side swings: a protection prayer makes an NPC's hit of its style 0, and a prayer's bonus adds
  floor(L + bonus x L) to the effective level in the accuracy, max-hit and defence formulas.
- A monster starts swinging on the character's swing ticks (it retaliates when the first hit lands), then each side
  keeps its own attack speed.

So a fight flicks, every swing:
- on the monster's swing ticks: the protection prayer for its style if the Prayer level has it, otherwise the best
  defence prayer (and, against magic, the best Mystic prayer, since magic defence is 70% Magic);
- on the character's swing ticks: the best accuracy and damage prayers for its combat class (attack and strength,
  the ranged prayers, or the Mystic prayers), except on a tick next to a monster swing, since two ticks in a row
  would drain. The monster's tick keeps priority (agent choice, reversible).
Prayer points therefore never drain in a fight.

The sim gives each monster one combat style, so the "multiple damage types" case isn't modelled (dragonfire is the
gear check in rlscape.combat.candidates). Chivalry and Piety need King's Ransom, which isn't in the quest set; when a
character has it, they count in the best bonus per skill like any prayer.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from math import lcm

from rlscape.gamedata import server as gd

PROTECTION = {"magic": "PROTECT_FROM_MAGIC", "ranged": "PROTECT_FROM_MISSILES", "melee": "PROTECT_FROM_MELEE"}
OFFENCE = {"melee": ("attack", "strength"), "ranged": ("ranged",), "magic": ("magic",)}


@dataclass(frozen=True)
class Flicks:
    """What a character's prayers give a fight: the best bonus per skill (a fraction of the level) and the styles it
    can protect itself from."""

    attack: float = 0.0
    strength: float = 0.0
    defence: float = 0.0
    ranged: float = 0.0
    magic: float = 0.0
    protects: frozenset[str] = frozenset()

    def bonus(self, skill: str) -> float:
        return getattr(self, skill)


NO_FLICKS = Flicks()


@cache
def flicks(prayer_level: int, defence_level: int = 1, quests: frozenset[str] = frozenset()) -> Flicks:
    """The prayers a character can use: those its Prayer and Defence levels and quests allow (PrayerType.permitted).
    The best bonuses a tick needs can be on together (PrayerType.flag), except Chivalry or Piety with a Mystic prayer
    against a caster, which needs King's Ransom and isn't handled."""
    usable = [p for p in gd.prayers().values() if p.level <= prayer_level and p.defence_level <= defence_level
              and (p.quest is None or p.quest in quests)]
    best = {skill: max((b for p in usable for s, b in p.bonuses if s == skill), default=0.0)
            for skill in ("attack", "strength", "defence", "ranged", "magic")}
    names = {p.name for p in usable}
    return Flicks(**best, protects=frozenset(style for style, name in PROTECTION.items() if name in names))


@cache
def boosted_swings(player_speed: int, npc_speed: int) -> tuple[bool, ...]:
    """For the character's swings in one cycle of the two attack speeds, whether each gets the offensive flick: not
    when the monster swings the tick before or after (a monster's first swing comes on the character's)."""
    cycle = lcm(player_speed, npc_speed)
    monster = set(range(0, cycle + npc_speed, npc_speed)) | {-npc_speed}
    return tuple(t - 1 not in monster and t + 1 not in monster for t in range(0, cycle, player_speed))


def boosted_share(player_speed: int, npc_speed: int) -> float:
    swings = boosted_swings(player_speed, npc_speed)
    return sum(swings) / len(swings)
