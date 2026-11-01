# Agent Interaction

## Metadata

- Interaction ID: m002-reachable-targets
- Timestamp CST: 2026-10-31 15:30:58 CST (from the session transcript's message timestamp, UTC−05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (recommendations given; no code changed)
- Commit: the main repo commit that adds this record (branch `sim-v0`; its SHA can only be filled in by a later commit)

## Full Prompt

> What are your recommendations for fixes? It seems obvious to me that an agent should not try to pick a resource
> that it cannot path to.

## Response Summary

- The policy never picks the tree: the bridge's `interact` does, through `ScriptAPI.getNearestNode`, which goes by
  straight-line distance in the current region and never checks for a path. The server's `Pathfinder.find`
  reports whether a path reaches a node.
- Recommended, in order (all fork changes, OQ-4):
  1. `interact` picks the nearest reachable target, with "none reachable" otherwise (the runner then waits for a
     respawn), and an optional id filter for mixed mines.
  2. Walking as a client packet, to cancel an action and for travel; the runner keeps its watchdog.
  3. Clicking by tile only if needed later.

## Documentation Changes

- `docs/open-questions-log.md`: OQ-4's recommendation.
- This record.

## Code Changes

None.

## Infrastructure Changes

None.

## Decisions

- **User decisions:** none yet (Caleb's go-ahead pending on OQ-4).
- **Agent recommendation:** as above.

## Validation

- Read `ScriptAPI.getNearestNode` and `Pathfinder.find` / `Path.isSuccessful` / `Path.isMoveNear` in the fork.

## Follow-Up

- Build (1) and (2) with a live test at the Draynor willows once Caleb approves.
