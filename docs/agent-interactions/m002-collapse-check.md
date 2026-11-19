# Agent Interaction

## Metadata

- Interaction ID: m002-collapse-check
- Timestamp CST: 2026-11-16 19:32:45 CST (the prompt), 19:55:52 CST (Caleb's answer in the question dialog), and
  the run checks at 21:01:39 and 23:32:02 CST and on 2026-11-17 at 07:08:22, 13:35:36 (Caleb's answer in the
  question dialog at 13:45:54 CST), 16:18:35 and 22:02:46 CST (Caleb's answer in the question dialog at 19:39:22
  CST), and on 2026-11-18 at 15:28:13 CST, the session transcript's timestamps (UTC−06:00).
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
  - the third run check (2026-11-17 07:08:22 CST) and `m002-loop-cause`'s correction: `dc08b5a`, to `main`
    directly (Caleb: "Commit it to main directly", 07:24:25 CST);
  - the fourth run check (13:35:36 CST) and the speed-rule decision: `5112c23`, to `main` directly (Caleb: "Commit
    it to main directly", 13:50:38 CST);
  - the fifth run check (16:18:35 CST) and the banking loop's notes in `m002-loop-cause` and the post-project gap:
    `bf02845`, to `main` directly (Caleb: "Commit it to main directly", 16:54:58 CST);
  - the RAM-rule decision (19:39:22 CST), the sixth run check (22:02:46 CST), the seventh run check (2026-11-18
    15:28:13 CST) and the corrections to E4's and E6b's rewards: this commit, to `main` directly (Caleb: "Commit it to
    main directly", 2026-11-18 15:55:35 CST).

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

Then (07:24:25 CST):

> Commit it to main directly

And (13:35:36 CST):

> Check on the runs.

The question dialog asked whether to keep five jobs or go back to `--jobs 4` after the speed rule fired. Caleb's
answer (13:45:54 CST):

> "Keep five (Recommended)"

Then (13:50:38 CST):

> Commit it to main directly

And (16:18:35 CST):

> Check on the runs.

Then (16:54:58 CST):

> Commit it to main directly

The midnight watch's RAM rule fired at 18:45:35. The question dialog asked whether to keep five jobs or go back to
`--jobs 4`. Caleb's answer (19:39:22 CST):

> "Keep five (Recommended)"

And (22:02:46 CST):

> Check on the runs.

And (2026-11-18 15:28:13 CST):

> Check on the runs.

Then (15:55:35 CST):

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
  | E6b | – | 200k | 129.9 | 0.0 (1.7M) |
  | E5 | – | – | 206.1 | 246.3 |

  - **E3 (0, 1) dips and recovers.** Its reward falls from about 700 to 331–392 between 1.0M and 1.4M. In that stretch
    the loot-setting options and GE repeats rise to about 30% of its decisions. It is back to 700 by 1.7M and ends at
    745.
  - **E4 drifts.** Its decisions an episode rise from 191 to 760, and its share of decisions of 8 ticks or less from 14%
    to 52%. The zero-effect ones spread over many options, none above 5%: melee gear withdrawals, worn-item deposits,
    GE buys and sells. Its reward falls from 129.8 (block 0; 137.0 at 100k) to 106.2. Its original fell too, from 158.8
    at 800k to 131.6. Like the RND bonus, this rewards changing the observation; that's a hypothesis, untested.
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
- **The fourth run check (Caleb: "Check on the runs.", 13:35:36 CST):**
  - **The queue (PID 9884):** no failure in its log, and `train-queue.err` is empty.
    - **Done:** 20 of the 50. Since 07:15, four finished:
      - E6a's γ_hr 0.9 seed 1, at 08:39;
      - E4's seed 1, at 08:48;
      - E6b's seed 1, at 10:40;
      - E5's seed 1, at 13:14.
    - **Started:** E3's seed 2 at (.75, .25) at 08:40, at (.5, .5) at 08:49, at (.25, .75) at 10:41, and at (0, 1) at
      13:15.
    - **Training at 13:40:** E3's five seed-2 runs. They're at about 1.6M decisions for (1, 0), 1.05M for (.75, .25),
      0.95M for (.5, .5), 0.8M for (.25, .75) and 0.1M for (0, 1).
  - **What's left:** about 55.4M decisions.
    - From 07:15 to 13:40 the runs made about 7.1M, about 308 a second.
    - At 300 to 330 a second, the rest takes 47 to 51 hours. The last run ends on Nov 19, about 13:00 to 17:00.
  - **RAM:**
    - At 13:36, 1.8 to 2.0 GB was available, falling as E3's (0, 1) seed 2 grew (a 3.2 GB working set). By 13:43 it
      was 3.5 GB.
    - Hard page reads ran at 0 to 39 a second at 13:36. One 5-second sample hit 4,255 at 13:42:50, during Claude's reads
      of the runs' files, with 3.5 GB available.

    The RAM and paging rules don't fire.
  - **The speed rule fired once** (scratchpad `rate_history.py`):
    - **E3's (.75, .25) seed 2** made 69.8 decisions a second from 12:52 to 13:07. Then it made 51.8 from 13:07 to
      13:22 (74%), 47.3 from 13:22 to 13:37, and 45.6 over the 4 minutes to 13:41.
    - **It began with a run's start:** E3's (0, 1) seed 2 started at 13:15, in the slot E5's seed 1 left at 13:14.
    - **The machine wasn't short:**
      - the total held at 299 to 318 a second (307 at 13:41);
      - the CPU was at 59–67%;
      - the other runs held or rose over the same windows: (.25, .75) 79.8 to 88.4, (1, 0) 53.8 to 57.2, (0, 1) 80.5
        to 88.1. (.5, .5) moved between 46.9 and 53.8.
    - **The slow run doesn't loop:** 314 decisions an episode at 950k, 28% of them short, 1% loot-setting.
    - **Asked Caleb** (the options are in the decision log). **Caleb (13:45:54 CST): keep five.**
    - **Watched until midnight,** from 13:47:
      - the runs' total speed every 15 minutes against the 15 before (scratchpad `total_watch.py`, log
        `total_watch_1117.log`), where a fall below 80% asks again;
      - RAM under 1 GB for a minute, and paging while RAM is under 2 GB (`watch_lows.ps1` on `trial_sample6.csv`, a
        10-second sampler).
  - **The four runs done since 07:15,** against their originals. These are the last 100k block's means (scratchpad
    `collapse_1340.txt`, `wealth_rounds_1340.txt`). All four have `cuda`, no horizon bootstrap, the 100-tick floor and
    a clean tree.

    | Run | Collapse, rerun | Collapse, original | Reward, rerun | Reward, original | Net worth, rerun | Net worth, original |
    |---|---|---|---|---|---|---|
    | E6a γ_hr 0.9 seed 1 | – | – | 204.0 | 254.5 | 0.30M | 1.13M |
    | E4 seed 1 | – | – | 107.4 | 106.3 | 0.06M | 0.10M |
    | E6b seed 1 | 1.7M, then recovers | 400k | 101.2 | 48.8 | 0.13M | 0.04M |
    | E5 seed 1 | – | – | 210.1 | 355.0 | 0.39M | 2.70M |

    - **E6b's seed 1 passes the marker and recovers.**
      - Its 1.7M block takes 1,069 decisions an episode, 49% of them short. Its last two blocks take 537 and 454.
      - Its reward ends at 101.2 (original 48.8).
      - Its original looped from 400k.
    - **E4's seed 1** takes 728 decisions an episode in its last block, 49% of them short. Its original took 524, 39%
      short. Its reward is 107.4 (original 106.3).
    - **E5's seed 1 misses the Gem Store loop that its original found** (scratchpad `strategy_e5_1340.txt`, the last
      part's 50k decisions):
      - the original spends 37% of its game time buying uncut emeralds and 17% selling them on the GE;
      - the rerun spends 38% chopping and fletching logs.
    - **E6a's γ_hr 0.9 seed 1** ends below its original. Neither run found the loop.
  - **The census** (20 finished runs; scratchpad `census_rerun_1340.txt`):
    - 4 pass the marker, and 3 end over it: E3's (.75, .25) seeds 0 and 1, and its (.5, .5) seed 1. E6b's seed 1
      passes it and recovers.
    - Among the same 20 runs, the first round had 5 ending looping: the 4 named at the third check, and E6b's seed 1.
  - **The Gem Store loop:**
    - With E5's seed 1, five rerun runs miss the loop that their originals found: E3's (.25, .75) seeds 0 and 1, its
      (.5, .5) seed 1, E6a's γ_hr 0.5 seed 1, and E5's seed 1.
    - Of the rerun's 16 finished runs that aren't at (1, 0) or (0, 1), none holds more than 1.2M net worth.
    - None of the training E3 seed-2 runs at mixed weights buys emeralds (their last complete part; scratchpad
      `strategy_1340.txt`):
      - (.25, .75) chops and fletches logs, 84% of its time;
      - (.5, .5) chops and fletches logs (43%) and fishes (14%);
      - (.75, .25) splits its time between fishing, chopping and fletching.

      In the first round, seed 2 didn't find the loop at (.25, .75) or at (.5, .5), so these don't test it.
- **The fifth run check (Caleb: "Check on the runs.", 16:18:35 CST):**
  - **The queue (PID 9884):** no failure in its log, and `train-queue.err` is empty.
    - **Done:** 21 of the 50. E3's (1, 0) seed 2 finished at 15:32.
    - **Started:** E6a's γ_hr 0.5 seed 2, at 15:33.
    - **Training at 16:20:** E3's seed 2 at (.75, .25), (.5, .5), (.25, .75) and (0, 1), at about 1.45M, 1.55M, 1.65M
      and 1.2M decisions, and E6a's γ_hr 0.5 seed 2 at about 0.1M.
  - **What's left:** about 52M decisions.
    - From 13:40 to 16:20 the runs made about 3.4M, about 350 a second.
    - At 300 to 360 a second, the rest takes 40 to 48 hours. The last run ends on Nov 19, about 08:00 to 16:00.
  - **The watch hasn't fired** (since 13:47):
    - **The total speed:** 333 to 399 decisions a second in each 15 minutes, 0.98 to 1.10 of the 15 before
      (`total_watch_1117.log`).
      - E3's (.75, .25) seed 2 kept slowing, from 52.2 a second (13:48 to 14:03) to 36.3 (15:49 to 16:04). Under
        Caleb's 13:45 answer, only the total asks again.
      - E3's (.5, .5) seed 2 sped up from 41–43 a second to 64, then 96, as its loop began (below).
    - **RAM** (`trial_sample6.csv`, 939 samples from 13:48 to 16:18):
      - never under 1 GB;
      - under 2 GB in 2 samples, the lowest 1,847 MB at 16:15:34;
      - no hard page reads over 1,000 a second while under 2 GB;
      - the CPU averaged 66%.
  - **E3's (1, 0) seed 2,** against its original (scratchpad `collapse_1620.txt`). It has `cuda`, no horizon bootstrap,
    the 100-tick floor and a clean tree.
    - Neither round collapses.
    - Its last block's reward is 362.8 (original 306.4), its total level 391 (335), with 244 decisions an episode.
    - The rerun's three (1, 0) seeds end at 365.9, 361.0 and 362.8.
  - **E3's (.5, .5) seed 2 loops, on banking** (complete parts only; scratchpad `live_1620.txt`,
    `loop_options_e3_55_s2.txt`, `loop_detail.py`):
    - From 1.25M its episodes take 1,316 to 5,556 decisions, 75–94% of them short. Its original takes 163 to 199 over
      the same parts, and it never looped.
    - **Its loop isn't the loot-setting options** (0% of its decisions). It's banking at a bank, 8 ticks a decision,
      with no skill or wealth reward:
      - `bank_deposit`;
      - then `bank_withdraw_for_fish_shrimp`, `bank_withdraw_for_mining` or `bank_withdraw_for_woodcutting`;
      - then a deposit again.

      In its part at 1.4M, these are 88% of its decisions and 18.6% of its game time.
    - Its reward per episode ended is about 182 at 1.0M and 1.1M. It is 154.5 and 151.9 in the 1.3M and 1.4M blocks.
  - **Banking loops aren't new** (each looping run's last part; scratchpad `loop_modes_1620.txt`):
    - **The first round's E3 (0, 1) seed 1 looped on banking alone:** deposits and withdrawals for woodcutting and
      mining are 98% of its last part's decisions. The decision log named this loop (2026-11-16, "a bank deposit and
      withdraw at 8 ticks").
    - **Some loops mix the two:**
      - the rerun's (.5, .5) seed 1: loot changes 41% of its last part, deposits 8%;
      - the first round's E6a γ_hr 0.5 seed 0: deposits 18%, then `loot_all` and `loot_vocabulary` at 6% each.
    - **The other loops are loot changes:**
      - the rerun's (.75, .25) seeds 0 and 1;
      - the first round's E6a γ_hr 0.9 seeds 0, 2 and 3;
      - E6b's five seeds.
    - **The docs:** `m002-loop-cause` and the post-project gap describe the loop by the loot-setting options, since
      they were measured on (.75, .25) seed 0.
      - One of the gap's remedies would mask the loot options until a fight. That wouldn't stop a banking loop.
      - The deliberation cost and game-time weighting would.
      - Both docs now say so (below).
  - **E3's (.75, .25) seed 2 is the next run to watch:** 350 to 515 decisions an episode from 1.0M (original 111 to
    141), 27–38% short, and 3–20% loot-setting. Its seeds 0 and 1 looped from 1.5M and 1.9M.
  - **E3's (.25, .75) and (0, 1) seed 2 don't loop:**
    - (.25, .75): 143 to 228 decisions an episode from 1.0M, 2–18% short;
    - (0, 1): 336 to 352 from 100k, 2–6% short.
  - **E6a's γ_hr 0.5 seed 2** tests the Gem Store loop, since its original found it. At 100k it's too early to say.
  - **The census** (21 finished runs; scratchpad `census_rerun_1620.txt`):
    - 4 pass the marker, and 3 end over it.
    - Among the same 21, the first round had 5 ending looping.
    - With the training (.5, .5) seed 2, 5 rerun runs have passed the marker.
- **The RAM rule fired (18:45:35), from the midnight watch:**
  - Available RAM was under 1 GB from 18:44:26 to 18:45:35, at its lowest 385 MB at 18:46:17. E6b's seed 2 had started
    at 18:32 and was still growing.
  - By 18:46:37 Windows had trimmed the runs' working sets, and 2.0 to 2.2 GB was available.
  - The total speed held, the commit charge was at 96%, and the pagefile is system-managed with 233 GB free on C:.
  - **Asked Caleb** (the options are in the decision log). **Caleb (19:39:22 CST): keep five.** The low-RAM watch
    was restarted.
- **The sixth run check (Caleb: "Check on the runs.", 22:02:46 CST):**
  - **The watch had a gap.** The sampler stopped at 19:39:49, when the Claude session ended, so RAM went unwatched
    from 19:40 to 22:03. The speed watch kept running to 21:52.
    - The sampler and both watches were restarted at 22:03, until midnight (`trial_sample7.csv`).
    - The gap shows no trouble: the speed held, and the system log has no low-virtual-memory event in the 7 days.
    - **The commit charge** stays at 96–99% of an 86.7 to about 89 GB limit. The limit moves with the
      system-managed pagefile. It reached 99.4% three times on 2026-11-17 (15:15, 16:21, 17:49), with nothing failing.
  - **The queue (PID 9884):** no failure in its log, and `train-queue.err` is empty.
    - **Done:** 25 of the 50, with E3's seeds 0 to 2 complete. Since 16:20, four finished:
      - E3's (.5, .5) seed 2, at 17:20;
      - its (.25, .75) seed 2, at 17:23;
      - its (0, 1) seed 2, at 18:31;
      - its (.75, .25) seed 2, at 19:54.
    - **Started:** E6a's γ_hr 0.9 seed 2 at 17:21, E4's seed 2 at 17:24, E6b's seed 2 at 18:32, and E5's seed 2 at
      19:55.
    - **Training at 22:05:** E6a's γ_hr 0.5 seed 2 at about 1.55M decisions, its γ_hr 0.9 seed 2 at about 1.0M, E4's
      seed 2 at about 0.75M, E6b's at about 0.6M and E5's at about 0.4M.
  - **What's left:** about 45.7M decisions.
    - **The speed watch:** each 15 minutes from 16:05 to 21:52 ran at 0.93 to 1.12 of the 15 before.
    - The total depends on which runs train.
      - While E3's (0, 1) seed 2 trained (to 18:31), the windows ran at 332 to 397 a second, about 120 of it from
        that run. The exception is 212 at 17:35, when two just-started runs were left out.
      - Since then they ran at 234 to 328.
    - At 300 to 360 a second, the rest takes 35 to 42 hours. The last run ends on Nov 19, about 09:00 to 16:30.
  - **The four runs done since 16:20,** against their originals. These are the last 100k block's means (scratchpad
    `collapse_2205.txt`, `wealth_rounds_2205.txt`). All four have `cuda`, no horizon bootstrap, the 100-tick floor and
    a clean tree.

    | Run | Collapse, rerun | Collapse, original | Reward, rerun | Reward, original | Net worth, rerun | Net worth, original |
    |---|---|---|---|---|---|---|
    | E3 (.75, .25) seed 2 | – | – | 281.4 | 234.9 | 0.03M | 0.08M |
    | E3 (.5, .5) seed 2 | 1.3M (banking) | – | 135.7 | 179.7 | 0.14M | 0.18M |
    | E3 (.25, .75) seed 2 | – | – | 153.1 | 182.7 | 0.81M | 0.96M |
    | E3 (0, 1) seed 2 | – | – | 723.2 | 716.0 | 3.94M | 3.90M |

    - **(.75, .25) seed 2 doesn't loop,** unlike seeds 0 and 1.
      - Its episodes peaked at 465 decisions in the 1.7M block, 49% of them short. They end at 355, 40% short.
      - Its reward is the highest of the three (.75, .25) reruns (204.9, 269.3, 281.4).
    - **(.5, .5) seed 2 ends in its banking loop:** 5,889 decisions an episode in the last block, 97% of them short.
      Its reward peaked at 182.4 in the 1.0M block.
    - **(.25, .75) seed 2** ends low, like the variant's other reruns: 161.4, 155.4 and 153.1. Its original didn't find
      the Gem Store loop either.
  - **The census** (25 finished runs; scratchpad `census_rerun_2205.txt`):
    - 5 pass the marker, and 4 end over it: E3's (.75, .25) seeds 0 and 1, and its (.5, .5) seeds 1 and 2. E6b's seed
      1 passes it and recovers.
    - Among the same 25, the first round had 5 ending looping.
  - **The training runs,** by complete part (scratchpad `live_2205.txt`):
    - **E6a's γ_hr 0.5 seed 2 tests the Gem Store loop, and hasn't found it at 1.5M** (scratchpad
      `strategy_2205.txt`, its part at 1.5M):
      - The rerun spends 36% of its game time fishing shrimp and 23% pickpocketing farmers and master farmers.
      - Its original was in the loop from 850k: 347 to 352 decisions an episode, 0–2% of them short. At 1.5M it
        spent 57% of its time buying uncut emeralds at the Gem Store, 32% banking and 6% selling them on the GE.
      - The rerun is 650k decisions past the point where its original found the loop. It has 450k left.
    - **E6b's seed 2** is past the point where its original looped (550k, at 50,000 decisions an episode). At 550k it
      takes 568, 27% of them short.
    - **E6a's γ_hr 0.9 seed 2:** 485 to 526 decisions an episode from 550k, 20–26% short, and no loot-setting. Its
      original took 357 to 442 there, then passed the marker in its last block.
    - **E4's seed 2:** 316 to 455 from 150k, 25–35% short, and 2–5% loot-setting. Its original took 149 to 223. E4's
      seeds 0 and 1 ended at 760 and 728.
    - **E5's seed 2:** 140 to 190 decisions an episode at 50k to 350k, 9–17% short. Its original took 107 to 145.
- **The midnight watches ended without firing.** RAM didn't stay under 1 GB. Each 15-minute window ran at 0.88 to 1.13
  of the one before, at 232 to 313 decisions a second.
  - Nothing watched the machine from midnight to the seventh run check.
  - At 15:30, 2.4 GB was available, paging was 0 to 15 page reads a second, and the commit charge was 84.9 of 87.2 GB.
    The system log has no low-virtual-memory event in the last day.
- **The seventh run check (Caleb: "Check on the runs.", 2026-11-18 15:28:13 CST):**
  - **The queue (PID 9884):** no failure in its log, and `train-queue.err` is empty.
    - **Done:** 36 of the 50. Since 22:05, eleven finished:
      - E6a's γ_hr 0.5 seed 2 at 23:31, its γ_hr 0.9 seed 2 at 01:17, E6b's seed 2 at 02:14, E5's seed 2 at 04:37,
        and E4's at 04:39;
      - E3's seed 3 at all five weightings, from 08:52 to 10:10;
      - E6a's γ_hr 0.5 seed 3, at 13:49.
    - **Training at 15:30:** E6a's γ_hr 0.9 seed 3 at about 1.5M decisions, E4's seed 3 at 1.4M, E5's at 1.2M, E6b's
      at 1.1M, and E3's (1, 0) seed 4 at 0.3M.
    - **Waiting:** nine seed-4 runs.
  - **What's left:** about 22.5M decisions.
    - Over the last 15 minutes, the five runs made 295 decisions a second together, 55 to 64 each (scratchpad
      `rate_now.py`). At that rate a run takes about 9.4 hours.
    - In the queue's order, the last run ends on Nov 19, about 12:00 to 16:00.
  - **The census** (36 finished runs; scratchpad `census_rerun_1530.txt`, `census_boot_1530.txt`):
    - **10 pass the marker, and 8 end over it.**
      - Four more end over it: E3's (.5, .5) seed 3 (from 800k), its (.75, .25) seed 3 (1.7M), its
        (1, 0) seed 3 (its last block) and E6b's seed 2 (1.2M).
      - E3's (.25, .75) seed 3 passes it from 1.5M to 1.8M, then recovers.
    - **Among the same 36, the first round has 7 passing and 7 ending over it.** So the rerun now loops a little
      more often than the first round. At 22:05 it was 4 against 5.
      - One of the first round's seven is marginal: E6a's γ_hr 0.5 seed 0 ends at 1,003 decisions an episode.
      - The 2026-11-16 decision-log entry counted 8 of the first round's 50 as looping. By the census's measure (the
        last block over the marker), it's 10: that entry left out γ_hr 0.5 seed 0 and γ_hr 0.9 seed 2, which passes
        only in its last block. The report should give one measure for both rounds.
    - **By discount.** E6a trains at γ_hr 0.5 and 0.9, and E3, E4, E5 and E6b at 0.99:

      | γ_hr | Runs | Ending over the marker, first round | Ending over the marker, rerun |
      |---|---|---|---|
      | 0.5 | 4 | 1 | 0 |
      | 0.9 | 3 | 2 | 0 |
      | 0.99 | 29 | 4 (E3 1, E6b 3) | 8 (E3 7, E6b 1) |

      - The rerun's 100-tick floor costs every decision at least 1 − γ_hr^(100/6000) of its value: 1.15% at 0.5,
        0.18% at 0.9 and 0.017% at 0.99. So the rerun stopped the loops where the floor costs most.
      - At 0.99, E3 loops more than before: 7 of its 20 runs, against 1. Why is untested.
        - The floor is too small there to matter much.
        - The rerun's other changes are the horizon bootstrap's removal, and for E3 the sim's death-budget cap (see
          Validation). Either could be the cause; that's a hypothesis, untested.
      - `m002-loop-cause` gave the trainer bug as part of the loops' cause, from 3 looping runs against 2 among the 13
        then. That doesn't hold at γ_hr 0.99. That record now gives these counts (below).
  - **The eleven runs done since 22:05,** against their originals. These are the last 100k block's means (scratchpad
    `collapse_1530.txt`, `wealth_rounds_1530.txt`). All eleven have `cuda`, no horizon bootstrap, the 100-tick floor
    and a clean tree.

    | Run | Collapse, rerun | Collapse, original | Reward, rerun | Reward, original | Net worth, rerun | Net worth, original |
    |---|---|---|---|---|---|---|
    | E3 (1, 0) seed 3 | 1.9M (loot) | – | 349.3 | 307.7 | 0.01M | 0.01M |
    | E3 (.75, .25) seed 3 | 1.7M (loot) | – | 264.7 | 240.1 | 0.07M | 0.09M |
    | E3 (.5, .5) seed 3 | 800k (banking) | – | 140.8 | 168.6 | 0.19M | 0.16M |
    | E3 (.25, .75) seed 3 | 1.5M (loot), recovers | – | 130.2 | 560.3 | 0.73M | 3.96M |
    | E3 (0, 1) seed 3 | – | – | 712.5 | 704.3 | 3.88M | 3.84M |
    | E6a γ_hr 0.5 seed 2 | – | – | 251.4 | 420.9 | 1.15M | 4.23M |
    | E6a γ_hr 0.5 seed 3 | – | – | 421.8 | 253.8 | 4.18M | 1.15M |
    | E6a γ_hr 0.9 seed 2 | – | 1.9M | 255.2 | 194.2 | 1.24M | 0.27M |
    | E4 seed 2 | – | – | 99.2 | 115.0 | 0.15M | 0.06M |
    | E6b seed 2 | 1.2M (loot) | 500k | 62.9 | 12.7 | 0.15M | 0.00M |
    | E5 seed 2 | – | – | 202.9 | 164.8 | 0.39M | 0.25M |

    The loops' options are from each run's last part, or for (.25, .75) seed 3 its part at 1.65M (scratchpad
    `loop_modes_1530.txt`, `loop_detail.py`).
    - **(1, 0) seed 3 is the first (1, 0) run to loop.** It does so in its last block: 1,598 decisions an episode,
      85% of them short. Its short no-effect decisions, mostly loot changes, take 3.5% of its game time, so its reward
      still beats its original's.
    - **(.75, .25) seed 3 loops from 1.7M, as seeds 0 and 1 did.** Three of the four (.75, .25) reruns end looping. In
      its last part, 99% of decisions are loot changes, taking 19% of the game time.
    - **(.5, .5) seed 3 loops on banking from 800k, the earliest of any E3 run.**
      - It ends at 3,058 decisions an episode, 86% of them short.
      - In its last part, 86% of decisions are short with no effect, taking 17% of the game time. Most are bank
        deposits and withdrawals: of food, of the shrimp-fishing kit and of magic gear.
      - Its reward peaked at 170.0 at 500k. Three of the four (.5, .5) reruns end looping.
    - **(.25, .75) seed 3 loops on `loot_all` and `loot_valuable` from 1.5M to 1.8M, then recovers.** It ends at 180
      decisions an episode. It misses the Gem Store loop its original found.
    - **E6b's seed 2 loops from 1.2M** on `loot_none` and `loot_all`. It ends at 26,448 decisions an episode. Its
      original looped from 500k.
    - **E6a's γ_hr 0.9 seed 2 doesn't loop.** Its original passed the marker in its last block.
  - **The Gem Store loop now goes both ways** (scratchpad `gem_census.py`, `gem_onset.py`). This is the share of game
    time each finished run's last full part spends buying uncut emeralds at the Gem Store.
    - **28 mixed-weight pairs are finished in both rounds:** E3's (.75, .25), (.5, .5) and (.25, .75), E6a, E4, E6b
      and E5. The first round ends in the loop in 7, with 37–57% of the game time buying. The rerun ends in it in 1.
    - **E6a's γ_hr 0.5 seed 3 rerun finds it, where its original didn't.**
      - It starts buying in its part at 350k, and from 500k it spends 55–56% of its game time on it.
      - Its last part: 56% buying, 31% banking and 6% selling on the GE.
      - It ends at 421.8 and 4.18M, the level of its variant's three originals that found the loop.
    - **E6a's γ_hr 0.5 seed 2 ended without it.** From 1.7M it fishes and pickpockets, and its part at 1.95M has no
      shop purchases. Its original found the loop by 850k.
    - **E3's (.25, .75) seed 3 misses it.** It ends at 130.2 and 0.73M, against its original's 560.3 and 3.96M.
    - **Still to come:**
      - E5's seed 3. Its original found the loop late, from its part at 1.8M. The rerun hadn't started buying by
        1.2M.
      - Seed 4 of (.25, .75) and E6a's γ_hr 0.5, whose originals found it.
      - Seed 4 of (.5, .5) and E5, whose originals didn't.
  - **The training runs,** by complete part (scratchpad `live_1530.txt`):
    - **E6a's γ_hr 0.9 seed 3:** 526 to 676 decisions an episode from 1.35M, 16–24% short, and no loot changes. Its
      original looped from 400k.
    - **E6b's seed 3:** 649 to 685 from 900k, 36–39% short, and 9% loot changes. Its original looped from 600k.
    - **E4's seed 3:** 455 to 725 from 1.15M, 43–51% short, and 2–7% loot changes. Its original took 228 to 303.
    - **E5's seed 3:** 230 to 243 from 1.0M, 24–27% short, and 10–13% loot changes. Its original took 205 to 243.
    - **E3's (1, 0) seed 4:** 121 to 149 at 100k to 250k.
- **Corrections to `079009c`:**
  - **The loot-setting options are four** (`loot_all`, `loot_valuable`, `loot_vocabulary`, `loot_none`).
    - The live check's loot share (`live_check.py`) counted three, without `loot_vocabulary`. With all four, E3's
      (.5, .5) seed 1 had 7–43% loot-setting decisions by part from 1.2M to 1.5M, not 10–22%.
    - E3's (.75, .25) seed 0 finding holds with all four counted: 95–99% by part from 1.55M, the three named, and
      `loot_vocabulary` hardly at all. "The three loot-setting options" now reads "three of the four", here and in
      the decision log.
  - **Two prompt times were off.** The run check's prompt was at 21:01:39 and the commit's at 21:47:00. The record had
    21:01:47 and 21:47:09, which are times of the replies, not of the prompts' user entries.
- **Corrections to `a06bbff` and `5112c23` (found at the seventh run check): E6b's and E4's rewards.**
  - **What went wrong:** the episodes' `reward` (`episodes.parquet`) is already the env's own weighted reward, without
    PBRS's shaping or RND's bonus (`rlscape/agents/training.py`). `collapse_check.py` took it for the reward PPO learned
    from, and subtracted them. So its "task" column, quoted as E6b's "unshaped" reward and E4's "task" reward, took
    them out twice.
  - **What was right:** its other columns, the census, and `m002-collapse-diagnosis`'s unshaped return, which comes from
    the decision log (`unshaped_return.py`).
  - **The corrected figures:**
    - E6b's seed 0 ends at 129.9, not 331.3. Its original's last block with an episode (1.7M) is 0.0, not 164.7.
    - E6b's seed 1 ends at 101.2, not 322.9. Its original ends at 48.8, not 215.8.
    - E4's seed 0 falls from 129.8 (block 0) to 106.2, not from 146.7 to 94.0.
    - E4's seed 1 ends at 107.4, not 118.9. Its original ends at 106.3, not 109.3.
  - **The findings hold:** E6b's reruns don't loop where their originals did, and E4 drifts. But E6b's reward hardly
    moves from its first block (seed 0: 124.1 to 129.9).
  - **Fixed in place,** here and in the decision log. `collapse_check.py` now shows the learned reward beside the env's.

## Documentation Changes

- `docs/decision-log.md`: the check's findings, the options and Caleb's answer. From the second run check, its
  collapsed run's loop reads "three of the four loot-setting options".
- From the fifth run check:
  - `docs/agent-interactions/m002-loop-cause.md`: banking loops, and the remedy that wouldn't stop them;
  - `docs/post-project-gaps.md`: the stalling gap names the banking loops, and its loot-masking remedy says it wouldn't
    stop them.
- From the sixth run check: `docs/decision-log.md`, the RAM-rule decision.
- From the seventh run check:
  - `docs/decision-log.md`: E6b's and E4's rewards in the 2026-11-16 entry are corrected, and a new finding gives the
    loop counts by discount;
  - `docs/agent-interactions/m002-loop-cause.md`: the loop counts by discount, which no longer support the trainer bug
    as a cause at γ_hr 0.99.
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
- From the fourth run check:
  - `live_check.py` skips the newest part, which may still be being written;
  - `strategy_time.py` takes a part's file;
  - `wealth_rounds.py` covers E4, E6b and E5;
  - `total_watch.py` (the runs' total speed every 15 minutes).
- From the fifth run check:
  - `loop_options.py` skips a training run's newest part;
  - `loop_detail.py` (one part's short no-effect options, with their ticks and the option after each).
- From the seventh run check:
  - `collapse_check.py` takes the episodes' reward as the env's, and shows the learned reward (with shaping or RND's
    bonus) beside it; the old version is kept as `collapse_check_old.py`;
  - `gem_census.py` (every finished mixed-weight run's Gem Store buying, both rounds) and `gem_onset.py` (a run's
    Gem Store buying, part by part);
  - `e6b_task.py` (a run's episodes, every column).

## Infrastructure Changes

- None.

## Decisions

- **User decision (Caleb):** carry on; each run's final model is evaluated as planned, and the report gives each
  round's collapse count and names the looping runs.
- **The speed rule (the fourth run check):**
  - **Agent recommendation:** keep five jobs, since the fall is one run's share, not the machine's total.
  - **User decision (Caleb, 13:45:54 CST):** keep five, watched until midnight.
- **The RAM rule (18:45):**
  - **Agent recommendation:** keep five jobs. The low was a young run growing, and Windows recovered the memory
    within a minute.
  - **User decision (Caleb, 19:39:22 CST):** keep five.
- **What the report says causes the loops** (the seventh run check):
  - **Agent recommendation:** give the loop counts by discount, for both rounds, by one measure. Say the rerun's
    changes ended the loops at γ_hr 0.5 and 0.9, but not at 0.99, where E3 loops more, and that the cause is untested.
    Don't call the loops a trainer bug that was fixed.
  - **User decision:** Caleb's, for the report. Not asked yet.
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
- The fourth run check read finished runs' files. For the training runs, it read their complete decision parts (all
  but the newest), with three columns each. Available RAM was 1.8 to 3.6 GB.
- The fifth run check read finished runs' files, and the training runs' complete decision parts (all but the newest).
  Available RAM was 3.3 to 3.7 GB.
- The sixth run check read finished runs' files, and the training runs' complete decision parts. Available RAM was 3.0
  to 3.5 GB.
- The seventh run check read finished runs' files, and the training runs' complete decision parts. Available RAM was
  2.4 GB at 15:30. The episodes' reward is the env's: the trainer's docstring and its callback
  (`rlscape/agents/training.py`, `reward_extrinsic`) say so. For E6b's seed 2, checked by hand on two episodes, the
  reward is 0.5 × `r_skill` + 9.18 × `r_wealth` (its config's weights), within 0.4, without the shaping.
- The sim versions come from each run's `config.json` `git_sha`, checked against the `sim-v1.*` tags
  (`git merge-base --is-ancestor`). The sim diff between the rounds (`git diff` of `rlscape/sim/`) is the death-budget
  cap in `fishing.py` and `gathering.py` for E3, and the tan guard in `crafting.py` for E6a.
- E6a γ_hr 0.9's rerun matches the floor test's finding (`m002-collapse-diagnosis`): 450–530 decisions an episode
  from 500k, and a quarter to a third of the decisions short.

## Follow-Up

- **Done:** E6a's γ_hr 0.5 seed 0 repeats its failed run's 250k decisions and is past the crash.
- **Claude:** run the same census on every rerun as it finishes. The report's collapse counts come from the full 50.
  At 23:32, 13 are done, and 2 of them end over the marker. At 07:15, 16 are done, and 3 of them end over it. At 13:40,
  20 are done, and 3 end over it. At 16:20, 21 are done and 3 end over it, and the training (.5, .5) seed 2 loops from
  1.25M. At 22:05, 25 are done, and 4 end over it. At 15:30 on 2026-11-18, 36 are done, and 8 end over it, against 7
  of the same 36 in the first round.
- **Done:** E3's (.75, .25) seed 2 ended without looping.
- **For the analysis:** at mixed weights, the first round's runs end in the Gem Store loop in 7 of the 28 pairs
  finished in both rounds, and the rerun's in 1 (the seventh run check).
  - Seven rerun runs miss it where their originals found it: E3's (.25, .75) seeds 0, 1 and 3, its (.5, .5) seed 1,
    E6a's γ_hr 0.5 seeds 1 and 2, and E5's seed 1.
  - One finds it where its original didn't: E6a's γ_hr 0.5 seed 3.
  - So the weighting's result differs between the two trainers. Which change causes it is untested.
  - Still to come: E5's seed 3 (its original found it from 1.8M), and seed 4 of (.25, .75) and E6a's γ_hr 0.5, whose
    originals found it. Seed 4 of (.5, .5) and E5, whose originals didn't, test the other way.
- **Done:** E4's and E6b's seed 1 ended without looping. E6b's passed the marker at 1.7M and recovered.
- **Done:** the watch ran until midnight without firing.
- **For the report:** the loop counts by discount, by one measure for both rounds, and what it says causes them
  (Caleb's call; the recommendation is under Decisions).
