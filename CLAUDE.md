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
- External references (papers, code, data sources, related work) are listed in `docs/resources.md`,
  numbered to continue the proposal's bibliography. Add a resource there when the project starts using it.

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
- `server/` is a **git submodule** pointing to the fork
  https://github.com/CGriffin81/2009scape-rl, branch `rl` (AGPLv3; upstream
  is https://gitlab.com/2009scape/2009scape). In the fork, `master` mirrors
  upstream (synced to `f279da8` on 2026-10-28, merged into `rl`) and our
  changes live on `rl`. All server modifications go in the fork and are
  committed there first; then this repo's submodule pointer is bumped.
  Sync upstream again only with Caleb's approval. Claude's recommendation is
  to keep the server version fixed once calibration starts. When syncing,
  run `git lfs fetch --all upstream` before pushing, or the push is rejected
  for missing cache objects.
- Our server code is `Server/src/main/content/rl/`: `RLBridge.kt` (transport),
  `RLCommands.kt` (commands), and `RLPlayer.kt` (the agent's character).
  - `RLPlayer` is **treated as a human by every game rule**
    (`isArtificial() == false`). Session plumbing uses
    `Player.hasClientSession()` instead.
  - Config: `server.tick_ms`, `server.bind_address`, `world.ge_freeze_prices`,
    `world.ge_frozen_buyer`, `world.ge_frozen_seller`, `world.ge_blocked_items`,
    and the `[rl]` section (`bridge_enabled`, `bridge_port`, `random_events`).
  - `worldprops/rl.conf` is the training config: `default.conf` with the
    bridge on, prices frozen, the frozen-price GE buyer and seller on, the
    anti-dragon shield blocked on the GE (Duke Horacio only), random events
    off for RL characters, and the game port bound to 127.0.0.1.
  - Other fork rule changes: Slayer levels are enforced on attack
    (`NPC.isAttackable`).
- **GE state:** before running the server for experiments, install the frozen
  2009 GE: `uv run python scripts/install_ge_db.py`. The server must be
  stopped; the old database is backed up. The pipeline is
  `export_item_definitions.py` → `fetch_ge_history.py` →
  `build_price_tables.py`.
- **Net worth** uses `data/prices_v2.csv`: max(high alchemy − nature rune,
  January 2009 GE price). `prices_v1` is superseded.
- Build from `server/Server`: `mvnw.cmd -B package -DskipTests` (about 3 min
  cold, about 1 min incremental).
- Run from `server/Server` (the working directory matters for `data/`):
  `java -jar target/server-1.0.0-jar-with-dependencies.jar worldprops/rl.conf`.
  The first launch ever takes about 7 min to fill the GE price index; later
  launches take about 8 s. The bridge listens on 127.0.0.1:43610.
- The world only ticks fully while the server can reach the internet (its
  connectivity check).
- Python: `uv sync`, `uv run pytest` (live bridge tests skip when the server
  is down), and `uv run python scripts/gate_check.py`.
- Database: not needed with the current config (auth and account persistence
  are off). `docker compose -f infra/docker-compose.db.yml up -d` starts
  MariaDB on 127.0.0.1:3306 if it's ever needed.

## Engineering rules

- **One environment contract, two backends.** `SimEnv` and `ServerEnv` share
  the same observation, action, mask, and info schema.
- **Port the formulas, measure the overheads.** Skilling, combat, and drop
  mechanics come from the server source. Travel, banking, and GE timing are
  measured on the server.
- **Don't reuse the bundled bots' economy helpers.** `ScriptAPI.sellOnGE` and
  `buyFromGE` bypass real GP flows, and `teleportToGE` and `withdraw` skip
  travel. Economy and banking options must use the player-facing GE and bank
  paths: the bridge's `ge_offer` and `ge_collect` call `StockMarket`.
- **`debug_*` bridge commands are for tests and calibration only.** Never
  expose them to the agent.
- **SMDP discounting.** Use γ^τ, with τ in game time, in GAE and in PBRS.
- **Log every agent decision** (obs, mask, option, action probabilities, value,
  duration, reward components), and seed everything.
- **Tests:** real sim and server behaviour, not mocks of it. Reproduce a
  failure before fixing it, and fix one failure at a time.
