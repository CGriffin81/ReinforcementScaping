# Agent Interaction

## Metadata

- Interaction ID: m002-speed-checks
- Timestamp CST: 2026-11-09 08:58:25 CST (the prompt), from the session transcript's timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (43 of 43 agree)
- Commit: None (uncommitted)

## Full Prompt

> Go ahead with the speed checks

## Response Summary

- **Ran the gate's 600 ms speed check (OQ-21)** for sim v1's calibrations, on instances 4 to 7, one script per server.
  Each case ran at 50 ms and then at 600 ms:

  | Instance | Cases |
  |---|---|
  | 4 | Crafting's 14 cases |
  | 5 | Herblore's 9 |
  | 6 | Runecrafting's 8 ruins and the tiaras, then 30 whole Abyss trips |
  | 7 | the Abyss's fitted fight case |

- **Taught `scripts/speed_check.py` these files:**
  - timings for the loads, the ruins and the tiaras;
  - paired server-over-sim ratios for the Abyss trips;
  - food an hour for combat.

  Timings agree within 2 standard errors, or within 5% where the runs have no spread. Rerun on the two earlier
  checks' files, it reproduces them.
- **A restart of Claude Code stopped all four servers** mid-run. Herblore, the ruins and tiaras, and the fight had
  finished. Crafting and the Abyss trips were rerun at 600 ms on instances 4 and 6.
- **Result: 43 of 43 agree.**
  - Every load, ruin and tiara takes the same ticks at both speeds (1.00), except picking flax (1.01).
  - The Abyss trips: 0.99.
  - The guardians' fight: 1.02 on XP/hr and 1.03 on food/hr.

## Documentation Changes

- `docs/decision-log.md`: "Measured: the gate's 600 ms speed check passes for Crafting, Herblore and Runecrafting
  (OQ-21)".
- `ROADMAP.md`:
  - the freeze item says the speed checks pass;
  - week 3's "Sim v1, before E2" is ticked.
- This record.

## Code Changes

- `scripts/speed_check.py`:
  - the new file shapes: `compare_runecrafting`, `compare_abyss_trips`, Crafting and Herblore's `case_id` cases, and
    combat's food rows;
  - `compare_means` with a floor, and `TIMING_TOLERANCE`;
  - the docstring lists every kind and its rule.

## Infrastructure Changes

- `scripts/server_instances.py 4 5 6 7`: the current jar copied, and the frozen GE reinstalled. Each instance's old
  database is kept as a `.bak`.
- **Servers started:**
  - instances 4 to 7 (PIDs 15476, 13124, 10816, 19576), which the restart stopped;
  - instances 4 and 6 again (PIDs 19044, 15228), stopped by PID after their reruns.

  No java was running at the end.
- `results/calibration/abyss-fight-speed-cases.json`: the guardians' case alone (git-ignored).
- **Results** (git-ignored, in `results/calibration/`):
  - `crafting-20261109-0907-i4` and `-1021-600ms-i4`;
  - `herblore-20261109-0905-i5` and `-0925-600ms-i5`;
  - `runecrafting-20261109-0904-i6` and `-0925-600ms-i6`;
  - `abyss-20261109-0907-i6` and `-1009-600ms-i6`;
  - `combat-20261109-0905-i7` and `-0926-600ms-i7`;
  - `speed-check-20261109-1021`.

## Decisions

- **User decision (Caleb):** run the speed checks.
- **Agent choices (reversible):**
  - the cases: every Crafting, Herblore and ruin case, all the runes' Abyss trips, and the one fitted Abyss fight;
  - the timing rule (2 standard errors, or 5% without spread);
  - pairing each Abyss trip with the sim's estimate for its landing.

## Validation

- **The rewritten script against the earlier files:**
  - `speed-check-20261106-1959`'s pairs: 20 of 20, the old 18 plus two new food rows;
  - `speed-check-20261108-2331`'s: 11 of 11.
- **The 50 ms sides** match the earlier calibrations: the Abyss trips 0.97 sim over server, the ruins 0.84 to 1.02,
  the tiaras 1.02.

## Follow-Up

- **The freeze:** Caleb confirms env contract v1.38 (OQ-52).
- **Then:** the guide's extension (OQ-53), the mask speed-up and `train.py`.
