"""The option interface every simulated option implements, and the termination reasons (env contract §6)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from rlscape.sim.state import CharacterState

COMPLETED = "completed"  # a one-shot option finished, or an activity used its whole time budget
INVENTORY_FULL = "inventory_full"
INPUTS_EXHAUSTED = "inputs_exhausted"
OUT_OF_FOOD = "out_of_food"
OUT_OF_AMMO = "out_of_ammo"
RESOURCES_EXHAUSTED = "resources_exhausted"
DIED = "died"
HORIZON = "horizon"  # set by the engine, never by an option


@dataclass(frozen=True)
class OptionResult:
    ticks: int  # game time the option took, travel included; never more than the budget it was given
    termination: str
    regenerated: bool = False  # the option applied hitpoint regeneration itself; otherwise the engine does


class Option(ABC):
    """One action in the catalog. `run` mutates the state (items, XP, location) but not `state.tick`; the engine
    advances time by the returned ticks."""

    id: str
    family: str

    @abstractmethod
    def available(self, state: CharacterState) -> bool:
        """The option's precondition: its entry in the action mask."""

    @abstractmethod
    def run(self, state: CharacterState, rng: np.random.Generator, budget: int) -> OptionResult:
        """Run until a termination condition or until `budget` ticks are used up (then COMPLETED)."""
