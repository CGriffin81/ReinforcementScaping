# Agent Interaction

## Metadata

- Interaction ID: m002-guide-signoff
- Timestamp CST: 2026-10-31 04:09:00 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (both decisions applied and tested)
- Commit: the main repo commit that adds this record, with `m002-wider-guide`'s guide work (branch `sim-v0`;
  its SHA can only be filled in by a later commit)

## Full Prompt

> Apply both recommended actions.

(Q5 and Q6 of `docs/scripted-guide-draft.md`: (a) keep the 13-skill guide as E1's baseline; keep the four sim fixes.)

## Response Summary

- **Q5:** the scripted guide joined `e1_baselines()`. The guide's module, the harness's registry comment and env
  contract decision 17 now say it's reviewed.
- **Q6:** nothing to change; the fixes stay, and the decision is recorded.

## Documentation Changes

- `docs/scripted-guide-draft.md`: Caleb's review note; Q5 and Q6 marked decided.
- `docs/env-contract.md`: decision 17's review recorded. That's a note on an existing decision, not a new
  version.
- `docs/decision-log.md`, `ROADMAP.md`.
- This record.

## Code Changes

- `rlscape/baselines/policies.py`: `e1_baselines()` includes `ScriptedGuidePolicy`.
- `rlscape/baselines/guide.py`: the module docstring.
- `rlscape/eval/harness.py`: the `scripted_guide` comment.
- `tests/test_baselines.py`: E1's baselines are the four.

## Infrastructure Changes

None.

## Decisions

- **User decisions:** Q5 (a) and Q6 (keep), as recommended.
- **Agent choices:** none beyond applying them.

## Validation

- `uv run pytest -q`: 198 passed and 24 skipped (live tests; the server was down).
- `e1_baselines()` returns `random`, `greedy_xp`, `greedy_wealth` and `scripted_guide`.

## Follow-Up

- Skilling slots (XP/hr and gp/hr), then the prayer-flicking live test.
- Commit when Caleb asks.
