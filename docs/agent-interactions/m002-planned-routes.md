# Agent Interaction

## Metadata

- Interaction ID: m002-planned-routes
- Timestamp CST: 2026-11-01 13:47:58 CST (from the session transcript's message timestamp, UTC−06:00); follow-ups at
  14:21:13, 14:29:41 and 14:34:05 CST
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (committed as asked; the sim walks the planned routes; OQ-10 and OQ-11 answered)
- Commit: the earlier travel and banking work is fork `8fe7cda` (branch `rl`) and main repo `da7a105` (branch
  `sim-v0`); this work is fork `d0a7af6` (branch `rl`) and the main repo commit that adds this record (branch
  `sim-v0`; its SHA can only be filled in by a later commit)

## Full Prompt

> Approve the state fields, commit, then switch the sim to planned routes.
> For OQ-10, all teleport jewelry at all charge levels are usable for teleporting and should be purchasable at any charge level as well. Notably, there are some teleport items that are consumable like teleport tablets

Follow-ups while the work ran:

> What can we do while the table builds?

> Add the ectophial.

> Add both for a later episode. Also add the seed pod from The Grand Tree.

## Response Summary

- Recorded the approval and OQ-10's answer, committed the fork (`8fe7cda`) and the main repo (`da7a105`).
- Switched the sim's travel to the planned routes: a table between the places the sim travels, searches for other
  tiles, the measured overheads, the toll gate decided by the planned lengths, the combat ranker on the same lengths.
- Checked it: the measured trips within 0.95 to 1.12 of the server; the gathering calibrations unchanged; E1 rerun;
  speed measured (about 30% slower).
- While the table built: mapped the server's transports (jewellery, tablets, spells, home teleport, ships,
  charters); recorded the Ectophial, OQ-11 (answered: both quests join the set) and the Grand seed pod.
- Fixed a pre-existing crash the speed benchmark found (an item needing a skill the sim lacks).

## Documentation Changes

- `docs/decision-log.md`: the approval and OQ-10; the Ectophial; OQ-11 and the seed pod; the switch.
- `docs/open-questions-log.md`: OQ-10 and OQ-11 removed (answered); OQ-7's speed updated.
- `docs/option-catalog.md`: travel as built, transports as decided. `ROADMAP.md`: status.
- `docs/agent-interactions/m002-travel-and-banking.md`: its commit field. This record.

## Code Changes

- `rlscape/routes.py`: anchors, the places' table (`Places`, `build_table`, `places`), `planned_steps`, `lengths`.
- `rlscape/travel.py`: planned lengths, the overheads, the straight-line fallback and its counter, `Destinations`,
  `travel_ticks_from_many`; paths remembered.
- `rlscape/sim/movement.py`: `timed`, the toll gate by planned lengths (`pays_toll`), the Shantay gate as a fixed leg.
- `rlscape/combat/ranking.py`, `rlscape/combat/candidates.py`, `rlscape/sim/buying.py`: the same travel.
- `rlscape/sim/equipment.py`: a requirement on a skill the sim lacks can't be met.
- `scripts/build_travel_places.py` (new), `data/travel/places.csv`; `.gitignore`: the built table.
- Tests: `tests/test_travel.py` (new); `tests/test_sim_movement.py`, `tests/test_sim_energy.py`,
  `tests/test_candidates.py`, `tests/test_sim_fletching.py` updated to planned routes; `tests/test_sim_combat.py`.

## Infrastructure Changes

- The server run for the live tests; stopped at the end. The place table (`data/travel/places.npz`) is built locally.

## Decisions

- **User decisions:** the state fields approved; OQ-10 (all teleport jewellery at all charges, usable and buyable;
  consumable teleports count); the Ectophial; OQ-11 (both quests, read as joining the set: to confirm); the Grand
  seed pod.
- **Agent choices (reversible):**
  - the overheads apply once per walk (start) and per step (pauses), as rest for run energy
  - walks are taken as the same both ways (walls are flagged on both sides)
  - the toll gate is used only when it shortens the walk
  - the place list comes from the data and from planned-route episodes; misses are searched
  - unreachable and off-map walks keep the straight-line estimate until the transports and crossings exist

## Validation

- `uv run pytest -q`: 252 passed offline; the 40 live tests passed with the server up.
- The trip recheck, the gathering rechecks, E1 and the speed benchmark in the decision log.
- ruff (unused names): passed.

## Follow-Up

- The transports and crossings (the Wilderness ditch, the Gnome Stronghold gate); then recalibrate travel on fresh
  trips.
- Confirm the reading of "for a later episode" (OQ-11).
- Commit when Caleb asks.
