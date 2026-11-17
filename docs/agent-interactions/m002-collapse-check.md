# Agent Interaction

## Metadata

- Interaction ID: m002-collapse-check
- Timestamp CST: 2026-11-16 19:32:45 CST (the prompt) and 19:55:52 CST (Caleb's answer in the question dialog), the
  session transcript's timestamps (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The check ran on the rerun's nine finished seed-0 runs. One collapses, and Caleb chose to carry on
  and report it.
- Commit:
  - `a06bbff`, to `main` directly (Caleb: "Commit it to main directly", 20:04:21 CST);
  - the run check's update (21:01:47 CST): this commit, to `main` directly (Caleb: "Commit it to main directly",
    21:47:09 CST).

## Full Prompt

> Run the collapse check on the seed-0 runs

The question dialog asked how the experiments should handle collapsed runs. The options were: carry on and report it;
also evaluate a pre-collapse checkpoint; or fix the loot loop and rerun all 50. Caleb's answer:

> "Carry on, report it (Recommended)"

Then (20:04:21 CST):

> Commit it to main directly

And (21:01:47 CST):

> Check on the runs.

Then (21:47:09 CST):

> Commit it to main directly

## Response Summary

- **The check** (`m002-rerun`'s follow-up): each finished seed-0 run of the rerun beside its first-round original
  (`runs/<name>-bootstrap`), in 100k-decision blocks. For each block:
  - the training episodes' mean decisions (a collapsed run's episodes take thousands);
  - the share of decisions of 8 ticks or less, and the mean option length;
  - the mean episode reward.

  It also checked each run's config. The collapse marker is a block whose episodes average over 1,000 decisions.
- **The runs:** E3's five seed-0 runs, E6a γ_hr 0.9's, E4's, E6b's and E5's. E6a γ_hr 0.5's seed 0 failed on the
  sim v1.3 bug (`m002-tan-guard`), so it isn't among them.
- **Configs:** all nine have `cuda`, `bootstrap_horizon: false`, `discount_floor_ticks: 100`, `git_dirty: false`, and a
  `run.json`.
- **One of the nine collapses: E3's (.75, .25) seed 0, at 1.5M decisions.**
  - **Decisions an episode:** 1,906 in the 1.5M block, then 10,559 to 21,631.
  - **What it loops on:** from 1.6M, 97–98% of its decisions are the three loot-setting options (`loot_all`,
    `loot_valuable`, `loot_none`), each completing in 8 ticks or less with no skill or wealth reward. They were already
    23–47% of its decisions from 1.0M to 1.4M.
  - **Reward:** its mean episode reward peaks at 261.2 (1.4M) and ends at 204.9.
  - **Its original didn't collapse.** It ended at 237.1, with about 167 decisions an episode.
- **The others** (the last block's mean episode reward, rerun against original; training episodes, sampled actions):

  | Run | Collapse, rerun | Collapse, original | Reward, rerun | Reward, original |
  |---|---|---|---|---|
  | E3 (1, 0) | – | – | 365.9 | 310.6 |
  | E3 (.75, .25) | 1.5M | – | 204.9 (peak 261.2) | 237.1 |
  | E3 (.5, .5) | – | – | 233.1 | 177.4 |
  | E3 (.25, .75) | – | – | 161.4 | 544.7 |
  | E3 (0, 1) | – | – | 745.2 | 710.0 |
  | E6a γ_hr 0.9 | – | 500k | 254.6 | 62.3 |
  | E4 | – | – | 106.2 (peak 137.0) | 131.6 (peak 158.8) |
  | E6b (unshaped) | – | 200k | 331.3 | 164.7 |
  | E5 | – | – | 206.1 | 246.3 |

  - **E3 (0, 1) dips and recovers.** Its reward falls from about 700 to 331–392 between 1.0M and 1.4M. In that stretch
    the loot-setting options and GE repeats rise to about 30% of its decisions. It is back to 700 by 1.7M and ends at
    745.
  - **E4 drifts.** Its decisions an episode rise from 191 to 760, and its share of decisions of 8 ticks or less from 14%
    to 52%. The zero-effect ones spread over many options, none above 5%: melee gear withdrawals, worn-item deposits,
    GE buys and sells. Its task reward falls from 146.7 (block 0) to 94.0. Its original fell too, from 158.8 at 800k to
    131.6. Like the RND bonus, this rewards changing the observation; that's a hypothesis, untested.
  - **E3 (.25, .75)** settles on a lower strategy than its original. From 1.3M it holds about 161 reward and 0.93M
    net worth, against the original's 545 and 3.8M. In the first round, seed 2 of the same weighting also settled
    low (182.7).
  - **E3 (.5, .5)** keeps 31–44% of its decisions as short zero-effect ones. Most are bank withdrawals for a fishing or
    mining trip, which set up the trip, not loops.
- **The first round, for comparison** (all 50 runs, the same marker):
  - 11 pass 1,000 decisions an episode in some block;
  - 8 end looping, at tens of thousands of decisions an episode: E3's (0, 1) seed 1, E6a γ_hr 0.9's seeds 0 and 3,
    and E6b's five. These are ROADMAP's 8;
  - 3 pass it briefly or at the margin: E6a γ_hr 0.5 seed 0 (1,003 at the end), γ_hr 0.9 seed 2 (1,540 in the last
    block) and seed 4 (from 400k, then 867 at the end);
  - among the same nine seed-0 runs, the first round's loopers were E6a γ_hr 0.9's and E6b's. The rerun has one.

  In the question I wrote "11 of 50 collapse": that is the first count; 8 ended looping.
- **Asked Caleb** how the experiments should handle collapsed runs (the options are in the decision log). **Caleb:
  carry on, report it.**
- **The failed run:** after the queue relaunch (`m002-tan-guard`), E6a's γ_hr 0.5 seed 0 started again at 19:57:39,
  when E3's (1, 0) seed 1 finished. Its `config.json` has E6a's merge of `main` (`176e4d6`, sim v1.4), a clean tree,
  `cuda` and both fixes.
- **The run check (Caleb: "Check on the runs.", 21:01:47 CST):**
  - **The queue:** no failure since 05:47. Eleven of the 50 are done; E3's (1, 0) seed 1 finished at about 19:56.
    Five are training: E3's (0, 1), (.25, .75), (.5, .5) and (.75, .25) seed 1, at 1.6M, 1.1M, 1.5M and 1.3M
    decisions at 21:02, and E6a's γ_hr 0.5 seed 0.
  - **Speed** over 15 minutes: 423 decisions a second in all; E3's (0, 1) seed 1 makes 151.
  - **RAM:** 5.8 GB available, 7 hard page reads a second, the CPU at 70%. OQ-81's rule doesn't fire.
  - **E6a's γ_hr 0.5 seed 0 repeats its failed run:**
    - its decision parts 0 to 4 (250k decisions) have the same SHA-256 as the failed run's;
    - it passed the failed run's crash point (about 278k decisions; that part was written at 05:39 and the run failed
      at 05:47);
    - its part 5 (250k to 300k, written at 21:25) holds 3,444 tanning decisions, and its log has no error.
  - **The training E3 seed-1 runs** (by 50k-decision part, against their originals):
    - **E3 (0, 1) seed 1:** 347 to 355 decisions an episode and 1% short decisions through 1.55M. Its original
      collapsed at 1.5M, onto 25,000 decisions an episode. Its speed comes from a policy that's cheap to simulate.
    - **E3 (.5, .5) seed 1:** crossing the marker. From 1.2M it takes 1,350 to 1,920 decisions an episode, and 60–65%
      of its decisions are short with no effect: bank deposits, withdrawals for a trip, and the loot-setting options
      (10–22%). Its reward an episode holds at about 211 to 214 (peak 229.7 at 800k). Its original didn't collapse.
      As Caleb decided, it carries on.
    - **E3 (.75, .25) and (.25, .75) seed 1:** about 330–400 and 105–120 decisions an episode, no collapse.

## Documentation Changes

- `docs/decision-log.md`: the check's findings, the options and Caleb's answer.
- This record.

## Code Changes

- None. The check's scripts are in the session scratchpad: `collapse_check.py` (a run beside its original),
  `loop_options.py` (what a run's short decisions are), `collapse_census.py` (every run of a round), `live_check.py`
  (a training run's parts beside its original's) and `part_tanning.py` (a part's tanning decisions).

## Infrastructure Changes

- None.

## Decisions

- **User decision (Caleb):** carry on; each run's final model is evaluated as planned, and the report gives each
  round's collapse count and names the looping runs.
- **Claude's choices:**
  - the marker (a 100k block over 1,000 decisions an episode);
  - the zero-effect test (a decision with no skill and no wealth reward).

## Validation

- The check reads each run's `episodes.parquet` and its decision log's `step`, `duration`, `option`, `termination`,
  `r_skill` and `r_wealth` columns, read-only, beside the five training runs. Available RAM was 5.1 GB at 19:33.
- E6a γ_hr 0.9's rerun matches the floor test's finding (`m002-collapse-diagnosis`): 450–530 decisions an episode
  from 500k, and a quarter to a third of the decisions short.

## Follow-Up

- **Done:** E6a's γ_hr 0.5 seed 0 repeats its failed run's 250k decisions and is past the crash.
- **Claude:** run the same census on every rerun as it finishes. The report's collapse counts come from the full 50.
