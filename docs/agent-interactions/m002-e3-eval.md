# Agent Interaction

## Metadata

- Interaction ID: m002-e3-eval
- Timestamp CST: 2026-11-15 11:11:42 CST, the prompt's timestamp in the session transcript (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUPERSEDED. The evaluation finished and its summary was published, but not committed: the collapse it
  found led to the trainer's two fixes (`m002-collapse-diagnosis`), and all of E3's runs train again with them
  (`m002-rerun`). Its results, the summary among them, are kept aside in E3's worktree.
- Commit: None.

## Full Prompt

> Start E3's evaluation

Answer in the question dialog (11:34:07 CST, the tool result's timestamp in the transcript):

> How should it run? "From this session"

## Response Summary

- **What it is:** `configs/e3-reward-weight-sweep-eval.yaml`, on `experiment/e3-reward-weight-sweep` at `ba9d8ec`
  (sim v1.3, `main`'s tooling merged in, clean):
  - the 29 policies are E1's four baselines and the sweep's 25 models (five weightings × five seeds, each its
    `model.zip`);
  - each plays E1's 30 seeds, 870 episodes in all, with sampled actions (OQ-65 (4)), 20 game-hours each.
- **Checked first:**
  - all 25 models exist;
  - E3's venv already has matplotlib and ruptures (from `main`'s figure tooling);
  - neither `evaluate.py` nor `publish_summary.py` imports the analysis code;
  - `--workers` on the command line overrides the config's 16.
- **The worker count: 8, not the config's 16.** E4's and E5's last runs were still training, and 16 workers would want
  more RAM than was free (14.6 GB). An episode depends only on its policy and seed (OQ-64; the digest proofs), so the
  worker count doesn't change a result.
- **Where it runs:** Claude recommended a one-time scheduled task, since a Claude app restart kills anything started
  from a session; **Caleb: from this session**. If the app restarts before it ends, it starts again from scratch.
- **Started** at 11:34:26: `uv run --frozen python scripts/evaluate.py --config
  configs/e3-reward-weight-sweep-eval.yaml --workers 8`, in `D:\ReinforcementScaping-runs`, with its log in
  `results/eval/e3-reward-weight-sweep.log`.

- **Finished** at about 12:15 CST: 870 episodes in 2,437 s (`results/eval/e3-reward-weight-sweep/`).
- **At hour 20** (30 seeds, means):

  | Weighting (skill, wealth) | Total level | Net worth |
  |---|---|---|
  | (1, 0) | 330 to 346 | 10k to 13k |
  | (.75, .25) | 343 to 348 | 61k to 105k |
  | (.5, .5), four seeds | 317 to 361 | 146k to 213k |
  | (.5, .5), seed 1 | 197 | 3.05M (the gem trade) |
  | (.25, .75), four seeds | 87 to 111 | 3.87M to 4.06M |
  | (.25, .75), seed 2 | 230 | 0.83M |
  | (0, 1), four seeds | 53 to 59 | 3.86M to 4.15M |
  | (0, 1), seed 1 | 37 | 1,649 gp |

  The baselines: random 214 levels and 17k; greedy XP/hr 157 and 1k; greedy GP/hr 79 and 1.76M; the guide 351 and
  130k.
- **Found: (0, 1) seed 1 collapsed in training.** Its reward held at 109 to 117 to 1.4M decisions, then from 1.5M fell
  to 0. Its episodes went from 150 to 340 decisions to about 14,900, cycling bank deposit and withdraw (8 ticks each,
  reward 0). Its critic valued those states at about 420.
- **Found: the same collapse elsewhere** (scratchpad `collapse_scan.py`, `collapse_onset.py`, `loop_option.py` over
  every finished run's `episodes.parquet` and last decision-log part). 7 of 48 finished runs end in it, plus E6b's
  seed 0, which the scan missed because few of its episodes finish:
  - **E6b, all five seeds:** they alternate two loot modes, a tick each; mid-run episodes reached 96k to 118k
    decisions. Their reward peaked at the start (0 to 100k) and collapsed from 200k to 800k.
  - **E6a γ0.9, seeds 0 and 3:** they cycle the loot modes from 400k to 500k, between better stretches. Seed 4 did
    too, and recovered.
  - **E3 (0, 1), seed 1:** the bank cycle, above.

  The mask keeps each loot mode from being chosen while it's set, but two modes can alternate, and with no fight
  between them nothing changes. Claude's hypothesis: a run of one-tick options is barely discounted (γ^τ), so the
  critic can bootstrap its own over-estimate. Not yet tested. E6b never improving on its start may point to its
  shaping.
- **Published, not committed:** `scripts/publish_summary.py results/eval/e3-reward-weight-sweep
  e3-reward-weight-sweep` wrote `results/summary/e3-reward-weight-sweep/` (6.4 MB). The diagnosis came first
  (Caleb), and then the rerun, so the summary was never committed.
- **Kept aside** (2026-11-15, `m002-rerun`): the evaluation as `results/eval/e3-reward-weight-sweep-bootstrap/`, its
  log beside it, the summary as `results/superseded/e3-reward-weight-sweep-bootstrap/`, and the runs as
  `runs/e3-reward-weight-sweep-bootstrap/`, all git-ignored in E3's worktree.

## Documentation Changes

- This record, on E3's branch.

## Code Changes

- None.

## Infrastructure Changes

- None.

## Decisions

- **User decision (Caleb):** run it from this session, not from a scheduled task.
- **Claude's choice:** 8 workers.

## Validation

- The evaluation's end: 870 episodes in 2,437 s.

## Follow-Up

- Superseded: E3's evaluation runs again on the rerun's models (`m002-rerun`).
