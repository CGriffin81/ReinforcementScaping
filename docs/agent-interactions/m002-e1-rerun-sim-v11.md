# Agent Interaction

## Metadata

- Interaction ID: m002-e1-rerun-sim-v11
- Timestamp CST: 2026-11-09 16:00:36 CST (the prompt), from the session transcript's timestamp (UTC−06:00). The run
  started at 16:28:18 CST (its `config.json`'s `created`, taken at the start since PR #9) and took 681 s.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (E1 rerun on sim v1.1 from a clean commit, checked, its summary republished, and PR #10 updated)
- Commit: the commit on branch `experiment/e1-baselines` after `4b969d1` that adds this record and the republished
  summary

## Full Prompt

> Continue once the digest finishes.

## Response Summary

- **Why it was rerun:** E1's first run (`d73e4d1`, record `m002-e1-baselines`) was on sim v1, whose walks depended
  on what a worker had played before (OQ-64). Sim v1.1 (PR #11) fixes that.
- **The branch:** merged `tooling/mask-speedup` into `experiment/e1-baselines` (`4b969d1`, a merge commit, so PR
  #10's history stays as it was). That brings in PR #9's later commits, sim v1.1 (#11) and the speed-up (#12), which
  changes no result.
- **The run:** `uv run python scripts/evaluate.py --config configs/e1-baselines.yaml`:
  - 120 episodes in 681 s, against 976 s before the speed-up;
  - config hash `4fd4698dbad7` (unchanged), git `4b969d1`, not dirty, fork `cad9743`;
  - sim v1's run kept, git-ignored, in `results/eval/e1-baselines-sim-v1/`.
- **At hour 20** (mean [95% bootstrap CI], 30 seeds), with sim v1's in brackets after each:

  | Policy | Total level | Net worth (gp) |
  |---|---:|---:|
  | random | 214 [205, 222] (215) | 14,190 [11,071, 17,676] (14,552) |
  | greedy XP/hr | 157 [157, 157] (157) | 1,160 [1,133, 1,188] (1,160) |
  | greedy GP/hr | 40 [36, 46] (40) | 1,891,142 [1,766,299, 1,975,610] (1,891,142) |
  | scripted guide | 351 [344, 357] (351) | 129,789 [123,945, 135,909] (130,567) |

- **Checked:**
  - **The greedy baselines** are unchanged in every episode. Greedy GP still picks flax in 28 of 30 seeds.
  - **Random and the guide** change in 27 and 28 of 30 episodes; every mean stays inside sim v1's CI.
  - **No loops:** the guide makes 343 to 512 decisions. Only random dies.
- **RQ1's bar is as it was:** the guide on total level (351), greedy GP/hr on net worth (1.89M).
- **Republished** with `scripts/publish_summary.py results/eval/e1-baselines e1-baselines --force`.

## Documentation Changes

- `results/summary/e1-baselines/` (README, the three tables, `config.json`): republished from the sim v1.1 run.
- This record.

## Code Changes

- None on this branch beyond the merge (`4b969d1`), whose code is PRs #9, #11 and #12's.

## Infrastructure Changes

- The merge commit `4b969d1` on `experiment/e1-baselines`; `git push`; PR #10's description updated.
- `results/eval/e1-baselines/` (the new run) and `results/eval/e1-baselines-sim-v1/` (the old one), git-ignored.

## Decisions

- **User decision (Caleb):** OQ-64 (a), which made the rerun necessary.
- **Agent choices:**
  - merge, not rebase, so PR #10's history isn't rewritten;
  - run with the speed-up in, which changes no result and is faster.

## Validation

- `config.json`: `git_dirty` false.
- The checks above, against sim v1's run, episode by episode.

## Follow-Up

- **Caleb:** merge PRs #9, #11 and #12, then #10.
- **Claude:**
  - tag `sim-v1.1` on #11's merge;
  - `train.py` with the decision logger;
  - then E2, the sanity ladder.
