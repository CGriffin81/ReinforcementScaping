# Agent Interaction

## Metadata

- Interaction ID: m002-prayer-flicking-in-fights
- Timestamp CST: 2026-10-31 12:04:57 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the defence-prayer rule recorded; prayer flicking built into the sim's fights and tested)
- Commit: the main repo commit that adds this record (branch `sim-v0`; its SHA can only be filled in by a later commit)

## Full Prompt

> Defence prayers don't need to be flicked unless an enemy has multiple damage types or the agent does not have
> access to the protection prayer associated.

## Response Summary

- Finished what `m002-prayer-in-combat` started (OQ-3: fights flick prayers automatically), with Caleb's rule for
  defence prayers.
- A fight flicks, on the monster's swing ticks, the protection prayer for its style, or the best defence prayer
  (and against magic the best Mystic prayer) when the Prayer level lacks it. On the character's swing ticks it
  flicks the best accuracy and damage prayers, except next to a monster swing. Prayer points never drain.
- The candidate rates, the danger filter and the sim's fights all use it.
- E1 baselines barely move: neither raises Prayer far.

## Documentation Changes

- `docs/env-contract.md`: v1.8, §8's Prayer row, decision 24.
- `docs/option-catalog.md`: §4 "Prayers in fights".
- `docs/decision-log.md`: the decision, what's built, agent choices, results.
- `ROADMAP.md`: the status line.
- `docs/agent-interactions/m002-prayer-in-combat.md`: its timestamp, from the transcript.
- This record.

## Code Changes

- `rlscape/combat/prayers.py` (new): `Flicks`, `flicks`, `boosted_swings`, `boosted_share`.
- `rlscape/combat/formulas.py`: `prayer_boosted`; a prayer term in every player roll and max hit.
- `rlscape/combat/rates.py`: `Fighter.flicks`; protection and defence prayers in `npc_offence`; boosted swings in
  `player_offence` and `combat_rates`.
- `rlscape/sim/combat.py`: `kill_sequence` takes the boosted swings' pattern; `fight` passes it.
- `rlscape/sim/equipment.py`: `fighter_for` adds the prayers.
- `tests/test_prayers.py` (new, 7 tests).

## Infrastructure Changes

None.

## Decisions

- **User decisions:** defence prayers only where the protection prayer is missing or the monster has several
  damage types.
- **Agent choices (reversible):**
  - on a tick next to a monster swing, the monster's tick keeps its prayer and the character's swing goes without
  - against magic, the defensive flick adds the best Mystic prayer
  - the sim's one style per monster leaves the several-damage-types case unmodelled
  - Chivalry or Piety with a Mystic prayer isn't handled (needs King's Ransom, outside the quest set)

## Validation

- `uv run pytest -q`: 225 passed, 28 skipped (live tests; the server was down).
- `uvx ruff check --select F401,F811,F841 rlscape tests scripts`: passed.
- The ported max hit matches the live test: Strength 60 gives 7, and 8 with Ultimate Strength.
- `scripts/evaluate.py --policies scripted_guide random --seeds 10` (`results/eval/guide-prayer-20261031`), hour 20:
  guide 314 [309, 319] / 95,721 / 109,572; random 234 [227, 241] / 102,050 / 11,032.

## Follow-Up

- Commit when Caleb asks (the fork first, then the main repo); fill in the Commit fields of this record,
  `m002-prayer-in-combat` and `m002-prayer-flicking` then.
