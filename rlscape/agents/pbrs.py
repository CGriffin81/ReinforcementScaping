"""Potential-based reward shaping for E6b (RQ4; ROADMAP §3, "PBRS in an SMDP"; env contract §4; Ng, Harada & Russell
1999). Each decision's reward gets

    F = γ_hr^τ · Φ(s′) − Φ(s)        (rlscape.agents.smdp.pbrs_bonus)

with γ_hr the agent's own discount per game-hour and τ the decision's duration, so the optimal policy is the unshaped
one's: shaping can change how fast and in what order strategies are found (RQ4), not which is best.

**The potential** (ROADMAP §3's candidate, "the best GP/hr the current unlocks allow"):

    Φ(s) = w_wealth · G(s) / 100,000 · A(hours left),    A(h) = ∫₀ʰ γ_hr^t dt = (1 − γ_hr^h) / −ln γ_hr

the discounted wealth reward that earning at the best gathering rate G(s) would bring in the time left (in the env's
reward units: r_wealth is Δ net worth / 100,000, weighted by w_wealth). A(0) = 0, so Φ at the episode's end is 0, as
the env contract has it, with no jump there.

- **G(s), the best gathering income** its levels and unlocks allow: the most gp/hr among the gathering methods
  (woodcutting, mining, fishing, thieving, picking flax), by the skilling slots' own rate model
  (rlscape.sim.skilling.path_rate) over the usual 15-minute option, for a *canonical* character. It
  - stands at the method's site, with the best tool its level allows (and bait) and an otherwise empty pack;
  - has its items and coins in the bank, where they still count for access (quests, items, coins and levels are
    what `access_progress` checks);
  - has the fresh character's combat stats and no armour, so a site's aggressive monsters are weighed as for it.
  So G, and Φ but for the clock, moves only when the character invests: a gathering level, or an unlock.
- **Left out**, so Φ doesn't move with every walk, purchase or meal: where the character stands, what it carries,
  its combat levels and gear, and the fights and processing paths, whose rates turn on food, ammunition and inputs
  held.
- **Cost:** a skill's best rate is kept per (skill, its level, the canonical character's access), each worked out
  once per process.
- **What a decision earns, shaped:** with G steady, F ≈ −w_wealth · G / 100,000 · τ, the wealth its best gathering
  would have earned meanwhile, so earning that much nets about 0; a level that raises G pays
  w_wealth · ΔG / 100,000 · A(hours left).

`PBRSShaping` wraps one SimEnv (in its own process under SubprocVecEnv). Its steps' infos carry `reward_extrinsic`
(the env's weighted reward), `r_shaping` (F) and `potential` (Φ(s′)), so the learning curve and the decision log keep
them apart (rlscape.agents.training's REWARD_PARTS).
"""

from __future__ import annotations

import math
from dataclasses import replace

import gymnasium as gym
import numpy as np

from rlscape.agents.smdp import TICKS_PER_HOUR, pbrs_bonus
from rlscape.gamedata import server as gd
from rlscape.sim.aggression import COMBAT_SKILLS
from rlscape.sim.crafting import PickFlax
from rlscape.sim.engine import ACTIVITY_TICKS, WEALTH_SCALE
from rlscape.sim.fishing import Fishing
from rlscape.sim.mining import PICKAXE_PRIORITY, Mining
from rlscape.sim.skilling import Path, _site, path_options, path_rate
from rlscape.sim.skills import SKILL_INDEX
from rlscape.sim.state import CharacterState
from rlscape.sim.thieving import Pickpocket, StealFromStall
from rlscape.sim.woodcutting import HATCHET_PRIORITY, Woodcutting

GATHERING = (Woodcutting, Mining, Fishing, Pickpocket, StealFromStall, PickFlax)
BAIT = 10_000  # the canonical character's bait: never the limit over a 15-minute option
POTENTIALS = ("gathering_income",)
KEYS = {"potential"}


def check_pbrs(pbrs: dict) -> None:
    unknown = sorted(set(pbrs) - KEYS)
    if unknown:
        raise ValueError(f"config: unknown pbrs keys {unknown}; known: {sorted(KEYS)}")
    if pbrs.get("potential") not in POTENTIALS:
        raise ValueError(f"config: pbrs.potential must be one of {POTENTIALS}")


def annuity(hours: float, gamma_hr: float) -> float:
    """∫₀ʰ γ_hr^t dt: the discounted length of `hours` game-hours."""
    if hours <= 0:
        return 0.0
    if gamma_hr >= 1.0:
        return float(hours)
    return (1.0 - gamma_hr ** hours) / -math.log(gamma_hr)


def _best_tool(priority: tuple[str, ...], level: int) -> gd.SkillingTool | None:
    tools = gd.skilling_tools()
    return next((tools[name] for name in priority if level >= tools[name].level), None)


class GatheringIncome:
    """G(s): the best gp/hr among the gathering methods, for the canonical character (the module's docstring)."""

    def __init__(self, duration_ticks: int = ACTIVITY_TICKS):
        self.duration_ticks = duration_ticks
        self.paths: dict[str, list[Path]] = {}
        for path in path_options():
            if type(path) is Path and path.process is None and isinstance(path.gather, GATHERING):
                self.paths.setdefault(path.skill, []).append(path)
        self.fresh = CharacterState.fresh()
        self._best: dict[tuple, float] = {}

    def canonical(self, state: CharacterState) -> CharacterState:
        """The character as G values it: its own levels but the fresh combat stats, everything it owns in the bank,
        nothing worn, full hitpoints, just arrived (no aggression tolerance yet)."""
        xp = list(state.xp)
        for skill in COMBAT_SKILLS:
            xp[SKILL_INDEX[skill]] = self.fresh.xp[SKILL_INDEX[skill]]
        bank = dict(state.bank)
        for item, amount in state.inventory.items():
            bank[item] = bank.get(item, 0) + amount
        for slot, item in state.equipment.items():
            bank[item] = bank.get(item, 0) + state.worn(slot)
        return CharacterState(tick=state.tick, xp=xp, hp=self.fresh.hp, inventory={}, bank=bank,
                              progress=state.progress, region_since=state.tick)

    def __call__(self, state: CharacterState) -> float:
        base = self.canonical(state)
        access = base.access_progress()
        return max((self.best(skill, base, access) for skill in self.paths), default=0.0)

    def best(self, skill: str, base: CharacterState, access) -> float:
        """A skill's best gathering gp/hr for the canonical character (0 if none pays), kept per its key."""
        key = (skill, base.level(skill), access)
        if key not in self._best:
            rates = [0.0]
            for path in self.paths[skill]:
                at = self._at(base, path)
                if at is not None and path.available(at) and (rate := path_rate(path, at, self.duration_ticks)):
                    rates.append(rate.gp)
            self._best[key] = max(rates)
        return self._best[key]

    def _at(self, base: CharacterState, path: Path) -> CharacterState | None:
        """The canonical character at the method's site, holding its tool (and bait)."""
        gather, inventory = path.gather, {}
        if isinstance(gather, (Woodcutting, Mining)):
            tool = _best_tool(HATCHET_PRIORITY if isinstance(gather, Woodcutting) else PICKAXE_PRIORITY,
                              base.level(path.skill))
            if tool is None:
                return None
            inventory[tool.item] = 1
        elif isinstance(gather, Fishing):
            inventory[gather.method.tool] = 1
            if gather.method.bait:
                inventory[gather.method.bait[0]] = BAIT
        return replace(base, inventory=inventory, location=_site(gather))


class Potential:
    """Φ(s) = w_wealth · G(s) / 100,000 · A(hours left) (the module's docstring)."""

    def __init__(self, gamma_hr: float, horizon_ticks: int, income: GatheringIncome | None = None):
        self.gamma_hr, self.horizon_ticks = float(gamma_hr), int(horizon_ticks)
        self.income = income or GatheringIncome()

    def __call__(self, state: CharacterState, wealth_weight: float) -> float:
        hours = (self.horizon_ticks - state.tick) / TICKS_PER_HOUR
        return wealth_weight * self.income(state) / WEALTH_SCALE * annuity(hours, self.gamma_hr)


class PBRSShaping(gym.Wrapper):
    """A SimEnv whose reward has F = γ_hr^τ · Φ(s′) − Φ(s) added; infos keep the env's reward and F apart."""

    def __init__(self, env: gym.Env, gamma_hr: float):
        super().__init__(env)
        sim = env.unwrapped.sim
        self.gamma_hr = float(gamma_hr)
        self.potential = Potential(gamma_hr, sim.horizon_ticks, GatheringIncome(sim.activity_ticks))
        self.phi = 0.0

    def _phi(self) -> float:
        env = self.env.unwrapped
        return self.potential(env.sim.state, env.weights[1])

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        self.phi = self._phi()
        return obs, {**info, "potential": self.phi}

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        phi_next = self._phi()
        shaping = float(pbrs_bonus(np.array([self.phi]), np.array([phi_next]), np.array([info["duration"]]),
                                   np.array([terminated or truncated]), self.gamma_hr)[0])
        self.phi = phi_next
        info = {**info, "reward_extrinsic": float(reward), "r_shaping": shaping, "potential": phi_next}
        return obs, float(reward) + shaping, terminated, truncated, info


def shaped_sim_env(gamma_hr: float, **sim_env_kwargs) -> PBRSShaping:
    """A training env for SubprocVecEnv's factories: SimEnv with E6b's shaping."""
    from rlscape.envs.sim_env import SimEnv
    return PBRSShaping(SimEnv(**sim_env_kwargs), gamma_hr)
