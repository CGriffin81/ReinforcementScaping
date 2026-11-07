# Agent Interaction

## Metadata

- Interaction ID: m002-shield-and-vocabulary
- Timestamp CST: 2026-11-06 17:55:19 CST (from the session transcript's queue timestamp, UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: DONE for the shield, the vocabulary, the hazards and the gate's speed check (passes); the drop tables'
  sub-tables ported; the drop probe built and IN PROGRESS on the server (results to follow)
- Commit: fork `d0a7af6` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA
  can only be filled in by a later commit)

## Full Prompt

> Allow the anti-dragon shield to be purchased from the ge now. Rerun both drafts with every quest complete so that we can add the appropriate items to the vocabulary. Only the eastern pair of black knights should be treated as hazards, rather than fightable enemies. Continue with implementation.

## Response Summary

- The GE sells the anti-dragon shield: the fork's `rl.conf` blocks nothing, and the price tables are rebuilt (the
  shield at its 2009 price, 301 gp, in `prices_v2` and the frozen GE; nothing else changed). A buy action for it.
- Found that a bought shield would never have been worn: fights wear the shield with the most defence. Now a fight
  against a dragonfire monster puts a carried one on, the ranking rates those monsters for the character wearing
  it, and deposits and the gear withdrawals keep it with the fighting kit.
- Redrafted *V* with every quest complete (and the shield against dragonfire): 16 items added, 192 in all. The buy
  list is the curated groups of Caleb's buying decisions, not a script: rerun by hand, it gains only the shield.
- Recorded the hazards' scope as Caleb confirmed it (only the eastern pair).
- Continued with the gate's speed check (OQ-21 (a)): a comparison script and the runs. It passes: 18 of 18 cases
  agree at 50 and 600 ms.
- Continued with OQ-20 (a): a drop probe (`scripts/probe_drops.py`), with a key for each ground item (fork). Found
  and ported the drop tables' shared sub-tables (rare drop table, gems, herbs, seeds), which the sim had left out.

## Documentation Changes

- `docs/decision-log.md`: OQ-22 and OQ-23 answered; the shield in fights; the redraft's result; the hazards.
- `docs/open-questions-log.md`: OQ-22 and OQ-23 removed (answered).
- `docs/option-catalog.md` v1.3: §4.B (the shield worn against dragonfire), §8 (the buy), §9 (the redraft, sizes),
  §10 (the shield on the GE), §4.C (the hazards' scope).
- `docs/env-contract.md` v1.13: decisions 29 and 30; §3's sizes. `CLAUDE.md`, `ROADMAP.md`. This record.

## Code Changes

- `rlscape/combat/candidates.py`: `special_damage_shields`; `evaluate`'s `shield_id`; `select_candidates`'s
  `dragonfire` fighters. `rlscape/combat/ranking.py`: the same (`_shielded_rates`), still equal to the reference.
- `rlscape/sim/equipment.py`: `wield_best`'s `protect`. `rlscape/sim/combat.py`: a fight passes it.
  `rlscape/sim/slots.py`: the shielded fighters (`_armed`). `rlscape/sim/kits.py`, `rlscape/sim/buying.py`: the
  kit, the withdrawal, `buy_ge_1540`.
- `scripts/draft_vocabulary.py`: every quest at every band; the shielded fighters; a stale unpacking fixed.
  `data/vocabulary_draft.csv` regenerated; `data/vocabulary.csv` +16; `rlscape/vocabulary.py`'s docstring.
- `data/prices_v2.csv`, `data/grandexchange_2009_frozen.db` and the `.meta.json` files rebuilt.
- `rlscape/bridge/client.py`: `CALIBRATION_TICK_MS`, `speed_suffix` (a results file's name says its tick when it
  isn't 50 ms), used by `scripts/calibrate.py`, `scripts/calibrate_combat.py`, `scripts/validate_travel.py`.
  `scripts/speed_check.py` (new): compares a 50 ms and a 600 ms results file case by case.
- `scripts/probe_drops.py` (new). `rlscape/gamedata/server.py`: `sub_tables`, `DropEntry.expected`,
  `DropTable.expected_items` with them. `rlscape/sim/combat.py`: `roll_drops` rolls them.
- Tests: `tests/test_sim_combat.py` (the sub-tables' rates), `tests/test_access.py` (men outrank cows for gp now),
  `tests/test_bridge_inputs_live.py` (a ground item keeps its key).
- Tests: `tests/test_sim_dragonfire.py` (new); `tests/test_human_player_live.py` (the shield bought on the GE);
  `tests/test_sim_economy.py`, `tests/test_vocabulary.py`, `tests/test_sim_buying.py` (sizes and the shield's price).

## Infrastructure Changes

- Fork (`server/`, uncommitted): `worldprops/rl.conf`, `ge_blocked_items = ""`; `RLCommands.kt`, a key on each
  ground item. Rebuilt; the rebuilt frozen GE installed; the server ran for the tests, the speed check and the probe.

## Decisions

- **User decisions:** the shield on the GE (not one of OQ-22's options); OQ-23 (a), adding the proposed items; the
  hazards' scope, the eastern pair only.
- **Agent choices (reversible):**
  - fights put a carried anti-dragon shield on only against dragonfire monsters; the kit keeps it, and the gear
    withdrawal takes one out when none is carried (one slot carried, not behind a two-handed weapon)
  - dragonfire's damage through the shield isn't modelled (up to 5 a breath)
  - nothing taken out of *V*, though 13 items aren't proposed any more; the mithril 2h sword added, as the rule
    passes a drop that's also smithed
  - the speed check's cases: woodcutting (willows), mining (iron) and fly fishing at band 31; the top melee and
    ranged picks at band 31; the travel check trips; 3 runs of at most 1,000 ticks a case; agreement within two
    standard errors (travel, run once: 5%)
- **Raised for Caleb:** OQ-24, whether the buy list should take any of the newly wearable quest gear (a new buying
  decision; recommendation: no, it's above the groups' tiers or can't be traded).

## Validation

- `uv run pytest -q` with the server up: 314 passed. ruff (pyflakes): passed.
- The price rebuild changed only the shield's two rows and the frozen GE's historical list (+1540, +1541).
- Live: the shield bought on the GE for 301 gp.
- The speed check's comparison script, checked on earlier results files against themselves (all agree, ratio 1).
- The speed check (`results/calibration/speed-check-20261106-1959.json`): 18 of 18 agree; gathering and combat 600
  over 50 ms 0.99 to 1.08, at most 1.7 standard errors; travel 1.00 but a charter's 1.03.
- After the key: 314 passed with the server up. The probe's 20-kill trial: 65 of 66 items fit with the sub-tables
  (the miss, bones, from the kill count; fixed).

## Follow-Up

- The drop probe's results (running); then OQ-19's measurement.
- Poison, ranged damage taken, magic, the willows; thieving and the processing skills.
- Commit when Caleb asks.
