# Agent Interaction

## Metadata

- Interaction ID: m002-cooking-on-fires
- Timestamp CST: 2026-10-28 16:19:15 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: main repo: the commit that adds this record, on branch `sim-v0` (its SHA can only be filled in by a later
  commit)

## Full Prompt

> Cooking most food does not require a range and can be cooked on a player-created fire.

## Response Summary

- **Checked the server:**
  - `StandardCookingPulse` already supports fires (a 4-tick delay and the fire burn bounds)
  - `CookingRewrite` refuses a fire only for bread dough, uncooked cake and barley ("You need to cook this on a range")
- **Changed `Cook`:**
  - with a tinderbox and a lightable log, it lights the cheapest log where the character stands (the firemaking roll,
    XP, a fire of `Log.life` ticks)
  - it cooks the fire-cookable food there
  - it walks to the nearest range only for range-only food, or when no fire can be made
- **gamedata:** `log_fire_ticks()`, sharing a `_logs()` parse with `log_types()`.
- Updated the catalog's `cook_fish` row and the processing module docstring.

## Documentation Changes

- `docs/option-catalog.md` (the `cook_fish` row), `docs/decision-log.md`, and this record.

## Code Changes

- `rlscape/sim/processing.py`: `Cook` (fire first, range fallback), `FIRE_TICKS`, `RANGE_ONLY`, the docstring.
- `rlscape/gamedata/server.py`: `log_fire_ticks`, `_logs`.
- `tests/test_sim_processing.py`: 3 tests.

## Infrastructure Changes

None.

## Decisions

- **User correction:** most food cooks on a player-made fire.
- **Agent choices (reversible):**
  - prefer a fire whenever one can be made, since it's faster (4 vs 5 ticks) and needs no walk; the Lumbridge range's
    slightly better bounds are ignored when a fire is possible
  - burn the cheapest lightable log
  - one fire per option, since `Log.life` (180+ ticks) outlasts a full inventory; a fire that burns out sends the rest
    of the food to a range

## Validation

- `uv run pytest -q`: 69 passed, 14 skipped. The new tests check:
  - cooking at the Draynor spot with no walk and no toll, one log used, 40 Firemaking XP, and exactly
    `3 + 1 + 10 × 4` ticks
  - bread dough still going to a range, after the shrimp are cooked on a fire
  - no tinderbox meaning a range
- Smoke run: 10 shrimps cooked on the spot in 44 ticks.

## Follow-Up

- Commit when Caleb asks; then the inventory and economy family.
