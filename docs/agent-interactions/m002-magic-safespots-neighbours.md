# Agent Interaction

## Metadata

- Interaction ID: m002-magic-safespots-neighbours
- Timestamp CST: 2026-11-07 23:17:39 CST, from the session transcript's message timestamp (UTC−06:00); the work ran
  into 2026-11-08
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (built and measured; one new question for Caleb, OQ-36)
- Commit: fork `1a36c9e` (branch `rl`) and the main repo commit after `21365bd` (branch `sim-v0`), both pushed

## Full Prompt

> 35 - a
> 34 - yes

## Response Summary

- **Recorded:** OQ-34 (yes: magic safespots as ranged does) and OQ-35 (a) (model monsters of other kinds near a
  fight), moved to the decision log.
- **The safespot table, re-exported** at ranges 7, 9 and 10 from the current fork:
  - one table from one server version; the old one predated the leash fix;
  - a first pass lost 90 sites to the export character's deaths; it now refills its hitpoints, and a second pass
    left 4 unanswered;
  - usable safespots: 207, 375 and 460.
- **Magic safespots:** in both rankers, the fight and the runner.
- **Monsters near a fight:**
  - From the server's rule, aggressive monsters pick only a character not "in combat", so they engage between
    kills.
  - Rate measured at the spades: 0.047 per exposed tick from the traces, 0.045 fitted.
  - Modelled in the sim's fight (each engagement a full kill) and both rankers (expected value, kept identical).
  - A fight with no neighbours is unchanged.
- **Runner:** melee and ranged characters attack an attacker back at once. On this server eating stops the fight,
  and waiting for retaliation cost 8 ticks an eat.
- **Results, sim over server XP/hr:**
  - magic fit set 0.97 to 1.12;
  - magic check set 0.95 to 1.03, except a low-share magic safespot at 1.31 (OQ-36);
  - beside neighbours 0.99, 1.17 and 1.28.
- **New question OQ-36:** a stricter share for usable safespots (recommended: 0.8), or the step race modelled.

## Documentation Changes

- `docs/decision-log.md`:
  - "Decided: OQ-34, magic safespots as ranged does; OQ-35 (a), monsters of another kind near a fight are
    modelled";
  - "Built: magic safespots (OQ-34) and monsters near a fight (OQ-35 (a)); the safespot table re-exported; the
    runner attacks back".
- `docs/open-questions-log.md`: OQ-34 and OQ-35 removed (answered); OQ-36 added.
- `docs/env-contract.md`: v1.18 (to confirm), §8's safespot and neighbour rows, decisions 31 and 32.
- `docs/option-catalog.md`: magic safespots; monsters near a fight.
- `ROADMAP.md`: the status line.
- This record.

## Code Changes

- `rlscape/combat/neighbours.py` (new): `site_aggressors` (moved), `site_neighbours`, `engaging`,
  `aggression_ticks`, `exposed_per_kill`, `ENGAGE_PER_TICK`, `NeighbourKill`, `with_neighbours`;
  `TOLERANCE_TICKS` moved here (re-exported by `rlscape.sim.state`).
- `rlscape/combat/safespots.py`: `MAGIC_TILES`, `SAFESPOT_RANGES`, `distance_class`; `style_range` for magic.
- `rlscape/combat/candidates.py`:
  - `Character.combat_level` and `tolerance_left`;
  - `Neighbours` and `neighbour_kills`;
  - `site_rates` with magic safespots and the neighbour load;
  - the site choice compared rounded.
- `rlscape/combat/ranking.py`: magic safespot arrays; neighbour rows, caches and per-site load; the same rounding;
  `_candidate` with the reference's neighbours.
- `rlscape/sim/combat.py`:
  - `FightNeighbours`;
  - `fight` refactored around one `kill` for a target or a neighbour;
  - magic safespots.
- `rlscape/sim/aggression.py`: uses the shared `site_aggressors`.
- `rlscape/sim/slots.py`: the combat level and tolerance left.
- `scripts/export_ranged_safespots.py`: range 10, the hitpoints refill.
- `scripts/calibrate_combat.py`:
  - attacking back;
  - other kinds' engagements counted;
  - a caster on a safespot casts only on held monsters.
- `tests/test_neighbours.py` (new, 7).

## Infrastructure Changes

- `data/ranged_safespots.csv`: re-exported, 6,555 rows (three ranges).
- Three server instances (`scripts/server_instances.py 2 3`, fresh jar copies) for the export and the runs; all
  stopped after, by PID.
- Results:
  - `results/calibration/combat-20261107-neighbours.json`;
  - `combat-20261108-spiders-clickback.json`;
  - `combat-20261108-0019-i3.json` (magic fit set);
  - `combat-20261108-0017-slot3-valuable.json` (magic check set).

## Decisions

- **User decisions:** OQ-34 yes; OQ-35 (a).
- **Agent choices (reversible):**
  - the engagement rate's form (per neighbour spawn, per exposed tick) and its fit at one site;
  - neighbours by NPC id;
  - an unfightable neighbour rules out the site while aggression lasts;
  - the runner attacking back;
  - the export's hitpoints refill;
  - the rounded site comparison.

## Validation

- Offline: 312 passed. With the server up: 367 passed.
- The earlier magic fit set re-simulated: the cases without neighbours to the same numbers.
- The calibration runs above.

## Follow-Up

- Caleb:
  - OQ-36;
  - env contract v1.18 (and whether v1.17's confirmation covers v1.11 and v1.14 to v1.16).
- Next: the willows' aggression rates; OQ-17's scope review today (Sunday 2026-11-08).
- Commit when Caleb asks (fork first, then the submodule pointer).
