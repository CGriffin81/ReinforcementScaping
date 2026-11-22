# Agent Interaction

## Metadata

- Interaction ID: m002-training-cost
- Timestamp CST: 2026-11-21 19:04:48 CST (the prompt), the session transcript's timestamp (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. `scripts/figures.py` tables E5's training cost against E3's, per front, from `main`'s summaries.
- Commit: a commit to `main` after `8c8929f` (Caleb: "Commit it to main directly", 2026-11-21 21:03:04 CST).

## Full Prompt

> Add the training-cost table

## Response Summary

- **What a row is:** a front, as `hypervolume_per_seed.csv` scores it. At each training seed, E3's front is its five
  agents (one per weighting) and E5's is its one agent. So the cost sits beside the hypervolume, seed for seed.
- **The tables** (`training_cost`, from each summary's `training/runs.csv`):
  - `training_cost_per_seed.csv`: per method and training seed, the front's runs, decisions (the SMDP's env steps),
    episodes, wall hours, and its runs' commits;
  - `training_cost.csv`: per method, the mean front's decisions and wall hours (with a 95% CI over the seeds), and the
    totals.
- **What it shows,** from `main`:

  | Method | Runs per front | Decisions per front | Wall hours per front | Hypervolume |
  |---|---|---|---|---|
  | E3: an agent per weighting | 5 | 10.0M | 38.1 [35.9, 40.2] | 0.373 [0.278, 0.484] |
  | E5: one weight-conditioned agent | 1 | 2.0M | 8.4 [7.9, 8.8] | 0.394 [0.360, 0.456] |

  E5's front takes a fifth of E3's decisions and 22% of its wall time, and its hypervolume's CI lies inside E3's. In
  all, E3's 25 runs took 50.0M decisions and 190.7 run-hours; E5's 5 took 10.0M and 42.2.
- **The wall time's caveat, checked:** the queue trained five runs at once. From each run's `run.json` (its
  `finished` less its wall time), every E3 and E5 run had on average 3.8 to 4.0 others beside it. The exception is
  E5's seed 4, with 2.8 at the queue's tail; its 7.3 hours is the fastest. The two shared one load, so the comparison
  holds, but no run's wall time is its speed alone. This is in the table's docstring and the decision log.

## Documentation Changes

- `docs/decision-log.md`: "Built: E5's training cost against E3's", with Caleb's decision, the table, the numbers and
  the caveat.
- `ROADMAP.md`: E5's line has the cost. The old week-5 box (the front, hypervolume and training cost) is ticked.
- `README.md`: the reviewer guide's RQ3 row names `training_cost.csv` and `figures.py`'s `training_cost`.
- This record.

## Code Changes

- `scripts/figures.py`:
  - `Summaries.runs`, an experiment's `training/runs.csv`;
  - `training_cost`, the two tables, or None unless E3's and E5's training summaries are both published;
  - `build` writes them, or says they're skipped;
  - the docstring lists them.
- `tests/test_analysis.py`: `test_the_training_cost_is_per_training_seed_what_one_front_costs`, on known runs: E3's
  fronts sum five runs each, E5's are one, the CI and totals are right, and with no E5 summary there's no table.

## Infrastructure Changes

- None.

## Decisions

- **Agent recommendation:** the table, from `training/runs.csv`, E5's 5 runs against E3's 25 (`m002-roadmap-boxes`).
- **User decision:** add it (Caleb, 19:04:48 CST).
- **Agent choices:**
  - per front, the hypervolumes' unit, rather than per run;
  - the hypervolume kept in its own table: the decision log and this record put the two side by side;
  - the runs' commits in the per-seed table, so a front trained on sim v1.3 shows;
  - no correction to the wall time for the load, only the caveat.

## Validation

- The new test, then all of `tests/test_analysis.py`: 24 passed (with the figure script's end-to-end test).
- `uv run python scripts/figures.py --summary results/summary --out <scratch>` on `main`'s summaries: all nine figures
  and every table, the training-cost tables among them, none skipped. The numbers above are from that run.
- The load: a scratch script over the 50 runs' `run.json` in the five worktrees.
- `git diff --check` is clean, and no added line is over 120 characters outside the tables.

## Follow-Up

- **Caleb:** asked whether to commit; "Commit it to main directly" (21:03:04 CST). Done, as under Commit. Still
  Caleb's: how the report words the comparison.
- **Claude:** the video script's [TO FILL] loop counts; the reviewer guide's claims table, its tag and RQ5's numbers.
