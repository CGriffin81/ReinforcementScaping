# Agent Interaction

## Metadata

- Interaction ID: m002-reviewer-guide
- Timestamp CST: 2026-11-12 16:04:27 CST, the prompt's timestamp in the session transcript (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL. A first draft of the reviewer's guide (`README.md`), in a PR into `main`. Its results wait for
  the evaluations, and its tag for the reviewed version. OQ-88 answered: Windows only.
- Commit: this commit on `docs/reviewer-guide` (from `main` at `175675d`; Caleb: "Commit it and open a PR into main",
  16:25:21 CST).

## Full Prompt

> Start on the reviewer's guide

Answer in the question dialog (16:21:45 CST, the tool result's timestamp in the transcript):

> OQ-88, which platforms the check runs on: "Windows only"

## Response Summary

- **The guide** (OQ-50 (a)): `README.md` at the repo's root, the repo's first. Five parts:
  1. **What the report claims:** RQ1 to RQ5 and H1 to H3, each with its experiments, the figures and tables
     `scripts/figures.py` makes, and the code behind them. The questions are the proposal's; their results go in
     with the report.
  2. **A reading path** through the RL code, ten steps, about 2,500 of the repo's 36,000 lines of Python.
  3. **What to skip and why it can be trusted:** the simulator (about 13,000 lines), backed by the sim-to-real
     table and the simulator's 32 test files; the server, the bridge and the calibration scripts, which nothing
     in training, evaluation or the figures needs; the docs.
  4. **A 10-minute check** with no server or GPU: the core tests, the figures from the committed summaries, and a
     short CPU training run.
  5. **Reproducing the experiments:** the commands, the branches, the machine.
- **Measured for the check** (beside four training runs):
  - the core tests (`test_smdp`, `test_smdp_ppo`, `test_toy`, `test_sim_env`), 25 passed in 108 seconds;
  - `scripts/figures.py` on `main`'s summaries, 7 seconds (it will take longer with every experiment published);
  - 2,048 decisions of E2's configuration on the CPU (`--total-decisions 2048 --out`), 157 seconds.
- **Found: the environment installs on Windows only.** `pyproject.toml` takes torch from `wheels/`, where
  `scripts/fetch_torch_wheel.py` puts PyTorch's Windows CUDA 13.0 wheel (1.9 GB), so `uv sync` fails on Linux or
  macOS. **OQ-88, Caleb: Windows only** (the options were a CPU torch on Linux and macOS, recommended, or a
  container). The guide says the check needs Windows x64.
- **Also found:** the simulator reads the server submodule's data (`server/Server/data/configs`,
  `src/main/content`, `worldprops/rl.conf`), not its cache, so a reviewer can clone it without its LFS files
  (`GIT_LFS_SKIP_SMUDGE=1`); `data/travel/places.npz` is built on the first run.
- **Placeholders left in the draft:** the reviewed version's tag; the queue's total time; the results.

## Documentation Changes

- `README.md` (new): the reviewer's guide, a draft.
- `docs/decision-log.md`: OQ-88, raised and answered.
- This record.

## Code Changes

- None.

## Infrastructure Changes

- None. The check's training run went to the session's scratchpad.

## Decisions

- **Claude's choices within OQ-50 (a)** (for Caleb's review): the claims table's rows (the proposal's RQs and
  hypotheses, and the simulator's validity) and their figures, from `scripts/figures.py`'s list; the reading path's
  files and order; the check's three steps, sized to run in about 10 minutes.
- **User decision (Caleb):** OQ-88 (b), Windows only.

## Validation

- The check's three steps, timed on this machine (above).
- The line counts from the files on `main` (`wc -l`); the experiments' own files (`rnd.py`, `pbrs.py`,
  `conditioned.py`) from their branches.

## Follow-Up

- **Caleb:** the draft.
- **Claude:** the results into the claims table once the evaluations are published; the tag; the report's
  half-page appendix with the same map (OQ-50 (a)).
