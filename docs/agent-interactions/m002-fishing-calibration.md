# Agent Interaction

## Metadata

- Interaction ID: m002-fishing-calibration
- Timestamp CST: 2026-10-31 19:29:11 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (every fishing case within ±20%; shrimp at Lumbridge Swamp too; Draynor's danger modelled)
- Commit: the main repo commit that adds this record (branch `sim-v0`; its SHA can only be filled in by a later commit)

## Full Prompt

> Calibrate fishing.

Claude asked two questions (`AskUserQuestion`); Caleb's answers:
- "Fishing calibrates within ±6% at bands 31–91 ... The exception is a level-3 fisher at Draynor's shrimp spots ...
  What should fish_shrimp be?": "Both sites".
- "The scripted guide (your signed-off E1 baseline) fishes shrimp at Draynor below Fishing 20 ... What should the
  guide do?": "Swamp below combat 15 (Recommended)".

## Response Summary

- Fishing calibrated at all four bands on full loads: the first attempt's and the after-catch tick measured and
  ported, and the server's spot-move rule (a spot moves only onto a tile with no NPC on it) ported.
- Draynor's shrimp spots kill a level-3 fisher on the server. On Caleb's answer, shrimp are fished at Lumbridge
  Swamp too, and the sim's aggression model gained engagements (a wizard casts every 5 ticks until the character
  runs, and as it runs), fitted on 40 traced server runs: Draynor's level-3 fisher within the gate (1.08).
- The scripted guide fishes shrimp at the swamp until its combat level passes 14 (Caleb).

## Documentation Changes

- `docs/decision-log.md`: the entry, with both questions, their options and Caleb's answers, and the tables.
- `docs/option-catalog.md`: 83 paths (fishing 8), `fish_shrimp_swamp`, Lumbridge Swamp's net fishing, Draynor's
  shrimp spots' measured exposure.
- `docs/scripted-guide-draft.md`: the guide's shrimp site.
- `ROADMAP.md`: status.
- This record.

## Code Changes

- `rlscape/sim/fishing.py`: `FIRST_ATTEMPT_TICKS`, `AFTER_CATCH_TICKS`, the spot-move chance, start tiles and local
  tiles, `fish_shrimp_swamp`, Draynor's measured exposure.
- `rlscape/sim/aggression.py`: `SiteExposure`; engagements (rate, cadence); attacks while running away (chase);
  `died_at`.
- `rlscape/sim/gathering.py`, `rlscape/sim/mining.py`: a site's `SiteExposure`; an option that ends in death ends at
  the death.
- `rlscape/sim/skilling.py`: the rate model's fishing timing; the start tile.
- `rlscape/gamedata/server.py`: `fishing_spot_ids`, `fish_spot_counts`.
- `rlscape/bridge/client.py`: `safespots` takes `object` (NPC targets).
- `rlscape/baselines/guide.py`: `shrimp_method` (Caleb's answer).
- `scripts/calibrate.py`: fishing cases, the shore tile, the starter kit dropped, a run ends at a death, hits by
  mode, the trace's hitpoints, mode and attackers; safespots against melee attackers only.
- Tests: `tests/test_sim_gathering.py` (spot moves, attempt timing), `tests/test_sim_aggression.py` (the chase and
  deaths), `tests/test_sim_skilling.py` and `tests/test_sim_gathering.py` (path counts, fishing's slots),
  `tests/test_guide.py` (the shrimp site).

## Infrastructure Changes

- The server run for the calibration (no fork changes); stopped at the end.

## Decisions

- **User decisions:** shrimp at both sites; the guide at the swamp below combat 15.
- **Agent choices (reversible):**
  - the fishing cases drop the starter kit, so loads are full and spots move during them
  - attacks while engaged are a Poisson process at the cadence, not a fixed beat
  - the willows and Al Kharid keep their rate model (engaged throughout) rather than being re-measured as
    engagements
  - the flee time at Draynor includes the walk back (the sim adds it before healing)
  - safespotting is tried only against melee attackers

## Validation

- `uv run pytest -q` with the server up: 278 passed; ruff (unused names): passed.
- The calibration table and rechecks in the decision log; E1 rerun (10 seeds).

## Follow-Up

- Travel and banking.
- The Dark wizards' cast every 5 ticks against a configured speed of 4: check NPC attack cadence in combat
  calibration.
- Commit when Caleb asks.
