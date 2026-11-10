# Agent Interaction

## Metadata

- Interaction ID: m002-train
- Timestamp CST: 2026-11-09 17:32:25 CST (the prompt), from the session transcript's timestamp (UTC−06:00). The
  "Commit and push all changes." just before it, at 17:28:23 CST, found everything already committed and pushed, and
  changed nothing.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (`sim-v1.1` tagged; `train.py` and the decision logger built, tested and smoke-run, opened as a
  tooling PR)
- Commit: the commit on branch `tooling/train` (from `main` at `704dd95`) that adds this record

## Full Prompt

> Carry on.

## Response Summary

- **PRs #9 to #12 had been merged by Caleb.** Tagged `sim-v1.1` (annotated) on `dc34b6b`, #11's merge, and pushed
  it.
- **`scripts/train.py` and `rlscape/agents/training.py`:**
  - one YAML config per experiment, its `ppo` section passed to SMDPMaskablePPO as it is, so the trainer sets no
    hyperparameter of its own;
  - unknown keys and numbers YAML reads as text are refused;
  - a run directory with `config.json` (the provenance taken at the start), `options.json`, checkpoints,
    `model.zip`, TensorBoard (with `sim/*`), `episodes.parquet` (the learning curve), the decision log and
    `run.json`;
  - `--jobs N` trains seeds in parallel processes;
  - `torch_threads` keeps several runs' updates from crowding their envs.
- **`rlscape/agents/decision_log.py`,** hooked into `SMDPMaskablePPO.collect_rollouts`. A row per decision, with
  everything CLAUDE.md's rule names: the observation, the packed mask, the action, the probabilities of the available
  actions, the value, the duration, the reward components, the option record and the metrics. About 560 bytes a
  decision.
- **Throughput measured:**
  - **One run of 16 envs:** 226 decisions a second once warm (the envs alone; the caches take about 16,000
    decisions to warm).
  - **Four runs of 4 envs:** 467 a second in all.
  - **Training four seeds at once:** about 240 to 280 a second in all, about 1M an hour, as the finishing plan
    assumed.
- **Design choices, for Caleb's review:**
  - **The full observation is logged,** not a replayable digest: the log is about 0.6 GB a run, about 40 GB for every
    run planned, on a disk with 1.8 TB free.
  - **Probabilities for the available actions only,** in the mask's order: 81 on average, at most 284 of 2,293.
  - **Seeds in parallel by `--jobs`,** child processes of the script, since a pool's workers can't start their own
    env processes.
  - **No hyperparameter defaults in the trainer:** the ladder's sweep chooses them, in its config.
- **Not in this PR** (with E2, since it's the first to need them):
  - evaluating a trained policy on E1's 30 seeds with the harness;
  - publishing a training run's summary: the learning curves and that evaluation.

## Documentation Changes

- `docs/decision-log.md`: "Built: `scripts/train.py` and the decision logger (tooling, OQ-61); training's throughput
  measured".
- `ROADMAP.md`: the finishing plan's `train.py` item, ticked.
- `CLAUDE.md`: the training command.
- This record.

## Code Changes

- `rlscape/agents/decision_log.py` (new): `DecisionLogger`, `read_decisions`, `unpack_mask`.
- `rlscape/agents/ppo.py`: the decision logger's hook in `collect_rollouts`, kept out of the saved model
  (`_excluded_save_params`).
- `rlscape/agents/training.py` (new): `load_config`, `check_config`, `env_kwargs`, `make_vec_env`, `EpisodeTable`,
  `run_dir`, `train`.
- `scripts/train.py` (new): `--config`, `--seed`, `--jobs`, `--total-decisions`, `--out`, `--force`.
- `tests/test_training.py` (new, 5 tests), on a real 32-decision run, twice:
  - the run's files;
  - every logged decision's mask, probabilities, log-probability and counters;
  - the learning curve against the log;
  - the same config and seed giving the same run;
  - the config's refusals.

## Infrastructure Changes

- The tag `sim-v1.1`, pushed.
- The branch `tooling/train`, pushed, and its PR into `main`.
- Smoke runs in the session's scratchpad (not the repo): one of 8,192 decisions on 16 envs, and four seeds of 40,960
  on 4 envs each.

## Decisions

- **User decisions (Caleb, earlier):** OQ-61, the tooling into `main` first.
- **Agent choices (technical, for review):** those above.

## Validation

- `uv run pytest -n 8 --dist loadgroup`: 439 passed, 75 skipped (the live tests, with the servers off).
- **The smoke runs:** every run finished. Each episode ran to the 20-hour horizon, and the four logs and curves were
  written.
- **The smoke policy** (an untuned config, not a result): total level 267 on average after about 230 episodes, above
  random's 214.

## Follow-Up

- **Caleb:** review and merge the PR.
- **Claude:** E2, the sanity ladder (`experiment/e2-ppo-sanity-ladder`), with the policy evaluation and the training
  summary it needs. Its hyperparameter sweep picks the settings E3 to E6 use.
