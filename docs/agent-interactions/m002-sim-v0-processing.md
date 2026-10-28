# Agent Interaction

## Metadata

- Interaction ID: m002-sim-v0-processing
- Timestamp CST: 2026-10-28 15:59:43 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the pickpocketing slice is committed; the processing family is built and tested)
- Commit: pickpocketing slice `32f4ed3` (branch `sim-v0`); processing uncommitted

## Full Prompt

> Commit this slice and keep going with processing

## Response Summary

- Committed the pickpocketing slice as `32f4ed3`; not pushed.
- **Read the server first:**
  - smelting: `SmeltingPulse` (timing, iron's `nextBool`, XP) and `smelting.Bar`
  - smithing: `SmithingPulse` (delay, bars and XP per item, quest checks), `Bars`, `SmithingType`, `BarType`
  - cooking: `StandardCookingPulse` (range and fire delays, `isBurned`, the Lumbridge range) and `CookableItems`
    (with `lumbridgeRangeValues`)
  - firemaking: `FireMakingPulse` (attempt timing, `success`, `setLastFire`) and `firemaking.Log`
  - burying: `BoneBuryListener` and `Bones`
  - for station tiles: the `VarrockSmither` bot, plus the diary checks in the smelting and smithing pulses
- **Built:**
  - `rlscape/sim/processing.py` (9 options and the nearest-station lookup)
  - `data/stations.csv`
  - six gamedata parsers
  - catalog §3 wired into `build_catalog`
  - `tests/test_sim_processing.py`
- **Raised for calibration:**
  - the 2-tick relight makes firemaking about 114k XP/hr at level 1
  - the Al Kharid toll gate isn't modelled
  - the estimated station tiles
  - fresh characters have no hammer

## Documentation Changes

- `docs/decision-log.md` (the build and the findings), `ROADMAP.md` (the week-2 status line), and this record.

## Code Changes

- New: `rlscape/sim/processing.py`, `data/stations.csv`, `tests/test_sim_processing.py`.
- Changed:
  - `rlscape/gamedata/server.py`: `SmeltedBar`/`smelted_bars`, `Smithable`/`smithables`, `Cookable`/`cookables`,
    `log_types`, `bone_experience`, `Station`/`stations`, paths
  - `rlscape/sim/__init__.py`: the catalog

## Infrastructure Changes

None.

## Decisions

- **User decision:** commit the pickpocketing slice, then build processing.
- **Agent choices (reversible):**
  - smithing's "best item" means the most bars per item, then value per bar, which is what a player training Smithing
    did
  - cooking covers everything `CookableItems` turns into food, not only fish (the option keeps the catalog's id,
    `cook_fish`)
  - cooking uses ranges only, not fires
  - `CHAIN_TICKS = 2` for a line of fires, to calibrate
  - stations are a curated CSV, nearest reachable station first
  - the pulses' first-tick delays are kept

## Validation

- `uv run pytest -q`: 60 passed, 14 skipped. The new tests check:
  - the parsed tables, including the smithable count against every `Bars` entry
  - iron smelting at 50% with the ores used either way
  - the smithing choice (a platebody at 18; 3-bar items at 17; leftovers used) and its XP
  - the Lumbridge range only with Cook's Assistant
  - the burn rate against the range bounds
  - the light chance against 400k simulated `random(99)` rolls
  - a line of fires rolling only for the first log
  - bone timing and XP
  - the masks following the inputs
- Smoke run:
  - 7 bronze bars: 56 ticks including the walk
  - two bronze two-handed swords and a wire from 7 bars at Smithing 15
  - 10 shrimps at Cooking 1: 5 cooked, 5 burnt
  - 10 logs: 21 ticks
  - 10 bones: 20 ticks

## Follow-Up

- Next: inventory and the economy (bank, drop, sell, buy, alch), which brings the hammer, food and feathers within
  reach.
- Calibration: `CHAIN_TICKS`, the station tiles, and the Al Kharid toll.
- Commit this slice when Caleb asks.
