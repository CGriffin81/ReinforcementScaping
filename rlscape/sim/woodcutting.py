"""Woodcutting options, ported from the server's WoodcuttingListener with event-level sampling.

Server mechanics (content/global/skill/gather/woodcutting/WoodcuttingListener.kt):
- a swing every 3 ticks, and 4 after a swing that got a log (measured on the server, scripts/calibrate.py; the code
  doesn't show why); a swing succeeds if randomDouble(100) < getSkillSuccessChance(low, high, level), where
  low/high are the tree's base values plus the axe's enum ordinal times the tree's tier modifiers (halved for the
  black axe);
- each success gives one log and the tree's experience;
- after a log, normal trees fall every time and other trees 1 time in 8 (rollDepletion), then respawn after
  getRespawnDuration (rlscape.sim.gathering).

Sampling (rlscape.sim.gathering): the swings until the next log are one geometric draw; whether the tree falls is
one Bernoulli draw per log.

Not modelled yet: bird nests (1 in 282 per log). The sites' tree counts and their first and next attempts are
measured on the server (scripts/calibrate.py, 2026-10-31); their tiles are the original estimates, which the
measured first attempt accounts for.
"""

from __future__ import annotations

from math import floor

import numpy as np

from rlscape.gamedata import server as gd
from rlscape.sim.gathering import Site, gather_depleting, respawn_ticks
from rlscape.sim.options import Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import CharacterState

SWING_TICKS = 3  # delayClock(player, Clocks.SKILLING, 3) after every swing
AFTER_LOG_TICKS = 1  # the swing after a log comes a tick later (measured: 4 ticks in 180 of 185)
FELL_CHANCE = 1 / 8  # rollDepletion for trees other than normal and dead trees

# SkillingTool.getHatchet's priority, standard axes only (the class 1-5 hatchets are Dungeoneering-era items).
HATCHET_PRIORITY = ("DRAGON_AXE", "RUNE_AXE", "ADAMANT_AXE", "MITHRIL_AXE", "BLACK_AXE", "STEEL_AXE", "IRON_AXE",
                    "BRONZE_AXE")


def skill_success_chance(low: float, high: float, level: int) -> float:
    """RandomFunction.getSkillSuccessChance, as a probability in [0, 1]."""
    value = floor(low * ((99 - level) / 98.0)) + floor(high * ((level - 1) / 98.0)) + 1
    return min(max(value / 256.0, 0.0), 1.0)


def chop_chance(tree: gd.TreeType, tool: gd.SkillingTool, level: int) -> float:
    """WoodcuttingListener.checkReward: the chance that one swing gives a log."""
    halve = tool.name == "BLACK_AXE"
    low = tree.base_low + tool.ordinal * (tree.tier_mod_low / 2 if halve else tree.tier_mod_low)
    high = tree.base_high + tool.ordinal * (tree.tier_mod_high / 2 if halve else tree.tier_mod_high)
    return skill_success_chance(low, high, level)


def best_tool(state: CharacterState, priority: tuple[str, ...], skill: str) -> gd.SkillingTool | None:
    """SkillingTool.getHatchet / getPickaxe: the best tool held or worn that the skill's level allows."""
    tools, level = gd.skilling_tools(), state.level(skill)
    for name in priority:
        tool = tools[name]
        if level >= tool.level and state.holds(tool.item):
            return tool
    return None


def best_hatchet(state: CharacterState) -> gd.SkillingTool | None:
    return best_tool(state, HATCHET_PRIORITY, "woodcutting")


class Woodcutting(Option):
    family = "gathering"
    task = "woodcutting"

    def __init__(self, option_id: str, tree_identifier: int, site: Site):
        self.id = option_id
        self.tree = gd.tree_types()[tree_identifier]
        self.site = site

    def available(self, state: CharacterState) -> bool:
        return (state.level("woodcutting") >= self.tree.level and best_hatchet(state) is not None
                and state.free_slots() > 0)

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        tree, tool, wc = self.tree, best_hatchet(state), SKILL_INDEX["woodcutting"]

        def collect() -> None:
            state.add(tree.reward)
            state.xp[wc] = min(state.xp[wc] + tree.experience, MAX_XP)

        return gather_depleting(
            state, rng, budget, self.site, SWING_TICKS,
            chance=lambda: chop_chance(tree, tool, state.level("woodcutting")),
            collect=collect,
            depletes=lambda: tree.depletes and (tree.always_falls or rng.random() < FELL_CHANCE),
            respawn=respawn_ticks(tree.respawn_min, tree.respawn_max), after_success=AFTER_LOG_TICKS)


# Catalog §2. Tree identifiers are WoodcuttingNode's: 1 normal, 7 oak, 8 willow, 15 yew.
# The counts and attempt times are measured on the server (results/calibration/gathering-20261031-1319.json): the
# trees a character clicked there, and the mean ticks to the first swing and from a fall to the next swing.
CALIBRATED = "calibrated 2026-10-31 (scripts/calibrate.py)"
SITES = {
    "wc_logs": (1, Site((3190, 3235, 0), 14, f"tile: estimate, west of Lumbridge castle; {CALIBRATED}: 14 or more "
                        "trees", first_attempt=5, next_attempt=6)),
    "wc_oak": (7, Site((3103, 3245, 0), 3, f"tile: estimate, Draynor Village; {CALIBRATED}", first_attempt=13,
                       next_attempt=8)),
    "wc_willow": (8, Site((3087, 3232, 0), 4, f"tile: DraynorWillows.willowZone (3084-3091, 3225-3239); {CALIBRATED}",
                          first_attempt=2, next_attempt=5)),
    "wc_yew": (15, Site((3087, 3475, 0), 2, f"tile: estimate, south of Edgeville bank; {CALIBRATED}",
                        first_attempt=5, next_attempt=8)),
}


def woodcutting_options() -> list[Woodcutting]:
    return [Woodcutting(option_id, tree, site) for option_id, (tree, site) in SITES.items()]
