# Agent Interaction

## Metadata

- Interaction ID: m002-device-rules
- Timestamp CST: 2026-11-07 09:28:02 CST, from the session transcript's message timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (OQ-28 answered and built in the fork and the sim, tested offline and live; the interference rule
  raised as OQ-29)
- Commit: fork `5e531bb` (branch `rl`) and the main repo commit after `bc7bfec` that adds this record (branch
  `sim-v0`), both pushed 2026-11-07 with `m002-pull-request`

## Full Prompt

> Avas devices attraction effects do not work if any metal items are equipped. That needs to be understood when
> modeling the behavior.
> OQ28 - Wear the devices only in ranged combat. Have the item collection turned off. Most of those items are not as
> valuable as the space they would otherwise take. Modeling drop behavior because of the junk items isn't worth the
> time or additional complexity.
> 2, option i
> 3, Implement a level 50 ranged skill requirement for the accumulator, no requirement for the attractor.
>
> 4. a

## Response Summary

- **OQ-28, answered and built:**
  - Devices are worn in ranged fights only, with their attraction off.
  - The accumulator gathers back the shots its catch misses that would land, reading (i).
  - The accumulator needs 50 Ranged to wear; the attractor needs nothing.
  - The observation gets a cape role.
- **The fork:**
  - `RangeSwingHandler.useAmmo`: the accumulator's gather.
  - `item_configs.json`: the accumulator's Ranged 50.
  - `RLCommands`: `spawn` switches attraction off, and `item_definitions` exports each item's worn model.
- **The sim:**
  - `equipment.shot_outcomes`, ported from the server, feeds both the fights and the ranking.
  - Ranged fights wear the best device carried; other fights take it off.
  - The ranged gear withdrawal brings the device out first.
  - The encoder has a cape role.
- **Caleb's note on metal:** the server's rule is narrower than "any metal item".
  - Only the chest piece counts, and only one whose worn model is one of three. That's 38 pieces, without the iron
    chainbody, the Saradomin platebody or the dragon chainbody.
  - Interference stops only the 80% catch.
  - The server's rule is what's built now, with a ranger leaving interfering chests off. The choice is raised as
    OQ-29.

## Documentation Changes

- `docs/decision-log.md`: OQ-28's answers, what was built, what was measured.
- `docs/open-questions-log.md`: OQ-28 removed; OQ-29 added (which armour stops a device).
- `docs/env-contract.md` v1.16 (to confirm): the cape role, E 12, and 2,119 features.
- `docs/option-catalog.md`: what a device does.
- `CLAUDE.md`: the fork's device rules.
- This record. `m002-devices-on-the-ge`'s follow-up points here.

## Code Changes

- `rlscape/sim/equipment.py`:
  - the devices' constants, `land_chance` and `shot_outcomes`
  - `hinders` covers the devices
  - `leaves_off` and `best_device`
  - `wield_best` wears the best device in a ranged fight
- `rlscape/sim/combat.py`: `_ammunition` uses `shot_outcomes`, and `arrow_land_chance` is now `land_chance`'s.
- `rlscape/sim/slots.py`: `_attacks_held` uses `shot_outcomes`.
- `rlscape/sim/buying.py`: the devices come from `equipment`, and `gear_to_withdraw` handles them.
- `rlscape/envs/encoding.py`: the cape role.
- `rlscape/gamedata/server.py`: `ava_interfering_items`.
- `tests/conftest.py`: the live tests' xdist group now takes effect (`tryfirst`); it never had.
- `scripts/export_ava_interference.py` (new) writes `data/ava_interference.csv` (new).
- Tests:
  - `tests/test_sim_avas_devices.py` (new)
  - `tests/test_sim_buying.py`: the accumulator's Ranged 50
  - `tests/test_vocabulary.py`: 2,119 features
  - `tests/test_human_player_live.py`: the Ranged 50 and the attraction

## Infrastructure Changes

- Fork (`server/`, uncommitted): `RangeSwingHandler.kt`, `RLCommands.kt`, `data/configs/item_configs.json`. Built;
  instance 1 runs it, and instances 2 and 3's jar copies (`results/servers/`) were refreshed to it.

## Decisions

- **User decisions:** OQ-28:
  - 1 (c): ranged fights only, attraction off
  - 2 (i)
  - 3 (a): Ranged 50 for the accumulator, none for the attractor
  - 4 (a): the cape role
- **Agent choices (reversible):**
  - the interference rule built as the server has it, chest models only, stopping only the catch
  - a ranger wearing a device leaves interfering chest armour off
  - a ranged fight prefers a device over any other cape
  - attraction switched off at spawn, rather than by the ServerEnv operating each device
  - the interfering pieces exported to their own file, rather than as a column of `item_definitions.csv`, whose
    informational GE-price column a re-export would rewrite
- **Raised for Caleb:** OQ-29.

## Validation

- `uv run pytest -q -n 8 --ignore-glob="tests/*_live.py"`: 295 passed. ruff (pyflakes): passed.
- `uv run pytest -n 8 --dist loadgroup tests/` with instance 1 up: 348 passed in 244 s, every live test on
  one worker. Before the conftest fix, the same run hung.
- Live, on instance 1 with the new build:
  - the accumulator refused at Ranged 1 ("You need a Ranged level of 50 to wear this.") and worn at 50
  - the attractor worn for 305 ticks attracted nothing
  - shooting cows at Ranged 50, arrows that landed out of those used:
    - no device: 58 of 70 (0.83; the formula's 0.86)
    - attractor: 13 of 20 (0.65; the formula's 0.5)
    - accumulator: 0 of 6
- `scripts/export_ava_interference.py`: 38 chest pieces.

## Follow-Up

- OQ-29 (Caleb): answered (a) in `m002-oq29`.
- Build OQ-27 (d).
- Commit when Caleb asks.
