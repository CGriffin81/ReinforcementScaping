"""Game data read straight from the 2009Scape fork's config files, plus the project's price table.

Everything the simulator and the combat-rate model know about items, monsters, drops and spawns comes from here,
so they describe the same world the server runs. Field meanings follow the server's own parsers
(ItemConfigParser, NPCConfigParser, DropTableParser) and are noted where they matter.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SERVER_CONFIGS = REPO / "server" / "Server" / "data" / "configs"
SERVER_CONTENT = REPO / "server" / "Server" / "src" / "main" / "content"
SLAYER_TASKS = SERVER_CONTENT / "global" / "skill" / "slayer" / "Tasks.java"
QUESTS = SERVER_CONTENT / "data" / "Quests.kt"
PRICES = REPO / "data" / "prices_v2.csv"
ITEM_DEFINITIONS = REPO / "data" / "item_definitions.csv"  # scripts/export_item_definitions.py (cache)
NPC_DEFINITIONS = REPO / "data" / "npc_definitions.csv"  # scripts/export_npc_definitions.py (cache)
BANKS = REPO / "data" / "banks.csv"  # curated bank tiles; see the file's "check" column

# Equipment bonus array layout (15 entries), as indexed by the server's swing handlers.
STAB, SLASH, CRUSH, MAGIC, RANGED = 0, 1, 2, 3, 4  # attack bonuses; the matching defence bonus is index + 5
SUMMONING_DEF, MELEE_STRENGTH, PRAYER, MAGIC_STRENGTH, RANGED_STRENGTH = 10, 11, 12, 13, 14
NO_BONUSES = (0,) * 15

# NPCConfigParser stores combat_style / protect_style as CombatStyle ordinals.
COMBAT_STYLES = ("melee", "ranged", "magic")
DEFAULT_ATTACK_SPEED = 4  # Properties.attackSpeed when an NPC config doesn't set one


@dataclass(frozen=True)
class Item:
    id: int
    name: str
    equipment_slot: int | None
    bonuses: tuple[int, ...]
    attack_speed: int | None
    requirements: dict[int, int]  # skill id -> level needed to equip
    two_handed: bool


@dataclass(frozen=True)
class Npc:
    id: int
    name: str
    hitpoints: int
    attack: int
    strength: int
    defence: int
    ranged: int
    magic: int
    bonuses: tuple[int, ...]
    attack_speed: int
    combat_style: str  # melee / ranged / magic
    protect_style: str | None  # the combat class this NPC is immune to, if any
    aggressive: bool
    poisonous: bool

    @property
    def melee_attack_type(self) -> int:
        """NPC.configure: the attack type with the highest of the first three bonuses (stab when all are 0)."""
        best, index = 0, STAB
        for i in (STAB, SLASH, CRUSH):
            if self.bonuses[i] > best:
                best, index = self.bonuses[i], i
        return index


@dataclass(frozen=True)
class DropEntry:
    item_id: int  # 0 means "nothing"
    min_amount: int
    max_amount: int
    weight: float

    @property
    def mean_amount(self) -> float:
        return (self.min_amount + self.max_amount) / 2


@dataclass
class DropTable:
    """WeightBasedTable.roll: every guaranteed entry drops; the main, charm and tertiary tables each roll once."""

    guaranteed: list[DropEntry] = field(default_factory=list)
    main: list[DropEntry] = field(default_factory=list)
    charm: list[DropEntry] = field(default_factory=list)
    tertiary: list[DropEntry] = field(default_factory=list)

    def expected_items(self) -> dict[int, float]:
        """Expected count of each item per kill."""
        expected: dict[int, float] = {}
        for entry in self.guaranteed:
            if entry.item_id:
                expected[entry.item_id] = expected.get(entry.item_id, 0.0) + entry.mean_amount
        for table in (self.main, self.charm, self.tertiary):
            total = sum(e.weight for e in table)
            for entry in table:
                if entry.item_id and total > 0:
                    expected[entry.item_id] = expected.get(entry.item_id, 0.0) + entry.weight / total * entry.mean_amount
        return expected

    def expected_value(self, values: dict[int, int]) -> float:
        """Expected gp per kill at the given item values (items missing from the table count as 0)."""
        return sum(count * values.get(item_id, 0) for item_id, count in self.expected_items().items())


def _ints(text: str | None, default: tuple[int, ...] = NO_BONUSES) -> tuple[int, ...]:
    if not text:
        return default
    parts = tuple(int(p) for p in str(text).split(","))
    return parts + (0,) * (15 - len(parts))


def _requirements(text: str | None) -> dict[int, int]:
    """'{1,40}-{4,40}' -> {1: 40, 4: 40}"""
    return {int(s): int(lvl) for s, lvl in re.findall(r"\{(\d+),(\d+)\}", text or "")}


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@cache
def items() -> dict[int, Item]:
    out = {}
    for raw in json.loads((SERVER_CONFIGS / "item_configs.json").read_text(encoding="utf-8")):
        item_id = int(raw["id"])
        out[item_id] = Item(
            id=item_id,
            name=raw.get("name", ""),
            equipment_slot=_int(raw.get("equipment_slot"), -1) if raw.get("equipment_slot") else None,
            bonuses=_ints(raw.get("bonuses")),
            attack_speed=_int(raw.get("attack_speed"), 0) or None,
            requirements=_requirements(raw.get("requirements")),
            two_handed=raw.get("two_handed") == "true",
        )
    return out


@cache
def npcs() -> dict[int, Npc]:
    """NPCs with combat stats (those with lifepoints). Missing levels default to 1, as on the server."""
    out = {}
    for raw in json.loads((SERVER_CONFIGS / "npc_configs.json").read_text(encoding="utf-8")):
        if not raw.get("lifepoints"):
            continue
        npc_id = int(raw["id"])
        style = _int(raw.get("combat_style"), 0)
        protect = raw.get("protect_style")
        out[npc_id] = Npc(
            id=npc_id,
            name=raw.get("name") or "",
            hitpoints=_int(raw.get("lifepoints"), 1),
            attack=_int(raw.get("attack_level"), 1),
            strength=_int(raw.get("strength_level"), 1),
            defence=_int(raw.get("defence_level"), 1),
            ranged=_int(raw.get("range_level"), 1),
            magic=_int(raw.get("magic_level"), 1),
            bonuses=_ints(raw.get("bonuses")),
            attack_speed=_int(raw.get("attack_speed"), DEFAULT_ATTACK_SPEED),
            combat_style=COMBAT_STYLES[style] if 0 <= style < 3 else "melee",
            protect_style=COMBAT_STYLES[int(protect)] if protect not in (None, "") else None,
            aggressive=raw.get("aggressive") == "true",
            poisonous=raw.get("poisonous") == "true",
        )
    return out


@cache
def drop_tables() -> dict[int, DropTable]:
    """NPC id -> drop table. One table in the file can serve several NPC ids."""
    def entries(raw_list) -> list[DropEntry]:
        return [DropEntry(_int(e.get("id"), 0), _int(e.get("minAmount"), 1), _int(e.get("maxAmount"), 1),
                          float(e.get("weight") or 0)) for e in (raw_list or [])]

    out = {}
    for raw in json.loads((SERVER_CONFIGS / "drop_tables.json").read_text(encoding="utf-8")):
        table = DropTable(entries(raw.get("default")), entries(raw.get("main")),
                          entries(raw.get("charm")), entries(raw.get("tertiary")))
        for npc_id in str(raw.get("ids", "")).split(","):
            if npc_id.strip():
                out[int(npc_id)] = table
    return out


@cache
def spawns() -> dict[int, list[tuple[int, int, int]]]:
    """NPC id -> spawn tiles (x, y, plane), from npc_spawns.json's '{x,y,z,...}-{...}' strings."""
    out: dict[int, list[tuple[int, int, int]]] = {}
    for raw in json.loads((SERVER_CONFIGS / "npc_spawns.json").read_text(encoding="utf-8")):
        tiles = [(int(x), int(y), int(z)) for x, y, z in re.findall(r"\{(\d+),(\d+),(\d+)", raw.get("loc_data", ""))]
        if tiles:
            out.setdefault(int(raw["npc_id"]), []).extend(tiles)
    return out


@cache
def item_values() -> dict[int, int]:
    """Net-worth value per item id from data/prices_v2.csv (Caleb's valuation formula)."""
    with PRICES.open(newline="") as f:
        return {int(row["item_id"]): int(row["value"]) for row in csv.DictReader(f)}


@dataclass(frozen=True)
class NpcDefinition:
    """The cache's view of an NPC: what the client shows, independent of npc_configs.json."""

    id: int
    name: str
    combat_level: int
    attackable: bool
    size: int


@dataclass(frozen=True)
class Bank:
    name: str
    x: int
    y: int
    plane: int
    members: bool


@cache
def npc_definitions() -> dict[int, NpcDefinition]:
    with NPC_DEFINITIONS.open(newline="") as f:
        return {int(r["id"]): NpcDefinition(int(r["id"]), r["name"], int(r["combat_level"]), r["attackable"] == "True",
                                            int(r["size"])) for r in csv.DictReader(f)}


# Summoning charms (gold, green, crimson, blue) are untradeable, so the tradeable-item export doesn't cover them, but they
# stack and drop from many monsters.
SUMMONING_CHARMS = frozenset({12158, 12159, 12160, 12163})


@cache
def stackable_items() -> frozenset[int]:
    """Item ids that stack in one inventory slot: tradeable stackables from the cache export (coins, runes, arrows,
    banknotes, ...) plus summoning charms. Other untradeable drops count as one slot each."""
    with ITEM_DEFINITIONS.open(newline="") as f:
        tradeable = {int(r["id"]) for r in csv.DictReader(f) if r.get("stackable") == "True"}
    return frozenset(tradeable | {995} | SUMMONING_CHARMS)


@cache
def banks() -> tuple[Bank, ...]:
    with BANKS.open(newline="") as f:
        return tuple(Bank(r["name"], int(r["x"]), int(r["y"]), int(r["plane"]), r["members"] == "True")
                     for r in csv.DictReader(f))


# Tasks enum entries: NAME(combatCheck, new int[] { ids }, new String[] { info }, levelReq, ...)
_TASK = re.compile(r"^\s*[A-Z_]+\s*\(\s*\d+\s*,\s*new int\[\]\s*\{([^}]*)\}\s*,\s*new String\[\]\s*\{.*?\}\s*,\s*(\d+)",
                   re.M | re.S)


@cache
def slayer_levels() -> dict[int, int]:
    """NPC id -> the Slayer level needed to fight it, from the server's Tasks.java. As in Tasks.forId, an NPC listed
    under two tasks takes the first one's level. NPC.isAttackable in the fork refuses the attack below this level, as
    2009 did (upstream only printed a message)."""
    out: dict[int, int] = {}
    for ids, level in _TASK.findall(SLAYER_TASKS.read_text(encoding="utf-8")):
        for npc_id in re.findall(r"\d+", ids):
            out.setdefault(int(npc_id), int(level))
    return out


@cache
def quest_names() -> frozenset[str]:
    """The server's Quests enum names (content/data/Quests.kt), the vocabulary for quest requirements."""
    return frozenset(re.findall(r"^\s+([A-Z_0-9]+)\(\"", QUESTS.read_text(encoding="utf-8"), re.M))
