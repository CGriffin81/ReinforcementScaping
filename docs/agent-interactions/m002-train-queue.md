# Agent Interaction

## Metadata

- Interaction ID: m002-train-queue
- Timestamp CST: 2026-11-11 06:39:28 CST, the prompt's timestamp in the session transcript (UTC−06:00). Caleb's
  go-ahead to launch came at 15:29:45 CST.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: COMPLETE. Built, then launched on Caleb's word at 15:30 CST (PID 8436). It waits for E3's slots.
- Commit: on `tooling/train-queue`, from `tooling/reward-parts` (PR #18).

## Full Prompt

> Yes, carry on with the queue launcher

After the report, at 15:29:45 CST:

> Yes, launch the queue now

## Response Summary

- **Checked first:**
  - `train.py --jobs` trains one experiment's runs, and each experiment's code lives on its own branch. A run must
    train in its experiment's worktree to record that branch's provenance.
  - E3's runs on the process table: each shows as three processes (uv, the venv's launcher, the interpreter) with one
    command line. Its `--jobs` launcher has no `--seed`, and its envs run `multiprocessing.spawn`.
  - The trainer on this branch can't read E4's, E6b's or E5's configs (`rnd:`, `pbrs:`, `conditioned:`). So each
    worktree must list its own runs.
- **Built `scripts/train_queue.py`:**
  - Each run trains in its worktree, by that worktree's own `train.py` and venv.
  - `--jobs` counts every training run on the machine, found on the process table, with a 30 s settle so E3's
    launcher keeps its slots.
  - The default order is by seeds across experiments.
  - Resuming: done runs are skipped, and training ones left to finish. A run stopped part-way is refused, unless
    `--restart-partial`.
  - Checks first: each config by its own branch's trainer, clean worktrees, one server commit.
  - `--dry-run` shows the plan and each run's state.
- **Set up the worktrees** for E4, E6b and E5, like E6a's, and built their venvs through the dry run.
- **Launched the queue** (second prompt), detached like E3, from the main checkout:
  `uv run --frozen python scripts/train_queue.py --jobs 4` with E6a's, E4's, E6b's and E5's configs, its log in
  `runs/train-queue.log` (git-ignored). It listed the 25 runs and found the machine full with E3's 4 (E3: 12 of 25
  done, its fourth wave from about 10:00), so its first runs start when E3's last wave leaves slots, about Nov 12
  12:15 to 12:45.

## Documentation Changes

- `docs/decision-log.md`: "Built: the training queue".
- `ROADMAP.md`: the training queue item.
- `CLAUDE.md`: the queue's command.
- This record.

## Code Changes

- `scripts/train_queue.py` (new).
- `tests/test_train_queue.py` (new, 4 tests).

## Infrastructure Changes

- **Git worktrees** `D:\ReinforcementScaping-e4` (`experiment/e4-rnd-exploration`), `D:\ReinforcementScaping-e6b`
  (`experiment/e6b-pbrs-shaping`) and `D:\ReinforcementScaping-e5` (`experiment/e5-weight-conditioned-ppo`). Each has:
  - the server cloned from the main checkout's submodule at `cad9743`, with LFS smudging skipped;
  - a junction to `wheels/`;
  - `data/travel/places.npz` copied (its SHA-256, `c03dac85…`, is the same as the main checkout's, E3's and E6a's).
- **A venv in each of the four worktrees** (E6a's too), built by `uv run --frozen` during the dry run, about 2.5
  minutes each.
- **The main checkout** moved from `experiment/e5-weight-conditioned-ppo` to `tooling/train-queue`, which freed E5's
  branch for its worktree.
- **E3's worktree** (`D:\ReinforcementScaping-runs`) wasn't touched.
- **The queue** runs detached: PID 8436 (uv), started 2026-11-11 15:30:02 CST. While it trains, the four experiment
  worktrees must stay unchanged, since each run records its worktree's state.

## Decisions

- **User decisions (Caleb):** build the queue launcher (the first prompt), and launch it now (the second).
- **Agent choices:**
  - `--jobs` counts the machine's training runs from the process table, rather than waiting for E3 to end.
  - The order is by seeds across experiments by default, so every experiment has its first seeds early. This is a
    scheduling choice, not a design one: `--order experiments` is there if Caleb wants each experiment done in turn.
  - A run stopped part-way stops the queue at its start, rather than being restarted silently.
  - The queue refuses dirty worktrees and mixed server commits.
  - The tool is on its own branch from `tooling/reward-parts`, as shared tooling (CLAUDE.md).

## Validation

- **Tests** (`tests/test_train_queue.py`): 4 passed.
  - The first run hung. With `--jobs 1`, the queue rightly counted E3's four runs, so its slot never came free. The
    test was stopped and its processes checked: none were left.
  - The fix: `run_queue` takes its reader of the machine's runs as an argument, and the test reads the real process
    table filtered to its own two experiments.
- **The live process table** read by the queue's parser (0.8 s): E3's four runs. The launcher, the envs and the
  duplicates aren't counted.
- **Dry run** over E6a, E4, E6b and E5: 25 runs in the seeds order. Each config was accepted by its own branch's
  trainer, and E3's four runs were counted against `--jobs 4`.

## Follow-Up

- **Caleb:**
  - review PR stack #13 to #18, then this one.
- **Claude:**
  - when E3 finishes, evaluate and publish it;
  - check the queue's first starts (about Nov 12 12:30) and its runs as they finish;
  - `scripts/replay.py` support for E5's `@<u>`;
  - the analysis scripts.
