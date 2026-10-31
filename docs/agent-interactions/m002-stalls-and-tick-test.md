# Agent Interaction

## Metadata

- Interaction ID: m002-stalls-and-tick-test
- Timestamp CST: 2026-10-30 19:38:23 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (stalls and the Shantay Pass built and tested; tick manipulation tested live, none found; three
  findings raised)
- Commit: fork `7956207` (branch `rl`, with the command renames from `m002-wider-guide`); main repo `6ad245c`,
  with `m002-thieving-targets` (branch `sim-v0`)

## Full Prompt

> 1. Go with B.
> 2. Good recommendation.
> 3. Let's try to test it. The code may have bugs that we can exploit for this limited use. Tick manipulation is an
> understood and normal part of the game.

(Answers to `m002-thieving-targets`' three questions: stall guards (b) run off and come back; model the Shantay Pass
as a toll; test tick manipulation live.)

## Response Summary

- **Stalls:** five Ardougne market stalls, from the server's Stall and StallThiefPulse.
  - A steal takes 3 ticks, gives one reward uniformly, and empties the stall for its restock time.
  - 4 in 15 steals are noticed by a guard within 8 tiles. Then the character takes the guard's escape swings and
    runs off for 20 ticks (an estimate).
  - The spice stall is left out: the server's table lacks it.
- **The Shantay Pass:** going south buys a 5-coin pass. Without the coins the desert is unreachable, and its options
  are masked. That adds desert bandits and Menaphite thugs.
- **The live test:**
  - New bridge commands send inputs on exact ticks, as client packets, and read the skilling clock every tick.
  - It tried burying bones, knife on logs and herb on tar, in several orders and timings, on woodcutting, fishing
    and mining.
  - No method shortened a gap between rolls. Each one either changed nothing or slowed the skill.
- **Three findings:**
  - Mining rolls every 5 ticks on the server; the sim assumes 4.
  - The bridge's direct commands land after the world's pulses. The new `packet` option fixes the timing.
  - The bridge used to close skill dialogues. It now leaves them open.

## Documentation Changes

- `docs/option-catalog.md`:
  - §2: the desert targets and the stalls, the Shantay Pass and stall rules
  - §9: 1,000 actions
- `docs/env-contract.md`: §3's as-built note (1,000 actions, 1,609 features).
- `docs/decision-log.md`: the decisions, the results table and the findings.
- `ROADMAP.md`: the status line.
- This record.

## Code Changes

- **Main repo:**
  - `rlscape/sim/movement.py`: the Shantay Pass (`in_desert`, `route`, `reachable`; `route_ticks` is infinite when
    the walk can't be made)
  - `rlscape/sim/thieving.py`: the two desert targets; `StealFromStall`, `STALLS`, `stall_options`
  - `rlscape/sim/slots.py`: a fight slot needs its site reachable
  - `rlscape/sim/__init__.py`: the stalls in the catalog
  - `rlscape/gamedata/server.py`: `stalls()`
  - `rlscape/bridge/client.py`: `item_option`, `use_item`, `dialogue_button`, `schedule`, `debug_set_levels`,
    `debug_complete_quest`, `debug_clocks`
  - `scripts/tick_manipulation_test.py` (new): the live experiment
  - Tests:
    - `tests/test_sim_movement.py`: the desert, the pass, unreachability, the pass before the Al Kharid toll, the
      desert targets
    - `tests/test_sim_thieving.py`: stall parsing, sites, restock timing, uniform rewards, the notice rate, eating
      before a guard's swings
    - `tests/test_bridge_inputs_live.py` (new): the input commands live, direct and as packets
    - `tests/test_vocabulary.py`: counts
- **Fork** (`Server/src/main/content/rl/`):
  - `RLCommands.kt`:
    - the commands above, the `packet` option, and `schedule`
    - `interact` follows the client's click path
    - skill dialogues stay open
  - `RLBridge.kt`: runs the schedules each tick

## Infrastructure Changes

None. The server was built and run locally for the live test, then stopped.

## Decisions

- **User decisions:**
  - stall guards: run off and come back
  - the Shantay Pass as a toll
  - test tick manipulation live
- **Agent choices (reversible):**
  - FLEE_TICKS = 20, and ESCAPE_ATTACKS reused for the guard
  - stall tiles at the merchants' spawns
  - eating before a steal at the guard's worst escape
  - the pass bought on the way rather than held
  - the test's design (packet inputs, clock readings, the trial list)
  - leaving skill dialogues open in the bridge
- **Awaiting Caleb:**
  - mining's interval (5 recommended)
  - the ServerEnv executor using the packet form (recommended)

## Validation

- `uv run pytest -q` with the server running: 218 passed, 0 skipped (all live tests ran).
- The live experiment's results are in `results/live/tick-manipulation-20261030-2023.json` and the decision-log
  table.
- Problems found along the way:
  - The first runs misread events. A bury's clock change (in the pulses) looks like a chop from the tick before.
    Raw per-tick readings showed this, and the analysis now separates them with the bone and shaft counts.
  - The skill-dialogue button was off by one (DialogueInterpreter passes button − 1).
  - Herb on tar never ran, because the bridge closed its dialogue. Direct probes isolated each.

## Follow-Up

- Caleb's call on mining's 5-tick interval.
- The wider guide (thieving included), skilling slots, then the prayer-flicking live test, which needs a
  prayer-toggle command.
- Commit when Caleb asks: main repo and fork.
