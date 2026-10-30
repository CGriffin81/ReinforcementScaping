# Agent Interaction

## Metadata

- Interaction ID: m002-vocabulary-draft
- Timestamp CST: 2026-10-30 14:30:31 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the Gymnasium layer committed; the item vocabulary drafted for Caleb's check)
- Commit: the Gymnasium layer is main repo `44ad628` (branch `sim-v0`); the vocabulary draft is the main repo commit
  that adds this record (its SHA can only be filled in by a later commit)

## Full Prompt

> Commit this and keep going with the item vocabulary

## Response Summary

- **Committed the Gymnasium layer** as `44ad628`, after the suite passed with the server stopped (153 passed, 18
  skipped).
- **Drafted the item vocabulary *V*.** The rule is agreed and Caleb checks the list, so this is a draft, not a
  change to the catalog:
  - `scripts/draft_vocabulary.py` applies the rule to the simulator's own data: what the activities produce and
    consume, every bought item, and the valuable common drops from a candidate-selection sweep.
  - It writes `data/vocabulary_draft.csv`, one row per item with the groups that put it there, its value, its drop
    data and the recommendation.
  - `docs/vocabulary-draft.md` explains the result, asks four questions with recommendations, and lists the
    recommended 156 items and what's left out.
- **Found:**
  - the rule taken literally gives 208 items, because buying alone adds 77
  - each *V* item adds 7 observation features, because the mask is part of the observation
- **Smoke-tested** the sim and `SimEnv` with the recommended *V*.

## Documentation Changes

- `docs/vocabulary-draft.md` (new): the draft for Caleb.
- `docs/option-catalog.md` §9: a pointer to the draft, noting that the estimate of 60 predates buying.
- `docs/decision-log.md`: the draft, the findings and the recommendation.
- `ROADMAP.md`: the status line.
- `m002-gymnasium-layer`'s `Commit:` field, now `44ad628`.
- This record.

## Code Changes

- `scripts/draft_vocabulary.py` (new):
  - produced and consumed items from the sim's sites, recipes and smithing options
  - bought items from `rlscape/sim/buying.py`
  - the drop sweep over bands, hubs and combat classes
  - writes `data/vocabulary_draft.csv`
- `data/vocabulary_draft.csv` (new, generated).
- No change to `rlscape/`: the catalog's *V* stays empty until Caleb signs off.

## Infrastructure Changes

None.

## Decisions

- **User decisions:** commit, then work on the item vocabulary. The rule was agreed earlier (2026-10-28); Caleb
  checks the list.
- **Agent recommendations, awaiting Caleb (Q1–Q4 in the draft):**
  - "common" drops: in at least 20 of the sweep's fights, and worth at least 1,000 gp/hr somewhere
  - smithed products that no other group names stay misc
  - burnt food stays out
  - the herb seeds and grimy herbs stay in for now
- **Agent choices in the method (reversible):**
  - the sweep uses the calibration bands' levels, gear and quests, 18 hubs and loot mode `all`
  - noted drops count as their items
  - coins are never in *V*

## Validation

- The script runs in about 15 s and gives 156 proposed items out of 255 rows.
- `SimEnv(vocabulary=V)` with the proposed list: 979 actions and 1,579 observation features. That was 157 items,
  before the noted-coal fix removed the duplicate coal id. 400 random masked steps over 5 seeds kept the
  observation inside its space and never left an empty or negative stack, at 135 steps/s; 114 per-item actions
  were picked.
- All 156 items have a 2009 GE price and can be alched, so none of their per-item actions is always masked.
- Mistakes caught while checking the draft against the data:
  - Coal appeared twice: the drop was a banknote id, so drops now count as their items.
  - The burnt-food rows had no names. They're untradeable, so neither export names them; they're now named after
    the food they came from.
  - A claim about black items' alchemy value didn't match the data and was replaced with a GE price.
  - The herb count was 23, not 24.

## Follow-Up

- Caleb's answers to Q1–Q4. Then *V* becomes the catalog's default (catalog §9, with tests).
- Commit when Caleb asks.
- The baselines and the eval harness.
