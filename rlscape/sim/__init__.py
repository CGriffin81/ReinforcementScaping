"""The surrogate simulator (sim v0): server formulas with event-level sampling, behind the env contract's step."""

from collections.abc import Iterable

from rlscape.sim.combat import ReclaimGravestone
from rlscape.sim.economy import inventory_options, selling_options
from rlscape.sim.engine import Simulator, StepResult
from rlscape.sim.fishing import fishing_options
from rlscape.sim.mining import mining_options
from rlscape.sim.options import Option, OptionResult
from rlscape.sim.processing import processing_options
from rlscape.sim.state import CharacterState
from rlscape.sim.thieving import pickpocket_options
from rlscape.sim.woodcutting import woodcutting_options


def build_catalog(vocabulary: Iterable[int] = ()) -> list[Option]:
    """The sim v0 action list, in action-id order (option catalog §2–§3 and §5–§7 so far). The per-item actions come
    from `vocabulary`; the catalog's V awaits Caleb's check, so the default is empty (misc actions only)."""
    return [*woodcutting_options(), *mining_options(), *fishing_options(), *pickpocket_options(),
            *processing_options(), *inventory_options(vocabulary), ReclaimGravestone(),
            *selling_options(vocabulary)]


__all__ = ["CharacterState", "Option", "OptionResult", "Simulator", "StepResult", "build_catalog"]
