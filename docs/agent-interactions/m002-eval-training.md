# Agent Interaction

## Metadata

- Interaction ID: m002-eval-training
- Timestamp CST: 2026-11-09 17:32:25 CST (the prompt, "Carry on.", the same as `m002-train`'s). Caleb's answers to
  OQ-65 came at 19:26:32 CST. Both are from the session transcript's timestamps (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (OQ-65 recorded; the tooling E2 to E6 share built and tested, opened as a tooling PR stacked on
  PR #13)
- Commit: the commit on branch `tooling/eval-training` (from `tooling/train` at `b1649dc`) that adds this record

## Full Prompt

> Carry on.

(The same turn as `m002-train`. After `train.py`, E2 was next, and its design was open, so Claude asked.)

## Response Summary

- **Asked Caleb E2's design** (AskUserQuestion, four questions, each with a recommendation). Caleb took every
  recommendation (OQ-65):
  1. a synthetic 3-option env with an exact optimum;
  2. a 2 × 2 sweep (learning rate × entropy coefficient), 2 seeds each;
  3. 1M decisions a run, revisited after E2;
  4. evaluation with sampled actions.
- **Built the tooling E2 needs** that E3 to E6 share too, so into `main` first (OQ-61):
  - **sweeps** in the config and `train.py`;
  - **trained policies in the eval harness**, `[label=]ppo:<model.zip>`, sampled, seeded per episode;
  - **`scripts/publish_training.py`.**
- **A mistake along the way, found and fixed before testing:** a quoting slip in an edit script put the next edit's
  text into `harness.py`. The diff showed it. The file was restored from git and the edits redone from a clean
  script.

## Documentation Changes

- `docs/decision-log.md`:
  - "Decided: OQ-65, E2's design: the toy env, the sweep, 1M decisions a run, sampled evaluation (Caleb)", with
    every option;
  - "Built: sweeps, trained policies in the eval harness, and training summaries".
- `ROADMAP.md`: E2's design (OQ-65), and the tooling item, ticked.
- `CLAUDE.md`: the training line covers sweeps, evaluating a trained model, and publishing runs.
- This record.

## Code Changes

- `rlscape/agents/training.py`: `sweep` and `variant` keys, `variants`, `_named`, `run_dir` with the variant, and
  `train` refusing an unexpanded sweep.
- `scripts/train.py`: every (variant, seed); `--variant`; `--jobs` over the pairs.
- `rlscape/eval/trained.py` (new): `TrainedPolicy`, `split`, `is_trained`, `load`.
- `rlscape/eval/harness.py`:
  - `make_policy` and `policy_label`;
  - trained specs accepted and their models checked;
  - labels in the tables, two policies never sharing one.
- `scripts/evaluate.py`: `--policies` takes trained specs.
- `rlscape/eval/publish.py`: `publish_training`, `training_readme`; `publish` replaces only its own files.
- `scripts/publish_training.py` (new).
- `tests/test_training_tools.py` (new, 3 tests):
  - a sweep's grid, names, run directories and refusals;
  - a trained policy in the harness, the same serial and on 2 workers in another order, with a missing model and a
    shared label refused;
  - publishing training runs, their refusals included.

## Infrastructure Changes

- The branch `tooling/eval-training`, pushed, and its PR into `main`, stacked on PR #13.

## Decisions

- **User decisions (Caleb):** OQ-65 (1) to (4), all (a).
- **Agent choices (technical, for review):**
  - variants named by their values;
  - one torch thread for an eval worker;
  - the learning curves published whole, a few MB an experiment.

## Validation

- `uv run pytest tests/test_training_tools.py tests/test_training.py tests/test_publish_summary.py
  tests/test_eval_harness.py`: 18 passed.
- `uv run pytest -n 8 --dist loadgroup`: 442 passed, 75 skipped (the live tests, with the servers off).

## Follow-Up

- **Caleb:** merge PR #13, then this one.
- **Claude:**
  - `experiment/e2-ppo-sanity-ladder`: the toy env and its rung, the sweep's config, the runs (about 8 hours: it can
    run overnight), the evaluation on E1's seeds, the summaries;
  - E2's PR.
