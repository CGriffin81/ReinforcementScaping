# Agent Interaction

## Metadata

- Interaction ID: m002-looting-and-hazards
- Timestamp CST: 2026-11-05 22:17:35 CST (from the session transcript's message timestamp, UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: DONE (the command, the uid fix, the hazards and the runner's looting built and tested; the first loot runs
  in; the uid fix, the hazards' scope, OQ-19 and OQ-20 wait on Caleb)
- Commit: fork `d0a7af6` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA
  can only be filled in by a later commit)

## Full Prompt

> Approve the combat-time change and the pickup command.
> Remove the taverley dungeon black knights from the list of enemies that can be fought. They should be treated as hazards, instead.

## Response Summary

- Recorded the approval of "in combat" in game ticks, and OQ-18's answer (a pickup command).
- Built the pickup command in the fork: `ground_items` (what the character sees on the ground) and `take` (a click
  on one's "Take", as the client's packet), with the Python client and live tests.
- Found that bridge characters' kills dropped nothing: every one had account uid 0 and wasn't in
  `Repository.uid_map`, which the server finds a kill's owner by. Gave each its own uid (a fork fix to approve).
- Made Taverley dungeon's two eastern Black Knights hazards: out of the enemy pool, still in the world. Checked live
  that the dungeon's other Black Knights (by the jail) fight as usual, so they stay targets (scope to confirm).
- Raised OQ-19: a fight ignores the aggressive monsters around its site.
- Gave the combat runner looting (`--loot`) and loot gp/hr on both sides; ran it on the ranker's top gp picks.
- Raised OQ-20: the mean gp/hr of a few short runs can't settle the gate where rare drops make up the loot.

## Documentation Changes

- `docs/decision-log.md`: "in combat" approved; OQ-18 answered; the account uid; the hazards; the runner's looting.
- `docs/open-questions-log.md`: OQ-18 removed (answered); OQ-19 (monsters near a fight); OQ-20 (the gp/hr gate).
- `docs/option-catalog.md` §4.C: hazards. `CLAUDE.md`: each bridge character's account uid. `ROADMAP.md`: status.
  This record.

## Code Changes

- `rlscape/combat/candidates.py`: `HAZARDS` and `is_hazard`; `enemy_pool` leaves out hazards' spawns.
- `rlscape/bridge/client.py`: `ground_items`, `take`.
- `scripts/calibrate_combat.py`: `--loot`; the server run waits for a kill's drop and takes its own drops the mode
  keeps; stops on a full inventory; loot gp/hr on both sides; the sim's food eaten leaves out looted food;
  `--resim` recomputes the server's rates.
- Tests: `tests/test_bridge_inputs_live.py` (a drop seen and taken back, both ways; a private drop unseen by another
  character; a kill's drop is its killer's and taken by tile), `tests/test_candidates.py` (hazards aren't targets
  but still aggressors).

## Infrastructure Changes

- Fork (`server/`, uncommitted): `RLCommands.kt` (`ground_items`, `take`; despawn leaves `uid_map`), `RLPlayer.kt`
  (its own account uid, in `uid_map`). Built; the server ran for the tests and the loot runs.

## Decisions

- **User decisions:** "in combat" in game ticks approved; the pickup command (OQ-18 (a)); Taverley dungeon's Black
  Knights are hazards.
- **Agent choices (reversible):**
  - the hazards' scope: the two Black Knights east of the lesser demons, not the jail's 12, which fight as usual
  - the account uid: 1,000,000,000 + the bridge uid
  - the runner's looting: wait up to 6 ticks for a drop, take after 2 idle ticks, its own drops only, within 15 tiles
  - the loot runs: the ranker's top gp picks (the fit set's monsters have no drops), the fresh character's mode
    (valuable)
- **Raised for Caleb:** the account uid fork fix; the hazards' scope; OQ-19; OQ-20.

## Validation

- Live: `ground_items` and `take`, 4 tests passed (a drop taken back with and without the packet; unseen by another
  character; a chicken's bones its killer's after the uid fix, not seen at all before it).
- Live probe: the eastern pair, the click taken and no move, no XP; the jail's knights 842 XP in 150 ticks.
- Loot runs (`results/calibration/combat-20261105-2247-resim.json`, 3 runs a case, loot mode valuable), sim over
  server: XP/hr and kills/hr 0.80 to 1.15 (8 of 8 within ±20%); time to a full inventory 0.81 to 1.05. Unicorn loot
  per kill 838 against 819 to 957; Black Knight runs between the sim's 4th and 96th percentiles, mean gp/hr 0.36 to
  1.97 (rare drops); band-1 hobgoblins 2 items a run, under attack throughout.
- A 40-kill probe of hobgoblins (id 2685): bones every kill, as the sim's table has.
- `uv run pytest -q` with the server up: 306 passed. ruff (pyflakes): passed. The server stopped at the end.

## Follow-Up

- OQ-19, OQ-20; poison; ranged damage taken; magic; the willows' exposure.
- Commit when Caleb asks.
