# Agent Interaction

## Metadata

- Interaction ID: m002-normalised-weights
- Timestamp CST: 2026-11-10 07:28:44 CST. That's Caleb's answers to OQ-67 to OQ-69 in chat, by the session
  transcript's timestamp (UTC−06:00). This record was written at about 07:55 CST (estimated).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The helper is built and tested, and its PR is open.
- Commit: on branch `tooling/normalised-weights`, stacked on `experiment/e2-ppo-sanity-ladder` (PR #15). Stacking
  keeps the decision log's appended entries in one line, with no conflicts.

## Full Prompt

Caleb's answers to the three questions Claude asked in chat (record `m002-e2-ladder`), as the app gave them:

> "OQ-67 (before E3): the wealth reward is Δ net worth / 100,000 gp, so a level outweighs 100,000 gp. E2's agents at
> (.5, .5) learned skill only, and E3's planned weights from (.75,.25) through (.25,.75) would all reward mostly
> skill: only (0, 1) makes wealth worth chasing. Where should E3's weights sit?"="Normalised weights (Recommended)",
> "OQ-68: does E2's rung 1 pass? At λ 0.99 and 2M toy decisions, PPO reached 94.9% and 94.4% of the exact optimum (13
> trainings where the optimum trains 22). Claude proposed a 95% bar; you didn't set it."="Pass, with its numbers
> (Recommended)", "OQ-69 (before E3): the best variant's training reward rose by 17 to 20 over the last 30% of its 1M
> decisions. OQ-65 (3)'s rule says that gives 2M for E3 to E6. That's 55 runs: about 110 hours at 2M, or 55 at 1M,
> within Nov 13–18's 144 hours. How long should they train?"="2M, as the rule says (Recommended)"

## Response Summary

- **Logged the three decisions** on E2's branch (PR #15): OQ-67 to OQ-69 moved from the open-questions log to the
  decision log, ROADMAP marks E2 done, and the record `m002-e2-ladder` is updated.
- **Built OQ-67's helper,** `rlscape/envs/weights.py`:
  - normalised weights (u_s, u_b) on the simplex become SimEnv's (u_s, u_b × 17.13);
  - the units are E1's ideal point: the guide's 323.87 levels and greedy GP/hr's 1,890,109 gp in 20 hours;
  - a level stays worth u_s, so rewards keep E2's scale.
- **`train.py`'s configs take `env.normalised_weights`,** refuse it beside `env.reward_weights`, and sweep over it.
- **No sim change.** The evaluation harness is unchanged too: E3's observations don't show the weights.

## Documentation Changes

- `docs/decision-log.md`: "Built: normalised reward weights for E3 to E6 (tooling, OQ-67)".
- `ROADMAP.md`: the technical decision on reward normalisation, and the tooling item.
- `CLAUDE.md`: the Training line names `env.normalised_weights`.
- This record.

## Code Changes

- `rlscape/envs/weights.py` (new): `SKILL_UNIT`, `WEALTH_UNIT`, `WEALTH_FACTOR`, `env_weights`,
  `normalised_weights`.
- `rlscape/agents/training.py`:
  - `ENV_KEYS` gains `normalised_weights`;
  - `check_config` refuses both weight keys at once, and normalised weights off the simplex;
  - `env_kwargs` converts.
- `tests/test_weights.py` (new, 7 tests):
  - the units match E1's committed summary;
  - the conversion and its round trip;
  - four refusals;
  - the config keys and a sweep's names;
  - 40 random options on the real sim, each rewarded by the converted weights.

## Infrastructure Changes

- None.

## Decisions

- **User decisions (Caleb):** OQ-67 (a), OQ-68 (a), OQ-69 (a).
- **Agent recommendations:** (a) on each, which Caleb took.
- **Agent choices:**
  - the helper's place (`rlscape/envs/`, beside the reward it reweights);
  - a level kept worth u_s, so rewards stay on E2's scale;
  - the units hard-coded, with a test against E1's committed summary;
  - this branch stacked on E2's.

## Validation

- `tests/test_weights.py`, `tests/test_training.py`, `tests/test_training_tools.py`, `tests/test_e2_rung2.py` and
  `tests/test_toy.py`: 21 passed.

## Follow-Up

- **Caleb:** merge #13, #14, #15, then this PR.
- **Claude:** E3's configs on `experiment/e3-reward-weight-sweep`: normalised weights, 2M decisions, E2's winner.
