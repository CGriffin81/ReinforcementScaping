"""The simulator's step: run one option, advance game time, and report the reward and info (env contract §1, §4, §6).

This is the backend SimEnv wraps. It knows nothing about observations or Gymnasium; that layer comes once enough
option families exist to make an action space worth encoding.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np

from rlscape.sim.energy import rest
from rlscape.sim.combat import die
from rlscape.sim.health import regenerate
from rlscape.sim.options import COMPLETED, DIED, HORIZON, Option
from rlscape.sim.skills import SKILLS
from rlscape.sim.state import CharacterState

HORIZON_TICKS = 120_000  # 20 game-hours
CHECKPOINT_TICKS = 12_000  # every 2 game-hours
ACTIVITY_TICKS = 1_500  # D = 15 game-minutes (decided); 5 and 45 minutes for the E5 ablation
WEALTH_SCALE = 100_000  # r_wealth = Δ net worth / 100,000 gp
TICKS_PER_HOUR = 6_000


@dataclass(frozen=True)
class StepResult:
    reward_vec: tuple[float, float]  # (r_skill, r_wealth), unweighted
    terminated: bool  # never true: death respawns the character and the episode carries on (env contract §1)
    truncated: bool  # the horizon was reached
    info: dict


def _delta(after: dict[int, int], before: dict[int, int]) -> dict[int, int]:
    return {item: after.get(item, 0) - before.get(item, 0) for item in after.keys() | before.keys()
            if after.get(item, 0) != before.get(item, 0)}


class Simulator:
    def __init__(self, options: Sequence[Option], activity_ticks: int = ACTIVITY_TICKS,
                 horizon_ticks: int = HORIZON_TICKS):
        self.options = list(options)
        self.activity_ticks = activity_ticks
        self.horizon_ticks = horizon_ticks
        self.state: CharacterState | None = None
        self.rng: np.random.Generator | None = None

    def reset(self, seed: int | None = None) -> CharacterState:
        self.rng = np.random.default_rng(seed)
        self.state = CharacterState.fresh()
        return self.state

    def action_mask(self) -> np.ndarray:
        return np.array([option.available(self.state) for option in self.options], dtype=bool)

    def step(self, action: int) -> StepResult:
        state, option = self.state, self.options[action]
        if not option.available(state):
            raise ValueError(f"option {option.id!r} is masked in this state")  # contract: never a silent no-op
        measure, worth, tick = state.skill_measure(), state.net_worth(), state.tick
        xp, inventory, bank = list(state.xp), dict(state.inventory), dict(state.bank)

        budget = min(self.activity_ticks, self.horizon_ticks - tick)
        state.dropped, state.energy_clock = {}, 0
        if state.gravestone is not None and state.tick >= state.gravestone.expires_at:
            state.gravestone = None  # crumbled: its items are gone
        result = option.run(state, self.rng, budget)
        if option.task is not None:
            state.task = option.task
        if not 1 <= result.ticks <= budget:
            raise RuntimeError(f"option {option.id!r} took {result.ticks} ticks with a budget of {budget}")
        if not result.regenerated:
            regenerate(state, result.ticks)
        if state.hp <= 0:  # poison, in an option that doesn't fight (fights handle their own deaths)
            die(state, state.tick + result.ticks)
            result = replace(result, termination=DIED)
        rest(state, result.ticks - state.energy_clock)  # run energy: the ticks not spent walking
        state.tick += result.ticks
        truncated = state.tick >= self.horizon_ticks
        termination = HORIZON if truncated and result.termination == COMPLETED else result.termination

        info = {
            "duration": result.ticks,
            "reward_vec": (state.skill_measure() - measure, (state.net_worth() - worth) / WEALTH_SCALE),
            "option": {"id": option.id, "action": action, **(result.detail or {})},
            "termination": termination,
            "game_ticks": state.tick,
            "total_level": state.total_level(),
            "total_xp": state.total_xp(),
            "net_worth": state.net_worth(),
            "coins": state.coins(),
            "xp_gained": {SKILLS[i]: state.xp[i] - xp[i] for i in range(len(SKILLS)) if state.xp[i] != xp[i]},
            "items_delta": {"inventory": _delta(state.inventory, inventory), "bank": _delta(state.bank, bank),
                            "dropped": dict(state.dropped)},
        }
        # Checkpoints crossed during the option, measured at its end (options last at most D, so the lag is small).
        crossed = range(tick // CHECKPOINT_TICKS + 1, state.tick // CHECKPOINT_TICKS + 1)
        if crossed:
            info["checkpoints"] = {k * CHECKPOINT_TICKS // TICKS_PER_HOUR: {
                "total_level": info["total_level"], "total_xp": info["total_xp"], "net_worth": info["net_worth"]}
                for k in crossed}
        return StepResult(info["reward_vec"], False, truncated, info)
