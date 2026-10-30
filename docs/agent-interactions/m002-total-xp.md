# Agent Interaction

## Metadata

- Interaction ID: m002-total-xp
- Timestamp CST: 2026-10-30 15:15:40 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (decision recorded in env contract v1.3; total XP reported by the sim, the env and the rollout)
- Commit: main repo: the commit that adds this record, on branch `sim-v0` (its SHA can only be filled in by a
  later commit)

## Full Prompt

> Keep level-based reward and include total xp, but only up to the required xp to get level 99.

## Response Summary

- Kept r_skill level-based, as Claude had recommended (option a).
- Added total XP as a reported metric, each skill counted up to level 99's 13,034,431, as Caleb specified. It's in
  `info`, the 2-hour checkpoints, the reset info and the rollout's `Episode`.
- Made E1's greedy XP/hr baseline maximise the same capped total.
- Recorded the decision as env contract v1.3 (decision 19).

## Documentation Changes

- `docs/env-contract.md` v1.3:
  - §4's reported metrics
  - §6's `total_xp` and checkpoint keys
  - decision 19 in §9
  - the status paragraph restructured as a version list
- `docs/decision-log.md`: the decision and the agent choice.
- This record.

## Code Changes

- `rlscape/sim/skills.py`: `capped_total_xp`.
- `rlscape/sim/state.py`: `CharacterState.total_xp()`.
- `rlscape/sim/engine.py`: `info["total_xp"]`, and `total_xp` in checkpoints.
- `rlscape/envs/sim_env.py`: `total_xp` in the reset info.
- `rlscape/eval/rollout.py`: `Episode.total_xp`.
- `rlscape/baselines/policies.py`: greedy `xp` gains are counted on the capped total.
- Tests:
  - `tests/test_sim.py`: the cap, and the checkpoint contents
  - `tests/test_baselines.py`: checkpoint and episode total XP

## Infrastructure Changes

None.

## Decisions

- **User decisions:**
  - r_skill stays level-based
  - total XP, capped at level 99's XP per skill, is reported
- **Agent choice (reversible):** greedy XP/hr maximises the capped total, matching the metric.

## Validation

- Full suite with the server stopped: `uv run pytest -q`, 165 passed and 18 skipped.

## Follow-Up

- Commit when Caleb asks.
- The eval harness: seeds, parquet, bootstrap CIs, and total XP among its metrics.
- The scripted-guide baseline for Caleb's review.
