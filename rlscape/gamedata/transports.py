"""Transports from the server's source: teleports and boats (Caleb, 2026-11-01: travel takes the fastest usable way).

A Transport takes the character from where it is (a teleport) or from a boarding tile (a boat) to an arrival tile, in
`ticks`, if it meets the requirements and pays the cost. Parsed from the server's enums where they're data; the rest
is ported by hand, with the source cited:
- the standard teleport spells and the home teleport (ModernListeners, Modern): Magic level, runes, quest, Magic XP.
  The home teleport can be cast once every 30 minutes, as in January 2009 (Caleb, 2026-11-01; a fork change to
  homeTeleport, counted in game ticks);
- teleport jewellery at every charge (EnchantedJewellery): each destination a transport, a charge used per teleport
  (the item becomes the next charge; the last crumbles, or leaves an uncharged item that can't teleport). The ring
  of life (an emergency teleport, not travel) is left out (Caleb, 2026-11-01);
- teleport tablets (TeleTabsListener: the city tablets and the Runecrafting altar tablets), used up;
- the Grand seed pod (GrandSeedPodHandler: "squash" to the Grand Tree, "launch" to the Ta Quir Priw glider for 100
  Farming XP), used up. The Ectophial is left out: it needs Ghosts Ahoy, which this server doesn't implement (Caleb,
  2026-11-01);
- boats: the fixed ships the server runs (Ships, with their NPCs' dialogues: Port Sarim and Musa Point, Brimhaven to
  Ardougne, Entrana) and the charters (ShipCharter: ten ports, a fare matrix, quest-locked destinations). The
  Ardougne-to-Brimhaven ship needs Captain Barnaby, whom this server doesn't spawn.
Teleports can't be used deep in the Wilderness (WildernessZone: above level 20, or 30 for jewellery). The times are
measured on the server (scripts/validate_travel.py, 2026-11-01: from the first click to walking on, the trip's ticks
less the sim's walks), where a transport could be taken; otherwise the source's.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache

from rlscape.gamedata import server as gd
from rlscape.gamedata.server import SERVER_CONTENT
from rlscape.gamedata.shortcuts import LINKS as SHORTCUT_LINKS, TRIP_TICKS as SHORTCUT_TRIP_TICKS

LAW, AIR, FIRE, WATER, EARTH, BANANA = 563, 556, 554, 555, 557, 1963
COINS = 995


@dataclass(frozen=True)
class Transport:
    id: str
    kind: str  # spell, home, jewellery, tablet, seed_pod, ship, charter, shortcut
    end: tuple[int, int, int]  # where it arrives (for a boat that lands on its deck: the deck)
    ticks: int  # from the first click to being able to walk on
    start: tuple[int, int, int] | None = None  # boats: where they're boarded; teleports work from anywhere
    magic: int = 0  # Magic level
    runes: tuple[tuple[int, int], ...] = ()  # spells: (rune, amount) per cast
    items: tuple[int, ...] = ()  # any one of these held (worn or carried): jewellery at its charges, a tablet
    consumed: bool = False  # the item is used up (tablets, the seed pod); jewellery uses a charge instead
    coins: int = 0  # the fare
    quests: tuple[str, ...] = ()  # Quests names that must be complete
    skills: tuple[tuple[str, int], ...] = ()  # (skill, level) needed besides Magic, boosts counting
    xp: tuple[tuple[str, float], ...] = ()  # (skill, XP) it gives
    wilderness_limit: int = 20  # the deepest Wilderness level it can be used from (teleports)
    no_arms: bool = False  # Entrana: no weapons or armour carried or worn
    button: int | None = None  # spells: the spellbook button; jewellery: the destination's option
    npc: str = ""  # boats: who's clicked
    land: tuple[int, int, int] | None = None  # boats: the dock the walk on starts from, off the gangplank


# --- teleports ---------------------------------------------------------------------------------------------------------

HOME_TICKS = 22  # measured 22 (homeTeleport: 18 stages a tick apart, then the teleport)
HOME_COOLDOWN_TICKS = 3000  # 30 minutes from the teleport (the fork's HOME_TELEPORT_COOLDOWN_TICKS)
SPELL_TICKS = 6  # measured 6 (TeleportType.NORMAL: there at delay 3, done at 4, then lock(4))
TABLET_TICKS = 7  # measured: the Varrock tablet's trip matched (TeleportType.TELETABS: there at delay 3, then lock(2))
JEWELLERY_TICKS = 10  # measured 9.3 and 9.9: "Rub", the destination menu, then lock(4) and delayScript(3)
SEED_POD_TICKS = {"squash": 14, "launch": 9}  # squash measured 14 (delayEntity(12)); launch: delayEntity(7), unmeasured
SPELLBOOK = 192  # the standard spellbook's interface
# ModernListeners: (name, button = Modern's id, Magic, runes, arrival, XP, quest)
SPELLS = (
    ("varrock", 15, 25, ((FIRE, 1), (AIR, 3), (LAW, 1)), (3213, 3424, 0), 35.0, ()),
    ("lumbridge", 18, 31, ((EARTH, 1), (AIR, 3), (LAW, 1)), (3221, 3219, 0), 41.0, ()),
    ("falador", 21, 37, ((WATER, 1), (AIR, 3), (LAW, 1)), (2965, 3378, 0), 47.0, ()),
    ("camelot", 26, 45, ((AIR, 5), (LAW, 1)), (2758, 3478, 0), 55.5, ()),
    ("ardougne", 32, 51, ((WATER, 2), (LAW, 2)), (2662, 3307, 0), 61.0, ("PLAGUE_CITY",)),
    ("watchtower", 37, 58, ((EARTH, 2), (LAW, 2)), (2549, 3112, 0), 68.0, ("WATCHTOWER",)),
    ("trollheim", 44, 61, ((FIRE, 2), (LAW, 2)), (2891, 3678, 0), 68.0, ("EADGARS_RUSE",)),
    ("ape_atoll", 47, 64, ((FIRE, 2), (WATER, 2), (LAW, 2), (BANANA, 1)), (2795, 2798, 1), 74.0, ("MONKEY_MADNESS",)),
)
HOME = (3222, 3218, 0)  # ServerConstants.HOME_LOCATION's default
# The Shantay Pass (rlscape.sim.movement crosses it with a pass): ShantayGuard's gate tiles; quick-pass moves 2 tiles
GATE_NORTH, GATE_SOUTH = (3304, 3117, 0), (3304, 3115, 0)
# TeleTabsListener's Runecrafting tablets need what the altar does (MysteriousRuinListener.checkReq)
ALTAR_QUESTS = {"ASTRAL": "LUNAR_DIPLOMACY", "DEATH": "MOURNINGS_END_PART_II", "BLOOD": "LEGACY_OF_SEERGAZE",
                "COSMIC": "LOST_CITY"}
GRAND_SEED_POD = 9469
GRAND_TREE, TA_QUIR_PRIW = (2464, 3494, 0), (2465, 3501, 3)  # GrandSeedPodHandler; Gliders.TA_QUIR_PRIW


def _source(path: str) -> str:
    return (SERVER_CONTENT / path).read_text(encoding="utf-8")


def _locations(text: str) -> list[tuple[int, int, int]]:
    return [(int(x), int(y), int(z)) for x, y, z in re.findall(r"Location\.create\((\d+),\s*(\d+),\s*(\d+)\)", text)]


@cache
def jewellery() -> dict[str, tuple[tuple[str, ...], tuple[tuple[int, int, int], ...], bool, tuple[int, ...]]]:
    """EnchantedJewellery: name -> (destinations' names, their tiles, crumbles, item ids from most charges down)."""
    text = _source("data/EnchantedJewellery.kt")
    body = text[text.index("enum class EnchantedJewellery"):text.index("val isCrumble")]
    out = {}
    for name, block in re.findall(r"\n    ([A-Z_]+)\((.*?)\n    \)[,;]", body, re.S):
        if block.lstrip().startswith("AMULET_OF_GLORY.options"):  # the trimmed glory: the plain one's
            options, tiles = out["AMULET_OF_GLORY"][0], out["AMULET_OF_GLORY"][1]
        else:
            tiles = tuple(_locations(block))
            options = tuple(re.findall(r'"([^"]+)"', block))[:len(tiles)] or tuple(f"{name.lower()}" for _ in tiles)
        ids = tuple(int(i) for i in re.findall(r"Items\.[A-Z0-9_]+_(\d+)\b", block))  # the id: the last number
        out[name] = (options, tiles, bool(re.search(r"\btrue\b", block)), ids)
    return out


@cache
def tablets() -> dict[str, tuple[int, tuple[int, int, int]]]:
    """TeleTabsListener.TeleTabs: name -> (item, arrival)."""
    text = _source("global/handlers/item/TeleTabsListener.kt")
    return {name: (int(item), (int(x), int(y), int(z))) for name, item, x, y, z in re.findall(
        r"\n\s+([A-Z_]+)\(Items\.[A-Z0-9_]+?_(\d+),\s*Location\.create\((\d+),\s*(\d+),\s*(\d+)\)", text)}


def _tablet_quests(name: str) -> tuple[str, ...]:
    if name == "ADDOUGNE_TELEPORT":
        return ("PLAGUE_CITY",)
    if name.endswith("_ALTAR_TELEPORT"):
        altar = name.removesuffix("_ALTAR_TELEPORT")
        return ("RUNE_MYSTERIES", *((ALTAR_QUESTS[altar],) if altar in ALTAR_QUESTS else ()))
    return ()


def _spell_gate(quests: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[tuple[str, int], ...]]:
    """What a teleport spell's quest check asks: ModernListeners checks ContentAPI.hasRequirement, so a quest the
    server has must be complete, and one it doesn't (Eadgar's Ruse, Watchtower, Monkey Madness) is met by its own
    requirement (gd.quest_gate; Caleb, 2026-11-08: these teleports are open, as the quests are flagged complete)."""
    needed: set[str] = set()
    levels: dict[str, int] = {}
    for quest in quests:
        gate_quests, gate_skills = gd.quest_gate(quest)
        needed |= gate_quests
        for skill, level in gate_skills:
            levels[skill] = max(levels.get(skill, 0), level)
    return tuple(sorted(needed)), tuple(sorted(levels.items()))


def _teleports() -> list[Transport]:
    out = [Transport("home", "home", HOME, HOME_TICKS, button=0)]
    for name, button, magic, runes, end, xp, quests in SPELLS:
        gate_quests, gate_skills = _spell_gate(quests)
        out.append(Transport(f"spell:{name}", "spell", end, SPELL_TICKS, magic=magic, runes=runes, quests=gate_quests,
                             skills=gate_skills, xp=(("magic", xp),), button=button))
    for name, (options, tiles, crumbles, ids) in jewellery().items():
        if name == "RING_OF_LIFE":
            continue
        charged = ids if crumbles else ids[:-1]  # the last of a recharging piece is uncharged
        for option, (button, tile) in zip(options, enumerate(tiles)):
            quests = ("HAUNTED_MINE",) if name == "RING_OF_SLAYING" and button == 3 else ()
            out.append(Transport(f"jewellery:{name.lower()}:{option.rstrip('.').lower()}", "jewellery", tile,
                                 JEWELLERY_TICKS, items=charged, quests=quests, wilderness_limit=30, button=button))
    for name, (item, tile) in tablets().items():
        out.append(Transport(f"tablet:{name.lower()}", "tablet", tile, TABLET_TICKS, items=(item,), consumed=True,
                             quests=_tablet_quests(name)))
    out.append(Transport("seed_pod:squash", "seed_pod", GRAND_TREE, SEED_POD_TICKS["squash"], items=(GRAND_SEED_POD,),
                         consumed=True))
    out.append(Transport("seed_pod:launch", "seed_pod", TA_QUIR_PRIW, SEED_POD_TICKS["launch"],
                         items=(GRAND_SEED_POD,), consumed=True, xp=(("farming", 100.0),)))
    return out


# --- boats -------------------------------------------------------------------------------------------------------------

DISEMBARK_TICKS = 3  # crossing the gangplank off a ship's deck
SHIP_BOARDING_TICKS = 11  # measured 10 and 13 beyond the sailing: the NPC's conversation (before Pirate's Treasure)
CHARTER_TICKS = 17  # measured 20 with the gangplank: the interface, the fare's Ok, the sailing (count 3 to 5)
# Fixed ships the server runs: (id, board near, NPC, arrival, Ships.delay, fare, Entrana's rule, the dock). A ship that
# lands on its deck is left by the gangplank, onto its dock: Musa Point's measured (the gangplank at 2956, 3144 lands
# at 2956, 3146); the others the nearest tile to the deck that joins the land (rlscape.routes), to check.
SHIPS = (
    ("port_sarim-karamja", (3028, 3220, 0), "Seaman Thresnor", (2956, 3143, 1), 9, 30, False, (2956, 3146, 0)),
    ("karamja-port_sarim", (2953, 3149, 0), "Customs officer", (3029, 3217, 0), 8, 30, False, (3029, 3217, 0)),
    ("brimhaven-ardougne", (2770, 3226, 0), "Customs officer", (2683, 3268, 1), 4, 30, False, (2683, 3271, 0)),
    ("port_sarim-entrana", (3047, 3234, 0), "Monk of Entrana", (2834, 3331, 1), 15, 0, True, (2830, 3335, 0)),
    ("entrana-port_sarim", (2833, 3335, 0), "Monk of Entrana", (3048, 3234, 0), 15, 0, True, (3048, 3234, 0)),
)
# The Rellekka ferries (Caleb, 2026-11-08, OQ-16 (a); RellekkaListeners: the ferrymen's own option, with The
# Fremennik Trials; free): (name, the tile beside the ferryman, who, where it lands, ticks from the click to standing
# there, measured on the server 2026-11-08: 17 each way, 3 runs each, one at 14)
RELLEKKA_FERRIES = (
    ("rellekka-neitiznot", (2645, 3710, 0), "Maria Gunnars", (2310, 3782, 0), 17),
    ("neitiznot-rellekka", (2311, 3782, 0), "Maria Gunnars", (2644, 3710, 0), 17),
    ("rellekka-jatizso", (2644, 3708, 0), "Mord Gunnars", (2421, 3781, 0), 17),
    ("jatizso-rellekka", (2422, 3782, 0), "Mord Gunnars", (2644, 3710, 0), 17),
)
FERRY_QUESTS = ("THE_FREMENNIK_TRIALS",)
# ShipCharter.Destination.getCost's table order, and the destinations' own checkTravel quests
CHARTER_ORDER = ("BRIMHAVEN", "CATHERBY", "KARAMJA", "MOS_LE_HARMLESS", "PORT_KHAZARD", "PORT_PHASMATYS", "PORT_SARIM",
                 "SHIPYARD", "PORT_TYRAS", "OO_GLOG")
CHARTER_QUESTS = {"PORT_PHASMATYS": "PRIEST_IN_PERIL", "CRANDOR": "DRAGON_SLAYER", "PORT_TYRAS": "REGICIDE",
                  "SHIPYARD": "THE_GRAND_TREE", "MOS_LE_HARMLESS": "CABIN_FEVER"}
CHARTER_IFACE = 95


@cache
def charter_ports() -> dict[str, tuple[tuple[int, int, int], int, tuple[int, ...], tuple[int, int, int] | None]]:
    """ShipCharter.Destination: name -> (arrival, button, fares in CHARTER_ORDER, base: where it's boarded)."""
    text = _source("global/travel/ship/ShipCharter.java")
    out = {}
    for name, x, y, z, button, costs, base in re.findall(
            r"\n\t\t([A-Z_]+)\(Location\.create\((\d+), (\d+), (\d+)\), (\d+), new int\[\] \{([^}]*)\}, "
            r"(null|Location\.create\(\d+, \d+, \d+\))", text):
        base_tile = _locations(base)[0] if base != "null" else None
        out[name] = ((int(x), int(y), int(z)), int(button), tuple(int(c) for c in costs.split(",")), base_tile)
    return out


def _boats() -> list[Transport]:
    out = [Transport(f"ship:{name}", "ship", end, SHIP_BOARDING_TICKS + delay + DISEMBARK_TICKS * (end[2] > 0),
                     start=start, coins=fare,
                     no_arms=no_arms, npc=npc, land=land)
           for name, start, npc, end, delay, fare, no_arms, land in SHIPS]
    out += [Transport(f"ship:{name}", "ship", end, ticks, start=start, npc=npc, land=end, quests=FERRY_QUESTS)
            for name, start, npc, end, ticks in RELLEKKA_FERRIES]
    ports = charter_ports()
    for origin, (_, _, fares, base) in ports.items():
        if base is None:
            continue  # Crandor: no charter leaves it
        for destination, (end, button, _, landing) in ports.items():
            if destination == origin or destination not in CHARTER_ORDER:
                continue
            fare = fares[CHARTER_ORDER.index(destination)]
            if fare <= 0:
                continue  # not offered from here
            quests = (CHARTER_QUESTS[destination],) if destination in CHARTER_QUESTS else ()
            out.append(Transport(f"charter:{origin.lower()}-{destination.lower()}", "charter", end,
                                 CHARTER_TICKS + DISEMBARK_TICKS * (end[2] > 0), start=base, coins=fare,
                                 quests=quests, button=button, npc="Trader Crewmember", land=landing))
    return out


def _shortcuts() -> list[Transport]:
    """The Agility shortcuts (rlscape.gamedata.shortcuts), as the boats are: taken from where they're clicked to where
    they land, at their Agility level, in their measured ticks and what one costs a trip, for any XP they give."""
    return [Transport(f"shortcut:{s.key}", "shortcut", s.end, s.ticks + SHORTCUT_TRIP_TICKS, start=s.start,
                      skills=(("agility", s.level),), xp=(("agility", s.xp),) if s.xp else (), land=s.end)
            for s in SHORTCUT_LINKS]


@cache
def transports() -> tuple[Transport, ...]:
    return tuple(_teleports() + _boats() + _shortcuts())


def wilderness_level(tile: tuple[int, int, int]) -> int:
    """The Wilderness level of a surface tile (0 outside it): a level every 8 tiles north of its edge at y 3520."""
    x, y = tile[0], tile[1]
    if not (2944 <= x <= 3391 and 3520 <= y <= 3967):
        return 0
    return (y - 3520) // 8 + 1
