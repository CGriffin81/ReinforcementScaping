"""Mining options, ported from the server's MiningListener with event-level sampling.

Server mechanics (content/global/skill/gather/mining/MiningListener.kt):
- an attempt every 4 ticks on ordinary rocks (getDelay); the first comes after one delay too;
- an attempt succeeds if Math.random() * (100 * rate) < Math.random() * ((1 + level - rock level) * (1 + pickaxe
  ratio)), i.e. one uniform roll racing another (uniform_race gives the exact probability);
- every ore empties the rock (respawnRate != 0); it respawns after getRespawnDuration (rlscape.sim.gathering);
- each ore also gives a gem 1 time in 282 (RandomFunction.roll), uniformly one of sapphire, emerald, ruby or
  diamond: GEM_REWARDS.random() ignores the drop frequencies listed beside them. With a full inventory the gem is
  dropped.

Site tiles and rock counts are estimates to verify on the server, except the coal tile, which is the CoalMiner bot's
Dwarven Mine zone.
"""

from __future__ import annotations

import numpy as np

from rlscape.gamedata import server as gd
from rlscape.sim.gathering import Site, gather_depleting, respawn_ticks
from rlscape.sim.options import Option, OptionResult
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import CharacterState
from rlscape.sim.woodcutting import best_tool

ATTEMPT_TICKS = 4  # MiningListener.getDelay for every rock except rune essence
GEM_CHANCE = 1 / 282
GEMS = (1623, 1621, 1619, 1617)  # MiningListener.GEM_REWARDS: uncut sapphire, emerald, ruby, diamond
# SkillingTool.getPickaxe's priority, standard pickaxes only.
PICKAXE_PRIORITY = ("RUNE_PICKAXE", "ADAMANT_PICKAXE", "MITHRIL_PICKAXE", "STEEL_PICKAXE", "IRON_PICKAXE",
                    "BRONZE_PICKAXE")


def uniform_race(a: float, b: float) -> float:
    """P(U(0, a) < U(0, b)) for independent uniforms."""
    if b <= 0:
        return 0.0
    if a <= 0:
        return 1.0
    return b / (2 * a) if b <= a else 1 - a / (2 * b)


def mine_chance(rock: gd.RockType, tool: gd.SkillingTool, level: int) -> float:
    """MiningListener.checkReward: the chance that one attempt gives an ore."""
    return uniform_race(100.0 * rock.rate, (1 + level - rock.level) * (1.0 + tool.ratio))


def best_pickaxe(state: CharacterState) -> gd.SkillingTool | None:
    return best_tool(state, PICKAXE_PRIORITY, "mining")


class Mining(Option):
    family = "gathering"

    def __init__(self, option_id: str, rock_identifier: int, site: Site):
        self.id = option_id
        self.rock = gd.rock_types()[rock_identifier]
        self.site = site

    def available(self, state: CharacterState) -> bool:
        return state.level("mining") >= self.rock.level and best_pickaxe(state) is not None and state.free_slots() > 0

    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        rock, tool, mining = self.rock, best_pickaxe(state), SKILL_INDEX["mining"]

        def collect() -> None:
            state.add(rock.reward)
            state.xp[mining] = min(state.xp[mining] + rock.experience, MAX_XP)
            if rng.random() < GEM_CHANCE:
                state.add(GEMS[rng.integers(len(GEMS))])  # silently lost with a full inventory, as on the server

        return gather_depleting(
            state, rng, budget, self.site, ATTEMPT_TICKS,
            chance=lambda: mine_chance(rock, tool, state.level("mining")),
            collect=collect,
            depletes=lambda: True,
            respawn=respawn_ticks(rock.respawn_min, rock.respawn_max))


# Catalog §2. Rock identifiers are MiningNode's: 1 copper, 2 tin, 6 iron, 8 coal.
SITES = {
    "mine_copper": (1, Site((3228, 3147, 0), 3, "estimate, Lumbridge Swamp east mine; verify")),
    "mine_tin": (2, Site((3226, 3146, 0), 3, "estimate, Lumbridge Swamp east mine; verify")),
    "mine_iron": (6, Site((3286, 3368, 0), 3, "estimate, Varrock south-east mine; verify")),
    "mine_coal": (8, Site((3040, 9738, 0), 8, "tile: CoalMiner.mine zone (3027-3054, 9733-9743); count: estimate")),
}


def mining_options() -> list[Mining]:
    return [Mining(option_id, rock, site) for option_id, (rock, site) in SITES.items()]
