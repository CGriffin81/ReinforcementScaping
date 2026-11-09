# Agent Interaction

## Metadata

- Interaction ID: m002-looting-and-scenery
- Timestamp CST: 2026-11-07 03:34:21 CST (first prompt) to 03:56:07 CST (last), four prompts, from the session
  transcript's message timestamps (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS for these prompts (built and tested; processing and the thieving check set calibrated; OQ-27 raised)
- Commit: fork `d0a7af6` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA
  can only be filled in by a later commit)

## Full Prompt

2026-11-07 03:34:21 CST:

> Go with option a for the looting rule

2026-11-07 03:35:57 CST (sent while Claude was working):

> Fix the overkill in the rate model's kill time too

2026-11-07 03:44:38 CST:

> Continue with implementation while the loot rerun finishes

2026-11-07 03:56:07 CST (sent while Claude was working):

> Make the changes required for using inventory items on scenery.

## Response Summary

- The calibration runner loots between kills, attacked or not (option a). Rerun: the time to a full inventory within
  ±20% everywhere (the chaos druids 0.98, from 0.72); the pickup time refitted (5 ticks melee, 18 ranged). Two
  ranged cases stay outside on XP/hr (Black Knights 1.21, band-1 women 1.27): arrow piles, OQ-27.
- The rate model's time to kill counts the last hit's overkill: the expected swings to a kill, exact (a hit's renewal
  function, cached per max hit), matching the sim's kill sequences within 0.8% (the old formula was 5 to 77% short).
- The drop probe's one-pile miss fixed (a 31-tick wait for the last drop; no attack after the count).
- `use_item_on`, a bridge command for an item used on scenery (the client's UseWithScenery packet), and the bridge
  leaves the furnace's, the range's and the anvil's interfaces open. Found on the way: the Edgeville furnace needs
  the Varrock Diary (now `never` in the sim's stations).
- A processing calibration runner (`scripts/calibrate_processing.py`): burying, firemaking, smelting, smithing and
  cooking, the activity alone, 34 cases. Every case within ±20% after four sim fixes, each measured on the server:
  burying 3 ticks a bone (it had 2; the same at 600 ms); smithing's "Make All" holds its item, and the next item costs
  9 ticks; firemaking's blocked step aside (4% of logs, a step off); iron's coin flip confirmed over 8 runs.
- The thieving check set: farmers, warriors, guards, knights, paladins and heroes all within ±20% on XP/hr (0.91 to
  1.14); heroes' gp/hr 0.75, a rare-item table 3 runs can't settle.

## Documentation Changes

- `docs/decision-log.md`: the looting rule, the overkill, the probe fix, `use_item_on`, the Edgeville furnace.
  `docs/open-questions-log.md`: OQ-27 (ranged's arrow pickups). `docs/env-contract.md` v1.15 (to confirm): §8's kill
  time; §7's item-on-scenery input. This record.

## Code Changes

- `rlscape/combat/rates.py`: `swings_to_kill`, `landed_hits_to_kill`; `PICKUP_TICKS` refitted.
- `rlscape/sim/processing.py`: `BURY_TICKS` 3; `SMITH_NEXT_ITEM_TICKS`, smithing holds its item through a batch;
  `FIRE_BLOCKED_CHANCE`, `FIRE_STEP_OFF_TICKS`. `data/stations.csv`: the Edgeville furnace `never`.
- `rlscape/bridge/client.py`: `use_item_on`.
- `scripts/calibrate_combat.py` (loot first), `scripts/probe_drops.py` (the wait, the last attack),
  `scripts/calibrate_thieving.py` (results named by target and band), `scripts/calibrate_processing.py` (new).
- Tests: `tests/test_combat_formulas.py` (the kill time against the sim's kill sequences), `tests/test_sim_combat.py`
  (the site-capacity test at the model's kill time again), `tests/test_bridge_inputs_live.py` (item on scenery),
  `tests/test_guide.py` (Prayer's expectation, with burying's measured pace).

## Infrastructure Changes

- Fork (`server/`, uncommitted): `RLCommands.kt` `use_item_on` and `reachBeside`; `dismissDialogues` leaves chatboxes
  311 and 307 and interface 300 open. Built; instance 1 on it. Instances 2 and 3 run the older jar copies (instance 3
  started for the 600 ms check).

## Decisions

- **User decisions:** option (a) for the looting rule; the overkill fixed; the changes for items on scenery.
- **Agent choices (reversible):**
  - the pickup time refitted on the new loot runs; magic as melee
  - the kill time's flicked and plain swings mixed at random (the sim keeps their pattern; 0.5 to 0.8% apart)
  - `use_item_on` prefers interact's paths, and takes a "move near" one only if it ends beside an edge
  - the Edgeville furnace marked `never` (the server refuses it without the Varrock Diary)
  - burying set to the measured 3 ticks a bone; smithing's next-item cost and firemaking's step-offs as measured
  - the processing runner's rules (a click when idle, an interface's button once open, the end at the last XP gain,
    a fresh fire row a run in the fields, a step off a fire it's left on)
- **Raised for Caleb:** OQ-27.

## Validation

- `uv run pytest -q -n 6 --ignore-glob="tests/*_live.py"`: 286 passed. ruff (pyflakes): passed.
- Live (instance 1, the new build): the three item-on-scenery tests passed.
- The kill time against 20,000 sampled kill sequences a case; the probe's cows and dragons; the resimulated loot set.

## Follow-Up

- OQ-27; an item-by-item check of the heroes' pickpocket table; magic, the GE and shops, and Fletching's own paths
  still to calibrate.
- Commit when Caleb asks.
