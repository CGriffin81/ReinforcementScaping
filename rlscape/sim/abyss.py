"""The Abyss (sim v1, Runecrafting part 4; Caleb, 2026-11-08, OQ-2 Choice H: "Include The Abyss"). The spec is
docs/sim-v1-skills-draft.md §5; the server's AbyssPlugin.kt, as rlscape.bridge.abyss describes it.

A trip through it, from beside the Mage of Zamorak (north of Edgeville, Wilderness level 5):
- the mage's teleport (TELEPORT_TICKS, measured) lands the character on the outer ring in one of twelve segments,
  each as likely (AbyssLoc.randomLoc's angle is uniform), drains its prayer and skulls it for SKULL_TICKS;
- the segment sets which kind each of the twelve obstacles shows (scripts/export_abyss.py's layouts, measured), and
  the character takes the obstacle that gets it to the rift soonest on average: the walk to it, the expected tries
  and the walk from the inner ring's landing behind it to the rift (the planner's steps on the server's collision
  map, rlscape.gamedata.runecrafting.abyss), from the kinds it can use. The passage always lets it through; rocks
  need a pickaxe and tendrils an axe, worn (getTool looks in the equipment too, and the trip's inventory is all
  essence); a boil's tinderbox must be carried, so it isn't used; eyes and a gap need nothing. A try passes with
  chance (level + 1) / 100 in the obstacle's skill, takes PASS_TICKS when it does and FAIL_TICKS when it doesn't;
- the abyssal leeches, guardians and walkers (2263-2265) attack it while it's on the outer ring, at ATTACKS_PER_TICK
  between them, each kind as its spawns over its attack speed, those its combat level allows (a character's combat
  level at most twice the monster's); each attack rolls the monster's hit chance and max hit against it, with no
  prayer (rlscape.combat.rates.npc_offence). When its hitpoints fall under twice the hardest hit there, it eats the
  food it carries (Caleb's gathering rule's line), EAT_TICKS each, the attacks going on. Hitpoints at 0 kill it,
  skulled: nothing is kept (DeathTask.getContainers) and no gravestone is made (GraveController.allowGenerate);
- the rift (RIFT_TICKS) lands it inside the rune's ruins, as entering them does (Altar.enterRift); chaos's rift lands
  it beside the altar, past the maze (AbyssPlugin's exit-through).
Walks are the planner's steps, timed as the travel model times walks (rlscape.sim.movement.timed: running with run
energy, and the travel walker's measured overhead for its clicks along a route), as a long walk round the ring takes
a person several minimap clicks.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import cache

import numpy as np

from rlscape.combat.rates import NO_FLICKS, npc_offence
from rlscape.gamedata import runecrafting as rcd
from rlscape.gamedata import server as gd
from rlscape.sim.aggression import GATHERING_STANCE
from rlscape.sim.combat import die
from rlscape.sim.energy import RUN_TILES
from rlscape.sim.equipment import fighter_for
from rlscape.sim.health import EAT_TICKS, eat_one
from rlscape.sim.mining import best_pickaxe
from rlscape.sim.movement import timed
from rlscape.sim.state import CharacterState
from rlscape.sim.woodcutting import best_hatchet
from rlscape.travel import overhead

MAGE_TILE = (3105, 3554, 0)  # the Mage of Zamorak's spawn (npc_spawns.json)
SEGMENTS = 12
SKULL_TICKS = 2000  # AbyssPlugin.teleport: spawnTimer<Skulled>(2000)
# Measured on the server (scripts/measure_abyss.py, 2026-11-08, 30 trips at 50 ms; results/calibration/abyss-*):
TELEPORT_TICKS = 3  # beside the mage, its Teleport clicked, to landing (the 3-tick lock, the 2-tick pulse; 0.94)
PASS_TICKS = 14  # walked to beside an obstacle, a try that passes to standing on the inner ring: the click, the
# 8-tick lock and the move on its seventh tick (fitted: 6.1 over the walk's timing and the lock)
FAIL_TICKS = 7  # a try that fails, to the next clicked as its fail shows (7 between tries, every time)
PASSAGE_TICKS = 5  # walked to beside the passage, its Go-through to the inner ring (fitted: it moves at once)
RIFT_TICKS = 6  # walked to beside a rift, its Exit-through to landing inside the ruins (fitted: 3.6 over the walk's
# timing and 2, spread 0.74, over 132 walks from the twelve inner landings to the eleven rifts; 1.02)
# Attacks on the character a tick on the outer ring, all its attackers together, from landing to the inner ring:
# fitted to the hitpoints 30 trips lost at combat level 50, which all three kinds draw (0.40 a tick at Defence 99),
# as the sim's damage a swing is the server's (standing there: 634 hitpoints against the sim's 636 over 678 swings;
# 1.13 swings a tick over 150 ticks standing, as more gather). Shared by the kinds as their spawns over their attack
# speeds (counted standing: leeches 54%, guardians 26%, walkers 20%; the rule's 54, 22, 24)
ATTACKS_PER_TICK = 0.43
ABYSSAL = (2263, 2264, 2265)  # AbyssalNPC: leech, guardian, walker
CHAOS_LANDING = (2269, 4840, 0)  # AbyssPlugin's chaos exit-through: beside the altar, past the maze
# kind -> the skill its tries roll (None: always passes)
KIND_SKILL = {"rocks": "mining", "tendrils": "woodcutting", "boil": "firemaking", "eyes": "thieving",
              "gap": "agility", "passage": None}


def pass_chance(state: CharacterState, kind: str) -> float:
    """A try's chance: (level + 1) / 100 in its skill (AbyssPlugin.handleObstacle's RandomFunction.random(100) <
    level + 1); the passage, 1."""
    skill = KIND_SKILL[kind]
    return 1.0 if skill is None else min((state.level(skill) + 1) / 100, 1.0)


def usable(state: CharacterState, kind: str) -> bool:
    """Whether the character can try the obstacle as the trip carries it: rocks with a worn pickaxe its Mining allows,
    tendrils with a worn axe; a boil's tinderbox would take an essence's slot, so not; the rest always."""
    if kind == "rocks":
        tool = best_pickaxe(state)
        return tool is not None and tool.item in state.equipment.values()
    if kind == "tendrils":
        tool = best_hatchet(state)
        return tool is not None and tool.item in state.equipment.values()
    return kind in ("eyes", "gap", "passage")


def expected_pass_ticks(state: CharacterState, kind: str) -> float:
    if kind == "passage":
        return PASSAGE_TICKS
    p = pass_chance(state, kind)
    return PASS_TICKS + (1 - p) / p * FAIL_TICKS


def walk_ticks(steps: float) -> float:
    """A walk's ticks, running, with the walker's overhead: for planning (a trip's own walks use the run energy it
    has, `_walk`)."""
    return steps / RUN_TILES + overhead(steps)


@dataclass(frozen=True)
class Crossing:
    """The obstacle a trip takes from a segment's landing to a rift: its place (index into the Abyss's places), its
    kind, and the expected ticks of the walk to it, the tries and the walk from behind it to the rift."""

    place: int
    kind: str
    outer_steps: float
    inner_steps: float
    outer: float  # expected ticks on the outer ring: the walk and the tries
    expected: float  # and the walk to the rift, and the rift


def best_crossing(state: CharacterState, segment: int, rune: str) -> Crossing:
    """The usable obstacle that gets the character from the segment's landing to the rune's rift soonest on
    average."""
    a = rcd.abyss()
    out = None
    for i, kind in enumerate(a.layouts[segment]):
        if kind == "blocked" or not usable(state, kind):
            continue
        outer_steps, inner_steps = a.outer_steps[segment][i], a.inner_steps[i][rune]
        outer = walk_ticks(outer_steps) + expected_pass_ticks(state, kind)
        expected = outer + walk_ticks(inner_steps) + RIFT_TICKS
        if out is None or expected < out.expected:
            out = Crossing(i, kind, outer_steps, inner_steps, outer, expected)
    assert out is not None, "the passage is always usable"
    return out


def expected_crossing_ticks(state: CharacterState, rune: str) -> float:
    """The mean over the twelve segments of the best crossing's expected ticks, teleport included."""
    return TELEPORT_TICKS + sum(best_crossing(state, v, rune).expected for v in range(SEGMENTS)) / SEGMENTS


def crossing_damage(state: CharacterState, rune: str) -> tuple[float, int]:
    """A crossing's expected damage on the outer ring, and the hardest hit of the monsters that attack the
    character (0 when none does)."""
    outer = sum(best_crossing(state, v, rune).outer for v in range(SEGMENTS)) / SEGMENTS
    drawn = _drawn(state)
    return ATTACKS_PER_TICK * mean_damage(state) * outer, max((m for *_, m in drawn), default=0)


@cache
def _attack_mix() -> tuple[tuple[gd.Npc, int, float], ...]:
    """The three abyssal monsters, their combat levels (the definitions', which aggression compares) and their shares
    of the attacks: their spawns (npc_spawns.json) over their attack speeds."""
    spawns, npcs, definitions = gd.spawns(), gd.npcs(), gd.npc_definitions()
    weights = {i: len(spawns.get(i, [])) / npcs[i].attack_speed for i in ABYSSAL}
    total = sum(weights.values())
    return tuple((npcs[i], definitions[i].combat_level, weights[i] / total) for i in ABYSSAL)


def _drawn(state: CharacterState) -> list[tuple[gd.Npc, float, float, int]]:
    """The kinds the character's combat level draws (a character at most twice the monster's level:
    AggressiveBehavior), each with its share of the attacks and its hit chance and max hit against the character, with
    no prayer."""
    level, fighter = state.combat_level(), replace(fighter_for(state), flicks=NO_FLICKS)
    out = []
    for npc, npc_level, share in _attack_mix():
        if level <= 2 * npc_level:
            chance, max_hit, _, _ = npc_offence(fighter, GATHERING_STANCE, npc)
            out.append((npc, share, chance, max_hit))
    return out


def mean_damage(state: CharacterState) -> float:
    """The mean damage of one of the outer ring's attacks of the whole mix (0 for a kind that doesn't attack)."""
    return sum(share * chance * max_hit / 2 for _, share, chance, max_hit in _drawn(state))


def _attacked(state: CharacterState, rng: np.random.Generator, ticks: float, now: int) -> tuple[bool, int]:
    """The outer ring's attacks over `ticks` from `now`, in time order: each monster kind the character's combat
    level draws attacks at its share of ATTACKS_PER_TICK, with no prayer. Under twice the hardest hit, it eats what it
    carries, which keeps it there longer. (Whether it died, skulled; the ticks it spent eating.)"""
    drawn = _drawn(state)
    if not drawn:
        return False, 0
    shares = np.array([share for _, share, _, _ in drawn])
    rate, hardest = ATTACKS_PER_TICK * shares.sum(), max(m for *_, m in drawn)
    t, end, eating = 0.0, float(ticks), 0
    while True:
        t += rng.exponential(1 / rate)
        if t >= end:
            return False, eating
        _, _, chance, max_hit = drawn[int(rng.choice(len(drawn), p=shares / shares.sum()))]
        if rng.random() < chance:
            state.hp -= int(rng.integers(0, max_hit + 1))
            if state.hp <= 0:
                die(state, now + int(t))
                return True, eating
        while state.hp < 2 * hardest and eat_one(state):
            end += EAT_TICKS
            eating += EAT_TICKS


def _walk(state: CharacterState, steps: float) -> int:
    """Walk the steps as walks are timed (movement.timed); the ticks taken."""
    ticks, energy = timed(state, [(steps, 0)])
    state.run_energy = energy
    return round(ticks)


@dataclass
class Trip:
    """One trip through the Abyss: the ticks it took, whether the character died on the outer ring, and the
    obstacle it took (for the decision log)."""

    ticks: int
    died: bool
    kind: str
    tries: int
    segment: int


def cross(state: CharacterState, rng: np.random.Generator, rune: str, at: int = 0) -> Trip:
    """From beside the mage, `at` ticks into the option, to landing inside the rune's ruins (state.location: the
    ruins' landing, or chaos's beside its altar), or to a death on the outer ring (state.location: the respawn)."""
    now = state.tick + at
    elapsed = TELEPORT_TICKS
    state.skulled_until = now + elapsed + SKULL_TICKS
    segment = int(rng.integers(SEGMENTS))
    crossing = best_crossing(state, segment, rune)
    outer = _walk(state, crossing.outer_steps)
    tries = 1
    if crossing.kind == "passage":
        outer += PASSAGE_TICKS
    else:
        p = pass_chance(state, crossing.kind)
        tries = int(rng.geometric(p))
        outer += (tries - 1) * FAIL_TICKS + PASS_TICKS
    died, eating = _attacked(state, rng, outer, now + elapsed)
    outer += eating
    if died:
        return Trip(elapsed + outer, True, crossing.kind, tries, segment)
    elapsed += outer + _walk(state, crossing.inner_steps) + RIFT_TICKS
    state.location = CHAOS_LANDING if rune == "chaos" else rcd.ruins()[rune].end
    return Trip(elapsed, False, crossing.kind, tries, segment)
