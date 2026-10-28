# Agent Interaction

## Metadata

- Interaction ID: m002-al-kharid-toll
- Timestamp CST: 2026-10-28 16:14:07 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: main repo: the commit that adds this record, on branch `sim-v0` (its SHA can only be filled in by a later
  commit)

## Full Prompt

> The finding for Firemaking is normal. It's normally seen as a kind of do-nothing skill, since it doesn't really
> unlock anything. Also, there is no return for your logs when they are burned.
>
> Model the 10 gp toll on the al kharid gate. Commit the slice but we'll have to wait a few hours to continue work.

## Response Summary

- **Firemaking:** recorded Caleb's judgement that the speed is normal. The model already charges for burning: logs
  leave with no product, so net worth falls. The calibration flag is dropped.
- **Read the server first:**
  - `TollGateOptionPlugin`: the "pay-toll(10gp)" option on the gate objects, 10 coins from the inventory, free past
    Prince Ali Rescue stage 50
  - `BorderGuardDialogue`: the same rules when talking to the guards
- **Built `rlscape/sim/movement.py`:**
  - `uses_toll_gate`, `route_ticks` and `walk`; when the toll can't be paid, the route goes round the fence's north end
  - moved every option's walk onto it: the gathering loop, fishing, pickpocketing, processing stations
  - nearest-station choices rank by `route_ticks`
- Updated the catalog's Al Kharid region note and the stations file's Al Kharid range note.
- Committed the processing slice together with the toll (one commit, as asked); not pushed.

## Documentation Changes

- `docs/decision-log.md` (Caleb's firemaking judgement; the toll), `docs/option-catalog.md` (the `al_kharid` region
  note), `data/stations.csv` (a check note), and this record.

## Code Changes

- New: `rlscape/sim/movement.py`, `tests/test_sim_movement.py`.
- Changed: `rlscape/sim/gathering.py`, `rlscape/sim/fishing.py`, `rlscape/sim/thieving.py` and
  `rlscape/sim/processing.py` (walking through `walk`; stations ranked by route).

## Infrastructure Changes

None.

## Decisions

- **User decisions:**
  - firemaking's speed is normal, with no calibration flag
  - model the 10 gp toll
  - commit, then pause
- **Agent choices (reversible):**
  - the toll is paid automatically when coins are held, as any player would
  - with no coins, a free detour round the fence instead of a dead end, so a broke character is never stranded in Al
    Kharid
  - Prince Ali Rescue counts only when complete; the server waives the toll past stage 50
  - the fence geometry is an estimate

## Validation

- `uv run pytest -q`: 66 passed, 14 skipped. The new tests check:
  - which walks use the gate (not from Varrock, north of the fence)
  - the toll paid both ways
  - the Prince Ali Rescue waiver
  - the longer detour without coins, and arriving all the same
  - nothing paid when the budget runs out on the way
  - `cook_fish` paying 10 coins to reach the Al Kharid range

## Follow-Up

- When work resumes: the inventory and economy family (bank, drop, sell, buy, alch).
- Calibration: the fence line, its north end and the detour route.
