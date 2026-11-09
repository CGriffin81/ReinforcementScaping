# Agent Interaction

## Metadata

- Interaction ID: m002-results-summary
- Timestamp CST: 2026-11-09 13:41:38 CST (the prompt), from the session transcript's timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the first tooling PR: committed summaries and experiment configs, opened for Caleb to merge)
- Commit: `c875431` on branch `tooling/results-summary` (from `main` at `2edac10`), and the commit after it with the
  provenance fix and OQ-62

## Full Prompt

> Continue on with the plan as stated.

## Response Summary

The plan as stated is OQ-61's: tag `sim-v1`, the shared tooling into `main` first (each by its own PR), then one
`experiment/<name>` branch per experiment, E1 first. This record covers the tag and the first tooling PR; E1 has its
own record (`m002-e1-baselines`).

- **Tagged** `sim-v1` (annotated) on `2edac10`, PR #8's merge, and pushed it.
- **The first tooling PR** (`tooling/results-summary`), which changes no result:
  - `results/summary/` is committed and the rest of `results/` stays ignored;
  - `scripts/publish_summary.py <run dir> <name>` writes `results/summary/<name>/`: the run's `config.json`, its three
    tables as CSV, and a README with the provenance and the last checkpoint's means and CIs. It refuses a run from a
    dirty tree unless `--allow-dirty`, and an existing summary unless `--force`;
  - `scripts/evaluate.py --config configs/<name>.yaml`, so each experiment runs by one command. A command-line option
    overrides the file, an unknown key is refused, and `config.json` records the command line (outside the hash).
- **Design choices, for Caleb's review:**
  - **CSV, not parquet,** for the committed copy: it diffs in a PR and opens anywhere, which keeps the peer review
    simple (OQ-17 (a′)). The tables are small (E1's checkpoints are 1,320 rows). The parquet stays in `results/eval/`.
  - **The summary is published by a second step,** not by `evaluate.py` itself, so a run gets looked at before it's
    committed, and an unchecked or dirty run never lands in `results/summary/` by accident.
  - **YAML, as OQ-61 states,** needs PyYAML (a new dependency, 6.0.3). TOML (in the standard library) would have
    avoided it, but would have changed what Caleb approved.
  - **The command line isn't hashed:** the hash names what was run. The same run from the file or from the flags
    gets the same hash.
- **A second commit on the PR, while E1 ran:** the run's provenance is taken when it starts (`save(..., started=)`).
  Taken at the save, a run started on a dirty tree and committed before it ended would be recorded clean, under a
  SHA that never ran. E1 isn't affected: nothing in the tree changed while it ran. The PR also logs OQ-62, Caleb's
  mid-turn suggestion to give the experiment branches descriptive names (record `m002-e1-baselines`).

## Documentation Changes

- `CLAUDE.md` (Environment): an experiment's run, `evaluate.py --config` then `publish_summary.py`.
- `ROADMAP.md`: §2's layout (`configs/`, `results/summary/` committed) and the finishing plan's tooling item, ticked.
- `docs/decision-log.md`: "Built: committed results summaries and experiment configs (the first tooling PR, OQ-61)",
  with the provenance from the run's start.
- `docs/open-questions-log.md`: OQ-62, the experiment branches' names.
- This record.

## Code Changes

- `.gitignore`: `/results/*` and `!/results/summary/`, in place of `/results/`.
- `rlscape/eval/publish.py` (new): `publish` and `readme`.
- `rlscape/eval/harness.py`: `save` takes an optional `extra`, provenance kept outside the hashed config, and
  `started`, the provenance taken when the run began.
- `scripts/publish_summary.py` (new).
- `scripts/evaluate.py`: `--config` and `parse_args`; the command line recorded in `config.json`; `provenance()`
  taken before the run.
- `tests/test_eval_harness.py`: `save` records the `started` provenance it's given.
- `pyproject.toml`, `uv.lock`: `pyyaml>=6.0.3` (`uv add pyyaml`).
- `tests/test_publish_summary.py` (new, 4 tests): the tables round-trip and the README holds the provenance and the
  last checkpoint's table; a dirty run and an existing summary are refused, and `allow_dirty` says so in the README;
  `evaluate.py` reads a config file, the command line overrides it, and an unknown key is refused.

## Infrastructure Changes

- The `sim-v1` tag, pushed to GitHub.
- The branch `tooling/results-summary`, pushed, and its PR into `main`.

## Decisions

- **User decision (Caleb, earlier):** OQ-61, which names the tooling, the summaries and `configs/<name>.yaml`.
- **Agent choices (technical, in this PR, for Caleb's review):** CSV for the committed tables, publishing as its own
  step, PyYAML, and the command line kept out of the hash.

## Validation

- `uv run pytest tests/test_publish_summary.py tests/test_eval_harness.py`: 10 passed.
- `uv run pytest -n 8 --dist loadgroup`: 427 passed, 75 skipped (the live tests, with the servers off).
- A file under `results/summary/` shows as untracked and one under `results/eval/` doesn't (checked with
  `git status`).

## Follow-Up

- **Caleb:** review and merge the PR.
- **Claude:** `experiment/e1-baselines` (stacked on this branch until it's merged), then the mask speed-up and
  `train.py` PRs.
