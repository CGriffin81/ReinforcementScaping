# CLAUDE.md

## Project

CS898BG Reinforcement Learning individual project (Caleb Griffin), due
**2026-11-30**: *Learning to Climb: Hierarchical RL for Skill and Wealth
Accumulation in 2009Scape*. A high-level policy picks activity-level options
(train skill X at location L, kill N monsters, bank, sell or buy at the GE) in
a semi-MDP. It is trained mostly on a calibrated surrogate simulator and
validated on a local 2009Scape server.

- The research plan is in `CS898BG_RL_Project_Proposal_2009Scape.pdf`. The
  course requirements are in `Requirements.md`.
- The week-by-week plan, technical decisions, and fixed design decisions are
  in `ROADMAP.md`. It's the authoritative status, so check it against today's
  date.
- Decisions and findings are logged chronologically in `docs/decision-log.md`.

Fixed decisions: every episode starts from a fresh level-3 character; training
episodes are 20 game-hours with checkpoints every 2 game-hours; combat is in
scope.

## Collaboration mode

Claude writes the code; Caleb reviews and runs it. So:

- Keep each change small enough to review, and explain the design choices in
  it.
- Caleb decides research questions, experiment design, scope, and anything that
  changes what the report claims. Present options with a recommendation; don't
  decide these yourself.
- Commit or push only when Caleb asks.

## AI interaction logging (mandatory)

The project follows the Promethean AI-assisted code policy:
`docs/ai-log-requirements.md`. Every materially significant interaction gets a
record in `docs/agent-interactions/m{NNN}-{desc}.md` (`m000` for planning,
`m00N` for ROADMAP week N). Each record holds the full verbatim prompt, the CST
timestamp (estimated and marked when not instrumented), the agent
(`Claude Code`), the model the session actually is, the separate
doc/code/infra changes, recommendation vs user decision, validation, status,
and commit. Never fabricate metadata. Write the record in the same turn as the
work.

## Environment

- Windows 11, Ryzen 7 5800X (16 threads), 32 GB RAM, RTX 3050 8 GB.
- Python: a `uv` project pinned to 3.12. The system Python is 3.14, which is
  too new for the RL stack.
- JDK 11: `C:\Program Files\Eclipse Adoptium\jdk-11.0.32.101-hotspot`.
  Maven comes from the repo's `server/Server/mvnw.cmd` wrapper.
- `server/` is an upstream clone of https://gitlab.com/2009scape/2009scape
  (AGPLv3) at commit `bea45a9e93592b567f9b9293b82a36c8773244be`. It's
  git-ignored and is **not** part of this repo.
- Database: `docker compose -f infra/docker-compose.db.yml up -d` starts
  MariaDB on 127.0.0.1:3306 (root, empty password, local only), loaded from
  `server/Server/db_exports/global.sql`.
- Build the server from `server/Server`: `mvnw.cmd -B clean package
  -DskipTests` (about 3 min cold).
- Run it from `server/Server` (the working directory matters for `data/`):
  `java -jar target/server-1.0.0-jar-with-dependencies.jar`. The first launch
  is slow because it fills the GE price index in SQLite one row at a time.

## Engineering rules

- **One environment contract, two backends.** `SimEnv` and `ServerEnv` share
  the same observation, action, mask, and info schema.
- **Port the formulas, measure the overheads.** Skilling, combat, and drop
  mechanics come from the server source. Travel, banking, and GE timing are
  measured on the server.
- **Don't reuse the bundled bots' economy helpers.** `ScriptAPI.sellOnGE` and
  `buyFromGE` bypass real GP flows, and `teleportToGE` and `withdraw` skip
  travel. Economy and banking options must use the player-facing GE and bank
  paths.
- **SMDP discounting.** Use γ^τ, with τ in game time, in GAE and in PBRS.
- **Log every agent decision** (obs, mask, option, action probabilities, value,
  duration, reward components), and seed everything.
- **Tests:** real sim and server behaviour, not mocks of it. Reproduce a
  failure before fixing it, and fix one failure at a time.
