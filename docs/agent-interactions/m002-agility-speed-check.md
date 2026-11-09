# Agent Interaction

## Metadata

- Interaction ID: m002-agility-speed-check
- Timestamp CST: 2026-11-08 23:01:54 CST, from the session transcript's message timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab), the Agility session, beside the Herblore and Runecrafting sessions in the
  same checkout
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: DONE (the shortcuts committed and pushed; Agility's speed check run, passing)
- Commit: the shortcuts are main repo `5ae37d4` (branch `sim-v0`), pushed; this turn's speed check is the main repo
  commit after `5ae37d4`, pushed when Caleb asked (`m002-agility-wrapup`)

## Full Prompt

> Commit and push the changes, then continue with implementation.

## Response Summary

- **Committed and pushed:** `5ae37d4`, the Agility shortcuts (this session's 13 files only). The Herblore session's
  `fc41eab` landed first, while this session's "committing now" message was still queued. The staged docs were
  checked against the new HEAD, so none of its hunks went in.
- **Next, the gate's speed check (OQ-21 (a)) for Agility's three calibrations.** None of the sim v1 families had a
  600 ms check. Agility's cases ran at 50 and 600 ms on instance 5: the three courses, Barbarian Fishing and the
  shortcut trips. **11 of 11 agree:**
  - laps 1.00 to 1.01;
  - Barbarian Fishing 1.06, within the noise;
  - every shortcut trip the same to the tick.
- **Found and fixed:** `BridgeClient.set_tick_ms` returned the new tick, so nine scripts (all three sessions')
  never set the server's tick back. Fixed in the client; no script changes.
- **Found:** five scripts at once on one server put 1 to 3 ticks into 5 of 7 shortcut trips. Run alone, they
  matched to the tick. So timing measurements are best run one script per server.

## Documentation Changes

- `docs/decision-log.md`: "Measured: the gate's speed check passes for Agility's calibrations (OQ-21); `set_tick_ms`
  never set the tick back".
- `ROADMAP.md`: the status line.
- This record; the Commit field of `m002-agility-shortcuts` (before the commit).

## Code Changes

- `rlscape/bridge/client.py`: `set_tick_ms` reads the tick first and returns the one it replaced.
- `scripts/speed_check.py`: reads a course's laps (`measure_agility.py`) and Barbarian Fishing's per-skill XP
  (`calibrate_barbfishing.py`); one label function for every kind, other case shapes by their fields (Crafting's and
  Herblore's files read, checked on two of Herblore's).
- `scripts/calibrate_barbfishing.py`: `--case FISHING AGILITY STRENGTH` (repeatable) runs only those levels.
- **Tests:** `tests/test_bridge_client_live.py` (new): `set_tick_ms` returns the tick it replaced. The cause was
  shown on the server first: the bridge answered a set to 50 with 50, from 600.

## Infrastructure Changes

- Server instance 5 (bridge 43614, jar fork `4f58237`) for the speed check and the live tests, stopped after by its
  PID.

## Decisions

- **User decisions:** OQ-21 (a) (Caleb, 2026-11-06: keep 50 ms, with a speed check at 600 ms in the gate).
- **Agent choices (reversible):**
  - the cases:
    - the Gnome course at 30, 5 laps, which can't fall;
    - the Barbarian course at 75, 8 laps;
    - the Wilderness at 99, 6 laps;
    - Barbarian Fishing at 70/45/45, 3 runs;
    - the 7 shortcut check trips;
  - the 600 ms side run at once, for the time, except the trips, rerun alone once concurrency was found to shift
    them;
  - the fix in the client rather than in nine scripts.
- **For Caleb:** whether CLAUDE.md's note that one server takes several scripts at once should say that timing
  measurements run one per server.

## Validation

- **The speed check:** `results/calibration/speed-check-20261108-2331.json`, 11 of 11.
  - The 50 ms files: `agility-20261108-2308-gnome-a30`, `-2309-barbarian-a75`, `-2309-wilderness-a99`,
    `barbfishing-20261108-2310`, `travel-validation-20261108-2311` (each `-i5`).
  - The 600 ms files: `-2324-gnome`, `-2326-barbarian`, `-2325-wilderness`, `barbfishing-20261108-2327`,
    `travel-validation-20261108-2331` (each `-600ms-i5`).
  - The concurrent batch's trips: `travel-validation-20261108-2323-600ms-i5.json`, `speed-check-20261108-2327.json`
    (6 of 11).
  - The first 600 ms batch, on a server left at 50 ms, was deleted.
- **`speed_check.py` on the first check's files** (2026-11-06): 18 of 18 again, as before.
- **The live tests** on instance 5, with the client fix: 68 passed, 2 failed. The two are the other sessions' tests of
  fork changes not in that jar (the Runecrafting session's `shown()` and the Herblore session's OQ-47 (c)), as
  before. Nearby offline tests (`test_sim_barbfishing`, `test_shortcuts`): 6 passed.

## Follow-Up

- Caleb: the CLAUDE.md note above; env contract v1.32 and the seven shortcuts (from `m002-agility-shortcuts`).
- The other sessions: Crafting's, Herblore's and Runecrafting's speed checks (their calibrations). They were told.
- Committed when Caleb asks: only this session's files and hunks, explicit paths.
