# Agent Interaction

## Metadata

- Interaction ID: m002-collapse-check
- Timestamp CST: 2026-11-16 19:32:45 CST (the prompt), 19:55:52 CST (Caleb's answer in the question dialog), and
  the run checks at 21:01:39 and 23:32:02 CST and on 2026-11-17 at 07:08:22 CST, the session transcript's timestamps
  (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The check ran on the rerun's nine finished seed-0 runs. One collapses, and Caleb chose to carry on
  and report it.
- Commit:
  - `a06bbff`, to `main` directly (Caleb: "Commit it to main directly", 20:04:21 CST);
  - the run check's update (21:01:39 CST): `079009c`, to `main` directly (Caleb: "Commit it to main directly",
    21:47:00 CST);
  - the second run check (23:32:02 CST) and the corrections: `c895905`, to `main` directly (Caleb: "Commit it to
    main directly", 23:51:48 CST);
  - the third run check (2026-11-17 07:08:22 CST) and `m002-loop-cause`'s correction: this commit, to `main`
    directly (Caleb: "Commit it to main directly", 07:24:25 CST).

## Full Prompt

> Run the collapse check on the seed-0 runs

The question dialog asked how the experiments should handle collapsed runs. The options were: carry on and report it;
also evaluate a pre-collapse checkpoint; or fix the loot loop and rerun all 50. Caleb's answer:

> "Carry on, report it (Recommended)"

Then (20:04:21 CST):

> Commit it to main directly

And (21:01:39 CST):

> Check on the runs.

Then (21:47:00 CST):

> Commit it to main directly

And (23:32:02 CST):

> Check on the runs.

Then (23:51:48 CST):

> Commit it to main directly

And (2026-11-17 07:08:22 CST):

> Check on the runs.

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
  - **What it loops on:** from 1.6M, 97–98% of its decisions are three of the four loot-setting options (`loot_all`,
    `loot_valuable`, `loot_none`; the fourth is `loot_vocabulary`), each completing in 8 ticks or less with no skill or
    wealth reward. They were already 23–47% of its decisions from 1.0M to 1.4M.
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
- **The run check (Caleb: "Check on the runs.", 21:01:39 CST):**
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
      (7–43% by part; first written as 10–22%, see the corrections below). Its reward an episode holds at about 211 to
      214 (peak 229.7 at 800k). Its original didn't collapse. As Caleb decided, it carries on.
    - **E3 (.75, .25) and (.25, .75) seed 1:** about 330–400 and 105–120 decisions an episode, no collapse.
- **The second run check (Caleb: "Check on the runs.", 23:32:02 CST):**
  - **The queue (PID 9884):** no failure in its log since its relaunch, and `train-queue.err` is empty.
    - **Done:** 14 of the 50. Since 21:02, E3's (0, 1), (.5, .5) and (.25, .75) seed 1 finished, at 21:46, 22:38 and
      23:29.
    - **Started:** E6a's γ_hr 0.5 seed 1 at 21:48, its γ_hr 0.9 seed 1 at 22:39, and E4's seed 1 at 23:31.
    - **Training at 23:36:** E3's (.75, .25) seed 1 (1.75M decisions; it ends at about 01:10), E6a's γ_hr 0.5 seed 0
      (800k) and seed 1 (350k), its γ_hr 0.9 seed 1 (150k), and E4's seed 1 (just started).
  - **Speed,** in 15-minute windows over the last 3 hours (scratchpad `rate_history.py`):
    - E6a's γ_hr 0.5 seed 0: 53 to 72 decisions a second, rising;
    - E6a's γ_hr 0.5 seed 1 and γ_hr 0.9 seed 1: 57 to 60;
    - E3's (.75, .25) seed 1: 38 to 47.
    - No window falls below 80% of the one before.
  - **RAM:** 3.3 GB available, 6 to 162 hard page reads a second, and the CPU at 78–81%. OQ-81's rule doesn't fire.
  - **What's left:** about 71M of the 100M decisions. At the 330 to 420 decisions a second that five runs have made
    today, that's 47 to 60 hours, so the last run ends between late Nov 18 and midday Nov 19.
  - **The training runs** (by 50k-decision part, against their originals):
    - **E6a's γ_hr 0.5 seed 0:** 156 to 360 decisions an episode and 1–13% short decisions through 800k. Its original
      took 667 to 1,000 decisions an episode from 150k, with 33–58% of them short.
    - **E6a's γ_hr 0.5 seed 1** (187 to 217 decisions an episode) and **γ_hr 0.9 seed 1** (113 to 245): both near
      their originals so far.
    - **E3's (.75, .25) seed 1:** 327 to 490 decisions an episode from 1.0M, and 27–43% of them short. From 1.3M,
      8–23% of its decisions are the loot-setting options (all four counted). No collapse at 1.75M. Its original
      took 112 to 159 decisions an episode.
  - **The four E3 seed-1 runs that are done** (scratchpad `collapse_e3_s1.txt`; the last block's mean training
    reward, rerun against original). All four have `cuda`, no horizon bootstrap, the 100-tick floor and a clean tree.

    | Run | Collapse, rerun | Collapse, original | Reward, rerun | Reward, original |
    |---|---|---|---|---|
    | E3 (1, 0) seed 1 | – | – | 361.0 | 312.7 |
    | E3 (.5, .5) seed 1 | 1.2M | – | 207.0 (peak 229.8) | 369.9 |
    | E3 (.25, .75) seed 1 | – | – | 155.4 | 552.3 |
    | E3 (0, 1) seed 1 | – | 1.5M | 479.9 | 0.1 (peak 117.4) |

    - **E3 (.5, .5) seed 1 ends over the marker.**
      - Its last block takes 1,730 decisions an episode, and 71% of its decisions are short with no effect.
      - From 1.3M, its top short decisions are the loot-setting options (`loot_none`, `loot_vocabulary` and
        `loot_valuable` together are 52% in the last block), bank deposits, and withdrawals for a trip.
      - Its original found a 3.2M net-worth strategy at 1.8M. The first round's other four (.5, .5) seeds end at
        168.6 to 179.7.
    - **E3 (.25, .75) seed 1 settles low, like the rerun's seed 0** (161.4). It holds 0.8M to 0.9M net worth from
      700k, against its original's 3.9M.
      - In the first round, four of the five (.25, .75) seeds end at 544.7 to 563.2; seed 2 settled at 182.7.
      - In the rerun, neither seed has found it so far.
    - **E3 (0, 1) seed 1 doesn't collapse; its original did.**
      - It holds one strategy from 500k: 350 decisions an episode, 1% short, and 2.6M net worth.
      - It ends at 479.9, below the rerun's seed 0 (745.2) and the first round's other four (0, 1) seeds (704.3 to
        764.6).
    - **E3 (1, 0) seed 1** gains on its original. Its short decisions rise to 33%, but its reward still climbs at the
      end.
  - **The rerun's census so far** (13 finished runs): 2 pass the marker, E3's (.75, .25) seed 0 and (.5, .5) seed 1,
    and both end over it. Among the same 13 runs, the first round had 3 ending looping: E3's (0, 1) seed 1, E6a's
    γ_hr 0.9 seed 0 and E6b's seed 0.
- **The third run check (Caleb: "Check on the runs.", 2026-11-17 07:08:22 CST):**
  - **The queue (PID 9884):** no failure in its log, and `train-queue.err` is empty.
    - **Done:** 16 of the 50. Overnight, E3's (.75, .25) seed 1 finished at 00:32, and E6a's γ_hr 0.5 seeds 0 and 1
      at 04:32 and 05:42.
    - **Started:** E6b's seed 1 at 00:33, E5's seed 1 at 04:33, and E3's (1, 0) seed 2 at 05:44.
    - **Training at 07:15:** E6a's γ_hr 0.9 seed 1 (about 1.7M decisions), E4's seed 1 (1.65M), E6b's seed 1
      (1.25M), E5's seed 1 (550k) and E3's (1, 0) seed 2 (300k).
  - **Speed:** 50 to 66 decisions a second a run over the last 15 minutes, 299 in all. Over the last 4 hours, no
    15-minute window falls below 80% of the one before.
  - **RAM,** sampled every 5 seconds for a minute:
    - 2.3 to 3.6 GB available;
    - 3 to 788 hard page reads a second (two samples over 250);
    - 0.4 to 1.7 GB on the free list.

    OQ-81's rule doesn't fire.
  - **What's left:** about 62.5M of the 100M decisions.
    - From 23:32 to 07:15 the runs made about 8.5M decisions, about 306 a second.
    - At 300 to 330 a second, the rest takes 53 to 58 hours. The last run ends between about noon and 17:00 on
      Nov 19.
    - The 23:32 estimate (late Nov 18 to midday Nov 19) assumed 330 to 420 a second.
  - **E3's (.75, .25) seed 1 loops in its last block** (scratchpad `collapse_0715.txt`):
    - At 1.9M, it takes 5,271 decisions an episode, and 95% of them are short (15 episodes in the block). The block
      before took 614.
    - Its reward an episode is 269.3 in the last block (peak 282.1 at 1.7M). That's still above its original's 239.8.
    - So (.75, .25) loops on both rerun seeds. `m002-loop-cause`, written while this run was at about 1.75M, said its
      seed 1 didn't. It's corrected there.
  - **E6a's γ_hr 0.5 seeds 0 and 1 don't loop:**
    - Seed 0 takes 452 decisions an episode in its last block, 10% of them short. Its original passed the marker at
      1.3M and ended at 1,003.
    - Seed 1 takes 463, 9% of them short.
  - **The rerun's census** (16 finished runs; scratchpad `census_rerun_0710.txt`):
    - 3 end looping: E3's (.75, .25) seeds 0 and 1, and its (.5, .5) seed 1.
    - Among the same 16, the first round had 4 ending looping: E3's (0, 1) seed 1, E6a's γ_hr 0.5 seed 0 (1,003, at
      the margin), its γ_hr 0.9 seed 0, and E6b's seed 0.
    - None of the 16 loops in both rounds.
  - **At mixed weights, no rerun run has found the first round's Gem Store loop.**
    - **The strategy** is OQ-57 (a)'s loop: buy uncut emeralds at Hervi's Gem Store (`buy_shop_1621`, 50 gp each),
      then sell them on the frozen GE (985 gp) or bank them. Net worth values them at 985.
    - **How the runs use it,** in their last decision part (its last 896 decisions; scratchpad
      `strategy_time_0715.txt`):
      - the first round's E3 (.25, .75) seed 0: 52% of the game time buying, 30% selling on the GE;
      - its E6a γ_hr 0.5 seed 1: 56% buying, 32% banking, 6% selling;
      - the rerun's E3 (0, 1) seed 0: 58% buying, 37% selling;
      - the rerun's (.25, .75) seed 0 chops and fletches logs (88% of its time) and chops yews (9%);
      - the rerun's E6a γ_hr 0.5 seed 1 fishes and cooks shrimp (54%) and pickpockets master farmers (31%).
    - **The runs**, by the last 100k block's means (scratchpad `wealth_rounds_0715.txt`):

    | Run | Net worth, rerun | Net worth, original | Total level, rerun | Total level, original | Reward, rerun | Reward, original |
    |---|---|---|---|---|---|---|
    | E3 (.25, .75) seed 0 | 0.93M | 3.82M | 164 | 108 | 161.4 | 544.7 |
    | E3 (.25, .75) seed 1 | 0.90M | 3.88M | 160 | 104 | 155.4 | 552.3 |
    | E3 (.5, .5) seed 0 | 1.19M | 0.19M | 278 | 349 | 233.1 | 177.4 |
    | E3 (.5, .5) seed 1 | 0.82M | 3.20M | 294 | 182 | 207.0 | 369.9 |
    | E6a γ_hr 0.5 seed 0 | 0.97M | 1.72M | 343 | 350 | 245.6 | 318.1 |
    | E6a γ_hr 0.5 seed 1 | 1.09M | 4.13M | 331 | 112 | 251.2 | 418.4 |
    | E6a γ_hr 0.9 seed 0 | 1.12M | 0.08M | 333 | 142 | 254.6 | 62.3 |
    | E3 (0, 1) seed 0 | 4.06M | 3.87M | 36 | 58 | 745.2 | 710.0 |
    | E3 (0, 1) seed 1 | 2.61M | 0.00M | 41 | 36 | 479.9 | 0.1 |

    - **In the first round,** 12 runs ended at 3.2M to 4.2M net worth and a total level of 50 to 182, like the two
      originals whose options were checked above. The loop is likely the strategy of all 12; only those two were
      checked. The 12 are:
      - at (.25, .75): 4 of 5 seeds;
      - at (.5, .5): E3's seed 1 of 5, and E6a γ_hr 0.5's seeds 1, 2 and 4;
      - at (0, 1): 4 of 5 (seed 1 collapsed).
    - **In the rerun,** the seven mixed-weight runs hold 0.8M to 1.2M at levels 160 to 343. E6a's γ_hr 0.9 seed 0 is
      one of the seven.
      - Four of them pair with an original that found the loop. They earn 40% to 72% less than those originals.
      - At (0, 1), seed 0 finds the loop (4.06M).
      - Three pair with an original that didn't find the loop. The rerun earns more on two of them, E3's (.5, .5)
        seed 0 and E6a's γ_hr 0.9 seed 0 (whose original looped). It earns less on E6a's γ_hr 0.5 seed 0: 245.6
        against 318.1, where the original held 1.72M.
    - **What changed between the rounds:**
      - the trainer: no horizon bootstrap, and the 100-tick floor;
      - the sim: E3's runs moved from v1.2 to v1.3 (`died()`, the death-budget cap), and E6a's from v1.3 to v1.4
        (the tan guard). Neither touches shops, the GE or net worth.

      Which change moves the runs off the loop, or whether it's chance, is untested.
    - **Claude's reading** (an inference):
      - The floor is an unlikely cause. Its charge falls on decisions under 100 ticks, and the loop's originals take
        0–1% decisions of 8 ticks or less in most blocks.
      - Chance looks unlikely too. Suppose each rerun run found the loop as often as the first round's seeds of its
        variant did: 4 of 5 at (.25, .75), 1 of 5 for E3 at (.5, .5), 3 of 5 for E6a γ_hr 0.5. Then the six rerun
        runs at those variants would all miss it about 0.4% of the time (0.2² × 0.8² × 0.4²).
      - But that test was chosen after seeing the result, and it rests on six runs.
    - **If seeds 2 to 4 also miss it,** E3's front and E6a's comparison differ between the two trainers. Under the
      rerun's trainer, the mixed weights get a mixed strategy, not the Gem Store loop.
  - **The training runs,** by 50k-decision part against their originals, without the part being written:
    - **E6a's γ_hr 0.9 seed 1:** 160 to 189 decisions an episode from 1.2M, 11–15% of them short, and under 1%
      loot-setting. Its original took 543 to 893, with 33–61% short.
    - **E4's seed 1 is rising:** 455 to 658 decisions an episode from 1.2M, 39–44% short, and 1% loot-setting. Its
      original rose to 602 by 1.55M and ended at 524.
    - **E6b's seed 1 is rising:** 581 to 725 from 700k, 32–37% short, and 5–7% loot-setting. Its original looped from
      700k, with all its decisions loot-setting.
    - **E5's seed 1** (to 500k) and **E3's (1, 0) seed 2** (to 250k): 132 to 187 decisions an episode from 50k, near
      their originals.

    E4's and E6b's seed 1 are the runs to watch. Neither is near the marker.
  - **Corrections to the earlier counts:** by the runs' `run.json` times, 10 runs were done at 21:02 and 13 at 23:32,
    not 11 and 14. The 23:32 census and follow-up already said 13.
- **Corrections to `079009c`:**
  - **The loot-setting options are four** (`loot_all`, `loot_valuable`, `loot_vocabulary`, `loot_none`).
    - The live check's loot share (`live_check.py`) counted three, without `loot_vocabulary`. With all four, E3's
      (.5, .5) seed 1 had 7–43% loot-setting decisions by part from 1.2M to 1.5M, not 10–22%.
    - E3's (.75, .25) seed 0 finding holds with all four counted: 95–99% by part from 1.55M, the three named, and
      `loot_vocabulary` hardly at all. "The three loot-setting options" now reads "three of the four", here and in
      the decision log.
  - **Two prompt times were off.** The run check's prompt was at 21:01:39 and the commit's at 21:47:00. The record had
    21:01:47 and 21:47:09, which are times of the replies, not of the prompts' user entries.

## Documentation Changes

- `docs/decision-log.md`: the check's findings, the options and Caleb's answer. From the second run check, its
  collapsed run's loop reads "three of the four loot-setting options".
- This record.

## Code Changes

- None. The check's scripts are in the session scratchpad: `collapse_check.py` (a run beside its original),
  `loop_options.py` (what a run's short decisions are), `collapse_census.py` (every run of a round), `live_check.py`
  (a training run's parts beside its original's) and `part_tanning.py` (a part's tanning decisions).
- From the second run check:
  - `rate_history.py` (each live run's speed in 15-minute windows);
  - `entry_times.py` (a transcript entry's type and time);
  - `live_check.py` now counts all four loot-setting options;
  - `collapse_check.py` takes a seed (`"E3 (.5, .5) s1"`).
- From the third run check:
  - `collapse_check.py` has E6a's γ_hr 0.5 (`"E6a g0.5"`);
  - `wealth_rounds.py` (each finished run's last block, net worth, level and reward, in both rounds);
  - `strategy_time.py` (a finished run's options by game time in its last part).

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
- The second run check read only finished runs' files and decision parts whose size had stopped changing. Available RAM
  was 3.3 GB at 23:32.
- The third run check read finished runs' files only. For the training runs, it copied each decision part but the
  newest and read the copies. Available RAM was 2.3 to 3.6 GB at 07:14.
- The sim versions come from each run's `config.json` `git_sha`, checked against the `sim-v1.*` tags
  (`git merge-base --is-ancestor`). The sim diff between the rounds (`git diff` of `rlscape/sim/`) is the death-budget
  cap in `fishing.py` and `gathering.py` for E3, and the tan guard in `crafting.py` for E6a.
- E6a γ_hr 0.9's rerun matches the floor test's finding (`m002-collapse-diagnosis`): 450–530 decisions an episode
  from 500k, and a quarter to a third of the decisions short.

## Follow-Up

- **Done:** E6a's γ_hr 0.5 seed 0 repeats its failed run's 250k decisions and is past the crash.
- **Claude:** run the same census on every rerun as it finishes. The report's collapse counts come from the full 50.
  At 23:32, 13 are done, and 2 of them end over the marker. At 07:15, 16 are done, and 3 of them end over it.
- **For the analysis:** at mixed weights, no rerun run has found the first round's Gem Store loop so far. That's
  seven runs: E3's (.25, .75) and (.5, .5), and E6a's γ_hr 0.5 and 0.9.
  - If seeds 2 to 4 do the same, the weighting's result differs between the two trainers.
  - Which change causes it is untested.
  - E3's (.5, .5) and (.25, .75) seed 2 are the queue's 23rd and 24th runs, after (.75, .25) seed 2.
- **Watch:** E4's and E6b's seed 1, both rising toward the marker.
