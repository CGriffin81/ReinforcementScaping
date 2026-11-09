# Agent Interaction

## Metadata

- Interaction ID: m002-dev-mode-and-pickups
- Timestamp CST: 2026-11-07 03:11:59 CST (first prompt) to 03:13:03 CST (last), two prompts, from the session
  transcript's message timestamps (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (built; tested offline and live; two items raised for Caleb)
- Commit: fork `d0a7af6` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA
  can only be filled in by a later commit)

## Full Prompt

2026-11-07 03:11:59 CST:

> Continue.

2026-11-07 03:13:03 CST (sent while Claude was working):

> Turn the server's dev mode off.

## Response Summary

- Dev mode off (OQ-26 (a)): `dev = false` in the fork's `rl.conf`, the instance configs regenerated, both servers
  restarted (`devMode=false`). The live tests: 49 passed.
- The bank test waits for the bank to open instead of expecting it on a fixed tick (it failed twice under the full
  suite's load, the bank a tick late).
- The combat timing refitted with the combat inventory: the overhead between kills 3 ticks (from 10 and 8), and a
  new pickup time a looted drop, 3 ticks melee, 10 ranged, in the sim's fights and the rates (the fast ranker still
  equals the reference). XP/hr within ±20% in all 24 cases (0.90 to 1.19).
- Still outside: the time to a full inventory at Edgeville's chaos druids (0.72), where the server's runner leaves
  drops while attacked.

## Documentation Changes

- `docs/decision-log.md`: OQ-26 answered and built; the refit and the pickup time; the bank test.
  `docs/open-questions-log.md`: OQ-26 removed. `docs/env-contract.md` v1.15 (to confirm): §8's overhead and pickup
  time. `CLAUDE.md`: `rl.conf` has dev mode off. `ROADMAP.md`. This record; `m002-potion-doses-and-moss-giants`
  points here.

## Code Changes

- `rlscape/combat/rates.py`: `OVERHEAD_TICKS_PER_KILL` 3; `PICKUP_TICKS`, `with_pickups`.
- `rlscape/gamedata/server.py`: `DropEntry.expected` and `DropTable.expected_items` take `stacks`.
- `rlscape/combat/candidates.py`: `pickups_per_kill`; `evaluate` times the pickups in.
- `rlscape/combat/ranking.py`: the same on the ranker's arrays; `_candidate` applies `with_pickups`.
- `rlscape/sim/combat.py`: a fight charges each drop it picks up.
- Tests: `tests/test_sim_combat.py` (the pickup time; the site-capacity test at the sim's own kill time),
  `tests/test_candidates.py` (`pickups_per_kill`), `tests/test_bridge_inputs_live.py` (the bank test).

## Infrastructure Changes

- Fork (`server/`, uncommitted): `worldprops/rl.conf` `dev = false`.
- `results/servers/rl-2.conf`, `rl-3.conf` regenerated; the GE databases of instances 1 to 3 reinstalled (the old
  ones kept as `.bak`). Instances 1 and 2 restarted from `server/Server`.

## Decisions

- **User decisions:** dev mode off.
- **Agent choices (reversible):**
  - `debug = true` left on (it gates only the admin commands)
  - the overhead fitted jointly on 16 no-loot cases; the pickup time fitted on the 8 loot cases at that overhead;
    magic's overhead as ranged's, its pickup as melee's (uncalibrated)
  - the danger filter's per-kill damage left as the fight's (a pickup's poison left out)
- **Raised for Caleb:** the calibration runner's looting rule (it loots only while nothing attacks it, so at
  aggressive monsters it leaves drops the sim picks up): (a) loot between kills while attacked too, as the sim does,
  and rerun the loot set (recommended); (b) keep it and note the druids' 0.72 as the runner's; (c) make the sim skip
  loot while attacked. The rate model's time to kill leaves out the last hit's overkill, which matters more at the
  smaller overhead for monsters killed in a swing or two.

## Validation

- `uv run pytest -q -n 8 --ignore-glob="tests/*_live.py"`: 280 passed in 65 s. ruff (pyflakes): passed.
- The live tests on instance 2 with dev mode off: 49 passed in 219 s.
- The resimulated calibration sets (`results/calibration/combat-20261107-0001-resim.json`, `-0049-resim.json`,
  `-0035-valuable-resim.json`), as above.

## Follow-Up

- Both answered (the looting rule, the overkill): `m002-looting-and-scenery`.
- Commit when Caleb asks.
