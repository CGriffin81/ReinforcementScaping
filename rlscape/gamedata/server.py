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
CHARACTER_DESIGN = SERVER_CONTENT / "region" / "misc" / "tutisland" / "handlers" / "iface" / "CharacterDesign.java"
WOODCUTTING_NODE = SERVER_CONTENT / "global" / "skill" / "gather" / "woodcutting" / "WoodcuttingNode.java"
MINING_NODE = SERVER_CONTENT / "global" / "skill" / "gather" / "mining" / "MiningNode.java"
FISH = SERVER_CONTENT / "global" / "skill" / "fishing" / "Fish.kt"
FISHING_OPTION = SERVER_CONTENT / "global" / "skill" / "fishing" / "FishingOption.kt"
FISH_SPOTS = SERVER_CONTENT / "global" / "skill" / "fishing" / "FishSpots.kt"
PICKPOCKETS = SERVER_CONTENT / "global" / "skill" / "thieving" / "Pickpockets.kt"
CONSUMABLES = SERVER_CONTENT / "data" / "consumables" / "Consumables.java"
PRAYER_TYPE = SERVER_CONTENT.parent / "core" / "game" / "node" / "entity" / "player" / "link" / "prayer" / "PrayerType.java"
SMITHING = SERVER_CONTENT / "global" / "skill" / "smithing"
COOKABLE_ITEMS = SERVER_CONTENT / "global" / "skill" / "cooking" / "CookableItems.java"
LOGS = SERVER_CONTENT / "global" / "skill" / "firemaking" / "Log.java"
BONES = SERVER_CONTENT / "global" / "skill" / "prayer" / "Bones.kt"
STATIONS = REPO / "data" / "stations.csv"  # curated furnaces, anvils and ranges; see the file's "check" column
SKILLING_TOOL = SERVER_CONTENT / "data" / "skill" / "SkillingTool.java"
COMBAT_SPELL_DIR = SERVER_CONTENT.parent / "core" / "game" / "node" / "entity" / "combat" / "spell"
MODERN_SPELLS = SERVER_CONTENT / "global" / "skill" / "magic" / "modern"
PRICES = REPO / "data" / "prices_v2.csv"
AVA_INTERFERENCE = REPO / "data" / "ava_interference.csv"
RANGED_SAFESPOTS = REPO / "data" / "ranged_safespots.csv"
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
    weight: float = 0.0  # kg (ItemConfigParser.WEIGHT); banknotes have no config entry, so they weigh nothing


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
    respawn: int = 17  # ticks from its death to its respawn (respawn_delay; NPC.java's default 17)
    poison_amount: int = 0  # the severity its swings poison with (poison_amount), if poisonous

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
        """WeightedItem.getItem draws RandomFunction.random(min, max), which never returns max (unless min == max)."""
        if self.max_amount <= self.min_amount:
            return float(self.min_amount)
        return (self.min_amount + self.max_amount - 1) / 2

    @property
    def special(self) -> bool:
        return self.item_id in SPECIAL_DROP_SLOTS

    def expected(self, stacks: bool = False) -> dict[int, float]:
        """The expected count of each item this entry gives when it drops: its item, or for a sub-table's slot what
        that table gives (WeightBasedTable.convertWeightedItems); "nothing" and clue scrolls give nothing. With
        `stacks`, the expected number of ground items instead: one a drop, whatever its amount."""
        if not self.item_id:
            return {}
        if not self.special:
            return {self.item_id: 1.0 if stacks else self.mean_amount}
        table = sub_tables().get(self.item_id, ())
        rolls = self.mean_amount if self.item_id in MULTI_ROLL_SLOTS else 1.0
        total, out = sum(e.weight for e in table), {}
        for entry in table:
            if entry.item_id and total > 0:
                amount = 1.0 if stacks else entry.mean_amount
                out[entry.item_id] = out.get(entry.item_id, 0.0) + rolls * entry.weight / total * amount
        return out


# WeightBasedTable's placeholder ids that stand for a sub-table, not an item: the rare drop table (31), clue scrolls
# (1, 5733, 12070), CELEDT (799), and the uncommon seed, herb, gem, rare seed and allotment seed tables (14422-14430).
SPECIAL_DROP_SLOTS = frozenset({31, 1, 5733, 12070, 799, 14422, 14424, 14426, 14428, 14430})
# The shared sub-tables (data/configs/shared_tables/*.xml) the slots roll, ported 2026-11-06 after the drop probe
# (scripts/probe_drops.py). Clue scrolls aren't modelled: they drop nothing.
SUB_TABLE_FILES = {31: "RDT", 799: "CELEDT", 14422: "USDT", 14424: "HDT", 14426: "GDT", 14428: "RSDT", 14430: "ASDT"}
MULTI_ROLL_SLOTS = frozenset({14422, 14424})  # WeightBasedTable.isSpecialSlot: these roll random(min, max) times


@cache
def sub_tables() -> dict[int, tuple[DropEntry, ...]]:
    """Slot id -> its shared sub-table's entries (id 0 is nothing; the rare drop table keeps its nothings, which only
    a ring of wealth removes). Each is one weighted pick: RareDropTable's roll, and for the others
    RandomFunction.rollWeightedChanceTable."""
    out = {}
    for slot, name in SUB_TABLE_FILES.items():
        text = (SERVER_CONFIGS / "shared_tables" / f"{name}.xml").read_text(encoding="utf-8")
        out[slot] = tuple(DropEntry(int(i), int(low), int(high), float(w)) for i, low, high, w in re.findall(
            r'<item id="(\d+)" minAmt="(\d+)" maxAmt="(\d+)" weight="([\d.]+)"', text))
    return out


@dataclass
class DropTable:
    """WeightBasedTable.roll: every guaranteed entry drops; the main, charm and tertiary tables each roll once."""

    guaranteed: list[DropEntry] = field(default_factory=list)
    main: list[DropEntry] = field(default_factory=list)
    charm: list[DropEntry] = field(default_factory=list)
    tertiary: list[DropEntry] = field(default_factory=list)

    def expected_items(self, stacks: bool = False) -> dict[int, float]:
        """Expected count of each item per kill, the sub-tables' included; with `stacks`, of its ground items (a
        pickup each)."""
        expected: dict[int, float] = {}
        for entry in self.guaranteed:
            for item, count in entry.expected(stacks).items():
                expected[item] = expected.get(item, 0.0) + count
        for table in (self.main, self.charm, self.tertiary):
            total = sum(e.weight for e in table)
            for entry in table:
                if total > 0:
                    for item, count in entry.expected(stacks).items():
                        expected[item] = expected.get(item, 0.0) + entry.weight / total * count
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
def ava_interfering_items() -> frozenset[int]:
    """Chest armour that stops Ava's devices: chest pieces whose worn model is one of AvasDevice.metalBodies (the
    server's own list, exported by scripts/export_ava_interference.py). Only the chest slot counts."""
    with AVA_INTERFERENCE.open(newline="", encoding="utf-8") as f:
        return frozenset(int(r["item_id"]) for r in csv.DictReader(f))


@dataclass(frozen=True)
class RangedSafespot:
    """The best tile to shoot a site's monster from that it can't attack back from (the bridge's ranged_safespots,
    exported by scripts/export_ranged_safespots.py)."""

    tile: tuple[int, int, int]
    held: int  # the site's monsters (spawned within its radius) it holds against
    share: float  # of their wandering it holds from, on average (attacked at their spawn, it always does)
    steps: float  # how far they walk chasing before they stick, on average
    walk: int | None  # tiles from it to where their arrows land, on average; None if there's no way there
    threats: int  # aggressive monsters that reach it until aggression runs out
    pickup_threats: int  # aggressive monsters, besides the one killed, whose leash covers its arrows


@cache
def ranged_safespots() -> dict[tuple[int, tuple[int, int, int], int], RangedSafespot | None]:
    """(NPC id, site spawn, range) -> its best safespot, or None where the export found none. Range is the attack
    style's (7, or 9 long-ranged). A site missing from the file wasn't checked; no file, nothing was."""
    if not RANGED_SAFESPOTS.exists():
        return {}
    out: dict[tuple[int, tuple[int, int, int], int], RangedSafespot | None] = {}
    with RANGED_SAFESPOTS.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (int(r["npc_id"]), (int(r["site_x"]), int(r["site_y"]), int(r["site_z"])), int(r["range"]))
            out[key] = None if r["found"] != "1" else RangedSafespot(
                (int(r["tile_x"]), int(r["tile_y"]), int(r["tile_z"])), int(r["held"]), float(r["share"]),
                float(r["steps"]), int(r["walk"]) if r["walk"] else None, int(r["threats"]), int(r["pickup_threats"]))
    return out


@cache
def destroy_only_items() -> frozenset[int]:
    """Items whose inventory option is Destroy, not Drop (item_configs' destroy flag: Ava's devices, quest items,
    Slayer heads). The server has no Drop for them (checked live for Ava's devices, 2026-11-07)."""
    return frozenset(int(raw["id"]) for raw in json.loads((SERVER_CONFIGS / "item_configs.json").read_text(
        encoding="utf-8")) if raw.get("destroy") == "true")


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
            weight=float(raw["weight"]) if raw.get("weight") else 0.0,
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
            respawn=_int(raw.get("respawn_delay"), 17),
            poison_amount=_int(raw.get("poison_amount"), 0),
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


@cache
def implemented_quests() -> frozenset[str]:
    """The quests the server has (a Quest subclass it registers, @Initializable), by Quests enum name: 68 of the
    enum's 150. The bridge's `spawn` completes exactly these. The server can't mark the others complete: content
    behind one stays shut, or (where it checks ContentAPI.hasRequirement) opens once the character meets that quest's
    own requirements, which the sim doesn't model. A live test checks the list against the running server's."""
    out = set()
    for path in SERVER_CONTENT.rglob("*"):
        if path.suffix not in (".kt", ".java"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        found = re.search(r":\s*Quest\(\s*Quests\.([A-Z_0-9]+)", text) or (
            re.search(r"extends\s+Quest\b", text) and re.search(r"super\(\s*Quests\.([A-Z_0-9]+)", text))
        if found and re.search(r"^\s*@Initializable", text, re.M):  # not commented out (unfinished quests)
            out.add(found.group(1))
    return frozenset(out - UNREGISTERED_QUESTS)


# Marked @Initializable, but the running server doesn't register it: not in QuestRepository (checked live, 2026-11-06)
UNREGISTERED_QUESTS = frozenset({"A_SOULS_BANE"})


@cache
def starter_kit() -> tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
    """(inventory, bank) as (item id, amount): what a character leaves Tutorial Island with. CharacterDesign's
    STARTER_PACK and STARTER_BANK, which the bridge's `spawn` also gives."""
    text = CHARACTER_DESIGN.read_text(encoding="utf-8")

    def items(name: str) -> tuple[tuple[int, int], ...]:
        body = re.search(rf"{name}\s*=\s*new Item\[\]\s*\{{(.*?)\}};", text, re.S).group(1)
        return tuple((int(i), int(n)) for i, n in re.findall(r"new Item\(\s*(\d+)\s*,\s*(\d+)\s*\)", body))

    return items("STARTER_PACK"), items("STARTER_BANK")


# WoodcuttingListener.rollDepletion: these tree identifiers fall after every log; every other tree falls 1 time in 8.
ALWAYS_FALLING_TREES = frozenset({1, 2, 3, 4, 6})


@dataclass(frozen=True)
class TreeType:
    """One WoodcuttingNode identifier's parameters (WoodcuttingNode's constructor switch)."""

    identifier: int
    reward: int  # log item id
    level: int
    experience: float
    base_low: float
    base_high: float
    tier_mod_low: float
    tier_mod_high: float
    respawn_min: int  # ticks; getRespawnDuration scales between min and max by the share of player slots in use
    respawn_max: int  # both -1 for a tree that never falls (respawnRate = -1)

    @property
    def depletes(self) -> bool:
        return self.respawn_min > 0  # rollDepletion only runs when getRespawnRate() > 0

    @property
    def always_falls(self) -> bool:
        return self.depletes and self.identifier in ALWAYS_FALLING_TREES


def _identifier_switch(text: str) -> dict[int, dict[str, str]]:
    """case label -> {field: expression} for a node enum's `switch(identifier & 0xFF)` constructor blocks (there
    can be several constructors, e.g. WoodcuttingNode's farming-tree one). Consecutive labels share a body, and
    `identifier == N ? a : b` is resolved for each label."""
    blocks = []
    for match in re.finditer(r"switch\s*\(\s*identifier\s*&\s*0xFF\s*\)", text):
        start = text.index("{", match.end())
        depth, end = 0, start
        for end in range(start, len(text)):
            depth += {"{": 1, "}": -1}.get(text[end], 0)
            if depth == 0:
                break
        blocks.append(text[start:end])
    out: dict[int, dict[str, str]] = {}
    for labels, body in re.findall(r"((?:case\s+\d+:\s*)+)(.*?)break;", "\n".join(blocks), re.S):
        fields = {k: v.strip() for k, v in re.findall(r"(?:this\.)?(\w+)\s*=\s*([^;]+);", body)}
        for label in map(int, re.findall(r"\d+", labels)):
            resolved = {}
            for key, value in fields.items():
                ternary = re.fullmatch(r"identifier\s*==\s*(\d+)\s*\?\s*(.+?)\s*:\s*(.+)", value)
                resolved[key] = (ternary.group(2) if int(ternary.group(1)) == label else ternary.group(3)) \
                    if ternary else value
            out[label] = resolved
    return out


def _respawn_bounds(expression: str) -> tuple[int, int]:
    """`min | max << 16` -> (min, max); anything else (respawnRate = -1) -> (-1, -1)."""
    rate = re.match(r"(\d+)\s*\|\s*(\d+)\s*<<\s*16", expression)
    return tuple(map(int, rate.groups())) if rate else (-1, -1)


@cache
def tree_types() -> dict[int, TreeType]:
    """WoodcuttingNode identifier -> TreeType, from the constructor's switch."""
    out: dict[int, TreeType] = {}
    for label, f in _identifier_switch(WOODCUTTING_NODE.read_text(encoding="utf-8")).items():
        if "baseLow" in f:
            out[label] = TreeType(label, int(f["reward"]), int(f["level"]), float(f["experience"]),
                                  float(f["baseLow"]), float(f["baseHigh"]), float(f["tierModLow"]),
                                  float(f["tierModHigh"]), *_respawn_bounds(f["respawnRate"]))
    return out


@dataclass(frozen=True)
class RockType:
    """One MiningNode identifier's parameters (MiningNode's constructor switch)."""

    identifier: int
    reward: int  # ore item id
    level: int
    experience: float
    rate: float  # MiningListener.checkReward's host roll is uniform on [0, 100 * rate]
    respawn_min: int
    respawn_max: int


@cache
def rock_types() -> dict[int, RockType]:
    """MiningNode identifier -> RockType, from the constructor's switch."""
    out: dict[int, RockType] = {}
    for label, f in _identifier_switch(MINING_NODE.read_text(encoding="utf-8")).items():
        if {"reward", "rate", "level", "experience", "respawnRate"} <= f.keys():
            out[label] = RockType(label, int(f["reward"]), int(f["level"]), float(f["experience"]),
                                  float(f["rate"]), *_respawn_bounds(f["respawnRate"]))
    return out


@cache
def rock_objects() -> dict[int, frozenset[int]]:
    """MiningNode identifier -> the scenery ids of its rocks with ore (each enum entry is `(full, empty, identifier)`),
    so a click can pick one ore's rocks at a mixed mine."""
    out: dict[int, set[int]] = {}
    for full, _, ident in re.findall(r"^\s*[A-Z_0-9]+\(\s*(\d+),\s*(\d+),\s*\(byte\)\s*(\d+)\)",
                                     MINING_NODE.read_text(encoding="utf-8"), re.M):
        out.setdefault(int(ident), set()).add(int(full))
    return {k: frozenset(v) for k, v in out.items()}


@dataclass(frozen=True)
class FishType:
    """A Fish enum constant."""

    name: str
    item: int  # raw fish item id
    level: int
    experience: float
    low_chance: float  # catch chance at level 1
    high_chance: float  # catch chance at level 99

    def success_chance(self, level: int) -> float:
        """Fish.getSuccessChance: linear in level between the two bounds."""
        return (level - 1.0) * ((self.high_chance - self.low_chance) / (99.0 - 1.0)) + self.low_chance


@dataclass(frozen=True)
class FishingMethod:
    """A FishingOption enum constant: the tool, the level to use it, the bait each catch uses, and the fish rolled
    in order (rollFish tries them first to last)."""

    name: str
    tool: int
    level: int
    bait: tuple[int, ...]
    fish: tuple[str, ...]


@cache
def fish_types() -> dict[str, FishType]:
    text = FISH.read_text(encoding="utf-8")
    return {name: FishType(name, int(item), int(level), float(xp), float(low), float(high))
            for name, item, level, xp, low, high in re.findall(
                r"^\s*([A-Z_]+)\(Items\.[A-Z0-9_]+?_(\d+),\s*(\d+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\)", text, re.M)}


@cache
def fishing_methods() -> dict[str, FishingMethod]:
    text = FISHING_OPTION.read_text(encoding="utf-8")
    out = {}
    for name, tool, level, bait, fish in re.findall(
            r"^\s*([A-Z_]+)\(Items\.[A-Z0-9_]+?_(\d+),\s*(\d+),\s*Animation\(\d+\),\s*(null|intArrayOf\(.*?\)),"
            r"\s*\"\w+\",\s*(.*?)\),?\s*$", text, re.M):
        out[name] = FishingMethod(name, int(tool), int(level), tuple(map(int, re.findall(r"_(\d+)", bait))),
                                  tuple(re.findall(r"Fish\.([A-Z_]+)", fish)))
    return out


@dataclass(frozen=True)
class LootItem:
    """A WeightedItem: an item, an amount range, a weight, and whether it always drops."""

    item: int
    min_amount: int
    max_amount: int
    weight: float
    always: bool


@dataclass(frozen=True)
class PickpocketTarget:
    """A Pickpockets enum constant."""

    name: str
    npc_ids: tuple[int, ...]
    level: int
    low: float  # getSkillSuccessChance bounds
    high: float
    experience: float
    stun_damage_min: int  # RandomFunction.random(min, max) on a failed attempt
    stun_damage_max: int
    stun_ticks: int
    loot: tuple[LootItem, ...]


CLUE_SLOT_EASY = 1  # WeightBasedTable.SLOT_CLUE_EASY, added to a table by insertEasyClue(weight)


@cache
def pickpocket_targets() -> dict[str, PickpocketTarget]:
    """The Pickpockets enum. NPC ids are an intArrayOf(...) or an IntStream.rangeClosed(a, b); a table's
    insertEasyClue(w) adds the easy-clue slot (CLUE_SLOT_EASY) with weight w."""
    text = PICKPOCKETS.read_text(encoding="utf-8")
    out = {}
    for name, ids, level, low, high, xp, dmin, dmax, stun, table, clue in re.findall(
            r"^\s*([A-Z_]+)\((intArrayOf\(.*?\)|IntStream\.rangeClosed\(\d+,\s*\d+\)\.toArray\(\)),\s*(\d+),"
            r"\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*(\d+),\s*(\d+),\s*(\d+),\s*WeightBasedTable\.create\((.*?)\)"
            r"(?:\.insertEasyClue\(([\d.]+)\))?\s*\),?\s*$", text, re.M | re.S):
        loot = tuple(LootItem(int(i), int(lo), int(hi), float(w), always == "true") for i, lo, hi, w, always in
                     re.findall(r"WeightedItem\(\s*(?:Items\.[A-Z0-9_]+?_)?(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,"
                                r"\s*([\d.]+)\s*(?:,\s*(true|false))?\s*\)", table))
        if clue:
            loot += (LootItem(CLUE_SLOT_EASY, 1, 1, float(clue), False),)
        if span := re.fullmatch(r"IntStream\.rangeClosed\((\d+),\s*(\d+)\)\.toArray\(\)", ids):
            npc_ids = tuple(range(int(span[1]), int(span[2]) + 1))
        else:
            npc_ids = tuple(map(int, re.findall(r"(?:NPCs\.[A-Z0-9_]+?_)?(\d+)", ids.removeprefix("intArrayOf"))))
        out[name] = PickpocketTarget(name, npc_ids, int(level), float(low), float(high), float(xp), int(dmin),
                                     int(dmax), int(stun), loot)
    return out


@dataclass(frozen=True)
class Stall:
    """A thieving Stall enum constant."""

    name: str
    full_ids: tuple[int, ...]  # the stall objects it can be stolen from
    level: int
    rewards: tuple[tuple[int, int], ...]  # (item, amount); a steal takes one, picked uniformly
    experience: float
    restock_ticks: int  # how long the stall stays empty after a steal (SceneryBuilder.replace's restoreTicks)


@cache
def stalls() -> dict[str, Stall]:
    """Stall.java's constants whose ids are numbers (CANDLES names its object by a constant and is skipped)."""
    text = (PICKPOCKETS.parent / "Stall.java").read_text(encoding="utf-8")
    out = {}
    for name, full, level, rewards, xp, delay in re.findall(
            r"^\s*([A-Z_]+)\(new Integer\[\]\s*\{([\d,\s]+)\},\s*new Integer\[\]\s*\{[\d,\s]+\},\s*(\d+),"
            r"\s*new Item\[\]\s*\{(.*?)\},\s*([\d.]+),\s*(\d+),", text, re.M):
        items = tuple((int(i), int(n)) for i, n in re.findall(r"new Item\((\d+),\s*(\d+)\)", rewards))
        out[name] = Stall(name, tuple(int(i) for i in full.split(",")), int(level), items, float(xp), int(delay))
    return out


FLETCHING = SERVER_CONTENT / "global" / "skill" / "fletching"
KNIFE, BOWSTRING, FEATHER, ARROW_SHAFT, HEADLESS_ARROW = 946, 1777, 314, 52, 53
FLETCHED_LOGS = (1511, 1521, 1519, 1517, 1515, 1513)  # logs, oak, willow, maple, yew, magic


@dataclass(frozen=True)
class FletchRecipe:
    """One thing Fletching makes, as its craft script runs it: per unit (a log, a bow, a set), the inputs used, the
    products made and the experience; units_per_stage units every stage_ticks ticks, after a first tick."""

    name: str  # e.g. "yew_longbow_u", "string_yew_longbow", "headless_arrow", "adamant_arrow", "rune_dart"
    kind: str  # cut, string, headless, arrow, dart, bolt
    inputs: tuple[tuple[int, int], ...]  # (item, amount) per unit
    product: int
    per_unit: int  # products per unit: 15 arrow shafts a log, otherwise 1
    level: int
    experience: float  # per unit
    units_per_stage: int
    stage_ticks: int
    quest: str | None = None  # darts need The Tourist Trap (DartListeners)
    tool: int | None = None  # cutting needs a knife


def _fletching_rows(file: str, pattern: str) -> list[tuple[str, ...]]:
    return re.findall(pattern, (FLETCHING / file).read_text(encoding="utf-8"), re.M)


@cache
def fletching_recipes() -> dict[str, FletchRecipe]:
    """Fletching's recipes, from its enums and craft scripts (content/global/skill/fletching):
    - cut (LogCraftInfo, CraftItemWithLogScript): a log every 3 ticks into a bow (u), or into 15 arrow shafts; the
      crossbow stocks and the achey-log items are out of scope;
    - string (StringableCraftInfo, StringItemScript): a bow (u) and a bowstring every 2 ticks; bows only;
    - headless (HeadlessArrowCraftScript): 15 shafts and 15 feathers every 3 ticks, 1 XP each;
    - arrow (ArrowCraftInfo, TippedArrowCraftScript): 15 headless arrows and arrowtips every 3 ticks;
    - dart (DartCraftInfo, DartCraftScript): 10 dart tips and feathers every 3 ticks, after The Tourist Trap;
    - bolt (BoltCraftInfo, BoltCraftScript): 10 unfinished bolts and feathers every 3 ticks.
    Dragon, broad, blurite and silver projectiles are out of scope (rewards, quests or materials sim v0 lacks)."""
    item = r"Items\.\w+?_(\d+)"
    out: dict[str, FletchRecipe] = {}
    names = items()

    def key(product: int) -> str:
        return re.sub(r"[^a-z0-9]+", "_", names[product].name.lower()).strip("_")

    for name, log, product, xp, level in _fletching_rows(
            "log/LogCraftInfo.kt", rf"^\s*([A-Z_]+)\({item},\s*{item},\s*([\d.]+),\s*(\d+)\)"):
        if int(log) in FLETCHED_LOGS and "STOCK" not in name:
            shafts = int(product) == ARROW_SHAFT
            out[key(int(product)) if not shafts else "arrow_shaft"] = FletchRecipe(
                key(int(product)) if not shafts else "arrow_shaft", "cut", ((int(log), 1),), int(product),
                15 if shafts else 1, int(level), float(xp), 1, 3, tool=KNIFE)
    for name, crossbow, unstrung, strung, level, xp in _fletching_rows(
            "stringing/StringableCraftInfo.kt", rf"^\s*([A-Z_]+)\((true|false),\s*{item},\s*{item},\s*(\d+),\s*([\d.]+),"):
        if crossbow == "false" and "OGRE" not in name:
            recipe = f"string_{key(int(strung))}"
            out[recipe] = FletchRecipe(recipe, "string", ((int(unstrung), 1), (BOWSTRING, 1)), int(strung), 1,
                                       int(level), float(xp), 1, 2)
    out["headless_arrow"] = FletchRecipe("headless_arrow", "headless", ((ARROW_SHAFT, 1), (FEATHER, 1)),
                                         HEADLESS_ARROW, 1, 1, 1.0, 15, 3)
    for file, kind, per_stage, quest in (("arrow/ArrowCraftInfo.kt", "arrow", 15, None),
                                         ("darts/DartCraftInfo.kt", "dart", 10, "THE_TOURIST_TRAP"),
                                         ("bolts/BoltCraftInfo.kt", "bolt", 10, None)):
        for name, tip, product, level, xp in _fletching_rows(
                file, rf"^\s*([A-Z_]+)\({item},\s*{item},\s*(\d+),\s*([\d.]+)\)"):
            if any(word in name for word in ("DRAGON", "BROAD", "BLURITE", "SILVER")):
                continue
            second = HEADLESS_ARROW if kind == "arrow" else FEATHER
            out[key(int(product))] = FletchRecipe(key(int(product)), kind, ((second, 1), (int(tip), 1)), int(product),
                                                  1, int(level), float(xp), per_stage, 3, quest)
    return out


@cache
def ground_spawns(item: int) -> tuple[tuple[tuple[int, int, int], int], ...]:
    """(tile, respawn ticks) for each spawn of an item (data/configs/ground_spawns.json, read by GroundSpawnLoader:
    "{amount,x,y,z,respawn}" per spawn; the respawn is a Pulse of that many ticks)."""
    with (SERVER_CONFIGS / "ground_spawns.json").open(encoding="utf-8") as f:
        rows = [r for r in json.load(f) if int(r["item_id"]) == item]
    return tuple(((int(x), int(y), int(z)), int(respawn))
                 for r in rows for _, x, y, z, respawn in re.findall(r"\{(\d+),(\d+),(\d+),(\d+),(\d+)\}", r["loc_data"]))


@cache
def food_healing() -> dict[int, int]:
    """Item id -> hitpoints healed, for Consumables' single-bite foods (`new Food(new int[] {id}, new
    HealingEffect(n))`). Multi-bite foods (pizzas, cakes, pies) aren't included yet."""
    text = CONSUMABLES.read_text(encoding="utf-8")
    return {int(item): int(heal) for item, heal in re.findall(
        r"new Food\(new int\[\]\s*\{\s*(\d+)\s*\},\s*new HealingEffect\((\d+)\)\)", text)}


@dataclass(frozen=True)
class SmeltedBar:
    """A smelting Bar enum constant: level, experience, the bar, and the ores one bar takes."""

    name: str
    level: int
    experience: float
    product: int
    ores: tuple[tuple[int, int], ...]  # (item, amount)


@cache
def smelted_bars() -> dict[str, SmeltedBar]:
    text = (SMITHING / "smelting" / "Bar.java").read_text(encoding="utf-8")
    out = {}
    for name, level, xp, items in re.findall(r"^\s*([A-Z_]+)\((\d+),\s*([\d.]+),\s*(new Item\(.*?)\),?\s*$", text, re.M):
        stacks = [(int(i), int(n or 1)) for i, n in re.findall(r"new Item\(\s*(\d+)\s*(?:,\s*(\d+))?\s*\)", items)]
        out[name] = SmeltedBar(name, int(level), float(xp), stacks[0][0], tuple(stacks[1:]))
    return out


@dataclass(frozen=True)
class Smithable:
    """A Bars enum constant joined with its SmithingType and BarType."""

    name: str
    bar: int  # bar item id
    kind: str  # SmithingType name, e.g. TYPE_PLATEBODY
    product: int
    level: int
    bars: int  # bars used per item
    amount: int  # items made per action
    experience_per_bar: float  # BarType experience


@cache
def smithables() -> dict[str, Smithable]:
    types = {name: (int(bars), int(amount)) for name, bars, amount in re.findall(
        r"^\s*(TYPE_[A-Z_]+)\(\s*(\d+)\s*,.*?,\s*(\d+)\s*\),?\s*;?\s*$",
        (SMITHING / "SmithingType.java").read_text(encoding="utf-8"), re.M)}
    bar_types = {name: (int(bar), float(xp)) for name, bar, xp in re.findall(
        r"^\s*([A-Z_]+)\(\s*(\d+)\s*,\s*([\d.]+)\s*,\s*\"", (SMITHING / "BarType.java").read_text(encoding="utf-8"), re.M)}
    out = {}
    for name, bar_type, kind, product, level in re.findall(
            r"^\s*([A-Z_]+)\(BarType\.([A-Z_]+),\s*SmithingType\.(TYPE_[A-Z_]+),\s*(\d+),\s*(\d+)\)",
            (SMITHING / "Bars.java").read_text(encoding="utf-8"), re.M):
        if kind in types and bar_type in bar_types:
            bar, xp = bar_types[bar_type]
            out[name] = Smithable(name, bar, kind, int(product), int(level), *types[kind], xp)
    return out


@dataclass(frozen=True)
class Cookable:
    """A CookableItems enum constant: burn bounds on a fire and on a range, and the Lumbridge castle range's own."""

    name: str
    cooked: int
    raw: int
    burnt: int
    level: int
    experience: float
    fire: tuple[int, int]  # (low, high) for getSkillSuccessChance
    range: tuple[int, int]
    lumbridge_range: tuple[int, int]  # CookableItems.lumbridgeRangeValues, else the range bounds


@cache
def cookables() -> dict[int, Cookable]:
    """Raw item id -> Cookable."""
    text = COOKABLE_ITEMS.read_text(encoding="utf-8")
    lumbridge = {int(item): (int(low), int(high)) for item, low, high in re.findall(
        r"lumbridgeRangeValues\.put\(Items\.[A-Z0-9_]+?_(\d+),\s*new int\[\]\s*\{\s*(\d+)\s*,\s*(\d+)\s*\}\)", text)}
    out = {}
    for name, cooked, raw, burnt, level, xp, low, high, rlow, rhigh in re.findall(
            r"^\s*([A-Z_]+)\((\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*([\d.]+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)", text, re.M):
        raw_id, range_bounds = int(raw), (int(rlow), int(rhigh))
        out[raw_id] = Cookable(name, int(cooked), raw_id, int(burnt), int(level), float(xp), (int(low), int(high)),
                               range_bounds, lumbridge.get(raw_id, range_bounds))
    return out


@cache
def log_types() -> dict[int, tuple[int, float]]:
    """Log item id -> (Firemaking level, experience), from the firemaking Log enum."""
    return {item: (level, xp) for item, (level, xp, _) in _logs().items()}


@cache
def log_fire_ticks() -> dict[int, int]:
    """Log item id -> how long its fire burns, in ticks (Log.life, passed to SceneryBuilder.add)."""
    return {item: life for item, (_, _, life) in _logs().items()}


@cache
def _logs() -> dict[int, tuple[int, float, int]]:
    return {int(item): (int(level), float(xp), int(life)) for item, level, life, xp in re.findall(
        r"^\s*[A-Z_]+\((\d+),\s*(\d+),\s*(\d+),\s*\d+,\s*([\d.]+),\s*\d+\)", LOGS.read_text(encoding="utf-8"), re.M)}


@cache
def bone_experience() -> dict[int, float]:
    """Bone item id -> Prayer experience for burying it (Bones enum)."""
    return {int(item): float(xp) for item, xp in re.findall(
        r"^\s*[A-Z_0-9]+\(Items\.[A-Z0-9_]+?_(\d+),\s*([\d.]+)", BONES.read_text(encoding="utf-8"), re.M)}


@cache
def alchemy_values() -> dict[int, tuple[int, int]]:
    """Item id -> (high alchemy, low alchemy) coins, for the items the export lists (tradeable items; the server
    refuses to alch untradeable ones unless flagged alchemizable)."""
    with ITEM_DEFINITIONS.open(newline="") as f:
        return {int(r["id"]): (int(r["high_alch"]), int(r["low_alch"])) for r in csv.DictReader(f)}


@cache
def ge_prices_2009() -> dict[int, int]:
    """Item id -> the frozen 2009 GE price the frozen buyer pays and the frozen seller charges, for items that have
    one and aren't GE-blocked (data/prices_v2.csv)."""
    with PRICES.open(newline="") as f:
        return {int(r["item_id"]): int(r["ge_price_2009"]) for r in csv.DictReader(f)
                if r["ge_price_2009"] and r["source"] != "ge_blocked"}


@cache
def item_base_values() -> dict[int, int]:
    """Item id -> ItemDefinition value, which shop prices are built from."""
    with ITEM_DEFINITIONS.open(newline="") as f:
        return {int(r["id"]): int(r["value"]) for r in csv.DictReader(f)}


@cache
def unnoted_ids() -> dict[int, int]:
    """Item id -> its unnoted id (a banknote's real item), for the exported items."""
    with ITEM_DEFINITIONS.open(newline="") as f:
        return {int(r["id"]): int(r["unnoted_id"]) for r in csv.DictReader(f)}


@cache
def staff_runes() -> dict[int, frozenset[int]]:
    """Rune id -> the staves that stand in for it (MagicStaff: air, water, earth, fire)."""
    text = (COMBAT_SPELL_DIR / "MagicStaff.java").read_text(encoding="utf-8")
    out = {}
    for body in re.findall(r"^\s*[A-Z]+_RUNE\(([^)]*)\)", text, re.M):
        rune, *staves = map(int, re.findall(r"\d+", body))  # the first number is the rune itself
        out[rune] = frozenset(staves) - {rune}
    return out


@cache
def fire_staves() -> frozenset[int]:
    """Staves that stand in for fire runes (MagicStaff.FIRE_RUNE)."""
    return staff_runes()[554]


@cache
def rune_ids() -> dict[str, int]:
    """Runes enum constant name (AIR_RUNE, ...) -> item id."""
    text = (COMBAT_SPELL_DIR / "Runes.java").read_text(encoding="utf-8")
    return {name: int(item) for name, item in re.findall(r"([A-Z_]+_RUNE)\((\d+)\)", text)}


@dataclass(frozen=True)
class CombatSpell:
    name: str  # e.g. wind_strike, as in rlscape.combat.formulas.SPELLS
    level: int
    experience: float  # given on every cast, hit or splash (MagicSpell.addExperience)
    runes: dict[int, int]  # rune id -> amount per cast


ELEMENT_NAMES = {"Air": "wind", "Water": "water", "Earth": "earth", "Fire": "fire"}


@cache
def combat_spells() -> dict[str, CombatSpell]:
    """The modern elemental combat spells, from the SpellBook.MODERN.register calls in AirSpell, WaterSpell,
    EarthSpell and FireSpell."""
    runes, out = rune_ids(), {}
    for element, prefix in ELEMENT_NAMES.items():
        text = (MODERN_SPELLS / f"{element}Spell.java").read_text(encoding="utf-8")
        for kind, level, xp, args in re.findall(
                rf"new {element}Spell\(SpellType\.(\w+),\s*(\d+),\s*([\d.]+),(.*?)\)\);", text):
            cost = {runes[name]: int(n) for name, n in re.findall(r"Runes\.([A-Z_]+)\.getItem\((\d+)\)", args)}
            name = f"{prefix}_{kind.lower()}"
            out[name] = CombatSpell(name, int(level), float(xp), cost)
    return out


@dataclass(frozen=True)
class RangedWeapon:
    item: int
    ammo_slot: int  # 13: arrows or bolts in the quiver; 3: thrown, the weapon stack is its own ammunition
    weapon_type: str  # Weapon.WeaponType: DEFAULT, CROSSBOW, DOUBLE_SHOT, THROWN, DEGRADING, STAFF, CHINCHOMPA
    drop_ammo: bool  # fired ammunition can land on the ground (RangeSwingHandler.useAmmo)
    ammunition: tuple[int, ...]


WEAPON_TYPES = ("DEFAULT", "CROSSBOW", "DOUBLE_SHOT", "THROWN", "DEGRADING", "STAFF", "CHINCHOMPA")


@cache
def ranged_weapons() -> dict[int, RangedWeapon]:
    """RangedConfigLoader: ranged_weapon_configs.json (drop_ammo is Kotlin's toBoolean, so only "true" is true)."""
    out = {}
    for raw in json.loads((SERVER_CONFIGS / "ranged_weapon_configs.json").read_text(encoding="utf-8")):
        item = int(raw["itemId"])
        out.setdefault(item, RangedWeapon(item, int(raw["ammo_slot"]), WEAPON_TYPES[int(raw["weapon_type"])],
                                          raw["drop_ammo"].strip().lower() == "true",
                                          tuple(int(a) for a in raw["ammunition"].split(","))))
    return out


@cache
def equip_quest_locks() -> dict[int, str]:
    """Item id -> the quest it can't be worn without, from ItemQuestRequirementListener's onEquip blocks (e.g.
    Dragon Slayer for rune platebodies and green d'hide bodies). A block that only checks a quest is underway is
    read as needing it complete."""
    text = (SERVER_CONTENT / "global" / "handlers" / "item" / "ItemQuestRequirementListener.kt").read_text(
        encoding="utf-8")
    ids = lambda body: [int(i) for i in re.findall(r"(?:Items\.[A-Z0-9_]+?_)?(\d+)", body)]  # noqa: E731
    arrays = {name: ids(body) for name, body in re.findall(r"private val (\w+) = intArrayOf\((.*?)\)", text, re.S)}
    out: dict[int, str] = {}
    for block in re.split(r"(?=onEquip\()", text)[1:]:
        arg = re.match(r"onEquip\(([^)]*)\)", block).group(1).strip()
        quest = re.search(r"Quests\.([A-Z_]+)", block)
        if quest:
            for item in arrays.get(arg, ids(arg) if arg not in arrays else []):
                out.setdefault(item, quest.group(1))
    return out


@dataclass(frozen=True)
class Station:
    kind: str  # furnace, anvil, range
    name: str
    tile: tuple[int, int, int]
    object: int | None  # scenery id when the server treats this one specially (the Lumbridge range, 114)
    requires: str  # access requirement grammar (rlscape.combat.access), empty for none


@cache
def stations() -> tuple[Station, ...]:
    with STATIONS.open(newline="", encoding="utf-8") as f:
        return tuple(Station(r["kind"], r["name"], (int(r["x"]), int(r["y"]), int(r["plane"])),
                             int(r["object"]) if r["object"] else None, r["requires"]) for r in csv.DictReader(f))


@cache
def fish_spot_locations() -> dict[str, tuple[tuple[int, int, int], ...]]:
    """FishSpots: the tiles each group of fishing spots moves between (FishingNPC.moveSpot)."""
    text = FISH_SPOTS.read_text(encoding="utf-8")
    return {name: tuple((int(x), int(y), int(z)) for x, y, z in
                        re.findall(r"Location\(\s*(\d+),\s*(\d+),\s*(\d+)\s*\)", body))
            for name, body in re.findall(r"^\s*([A-Z_]+)\(\s*((?:\s*Location\([^)]*\),?)+)\s*\)", text, re.M)}


@cache
def fish_spot_counts() -> dict[str, int]:
    """FishSpots group -> the fishing spot NPCs spawned on its tiles (any kind: they block each other's moves)."""
    ids = set().union(*fishing_spot_ids().values())
    spawned = [tuple(t) for i in ids for t in spawns().get(i, ())]
    return {name: sum(t in set(tiles) for t in spawned) for name, tiles in fish_spot_locations().items()}


@cache
def fishing_spot_ids() -> dict[str, frozenset[int]]:
    """FishingOption name -> the fishing spot NPC ids that offer it (FishingSpot: each entry's ids and options), so a
    click can pick a spot of the right kind where several kinds sit together."""
    out: dict[str, set[int]] = {}
    text = (FISH_SPOTS.parent / "FishingSpot.kt").read_text(encoding="utf-8")
    for ids, options in re.findall(r"intArrayOf\(([^)]*)\)\s*,((?:\s*FishingOption\.[A-Z_]+,?)+)", text):
        for option in re.findall(r"FishingOption\.([A-Z_]+)", options):
            out.setdefault(option, set()).update(int(i) for i in re.findall(r"FISHING_SPOT_(\d+)", ids))
    return {k: frozenset(v) for k, v in out.items()}


@dataclass(frozen=True)
class SkillingTool:
    """A SkillingTool enum constant. `ordinal` is its position in the enum, which WoodcuttingListener.checkReward
    multiplies into the success bounds."""

    name: str
    item: int
    level: int
    ratio: float
    ordinal: int


@cache
def skilling_tools() -> dict[str, SkillingTool]:
    text = SKILLING_TOOL.read_text(encoding="utf-8")
    constants = re.findall(r"^\s*([A-Z_0-9]+)\(\s*(?:Items\.[A-Z0-9_]+_)?(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)D?", text,
                           re.M)
    return {name: SkillingTool(name, int(item), int(level), float(ratio), i)
            for i, (name, item, level, ratio) in enumerate(constants)}


@dataclass(frozen=True)
class Shop:
    """A shops.json entry as Shops.startup parses it: stock is '{item,amount,restockRate}-...', the rate defaulting
    to 100 ticks."""

    id: int
    title: str
    npcs: tuple[int, ...]
    general: bool
    currency: int
    stock: dict[int, tuple[int, int]]  # item -> (normal amount, restock rate in ticks)

    def tile(self) -> tuple[int, int, int] | None:
        """Where its first shopkeeper with a spawn stands."""
        return next((spawns()[npc][0] for npc in self.npcs if npc in spawns()), None)


@cache
def shops() -> dict[int, Shop]:
    out = {}
    for raw in json.loads((SERVER_CONFIGS / "shops.json").read_text(encoding="utf-8")):
        stock: dict[int, tuple[int, int]] = {}
        for item, amount, *rate in re.findall(r"\{(\d+),(-?\d+|inf)(?:,(\d+))?\}", raw["stock"]):
            normal = -1 if amount == "inf" else int(amount)
            if int(item) in stock:  # Shops.parseStock adds a repeated item's amount to the first entry
                stock[int(item)] = (stock[int(item)][0] + normal, stock[int(item)][1])
            else:
                stock[int(item)] = (normal, int(rate[0]) if rate and rate[0] else 100)
        npcs = tuple(int(n) for n in raw["npcs"].split(",") if n.strip())
        out[int(raw["id"])] = Shop(int(raw["id"]), raw["title"], npcs, raw["general_store"] == "true",
                                   int(raw["currency"]), stock)
    return out


@cache
def noted_ids() -> dict[int, int]:
    """Item id -> its banknote, for the exported items that have one."""
    return {real: note for note, real in unnoted_ids().items() if note != real}


@dataclass(frozen=True)
class Prayer:
    """A prayer as PrayerType defines it: the Prayer level it needs, the Defence level (Chivalry and Piety, which
    PrayerType.permitted also gives King's Ransom as a requirement) and its bonuses, each a fraction added to a
    skill's effective level in combat (SkillBonus)."""

    name: str
    level: int
    defence_level: int
    bonuses: tuple[tuple[str, float], ...]  # (skill, fraction), e.g. ("strength", 0.15)

    @property
    def quest(self) -> str | None:
        return "KINGS_RANSOM" if self.defence_level in (65, 70) else None


@cache
def prayers() -> dict[str, Prayer]:
    """PrayerType's prayers, by enum name."""
    skills = {"ATTACK": "attack", "STRENGTH": "strength", "DEFENCE": "defence", "RANGE": "ranged", "MAGIC": "magic"}
    out = {}
    for name, level, args in re.findall(r"^	([A-Z_]+)\((\d+), (.*)\),?;?$", PRAYER_TYPE.read_text(encoding="utf-8"), re.M):
        defence = re.search(r"Sounds\.\w+, (\d+),", args)  # the constructor that takes a Defence requirement
        bonuses = tuple((skills[s], float(v)) for s, v in re.findall(r"SkillBonus\(Skills\.(\w+), ([\d.]+)\)", args))
        out[name] = Prayer(name, int(level), int(defence.group(1)) if defence else 1, bonuses)
    return out

