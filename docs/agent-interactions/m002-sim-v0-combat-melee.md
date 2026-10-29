# Agent Interaction

## Metadata

- Interaction ID: m002-sim-v0-combat-melee
- Timestamp CST: 2026-10-28 22:30:04 CST (the same prompt as `m002-sim-v0-inventory-and-selling`, from the session
  transcript's message timestamp, UTC−05:00; this is the second piece of work done under it)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (melee fights, drops, death and gravestones are built and tested; ranged, magic, candidate-slot
  actions and loot-mode actions come next)
- Commit: main repo: the commit that adds this record, on branch `sim-v0` (its SHA can only be filled in by a later
  commit)

## Full Prompt

> Continue work on the project. Try to avoid things that need my approval for now.

## Response Summary

- **Read the server first:**
  - `WeightBasedTable` (roll, special slots) and `WeightedItem.getItem` (`random(min, max)`, upper bound excluded)
  - `ItemQuestRequirementListener` (17 equip locks), `EquipmentContainer` slots
  - `WildernessZone` (borders), rl.conf's `home_location`
  - `DeathTask`, `GraveController` and `GraveType` (via the death rule already recorded)
- **Found and fixed two drop-model divergences from the server:**
  - amounts excluded max; the mean had been (min + max) / 2
  - 477 placeholder entries had counted as items and slots
- **Built:**
  - `rlscape/sim/equipment.py` (wearing rules, `wield_best`, `fighter_for`)
  - `rlscape/sim/combat.py` (`fight` with kill sampling, eating, retreat and death; `roll_drops`; `die`;
    `ReclaimGravestone`)
  - gamedata `equip_quest_locks()`; public offence helpers in `rlscape/combat/rates.py`
  - `CharacterState.gravestone`, and the engine clearing expired gravestones
  - `reclaim_gravestone` in the catalog
- **Fixed during testing:**
  1. the first wielding pass picked the slower bronze axe over the sword; the score now divides by attack speed
  2. a retreat mid-kill returned before charging the time fought and the XP for damage dealt; it now uses the kill's
     cumulative-damage sequence
  3. my death test assumed the wrong kept items (a rune full helm alchs for more than a rune scimitar); the test now
     computes them

## Documentation Changes

- `docs/decision-log.md` (the build, the findings, the agent choices, what's still to come), and this record.

## Code Changes

- New: `rlscape/sim/equipment.py`, `rlscape/sim/combat.py`, `tests/test_sim_combat.py`.
- Changed:
  - `rlscape/gamedata/server.py` (`DropEntry.mean_amount`, `special`, `SPECIAL_DROP_SLOTS`, `expected_items`,
    `equip_quest_locks`)
  - `rlscape/combat/rates.py` (offence helpers made public)
  - `rlscape/sim/state.py` (`gravestone`), `rlscape/sim/engine.py` (gravestone expiry), `rlscape/sim/__init__.py`
    (`ReclaimGravestone`)

## Infrastructure Changes

None.

## Decisions

- **User instruction:** avoid things that need approval.
- **Agent choices (reversible, in the decision log):**
  - automatic wielding of the best gear carried
  - "underway" quest locks read as "complete"
  - Protect Item not modelled; stacks as one unit for the kept items
  - unfitting reclaimed items left behind
  - placeholder drop slots counted as nothing until their sub-tables are ported (a server-fidelity fix, not a design
    change)

## Validation

- `uv run pytest -q`: 90 passed, 14 skipped. The new tests check:
  - drops (cow items present, placeholders never dropped, amounts never reaching max)
  - sampled kill times within 3% of the rate model
  - wielding (sword over axe, the Dragon Slayer lock, a two-handed bow)
  - a level-30 fighter's exact Strength and Hitpoints XP per kill and its `inventory_full` stop
  - fresh characters stopping out of food and never dying on cows, with the time charged
  - the Wilderness borders
  - death keeping the top 3 alchemy items and leaving a timed gravestone
  - no gravestone in the Wilderness
  - reclaiming only while the walk beats the timer

## Follow-Up

- Ranged and magic fights; candidate-slot actions (after making the ranking fast); loot-mode actions.
- Drop sub-tables (rare drop table, gems, herbs, seeds).
- Commit everything when Caleb asks.
