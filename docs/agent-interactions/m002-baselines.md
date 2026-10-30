# Agent Interaction

## Metadata

- Interaction ID: m002-baselines
- Timestamp CST: 2026-10-30 14:51:05 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (*V* adopted and committed; the random and greedy baselines built and tested; the scripted
  guide and the eval harness are next)
- Commit: *V* is main repo `cf050ed` (branch `sim-v0`); the baselines are in the main repo commit that adds
  this record (its SHA can only be filled in by a later commit)

## Full Prompt

> Accept the recommendations, commit this, and keep going with the baselines

## Response Summary

- **Adopted *V*** with Caleb's acceptance of Q1–Q4:
  - the 156 items are frozen in `data/vocabulary.csv`
  - they're the default for `build_catalog()` and `SimEnv()`: 974 actions, 1,572 observation features
  - vocabulary tests added
  - two existing tests updated for the new default
- **Committed** it as `cf050ed`, after the suite passed (156 passed, 18 skipped).
- **Built the E1 baselines:**
  - `RandomPolicy`
  - `GreedyPolicy` with three objectives: `skill`, `wealth` and `xp`
  - `play()`, which plays one episode and collects the contract's metrics
- **Ran a first 20-hour episode per baseline** and reported two findings:
  - greedy raw XP ends below random on total level
  - greedy wealth mines iron to a million gp
- **Asked Caleb** which greedy objective is E1's "greedy XP/hr".

## Documentation Changes

- `docs/option-catalog.md` §9: the decided *V*, its groups and readings, and the real action counts (974 in sim v0).
- `docs/vocabulary-draft.md`: marked accepted.
- `docs/env-contract.md` §3's as-built note: 974 actions, 1,572 features.
- `docs/decision-log.md`: the *V* decision, and the baselines with their 20-hour results and findings.
- `ROADMAP.md`:
  - the status line
  - the vocabulary item marked done
  - the random and greedy baseline items marked done
- `m002-vocabulary-draft`'s `Commit:` field (`cf050ed`).
- This record.

## Code Changes

- `data/vocabulary.csv` (new, frozen) and `rlscape/vocabulary.py` (new): *V*.
- `rlscape/sim/__init__.py`, `rlscape/envs/sim_env.py`: *V* is the default vocabulary.
- `rlscape/envs/sim_env.py`: `observe()` is public.
- `rlscape/baselines/` (new): `RandomPolicy`, `GreedyPolicy`, the `Policy` protocol.
- `rlscape/eval/` (new): `play()` and `Episode`.
- Tests:
  - `tests/test_vocabulary.py` (new, 3 tests)
  - `tests/test_baselines.py` (new, 7 tests)
  - `tests/test_sim_economy.py`: the misc-only test now uses an empty vocabulary
  - `tests/test_sim_slots.py`: the reference ranking uses the same *V*, and the melee mask assertion checks the rule
    (open exactly when the style passes the filter) rather than one ranking's outcome

## Infrastructure Changes

None.

## Decisions

- **User decisions:** Q1–Q4 of the vocabulary draft as recommended; commit; build the baselines.
- **Agent choices (reversible):**
  - greedy uses two lookahead samples per option and scores by mean gain per mean tick
  - when nothing gains, greedy banks if it can
  - greedy never picks loot-mode actions
  - the lookahead uses the policy's own random numbers, so it can't change the episode
  - `play()` resets the policy with the episode's seed
- **Awaiting Caleb:** whether E1's "greedy XP/hr" is greedy on r_skill (recommended: it's what total level
  tracks) or on raw XP.

## Validation

- After *V*: `uv run pytest -q`, 156 passed and 18 skipped, before the commit.
- `uv run pytest -q tests/test_baselines.py`: 7 passed.
- Full suite with the server stopped: 163 passed and 18 skipped.
- 2- and 20-hour episodes per baseline, seed 0, ran without errors. The 20-hour numbers are in the decision log, for
  one seed only. A 20-hour greedy episode takes 10–90 s on one core.

## Follow-Up

- Commit when Caleb asks.
- Caleb's choice of greedy objective for E1.
- The eval harness: seeds, parquet, bootstrap CIs.
- The scripted-guide baseline, drafted from archived 2009 guides and cited, for Caleb's review.
