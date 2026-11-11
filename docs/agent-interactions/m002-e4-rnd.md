# Agent Interaction

## Metadata

- Interaction ID: m002-e4-rnd
- Timestamp CST: 2026-11-10 21:31:21 CST, the prompt's timestamp in the session transcript (UTC−06:00). Caleb
  answered OQ-72 at 22:15:07 CST.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL. RND is built and tested and E4's configs are ready; E4 trains when E3 frees the machine.
- Commit: on `experiment/e4-rnd-exploration`, from `tooling/replay` (PR #17's head, `fd9f371`).

## Full Prompt

> Start with E6a's config and E4's RND

Caleb's answers to OQ-72, as the app gave them:

> "E4 (PPO + RND), OQ-72a: how big should RND's exploration bonus be? ..."="0.75, half the env's (Recommended)",
> "E4, OQ-72b: should RND's bonus be centred? ..."="Centred, mean zero (Recommended)",
> "E4, OQ-72c: which parts of the 3,482-feature observation should RND judge novelty on?"="Character state, 917
> (Recommended)".

(E6a's config has its own record, `m002-e6a-config`, on its branch.)

## Response Summary

- **Read first:**
  - ROADMAP §3's plan: v1, a VecEnv wrapper adding a normalised intrinsic reward, with v2's second value head only if
    v1 is ambiguous.
  - The proposal: RND, Burda et al. [8], for H3.
  - The observation's named parts.
  - The PPO loop.
- **Found:**
  - Episodes end only at the 20-hour limit, which every run bootstraps. So v1's single value head doesn't cut the bonus
    off at an episode's end.
  - The env's reward per decision at (.5, .5): mean 0.65 to 1.25, spread about 1.5 (E2's and E3's decision logs).
  - A small test run showed an uncentred bonus averaging about 3× its spread. In an SMDP whose decisions last seconds
    to 15 minutes, that pays for more, shorter decisions. So Claude added centring and asked about it.
- **Built:**
  - `rlscape/agents/rnd.py`: `RNDReward` and `check_rnd`.
  - The trainer: the `rnd:` config section, `rnd.*` sweeps, the learning curve's extrinsic reward and `r_intrinsic`,
    and TensorBoard's `rnd/*`.
  - The decision log's `r_intrinsic` column.
- **Asked OQ-72** (size, centring, inputs). Caleb took the three recommendations.
- **E4's configs:** E3's (.5, .5) plus `rnd` (coef 0.75, centred, 917 features), checked setting for setting; and the
  evaluation's config.

## Documentation Changes

- `docs/decision-log.md`: "Decided: OQ-72" and "Built: RND for E4".
- `ROADMAP.md`: the E4 item and §3's RND row.
- `CLAUDE.md`: the `rnd:` section.
- This record.

## Code Changes

- `rlscape/agents/rnd.py` (new).
- `rlscape/agents/training.py`:
  - the `rnd` key, its checks and sweeps;
  - `with_rnd`;
  - `RNDStats`;
  - `EpisodeTable` keeps the env's reward and adds `r_intrinsic`.
- `rlscape/agents/decision_log.py`: the `r_intrinsic` column.
- `configs/e4-rnd-exploration.yaml` and `configs/e4-rnd-exploration-eval.yaml` (new).
- `tests/test_rnd.py` (new, 5 tests).

## Infrastructure Changes

- None. E4 gets a worktree of its own at its launch, as E3's and E6a's have.

## Decisions

- **User decisions (Caleb):**
  - start E4's RND (this prompt);
  - OQ-72 (a) a spread of 0.75, (b) centred, (c) the character's state.
- **Agent recommendations:** OQ-72's three, all taken.
- **Agent choices:**
  - v1 as ROADMAP §3 planned;
  - Burda's network shapes as MLPs, his input normalisation and ±5 clip;
  - the predictor trained once a rollout (4 epochs, 256, Adam 1e-4);
  - no bonus in the first rollout;
  - the bonus scaled per decision, not by its return's spread;
  - the bonus kept apart in infos, the learning curve, the decision log and TensorBoard;
  - E3's (.5, .5) as E4's baseline instead of training it again.

## Validation

- **Tests:** `tests/test_rnd.py` 5 passed; `tests/test_training.py` and `tests/test_training_tools.py` 8 passed. All
  ran in one process, while E3 trained.
- **A small run with subprocess envs** (2 envs, 512 decisions):
  - the encoder crosses the process boundary;
  - `rnd/*` reached TensorBoard;
  - the observation's parts, and RND's 917 inputs.
  - The first attempt hung: the scratch script had no `__main__` guard, so Windows' subprocess envs re-ran it. It was
    stopped with nothing left running, and the second attempt took 77 s.
- **Cost:** 0.51 ms to score a step of 4 envs, and 131 ms to train on a rollout of 1,024 decisions. That's about
  0.26 ms a decision.
- **E4's config:** it loads; RND's parts are the observation's; without `rnd` it equals E3's (.5, .5).

## Follow-Up

- **Claude:**
  - when E3 frees the machine, a worktree for E4 and its launch, alongside E6a;
  - then its evaluation, summaries and PR;
  - E6b's PBRS and E5 next.
