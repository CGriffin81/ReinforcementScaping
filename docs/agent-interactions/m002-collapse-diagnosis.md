# Agent Interaction

## Metadata

- Interaction ID: m002-collapse-diagnosis
- Timestamp CST: 2026-11-15 13:08:04 CST, Caleb's answer in the question dialog (the tool result's timestamp in the
  session transcript, UTC−06:00), after E3's evaluation (`m002-e3-eval`, on E3's branch) found the collapse.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The diagnosis found two causes and tested a fix for each: the trainer's horizon bootstrap (the
  critic's growing value) and the cost of a zero-effect option (the loops). With both fixed, E6a γ0.9 seed 0 didn't
  collapse to 800k decisions. Caleb chose to train all 50 runs again with both (`m002-rerun`).
- Commit: the PR from `tooling/horizon-terminal` (see `m002-rerun` for its merge).

## Full Prompt

The question, after E3's evaluation: 8 runs end looping zero-effect options; how to proceed? Caleb's answer
(13:08:04 CST):

> "Diagnose first (Recommended)"

## Response Summary

- **E3's evaluation summary was published as it ran** (`results/summary/e3-reward-weight-sweep/` in E3's worktree,
  6.4 MB, not committed): (0, 1) seed 1's collapse is a real outcome under E3's design.
- **E6b's shaping is as designed** (`rlscape/agents/pbrs.py` on E6b's branch). With G steady, every option pays a
  time rent, F ≈ −w·G/100,000·τ: about −0.0014 a tick here, for a one-tick loot toggle as for anything else. Over an
  episode the shaping sums to −Φ(start) whatever the agent does, so it can't make the loop optimal. The loop is a
  learning failure.
- **The trainer bootstraps the horizon** ([ppo.py:117](../../rlscape/agents/ppo.py)):
  - at the 20-hour horizon, a step's reward gets γ_hr^τ·V(final observation) added, the time-limit treatment (sb3
    issue #633);
  - the env contract chose it: the episode "ends as *truncated* (not terminal), so value bootstrapping is handled
    correctly" (§1);
  - but the observation carries the time left, and the task ends at 20 hours, so the true value at the end is 0;
  - the final observation is only ever a bootstrap target, never trained on, so nothing pins it.
- **Found: the critic's value grows through training in every run**, collapsed or healthy (scratchpad
  `critic_offset.py`, over E3's (0, 1) seeds 1 and 2, (1, 0) seed 0 and (.5, .5) seed 0).
  - It's the same at an episode's first decision as at its last.
  - It's nearly the same number in each run at the same point: about 81, 202, 323, 443, 563 and 615 at
    decision-log parts 4, 12, 20, 28, 36 and 40.
  - What an episode earns is 106 to 319. So the critic holds a large, growing offset c, and doesn't tell an
    episode's start from its end.
- **How an offset biases the policy.** An offset c shifts an option of duration τ's advantage by about
  −c·(1 − γ_hr^τ). That penalises long options in proportion to their length, and one-tick options hardly at all.
  - At γ_hr 0.99 and c ≈ 615, a 15-minute option is about −1.5 against a few points of reward a decision.
  - At γ_hr 0.9 the penalty is about ten times larger an hour.
  - In a loop the rewards are about 0, so nothing corrects c.
- **The evidence fits:**
  - every run's mean option length falls through training: E3 (1, 0) seed 0 from 1,089 ticks to 767, (.5, .5)
    seed 0 from 1,167 to 392;
  - E6a γ0.9 collapses earliest, from 400k to 500k decisions, in more seeds;
  - E6b's large negative per-decision rewards on long options add to it.

  It is a hypothesis with consistent evidence, not yet a tested cause.
- **All 50 runs had finished** by then: the queue at 12:35:41, 0 failed. Its scheduled task is kept (state Ready) in
  case a rerun needs it.

- **Asked Caleb how to proceed**: test the fix first (recommended), fix and rerun everything now, or keep the results
  and report it. **Caleb: test the fix first.**
- **The fix, for the test** (branch `tooling/horizon-terminal` from `main`, not committed):
  - `SMDPMaskablePPO` takes `bootstrap_horizon`, default True (how every run so far trained). With it False, the
    horizon's step keeps the env's reward, with no γ_hr^τ·V(final observation) added.
  - The test `test_the_horizon_is_bootstrapped_only_when_asked`: the same seeded rollout, both ways, differs only at
    the steps that end an episode. The PPO and SMDP tests pass (12).
- **The test runs**, started 13:16:
  - both from E6b's worktree, with the change applied to it uncommitted (its runs had finished), into the session's
    scratchpad (`fixtest/`), to 800k decisions each;
  - E6b seed 0 (its run collapsed from 200k), and E6a γ0.9 seed 0 (collapsed from 500k);
  - their configs are the experiments' own with `ppo.bootstrap_horizon: false`, on the same seeds, so the original
    runs are the comparison.
- **The test's result** (E6a γ0.9 done at about 15:15; E6b at 600k decisions at 15:25; decision log):
  - **the fix pins the critic:** V − G stays about +2 to +4 through the episode, where the original's grew to about
    +51 by hour 19;
  - **E6a γ0.9 collapses anyway,** at part 11 against the original's part 10;
  - **the loop isn't the entropy bonus** (the policy's entropy where it loops is about 1 nat, against 4.5 uniform),
    **and the critic doesn't overvalue the loop's states** (V − G within 0.7 of the acting decisions');
  - **E6b hasn't collapsed** by 600k decisions, where its original was all loops, but its unshaped return falls from
    135 to 116;
  - **what's left,** a hypothesis: a zero-effect option costs only its game time (about 0.01 reward for 8 ticks at
    γ_hr 0.9), less than a few percent of critic error biases a long option. Once loops cost reward, the lagging
    critic overestimates, which favours them more.
- **Asked Caleb how to proceed** (in the question dialog): test a decision floor (recommended), rerun all 50
  with the horizon fix only, keep the results, or mask the loops in the sim (sim v1.4). **Caleb: test a decision
  floor** (17:38:19 CST, the tool result's timestamp in the session transcript).
- **The floor** (branch `tooling/horizon-terminal`, not committed): `option_discounts`, `smdp_gae` and `pbrs_bonus`
  take `floor_ticks`, and a decision is discounted as at least that many ticks, γ_hr^(max(τ, m)/6000).
  `SMDPMaskablePPO(discount_floor_ticks=…)` passes it to its buffer and to the horizon's bootstrap; 0, the default,
  is how every run so far trained. PBRS takes the same floor, so that a floored run's shaping stays its own discount.
  The tests: hand-computed discounts and returns with the floor, in `test_smdp.py` and `test_smdp_ppo.py` (16 pass).
- **The floor's test run:** E6a γ0.9 seed 0, the horizon fix and a floor of 100 ticks (a game-minute), to 800k
  decisions, from the main checkout (E6b's worktree reverted to its branch), from 17:42:07 to 20:01:21.
- **The floor's result** (decision log): no collapse to 800k. Episodes take about 450 to 530 decisions from 500k on
  (the horizon-only test: 3,229 at 600k), and the short options are drops and bank withdrawals, not loops. The mean
  episode reward is still rising at the end, 232, against 181 and 202 for the horizon-only test and the original.
  One seed of one experiment, to 800k of a run's 2M.

## Documentation Changes

- `docs/decision-log.md`: the findings (the collapse; the horizon fix's test), and Caleb's decisions.
- This record.

## Code Changes

On branch `tooling/horizon-terminal`, not committed:
- `rlscape/agents/ppo.py`: `bootstrap_horizon` (default True) and `discount_floor_ticks` (default 0), so every run
  so far is the defaults.
- `rlscape/agents/smdp.py`: `floor_ticks` in `option_discounts`, `smdp_gae` and `pbrs_bonus`.
- `tests/test_smdp.py`, `tests/test_smdp_ppo.py`: the floor's and the horizon's tests.

Applied, uncommitted, to E6b's worktree for the first test runs (the horizon change only), then reverted.

## Infrastructure Changes

- None.

## Decisions

- **User decisions (Caleb):** diagnose first; test the horizon fix first; then test a decision floor.
- **Claude's choices:** E3's evaluation published as it ran, before any rerun decision. The floor's value, 100 ticks
  (a game-minute), offered in the question.

## Validation

- The loop's options: the last decision-log part of E3 (0, 1) seed 1, E6a γ0.9 seed 0 and E6b seeds 0 and 2
  (`loop_option.py`).
- The collapse's onset in each flagged run (`collapse_onset.py`).
- The critic's values (`critic_offset.py`, above).
- The code: `ppo.py`'s time-limit bootstrap; `pbrs.py`'s potential.
- The test runs against their originals, part by part (scratchpad `fix_compare.py`); the critic against the realised
  discounted return through the episode (`critic_bias.py`, `island_bias.py`); the advantages PPO saw for short and
  long options (`loop_advantage.py`); the policy's entropy where it loops (`loop_entropy.py`); E6b's unshaped return
  (`unshaped_return.py`).
- `uv run pytest tests/test_smdp.py tests/test_smdp_ppo.py`: 16 passed.

## Follow-Up

- Done: the floor's test held (decision log). Caleb chose to train all 50 runs again with both fixes; the rerun,
  E6b's shaping taking the same floor, and the old runs moved aside are in `m002-rerun`.
