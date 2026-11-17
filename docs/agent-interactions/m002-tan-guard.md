# Agent Interaction

## Metadata

- Interaction ID: m002-tan-guard
- Timestamp CST: 2026-11-16 07:31:17 CST (the prompt) and 08:04:16 CST (Caleb's answers in the question dialog), the
  session transcript's timestamps (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL. Sim v1.4's fix, its test and its docs, in a PR into `main`: it equals sim v1.3 on every checked
  trajectory. The tag, the merges into the five experiment branches and the queue's relaunch wait for the merge.
- Commit: this commit on `sim/v1.4-tan-guard` (from `main` at `291f4a6`; Caleb: "Commit it and open a PR into main",
  17:32:43 CST).

## Full Prompt

> Check on the runs.

The question dialog asked two things. First, how to handle E6a's γ_hr 0.5 seed 0, which crashed on a sim bug. The
options were a sim v1.4 guard, a fuller fix, or no sim change. Second, whether the fare-for-the-fee route goes in the
post-project gaps. Caleb's answers:

> "sim-v1.4 guard (Recommended)"
>
> "Log it (Recommended)"

Then (17:32:43 CST):

> Commit it and open a PR into main

## Response Summary

- **The runs at 07:31:**
  - E3's (0, 1), (.25, .75) and (.5, .5) seed 0 were done (04:29, 05:33, 07:11).
  - Five runs were training: E3's (1, 0) seed 0 (1.7M decisions) and (.75, .25) seed 0 (1.5M); E6a's γ_hr 0.9 seed 0
    (400k); E4's seed 0 (400k); E6b's seed 0 (from 07:12).
  - One had failed: E6a's γ_hr 0.5 seed 0, at 05:47:40, with 200k decisions checkpointed.
- **RAM:** 887 MB available at 07:32, under OQ-81's 1 GB. Sampled every 5 seconds from 07:36:15 to 07:37:39, it was
  2,063 to 2,335 MB, so the rule (under 1 GB for more than a minute) didn't fire. The queue stays at five. The commit
  charge was 92.5 of 94.3 GB, with the pagefile system-managed and 2.1 GB of it in use.
- **The crash:** an env worker raised `KeyError: 995` in `TanAtTanner._work`. It took the tanning fee from an
  inventory without coins (`state.take(COINS, 0)`).
  - The cause: the walk from the bank to the tanner pays its fares from the coins carried, the fee's among them, and
    a fare had left none.
  - Reproduced: at Catherby's bank with exactly 1,000 coins carried and 20 cowhides banked, `tan_leather`'s walk takes
    the 1,000 gp charter to Port Sarim, and the fee raises. With 1,001 coins it tans one hide; with 999 it walks and
    tans all 20.
  - With 1,000 coins carried, the walks to Ellis from 7 of the 20 banks take that charter.
  - The GE's and shops' buying already skip a purchase of no units; tanning was the only such take.
- **Asked Caleb** (the options are in the decision log). **Caleb: the sim v1.4 guard; log the fare-for-the-fee route
  as a post-project gap.**
- **Built** (branch `sim/v1.4-tan-guard` from `main` at `291f4a6`):
  - `TanAtTanner._work` takes the fee, the hides and the leather only when the coins pay for a hide. With no coins it
    tans nothing, as it already did with coins under the fee.
  - A test of the Catherby case: 1,000 coins carried tans nothing; 1,001 tans one hide.
- **The queue at 17:32** (`runs/train-queue.log`): no failure since 05:47. Eight runs done: E3's five seed-0 runs (the
  last two at 08:36 and 09:21), E6a's γ_hr 0.9 seed 0 (14:06), E4's seed 0 (15:00) and E6b's seed 0 (16:50). Five
  training, on sim v1.3: E5's seed 0 (from 08:37) and E3's (1, 0), (.75, .25), (.5, .5) and (.25, .75) seed 1.

## Documentation Changes

- `docs/decision-log.md`: the crash, the cause, the reproduction, the options and Caleb's answers.
- `docs/post-project-gaps.md`: "An option's walk can spend the coins the option needs on a fare".
- `CLAUDE.md`: `sim-v1.4` marks the frozen sim.
- `ROADMAP.md`: a note on sim v1.4.
- This record.
- Not changed: `docs/env-contract.md`. Its rules and schema are unchanged, since tanning still tans every hide the
  coins carried pay for.

## Code Changes

- `rlscape/sim/crafting.py`: `TanAtTanner._work`'s guard and docstring.
- `tests/test_sim_crafting.py`: `test_a_tanning_path_whose_walk_spends_every_coin_tans_nothing`. On sim v1.3 it raises
  the training run's error, `KeyError: 995`.

## Infrastructure Changes

- None yet. The queue, its runs and the worktrees are unchanged.

## Decisions

- **User decisions (Caleb):** the sim v1.4 guard; the post-project gap entry.
- **Claude's choices:** the reproduction and the checks, as for sim v1.3.

## Validation

- The new test fails on sim v1.3 with `KeyError: 995` and passes with the fix.
- `tests/test_sim_crafting.py`, `test_sim_skilling`, `test_sim_buying`, `test_sim_transport` and
  `test_sim_processing`: 70 passed. The full suite wasn't run, to spare the five training runs' RAM; the change is one
  guard in one path.
- Twenty seeded 20-hour episodes on sim v1.3 and on sim v1.4, byte-identical:
  - the policy: random, choosing a Crafting gp slot (where tanning is offered) 40% of the time, an option that kills
    cows or sells 30%;
  - the run: 6,874 decisions, 255 of them tanning paths, none raising on v1.3;
  - the comparison: each decision's option, path, duration, termination, game tick, total level, reward and
    observation (scratchpad `tan_trace.py`; v1.3's `crafting.py` swapped in for its run, then the fix put back).
- `scripts/sim_to_real.py --families crafting --no-drops`, into the scratchpad: crafting's 53 rows (14 cases, tanning
  among them) and the speed check's 72 are byte-identical to the committed `results/summary/sim-to-real/`.

## Follow-Up

- **Waiting for Caleb:** the PR's merge into `main`. Then the tag `sim-v1.4`, the launcher stopped, `main` merged into
  the five experiment branches, and the queue relaunched with `--restart-partial` (as on Nov 12).
- **Claude:** the collapse check on E6a's γ_hr 0.9 seed 0 and E6b's seed 0 (around noon).
