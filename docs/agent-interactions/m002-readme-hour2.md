# Agent Interaction

## Metadata

- Interaction ID: m002-readme-hour2
- Timestamp CST: 2026-11-23 16:10:49 CST (the prompt), the session transcript's timestamp (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The reviewer's guide's hour-2 comparison names the best baseline at hour 2.
- Commit: a commit to `main` after `71ba2f9`.

## Full Prompt

> Fix the README's hour-2 wording and commit it to main directly

## Response Summary

- **The slip** (found while checking the progress report, `m002-progress-report`): the README's RQ1 row said the
  agents were ahead at hour 2 with "121 levels against 97". 97 is the guide's level at hour 2, but the best baseline on
  level then is greedy XP/hr, at 106 (105.6, CI 105.3–105.8, `results/figures/progress.csv`). The guide is the best
  only at hour 20. On net worth, 108k is already the best baseline's (greedy GP/hr's).
- **The fix:** the row now reads "ahead of every baseline (121 levels against greedy XP/hr's 106, the best baseline on
  level that early; 247k gp against greedy GP/hr's 108k)".
- **The decision log:** H1's evidence (2026-11-22) repeats the comparison. The log is chronological, so that entry
  stays as Caleb saw it, and a new entry at the end says what was wrong and that it changes no result or verdict: the
  agents lead every baseline at hour 2 either way.

## Documentation Changes

- `README.md`: the RQ1 row's hour-2 sentence.
- `docs/decision-log.md`: "Fixed: the hour-2 comparison names the best baseline (2026-11-23)".
- This record.

## Code Changes

- None.

## Infrastructure Changes

- None.

## Decisions

- **User decision (Caleb):** fix the README's wording and commit it to `main` directly (the prompt).
- **Agent choices:**
  - name the baseline at hour 2, rather than drop the hour-2 comparison;
  - a correction entry in the decision log rather than an edit to the 2026-11-22 entry, which records the evidence
    Caleb decided on.

## Validation

- The hour-2 numbers from `results/figures/progress.csv`: E3 (1, 0) 120.7 levels (CI 118.1–123.6), greedy XP/hr 105.6,
  the guide 97.3; E3 (0, 1) 247k gp, greedy GP/hr 108k.
- A search of the repository for the old comparison: the README and the decision log hold it (both handled); the
  progress report already says "at most 106 for a baseline".
- `git diff --check` is clean.

## Follow-Up

- None.
