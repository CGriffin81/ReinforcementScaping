# Agent Interaction

## Metadata

- Interaction ID: m002-fast-candidate-ranking
- Timestamp CST: 2026-10-28 22:30:04 CST (the same prompt as `m002-sim-v0-inventory-and-selling` and
  `m002-sim-v0-combat-melee`, from the session transcript's message timestamp, UTC−05:00; the third piece of work
  done under it)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: main repo `59d7a31` (branch `sim-v0`)

## Full Prompt

> Continue work on the project. Try to avoid things that need my approval for now.

## Response Summary

- **Profiled the reference ranking** (89 ms): most of the time went to recomputing expected loot and rates that only
  change with the fighter, plan or loot mode.
- **Built `CandidateRanker`:** cached per-monster rates and loot, with every per-step quantity vectorised over all
  sites.
- **Checked it against the reference** on six characters with warnings as errors.
- **Fixed during the work:**
  1. a tie-order mismatch under loot mode "none" (alphabetical against first-seen); the ranker now reproduces the
     reference's order
  2. a 3.5 ms first version with a per-monster Python loop, replaced by vectorised best-plan bookkeeping (1.3 ms)

## Documentation Changes

- `docs/decision-log.md`, `ROADMAP.md` (the week-2 status line), and this record.

## Code Changes

- New: `rlscape/combat/ranking.py`, `tests/test_ranking.py`.

## Infrastructure Changes

None.

## Decisions

- **Agent choices (reversible):**
  - keep the scalar `select_candidates` as the reference and test the fast ranker against it
  - cache sizes (256 fighter/plan entries, 64 loot entries, 1,024 progress entries)

## Validation

- `uv run pytest -q`: 96 passed, 14 skipped.
- `tests/test_ranking.py`: 6 cases, exact match on ids, XP/hr, gp/hr, sites and styles.
- Timing: 1.26 ms per ranking against the reference's 89 ms.

## Follow-Up

- Combat-slot actions (30) and loot-mode actions (4) on the ranker; ranged and magic fights.
