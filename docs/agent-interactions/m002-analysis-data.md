# Agent Interaction

## Metadata

- Interaction ID: m002-analysis-data
- Timestamp CST: 2026-11-11 16:23:33 CST, the prompt's timestamp in the session transcript (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL. The data the analysis reads is built and tested. The figure script waits on Caleb's definitions
  (what an activity is and what counts as taking one up, the hypervolume's reference point, and others), asked
  after this.
- Commit: on `tooling/analysis-data`, from `tooling/train-queue` (PR #19).

## Full Prompt

> Yes, carry on with the analysis scripts

## Response Summary

- **Checked first:**
  - the committed summaries (E1's and E2's);
  - what `publish` and `publish_training` write;
  - the proposal's §6 (its measurements and plots);
  - what an evaluation episode and the decision log record.
- **Found:**
  - Time allocation and milestones need each evaluation episode's decisions, which the harness didn't keep.
  - The time allocation across training, the discovery timeline and the entropy need the training logs, which are
    git-ignored.
  - E3's evaluation (about Nov 12) is the deadline for the first: evaluating again later would compete with the
    training queue.
- **Built the data side first, general enough** that the definitions can be chosen afterwards:
  - every evaluation episode's trace (`decisions.csv.gz`);
  - each training run's behaviour per 100,000 decisions (`behaviour_bins.csv`, `behaviour_options.csv.gz`,
    `first_choices.csv.gz`).
- **Ran the extraction on E2's best run** (7.8 s, adds up exactly). It showed that "first chosen" can't define
  discovery: 1,000 options are tried at least once, the last near the end of training.
- **Mid-turn,** Caleb asked why no run does anything with fletching; see `m002-fletching-unused.md`.

## Documentation Changes

- `docs/decision-log.md`: "Built: the analysis's data".
- `ROADMAP.md`: the analysis item.
- `CLAUDE.md`: the published traces and behaviour tables.
- This record.

## Code Changes

- `rlscape/eval/rollout.py`: `TRACE`, an episode's trace.
- `rlscape/eval/harness.py`: `run_tables` (three tables); `run` is unchanged for its callers; `save` takes the
  decisions.
- `scripts/evaluate.py`: saves the decisions.
- `rlscape/eval/publish.py`: `decisions.csv.gz` in a summary; the behaviour tables in a training summary;
  deterministic gzip.
- `rlscape/eval/behaviour.py` (new): `entropy`, `read_log`, `training_behaviour`.
- `tests/test_analysis_data.py` (new, 5 tests).

## Infrastructure Changes

- None. E2's decision log was only read.

## Decisions

- **User decision (Caleb):** carry on with the analysis scripts (this prompt).
- **Agent choices:**
  - the data before the figures, because of E3's evaluation date;
  - the trace and the behaviour tables keep every option, so the activity grouping and the discovery definition stay
    open;
  - `run` kept as it was, beside `run_tables`;
  - bins of the run's checkpoint interval;
  - gzip for the larger tables.

## Validation

- **Tests:** `tests/test_analysis_data.py`, `tests/test_eval_harness.py` and `tests/test_publish_summary.py`: 15
  passed. The first run had 2 failures, both in the tests: a groupby sorted policies by name, and two Series were
  compared in different orders.
- **E2's best run:** the bins sum to its 1,000,448 decisions and 8,638 episodes. Combat and gathering hold about 50%
  and 45% of its game time.

## Follow-Up

- **Caleb:** the analysis's definitions (OQ-75 onwards, asked next).
- **Claude:**
  - the figure script, once they're decided;
  - E3's branch merges this tooling before E3 is evaluated.
