# Decision Log

A chronological record of project decisions and findings. Each entry says
whether it is a **User Decision**, an **Agent Recommendation** (not binding
until accepted), or a **Finding** (an observed fact, with where it came from).
The interaction records in `docs/agent-interactions/` hold the full context.

---

## 2026-10-05

### User decisions
- **Schedule:** week 1 starts 2026-10-05; the final report is due 2026-11-30.
- **Division of labor:** Claude writes the code; Caleb reviews and runs it. The
  Promethean AI-assisted code policy applies (`docs/ai-log-requirements.md`).
- **Starting state:** every episode starts from a fresh level-3 character.
- **Horizon:** training episodes are 20 game-hours, with evaluation
  checkpoints every 2 game-hours.
- **Scope:** combat is included.
- **Infrastructure:** install JDK 11, clone the 2009Scape server, and run
  MariaDB in Docker with an empty root password (local only).
- **Repository:** create a new GitHub repo under the `CGriffin81` account. It was
  created private at https://github.com/CGriffin81/ReinforcementScaping; private
  is the agent's reversible default. Keep the GitHub CLI installed.
- **Stretch (E7):** deferred. Caleb asked for more information, which is now
  in ROADMAP Appendix B. Decide at the week-5 midpoint.

### Agent recommendations (pending acceptance)
- Make the simulator the critical path, with the real server for calibration
  and validation only (ROADMAP §0).
- Use SMDP-correct discounting (γ^τ) in GAE and in potential-based shaping.
- Measure wealth as net worth, counting equipped and inventory items at the
  fixed price table, so that investing isn't penalized.
- Measure skill reward as fractional total level gained.
- Stretch: an LLM planner (option A).
- Keep server modifications out of this repo for now: `server/` is a pinned
  upstream clone. Whether to keep them as an overlay or patch set here, or as
  a separate fork, is still open.

### Findings
- **G1 (tick speed), early read:** the game loop is
  `core/worker/MajorUpdateWorker.kt`, which sleeps a hard-coded
  `600 - elapsed` ms, so making the tick configurable is a one-line patch.
  About 160 `System.currentTimeMillis()` call sites exist, mostly farming,
  brewing, and minigame timers. The one in scope is the 10-second
  "in combat" flag (`CombatPulse.kt:190`, `Entity.java:258`). Not yet
  tested under speedup.
- **G2 (control), early read:** a server-side bot framework already exists
  (`core/game/bots/`, 28 scripts in `content/global/bots/`), so options can
  run as `Script`s on an `AIPlayer` without a client. However, the
  `ScriptAPI` economy helpers cut corners:
  - `sellOnGE` deletes the items and pays nothing (`GrandExchange.addBotOffer`).
  - `buyFromGE` prices at the item's base value.
  - `teleportToGE` and `withdraw` skip travel.
- **G3 (GE dynamics), early read:** on first launch the GE price index is
  seeded with each item's **high-alchemy value**, not 2009 market prices
  (`core/game/ge/GEDB.kt` `populateInitialPriceIndex`). Prices then move
  with trades (`bots_influence_ge_price = true`). So the fixed price table
  must be a deliberate snapshot, either alch-seeded or after a bot warm-up
  period, and the report has to say which.
- **Starting kit** (`tutisland/handlers/iface/CharacterDesign.java`): bronze
  axe and pickaxe, small net, tinderbox, bronze dagger and sword, wooden
  shield, shortbow and 25 arrows, some runes and food; 25 coins in the bank.
- **Server:** upstream commit `bea45a9e` builds cleanly with Temurin 11 and
  `mvnw.cmd`. The first launch spends minutes populating the GE price index
  in SQLite, one autocommitted insert per tradeable item.
