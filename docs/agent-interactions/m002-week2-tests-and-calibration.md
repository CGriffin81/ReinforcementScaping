# Agent Interaction

## Metadata

- Interaction ID: m002-week2-tests-and-calibration
- Timestamp CST: 2026-10-31 12:56:00 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (the week-2 tests and benchmark done; calibration's first slice done; the rest of calibration waits
  for bridge commands, OQ-4)
- Commit: fork `84102f9` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA can only be filled in by a later commit)

## Full Prompt

> Keep going with the week-2 tests and calibration

## Response Summary

- **Tests:** whole random episodes never break the mask or the counts; trajectories repeat across processes.
- **Benchmark:** 804 decisions a second with 16 workers after caching the nearest bank, against the contract's
  20k. Raised as OQ-7.
- **Calibration, woodcutting at the site:** the server swings 4 ticks after a log; the sites' first and next
  swings and tree counts are measured and now in the sim. Every case is within ±20%, willow over the runs that
  finished.
- **Found:** ambient bots were on in `rl.conf`, against the 2026-10-28 decision; now off. The runner gets stuck on a
  willow out of reach, and needs a click-by-tile or walk-packet command (added to OQ-4).
- **Guide:** a Firemaking stall the new rates exposed, fixed like Smithing's fallback.

## Documentation Changes

- `docs/decision-log.md`, `docs/open-questions-log.md` (OQ-4 extended, OQ-7 new), `ROADMAP.md` (week-2 items and
  status), `CLAUDE.md` (`rl.conf` has bots off).
- This record.

## Code Changes

- `tests/test_sim_properties.py` (new): five property tests.
- `scripts/benchmark_sim.py` (new), `scripts/calibrate.py` (new).
- `rlscape/sim/economy.py`: `nearest_bank` cached on what a walk depends on.
- `rlscape/sim/gathering.py`: `Site.first_attempt`, `Site.next_attempt`, `site_offsets`; `gather_depleting`'s
  `after_success`.
- `rlscape/sim/woodcutting.py`: `AFTER_LOG_TICKS`; the sites' measured counts and times.
- `rlscape/sim/skilling.py`: the rate model's replay uses the same.
- `rlscape/baselines/guide.py`: Firemaking chops and burns when it has no logs.
- `tests/test_sim.py`: the ticks-per-log test counts the extra tick.

## Infrastructure Changes

- Fork (`server/`, branch `rl`, uncommitted): `worldprops/rl.conf` sets `enable_bots = false`.
- The server was run for calibration and the live tests.

## Decisions

- **User decisions:** none new; turning the bots off applies Caleb's 2026-10-28 decision.
- **Agent choices (reversible):**
  - calibration's first slice is the activity at the site, with the band's best standard tool given at setup
    rather than bought on the GE (env contract §7 has calibration characters buy it; the GE trip isn't measured)
  - the sites' times are the measured means, kept with each site
  - the runner re-clicks within two ticks of going idle, as a person would
  - willow's comparison is over the runs that finished
  - the guide's Firemaking fallback
- **Awaiting Caleb:** OQ-4 (bridge commands, now blocking calibration), OQ-7 (speed).

## Validation

- `uv run pytest -q` with the server up: 258 passed. The live tests again after turning the bots off: 28 passed.
- `uvx ruff check --select F401,F811,F841 rlscape tests scripts`: passed.
- Calibration results as in the decision log.

## Follow-Up

- Caleb's answers to OQ-4 and OQ-7.
- Then fishing and mining at their sites, travel and banking.
- Commit when Caleb asks (the fork first).
