# Agent Interaction

## Metadata

- Interaction ID: m002-task-kits
- Timestamp CST: 2026-10-30 17:11:11 CST (from the session transcript's message timestamp, UTC−05:00); the mid-turn
  link at 17:38:11 CST
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (decisions recorded; the first slice, deposits by task, built and tested; tick manipulation
  assessed from the server source; four slices remain)
- Commit: main repo `63ebb0d` (branch `sim-v0`), with `m002-scripted-guide` and `m002-withdraw-for-sale`

## Full Prompt

> 1. Widen the guide.
> 2. Deposit all items that are not suitable to the task at hand.
> 3. Go after lowest skill for schedule.
> 4. For scope, include more skills. I think Thieving, specifically will be a great money maker early on.
> 5. Offer the different paths as gp/hr or xp/hr for the agents to choose from.
> 6. We will implement prayer flicking and 3-tick woodcutting if they can be used.

Claude asked four questions (`AskUserQuestion`); Caleb's answers:
- How deposits know the task: "Last activity's kit (Recommended)".
- What paths agents get: "Skilling slots (Recommended)".
- The techniques: "I want to go with the recommendation here, but I want to see if we can woodcut at 2 ticks. I also
  want to see if we can apply the tick manipulation techniques to other skills, like Fishing and Mining."
- Thieving: "Targets and stalls (Recommended)".

Mid-turn:

> You can review this webpage for tick manipulation information: https://oldschool.runescape.wiki/w/Tick_manipulation

## Response Summary

- **Read the server source before asking.**
  - 2009Scape's woodcutting already rolls every 3 ticks.
  - Protection prayers block NPC hits completely (`Entity.getFormattedHit` × 0).
  - Then asked the four questions, since each one changes the action space.
- **Built the first slice, deposits by task:**
  - every activity names its task, and the engine records the last one
  - `bank_deposit` keeps only that task's kit
  - new withdrawals for gathering kits and for any food
  - the task is in the observation
- **The guide** now withdraws its tools when needed. Its 10-seed result rose from total level 233 to 306, and from
  23k to 353k net worth, because the inventory clog is gone.
- **Read the wiki page Caleb linked** (summarised, not copied). Then checked 2009Scape's code for each technique:
  - **Mining and fishing:** script-gated, so no tick manipulation is possible.
  - **Woodcutting:** 2-tick looks possible by burying a bone on the chop tick, because burying sets the shared
    skilling clock to 2 ticks.
  - **Prayer flicking:** avoids drain.
  - **Live tests are planned for both,** which need new bridge commands.

## Documentation Changes

- `docs/option-catalog.md` §5 (the deposit rule and three new withdrawal rows) and §9 (981 actions).
- `docs/env-contract.md` v1.4: the task part in §3, the as-built sizes (981 actions, 1,590 features), and decision 20.
- `docs/scripted-guide-draft.md`: Caleb's review and the new results.
- `docs/decision-log.md`: the decisions, the slice, the tick-manipulation findings and the remaining plan.
- `ROADMAP.md`: the status line.
- This record.

## Code Changes

- `rlscape/sim/kits.py` (new): `kit(state, task)`.
- `rlscape/sim/options.py`: `Option.task`.
- `rlscape/sim/woodcutting.py`, `mining.py`, `fishing.py`, `thieving.py`, `processing.py`, `slots.py`: each activity's
  task.
- `rlscape/sim/state.py`: `task`.
- `rlscape/sim/engine.py`: records the last task.
- `rlscape/sim/economy.py`: `BankDeposit` keeps the kit; `BankWithdrawKit` and `GATHERING_KITS`.
- `rlscape/sim/buying.py`: `BankWithdrawAnyFood`.
- `rlscape/envs/encoding.py`: the `task` part.
- `rlscape/baselines/guide.py`: withdraws its gathering kits, and deposits only when the inventory is full.
- Tests:
  - `tests/test_sim_economy.py`: each task's kit; the kit and food withdrawals; the existing deposit test sets a task
  - `tests/test_sim_buying.py`, `tests/test_vocabulary.py`: counts

## Infrastructure Changes

None.

## Decisions

- **User decisions:**
  - widen the guide
  - deposits keep the task's kit, the task being the last activity
  - lowest skill first
  - more skills in scope, with thieving targets and stalls
  - skilling offered as XP/hr and gp/hr slots
  - prayer flicking and tick manipulation (2-tick woodcutting; fishing and mining too) after live tests
- **Agent choices (reversible):**
  - gathering withdrawals per skill (woodcutting, mining) and per fishing method
  - a generic food withdrawal, so food a deposit banked can come back
  - the kits' contents (in `kits.py`)
  - the 11-way task part of the observation
  - the order of the remaining slices

## Validation

- `uv run pytest -q`: 177 passed and 18 skipped. A new test found that the withdrawal ranked tools by required level,
  which made iron and bronze axes equal; it now ranks by the server's tool priority.
- `scripts/evaluate.py --policies scripted_guide random --seeds 10 --workers 10`: guide 306 [304, 307] levels and
  353k [302k, 407k] gp; random 190 levels and 10k.
- The tick-manipulation findings come from reading the code (`ContentAPI.delayClock`, `WoodcuttingListener`,
  `MiningListener`, `FishingPulse`, `BoneBuryListener`, `Prayer.tick`, `Entity.getFormattedHit`). None is tested
  live yet.

## Follow-Up

- The next slices:
  1. thieving targets and stalls
  2. the wider guide
  3. skilling slots
  4. the live tests, with bridge commands for item options and prayer toggles
- Commit when Caleb asks.
