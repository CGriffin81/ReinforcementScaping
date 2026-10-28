# Agent Interaction

## Metadata

- Interaction ID: m002-sim-v0-core-and-woodcutting
- Timestamp CST: 2026-10-28 15:11:50 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (the branch is deleted and the docs committed; sim v0's first slice, the core plus woodcutting, is
  built and tested; the other families follow in later slices)
- Commit: docs `493af16` (branch `sim-v0`); the sim code is uncommitted

## Full Prompt

> Delete the branch, commit the docs, and start building sim v0.

## Response Summary

- **Branch and docs:**
  - deleted `sync-upstream-2009scape` locally and on GitHub, after checking it had no commits outside `main`
  - committed the simulation-decision docs on `sim-v0` as `493af16`; not pushed
- **Sim v0 plan:** reviewable slices:
  1. the core plus woodcutting (this slice)
  2. mining, fishing and thieving
  3. processing
  4. inventory and the economy
  5. combat
  6. the Gymnasium `SimEnv` (observation and masks) and the RL stack
- **Read the server before writing:**
  - `WoodcuttingListener` (swing timing, `checkReward`, `rollDepletion`, XP)
  - `WoodcuttingNode` (the constructor switch and `getRespawnDuration`)
  - `RandomFunction.getSkillSuccessChance`
  - `SkillingTool` (the enum and `getHatchet`'s priority)
  - `Skills` (`SKILL_NAME`, `getExperienceByLevel`)
  - `CharacterDesign` (the starter kit)
  - `ServerConstants.MAX_PLAYERS`
  - the `DraynorWillows` bot (the willow zone)
  - also looked at the mining and fishing rolls, to plan the next slice
- **Built:**
  - `rlscape/sim/` (`skills`, `state`, `options`, `engine`, `woodcutting`, `build_catalog`)
  - three gamedata parsers
  - `rlscape/travel.py`, moved out of `candidates`
  - the `numpy` dependency
  - `tests/test_sim.py`
- **Fixed during testing:**
  1. `tree_types()` crashed on `respawnRate = -1`; it's now parsed as "never falls", matching `rollDepletion`'s
     `> 0` check
  2. the `SkillingTool` regex missed constants written as `Items.NAME_<id>`; now all 36 parse
  3. my statistical test reused one character, which levelled up over 300 runs; it now resets the level each run

## Documentation Changes

- `docs/decision-log.md` (the build and the findings), `ROADMAP.md` (the week-2 status line), and this record.

## Code Changes

- New:
  - `rlscape/sim/__init__.py`, `rlscape/sim/skills.py`, `rlscape/sim/state.py`, `rlscape/sim/options.py`,
    `rlscape/sim/engine.py`, `rlscape/sim/woodcutting.py`
  - `rlscape/travel.py`
  - `tests/test_sim.py`
- Changed:
  - `rlscape/gamedata/server.py` (`starter_kit`, `TreeType`/`tree_types`, `SkillingTool`/`skilling_tools`, paths)
  - `rlscape/combat/candidates.py` (imports travel from `rlscape.travel`)
  - `pyproject.toml` and `uv.lock` (`numpy`)

## Infrastructure Changes

- Deleted the remote branch `sync-upstream-2009scape`. Added the `numpy` 2.5.4 dependency.

## Decisions

- **User decision:** delete the branch, commit the docs, start sim v0.
- **Agent choices (reversible):**
  - the slice order above
  - woodcutting first, done fully, instead of all gathering at once
  - parse server tables from source instead of copying their values
  - one geometric draw per log, and one Bernoulli per fall
  - the engine measures checkpoints at the end of the option that crosses them
  - estimated site tiles and tree counts until a scenery export exists
  - `WALK_BETWEEN_TREES = 3`, to calibrate
  - bird nests deferred

## Validation

- `uv run pytest -q tests/test_sim.py`: 10 passed, covering:
  - the XP table against the server formula
  - the fresh character (total level 33, 10 free slots, 25 bank coins)
  - stacking
  - the parsed tables
  - the success-chance helper
  - axe choice by level
  - sampled ticks per log matching `3 / chop_chance` within 3% over 300 runs
  - same seed, same trajectory
  - masking raises
  - horizon truncation with the checkpoint at hour 20
- Full suite: 35 passed, 14 skipped (the live tests; server stopped).
- A fresh character's first `wc_logs`: 10 logs, 250 XP, `inventory_full` at 197 ticks. The server's G2 gate gave the
  same 10 logs and 250 XP.
- Speed: about 5,700 decisions/s on one core, reset included.

## Follow-Up

- Next slice: mining, fishing (`FishingListener.rollFish`, 5-tick attempts) and pickpocketing.
- A bridge export of the scenery near a tile, to replace the estimated site tiles and tree and rock counts.
- Commit the sim code when Caleb asks.
