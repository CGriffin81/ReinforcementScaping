"""Run energy and weight (option catalog §8; buying decision Q3b in docs/decision-log.md), from the server's
WalkingQueue and Settings.

- Weight (Settings.updateWeight): each inventory slot's item once, so a stack counts once, and only when it weighs
  more than nothing; plus every worn item, negative weights included (boots of lightness). Banknotes weigh nothing.
- Running (WalkingQueue.update): with run on, a tick covers 2 tiles and drains 0.55 × (1 + kg / 100)% energy
  (getEnergyDrainRate; weight at or below 0 kg leaves it at 0.55). Before each step, energy under 1% turns run off.
- Every other tick, walking or standing still, restores 0.6 × 100 / (175 − Agility)% energy (getEnergyRestore), up
  to 100%. At Agility 1 that's about 0.34% a tick, so empty to full takes about 290 ticks (3 minutes).
- Death restores it to 100% (Player.finalizeDeath).

Walks: run is turned on at the start of every walk, as a person would (on the server, the bridge's `set_run`). The
walk runs until energy drops under 1%; the server then turns run off, and the rest of the walk is walked at 1 tile a
tick. Stairs and ladders count as rest. An option's other ticks restore energy (`rest`): the engine applies them at
the end of the step, and a walk applies the ones before it, so a second walk in one option starts from the energy it
would really have.
"""

from __future__ import annotations

from collections.abc import Iterable
from math import floor

from rlscape.gamedata import server as gd
from rlscape.sim.state import CharacterState
from rlscape.travel import LEVEL_CHANGE_TICKS

MAX_ENERGY = 100.0
RUN_THRESHOLD = 1.0  # WalkingQueue: run turns off when energy is under 1
BASE_DRAIN = 0.55  # % per running tick
RUN_TILES = 2  # tiles a running tick covers; walking covers 1


def weight(state: CharacterState) -> float:
    """The character's weight in kg, as Settings.updateWeight counts it."""
    items, stackable = gd.items(), gd.stackable_items()
    total = 0.0
    for item, amount in state.inventory.items():
        kg = items[item].weight if item in items else 0.0
        if kg > 0:
            total += kg * (1 if item in stackable else amount)  # one slot per unit unless it stacks
    return total + sum(items[item].weight for item in state.equipment.values() if item in items)


def drain_per_run_tick(kg: float) -> float:
    return BASE_DRAIN * (1 + kg / 100) if kg > 0 else BASE_DRAIN


def restore_per_tick(agility: int) -> float:
    return 100 / ((175 - agility) / 0.6)


def rest(state: CharacterState, ticks: int) -> None:
    """`ticks` without running: restore energy."""
    if ticks > 0 and state.run_energy < MAX_ENERGY:
        state.run_energy = min(MAX_ENERGY, state.run_energy + ticks * restore_per_tick(state.level("agility")))


def walk_plan(state: CharacterState, legs: Iterable[tuple[float, int]]) -> tuple[float, float]:
    """Ticks to walk the legs in order, each (tiles, changes of level), and the energy left at the end. Run starts on
    and, once energy runs out, stays off for the rest of the walk. The state isn't changed."""
    energy, drain = state.run_energy, drain_per_run_tick(weight(state))
    gain = restore_per_tick(state.level("agility"))
    running, ticks = energy >= RUN_THRESHOLD, 0.0
    for tiles, level_changes in legs:
        # Run steps happen while energy is at least 1 before the step: the first, then one per `drain` above 1. The
        # tolerance keeps exact quotients (99 / 0.55 = 180) from rounding down.
        run_steps = floor((energy - RUN_THRESHOLD) / drain + 1e-9) + 1 if running else 0
        if run_steps * RUN_TILES >= tiles:
            run_ticks, walk_ticks = tiles / RUN_TILES, 0.0
        else:
            run_ticks, walk_ticks, running = float(run_steps), tiles - run_steps * RUN_TILES, False
        resting = walk_ticks + level_changes * LEVEL_CHANGE_TICKS
        energy = min(max(energy - run_ticks * drain, 0.0) + resting * gain, MAX_ENERGY)
        ticks += run_ticks + resting
    return ticks, energy
