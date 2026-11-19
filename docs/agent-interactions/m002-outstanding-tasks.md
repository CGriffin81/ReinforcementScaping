# Agent Interaction

## Metadata

- Interaction ID: m002-outstanding-tasks
- Timestamp CST: 2026-11-19 14:12:34 CST (the prompt), the session transcript's timestamp (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The training is done. What's left before and around the analysis is listed. The two decisions
  raised at the seventh run check are logged as OQ-89 and OQ-90.
- Commit: this commit, to `main` directly (Caleb: "Commit it to main directly", 2026-11-19 15:43:21 CST).

## Full Prompt

> Check for outstanding tasks before analysis.

## Response Summary

- **The training is done:** the queue finished all 50 reruns at 10:00:06 on 2026-11-19, 0 failed, and
  `train-queue.err` is empty. The queue's processes have exited, and the scheduled task "ReinforcementScaping train
  queue" is Ready, not running. Every run has its `run.json` and `model.zip` (E3 25, E6a 10, E4 5, E6b 5, E5 5). The
  worktrees are clean, and D: has 1.58 TB free.
- **Before the analysis, in order:**
  1. **Merge `main` into the five experiment branches.** Each is 9 commits behind, all records and the decision log
     (from `587183f` to `562fb03`). The code they need (PR #31's figure fixes, sim v1.4) is already merged in.
  2. **Run the five evaluations** on E1's 30 seeds with sampled actions (`scripts/evaluate.py --config
     configs/<name>-eval.yaml`):
     - E3: 29 policies, 870 episodes (the first round's took 41 minutes at 8 workers);
     - E6a: 14 policies, 420 episodes;
     - E4 and E6b: 9 policies, 270 episodes each;
     - E5: 65 conditioned specs plus the baselines, about 2,000 episodes (its config says about 1.5 hours at 16
       workers).
     - In all, about 3 to 4 hours, one after another, at 16 workers. **How to run them is Caleb's call:** from this
       session (as E3's first was, Caleb's choice on 2026-11-15) or from a one-time scheduled task, since an app
       update kills what a session starts (2026-11-13).
  3. **Publish each one:** `publish_summary.py` (the evaluation) and `publish_training.py` (the 2M-decision runs, about
     6 minutes for E3's 25 in the rehearsal), into `results/summary/<name>/` on each branch.
  4. **The final collapse census of all 50, and the Gem Store tally** (`m002-collapse-check`'s follow-up). 14 runs
     finished after the seventh run check and haven't been looked at: E3's seed 4 at all five weightings, E6a's γ_hr
     0.9 seed 3 and both seed 4s, and E4's, E6b's and E5's seeds 3 and 4. That settles the Gem Store finding, which has
     been held out of the decision log until the seeds settle it.
  5. **Each experiment's PR into `main`,** once its summary is checked. Then `scripts/figures.py` over the published
     summaries.
- **Decisions for Caleb:**
  - **OQ-89:** what the report says causes the loops. Recommended: (a), the counts by discount, with the cause at 0.99
    called untested. (b) would test it with about four more E3 runs (8 to 10 hours) after the evaluations.
  - **OQ-90:** the rule that counts a run as looping, the same for both rounds. Recommended: (a), the run checks' rule
    (10 of the first round's 50 by it, where the 2026-11-16 entry said 8).
  - **How the evaluations run** (above).
  - **PR #20** (E5's replay at any weighting, into E5's branch, open since 2026-11-11): E5's runs are done, so it can
    merge. It conflicts with E5's branch now, so it needs E5's branch merged in first. It's for the demo, not the
    analysis.
  - **The scheduled task:** with the queue done, it can be deleted, or kept for one-time jobs such as the evaluations.
- **Later, around the report:**
  - the reviewer's guide's claims table, the tag for the reviewed version, and the report's half-page appendix
    (`m002-reviewer-guide`);
  - RQ5's numbers from E3's evaluation traces (`m002-oq1-oq50`);
  - Dohare et al.'s full text, before the report quotes it (`m002-loop-cause`);
  - the ROADMAP's E3 to E6 boxes, ticked once each experiment's summary is published;
  - the record `m002-collapse-check` still says "this commit" for `562fb03`;
  - leftover worktrees: `.claude/worktrees/funny-goldstine-4ada0b` (detached), `-int` (the task's Python) and
    `-e5-replay` (PR #20);
  - **Windows Update** is paused until every run, evaluation and test is done (ROADMAP's "after the last test").

## Documentation Changes

- `docs/open-questions-log.md`: OQ-89 (what causes the loops, for the report) and OQ-90 (the looping rule). Both were
  raised at the seventh run check, recorded there as recommendations, and not logged as open questions until now.
- This record.

## Code Changes

- None.

## Infrastructure Changes

- None.

## Decisions

- **Agent recommendation:** merge `main` into the branches, then run the evaluations, then publish, then the final
  census. OQ-89 (a) and OQ-90 (a).
- **User decision:** commit the list and the two open questions to `main` (2026-11-19 15:43:21 CST). OQ-89, OQ-90
  and the rest are still pending.

## Validation

- Read-only: the queue's log, its processes and the task's state; each run folder's `run.json` and `model.zip`; each
  eval config's policy count; `git rev-list` for each branch against `main`; `gh pr view 20`; free disk; the
  follow-ups of the recent records.

## Follow-Up

- **Caleb:** OQ-89, OQ-90, how the evaluations run, PR #20, the scheduled task.
- **Claude:** the steps above once Caleb says go.
