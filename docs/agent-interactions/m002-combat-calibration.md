# Agent Interaction

## Metadata

- Interaction ID: m002-combat-calibration
- Timestamp CST: 2026-11-05 17:53:32 CST (from the session transcript's message timestamp, UTC−06:00): Caleb's
  answer to the feasibility review, which set this work going
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (melee and ranged XP/hr calibrated without looting; poison, ranged damage taken, one Black Knight
  site, looting and magic still open)
- Commit: fork `d0a7af6` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA
  can only be filled in by a later commit)

## Full Prompt

> Let's continue with the current plan for now and reevaluate on Sunday. I'm hoping that the calibration section is just an unusually heavy lift for the project and we're almost done with it.

(Also recorded in `m000-feasibility-review`, for the scope decision it deferred.)

## Response Summary

- Audited the calibration still to do (combat, thieving, processing, the GE and shops) and started with combat.
- Wrote the combat calibration runner and ran it on the server: the ranker's own picks at four bands, melee and
  ranged, fit and check sets.
- Found and fixed two server-side problems: the bridge clicked dead monsters, and "in combat" counted wall-clock time
  (on the sped-up server, single-combat lockouts lasted twelve times too long).
- Found what the sim lacked (respawn waits where a site is short of monsters), added site capacity to the rates and
  the sim's fights, and fitted the per-kill overhead per class.
- Reran the gathering cases with aggressive monsters after the fix; the willows need their exposure re-measured.

## Documentation Changes

- `docs/decision-log.md`: "combat calibrated (melee and ranged, without looting)".
- `docs/open-questions-log.md`: OQ-18 (a pickup command).
- `docs/env-contract.md`: v1.11, the combat-rate model's measured overhead and respawn waits (§8). To confirm.
- `docs/option-catalog.md`: the rates' time between kills. `CLAUDE.md`: "in combat" in game ticks among the fork's
  rule changes. `ROADMAP.md`: status. This record.

## Code Changes

- `scripts/calibrate_combat.py` (new): the runner (`--slot`, `--cases-from`, `--resim`).
- `rlscape/gamedata/server.py`: NPCs' respawn delays. `rlscape/combat/candidates.py`: each site's spawns within
  15 tiles; the reference ranking with site capacity; rates compared rounded as before.
- `rlscape/combat/rates.py`: `site_slowdown`; the per-kill overhead per class (`OVERHEAD_TICKS_PER_KILL`).
- `rlscape/combat/ranking.py`: site capacity, as the reference. `rlscape/sim/combat.py`: each site monster's respawn.
- Tests: `tests/test_sim_combat.py` (site capacity; the overhead constant), `tests/test_combat_formulas.py`,
  `tests/test_sim_slots.py` (the magic character's dagger).

## Infrastructure Changes

- Fork (`server/`, uncommitted): `RLCommands.kt` (`interact` skips hidden and dead NPCs); `Entity.java`,
  `CombatPulse.kt`, `MapZone.java`, `IdleAbstractNPC.java` ("combat-time" in game ticks, `COMBAT_TIME_TICKS = 17`;
  a rule-timing change to approve). Built; the server ran for the calibration and the tests, stopped at the end.

## Decisions

- **User decisions:** continue the current plan until Sunday (OQ-17 deferred).
- **Agent choices (reversible):**
  - combat first among the remaining calibration
  - the calibration character: band levels, standard gear given, Prayer 1, the accurate style, drops left
  - site capacity: spawns of the same NPC within 15 tiles, its respawn delay; in the sim, a respawn per monster
  - the overhead per class (melee 10, ranged 8; magic as ranged, uncalibrated), fitted on the fit set only
  - the runner clicks again only after 3 idle ticks (a person waits for the walk to start)
- **Raised for Caleb:** the "in combat" fork change; env contract v1.11; OQ-18.

## Validation

- `scripts/calibrate_combat.py`: fit set 0.88 to 1.13 (8 of 8 within ±20%); not fitted on, 8 of 9 within (ranged
  at poison spiders 1.22); the four Black Knight cases got nothing on the server.
- The same fight at 600 ms and 50 ms ticks after the fix: 13,671 and 13,352 XP/hr.
- `uv run pytest -q` with the server up: 301 passed. ruff (pyflakes): passed.

## Follow-Up

- Poison; ranged damage taken; the Taverley dungeon Black Knights; the willows' exposure; magic; looting (OQ-18).
- Then thieving, the processing skills, the GE and shops.
- Commit when Caleb asks.
