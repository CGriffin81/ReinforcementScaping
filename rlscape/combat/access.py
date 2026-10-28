"""The access table (option catalog §4.C): which pool sites the character can reach right now.

Two kinds of lock, both checked every decision against the character's progress:
  1. access rules (data/access_areas.csv, curated): gated areas (a rectangle) and quest-only NPCs (a list of names,
     optionally inside a rectangle). Each row names the server check that enforces it, or says the server doesn't;
     the rule applies on both backends either way, because the candidate list is built here for both.
  2. Slayer levels, ported from the server's Tasks.java (rlscape.gamedata.slayer_levels).

Areas the table doesn't list count as open until calibration on the server finds them closed.

Requirement grammar (the csv's `requires` column): alternatives separated by " or ", each a set of terms joined
by "&", all of which must hold:
  quest:NAME      the quest is complete (server Quests enum names, plus the miniquests in MINIQUESTS)
  started:NAME    the quest is underway or complete
  underway:NAME   the quest is underway and not complete (quest-only monsters)
  item:ID|ID      any of these items is held: inventory, bank or equipped
  level:SKILL:N   the skill is at least N
  coins:N         at least N coins
  never           not fightable as an option (minigames, monsters fought inside a quest option)
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import cache, lru_cache

from rlscape.gamedata import server as gd

ACCESS_AREAS = gd.REPO / "data" / "access_areas.csv"
MINIQUESTS = frozenset({"PLAYER_SAFETY_TEST"})  # not in the server's Quests enum


@dataclass(frozen=True)
class Progress:
    """What the character has done and holds, as far as access is concerned. The default is a fresh character."""

    quests_complete: frozenset[str] = frozenset()
    quests_underway: frozenset[str] = frozenset()
    items_held: frozenset[int] = frozenset()  # inventory, bank or equipped
    levels: tuple[tuple[str, int], ...] = ()  # (skill, level) for skills above 1; lower-case skill names
    coins: int = 0

    def level(self, skill: str) -> int:
        return dict(self.levels).get(skill, 1)


Term = tuple[str, ...]


@dataclass(frozen=True)
class Requirement:
    alternatives: tuple[tuple[Term, ...], ...]

    def met(self, progress: Progress) -> bool:
        return any(all(_term_met(term, progress) for term in terms) for terms in self.alternatives)


def _term_met(term: Term, p: Progress) -> bool:
    kind = term[0]
    if kind == "quest":
        return term[1] in p.quests_complete
    if kind == "started":
        return term[1] in p.quests_complete or term[1] in p.quests_underway
    if kind == "underway":
        return term[1] in p.quests_underway
    if kind == "item":
        return any(int(item) in p.items_held for item in term[1].split("|"))
    if kind == "level":
        return p.level(term[1]) >= int(term[2])
    if kind == "coins":
        return p.coins >= int(term[1])
    if kind == "never":
        return False
    raise ValueError(f"unknown requirement term {':'.join(term)!r}")


def parse_requirement(text: str) -> Requirement:
    return Requirement(tuple(tuple(tuple(term.strip().split(":")) for term in alternative.split("&"))
                             for alternative in text.split(" or ")))


@dataclass(frozen=True)
class AccessRule:
    name: str
    npcs: frozenset[str]  # NPC names the rule covers; empty = every NPC in the bounds
    bounds: tuple[int, int, int, int] | None  # x1, y1, x2, y2 inclusive; None = anywhere
    planes: frozenset[int] | None  # None = every plane
    requires: Requirement
    enforced_by: str

    def covers(self, npc_name: str, spawn: tuple[int, int, int]) -> bool:
        if self.npcs and npc_name not in self.npcs:
            return False
        if self.planes is not None and spawn[2] not in self.planes:
            return False
        if self.bounds is not None:
            x1, y1, x2, y2 = self.bounds
            return x1 <= spawn[0] <= x2 and y1 <= spawn[1] <= y2
        return True


@cache
def access_rules() -> tuple[AccessRule, ...]:
    """The access table, in file order (which is also the order of the observation's access flags)."""
    rules = []
    with ACCESS_AREAS.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            bounds = tuple(int(r[k]) for k in ("x1", "y1", "x2", "y2")) if r["x1"] else None
            planes = None if r["planes"] == "all" else frozenset(int(p) for p in r["planes"].split("|"))
            rules.append(AccessRule(r["name"], frozenset(filter(None, r["npcs"].split("|"))), bounds, planes,
                                    parse_requirement(r["requires"]), r["enforced_by"]))
    return tuple(rules)


@lru_cache(maxsize=4096)
def unlocked_rules(progress: Progress) -> frozenset[str]:
    """Names of the access rules whose requirement the character meets (the observation's access flags)."""
    return frozenset(rule.name for rule in access_rules() if rule.requires.met(progress))


@cache
def rules_at(npc_name: str, spawn: tuple[int, int, int]) -> frozenset[str]:
    """Names of the access rules that cover this NPC at this spawn."""
    return frozenset(rule.name for rule in access_rules() if rule.covers(npc_name, spawn))


def meets_slayer_level(npc_id: int, progress: Progress) -> bool:
    return progress.level("slayer") >= gd.slayer_levels().get(npc_id, 1)


def can_reach(npc_name: str, spawn: tuple[int, int, int], progress: Progress) -> bool:
    """True if every access rule covering this NPC at this spawn is unlocked."""
    return rules_at(npc_name, spawn) <= unlocked_rules(progress)
