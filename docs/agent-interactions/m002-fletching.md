# Agent Interaction

## Metadata

- Interaction ID: m002-fletching
- Timestamp CST: 2026-10-31 04:50:38 CST (from the session transcript's message timestamp, UTC−05:00); mid-turn
  message at 05:01:03 CST
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (Fletching built into sim v0 as decided, with the knife spawn; the guide trains it; docs and env
  contract v1.7 updated)
- Commit: the commit that adds this record holds this work (main repo, branch `sim-v0`; its SHA can only be
  filled in by a later commit)

## Full Prompt

> B, but do not use bowstrings to complete bows where the value of the bow is not greater than unfinished +
> bowstring. Take the recommended option for other fletching decisions.

Mid-turn:

> There should be a knife spawn in Lumbridge Castle, which is very convenient for a fresh starting character.

## Response Summary

- **Fletching in sim v0**, from the server's recipes (44: logs cut into arrow shafts or bows (u), stringing,
  headless arrows, arrows, darts after The Tourist Trap, bolts), at the live-measured timings: a log every 3 ticks,
  stringing every 2, arrows 15 and darts or bolts 10 per 3-tick stage, after a first tick.
- **Caleb's stringing rule**, at prices_v2's values: only maple, yew and magic longbows and yew shortbows are strung.
- **The recommended rest:**
  - woodcutting's chop-and-fletch paths (`wc_<tree>_fletch`): normal logs into arrow shafts (they stack, so the
    chopping goes on), other logs into the best bow (u) the level allows
  - Fletching's own skilling slots over bank paths (`fletch_<recipe>`): a load of inputs from the bank, crafted,
    banked, again
  - the guide trains Fletching by the Fletching article ([40])
- **The knife spawn:** the server's ground spawns have knives at (3205, 3212, 0) and (3224, 3202, 0). `take_knife`
  walks to the nearest and picks it up while no knife is held; a fresh character has one in under 30 ticks.
- **Sizes:** *V* = 176 (20 fletching inputs added by *V*'s rule), 1,110 actions, 1,860 observation features.

## Documentation Changes

- `docs/option-catalog.md`:
  - §2: the chop-and-fletch paths, Fletching's paths and recipes, 5 skills × 4 = 20 slots, 79 paths
  - §3.5: Fletching moved to sim v0
  - §5: `take_knife`; the woodcutting kit keeps a knife; the Fletching kit
  - §8: the knife and 19 fletching inputs (96 GE actions)
  - §9: the sizes (1,110 actions)
- `docs/env-contract.md`: v1.7; §5 (Fletching in sim v0, 15 skills; sim v1 adds 4); §3 (skilling candidates
  20 × 5, task 12-way, 1,860 features); decision 23.
- `docs/scripted-guide-draft.md`: the fourth revision note and results.
- `docs/decision-log.md`, `ROADMAP.md`.
- This record.

## Code Changes

- `rlscape/gamedata/server.py`: `FletchRecipe`, `fletching_recipes()` (from the server's fletching enums),
  `ground_spawns(item)`, and the fletching item constants.
- `rlscape/sim/fletching.py` (new): `worth_stringing`, `path_recipes`, `Fletch`, `wood_recipe`, `FletchLogs`,
  `FletchAtBank`, `fletching_paths`.
- `rlscape/sim/skilling.py`: Fletching in `SKILLS`; the chop-and-fletch paths; the Fletching paths; their rates
  (`_fletch_rate`).
- `rlscape/sim/economy.py`: `TakeSpawn` (`take_knife`); the woodcutting kit withdrawal takes a knife; deposits keep
  it.
- `rlscape/sim/kits.py`: the woodcutting kit keeps the knife; a Fletching kit.
- `rlscape/sim/buying.py`: the knife and 19 fletching inputs on the GE.
- `rlscape/envs/encoding.py`: the fletching task.
- `data/vocabulary.csv`, `rlscape/vocabulary.py`: *V* = 176.
- `rlscape/baselines/guide.py`: Fletching as the 14th skill (`FLETCHING`, `fletching_methods`, `take_knife`).
- Tests:
  - `tests/test_sim_fletching.py` (new): the recipes, the stringing rule, timings, darts and the quest, the bank
    path and its rate, chop-and-fletch, the kits, `take_knife`
  - updated: `tests/test_sim_skilling.py`, `tests/test_vocabulary.py`, `tests/test_sim_buying.py`,
    `tests/test_guide.py`

## Infrastructure Changes

None.

## Decisions

- **User decisions:**
  - Fletching option B (cutting, stringing, arrows, darts, bolts)
  - stringing only where the bow is worth more than its parts
  - the recommended rest: chop-and-fletch paths, Fletching's own slots, the guide following [40]
  - the Lumbridge Castle knife
- **Agent choices (reversible):**
  - leaving out stocks, ogre, dragon, broad, blurite and silver recipes (quests or items not in sim v0)
  - shafts from normal logs and the best bow (u) for other logs on chop-and-fletch paths
  - lots of 1,000 for the fletching inputs, as for processing inputs
  - the guide's Fletching table

## Validation

- `uv run pytest -q`: 218 passed, 24 skipped (live tests; the server was down).
- `uvx ruff check --select F401,F811,F841 rlscape tests scripts`: passed.
- The Fletching bank path's modelled XP rate is within 5% of its simulation (test).
- `scripts/evaluate.py --policies scripted_guide random --seeds 10` (`results/eval/guide-fletching-20261031`), hour
  20: guide total level 312 [307, 316], total XP 94,137, net worth 107,825; random 235 [227, 243], 101,804, 8,398.
- Seed 0 of the guide, rerun: Fletching 20; 13,205 arrow shafts are 66k of its 106k net worth. A first draft of the
  guide page said bows drove the gain; this check corrected it.

## Follow-Up

- Commit when Caleb asks; fill in this record's and `m002-skilling-slots`' Commit fields then.
- The prayer-flicking live test (needs a prayer-toggle bridge command, a fork change).
