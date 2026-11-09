# Agent Interaction

## Metadata

- Interaction ID: m002-herblore-times
- Timestamp CST: 2026-11-08 20:43:14 CST, from the session transcript's message timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: DONE (Herblore calibrated on the server; Herblore is built)
- Commit: the earlier work is main repo `ff2fce1` (branch `sim-v0`), pushed; this turn's calibration went into the Runecrafting
  session's whole-tree commit after it, at Caleb's request there

## Full Prompt

> Commit and push the changes, then continue with implementation.

## Response Summary

- **Committed and pushed:** main repo `ff2fce1` (Herblore's inputs in *V* and on the GE, the bird's nest at 1,765 gp).
  Staged by explicit paths: the Agility and Runecrafting sessions' uncommitted files were left out.
- **Built: `scripts/calibrate_herblore.py`**, Herblore's server calibration: each stage alone (cleaning, unfinished
  potions, finished ones, grinding) and two whole loads, a person's clicks against the sim's times. 9 cases, 3 runs, on
  Claude's own instance 7.
- **Found:** the times from the server's source and the assumed 3-tick start hold (1.00). Cleaning was a tick slower:
  the first herb a tick after the first click.
- **Fitted:** `CLEAN_FIRST`; every case 1.00.
- **Working beside the other sessions:** the Agility session had uncommitted edits in `skilling.py`. Claude messaged
  it before a three-line edit to the Herblore import and `_herb_rate`, made so as to keep its lines.

## Documentation Changes

- `docs/decision-log.md`: "Measured (sim v1, Herblore): the server's times; cleaning's first tick fitted, every case
  1.00".
- `docs/sim-v1-skills-draft.md` §7; `ROADMAP.md`: the status line.
- This record; the Commit field of `m002-herblore-inputs` (before the commit).

## Code Changes

- `scripts/calibrate_herblore.py` (new).
- `rlscape/sim/herblore.py`: `CLEAN_FIRST`, `clean_ticks`, used by the paths and `load_ticks`; the docstring on the
  measured times.
- `rlscape/sim/skilling.py`: `_herb_rate` uses `clean_ticks` (the file also holds the Agility session's uncommitted
  lines).
- **Tests:** `tests/test_sim_herblore.py`: the measured times.

## Infrastructure Changes

- Server instance 7 (`scripts/server_instances.py 7`, bridge 43616) with a fresh frozen GE. Its jar was the main
  checkout's build (`df2b8a6` with the Agility session's inert `at` filter). Stopped at the end, by its PID.

## Decisions

- **User decisions:** none new.
- **Agent choices (reversible):** the fitted first tick of cleaning (measured).

## Validation

- The calibration: before the fit 1.00 for every stage but cleaning (1.04 on XP/hr), loads 1.01 and 1.02; after it
  every case 1.00. The server's 3 runs a case were identical.
- `tests/test_sim_herblore.py`: 7 passed.

## Follow-Up

- Caleb: env contract v1.24 to v1.27 and catalog v1.4 (to confirm); OQ-17's scope review; OQ-43; OQ-45.
- Commit when Caleb asks: `skilling.py` holds the Agility session's uncommitted lines too, so it goes in with theirs
  or waits for them.
