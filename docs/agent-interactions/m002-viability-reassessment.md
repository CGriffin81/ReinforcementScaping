# Agent Interaction

## Metadata

- Interaction ID: m002-viability-reassessment
- Timestamp CST: 2026-11-09 00:34:15 CST (the prompt), from the session transcript's timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (recommendation given); Caleb chose (a′), with every research question answered, on 2026-11-09
  (`m002-oq17-scope`)
- Commit: the main repo commit after `dc92982` (branch `sim-v0`) that adds this record (`m002-commit-all`)

## Full Prompt

> Let's reassess the viability of completing the project within the given time frame.

## Response Summary

- **Compared** `ROADMAP.md`'s plan, the proposal's RQ1 to RQ5 and H1 to H3, and OQ-17's options from 2026-11-05
  (`m000-feasibility-review`) with where the project is now:
  - built: the sim with all 17 skills, calibrated; the baselines and eval harness; the RL stack and SMDP PPO;
  - not started: no training run yet, and none of E2 to E7 or `ServerEnv`.
- **Measured the compute** instead of estimating it, at main repo `dc92982`, in a separate worktree, since another
  session's edits were in the working tree:
  - one sim worker makes 70 to 80 decisions a second after warm-up (sim v0: 110), and 92% of that time is the action
    mask;
  - training makes about 200 decisions a second with one 16-worker run, or about 280 with four 4-worker runs;
  - a random episode is about 385 decisions;
  - so about 1M training decisions an hour.
- **Verdict:** the full scope doesn't fit: about 25 days of building and 3 to 6 days of compute, against 17 days to
  peer review. Recommended **(a′)**: freeze the sim on Nov 10, then:
  - spend one day, at most, speeding up the action mask;
  - `train.py` and the sanity ladder;
  - E1 rerun, then E2 (5 × 5, or 5 × 3);
  - E3 (RND) for RQ4 and H3;
  - a weight-conditioned PPO for RQ3's second half, cut first if time runs short;
  - the calibration gate as the sim-to-real evidence;
  - a draft by Nov 25.

  Cut: E4 as planned, `ServerEnv` and E6's replays, PBRS, E5's granularity, and E7. The fallback is (b), E1 and E2
  alone.

## Documentation Changes

- `docs/open-questions-log.md`: OQ-17 reassessed. Updated: where it stands, the measured compute, options (a′), (b)
  and (c) with estimates, the biggest risk, and the status.
- `docs/decision-log.md`: "Measured: sim v1's training throughput, for OQ-17's reassessment". It's appended after
  the Runecrafting session's uncommitted entry, which was left as it was.
- This record.

## Code Changes

- None. The measurement scripts are scratch files (in the session's scratchpad), not in the repo:
  - a profiled run and a steady-state run of one worker;
  - a PPO throughput run.

## Infrastructure Changes

- A temporary git worktree at `dc92982` in the scratchpad, with a junction to `server/`. The junction was removed
  first, then the worktree, and `server/` was checked to be intact.
- No server was started. `results/benchmark/sim-speed-20261109-0037.json` comes from the first benchmark run, in the
  working tree.

## Decisions

- **User decisions:** none yet. OQ-17 is Caleb's.
- **Agent recommendation:** (a′), as above.
  - E3 (RND) over the γ sweep with PBRS as the one RQ4 experiment: it tests H3, feeds RQ2's discovery order, and its
    code is small.
  - Four concurrent runs over one 16-worker run, measured to be faster.

## Validation

- **The throughput numbers are measurements:**
  - one worker: 6 minutes, after warm-up;
  - PPO: one 16-worker run of 7 minutes, and four 4-worker runs of 6.7 minutes.

  Another session was working on the machine during them, so they may read slightly low.
- **The day counts are Claude's judgment,** from the task list and the recent pace. They aren't measured.
- **The four 4-worker runs** used the same seed, so they made identical decisions. That's fine for timing, but it's
  not a learning result.

## Follow-Up

- **Caleb:** OQ-17. Under (a′) also:
  - OQ-1 → D;
  - confirm env contract v1.18 and v1.22 to v1.33, and option catalog v1.4, for the sim freeze.
- **After the answer:** move OQ-17 (and OQ-1, if decided) to the decision log, and update `ROADMAP.md`'s weeks 6 to
  8 to match.
