# Agent Interaction

## Metadata

- Interaction ID: m002-oq79-rnd-centring
- Timestamp CST: 2026-11-11 18:09:30 CST, the prompt's timestamp in the session transcript (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: COMPLETE. E4's centred bonus is centred on a recent mean, tested, and E4 has joined the training queue.
- Commit: on `experiment/e4-rnd-exploration`.

## Full Prompt

> Go with (a) for OQ-79 and add E4

## Response Summary

- **Built (OQ-79 (a))** in `rlscape/agents/rnd.py`:
  - `RecentStats` is an exponential moving average of the error's mean and second moment over `ema_rollouts` × the
    rollout's steps (10 rollouts), bias-corrected as Adam's moments are.
  - A centred bonus uses it. The uncentred one keeps `RunningMeanStd`.
  - `ema_rollouts` is an `rnd` key (default 10), stated in E4's config.
- **E4's test kept failing with it,** and the reason changed what the recommendation had said:
  - That test looks at 5 rollouts of 8 steps, inside a 10-rollout window, where the recent mean is the cumulative one.
  - With a one-rollout window, the bonus was still mostly negative, because the predictor learns fastest at first.
- **Measured at E4's scale:** 4 envs, rollouts of 256 steps, E4's features and coef, random actions, 20 rollouts. The
  errors were centred both ways from the same run.
  - Over the first 10 rollouts the error falls from 0.98 to about 0.3, and both centrings average about −0.5 spreads.
  - Over rollouts 12 to 20, the recent one averages about −0.2 and the cumulative one about −0.3.
  - So (a) shortens the drift; it doesn't remove it in the first one or two percent of a run. "About zero at every
    stage" holds once the error levels off. The docs say this.
- **The tests:**
  - A unit test now checks the mechanism: on a falling error, the recent mean is back at about zero within its
    window, while the cumulative one stays below.
  - The short integration test keeps what holds in its first rollouts: both signs appear, and centring takes most of
    the uncentred bonus's mean away. Its "|mean| < 0.5 spreads" failed under either centring at that length.
- **E4 added to the training queue,** which was restarted with E4's config. Only the queue's own process was stopped;
  the runs it had started kept training.

## Documentation Changes

- **On `tooling/units-v1.2`:** OQ-79 moved from the open-questions log to the decision log ("Decided: OQ-79"), with
  the measurement.
- **On E4's branch:** "Built: E4's bonus centred on a recent mean" in the decision log, and this record.

## Code Changes

- `rlscape/agents/rnd.py`: `RecentStats`; the `ema_rollouts` key; the docstring.
- `configs/e4-rnd-exploration.yaml`: `ema_rollouts: 10`.
- `tests/test_rnd.py`: the unit test, and the integration test's claims.

## Infrastructure Changes

- **The training queue** restarted with E4 added: PID 10900 (uv), 2026-11-11 18:29:38 CST, from
  `D:\ReinforcementScaping-int`, log `D:\ReinforcementScaping\runs\train-queue.log` (the first part's renamed
  `train-queue-v1.2-part1.log`). 50 runs from 5 experiments; E3's four seed-0 runs kept training; E4's seed 0 is
  eighth.

## Decisions

- **User decision (Caleb):** OQ-79 (a), and add E4.
- **Agent choices:**
  - the bias-corrected moving average;
  - the window as a config key, stated in E4's config;
  - the cumulative statistics kept for the uncentred bonus;
  - the integration test's claims changed to what holds at its length, with the mechanism tested directly.

## Validation

- **`tests/test_rnd.py` and `tests/test_training.py`:** 11 passed.
- **The measurement at E4's scale,** as above.

## Follow-Up

- **Caleb:** E4's branch is pushed; it merges into `main` by its own PR once its runs are checked.
