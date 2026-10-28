"""The surrogate simulator (sim v0): server formulas with event-level sampling, behind the env contract's step."""

from rlscape.sim.engine import Simulator, StepResult
from rlscape.sim.fishing import fishing_options
from rlscape.sim.mining import mining_options
from rlscape.sim.options import Option, OptionResult
from rlscape.sim.state import CharacterState
from rlscape.sim.thieving import pickpocket_options
from rlscape.sim.woodcutting import woodcutting_options


def build_catalog() -> list[Option]:
    """The sim v0 action list, in action-id order (option catalog §2 so far). It grows family by family."""
    return [*woodcutting_options(), *mining_options(), *fishing_options(), *pickpocket_options()]


__all__ = ["CharacterState", "Option", "OptionResult", "Simulator", "StepResult", "build_catalog"]
