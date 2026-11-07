# Agent Interaction

## Metadata

- Interaction ID: m002-poison
- Timestamp CST: 2026-11-06 21:03:08 CST (from the session transcript's message timestamp, UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: DONE for poison and the eat-count fix (built, tested without the live suite while the drop probe holds
  the server); the drop probe's results to follow
- Commit: fork `d0a7af6` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA
  can only be filled in by a later commit)

## Full Prompt

> Continue with implementation

## Response Summary

- Ported poison from the server: a poisonous monster's swings poison 4 times in 10, hit or miss, so a protection
  prayer doesn't stop it, and poison hits every 30 ticks for floor((severity + 4) / 5), weakening by 1 a hit. In
  fights (per swing), after them (wherever time passes), and in the rate model's damage.
- Resimulated the poison spider cases: the sim now runs out of food when the server did (963 and 726 ticks against
  891 to 1,049 and 697 to 735); before, it never did.
- Found that both calibration runners counted eat clicks as food eaten (a bite lands a tick after its click), which
  overstated the server's food/hr up to twice. Fixed. Counted as food, the spider runs ate about 95 an hour against
  the sim's 93 and 124; last night's "ranged fighters take more damage" may be the same artifact (to rerun).

## Documentation Changes

- `docs/decision-log.md`: poison; the eat count. `docs/option-catalog.md` §4.B (poison's row).
  `docs/env-contract.md` v1.14 (to confirm): poison in §8's risk. This record.

## Code Changes

- `rlscape/gamedata/server.py`: `Npc.poison_amount`. `rlscape/combat/rates.py`: `POISON_TICKS`, `POISON_CHANCE`,
  `poison_damage`, `poison_per_tick`, in the damage per kill and per hour.
- `rlscape/sim/state.py`: `poison_severity`, `poison_clock`. `rlscape/sim/health.py`: `apply_poison`,
  `advance_poison`, `regenerate` advancing it. `rlscape/sim/combat.py`: the fight's per-swing poison and death
  checks; `die` clears it. `rlscape/sim/engine.py`: a death outside a fight.
- `scripts/calibrate_combat.py`, `scripts/calibrate.py`: food eaten from the inventory, clicks apart.
- Tests: `tests/test_sim_poison.py` (new).

## Infrastructure Changes

- None (the server ran the drop probe).

## Decisions

- **Agent choices (reversible):**
  - outside fights, a poison hit that leaves HP at or below the retreat point is eaten through while food lasts
  - the rate model takes the severity as staying at the monster's while it fights (its swings come several times
    in each 30 ticks)
  - a death from poison outside a fight is found at the end of the option
- **Raised for Caleb:** env contract v1.14's wording (poison in §8).

## Validation

- `uv run pytest -q --ignore-glob="tests/*_live.py"`: 270 passed. ruff (pyflakes): passed.
- `scripts/calibrate_combat.py --resim results/calibration/combat-20261105-2007.json`: the poison spider cases end
  out of food in both, at matching times.

## Follow-Up

- The drop probe's results; the live suite; rerun the ranged cases with the fixed eat count.
- Commit when Caleb asks.
