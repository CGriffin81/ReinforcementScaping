"""Runecrafting's data from the server (sim v1; docs/sim-v1-skills-draft.md §5): content/global/skill/runecrafting
(Rune.java, RunecraftingData.kt). The essence mine is left out: essence isn't mined (Caleb, 2026-11-08)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache

from rlscape.gamedata.server import SERVER_CONTENT, rune_ids

RUNECRAFTING = SERVER_CONTENT / "global" / "skill" / "runecrafting"
RUNE_ESSENCE, PURE_ESSENCE = 1436, 7936
PLAIN_TIARA = 5525


def _item_const(text: str) -> int:
    """An `Items.NAME_123` constant's id (org.rs09.consts.Items names end in the id)."""
    return int(re.search(r"_(\d+)$", text).group(1))


@dataclass(frozen=True)
class Rune:
    """A Rune constant as a normal altar crafts it (RuneCraftPulse, at world.runecrafting_formula_revision 530, as
    rl.conf has it): every essence makes as many runes as the `multiples` levels at or under the character's
    Runecrafting level (at least 1), for `experience` an essence, from `level`. Air to body take rune or pure essence
    (Rune.isNormal); the rest only pure."""

    name: str  # e.g. "air", "nature"
    item: int
    level: int
    experience: float
    multiples: tuple[int, ...]
    pure_only: bool

    def per_essence(self, level: int) -> int:
        return max(sum(1 for m in self.multiples if level >= m), 1)


@dataclass(frozen=True)
class Ruins:
    """A MysteriousRuins constant: the ruins' tile outside (`base`) and where entering lands the character beside its
    altar (`end`). The talisman, used on the ruins, or the tiara, worn, lets it in (MysteriousRuinListener)."""

    name: str
    base: tuple[int, int, int]
    end: tuple[int, int, int]


@cache
def runes() -> dict[str, Rune]:
    text = (RUNECRAFTING / "Rune.java").read_text(encoding="utf-8")
    ids = rune_ids()
    normal = ("AIR", "MIND", "WATER", "EARTH", "FIRE", "BODY")  # Rune.isNormal
    out = {}
    for name, level, xp, multiples in re.findall(
            r"^\s*([A-Z]+)\(Runes\.[A-Z_]+\.transform\(\),\s*(\d+),\s*([\d.]+)(?:,\s*new int\[\]\s*\{([\d,\s]*)\})?\)",
            text, re.M):
        if not multiples:
            continue  # soul: no altar on the server
        out[name.lower()] = Rune(name.lower(), ids[f"{name}_RUNE"], int(level), float(xp),
                                 tuple(int(m) for m in multiples.replace(" ", "").split(",") if m), name not in normal)
    return out


@cache
def ruins() -> dict[str, Ruins]:
    text = (RUNECRAFTING / "RunecraftingData.kt").read_text(encoding="utf-8")
    loc = r"Location\.create\((\d+),\s*(\d+),\s*(\d+)\)"
    return {name.lower(): Ruins(name.lower(), (int(bx), int(by), int(bz)), (int(ex), int(ey), int(ez)))
            for name, bx, by, bz, ex, ey, ez in re.findall(
                rf"^\s*([A-Z]+)\(intArrayOf\([^)]*\),\s*{loc},\s*{loc}\)", text, re.M)}


@cache
def talismans() -> dict[str, int]:
    """Talisman: the rune -> its talisman's item id (the elemental and omni ones left out)."""
    text = (RUNECRAFTING / "RunecraftingData.kt").read_text(encoding="utf-8")
    body = text[text.index("enum class Talisman"):]
    return {name.lower(): _item_const(item) for name, item in re.findall(
        r"^\s*([A-Z]+)\(Item\(Items\.([A-Z_]+_TALISMAN_\d+)\)\)", body, re.M) if name not in ("ELEMENTAL", "OMNI")}


@cache
def tiaras() -> dict[str, tuple[int, float]]:
    """Tiara: the rune -> (its tiara, the Runecrafting XP of making it from a plain tiara and the talisman at the
    altar, TalismanEnchantingListener); the omni tiara left out."""
    text = (RUNECRAFTING / "RunecraftingData.kt").read_text(encoding="utf-8")
    body = text[text.index("enum class Tiara"):text.index("enum class Talisman")]
    return {name.lower(): (_item_const(item), float(xp)) for name, item, xp in re.findall(
        r"^\s*([A-Z]+)\(Item\(Items\.([A-Z_]+_TIARA_\d+)\),\s*([\d.]+)\)", body, re.M) if name != "OMNI"}
