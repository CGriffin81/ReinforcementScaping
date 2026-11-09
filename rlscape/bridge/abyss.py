"""The Abyss on the server, as a player sees it (sim v1, Runecrafting part 4; docs/sim-v1-skills-draft.md §5).

The server (content/global/skill/runecrafting/abyss/AbyssPlugin.kt):
- the Mage of Zamorak's Teleport (north of Edgeville, Wilderness level 5) lands the character on the outer ring at a
  random angle (AbyssLoc.randomLoc: radius 25.1, drawn in a tile at a time until the tile is free), drains its prayer
  and skulls it, and sets varbit 625 to the landing's segment (AbyssLoc.getSegment), which turns the twelve obstacles
  (scenery 7142-7153, multi-objects shown by that varbit) so the one by the landing is blocked;
- passing an obstacle (rocks: Mine; tendrils: Chop; a boil: Burn-down; eyes: Distract; a gap: Squeeze-through)
  locks the character 8 ticks, rolls (level + 1) / 100 on the third and moves it to the inner ring on the seventh
  (AbyssPlugin.innerRing: the obstacle's tile drawn 5 tiles in); a fail unlocks it on the third. The passage
  (Go-through) always moves it, at once;
- a rift's Exit-through sends it to the landing inside its altar's ruins (Altar.enterRift; chaos's beside the altar).

Every obstacle is clicked by the places' ids: the walls' tendrils (7189-7191) are named "Tendrils" too.
"""

from __future__ import annotations

import math
from typing import Any

from rlscape.bridge.client import BridgeClient
from rlscape.routes import beside, nearest_beside  # noqa: F401 (the scripts' and the walker's)

ORIGIN = (3039, 4832)  # AbyssLoc.origin
OUTER_RADIUS = 25.1  # AbyssLoc.outerRadius
INNER_STEPS = 5  # AbyssPlugin.innerRing: the obstacle's tile drawn this many tiles in
MAGE = "Mage of Zamorak"
MAGE_TILE = (3105, 3554, 0)  # its spawn, north of Edgeville
OBSTACLES = tuple(range(7142, 7154))  # the twelve places around the outer ring
INNER_RADIUS = 17  # the inner ring's landings are 13 to 15 tiles out; walks round the outer ring come to 19.9
# kind: (the name a player sees, its option, the skill it rolls)
KINDS = {
    "rocks": ("Rock", "Mine", "mining"),
    "tendrils": ("Tendrils", "Chop", "woodcutting"),
    "boil": ("Boil", "Burn-down", "firemaking"),
    "eyes": ("Eyes", "Distract", "thieving"),
    "gap": ("Gap", "Squeeze-through", "agility"),
    "passage": ("Passage", "Go-through", None),
}
# Altar's rifts (RunecraftingData.kt), by rune; blood's never opens (OQ-39) and soul's has no altar on the server.
# Chaos's is the server's, exported and measured, though the sim crafts no chaos runes (Caleb, 2026-11-09)
RIFTS = {"air": 7139, "mind": 7140, "water": 7137, "earth": 7130, "fire": 7129, "body": 7131, "cosmic": 7132,
         "law": 7135, "nature": 7133, "chaos": 7134, "death": 7136}


def polar(x: int, y: int) -> tuple[float, float]:
    """The radius from the Abyss's centre and the angle, degrees anticlockwise from east, in [0, 360)."""
    dx, dy = x - ORIGIN[0], y - ORIGIN[1]
    return math.hypot(dx, dy), math.degrees(math.atan2(dy, dx)) % 360


def segment(angle: float) -> int:
    """AbyssLoc.getSegment for an angle in degrees in [0, 360): the varbit's value."""
    return (9 - int(angle * 12 / 360 + 0.5)) % 12


def xy(s: dict[str, Any]) -> tuple[int, int]:
    return s["location"]["x"], s["location"]["y"]


def in_abyss(s: dict[str, Any]) -> bool:
    x, y = xy(s)
    return s["location"]["z"] == 0 and y > 4700 and polar(x, y)[0] < 40


def tick(c: BridgeClient, uid: int) -> tuple[int, dict[str, Any]]:
    step = c.schedule([[{"cmd": "state", "uid": uid}]])[0]
    return step["tick"], step["results"][-1]["state"]


def teleport(c: BridgeClient, uid: int, budget: int = 60) -> tuple[int, int, dict[str, Any]]:
    """The mage's Teleport, clicked where the character stands; (the click's tick, the landing's, the state on
    landing)."""
    c.interact(uid, MAGE, "Teleport", is_object=False)
    t0, s = tick(c, uid)
    for _ in range(budget):
        t, s = tick(c, uid)
        if in_abyss(s):
            return t0, t, s
    raise RuntimeError("the mage's teleport didn't land")


def places(c: BridgeClient, uid: int) -> dict[int, dict[str, Any]]:
    """The obstacles this character sees now, by the names a player sees (debug_nearby; calibration only): id ->
    its tile, angle and kind. The one by the landing is blocked, and no kind's name matches it."""
    out: dict[int, dict[str, Any]] = {}
    for kind, (name, _, _) in KINDS.items():
        for n in c.request("debug_nearby", uid=uid, name=name, radius=60)["nodes"]:
            if n["id"] in OBSTACLES:
                x, y = n["location"]["x"], n["location"]["y"]
                out[n["id"]] = {"kind": kind, "tile": (x, y), "angle": polar(x, y)[1]}
    return out


def landing_place(seen: dict[int, dict[str, Any]], angles: dict[int, float], landing_angle: float) -> int:
    """The landing's place: the one no kind's name matches, or if every one has a name, the nearest by angle."""
    unseen = [i for i in OBSTACLES if i not in seen]
    if len(unseen) == 1:
        return unseen[0]
    return min(angles, key=lambda i: abs((angles[i] - landing_angle + 180) % 360 - 180))
