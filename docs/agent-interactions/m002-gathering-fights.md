# Agent Interaction

## Metadata

- Interaction ID: m002-gathering-fights
- Timestamp CST: 2026-10-31 15:58:06 CST (from the session transcript's message timestamp, UTC−05:00); the
  correction at 15:59:11 CST
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (the rule recorded; building it waits for OQ-8's remaining choices)
- Commit: the main repo commit that adds this record (branch `sim-v0`; its SHA can only be filled in by a later commit)

## Full Prompt

> Do not fight monsters if you are on a gathering task, unless it would be trivial to defeat them. If the setup's
> max hit is greater than or equal to twice the monster's hitpoints and their max hit is less than .25x the agent's
> health as it enters combat.

Claude asked four questions (`AskUserQuestion`: where safety is, safespotting now or later, the sim's model, the fork
changes); Caleb replied instead:

> I meant if the setup's max hit is at least half the monsters max hitpoints. My mistake.

## Response Summary

- Recorded the rule: fight on a gathering task only when the setup's max hit is at least half the monster's
  hitpoints and its max hit is under a quarter of the character's hitpoints as the fight starts.
- The four choices stay open in OQ-8, with recommendations; nothing is built until Caleb picks.

## Documentation Changes

- `docs/decision-log.md`, `docs/open-questions-log.md` (OQ-8), this record.

## Code Changes

None.

## Infrastructure Changes

None.

## Decisions

- **User decisions:** the trivial-fight rule, as corrected.
- **Awaiting Caleb:** OQ-8's remaining choices.

## Validation

None needed (docs only).

## Follow-Up

- Build the rule on both backends once OQ-8 is answered, then calibrate the willows again.
