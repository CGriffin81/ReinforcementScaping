# Agent Interaction

## Metadata

- Interaction ID: m002-e1-sim-v1.2
- Timestamp CST: 2026-11-11 17:14:55 CST, the prompt's timestamp in the session transcript (UTC−06:00), the same
  prompt as `m002-sim-v1.2`. The run started at about 17:50 CST and took 799 s.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: COMPLETE. E1 is rerun and published on sim v1.2, and OQ-67's units are recomputed from it (the tooling).
- Commit: on `experiment/e1-baselines`, after sim v1.2 (`fc55a14`).

## Full Prompt

> Go with your recommendations for all five. Have we begun to use the GPU for the tests yet?

The fourth recommendation: rerun E1 on the new sim, and keep E2 on v1.1 with a note.

## Response Summary

- **E1's branch** fast-forwarded to sim v1.2 (`fc55a14`). The v1.1 run was moved aside to
  `results/eval/e1-baselines-sim-v1.1`.
- **E1 evaluated** with its config (4 baselines, seeds 0 to 29, 16 workers) on the idle machine, and published over
  the v1.1 summary.
- **Results:** the guide's episodes are unchanged; greedy GP/hr's changed (79 levels and 1.76M gp against 40 and
  1.89M); random and greedy XP/hr moved within noise.
- **OQ-67's units:** skill unchanged (323.866); wealth 17.639 (was 18.901); `WEALTH_FACTOR` 18.36 (was 17.13).

## Documentation Changes

- `docs/decision-log.md`: "Rerun: E1 on sim v1.2".
- This record.

## Code Changes

- None on this branch.
- `results/summary/e1-baselines/` republished: `README.md`, `checkpoints.csv`, `config.json`, `episodes.csv`,
  `summary.csv`.

## Infrastructure Changes

- `results/eval/e1-baselines-sim-v1.1` (git-ignored): v1.1's run, kept.

## Decisions

- **User decision (Caleb):** rerun E1 on v1.2 and keep E2 on v1.1 (the fourth recommendation).
- **Agent choices:** none beyond running E1's own config.

## Validation

- **The run's provenance** is clean: `fc55a14`, no uncommitted changes. So `publish_summary` accepted it.
- **The units** were recomputed from the published `episodes.csv`: the mean 20-hour r_skill and r_wealth per
  baseline, and the best of each.

## Follow-Up

- **Claude:** the units in `rlscape/envs/weights.py` (tooling), then E3 to E6 merge them and train again.
- **Caleb:** this branch's PR into `main`, after the sim's (#22).
