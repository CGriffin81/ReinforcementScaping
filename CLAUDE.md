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
- Undecided questions go in `docs/open-questions-log.md` as they come up, including future ones that can't be
  decided yet. When one is answered, move it (with its options and the answer) to the decision log and delete it
  from the open-questions log. Answered questions live only in the decision log; other docs state the design.
- Gaps Caleb chose to leave for after the project are in `docs/post-project-gaps.md` (what, why, the cost, how
  to close each).
- External references (papers, code, data sources, related work) are listed in `docs/resources.md`,
  numbered to continue the proposal's bibliography. Add a resource there when the project starts using it.

Fixed decisions: every episode starts from a fresh level-3 character with
the starter kit; training episodes are 20 game-hours with checkpoints every 2
game-hours; combat is in scope. Quests are out (2026-11-06): every quest the
server has (68) is complete from the start, as flags only (quest points and
unlocks, no XP or items), and there are no quest options. Simulator
(2026-10-28):
- event-level sampling
- four more skills (Crafting, Agility, Herblore, Runecrafting) arrive in sim
  v1, before E2; Fletching was brought into sim v0 (2026-10-31)
- ambient bots off on the server for calibration and E6
- a ±20% sim-to-server gate before E2 (env contract §7), calibrated at 50 ms
  ticks with a speed check at 600 ms (2026-11-06)

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
  The server version is frozen from 2026-10-31, the start of calibration
  (Caleb): no more upstream syncs. (If one is ever approved, run
  `git lfs fetch --all upstream` before pushing, or the push is rejected
  for missing cache objects.)
- Our server code is `Server/src/main/content/rl/`: `RLBridge.kt` (transport),
  `RLCommands.kt` (commands), and `RLPlayer.kt` (the agent's character).
  - `RLPlayer` is **treated as a human by every game rule**
    (`isArtificial() == false`). Session plumbing uses
    `Player.hasClientSession()` instead. Each has its own account uid
    (1,000,000,000 + its bridge uid, in `Repository.uid_map`), which kill
    credit and drops, gravestones and GE offers go by. `spawn` completes every
    quest the server has (`completeEveryQuest`).
  - Config: `server.tick_ms`, `server.bind_address`, `world.ge_freeze_prices`,
    `world.ge_frozen_buyer`, `world.ge_frozen_seller`, `world.ge_blocked_items`,
    and the `[rl]` section (`bridge_enabled`, `bridge_port`, `random_events`).
  - `worldprops/rl.conf` is the training config: `default.conf` with the
    bridge on, prices frozen, the frozen-price GE buyer and seller on,
    nothing blocked on the GE (the anti-dragon shield was, until
    2026-11-06), random events off for RL characters, ambient bots off (`enable_bots = false`, since
    2026-10-31), dev mode off (`dev = false`, since 2026-11-07: it changes drop and catch rates), and
    the game port bound to 127.0.0.1.
  - Other fork rule changes: no Slayer level requirements for any monster
    (2026-11-07, OQ-32: `NPC.isAttackable` and `checkImpact`, `IdleAbstractNPC`,
    the ice cooler; Slayer gear still applies); aggression tolerance counts 1,000 game ticks, not
    10 wall-clock minutes (`Region.isTolerated`), so a sped-up server behaves the
    same; the home teleport waits 3,000 game ticks (30 minutes) between casts
    (`homeTeleport`); being hit keeps an entity "in combat" for 17 game ticks,
    not 10 wall-clock seconds (`combat-time`: `CombatPulse`, `Entity.inCombat`,
    `MapZone.checkMulti`), which single-combat areas and logging out read.
  - Ava's devices (2026-11-07): the accumulator needs 50 Ranged and gathers back
    the shots its 80% catch misses that would land; `spawn` switches the
    devices' attraction off.
  - Ranged safespots (2026-11-07, OQ-27 (d)): the bridge's `ranged_safespots`
    runs the server's own chase (DUMB pathing, each monster's `canSwing`) on
    detached copies to find where a monster gets stuck short of attacking, and
    `npcs` tells a safespotter which monsters would stay stuck in shot. The
    export is `scripts/export_ranged_safespots.py` → `data/ranged_safespots.csv`.
- **GE state:** before running the server for experiments, install the frozen
  2009 GE: `uv run python scripts/install_ge_db.py`. The server must be
  stopped; the old database is backed up. The pipeline is
  `export_item_definitions.py` → `fetch_ge_history.py` →
  `build_price_tables.py`.
- **Travel map:** `scripts/export_collision.py` (server running) writes the surface's collision map and doors
  to `data/travel/`, which `rlscape/routes.py` plans walking routes on.
- **Net worth** uses `data/prices_v2.csv`: max(high alchemy − nature rune,
  January 2009 GE price). `prices_v1` is superseded. Ava's devices, untradeable
  in the game, are on the frozen GE at Caleb's set prices (2,500 and 10,000 gp).
- Build from `server/Server`: `mvnw.cmd -B package -DskipTests` (about 3 min
  cold, about 1 min incremental).
- Run from `server/Server` (the working directory matters for `data/`):
  `java -jar target/server-1.0.0-jar-with-dependencies.jar worldprops/rl.conf`.
  The first launch ever takes about 7 min to fill the GE price index; later
  launches take about 8 s. The bridge listens on 127.0.0.1:43610.
- The world only ticks fully while the server can reach the internet (its
  connectivity check).
- Python: `uv sync`, `uv run pytest` (live bridge tests skip when the server
  is down), and `uv run python scripts/gate_check.py`. In parallel:
  `uv run pytest -n 8 --dist loadgroup` (the live tests stay on one worker).
- More servers at once (Caleb, 2026-11-06): `uv run python
  scripts/server_instances.py 2 3` writes `results/servers/rl-<n>.conf`
  (world n, bridge port 43610 + n - 1, its own GE under
  `data/eco/instance-<n>`); start each like the first with that config, and
  point a script or the tests at one with `RL_BRIDGE_PORT`. Each world has
  its own tick speed. One server also takes several scripts at once, each
  with its own characters (the bridge serves each connection on a thread):
  set its tick first, keep their sites apart, and give the live tests a
  server of their own (they set the tick).
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
