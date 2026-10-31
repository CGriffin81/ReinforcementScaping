# Agent Interaction

## Metadata

- Interaction ID: m002-greedy-xp
- Timestamp CST: 2026-10-30 15:12:38 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (decision recorded and built; a related question about r_skill raised with Caleb)
- Commit: main repo `43887df` (branch `sim-v0`)

## Full Prompt

> Go with raw XP. There should be break points where going for certain levels in skills is very lucrative,
> comparatively. Going only by level will penalize an agent for going after higher skills to reach those break
> points.

## Response Summary

- E1's "greedy XP/hr" baseline is greedy on raw XP, as Caleb decided.
- Added `e1_baselines()`: masked random, `greedy_xp` and `greedy_wealth`, so the eval harness runs exactly E1's
  set. Greedy on r_skill stays available for comparison.
- Raised the question Caleb's reasoning opens: whether the agent's own skill reward, r_skill, which is level-based
  (env contract §4, signed off), should change too. Gave options with a recommendation; nothing changed without
  Caleb's decision.

## Documentation Changes

- `docs/decision-log.md`: the decision, and the open question about r_skill.
- `ROADMAP.md`: the greedy baseline item.
- This record.

## Code Changes

- `rlscape/baselines/policies.py`: `e1_baselines()`; the docstring records the decision and its reason.
- `rlscape/baselines/__init__.py`: exports `e1_baselines`.
- `tests/test_baselines.py`: `test_e1_uses_raw_xp_and_net_worth`.

## Infrastructure Changes

None.

## Decisions

- **User decision:** greedy XP/hr uses raw XP. Agent recommendation (r_skill) not taken.
- **Open, for Caleb:** whether the agent's skill reward r_skill moves to raw XP as well, or to something between.

## Validation

- `uv run pytest -q tests/test_baselines.py`: 8 passed.

## Follow-Up

- Caleb's answer on r_skill.
- Commit when Caleb asks.
- The eval harness, then the scripted-guide baseline.
