# Agent Interaction

## Metadata

- Interaction ID: m002-restart-v1.2
- Timestamp CST: 2026-11-11 17:14:55 CST, the prompt's timestamp in the session transcript (UTC−06:00), the same
  prompt as `m002-sim-v1.2` and `m002-e1-sim-v1.2`. The queue started at 18:00:08 CST.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL. E3, E6a, E6b and E5 train on sim v1.2 from one queue. E4 waits on OQ-79, a flaw in its RND
  centring found by its tests on v1.2.
- Commit: on `tooling/units-v1.2`, and the experiment branches' merges of it.

## Full Prompt

> Go with your recommendations for all five. Have we begun to use the GPU for the tests yet?

## Response Summary

- **The units** (OQ-67), from E1 on v1.2 (`m002-e1-sim-v1.2`): skill unchanged; wealth 17.639 (was 18.901);
  `WEALTH_FACTOR` 18.36. The normalised (.5, .5) is env (.5, 9.18).
- **`tooling/units-v1.2`** is the tooling stack (to PR #21) with sim v1.2 and E1's rerun merged in, and the units.
- **The experiment branches merged it:**
  - E3 and E6a cleanly;
  - E4, E6b and E5 with the decision log's appends kept from both sides;
  - E5's test got the observation's new size (3,488);
  - the configs' comments give the new env equivalent.
- **Each experiment's own tests on v1.2:**
  - E6b's PBRS: 5 passed.
  - E5's conditioned agent: 4 passed.
  - E4's RND: 4 passed, 1 failed. The centred bonus averages −0.53 spreads (55 of 64 negative), because it's centred
    on the error's cumulative mean while the predictor learns. That's a design question: OQ-79, with the
    recommendation to centre on a recent mean. E4 is held out of the queue until it's decided.
- **E3's v1.1 runs** (13 finished, 4 partial) moved aside to `runs/e3-reward-weight-sweep-sim-v1.1` in its worktree.
- **The queue,** from `D:\ReinforcementScaping-int`, was dry-run, then launched. It trains 45 runs by seeds: E3's 5
  weightings, E6a's 2, E6b and E5, seed 0 first. Its first four runs are E3's seed 0 at four weightings (18:01:38).
  They record `6fd5108`, a clean tree, server `cad9743`, (.5, .5) as env (0.5, 9.1806), and 2,294 options with
  `skill_woodcutting_fletch`.

## Documentation Changes

- `docs/decision-log.md`: "Changed: OQ-67's units on sim v1.2, and E3 to E6 restart from one queue".
- `docs/open-questions-log.md`: OQ-79.
- `ROADMAP.md`: the restart, and the queue's item.
- This record.

## Code Changes

- `rlscape/envs/weights.py`: `WEALTH_UNIT` and its docstring.
- `tests/test_weights.py`: (.5, .5) is (0.5, 9.1806).
- `tests/test_training.py`: v1.44's sizes (in the merge of sim v1.2).
- On E5's branch, `tests/test_conditioned.py`'s `N_OBS`. On E3's, E6a's, E4's and E6b's, their configs' comments.

## Infrastructure Changes

- **The worktree `D:\ReinforcementScaping-int`** on `tooling/units-v1.2`, with its own venv. The queue runs from it.
- **E3's v1.1 run folder** renamed in `D:\ReinforcementScaping-runs` (git-ignored).
- **The training queue:** PID 17112 (uv), started 2026-11-11 18:00:08 CST, log
  `D:\ReinforcementScaping\runs\train-queue.log`. The first launch's log was renamed to `train-queue-sim-v1.1.log`.

## Decisions

- **User decisions (Caleb):** the five recommendations; OQ-75 (c) before them.
- **Agent choices:**
  - E3 joins the queue with the others, by seeds, rather than training on its own first;
  - E4 held out pending OQ-79, rather than its test loosened;
  - the queue run from the integration worktree, which has the queue's script, leaving the main checkout free.

## Validation

- **The integration branch's full suite** (`pytest -n 6`, while E1's 16 workers ran): 467 passed, 78 skipped,
  2 failed. The 2 were the tests that start a process pool (`WinError 6`, a handle error under the load). Run on
  their own, both passed.
- **After the units:** `tests/test_weights.py`, `tests/test_training.py` and `tests/test_training_tools.py`, 15 passed.
- **The queue's dry run:** 45 runs, each config accepted by its own branch's trainer.

## Follow-Up

- **Caleb:**
  - OQ-79 (E4's centring);
  - PRs #22 (sim v1.2), E1's rerun, and this branch's;
  - tag `sim-v1.2` on #22's merge.
- **Claude:**
  - E4 into the queue once OQ-79 is decided;
  - the figure script (OQ-76 to OQ-78), with ruptures.
