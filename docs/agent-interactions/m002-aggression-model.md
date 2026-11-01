# Agent Interaction

## Metadata

- Interaction ID: m002-aggression-model
- Timestamp CST: 2026-10-31 16:17:06 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the bridge changes and the tolerance fix built and tested; aggressive monsters modelled in the sim
  and calibrated at the willows)
- Commit: fork `84102f9` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA can only be filled in by a later commit)

## Full Prompt

> Go ahead with both OQ-8 changes and OQ-9 option a

## Response Summary

- Fork: attackers in `state`; `interact` by NPC index; tolerance in game ticks; `debug_set_levels` recomputes the
  combat level (a bug: calibration characters looked level 3 to aggression).
- Measured aggression at the willows, built the sim's model of aggressive monsters at gathering sites with Caleb's
  rule, and the same rule in the server runner. A woodcutting-only character there: sim over server 0.95.

## Documentation Changes

- `docs/decision-log.md`; `docs/open-questions-log.md` (OQ-8 and OQ-9 answered, removed); `docs/option-catalog.md`
  §4; `docs/env-contract.md` v1.9, decision 25; `CLAUDE.md` (the tolerance fork change); `ROADMAP.md`; this record.

## Code Changes

- Fork (uncommitted): `content/rl/RLCommands.kt` (attackers, `index`, combat level in `debug_set_levels`);
  `core/game/world/map/Region.java`, `RegionManager.kt` (tolerance in ticks).
- `rlscape/sim/aggression.py` (new); `rlscape/sim/gathering.py`, `fishing.py` (the exposure); `rlscape/sim/state.py`
  (`combat_level`, `region_since`); `rlscape/sim/movement.py`, `combat.py` (region entry); `rlscape/combat/rates.py`
  (`npc_max_hit`); `rlscape/bridge/client.py` (`interact(index)`).
- `scripts/aggression_test.py` (new); `scripts/calibrate.py` (`Safety`, `--levels`).
- Tests: `tests/test_sim_aggression.py` (new, 5); `tests/test_bridge_inputs_live.py` (attackers by index,
  tolerance in ticks, combat level).

## Infrastructure Changes

- The server rebuilt and run; the earlier detached server process stopped by its PID.

## Decisions

- **User decisions:** OQ-8 (both), OQ-9 (a).
- **Agent choices (reversible):**
  - the sim doesn't move monsters: a site's aggressors attack at a measured rate
  - aggressors within 10 tiles of the site; only attackable ones with a combat level
  - the willows' rates for other sites until calibrated
  - healing back to twice the max hit before returning; leaving a site where that's beyond the max hitpoints
  - the skilling slots' rate model doesn't price aggression yet

## Validation

- `uv run pytest -q` with the server up: 272 passed; `uvx ruff check --select F401,F811,F841`: passed.
- Calibration and E1 as in the decision log.

## Follow-Up

- Mining with safespotting; then fishing, travel and banking.
- Commit when Caleb asks (the fork first).
