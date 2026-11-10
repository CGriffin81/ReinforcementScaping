# Agent Interaction

## Metadata

- Interaction ID: m002-e2-ladder
- Timestamp CST: 2026-11-09 17:32:25 CST. That's the prompt, "Carry on.", the same turn as `m002-train` and
  `m002-eval-training`.
  - Caleb's answer to OQ-66 came at 20:26:57 CST. Both times are the session transcript's (UTC−06:00).
  - The sweep ran from 2026-11-09 20:37:05 to 2026-11-10 04:50:45 CST, from its runs' `config.json` `created` and
    `run.json` `finished`.
  - Its evaluation finished at 04:55:50 CST, after 253 s.
  - This record was written at about 05:15 CST on 2026-11-10 (estimated).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. E2's three rungs have run and are published, and rung 2 passes. Two things wait on Caleb: rung 1's
  verdict (OQ-68) and E3's setup (OQ-67, OQ-69).
- Commit: on branch `experiment/e2-ppo-sanity-ladder` (from `tooling/eval-training`):
  - `57a31ae`: E2's code and configs;
  - `32719ba`: OQ-66, keeping the λ 0.95 rung;
  - `e3719a3`: the λ 0.99 rung;
  - the commit that adds this record with the sweep's results.

  Also `63a6f7f` on `tooling/eval-training` (PR #14): the printed table's fix.

## Full Prompt

> Carry on.

## Response Summary

- **E2's branch,** `experiment/e2-ppo-sanity-ladder`, stacked on PR #14.
- **Rung 1's env** (`rlscape/envs/toy.py`, OQ-65 (1)):
  - work, train (masked at 40) and idle, over 20 game-hours;
  - the optimum by dynamic programming under the same γ_hr discount: 22 trainings then work, a discounted return of
    72.7, against 18.1 for always working;
  - with γ_hr 0.9 the optimum trains 12 times, with 0.5 twice: a preview of E6a.
- **Rung 1 at λ 0.95** (as OQ-65 set it, 200k decisions): 70% of the optimum, about 7.5 trainings. **It fails, by
  under-investing.**
- **Diagnosed:**
  - λ near 1 finds the investment; entropy and the learning rate barely matter;
  - λ 0.95 a decision cuts the credit for a payoff 50 to 60 decisions later;
  - treating the horizon as a true end makes things worse.
- **Asked Caleb (OQ-66):** sweep λ {0.95, 0.99} × learning rate {1e-4, 3e-4}, entropy 0.01 (recommended). Caleb took
  it.
- **Rung 1 at λ 0.99** (2M decisions): **94.9% and 94.4%** of the optimum, 13 trainings, almost no idling.
  - That's just under the 95% bar Claude proposed, so the README says "fails".
  - Whether the rung passes is for Caleb, since the bar wasn't Caleb's (OQ-68).
- **Rung 3, the sweep** (`configs/e2-ppo-sanity-ladder.yaml`): 8 runs of 1M decisions, `--jobs 4`, from a clean
  `e3719a3`, 3.8 to 4.4 hours a run.
- **Rung 2** (`configs/e2-ppo-sanity-ladder-eval.yaml`): the 8 models on E1's 30 seeds, sampled actions. Random's and
  the guide's numbers match E1's exactly.
  - **The best variant** is λ 0.95 with learning rate 3e-4: 149.6 reward an episode. The other three score 142.4,
    127.7 and 124.5.
  - **Rung 2 passes:** both of its runs beat random by +59.1 [55.0, 63.4] and +54.7 [50.1, 59.2] reward, paired over
    the seeds, and by +119 and +110 total levels.
  - **They're still below the guide:** by 10.8 and 15.1 reward, and 18 and 27 levels. They gain 2.2 and 3.0 times
    the guide's XP.
- **Found, for E3 (OQ-67):** at (.5, .5) the agents learn skill only. Δ net worth / 100,000 gp makes a level outweigh
  100,000 gp, so E3's (.75,.25) to (.25,.75) would reward skill too. Recommended: normalised weights with no sim
  change.
- **Found, for E3 to E6 (OQ-69):** the best variant is still rising at 1M decisions, so OQ-65 (3)'s rule gives 2M.
- **Fixed (PR #14):** `evaluate.py`'s printed table looked trained policies up by spec, not label, and showed no
  numbers for them. The saved files were right.

## Documentation Changes

- `docs/decision-log.md`:
  - "Found: E2's rung 1 fails at GAE λ 0.95; decided: OQ-66, the sweep varies λ and the learning rate (Caleb)", with
    the diagnostics table and the options;
  - "Found: E2's sweep and rung 2: PPO beats random; the best variant is GAE λ 0.95 with learning rate 3e-4".
- `docs/open-questions-log.md`:
  - OQ-67 (where E3's weights sit, given the wealth scale);
  - OQ-68 (does rung 1 pass);
  - OQ-69 (1M or 2M decisions for E3 to E6).
- `ROADMAP.md`: E2's sweep is λ × learning rate (OQ-66), and its results so far.
- `results/summary/e2-ppo-sanity-ladder/`:
  - the evaluation (`publish_summary.py`);
  - `training/` (`publish_training.py`);
  - `rung2/` (`scripts/e2_rung2.py`);
  - `toy-lambda0.95/` and `toy/`: rung 1's two runs.
- This record.

## Code Changes

- `rlscape/envs/toy.py` (new): `ToyEnv`, `optimum`, `returns_of`.
- `tests/test_toy.py` (new, 3 tests):
  - the rules;
  - the optimum beating every train-then-work schedule and 200 random sequences;
  - fewer trainings at a shorter discount.
- `scripts/e2_toy_rung.py` (new): trains, evaluates against the optimum, and writes the summary, refusing a dirty
  tree.
- `scripts/e2_rung2.py` (new):
  - ranks the variants by mean evaluated reward;
  - pairs each trained run with random and the guide by seed (bootstrap CIs);
  - writes `rung2/`.

  It reads the committed evaluation summary, so it needs no runs.
- `tests/test_e2_rung2.py` (new, 3 tests):
  - the ranking and the pairing;
  - the hour-20 metrics;
  - the committed `rung2/` reproduced from the committed evaluation.
- Configs:
  - `configs/e2-ppo-sanity-ladder-toy.yaml` (λ 0.99, 2M);
  - `configs/e2-ppo-sanity-ladder-toy-lambda0.95.yaml` (the first run's);
  - `configs/e2-ppo-sanity-ladder.yaml` (the sweep);
  - `configs/e2-ppo-sanity-ladder-eval.yaml` (rung 2).
- On `tooling/eval-training` (PR #14): `scripts/evaluate.py` prints the summary by label, with the label column as
  wide as the longest.

## Infrastructure Changes

- The branch `experiment/e2-ppo-sanity-ladder`, pushed.
- The sweep's runs in `runs/e2-ppo-sanity-ladder/` (git-ignored), with their decision logs.
- The evaluation in `results/eval/e2-ppo-sanity-ladder/` (git-ignored).
- The diagnostics ran in the session's scratchpad.

## Decisions

- **User decisions (Caleb):** OQ-65 (1) to (4) (record `m002-eval-training`); OQ-66 (a).
- **Agent recommendations:**
  - OQ-66 (a), which Caleb took;
  - OQ-67 (a): normalised weights, no sim change;
  - OQ-68 (a): rung 1 passes, reported with its numbers;
  - OQ-69 (a): 2M decisions, as OQ-65 (3)'s rule says.
- **Agent choices:**
  - the toy's shape (pay 1 + √k, the cap at 40, idle's minute);
  - keeping the failed run as a finding, not overwriting it;
  - rung 2's test: the CI of each best-variant run's paired reward difference against random is above 0.

## Validation

- `tests/test_toy.py` and `tests/test_e2_rung2.py`: 6 passed. `tests/test_training_tools.py` and
  `tests/test_eval_harness.py` on PR #14's branch with the print fix: 9 passed.
- The fix was checked on a 2-hour, one-seed evaluation of a trained model, whose row now prints its numbers.
- Every run comes from a clean commit: rung 1's two (`57a31ae`, `32719ba`), the sweep's eight and the evaluation
  (`e3719a3`).
- `publish_summary.py` and `publish_training.py` accepted them.
- The behaviour described in the decision log comes from the best variant's training decision logs.

## Follow-Up

- **Caleb:**
  - OQ-68: does rung 1 pass at 94.4% to 94.9%?
  - OQ-67 and OQ-69, before E3's configs (Nov 12);
  - merge PRs #13 and #14, then E2's.
- **Claude:** E3's configs once OQ-67 and OQ-69 are answered.
