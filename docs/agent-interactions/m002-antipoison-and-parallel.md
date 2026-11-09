# Agent Interaction

## Metadata

- Interaction ID: m002-antipoison-and-parallel
- Timestamp CST: 2026-11-06 22:12:34 CST (first prompt) to 22:27:01 CST (last), three prompts, from the session
  transcript's message timestamps (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (antipoison and the parallel tooling built and tested offline; the bridge's flicking written,
  to build once the running probe frees the servers; the dragon probe to rerun with it)
- Commit: fork `d0a7af6` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA
  can only be filled in by a later commit)

## Full Prompt

2026-11-06 22:12:34 CST:

> Add in anti-poison and super anti-poison potions to counteract poisonous effects. I don't recall if I greenlit it before, but in the interest of saving time, we can absolutely increase the number of concurrent agents training and/or run multiple tests at once, where possible.

2026-11-06 22:25:13 CST:

> Why did the probe character die?

2026-11-06 22:27:01 CST:

> Make sure the dragon fighters have protection from dragon fire and are flicking their prayers.

## Response Summary

- Antipoison and super antipoison, from the server's potions: a dose cures and gives 150 or 600 ticks of immunity;
  fights drink one when poisoned; the ranking counts the cover; the GE sells both; *V* takes the potions, their
  lower doses and the vial (212).
- Tests in parallel (pytest-xdist; live tests kept on one worker: 68 s against 134) and extra server instances
  (`scripts/server_instances.py`; `RL_BRIDGE_PORT`), each with its own world, GE and jar copy.
- The probe's death, traced: in the Wilderness green dragons' single-combat area it kept clicking a dragon other
  than the one attacking it, which the server refused, and with retaliation off and no prayer it was killed. The
  anti-dragon shield worked.
- Fixed: the bridge flicks protection prayers on the server (`flick`), exact to the tick; the probe uses it, wears
  the shield, attacks its attacker, stops on death, and reports and saves as it goes.

## Documentation Changes

- `docs/decision-log.md`: antipoison; parallel tests and servers; the probe's death and the flicking.
- `docs/option-catalog.md`: §4.B poison's row, §8's antipoison buys, §9's sizes. `docs/env-contract.md` v1.14 (to
  confirm): the cover in §8's risk; §3's sizes. `CLAUDE.md`: parallel tests and servers. This record.

## Code Changes

- `rlscape/sim/health.py`: the potions, `drink_antipoison`, `apply_poison`'s immunity, `poison_cover`.
  `rlscape/sim/state.py`: `poison_immune_until`. `rlscape/sim/combat.py`: the fight drinks; death clears immunity.
- `rlscape/combat/rates.py`: `poison_per_kill`, `poison_per_hour`, the filter's cover. `rlscape/combat/candidates.py`,
  `rlscape/combat/ranking.py`: the cover, still matching. `rlscape/sim/slots.py`, `rlscape/envs/encoding.py`: the
  cover in the ranking and the damage feature. `rlscape/sim/kits.py`: the doses kept. `rlscape/sim/buying.py`:
  `ANTIPOISONS`.
- `scripts/draft_vocabulary.py` (what drinking leaves); `data/vocabulary.csv` (+9); `data/vocabulary_draft.csv`.
- `rlscape/bridge/client.py`: `RL_BRIDGE_PORT`, `BASE_PORT`, `run_suffix`, `flick`. `scripts/install_ge_db.py`
  (`--instance`), `scripts/server_instances.py` (new). `scripts/probe_drops.py`: flicking, the attacker, the stops,
  progress and saving.
- `pyproject.toml`, `uv.lock`: pytest-xdist (dev). `tests/conftest.py` (new): live tests on one worker.
- Tests: `tests/test_sim_poison.py` (antipoison), `tests/test_vocabulary.py` and `tests/test_sim_buying.py` (sizes),
  `tests/test_bridge_inputs_live.py` (the bridge's flicking, live).

## Infrastructure Changes

- Fork (`server/`, uncommitted): `RLCommands.kt`: `flick` and `flickPrayers`; attackers' `next_swing`.
  `RLBridge.kt`: calls `flickPrayers` each tick. To build.
- Server instances 2 and 3 (`results/servers/`; GE under `data/eco/instance-<n>`), run for the probe and the trace.

## Decisions

- **User decisions:** antipoison and super antipoison; parallel training and tests where possible; dragon fighters
  wear dragonfire protection and flick.
- **Agent choices (reversible):**
  - drink when poisoned, the super first, the emptiest potion first; one potion a buy
  - *V* takes the lower doses and the vial by the rule (what drinking leaves)
  - flicking scripted on the server, the style from the monster's config, the strongest attacker's
  - calibration keeps Prayer at 1 on both sides (its design); only the probe flicks so far
  - each extra instance runs a copy of the jar

## Validation

- `uv run pytest -q -n 8 --dist loadgroup --ignore-glob="tests/*_live.py"`: 272 passed in 68 s. ruff (pyflakes):
  passed.
- The probe on instance 2: Black Knights, 200 kills, 67 of 68 items within the sim's 99%.
- The trace on instance 3: the death's cause, as above.

## Follow-Up

- Build the fork with flicking; the live suite; the dragon probe with flicking; the ranged reruns with the fixed eat
  count, on separate instances at once.
- Commit when Caleb asks.
