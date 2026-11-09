# Agent Interaction

## Metadata

- Interaction ID: m002-agility
- Timestamp CST: 2026-11-08 19:59:53 CST, from the session transcript's message timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab), a session working beside the Herblore and Runecrafting sessions in the
  same checkout
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: DONE for the courses (Agility's laps built, measured and gated); Barbarian Fishing and the shortcuts not
  started
- Commit: uncommitted

## Full Prompt

> Work on agility.

## Response Summary

- **Built: the agility courses** (sim v1, OQ-2 Choice D: the Gnome Stronghold, the Barbarian Outpost, the Wilderness):
  the courses from the server's handlers (`rlscape/gamedata/agility.py`), the laps in the sim (`rlscape/sim/agility.py`,
  `agility_<course>`), Agility's 4 skilling slots and task, and a measurement of the courses on the server
  (`scripts/measure_agility.py`).
- **Found on the server:**
  - a rope swing's fail does nothing (`AgilityHandler.fail` plays out only with an animation, and the swings pass
    none);
  - the Barbarian ledge's falls land west of the net, which can't be climbed from there, so the lap goes on at the
    walls, without the bonus;
  - the Barbarian pipe gives no XP (`AgilityShortcut` never awards it);
  - the Wilderness pipe needs Agility 49;
  - the Barbarian course's three walls share an id, so the bridge's `interact` takes a tile now (`at`, a fork change).
- **The gate:** sim over server XP/hr 1.00 on the Gnome course and the fall-free runs, 1.03 on 40 Barbarian laps at
  Agility 35; the Wilderness at 52, see Validation.
- **Coordination:** instance 5 (bridge 43614); shared files edited after telling the Runecrafting session; env contract
  v1.28 taken.

## Documentation Changes

- `docs/decision-log.md`: "Built and measured (sim v1, Agility): the three courses' laps, Agility's slots".
- `docs/open-questions-log.md`: OQ-46.
- `docs/env-contract.md`: v1.28, to confirm (Agility's 4 slots and task; 2,161 actions, 3,299 features).
- `docs/option-catalog.md`: §2's Agility paragraph; the v1.4 note.
- `docs/sim-v1-skills-draft.md` §3: Agility as built. `ROADMAP.md`: the status line.
- This record.

## Code Changes

- `rlscape/gamedata/agility.py` (new): the courses, `fail_chance`, `fall_hit`.
- `rlscape/sim/agility.py` (new): `AgilityLaps` (the laps, eating as thieving does, the expected rate), the measured
  `TIMES`.
- `rlscape/sim/skilling.py`, `rlscape/envs/encoding.py`, `rlscape/sim/kits.py`: Agility's slots, task and kit.
- `rlscape/bridge/client.py`: `interact`'s `at`.
- **Fork** `Server/src/main/content/rl/RLCommands.kt`: `candidates` takes an optional tile (`at`).
- `scripts/measure_agility.py` (new): laps, falls and entries on the server, and the gate's comparison.
- **Tests:** `tests/test_sim_agility.py` (new: the fall chance against the server's two draws, the courses against their
  handlers, the Gnome laps, the lap loop against the expected rate); counts in `test_sim_skilling`,
  `test_sim_gathering`, `test_vocabulary`.

## Infrastructure Changes

- The fork rebuilt in the main checkout (the `at` filter) and its jar given to instance 5 (`results/servers/server-5.jar`),
  run on bridge port 43614; restarted twice to clear stuck characters, by its PID. `scripts/server_instances.py 7` was
  run before Herblore claimed instance 7 (told; no server ran there).

## Decisions

- **User decisions:** none new (this builds OQ-2's Choice D).
- **Agent choices (reversible):**
  - eating by thieving's rule (the retreat point, or the largest fall hit if higher), not the fights';
  - the measurement's calibration setup: a character teleported onto the course, hitpoints reset to 99 between laps,
    low Agility (15) to sample the Barbarian falls;
  - the Wilderness ridge's fall time (about 40 ticks) from one run, to measure again;
  - the gate compared over whole laps against the expected lap at the run's middle level.

## Validation

- The gate, sim over server XP/hr over whole laps: Gnome Stronghold 1.00; Barbarian Outpost 1.00 at Agility 75, 1.03
  over 39 laps at 35; Wilderness 1.00 at 99, 0.86 over 45 laps at 52 (fewer stepping-stone falls on the server than the
  formula gives, 1.5 standard errors).
- The full suite on instance 5 (`RL_BRIDGE_PORT=43614`, `-n 8 --dist loadgroup`): 434 passed.
- Speed: 81 decisions a second in one process (96 after Crafting, before the other sessions' Herblore and
  Runecrafting and this one's Agility).

## Follow-Up

- Caleb: env contract v1.28 (to confirm); OQ-46 (the Wilderness spike pit's skeletons).
- Next: Barbarian Fishing (`barb_fish`, the rod's buy action), the Agility shortcuts in travel.
- Commit when Caleb asks: the fork first (only this session's hunk of `RLCommands.kt`), then the submodule pointer;
  explicit paths.
