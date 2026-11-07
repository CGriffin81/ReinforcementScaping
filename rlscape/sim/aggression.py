"""Aggressive monsters at gathering sites (Caleb, 2026-10-31; decision log and OQ-8, OQ-9).

On the server (AggressiveHandler, AggressiveBehavior, Region): an aggressive monster picks a character within 4
tiles of it whose combat level is at most twice its own, unless the character has spent TOLERANCE_TICKS in that map
region (the rl fork counts game ticks; the server counted wall-clock minutes). Caleb's rule for a gathering
character:
- auto-retaliate is off, so attacks don't stop the gathering (checked live at Draynor's willows);
- it fights a monster only if that's trivial: its setup's max hit is at least half the monster's hitpoints, and the
  monster's max hit is under a quarter of its hitpoints as the fight starts;
- when its hitpoints fall under twice the attacker's max hit, it runs out of the monster's aggressive range, eats
  (or waits for its hitpoints to come back) until that's no longer so, and walks back.

The sim doesn't move monsters. A site's aggressors are the aggressive monsters spawned within SITE_REACH tiles of
its tile; the ones the character's combat level allows attack it while it gathers, as the site's measured exposure
(SiteExposure, measured with the server runner following the same rule, safespotting included) has it:
- engaged throughout, attacks spread at a rate per aggressor (`attack_rate`, or ATTACKS_PER_TICK, the willows'
  (scripts/calibrate.py, 2026-10-31): a Dark wizard there attacks about once every 29 ticks, much less often than its
  attack speed, since it often can't reach the character from where it wanders);
- or engagements (`engage_rate` per aggressor, while none is attacking): the monster then attacks every `cadence`
  ticks until the character runs, and goes on as it runs. Only one at a time: single-way combat. Draynor's shrimp
  spots, where nothing blocks the Dark wizards (measured 2026-11-01: a cast every 5 ticks, every engagement ending
  in a run away). An engagement under way outlasts the tolerance, which only stops new ones.
Each attack rolls the monster's own hit chance and max hit against the character (rlscape.combat.rates.npc_offence,
with its flicked prayers). Running away and back costs the site's flee time (FLEE_TICKS at the willows), plus the
eating or waiting, and the attacks taken as it runs (the site's measured `chase`, their mean number; none were seen
at the willows), which can kill it. Safespotting isn't modelled as a move: it's in the measured rates, as the attacks
it prevents.

While a site has aggressors for the character, this keeps the option's hitpoint regeneration itself, so a wait for
hitpoints to come back heals as it goes; the option then reports `regenerated`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache

import numpy as np

from rlscape.combat import formulas as f
from rlscape.combat.rates import Plan, npc_offence, player_offence
from rlscape.gamedata import server as gd
from rlscape.sim.combat import die, kill_sequence
from rlscape.sim.equipment import fighter_for
from rlscape.sim.health import EAT_TICKS, REGEN_TICKS, eat_one, regenerate
from rlscape.sim.skills import MAX_XP, SKILL_INDEX
from rlscape.sim.state import CharacterState

TOLERANCE_TICKS = 1000  # Region.TOLERANCE_TICKS
SITE_REACH = 10  # tiles from a site's tile to an aggressor's spawn (Draynor's wizards spawn 8 from the willows)
ATTACKS_PER_TICK = 1 / 29  # per aggressor, while gathering (measured at the willows; elsewhere to calibrate)
FLEE_TICKS = 129  # running out of reach and back, beyond eating (measured at the willows, 4 flees; to calibrate)
GATHERING_STANCE = Plan("melee", f.ACCURATE)  # how a gathering character defends, and fights a trivial monster


@dataclass(frozen=True)
class Aggressor:
    npc: gd.Npc
    level: int  # the combat level the server compares with the character's (the NPC definition's)


@cache
def site_aggressors(tile: tuple[int, int, int]) -> tuple[Aggressor, ...]:
    """The aggressive monsters spawned within SITE_REACH tiles of a site's tile, one per spawn. Only attackable ones
    with a combat level: the config marks some others aggressive (a Draynor banker), which never pick anyone."""
    npcs, definitions, out = gd.npcs(), gd.npc_definitions(), []
    for npc_id, spawns in gd.spawns().items():
        npc, definition = npcs.get(npc_id), definitions.get(npc_id)
        if npc is None or not npc.aggressive or definition is None or not definition.attackable                 or definition.combat_level <= 0:
            continue
        for x, y, z in spawns:
            if z == tile[2] and max(abs(x - tile[0]), abs(y - tile[1])) <= SITE_REACH:
                out.append(Aggressor(npc, definitions[npc_id].combat_level))
    return tuple(out)


@dataclass(frozen=True)
class SiteExposure:
    """A site's measured exposure to its aggressive monsters (scripts/calibrate.py); None fields take the willows'."""

    attack_rate: float | None = None  # attacks a tick per aggressor, engaged throughout
    flee_ticks: int | None = None  # running out of reach and back, beyond eating or waiting
    chase: float = 0.0  # mean attacks taken while running away
    engage_rate: float | None = None  # engagements a tick per aggressor, while none attacks (instead of attack_rate)
    cadence: float | None = None  # ticks between an engaged monster's attacks


@dataclass
class Exposure:
    """A gathering option's exposure to its site's aggressive monsters, on the option's own clock (ticks into the
    option). `active` is empty when none would pick the character; then nothing here touches the state or the rng."""

    state: CharacterState
    rng: np.random.Generator
    active: list[Aggressor]
    site: SiteExposure = SiteExposure()
    engaged: Aggressor | None = None  # the monster attacking, with engagements
    died_at: int | None = None  # ticks into the option, if the character died
    clock: int = 0  # ticks into the option the hitpoint regeneration has reached
    keeps_regeneration: bool = False  # set when there are aggressors, for the whole option
    abandoned: bool = False  # it can't heal out of danger here (twice the max hit is beyond its max hitpoints)
    counts: dict[str, int] = field(default_factory=lambda: {"attacks": 0, "hits": 0, "flees": 0, "fights": 0})

    @classmethod
    def at(cls, state: CharacterState, tile: tuple[int, int, int], rng: np.random.Generator,
           site: SiteExposure | None = None) -> Exposure:
        """The exposure at a site's tile, as the site's measured exposure has it."""
        level = state.combat_level()
        active = [a for a in site_aggressors(tile) if level <= 2 * a.level]
        return cls(state, rng, active, site or SiteExposure(), keeps_regeneration=bool(active))

    @property
    def rate(self) -> float:
        return ATTACKS_PER_TICK if self.site.attack_rate is None else self.site.attack_rate

    @property
    def flee_ticks(self) -> int:
        return FLEE_TICKS if self.site.flee_ticks is None else self.site.flee_ticks

    def _next_attack(self, t: float, end: int, tolerated: int) -> tuple[float, Aggressor] | None:
        """The next attack after `t` and its monster, or None if none comes before `end` (memoryless: the next
        stretch draws again)."""
        site, n = self.site, len(self.active)
        if site.engage_rate is None:  # engaged throughout
            t += self.rng.exponential(1 / (self.rate * n))
            if t >= min(end, tolerated):
                return None
            return t, self.active[int(self.rng.integers(n))]
        if self.engaged is None:
            t += self.rng.exponential(1 / (site.engage_rate * n))
            if t >= min(end, tolerated):
                return None
            self.engaged = self.active[int(self.rng.integers(n))]
        t += self.rng.exponential(site.cadence)
        return (t, self.engaged) if t < end else None

    def _attacked(self, chance: float, max_hit: int, at: int) -> bool:
        """One attack, `at` ticks into the option; True if it killed the character."""
        self.counts["attacks"] += 1
        damage = int(self.rng.integers(0, max_hit + 1)) if self.rng.random() < chance else 0
        if damage:
            self.counts["hits"] += 1
            self.state.hp -= damage
        if self.state.hp > 0:
            return False
        self.died_at = at
        die(self.state, self.state.tick + at)
        return True

    def _advance(self, to: int) -> None:
        if to > self.clock:
            regenerate(self.state, to - self.clock)
            self.clock = to

    def gather(self, start: int, end: int) -> int | None:
        """The attacks during gathering from `start` to `end` ticks into the option, and what Caleb's rule makes of
        them: the extra ticks it takes (trivial fights, running away and back), or None if the character died (at
        `died_at`)."""
        if not self.active:
            return 0
        tolerated = self.state.region_since + TOLERANCE_TICKS - self.state.tick  # ticks into the option
        t, extra = float(start), 0
        while self.active:
            attack = self._next_attack(t, end, tolerated)
            if attack is None:
                break
            t, aggressor = attack
            self._advance(int(t) + extra)
            fighter = fighter_for(self.state)
            chance, max_hit, _, _ = npc_offence(fighter, GATHERING_STANCE, aggressor.npc)
            p_chance, p_max, speed, _, xp_per_damage = player_offence(fighter, GATHERING_STANCE, aggressor.npc, True)
            if p_max >= aggressor.npc.hitpoints / 2 and max_hit < 0.25 * self.state.hp:  # trivial: fight it
                attacks = len(kill_sequence(aggressor.npc.hitpoints, p_chance, p_max, self.rng))
                extra += int(attacks * speed)
                for skill, rate in xp_per_damage.items():
                    i = SKILL_INDEX[skill]
                    self.state.xp[i] = min(self.state.xp[i] + rate * aggressor.npc.hitpoints, MAX_XP)
                self.active.remove(aggressor)
                self.engaged = None
                self.counts["fights"] += 1
                continue
            if self._attacked(chance, max_hit, int(t) + extra):
                return None
            if self.state.hp < 2 * max_hit:  # dangerous: out of its range, heal, back
                self.counts["flees"] += 1
                self.engaged = None
                for _ in range(self.rng.poisson(self.site.chase)):  # attacked as it runs
                    if self._attacked(chance, max_hit, int(t) + extra + self.flee_ticks // 4):
                        return None
                if 2 * max_hit > self.state.max_hp():  # never safe here: leave the site
                    self.abandoned = True
                    return extra + self.flee_ticks // 2
                extra += self.flee_ticks
                self._advance(int(t) + extra)
                while self.state.hp < 2 * max_hit and eat_one(self.state):
                    extra += EAT_TICKS
                if self.state.hp < 2 * max_hit:  # no food left: wait for hitpoints to come back
                    wait = (2 * max_hit - int(self.state.hp)) * REGEN_TICKS
                    extra += wait
                self._advance(int(t) + extra)
        return extra

    def finish(self, ticks: int) -> bool:
        """At the option's end: regenerate up to it, if this kept the regeneration. Returns OptionResult's
        `regenerated`."""
        if not self.keeps_regeneration:
            return False
        self._advance(ticks)
        return True
