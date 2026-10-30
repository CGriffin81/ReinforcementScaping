# Agent Interaction

## Metadata

- Interaction ID: m002-eval-harness
- Timestamp CST: 2026-10-30 15:25:47 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (baselines committed; the eval harness built and tested; a preliminary E1 run done)
- Commit: the baselines and total XP are main repo `43887df` (branch `sim-v0`); the harness is the main repo commit
  that adds this record (its SHA can only be filled in by a later commit)

## Full Prompt

> Commit this and keep going with the eval harness

Caleb asked during the run (answered in the same turn, before the run finished):

> How long will running E1 baselines for 20 game-hours take?

## Response Summary

- **Committed** the baselines and total XP as `43887df`, after the suite passed (165 passed, 18 skipped). Before
  committing, filled in the `Commit:` fields of the three records that commit adds.
- **Built the eval harness** (`rlscape/eval/harness.py`, `scripts/evaluate.py`):
  - any named policy × N seeds, in worker processes
  - total level, total XP and net worth at hour 0 and every checkpoint
  - percentile-bootstrap 95% CIs and paired differences between policies
  - parquet plus a provenance `config.json`
- **Ran a preliminary E1:** 3 baselines × 10 seeds × 20 game-hours on 14 workers, in 223 s.
  - Estimated 3–5 minutes when Caleb asked, from the single-core episode times measured earlier.
  - Found greedy wealth bimodal: myopic lock-in between mining iron and fighting.

## Documentation Changes

- `docs/decision-log.md`: the harness, the preliminary results table and the bimodal finding.
- `ROADMAP.md`: the eval item ticked and the status line.
- `Commit:` fields of `m002-baselines`, `m002-greedy-xp`, `m002-total-xp` (now `43887df`).
- This record.

## Code Changes

- `rlscape/eval/harness.py` (new): `run`, `summarize`, `paired_difference`, `bootstrap_ci`, `save`, `provenance`,
  `POLICIES`.
- `rlscape/eval/rollout.py`: `Episode.start`, the metrics at reset.
- `rlscape/eval/__init__.py`: exports.
- `scripts/evaluate.py` (new): the command line.
- `tests/test_eval_harness.py` (new, 6 tests):
  - the bootstrap
  - the table shapes
  - parallel runs equal serial ones
  - the summary and paired difference
  - the parquet round trip and provenance
  - unknown policies are refused
- `pyproject.toml`, `uv.lock`: pandas 3.1.0 and pyarrow 26.0.0.

## Infrastructure Changes

None. Results go to `results/` (git-ignored); the preliminary run is `results/eval/e1-preliminary-20261030`.

## Decisions

- **User decisions:** commit, then build the eval harness.
- **Agent choices (reversible):**
  - hour 0 (the fresh character) is included alongside the 2-hour checkpoints, so curves start at the beginning
  - percentile bootstrap with 10,000 resamples and a fixed seed, so CIs are reproducible
  - paired differences, because policies run on the same seeds
  - policies are referred to by name, so worker processes can build them (Windows spawns workers)
  - provenance records both repos' SHAs and whether the tree had uncommitted changes
- **Not decided here:** the preliminary run isn't the E1 deliverable. That needs calibration and the scripted guide.

## Validation

- `uv run pytest -q tests/test_eval_harness.py`: 6 passed. On the first run one test failed on a chained comparison
  with `pytest.approx`, a mistake in the test; it was fixed.
- Full suite with the server stopped: `uv run pytest -q`, 171 passed and 18 skipped.
- A smoke run of the script with 3 workers wrote all four files with correct provenance.
- The preliminary E1 run finished without errors. Its numbers are in the decision log, and the bimodal ranges were
  checked against the episode table.

## Follow-Up

- Commit when Caleb asks.
- The scripted-guide baseline: drafted from archived 2009 guides and cited, for Caleb's review.
- Speed: greedy episodes are the slow part (about 90–160 s in parallel), still dominated by the combat-slot mask
  (the separate task).
