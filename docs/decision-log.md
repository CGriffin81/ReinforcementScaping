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
- **Server changes live in a separate fork,** not as patches in this repo. This
  overrides the agent's recommendation.
  - The fork is https://github.com/CGriffin81/2009scape-rl (private), with
    `master` = upstream `bea45a9e` and our work on `rl`.
  - It's linked here as the `server/` submodule; that link is the agent's
    reversible choice.
  - The fork's LFS cache history (43 objects, 367 MB) went to GitHub LFS. The
    GitHub Free quota is 10 GiB.
- **Fixed price table:** snapshot the GE price index after the ambient bots
  have traded for **10 game-hours** from a freshly seeded GE. This is the
  agent's recommended option (b); the alternative was the seeded
  high-alchemy values (a). Produced by `scripts/ge_warmup.py` into
  `data/prices_v1.csv` plus `.meta.json`.
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
- Keep server modifications as a patch set in this repo. **Not accepted:** the
  user chose a separate fork (see the user decisions above).
- **Pending, from the G3 findings:**
  - *Economy model:* sell through shops, plus High Level Alchemy once it's
    unlocked; buy from shops and from GE bot stock. This needs a fork change
    so bridge characters trade on the GE as players. Drop the "sell at GE"
    options, since this world has no GE buyers.
  - *Stable prices across episodes:* set `bots_influence_ge_price = false` in
    `rl.conf` so the agent's purchases don't move the index (avoiding the
    upstream first-trade bug), and reset the GE to
    `grandexchange_warmup10h.db` at the start of each real-server episode.
  - *Valuation:* keep the high-alchemy table (`prices_v1`) for net worth,
    since it's what this world actually pays through alchemy and shops. Add
    an evaluation-time sensitivity check against an alternative table built
    from `BotPrices`.

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
- **G1 PASS:** the tick length is configurable (`server.tick_ms`, and at
  runtime through the bridge). Achieved ms per tick: 604 at 600, 123 at 120,
  63 at 60, 34 at 30, and 17.6 at 15, i.e. 34× real time. Source:
  `results/gates/gate_check_20261005_220938.json` (local only).
- **G2 PASS:** the bridge spawns a character, reads its state, and injects
  authentic interactions. 600 ticks of chopping gave 10 logs and 250 XP.
- **XP cap without the tutorial flag:** `Skills.addExperience` clamps every
  skill at 175 XP unless `tutorial:complete` is set. The first gate run hit
  this (10 logs, 175 XP). The bridge's `spawn` now copies what the real
  tutorial exit does (flag, varp/varbit, starter kit, landing tile
  3233,3230). A live regression test covers it.
- **No database needed:** with `use_auth = false` and
  `persist_accounts = false`, the server doesn't need MariaDB (its own config
  comment says so). The container is harmless but optional.
- **World freezes offline:** `MajorUpdateWorker` runs a cut-down tick (no
  pulses, no tick listeners) when the connectivity check to google.com and
  2009scape.org fails. Experiments therefore need internet access, or a
  config change.
- **GE economy mechanics (G3, from reading the code):**
  - *Bot sales are stock, not trades.* Ambient bots sell through
    `GrandExchange.addBotOffer` into a `bot_offers` table, priced at
    1.1 × max(base value or `BotPrices` override, price index).
  - *Only real players' buy offers match bot stock.* `tryExchangeWithBots`
    runs only for non-bot **buy** offers. Player **sell** offers match only
    player buy offers. Nothing in the game creates buy offers: no bot calls
    `ScriptAPI.buyFromGE`, and it only stores the offer in a map without
    dispatching it.
  - *The price index moves only on executed trades* (`PriceIndex.addTrade`).
    With no human players it should stay at the seeded high-alchemy value
    (about 60% of base value). The warm-up below tests this.
  - *A server-controlled character can't trade as a player.*
    `GrandExchange.dispatch` rewrites every offer from an artificial player
    into a bot offer on the server's own account. Our RL character is an
    `AIPlayer`, so as-is its buys never fill and its sales vanish into bot
    stock.
  - *Upstream seeding bug:* the index is seeded with `total_value = alch` but
    `unique_trades = 0`, so an item's first trade sets its price to about
    alch + trade price.
- **G3 result: prices are static and the market is bot-stocked.** The
  10-game-hour warm-up from a freshly seeded GE (22:30–22:52, fork
  `a394d60`, 15 ms ticks, 100 ambient bots) changed **0 of 7,324 prices** and
  left **0 items ever traded**. Open player offers stayed at 0 throughout.
  - Bot stock grew from 0 to 19,675 units of 145 items. The largest stocks:
    pure essence 5,643; oak logs 3,192; cannonballs 2,016; bow strings 1,596;
    logs 1,544; willow logs 1,287; yew logs 955; bones 764.
  - Achieved speed over the run was 21.5 ms per tick (28×), slower than the
    gate's 17.6 ms. Per-sample snapshots and the growing world state add
    overhead.
  - So `data/prices_v1.csv` is **exactly the seeded high-alchemy values**.
    Under this server's mechanics, options (a) and (b) give the same table.
    Examples: cowhide 1, bones 1, big bones 1, logs 2, oak 12, willow 24,
    coal 27, iron bar 17, raw lobster 170, steel pickaxe 300.
  - `data/grandexchange_warmup10h.db` keeps the GE database at the end of the
    warm-up. It was copied about 1 game-minute after the 10-hour mark, so it
    holds 19,723 bot-stock units. Real-server episodes can reset to it.
- **Shop economics:** general stores buy from players at the low-alchemy
  value (about 40% of base value), minus 3% of value per unit of overstock
  (capped at 10 units). They sell at 100–130% of base value. Items sold to
  shops are recycled into GE bot stock every 180 game-minutes
  (`Shops.kt`, tick-based).
- **Fidelity notes for later:**
  - `AIPlayer.finalizeDeath` calls `fullRestore()`. Check death and item-loss
    behaviour against a real player before combat options rely on it.
  - The bundled `BotScriptPulse` caps bot actions at 75 per tick across all
    bots. Our own option executor should not go through it.
