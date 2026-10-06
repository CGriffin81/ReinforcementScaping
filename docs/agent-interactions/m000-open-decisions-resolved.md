# Agent Interaction

## Metadata

- Interaction ID: m000-open-decisions-resolved
- Timestamp CST: 2026-10-05 ~21:13:00 CST (estimated: the server clone this prompt triggered started at 21:15)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: None (first committed with the m001 work)

## Full Prompt

> 1. The final report is due November 30.
> 2. I want you to write the code while I review and run it. Use the AI-assisted Code policy from Promethean. I can provide more of a reference for that, if you need it.
> 3. Yes.
> 4. The starting character will always be a fresh level 3.
> 5. The episode length will be 20 hours for training with checkpoints every 2 hours.
> 6. Combat should absolutely be included.
> 7. I need more information on this.
> 8. No work has been started yet.

Context: these answer the 8 questions at the end of `m000-initial-roadmap`. Item 3
answered "permission to install JDK 11 + Maven via winget and clone or fork the
2009Scape server into `server/`, and where the repo should live".

## Response Summary

- Searched the web for "Promethean AI-assisted code policy". The closest public
  result was OpenBook's AI Code Policy, which is not the right policy, so I asked
  the user for the reference.
- Installed Temurin JDK 11 via winget. Found that Maven isn't needed because the
  repo ships `Server/mvnw.cmd`. Shallow-cloned upstream 2009Scape into `server/`
  (284 MB, commit `bea45a9e`). Built the server jar (about 3 minutes, exit code 0).
- Ran `git init` on the project with a `.gitignore` that excludes `server/`.
- Read the server code for the week-1 gates:
  - **G1:** the tick loop is a hard-coded 600 ms sleep in `MajorUpdateWorker.kt`.
    Wall-clock dependencies are mostly out of scope; the "in combat" flag is the
    exception.
  - **G2:** the bundled `ScriptAPI` economy helpers bypass real GP flows (bot sales
    pay nothing; buys are priced at the item's base value) and skip travel by
    teleporting.
  - **Starter kit:** read from `CharacterDesign.java`.
- Updated `ROADMAP.md` with the decisions, the 20-hour horizon, 2-hour checkpoints,
  revised E6 throughput math, combat as core in Appendix A, how the simulator will
  model combat, the bot-helper finding, the starting state, and a new Appendix B
  comparing the stretch options (LLM planner, DreamerV3, learned micro-options,
  none).
- Explained the stretch options in chat and recommended option A, the LLM planner.

## Documentation Changes

- Updated `ROADMAP.md`: fixed-decisions block, throughput, G1 early read, a
  bot-helper row in the technical-decisions table, week-1 checkboxes, 2-hour
  checkpoints, Appendix A (starting kit, combat), Appendix B (stretch options), and
  the open-questions section.
- Added Claude memory notes outside the repo (collaboration mode, timeline).

## Code Changes

None.

## Infrastructure Changes

- Installed Eclipse Temurin JDK 11.0.32 via winget (sets the machine `JAVA_HOME`).
- Cloned `https://gitlab.com/2009scape/2009scape.git` (depth 1) into `server/`.
- Built `server/Server/target/server-1.0.0-jar-with-dependencies.jar`; Maven and
  its dependencies were downloaded into `~/.m2`.
- Initialized the git repo at the project root.

## Decisions

- **User decisions:**
  - final report due 2026-11-30
  - Claude codes; Caleb reviews and runs
  - Promethean AI-code policy applies
  - installs approved
  - fresh level-3 start
  - 20 game-hour episodes with 2-hour checkpoints
  - combat in scope
  - stretch decision deferred pending more information
- **Agent recommendation:** stretch option A (LLM planner), with B (DreamerV3) as
  the pure-RL alternative. Not decided.
- **Agent recommendation:** reuse only the gathering and combat logic from the
  bundled bot scripts; economy and banking go through the player-facing GE and
  bank paths. Proposed.

## Validation

- `java -version` reports Temurin 11.0.32.1.
- The Maven build exited with code 0 and produced a 43.9 MB jar with dependencies.
  The only console output was a harmless Kotlin compiler `WARN`.
- The server was **not** run in this interaction; it needs MariaDB, which wasn't yet
  approved.

## Follow-Up

- Get the Promethean policy reference. Provided in `m001-github-repo-and-local-infra`.
- Decide where the remote repo lives. Decided in `m001-github-repo-and-local-infra`.
- Get approval to run MariaDB. Given in `m001-github-repo-and-local-infra`.
