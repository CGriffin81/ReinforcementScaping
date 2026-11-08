"""Ranged fights from safespots, and their arrow piles (Caleb, 2026-11-07, OQ-27 (d)).

Rangers safespot: they stand where they can shoot a monster that, chasing them, gets stuck where none of its attacks
reach (a fence or wall holds a melee monster; a long-ranged bow outranges a skeletal wyvern). A monster without one
is a bad ranged target unless the damage it does is trivial. So:
- a ranged plan needs a safespot at the site unless the monster's damage is trivial: the fight needs no food, its
  expected damage over the option less the hitpoints regenerated meanwhile fitting in those above the retreat point
  (`needs_safespot`; Caleb, 2026-11-07, OQ-30 (b));
- the safespot is the site's best from the server (gd.ranged_safespots, the bridge's ranged_safespots exported by
  scripts/export_ranged_safespots.py), for the style's range (RangeSwingHandler.canSwing: 7, long-ranged 9). It
  counts when it holds from at least MIN_SHARE of the monsters' wandering (attacked at their spawn, where they
  respawn, it always holds); from it the monster deals nothing, and the site's supply is the monsters it holds
  against;
- arrows land where the monster stands when hit (RangeSwingHandler.useAmmo), and join a pile only while it's
  private, its first PILE_PRIVATE_TICKS (GroundItemManager.increase): a pile per PILE_PRIVATE_TICKS of a kill
  (`piles_per_kill`). Ground items last GROUND_TICKS;
- they're picked up between kills, a pickup a pile (rates.PICKUP_TICKS), with a walk from the safespot to them and
  back (`trip_ticks`: the export's walk each way, at WALK_TILES_PER_TICK); without a safespot the monster dies
  beside the character, and the walk is in the pickup time. When aggressive monsters guard the piles and aggression
  hasn't run out, the walk would take hits, so the fight waits, picking them up just before the oldest would go
  (rlscape.sim.combat). The rankers take a trip after every kill.
"""

from __future__ import annotations

from math import ceil

from rlscape.combat import formulas as f
from rlscape.combat.rates import EAT_BELOW_FRACTION, REGEN_TICKS, TICKS_PER_HOUR, Plan, Rates
from rlscape.gamedata import server as gd

RANGE_TILES = 7  # RangeSwingHandler.canSwing: the accurate and rapid styles
LONGRANGE_TILES = 9  # long-ranged: 2 more
MIN_SHARE = 0.5  # of the monsters' wandering a safespot must hold from (an agent choice)
PILE_PRIVATE_TICKS = 100  # GroundItem: private to its dropper for its first 100 ticks, when increase() still joins it
GROUND_TICKS = 200  # then public until it goes, 200 ticks after it was dropped
WALK_TILES_PER_TICK = 1  # the walk to the arrows and back, a tile a tick (short walks barely run; an agent choice)


def style_range(plan: Plan) -> int:
    return LONGRANGE_TILES if plan.style == f.LONGRANGE else RANGE_TILES


def fighting_ticks(rates: Rates, overhead: float) -> float:
    """A kill's fighting, without finding and reaching the monster."""
    return max(rates.ticks_per_kill - overhead, 0.0)


def needs_safespot(rates: Rates, hp_margin: float, duration: float) -> bool:
    """Whether a ranged fight needs a safespot: it would need food (OQ-30 (b)). The monster's expected damage over the
    option's `duration` (poison and breath included), less the hitpoints regenerated meanwhile, is more than
    `hp_margin`, the hitpoints above the retreat point."""
    return rates.damage_taken_per_hour * duration / TICKS_PER_HOUR - duration / REGEN_TICKS > hp_margin


def hp_margin(current_hp: float, max_hp: float) -> float:
    """The hitpoints above the retreat point (rlscape.sim.health.retreat_hp)."""
    return max(current_hp - EAT_BELOW_FRACTION * max_hp, 0.0)


def safespot(npc_id: int, site: tuple[int, int, int], plan: Plan) -> gd.RangedSafespot | None:
    """The site's usable safespot for the plan's range, if any."""
    spot = gd.ranged_safespots().get((npc_id, site, style_range(plan)))
    return spot if spot is not None and spot.share >= MIN_SHARE else None


def piles_per_kill(fight_ticks: float) -> int:
    """Arrow piles a kill leaves where the monster stands: one per PILE_PRIVATE_TICKS of shooting."""
    return max(1, ceil(fight_ticks / PILE_PRIVATE_TICKS))


def trip_ticks(spot: gd.RangedSafespot | None) -> float:
    """The walk from the safespot to the arrows and back (none without a safespot)."""
    if spot is None or spot.walk is None:
        return 0.0
    return 2 * spot.walk / WALK_TILES_PER_TICK
