"""The observation (env contract §3): one flat float32 vector in [0, 1], built from named parts by one ObsEncoder that
SimEnv and ServerEnv share. ServerEnv turns the bridge's state into a CharacterState first, so both backends encode
the same thing the same way.

Parts, in order (sizes for vocabulary V, A access rules, N actions):

| Part | Size | Encoding |
|---|---|---|
| time | 2 | elapsed / horizon; remaining / horizon |
| skills | 2 × 20 | level / 99 and progress to the next level, for the 19 trainable skills and Slayer |
| total_level | 1 | total level / 2376 |
| hitpoints_prayer | 2 | current / max (prayer isn't drained in the sim, so it reads 1) |
| run_energy_weight | 2 | energy / 100; kg / 100, clipped |
| wealth | 2 | log1p(coins) and log1p(net worth), over log1p(10M) |
| inventory | V + 1 | log1p(count) / log1p(28) per V item; free slots / 28 |
| bank | V | log1p(count) / log1p(10k) per V item |
| equipment | 11 | tier / top tier of the best item carried (worn or in the inventory) per role, 0 for none |
| region | 12 | one-hot: the catalog's 11 regions, or elsewhere |
| combat_candidates | 18 × 5 | per slot: XP/hr, gp/hr, damage per hour vs HP and food, travel, open |
| skilling_candidates | 20 × 5 | per slot: the slot's skill's XP/hr, its processing counterpart's XP/hr, gp/hr, travel, open |
| loot_mode | 4 | one-hot |
| task | 12 | one-hot: the last activity's task, which decides what bank_deposit keeps (rlscape.sim.kits) |
| potions | 11 × 2 | each potion's doses in the inventory and the bank, log1p-scaled (four-dose potions alone are in V) |
| access | A | 0/1 per access rule (data/access_areas.csv order) |
| mask | N | the action mask |
| preference | 2 | (w_s, w_b), only for the preference-conditioned agent (E4) |

Agent choices the contract leaves open, all reversible:
- Equipment tiers come from the item's name: the metal (bronze 1 … dragon 8) for melee weapons, ammunition, armour
  and anything else metal; the wood for bows (plain 1 … magic 6); the kind for staves (plain 1, elemental 2,
  battlestaff 3, mystic 4); the tool chains for axes and pickaxes; for fishing gear, the highest Fishing level a tool
  held is used at, over the highest any tool needs. An item that fits none of these counts as tier 1.
- Regions: the nearest of the catalog's 11 regions, by an anchor tile each (a bank where the catalog names one,
  otherwise an estimate to verify), if within REGION_RADIUS tiles on the surface map (dungeons count at the surface
  tile above them); otherwise "elsewhere". Combat sites anywhere on the map mostly read "elsewhere".
- Candidate features: XP/hr is the sum over skills; gp/hr keeps its sign, 0.5 meaning 0; damage per hour is divided
  by the HP and food healing held and squashed to d / (1 + d); travel is over 15 game-minutes, clipped; open is 1
  for a filled slot (candidates are already eligible: Slayer, levels, access).
- Skilling candidates (rlscape.sim.skilling) use the same scales: the two XP/hr features split a path's XP between
  the gathering skill and the one that processes its produce (0 for paths that keep it, and for thieving).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from math import log1p

import numpy as np

from rlscape.combat.access import access_rules, unlocked_rules
from rlscape.combat.candidates import COMBAT_CLASSES, LOOT_MODES
from rlscape.gamedata import server as gd
from rlscape.sim.energy import MAX_ENERGY, weight
from rlscape.sim.health import food_healing_held, poison_cover
from rlscape.sim.potions import ALL_POTIONS, antifire_cover, doses_held
from rlscape.sim.mining import PICKAXE_PRIORITY
from rlscape.sim.options import Option
from rlscape.sim.skilling import K_GP, K_XP, SkillSlot
from rlscape.sim.skilling import SKILLS as SKILLING_SKILLS
from rlscape.sim.skills import MAX_LEVEL, SKILL_INDEX, SKILLS, XP_FOR_LEVEL, level_for_xp
from rlscape.sim.slots import K, FightSlot
from rlscape.sim.state import INVENTORY_SLOTS, CharacterState
from rlscape.sim.woodcutting import HATCHET_PRIORITY
from rlscape.travel import UNDERGROUND_Y_OFFSET

# The 19 trainable skills (env contract §5) and Slayer, in the server's skill order.
OBSERVED_SKILLS = tuple(s for s in SKILLS if s not in ("farming", "hunter", "construction", "summoning"))
MAX_TOTAL_LEVEL = 2376
WEALTH_SCALE = log1p(10_000_000)
INVENTORY_SCALE, BANK_SCALE = log1p(INVENTORY_SLOTS), log1p(10_000)
POTION_INVENTORY_SCALE = log1p(4 * INVENTORY_SLOTS)  # every slot a four-dose potion
MAX_WEIGHT = 100.0  # kg
XP_HR_SCALE, GP_HR_SCALE = log1p(1_000_000), log1p(1_000_000)
TRAVEL_SCALE_TICKS = 1_500  # 15 game-minutes, the default activity duration

# Equipment slots (EquipmentContainer)
HEAD, WEAPON, BODY, SHIELD, LEGS, AMMO = 0, 3, 4, 5, 7, 13
EQUIPMENT_ROLES = ("melee_weapon", "ranged_weapon", "staff", "ammunition", "head", "body", "legs", "shield", "axe",
                   "pickaxe", "fishing_gear")
METALS = ("bronze", "iron", "steel", "black", "mithril", "adamant", "rune", "dragon")
BOW_WOODS = ("", "oak", "willow", "maple", "yew", "magic")  # "" is the plain shortbow or longbow
STAFF_KINDS = ("staff", "staff of", "battlestaff", "mystic")

# The catalog's regions (option catalog, Regions) and an anchor tile each. Banks come from data/banks.csv; the rest
# are estimates to verify.
REGIONS = {
    "lumbridge": (3208, 3220),  # castle bank
    "lumbridge_swamp": (3228, 3150),  # copper and tin mine; estimate
    "lumbridge_farms": (3255, 3280),  # cow and chicken fields; estimate
    "draynor": (3092, 3243),  # Draynor bank
    "varrock": (3219, 3429),  # between the west and east banks
    "grand_exchange": (3164, 3487),  # GE bank
    "falador": (2980, 3363),  # between the east and west banks
    "barbarian_village": (3082, 3420),  # estimate
    "edgeville": (3094, 3493),  # Edgeville bank
    "al_kharid": (3269, 3168),  # Al Kharid bank
    "catherby": (2809, 3441),  # Catherby bank
}
REGION_RADIUS = 60  # tiles (Chebyshev)
CANDIDATE_FEATURES = ("xp_per_hour", "gp_per_hour", "damage_vs_food", "travel", "open")
SKILLING_FEATURES = ("gather_xp_per_hour", "process_xp_per_hour", "gp_per_hour", "travel", "open")
TASKS = ("none", "woodcutting", "mining", "fishing:SMALL_NET", "fishing:LURE", "fishing:LOBSTER_CAGE", "thieving",
         "fletching", "processing", "combat:melee", "combat:ranged", "combat:magic")


@dataclass(frozen=True)
class Part:
    name: str
    names: tuple[str, ...]  # one per feature


def _metal_tier(name: str) -> int | None:
    lower = name.lower()
    return next((i + 1 for i, metal in enumerate(METALS) if lower.startswith(metal + " ")), None)


def _bow_tier(name: str) -> int:
    lower = name.lower()
    return next((i + 1 for i, wood in enumerate(BOW_WOODS) if wood and lower.startswith(wood + " ")), 1)


def _staff_tier(name: str) -> int:
    lower = name.lower()
    if lower.startswith("mystic"):
        return 4
    if "battlestaff" in lower:
        return 3
    return 2 if lower.startswith("staff of") else 1


@cache
def _staves() -> frozenset[int]:
    elemental = frozenset().union(*gd.staff_runes().values())
    return elemental | {i for i, item in gd.items().items() if item.equipment_slot == WEAPON
                        and item.name.lower().endswith("staff")}


@cache
def _tool_tiers() -> dict[str, dict[int, int]]:
    """Role -> item -> tier, for the tool chains (worst tier 1) and fishing gear (the method's level)."""
    tools = gd.skilling_tools()
    chain = lambda priority: {tools[n].item: len(priority) - i for i, n in enumerate(priority) if n in tools}
    fishing: dict[int, int] = {}
    for method in gd.fishing_methods().values():
        fishing[method.tool] = max(fishing.get(method.tool, 0), method.level)
    return {"axe": chain(HATCHET_PRIORITY), "pickaxe": chain(PICKAXE_PRIORITY), "fishing_gear": fishing}


@cache
def _top_tiers() -> dict[str, int]:
    tools = _tool_tiers()
    return {"melee_weapon": len(METALS), "ranged_weapon": len(BOW_WOODS), "staff": len(STAFF_KINDS),
            "ammunition": len(METALS), "head": len(METALS), "body": len(METALS), "legs": len(METALS),
            "shield": len(METALS), "axe": max(tools["axe"].values()), "pickaxe": max(tools["pickaxe"].values()),
            "fishing_gear": max(tools["fishing_gear"].values())}


@cache
def item_roles(item: int) -> tuple[tuple[str, int], ...]:
    """(role, tier) for every equipment role the item fills."""
    definition, tools = gd.items().get(item), _tool_tiers()
    out = [(role, chain[item]) for role, chain in tools.items() if item in chain]
    if definition is None or definition.equipment_slot is None:
        return tuple(out)
    slot, name = definition.equipment_slot, definition.name
    metal = _metal_tier(name) or 1
    if slot == WEAPON:
        if item in gd.ranged_weapons():
            out.append(("ranged_weapon", _bow_tier(name)))
        elif item in _staves():
            out.append(("staff", _staff_tier(name)))
        else:
            out.append(("melee_weapon", metal))
    elif slot in (HEAD, BODY, LEGS, SHIELD, AMMO):
        out.append(({HEAD: "head", BODY: "body", LEGS: "legs", SHIELD: "shield", AMMO: "ammunition"}[slot], metal))
    return tuple(out)


def region_of(tile: tuple[int, int, int]) -> int:
    """Index into REGIONS, or len(REGIONS) for elsewhere."""
    x, y = tile[0], tile[1] - UNDERGROUND_Y_OFFSET if tile[1] >= UNDERGROUND_Y_OFFSET else tile[1]
    distance, index = min((max(abs(x - ax), abs(y - ay)), i) for i, (ax, ay) in enumerate(REGIONS.values()))
    return index if distance <= REGION_RADIUS else len(REGIONS)


def _signed_log(value: float, scale: float) -> float:
    return 0.5 + np.sign(value) * min(log1p(abs(value)) / scale, 1.0) / 2


class ObsEncoder:
    """Builds the observation for a catalog (the options, in action order) and vocabulary."""

    def __init__(self, options: Sequence[Option], vocabulary: Sequence[int] = (), horizon_ticks: int = 120_000,
                 preference: bool = False):
        self.vocabulary = tuple(sorted(set(vocabulary)))
        self.horizon_ticks = horizon_ticks
        self.preference = preference
        self.slots = next((o.slots for o in options if isinstance(o, FightSlot)), None)
        self.skilling = next((o.slots for o in options if isinstance(o, SkillSlot)), None)
        self.rules = tuple(rule.name for rule in access_rules())
        self._unlocked: dict = {}
        item_name = lambda i: gd.items()[i].name if i in gd.items() else str(i)
        slot_names = [f"{c}_{'xp' if i < K else 'gp'}{i % K + 1}" for c in COMBAT_CLASSES for i in range(2 * K)]
        parts = [
            Part("time", ("elapsed", "remaining")),
            Part("skills", tuple(f"{s}_{kind}" for s in OBSERVED_SKILLS for kind in ("level", "progress"))),
            Part("total_level", ("total_level",)),
            Part("hitpoints_prayer", ("hitpoints", "prayer")),
            Part("run_energy_weight", ("run_energy", "weight")),
            Part("wealth", ("coins", "net_worth")),
            Part("inventory", (*(f"inv_{item_name(i)}" for i in self.vocabulary), "free_slots")),
            Part("bank", tuple(f"bank_{item_name(i)}" for i in self.vocabulary)),
            Part("equipment", EQUIPMENT_ROLES),
            Part("region", (*REGIONS, "elsewhere")),
            Part("combat_candidates", tuple(f"{s}_{f}" for s in slot_names for f in CANDIDATE_FEATURES)),
            Part("skilling_candidates", tuple(f"{o.id}_{f}" for o in options if isinstance(o, SkillSlot)
                                              for f in SKILLING_FEATURES)),
            Part("loot_mode", tuple(f"loot_{m}" for m in LOOT_MODES)),
            Part("task", tuple(f"task_{t}" for t in TASKS)),
            Part("potions", tuple(f"{name}_doses_{where}" for name in ALL_POTIONS for where in ("inventory", "bank"))),
            Part("access", tuple(f"access_{r}" for r in self.rules)),
            Part("mask", tuple(f"mask_{o.id}" for o in options)),
        ]
        if preference:
            parts.append(Part("preference", ("w_skill", "w_wealth")))
        self.parts: dict[str, slice] = {}
        start = 0
        for part in parts:
            self.parts[part.name] = slice(start, start + len(part.names))
            start += len(part.names)
        self.names = tuple(n for part in parts for n in part.names)
        self.size = start

    def encode(self, state: CharacterState, mask: np.ndarray,
               weights: tuple[float, float] = (0.5, 0.5)) -> np.ndarray:
        obs = np.zeros(self.size, dtype=np.float32)
        p = self.parts
        obs[p["time"]] = (min(state.tick / self.horizon_ticks, 1.0), max(1 - state.tick / self.horizon_ticks, 0.0))
        obs[p["skills"]] = [v for s in OBSERVED_SKILLS for v in _skill(state.xp[SKILL_INDEX[s]])]
        obs[p["total_level"]] = state.total_level() / MAX_TOTAL_LEVEL
        obs[p["hitpoints_prayer"]] = (min(state.hp / state.max_hp(), 1.0), 1.0)
        obs[p["run_energy_weight"]] = (state.run_energy / MAX_ENERGY, min(max(weight(state), 0.0) / MAX_WEIGHT, 1.0))
        obs[p["wealth"]] = (min(log1p(state.coins()) / WEALTH_SCALE, 1.0),
                            min(log1p(max(state.net_worth(), 0.0)) / WEALTH_SCALE, 1.0))
        inventory, bank = p["inventory"], p["bank"]
        for j, item in enumerate(self.vocabulary):
            obs[inventory.start + j] = min(log1p(state.inventory.get(item, 0)) / INVENTORY_SCALE, 1.0)
            obs[bank.start + j] = min(log1p(state.bank.get(item, 0)) / BANK_SCALE, 1.0)
        obs[inventory.stop - 1] = state.free_slots() / INVENTORY_SLOTS
        obs[p["equipment"]] = self._equipment(state)
        obs[p["region"].start + region_of(state.location)] = 1.0
        obs[p["combat_candidates"]] = self._candidates(state)
        obs[p["skilling_candidates"]] = self._skilling(state)
        obs[p["loot_mode"].start + LOOT_MODES.index(state.loot_mode)] = 1.0
        obs[p["task"].start + TASKS.index(_task_key(state.task))] = 1.0
        obs[p["potions"]] = [min(log1p(doses_held(container, name)) / scale, 1.0) for name in ALL_POTIONS
                             for container, scale in ((state.inventory, POTION_INVENTORY_SCALE),
                                                      (state.bank, BANK_SCALE))]
        obs[p["access"]] = self._access(state)
        obs[p["mask"]] = mask
        if self.preference:
            obs[p["preference"]] = weights
        return obs

    def _equipment(self, state: CharacterState) -> list[float]:
        best = dict.fromkeys(EQUIPMENT_ROLES, 0)
        for item in (*state.inventory, *state.equipment.values()):
            for role, tier in item_roles(item):
                best[role] = max(best[role], tier)
        top = _top_tiers()
        return [best[role] / top[role] for role in EQUIPMENT_ROLES]

    def _candidates(self, state: CharacterState) -> list[float]:
        out = [0.0] * (len(COMBAT_CLASSES) * 2 * K * len(CANDIDATE_FEATURES))
        if self.slots is None:
            return out
        reserves = max(state.hp + food_healing_held(state), 1.0)
        # the poison and the breath the antipoison and antifire carried keep off
        cover, fire_cover = poison_cover(state, self.slots.duration_ticks), antifire_cover(state, self.slots.duration_ticks)
        n = 0
        for combat_class in COMBAT_CLASSES:
            for index in range(2 * K):
                candidate = self.slots.candidate(state, combat_class, index)
                if candidate is not None:
                    rates = candidate.rates
                    danger = (rates.damage_taken_per_hour - cover * rates.poison_per_hour
                              - fire_cover * rates.breath_per_hour) / reserves
                    out[n:n + len(CANDIDATE_FEATURES)] = (
                        min(log1p(sum(candidate.xp_per_hour.values())) / XP_HR_SCALE, 1.0),
                        _signed_log(candidate.gp_per_hour, GP_HR_SCALE),
                        danger / (1 + danger),
                        min(candidate.travel_ticks / TRAVEL_SCALE_TICKS, 1.0),
                        1.0)
                n += len(CANDIDATE_FEATURES)
        return out

    def _skilling(self, state: CharacterState) -> list[float]:
        out = [0.0] * (len(SKILLING_SKILLS) * (K_XP + K_GP) * len(SKILLING_FEATURES))
        if self.skilling is None:
            return out
        n = 0
        for skill in SKILLING_SKILLS:
            for index in range(K_XP + K_GP):
                candidate = self.skilling.candidate(state, skill, index)
                if candidate is not None:
                    rate = candidate.rate
                    out[n:n + len(SKILLING_FEATURES)] = (
                        min(log1p(rate.gather_xp) / XP_HR_SCALE, 1.0),
                        min(log1p(rate.process_xp) / XP_HR_SCALE, 1.0),
                        _signed_log(rate.gp, GP_HR_SCALE),
                        min(rate.travel / TRAVEL_SCALE_TICKS, 1.0),
                        1.0)
                n += len(SKILLING_FEATURES)
        return out

    def _access(self, state: CharacterState) -> list[float]:
        progress = state.access_progress()
        if progress not in self._unlocked:
            unlocked = unlocked_rules(progress)
            self._unlocked[progress] = [float(rule in unlocked) for rule in self.rules]
        return self._unlocked[progress]


def _task_key(task: str | None) -> str:
    if task is None:
        return "none"
    return "processing" if task.startswith("processing:") else task


def _skill(xp: float) -> tuple[float, float]:
    level = level_for_xp(xp)
    if level >= MAX_LEVEL:
        return 1.0, 0.0
    low, high = XP_FOR_LEVEL[level], XP_FOR_LEVEL[level + 1]
    return level / MAX_LEVEL, (xp - low) / (high - low)


__all__ = ["ObsEncoder", "item_roles", "region_of"]
