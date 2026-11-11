# Agent Interaction

## Metadata

- Interaction ID: m002-sim-v1.2
- Timestamp CST: 2026-11-11 17:14:55 CST, the prompt's timestamp in the session transcript (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL. Sim v1.2 is built and tested on its branch, and E3 is stopped. Next: E1's rerun, OQ-67's units,
  and the restart of E3 to E6.
- Commit: on `sim/v1.2-fletching-slot`, from `main` (`704dd95`).

## Full Prompt

> Go with your recommendations for all five. Have we begun to use the GPU for the tests yet?

The five, as Claude recommended them after OQ-75 (c):
1. one new woodcutting slot for the best chop-and-fletch path;
2. the path takes the Lumbridge knife when none is held;
3. stop E3 now;
4. rerun E1 on the new sim, and keep E2 on v1.1 with a note;
5. keep the gem trade.

## Response Summary

- **E3 stopped** at 17:15:57 CST: its launcher (PID 21952) and its tree, 28 processes. Four runs were part-way
  ((.5, .5) seeds 2 to 4, (.25, .75) seed 1). TensorBoard and the replay server weren't in the tree.
  - E3's 13 finished v1.1 runs and the 4 partial ones stay on disk as a record.
  - The training queue had been stopped before (`m002-fletching-unused`).
- **Sim v1.2** (env contract v1.44):
  - `skill_woodcutting_fletch` holds the best open chop-and-fletch path by XP/hr. It's filled before woodcutting's
    XP and gp slots, which rank the rest.
  - A chop-and-fletch path without a knife takes one on its way, from the nearest reachable spawn, and its rate counts
    the detour.
  - The observation gains the slot's 5 rate features: 2,294 actions and 3,488 features.
- **The GPU:** no run has used it. Every training config says `device: cpu`, with `torch_threads: 2`.
  - The measurements of 2026-11-08 (decision log, the RL stack) found the PPO update only a few percent of the time;
    the action mask is 92% of it, in the env processes. So the GPU can't speed a run much.
  - On the CPU a run is bit-for-bit repeatable (tested); on the GPU it isn't.

## Documentation Changes

- `docs/env-contract.md`: v1.44; §3's skilling candidates and the vector's size.
- `docs/option-catalog.md`: §2's fletch slot; the action count (2,294).
- `docs/decision-log.md`: "Built: sim v1.2".
- `CLAUDE.md`: the frozen sim's tag is `sim-v1.2`, once this merges.
- This record.

## Code Changes

- `rlscape/sim/skilling.py`: `EXTRA_SLOTS`, `slot_names`, `knife_spawn`, `_best_fletch` and `EXTRA_RANKERS`; the
  extra slot in `SkillingSlots._rank` and `SkillSlot`; `Path.available` and `run` for the knife; `path_rate`'s detour.
- `rlscape/envs/encoding.py`: the skilling part iterates each skill's slots.
- **Tests:**
  - `tests/test_sim_skilling.py`: 2 new; the slot test reads the extra slot.
  - `tests/test_sim_gathering.py`: a fresh character's open paths and slots include chop-and-fletch.
  - `tests/test_vocabulary.py`: the sizes.

## Infrastructure Changes

- **E3's training stopped,** by PID (its tree only).
- **`.claude/launch.json`'s uncommitted local edit** (the `tensorboard-e3` entry) is stashed, to switch branches:
  `stash@{0}`.

## Decisions

- **User decisions (Caleb):** the five above, and OQ-75 (c) before them.
- **Agent choices:**
  - the fletch slot filled first, so no path is offered twice;
  - the knife taken from the nearest reachable spawn, with no room for it closing the path;
  - `EXTRA_SLOTS` and named rankers, so another skill's extra slot would be one entry;
  - the branch from `main`, as v1.1's was.

## Validation

- **Tests:** the full suite (`pytest -n 8`), 436 passed, 75 skipped (live tests; the server was down). The first run
  failed 2:
  - a fresh character's expected paths, which now include `wc_logs_fletch`, as intended;
  - a new test of mine that rated a path for a state without an axe.
- **A fresh character's fletch slot,** run for 15 game-minutes: the knife taken, 1,095 arrow shafts, 365 Fletching XP,
  2,025 Woodcutting XP.
- **Speed:** random episodes run at 64 decisions a second on v1.2 and 61 on v1.1 (the same 4 seeds, warm).

## Follow-Up

- **Claude:**
  - E1's rerun on v1.2 and its summary;
  - OQ-67's units from it;
  - merging v1.2 into E3 to E6 (and E5's hard-coded observation size);
  - moving E3's v1.1 runs aside;
  - relaunching E3 and the queue.
- **Caleb:** merge the sim PR, and tag `sim-v1.2`.
