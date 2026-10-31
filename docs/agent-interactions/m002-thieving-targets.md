# Agent Interaction

## Metadata

- Interaction ID: m002-thieving-targets
- Timestamp CST: 2026-10-30 18:58:40 CST (from the session transcript's message timestamp, UTC−05:00); the mid-turn
  message at 19:08:55 CST
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the previous work committed; 13 pickpocket targets built and tested; the tick-manipulation finding
  corrected; stalls wait on Caleb's call about the market guards)
- Commit: the guide, withdraw-to-sell and task kits are main repo `63ebb0d` (branch `sim-v0`); this work is the main
  repo commit that adds this record (its SHA can only be filled in by a later commit)

## Full Prompt

> Commit this and keep going with thieving

Mid-turn:

> I've seen tick manipulation methods with fishing and mining using either herb+tar+pestle/mortar or knife +
> log/barbarian fish.

## Response Summary

- **Committed** the scripted guide draft, withdraw-to-sell and task kits as `63ebb0d`.
- **Built 13 pickpocket targets** from the server's Pickpockets table (Caleb's "Targets and stalls"):
  - men, farmers, both H.A.M. members, warriors, master farmers, guards, Fremenniks, Knights of Ardougne, Yanille
    watchmen, paladins, gnomes, heroes
  - each at its server spawn nearest Lumbridge, outside the Wilderness and the access table's areas
  - weighted loot, the server's canRoll rule, and loot lost when it doesn't fit
  - an eating rule that keeps a failed attempt from killing: heroes hit 6, above a 10-HP character's retreat point
- **Left out, with reasons:** rogues (Wilderness only), cave goblins (Dorgesh-Kaan is outside the travel model),
  bearded bandits (no spawns), desert bandits and Menaphite thugs (behind the Shantay Pass gate, which takes a pass).
- **Stalls not built.** The server's guards attack 4 in 15 steals when within 8 tiles, and Ardougne's market has 7
  guard spawns near its stalls. How the character responds is a modelling choice for Caleb.
- **The mid-turn question:** checked both methods in the server code. Neither works on 2009Scape, and the check
  showed the earlier 2-tick woodcutting finding was wrong. Every action that sets the skilling clock first checks
  that it's ready, so none can shorten a wait. Herb on tar doesn't use the clock. Mining doesn't use it either.

## Documentation Changes

- `docs/option-catalog.md`:
  - §2: the 13 target rows and the pickpocketing rules
  - §9: 993 actions
- `docs/env-contract.md`: §3's as-built note (993 actions, 1,602 features).
- `docs/decision-log.md`: the targets, the stall questions, and the tick-manipulation correction.
- `ROADMAP.md`: the status line.
- `Commit:` fields of `m002-scripted-guide`, `m002-withdraw-for-sale` and `m002-task-kits` (`63ebb0d`).
- This record.

## Code Changes

- `rlscape/gamedata/server.py`: `pickpocket_targets` reads `IntStream.rangeClosed` ids (cave goblins) and
  `insertEasyClue` (`CLUE_SLOT_EASY`).
- `rlscape/sim/thieving.py`:
  - `PICKPOCKET_TARGETS` and `LEFT_OUT`
  - `Pickpocket` gains weighted loot (`_succeed`), `can_roll` and `eat_below`
  - `nearest_spawn` skips the Wilderness and the access table's areas
  - `largest_random`
- Tests:
  - `tests/test_sim_thieving.py`: every target parses; each target has an option or a reason; weighted loot follows
    the table; canRoll and lost loot; non-stackable loot fills the inventory; a hero's hit never kills
  - `tests/test_vocabulary.py`: 993 actions and 1,602 features

## Infrastructure Changes

None.

## Decisions

- **User decisions:** commit; continue with thieving (targets and stalls, decided earlier).
- **Agent choices (reversible):**
  - the option ids
  - sites at the spawn nearest Lumbridge
  - the five targets left out
  - the eat-at-the-largest-hit rule
  - the clue slot giving nothing, as in combat drops
- **Awaiting Caleb:**
  - how stall guards are handled
  - whether to model the Shantay Pass for the two desert targets
  - whether to drop the tick-manipulation live test

## Validation

- `uv run pytest -q`: 183 passed and 18 skipped.
- The first loot-frequency test failed on coins, because stacked coins counted once per inventory. That was a test
  bug: it now rolls one success per empty inventory.
- Rates with HP to spare, while pickpocketing (no banking), from `pickpocket_options()` over 40 runs of 600 ticks
  each:

  | Target | XP/h and gp/h |
  |---|---|
  | men (level 1) | 12k XP/h |
  | H.A.M. men (level 20) | 26k XP/h, 227k gp/h |
  | master farmers (level 38) | 43k XP/h, 355k gp/h |
  | Knights of Ardougne (level 55) | 95k XP/h |
  | heroes (level 80) | 159k XP/h, 548k gp/h |

  The gp figures come from grimy kwuarm (2,911 gp) and ranarr and snapdragon seeds (22,700 and 37,500 gp) at January
  2009 prices. The sim is uncalibrated.
- The tick-manipulation correction comes from reading `ContentAPI.delayClock`/`clockReady`, `FishingListener`,
  `MiningListener`, `WoodcuttingListener`, `CraftItemWithLogScript`, `BoneBuryListener`, `HerbTarPlugin` and
  `HerbTarPulse`. It's not tested live.

## Follow-Up

- Caleb's three calls, then stalls.
- Then the wider guide, skilling slots, and the prayer-flicking live test.
- Commit when Caleb asks.
