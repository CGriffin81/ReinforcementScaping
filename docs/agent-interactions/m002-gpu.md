# Agent Interaction

## Metadata

- Interaction ID: m002-gpu
- Timestamp CST: 2026-11-11 18:39:50 CST, the prompt's timestamp in the session transcript (UTC−06:00). The
  follow-up came in mid-turn at 18:42:42 CST.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: COMPLETE. Caleb chose OQ-80 (a) ("Go with (a) for OQ-80."): the trainer runs CUDA deterministically,
  the five configs say `device: cuda`, and the queue restarted all 50 runs on the GPU.
- Commit: on `tooling/units-v1.2`.

## Full Prompt

> Why are the experiments not running on GPU?

Mid-turn:

> What are the projected time savings on running all of the experiments on GPU instead of CPU?

## Response Summary

- **Why:** Caleb chose CUDA torch on 2026-11-08, but Claude set every training config to `device: cpu` on
  2026-11-09, for repeatability and because the simulator takes the time. That choice wasn't put to Caleb, though it
  should have been: it's a setting that shapes the runs.
- **Measured:**
  - **The PPO update:** 1.12 s for one rollout on the CPU, 0.11 s on the GPU.
  - **A rollout:** about 20 s in the current runs, so the update is about 5% of a run.
  - **Repeatability:** two tiny GPU runs were identical, with and without deterministic mode, so the earlier claim
    that GPU runs aren't repeatable was wrong for this network.
  - **The current runs:** 50 to 54 decisions a second over their first 45 minutes, slowed by the E1 evaluation and
    tests in that hour. That's about 10 to 11 hours a run if it holds, so the queue would end late on Nov 16 or early
    on Nov 17, later than the "around Nov 16" given before.
  - **Not a GPU effect:** the first benchmark's rollouts (75 s on the CPU model, 32 s on the GPU one) differ because
    the first ran on a cold simulator and the second reused its warmed caches.
- **Projected saving:** about 5 to 7% of training, about 6 to 8 hours over the queue. OQ-80 gives the options;
  recommended (a): switch now, all 50 runs on the GPU in deterministic mode, restarting E3's four seed-0 runs.

## Documentation Changes

- `docs/open-questions-log.md`: OQ-80.
- This record.

## Code Changes

- None. The benchmarks were scratch scripts.

## Infrastructure Changes

- None. The benchmarks ran beside the queue's four runs and left them alone.

## Decisions

- **User decision (Caleb):** OQ-80 (a).
- **Agent recommendation:** OQ-80 (a).

## Validation

- **The update's time:** `SMDPMaskablePPO.train` on the same rollout, 3 times per device, the shortest taken
  (CUDA synchronised).
- **Repeatability:** two runs of `train()` per mode, compared by their decision logs' actions and their policies'
  weights.
- **The runs' speed:** from their decision logs' last part: its step against its file time, from the run's start.

## Follow-Up

- **Caleb:** OQ-80.
- **Claude:** the switch, if (a) or (b).
