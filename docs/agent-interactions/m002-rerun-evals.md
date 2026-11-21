# Agent Interaction

## Metadata

- Interaction ID: m002-rerun-evals
- Timestamp CST: 2026-11-19 17:06:24 CST (the prompt), the session transcript's timestamp (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The five evaluations ran, and all five summaries are published, committed and pushed. E6b's came
  last, after OQ-91 (b) and the README fix (`m002-oq89-oq91`): two of its policies' episodes stop at the evaluation's
  100,000-decision cap.
- Commit: this record in the docs commit to `main` (Caleb: "Commit it to main directly", 2026-11-20 17:56:18 CST). The
  summaries are on their branches, pushed with each branch's merge of `main`: E3 `a460bd0`, E6a `905a31d`, E4
  `00da2c2`, E5 `7b4ad52`, E6b `736adb6` (its merges `47d2bea` and `61f6e32`).

## Full Prompt

> Run the evaluations from this session

## Response Summary

- **The merges** (`m002-outstanding-tasks`'s first step): `main` (to `7eac963`) into each experiment branch, each
  clean, each docs only (the run checks' records, the decision log, OQ-89 and OQ-90):
  - E3 `experiment/e3-reward-weight-sweep` → `7d0917e`;
  - E6a `experiment/e6a-discount-sweep` → `4ca2bed`;
  - E4 `experiment/e4-rnd-exploration` → `88b7255`;
  - E6b `experiment/e6b-pbrs-shaping` → `47d2bea`;
  - E5 `experiment/e5-weight-conditioned-ppo` → `388a4f8`.
- **The evaluations**, in this order, each from its own worktree with `uv run --frozen python scripts/evaluate.py
  --config configs/<name>-eval.yaml` (16 workers, E1's 30 seeds, 20 game-hours, sampled actions), each beside E1's four
  baselines:

  | Experiment | Policies | Models | Episodes |
  |---|---|---|---|
  | E3 | 29 | 25 | 870 |
  | E6a | 14 | 10 | 420 |
  | E4 | 9 | 5 | 270 |
  | E6b | 9 | 5 | 270 |
  | E5 | 69 (5 models at 13 weightings) | 5 | 2,070 |

  - Every model the configs name exists (the reruns' `runs/<name>/`; the first round's are in `runs/<name>-bootstrap`,
    and E3's first evaluation is in `results/eval/e3-reward-weight-sweep-bootstrap`, so nothing is overwritten).
  - The runner is a session background job (Caleb's choice, so an app update would kill it; an evaluation doesn't
    resume, so a killed one restarts from its beginning). Its log is `runs/eval-queue.log` (each start, commit and exit
    code), and each evaluation's own log is `results/eval/<name>.log` in its worktree.
  - E3's started at 17:08:06 at `7d0917e`.
- **All five finished with exit 0** by 20:29:46: E3 in 61 minutes, E6a 15, E4 16, E6b 79 and E5 30 (3 h 22 min in
  all). Every policy has 30 episodes, on seeds 0 to 29, and no summary has a null.
- **E6b's capped episodes (OQ-91):** the evaluation's rollout stops an episode at 100,000 decisions (`play`'s
  `max_decisions`, `rlscape/eval/rollout.py`). Two of E6b's policies loop on 1-tick options long enough to reach it. All
  30 of `pbrs/seed3`'s episodes stop there, between 16.8 and 19.8 game-hours: none reaches hour 20, and its line in the
  printed hour-20 table is blank. So do 3 of `pbrs/seed2`'s 30, at 19.5 to 19.7 game-hours. Those 33 episodes are E6b's
  79 minutes. No episode of E3's, E6a's, E4's, E5's or the first round's E3 reaches the cap; the most decisions in one
  is 31,160 (E3's (.75, .25) seed 3). How E6b is reported is OQ-91 (Caleb), so its summary waits.
- **Publishing E3, E6a, E4 and E5,** which don't depend on OQ-91: `publish_summary.py results/eval/<name> <name>` then
  `publish_training.py runs/<name> <name>`, in each worktree, one after another (a second session background job,
  logged to the same `runs/eval-queue.log` and to `results/eval/<name>-publish.log`). All eight exited 0, from 20:31:57
  to 20:41:51. Each summary's provenance is its branch's merge commit, and every policy has its hour-20 row. Each
  `training/runs.csv` has every run at 2,000,896 decisions from a clean tree. The runs that trained before sim v1.4
  (E3's 10 at `cbe3baa`, and one each of E6a's, E4's and E5's) are the decision log's sim v1.4 entry's 14 on sim v1.3.
- **Committed and pushed,** each with its branch's merge of `main` (Caleb):
  - E3 `a460bd0` (37 files; `decisions.csv.gz` 16.6 MB, the largest);
  - E6a `905a31d` (22 files);
  - E4 `00da2c2` (17 files);
  - E5 `7b4ad52` (17 files);
  - E6b `736adb6` (17 files), on 2026-11-20, after `main`'s README fix was merged in (`61f6e32`).

## Documentation Changes

- This record.
- `docs/open-questions-log.md`: OQ-91 (E6b's capped episodes).
- The five experiment branches' `results/summary/<name>/` (above).

## Code Changes

- None. The runner is a scratch script, not in the repo.

## Infrastructure Changes

- None.

## Decisions

- **Agent recommendation:** merge first, so each evaluation's provenance is the branch it'll publish from; then the
  five evaluations one at a time at 16 workers.
- **User decision:** run the evaluations from this session (2026-11-19 17:06:24 CST). Push each merge with its
  experiment's published summary, not before (2026-11-19 17:40:49 CST).

## Validation

- `git merge-tree` before each merge (all clean); after each, nothing behind `main`, a clean tree, and no file outside
  `docs/` changed.
- Each eval config's model paths checked to exist (E3 25, E6a 10, E4 5, E6b 5, E5 5); 24.9 GB of RAM free at the
  start.
- After the evaluations, a scratch check of each `episodes.parquet`: 30 episodes per policy on 30 seeds, no nulls,
  and each episode's decisions and game ticks against the cap and hour 20. The same check on the first round's E3
  evaluation.
- After publishing: each README's provenance SHA and hour-20 table (no blank row), each `runs.csv`'s run count,
  decisions, commit and dirty flag, and the largest file's size.

## Follow-Up

- **Caleb:** OQ-91, how E6b's capped episodes are reported: (b), as they are (2026-11-20, `m002-oq89-oq91`). E6b's
  summary is published with the README fix there.
- **Claude:** the final census of all 50 and the Gem Store tally
  (`m002-outstanding-tasks`'s fourth step), and each experiment's PR into `main`.
