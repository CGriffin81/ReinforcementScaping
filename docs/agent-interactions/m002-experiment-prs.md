# Agent Interaction

## Metadata

- Interaction ID: m002-experiment-prs
- Timestamp CST: 2026-11-21 10:41:33 CST (the prompt), the session transcript's timestamp (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The five experiment PRs into `main` were opened; they're since merged (`m002-experiment-merges`).
- Commit: this record in the docs commit to `main` after `92170fd`, with `m002-experiment-merges` (Caleb: "Commit
  it to main directly", 2026-11-21 13:43:21 CST).

## Full Prompt

> Open the experiment PRs into main

## Response Summary

- **Opened:**
  - [#33](https://github.com/CGriffin81/ReinforcementScaping/pull/33) E3, the reward-weight sweep;
  - [#34](https://github.com/CGriffin81/ReinforcementScaping/pull/34) E6a, the discount sweep;
  - [#35](https://github.com/CGriffin81/ReinforcementScaping/pull/35) E4, PPO + RND;
  - [#36](https://github.com/CGriffin81/ReinforcementScaping/pull/36) E5, the weight-conditioned PPO;
  - [#37](https://github.com/CGriffin81/ReinforcementScaping/pull/37) E6b, PBRS.

  E1 (#10, #23) and E2 (#15) were merged before. Each body gives the experiment, its hour-20 results per series (the
  mean over the training seeds, with their range), the trainer, sim and evaluation it ran on, the census's loops and
  Gem Store notes, its files, and the records. The session's PR bar tracks all five. The repo has no CI.
- **Merging:** each one merges into today's `main` cleanly. Simulated one after another (scratchpad `seq_merge.sh`:
  `git merge-tree` and `git commit-tree`, no ref touched), E3 and E6a go in cleanly in any order. But E4, E5 and E6b
  each add their section to the same lines of `rlscape/agents/training.py` and the same sentence of `CLAUDE.md`. Once
  one of the three is merged, the other two conflict there, whatever the order. Their bodies give the fix: merge `main`
  into the next branch, keep both sections, and run its tests.
- **Found while writing them:**
  - 14 of the 50 reruns trained on sim v1.3, as the 2026-11-16 entry logged: E3's 10 (every seed 0 and seed 1) and
    one each of E6a, E4, E5 and E6b. The PRs say so.
  - E4's, E5's and E6b's ROADMAP lines ("trains when E3 frees the machine") and their records' PARTIAL statuses date
    from before they trained, and will reach `main` that way. The PRs say so. They're for the ROADMAP's boxes after
    the merges.
  - PR #20 (`e5/replay-weightings`, into E5's branch) now conflicts with that branch. It's still Caleb's to decide.

## Documentation Changes

- This record.

## Code Changes

- None. Scratchpad scripts, read-only: `seq_merge.sh` (the merge order), `pr_tables.py` and `pr_seeds.py` (the
  bodies' tables, from each worktree's committed summary), and the bodies (`prs/*.body.md`).

## Infrastructure Changes

- Five pull requests on GitHub.

## Decisions

- **Agent recommendation:** merge E3 and E6a first. Then merge E4, E5 and E6b one at a time, merging `main` into each
  of the last two and resolving it before its own merge.
- **User decision:** "Merge them in that order" (Caleb, 2026-11-21 12:16:33 CST). Done in `m002-experiment-merges`.

## Validation

- Every branch is clean and pushed. `git diff origin/main...<branch>` shows no file under `rlscape/sim/` in any, so no
  branch changes the sim. E3's and E6a's change only `configs/`, `results/summary/` and their records.
- Each branch's own tests in its worktree: E4 `tests/test_rnd.py` and `tests/test_training.py`, 12 passed; E5
  `tests/test_conditioned.py` and `tests/test_training.py`, 10 passed; E6b `tests/test_pbrs.py` and
  `tests/test_training.py`, 13 passed.
- `gh pr list`: all five MERGEABLE. The bodies' numbers come from the summaries each PR commits. E3's match
  `m002-oq92`'s table; E6b's `pbrs/seed2` mean is over its 27 episodes, as its README says.

## Follow-Up

- **Caleb:** asked Claude to merge them in the order above; done, with E5's and E6b's conflict resolutions and
  `scripts/figures.py` on `main`'s summaries (`m002-experiment-merges`). PR #20 is still open.
- **Claude:** the ROADMAP's boxes and the stale lines, and the video script's [TO FILL] loop counts.
