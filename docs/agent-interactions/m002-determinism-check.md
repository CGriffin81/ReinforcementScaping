# Agent Interaction

## Metadata

- Interaction ID: m002-determinism-check
- Timestamp CST: 2026-11-12 08:46:34 CST, the prompt's timestamp in the session transcript (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: COMPLETE. The check passed. Windows Update is Caleb's to pause; the step to turn it back on is in ROADMAP.
- Commit: this record, with the decision log's and ROADMAP's changes, committed directly to `main` after `ab2e543`
  (Caleb: "Commit it to main directly", 08:54:49 CST).

## Full Prompt

> Yes, run the determinism check on (0, 1)
> Pause Windows Update until we are done with all of our tests. Put a requirement post-testing to turn Windows Update back on.

Follow-up (2026-11-12 08:54:49 CST), when asked where the record and the docs should go:

> Commit it to main directly

## Response Summary

- **The determinism check.** Windows Update's restart at 02:29 killed E3's four seed-0 runs (`m002-queue-reboot`).
  The queue started them again from the start, at the same commit (`b29de68`), config and seed. By 08:40 the
  restarted (0, 1) run was at 1.8M decisions, past the killed run's 1.0M. Compared:
  - **the decision log:** all 20 parts of the killed run (50,000 rows each, 1,000,000 in all) against the restarted
    run's first 20, by SHA-256. All 20 are byte-identical: observations, masks, actions, action probabilities, values,
    reward parts, durations and character state;
  - **the 10 checkpoints** (100,000 to 1.0M), each zip member by SHA-256. `policy.pth`, `policy.optimizer.pth`,
    `pytorch_variables.pth`, the sb3 version and the system info are identical. `data` differs, so its keys were
    compared:
    - `start_time`, the wall clock;
    - `ep_info_buffer`: the 100 episodes' lengths and returns are equal; only their wall-clock field `t` differs;
    - `policy_class` and `rollout_buffer_class`: only the memory addresses in their function and ABC reprs.
  - `options.json` is identical, and `config.json` differs only in its `created` time.
  
  So a GPU run in deterministic mode is reproducible from its config and seed alone over 1M decisions. OQ-80's test
  had shown it on a small run.
- **Windows Update:** Claude can't change it, since it's a system setting, so Caleb pauses it (Settings → Windows
  Update → Pause updates). Claude recommended "Pause for 3 weeks", to about Dec 3, which covers the report's due
  date.
- **The requirement to turn it back on:** a step in ROADMAP's plan, *After the last test*: turn Windows Update back
  on once every run, evaluation and test is done. Also in the decision log, and in Claude's memory so that later
  sessions remind Caleb.

## Documentation Changes

- `docs/decision-log.md`: "Found: GPU training is deterministic over 1M decisions" and "Decided: Windows Update paused
  until the last test is done".
- `ROADMAP.md`:
  - under *Nov 13–18*, the restart after Windows Update's and the check's result;
  - *After the last test*: the step to turn Windows Update back on.
- This record.

## Code Changes

- None committed. The check's scripts are in the session's scratchpad:
  - `determinism_check.py`: each log part's and checkpoint member's SHA-256, and a column-by-column comparison for a
    part that differs;
  - `ckpt_data_diff.py` and `ckpt_data_diff2.py`: the differing `data` keys.

## Infrastructure Changes

- None. Claude's memory notes that Windows Update is paused and has to be turned back on.

## Decisions

- **User decisions (Caleb):**
  - run the determinism check on (0, 1);
  - pause Windows Update until all the tests are done;
  - a requirement to turn it back on after them;
  - this record and the docs committed directly to `main`.
- **Claude's choices within it:**
  - bytes first, columns only if bytes differ;
  - the step's place in ROADMAP;
  - the 3-week pause recommended.

## Validation

- The check's output, as above.
- `git diff` of the docs.

## Follow-Up

- **Caleb:** pause Windows Update.
- **Claude:** the same check on (1, 0), (.75, .25) and (.5, .5) once their restarts pass 1.6M to 1.7M decisions
  (about 4 to 5 hours from 08:40), if Caleb wants it.
