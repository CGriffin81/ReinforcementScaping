# Agent Interaction

## Metadata

- Interaction ID: m002-e6b-pbrs
- Timestamp CST: 2026-11-10 22:27:42 CST, the prompt's timestamp in the session transcript (UTC−06:00). Caleb
  confirmed Φ (OQ-73) at 23:29:49 CST.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL. PBRS is built and tested and E6b's configs are ready; E6b itself trained later. *Updated
  2026-11-21:* it trained from the queue (`m002-restart-v1.2`), again with the trainer's fixes (`m002-rerun`), was
  evaluated (`m002-rerun-evals`) and merged into `main` by PR #37 (`m002-experiment-merges`).
- Commit: on `experiment/e6b-pbrs-shaping`, from `tooling/reward-parts` (record `m002-reward-parts`).

## Full Prompt

> Yes, carry on with E6b

Caleb's answer to OQ-73, as the app gave it:

> "E6b (PBRS), OQ-73: confirm the potential Φ? ..."="As built (Recommended)"

## Response Summary

- **Shared tooling first:**
  - E6b's shaping, like E4's RND, adds to the env's reward. Claude moved the logging of such additions into
    `tooling/reward-parts` (its own record and PR).
  - E4's branch merged it, and E6b's starts from it.
- **Designed Φ:**
  - The candidates' rates in the observation include the walk from where the character stands, its pack, and (for
    fights) its food and ammunition. A Φ built from them would swing by tens of reward with every walk or purchase.
  - So G is a capability: the best gathering gp/hr for a canonical character, with only its gathering levels and
    unlocks its own.
  - It's valued over the discounted time left, so Φ is 0 at the end with no jump. The shaping then charges each
    decision the income it forgoes, and pays up front for an investment.
- **Found:** the rate model's flax picking pays about 90k gp/hr from the start, and master farmers about 481k at 38
  Thieving. That makes 38 Thieving Φ's big step.
- **Built and tested;** Caleb confirmed Φ (OQ-73 (a)).
- **E6b's configs:** E3's (.5, .5) plus `pbrs`, checked; and the evaluation's config.

## Documentation Changes

- `docs/decision-log.md`: "Decided: OQ-73" and "Built: PBRS for E6b".
- `ROADMAP.md`: the E6b item.
- `CLAUDE.md`: the `pbrs:` section.
- This record.

## Code Changes

- `rlscape/agents/pbrs.py` (new): `GatheringIncome`, `Potential`, `annuity`, `PBRSShaping`, `shaped_sim_env`,
  `check_pbrs`.
- `rlscape/agents/training.py`: the `pbrs` key and its check; `make_vec_env` shapes each env with `ppo.gamma_hr`.
- `configs/e6b-pbrs-shaping.yaml` and `configs/e6b-pbrs-shaping-eval.yaml` (new).
- `tests/test_pbrs.py` (new, 5 tests).

## Infrastructure Changes

- None. E6b gets a worktree of its own at its launch.

## Decisions

- **User decisions (Caleb):**
  - carry on with E6b (this prompt);
  - OQ-73 (a): Φ as built.
- **Agent recommendations:** OQ-73 (a), taken.
- **Agent choices:**
  - the shared reward-parts tooling;
  - G as a capability (the canonical character), gathering methods only;
  - the time-left annuity;
  - the cache key;
  - E3's (.5, .5) as E6b's raw-reward baseline instead of training it again.

## Validation

- **Tests:** `tests/test_pbrs.py`, 5 passed. That includes Ng et al.'s identity on a whole real episode: the
  discounted shaping summed to −Φ(s₀) exactly.
- **A probe on real states:**
  - G is 89,675 gp/hr fresh, from flax;
  - 114,441 at 60 Woodcutting (yews);
  - 481,159 at 40 Thieving (master farmers);
  - unchanged by moving the character.
  - Φ at the start, at (.5, .5) and γ_hr 0.99: 139.2.
- **Cost:** a warm Φ takes 0.05 ms; a new level 0.03 to 0.4 s, once per process. Decisions per second with and
  without shaping: 70.1 and 63.3, the same within the noise of E3 sharing the machine. A first timing was invalid (the
  unshaped env warmed the sim's caches) and was redone with both warmed.
- **A subprocess run** (2 envs, 256 decisions): r_shaping between −1.92 and 0, mean −0.39, and every logged reward is
  the env's plus F.
- **E6b's config:** without `pbrs` it equals E3's (.5, .5).

## Follow-Up

- **Claude:**
  - when E3 frees the machine, worktrees for E4 and E6b and their launch, with E6a's;
  - then E5's design questions and build.
- **Caleb:** merge `tooling/reward-parts`'s PR after #17.
