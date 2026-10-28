# Agent Interaction

## Metadata

- Interaction ID: m002-slayer-fix-and-commit
- Timestamp CST: 2026-10-28 ~13:44 CDT (estimated: the first server build in this turn finished at 13:48 local time)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: fork `b7c9d8c` and `d49172e` (branch `rl`); main repo: the commit that adds this record, on branch
  `env-contract-and-combat-model`

## Full Prompt

> Apply the Slayer fix and commit everything.

## Response Summary

- **Reproduced first,** following the project's testing rule:
  - added a `target` field (the current combat victim) to the bridge's `state`, so a test can see whether an attack
    started
  - added the live test `test_slayer_level_blocks_attacks`: a fresh character among the cave crawlers (Slayer 10)
    attacks and should have no target
  - built the fork, reinstalled the frozen GE, started the server: the test failed with `target == 'Cave crawler'`
- **Fixed:** `return false` after the warning in `NPC.isAttackable` and `IdleAbstractNPC.isAttackable` (the only two
  places the message is printed). Rebuilt, restarted, and the test passed.
- **Regression checks:**
  - the full suite with the live server: 39 passed, all 14 live tests included
  - `scripts/gate_check.py`: G1 34.6× at 15 ms per tick; G2 fresh character, 10 logs, 250 Woodcutting XP
  - stopped the server and reinstalled the clean frozen GE
- **Committed and pushed:** the fork (two commits), then this repo (the access table from `m002-access-table`, this
  fix's docs, and the submodule bump) on `env-contract-and-combat-model`.

## Documentation Changes

- `docs/option-catalog.md` §4.C: Slayer levels are now enforced in the fork, with the evidence.
- `docs/decision-log.md`: the decision, the build, the validation.
- `rlscape/gamedata/server.py`: the `slayer_levels` docstring.
- This record, and the `Commit:` field of `m002-access-table`.

## Code Changes

- Fork, branch `rl`:
  - `b7c9d8c`: `content/rl/RLCommands.kt` (`target` in `state`)
  - `d49172e`: `core/game/node/entity/npc/NPC.java` and `IdleAbstractNPC.java` (`return false`)
- Main repo: `tests/test_human_player_live.py` (the new live test); the submodule pointer moves to `d49172e`.

## Infrastructure Changes

- Two fork builds and two server runs with `rl.conf`, each with the frozen GE reinstalled first. The server is
  stopped, and the clean frozen GE is reinstalled.

## Decisions

- **User decision:** apply the Slayer fix in the fork (Claude's recommendation); commit everything.
- **Agent choices:**
  - the reproduction monster: cave crawlers, open-access and outside Morytania, where the server ejects characters
    without Priest in Peril
  - the `target` state field as the observable
  - two fork commits, split by purpose

## Validation

- Before the fix: `test_slayer_level_blocks_attacks` failed (`'Cave crawler'`). After: it passed.
- `uv run pytest -q` with the server up: 39 passed.
- `scripts/gate_check.py`: G1 and G2 as above (results in `results/gates/gate_check_20261028_135203.json`, which is
  git-ignored).

## Follow-Up

- Ambient bots with low Slayer levels can no longer fight Slayer monsters. Expected and authentic, but worth knowing if
  a bundled bot script (e.g. `GenericSlayerBot`) is used for calibration.
