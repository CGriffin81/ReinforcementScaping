# Agent Interaction

## Metadata

- Interaction ID: m002-subtable-items
- Timestamp CST: 2026-11-06 20:54:02 CST (from the session transcript's queue timestamp, UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the live tests wait for the drop probe to free the server)
- Commit: fork `d0a7af6` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA
  can only be filled in by a later commit)

## Full Prompt

> Add the five items to the vocabulary

## Response Summary

- Added the five items the vocabulary rule proposes once the drop tables' shared sub-tables are modelled (ported in
  `m002-shield-and-vocabulary`'s continuation): rune arrows, the tooth half of a key, a rune 2h sword, an earth
  talisman and mithril bolts. *V* 203; 1,252 actions; 1,992 observation features.

## Documentation Changes

- `docs/decision-log.md`: the sub-tables, the probe, the five items. `docs/option-catalog.md` §9 and its status;
  `docs/env-contract.md` §3's sizes, v1.13's note, decision 30. `ROADMAP.md`. This record.

## Code Changes

- `data/vocabulary.csv` (+5), `rlscape/vocabulary.py`'s docstring, `tests/test_vocabulary.py` (the sizes).

## Infrastructure Changes

- None.

## Decisions

- **User decision:** add the five items.
- **Claude's recommendation:** they were held until the drop probe confirmed the sub-tables against the server;
  Caleb added them now.

## Validation

- `tests/test_vocabulary.py`, `tests/test_sim_buying.py`, `tests/test_sim_env.py`: 30 passed (each item has a 2009
  price and can be alched).

## Follow-Up

- The drop probe's results; the live suite after it.
- Commit when Caleb asks.
