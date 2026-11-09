# Agent Interaction

## Metadata

- Interaction ID: m002-agility-shortcuts
- Timestamp CST: 2026-11-08 22:12:04 CST, from the session transcript's message timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab), the Agility session, beside the Herblore and Runecrafting sessions in the
  same checkout
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: DONE (the Agility shortcuts built, measured and validated on the server)
- Commit: the earlier work (Barbarian Fishing) is main repo `9dd85c1` (branch `sim-v0`), pushed; this turn's
  shortcuts are the main repo commit after `1c8f05e`, pushed when Caleb asked (the next turn)

## Full Prompt

> Commit and push the changes, then continue with implementation.

## Response Summary

- **Committed and pushed:** `9dd85c1`, Barbarian Fishing (this session's files and hunks only).
- **Built: the Agility shortcuts in travel** (OQ-16 (a)). Seven of the server's shortcuts are transports of kind
  "shortcut", each both ways, taken from their Agility levels: Falador's west wall (5), the lumberyard's fence (13),
  the coal trucks' log balance (20), the River Lum's stepping stone (31), Ardougne's log balance (33), the Al Kharid
  pit (38) and Rellekka's log balance (48).
  - **Chosen** as the ones whose two ends the planner joins only by a long walk round (56 to 242 steps, against 2 to 7
    across), in places the sim travels.
- **Measured** on the server (`scripts/measure_shortcuts.py`): 4 to 7 ticks a crossing, and 13 for the stepping stone.
  Only the log balances give XP.
  - **Found and fixed:** the stepping stone jumps a tile every 2 ticks and stands idle between jumps. The runner's
    first rule, idle within a tile of the end, timed it at 3 ticks. It now waits for the end tile itself.
- **The server backend:** the bridge's `travel.perform` takes a shortcut as a player does. Before, it raised on any
  kind it didn't know, so a server trip over a shortcut would have failed.
- **Fitted:** a shortcut costs a trip 3 ticks beyond its own (`TRIP_TICKS`): the approach and the click, and the walk
  on's start. Fitted on 7 trips, one over each shortcut; before the fit, sim over server was 0.79 to 0.94.
- **Validated** on the server: the fit set 0.90 to 1.03, and the check set (each shortcut the other way) 0.90 to 1.00.
  7 of 7 within ±20% in each.
- **Env contract v1.32, to confirm:** travel gains the shortcuts; no actions or features change.
- **Speed:** about 7% slower over 450 seeded decisions, mostly one-time searches from the shortcuts' ends.

## Documentation Changes

- `docs/decision-log.md`: "Built and measured (sim v1, Agility in travel): seven shortcuts, taken from their levels on
  both backends".
- `docs/env-contract.md`: v1.32 (to confirm): §7's travel list, §1's Agility line.
- `docs/option-catalog.md`: §4's Agility shortcuts (which seven: Claude's choice, to confirm), §2's Agility paragraph,
  the v1.4 note, the unreachable-places note.
- `docs/sim-v1-skills-draft.md` §3: "Agility in travel" as built. `ROADMAP.md`: the status line.
- This record.

## Code Changes

- `rlscape/gamedata/shortcuts.py` (new): `ShortcutLink`, the 14 one-way `LINKS`, `TRIP_TICKS`.
- `rlscape/gamedata/transports.py`: `_shortcuts()`, in `transports()` after the boats.
- `rlscape/bridge/travel.py`: a `shortcut` case in `perform`: its option on the nearest of its scenery, done when the
  character stands idle on the far end (`_over`).
- `scripts/measure_shortcuts.py` (new); `scripts/validate_travel.py`: the "shortcuts" and "shortcuts_check" trip sets.
- **Tests:**
  - `tests/test_shortcuts.py` (new, 3): each link is its handler's scenery and level; Falador's west wall from
    Agility 5; a log balance's XP on the way.
  - `tests/test_shortcuts_live.py` (new, 2): the trip over Falador's wall on the server in the sim's time; a level
    short, the server keeps the character outside.

## Infrastructure Changes

- Server instance 5 (bridge 43614) for the measurements, the validation and the live tests, stopped after by its PID.

## Decisions

- **User decisions:** OQ-16 (a) (Caleb, 2026-11-08: "Agility shortcuts with Agility").
- **Agent choices (reversible):**
  - which shortcuts: the seven whose walk round is long, in places the sim travels;
  - left out:
    - those into areas the sim doesn't travel (Tirannwn's logs, Karamja's jungle and Shilo, the lighthouse's basalt
      rocks, Trollheim's climbs, which Caleb left out);
    - the dungeons' (the planner has no underground map);
    - the grapples (they need a mithril grapple and a crossbow);
  - a shortcut is a transport the route search treats as a boat (a start and an end), at most one transport a route;
  - `TRIP_TICKS`, one fitted overhead for every shortcut, as the boats' boarding was fitted;
  - the places table left as it is (the speed cost above).

## Validation

- `tests/test_shortcuts.py` and `tests/test_shortcuts_live.py`: 5 passed. With the travel, transport and movement
  tests, 30 passed.
- The server (instance 5, jar fork `4f58237`, 50 ms ticks):
  - the measurement: `results/calibration/shortcuts-20261108-2246-i5.json`;
  - the fit trips: `travel-validation-20261108-2247-i5.json` (before the fit) and `-2249-i5.json` (after);
  - the check trips: `-2248-i5.json`.
- The live tests on instance 5: 65 passed, 2 failed. The two are the other sessions' tests of fork changes not in
  that jar (the Runecrafting session's `shown()` and the Herblore session's OQ-47 (c)).
- The suite without the server (before the fit): 377 passed, 2 failed. Neither failure is from this work:
  - `test_travel_counts_against_a_far_site`: another session's uncommitted `gathering_share`. It fails the same way
    with the shortcuts switched off.
  - `test_the_same_seed_gives_the_same_trajectory_in_another_process`: another session saved `aggression.py` while it
    ran. It passed when rerun.
- The suite without the server after the fit (and after the other session's change to `gathering_share`): 382 passed.

## Follow-Up

- Caleb: env contract v1.32 and which seven shortcuts (to confirm).
- Committed when Caleb asks: only this session's files and hunks, explicit paths.
