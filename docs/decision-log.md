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
  `data/prices_v1.csv` plus `.meta.json`. **Superseded for valuing wealth** by
  economy decision 3 below; the warm-up's bot stock is still the base of the
  frozen GE.
- **Stretch (E7):** deferred. Caleb asked for more information, which is now
  in ROADMAP Appendix B. Decide at the week-5 midpoint.

### Agent recommendations (pending acceptance)
*Resolved later (noted 2026-10-31):* the env contract Caleb signed off on
2026-10-28 adopts the discounting (§1) and both rewards (§4); his simulation
decisions the same day build on the sim-first plan; the stretch is tentatively
A (`docs/open-questions-log.md`, OQ-1).
- Make the simulator the critical path, with the real server for calibration
  and validation only (ROADMAP §0).
- Use SMDP-correct discounting (γ^τ) in GAE and in potential-based shaping.
- Measure wealth as net worth, counting equipped and inventory items at the
  fixed price table, so that investing isn't penalized.
- Measure skill reward as fractional total level gained.
- Stretch: an LLM planner (option A).
- Keep server modifications as a patch set in this repo. **Not accepted:** the
  user chose a separate fork (see the user decisions above).
- **Pending, from the G3 findings** (resolved by Caleb's decisions below):
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

### User decisions (economy, later on 2026-10-05)
1. **The RL character is always treated as a human player.** Implemented in
   the fork as `content/rl/RLPlayer`.
   - It keeps AIPlayer's connection-less plumbing: no packets, no saves, no
     ping timeout. The new `Player.hasClientSession()` guards that plumbing.
   - It reports `isArtificial() == false`, so every game rule sees a human.
     Game-rule checks that tested the `AIPlayer` *type* now test
     `isArtificial()`: interaction blocking by dialogues, the tutorial damage
     guard, kill credit, drop tracking, Morytania effects, and
     death-restore.
   - Like a human, it runs every login hook (which creates the GE records,
     slayer and hunter managers, etc.) and "clicks Play" on the welcome
     screen.
2. **Freeze the GE at historical 2009 prices.**
   - Source: the RuneScape Wiki's Weird Gloop exchange API.
   - Window: January 2009, since 2009Scape targets content "in and around
     January 1st, 2009". An item first tracked later in 2009 uses its first
     month with data. Items with no 2009 data keep the server's seeded
     (high-alchemy) GE price.
   - `world.ge_freeze_prices = true` (in `rl.conf`) stops trades from moving
     the index, and makes bot stock sell at exactly the index price, with no
     10% markup and no `BotPrices` floor.
   - `data/grandexchange_2009_frozen.db` is the 10-hour warm-up bot stock with
     the 2009 price index.
3. **Value wealth at max(high alchemy − nature rune, historical 2009 GE
   price).**
   - The nature rune is priced from the January 2009 table (229 gp).
   - The alchemy term follows the server's spell rule
     (`ModernListeners.alchemize`: tradeable or alchemizable, not coins),
     which covers every tradeable item.
   - Coins = 1; values are floored at 0.
   - Output: `data/prices_v2.csv`. This **supersedes `data/prices_v1.csv`**
     (the 10-hour snapshot) for valuing wealth; v1 is kept as a record.

### Agent interpretations of those decisions (reversible; flag if wrong)
- Use the median of January 2009 samples. The `sample` endpoint gives about
  500 points per item history, which is 2–4 points in January 2009.
- When frozen, the GE quotes and trades at exactly the 2009 price.
- Noted items take their unnoted item's prices.
- Open dialogues are dismissed automatically each tick (a human clicking
  "continue").
- `ge_offer` requires standing within 15 tiles of the GE.
- `ge_collect` takes banknotes when the items don't fit in the inventory.
- `debug_teleport` and `debug_give` exist for tests and calibration only, and
  are never exposed to the agent.

### Findings (economy implementation)
- An `AIPlayer`'s GE offer is rewritten into a bot offer. As an `RLPlayer`,
  our buy matched bot stock: 10 oak logs at 12 gp, coins deducted, price
  index unchanged under the freeze.
- Without the login hooks, `GrandExchangeRecords.getInstance` returned a fresh
  throwaway object on every call, so offer slots were lost even though the
  trade completed.
- With the tutorial flag set before init, `LoginConfiguration` parked the
  character on the lobby screen, where it couldn't move.
- A GE sell still never fills: nothing in this world places buy orders.
- `ItemDefinition.isAlchemizable` is true for 1 of 7,324 items. The spell
  doesn't rely on it.
- RuneScape later re-issued many items under new ids (for example, rune
  platebody 1127 → 45543), so the wiki's *current* item list can't be used as
  a filter. The old ids' history (to 2019) is still served: rune platebody was
  58,400–59,000 gp in January 2009, rune scimitar about 30,000.
- RL characters all have GE `player_uid` 0 (AIPlayer details). This is
  harmless while each episode resets the GE database.

### Pending (needs Caleb)
- **Random events:** they are on for the RL character, per "always human".
  They will interrupt activities (some teleport the player away) until the
  agent can handle them. `rl.random_events = false` turns them off.
- **GE selling:** with no buyers in this world, the agent can only turn items
  into coins through shops or alchemy. A market-maker that fills sell offers at
  the frozen price would restore GE selling, but it isn't authentic to this
  server.

---

## 2026-10-27

### User decisions
- **Random events are off for training.** `rl.conf` sets
  `rl.random_events = false`, so RL characters get no AntiMacro timer.
  `default.conf` keeps the human default (on). This resolves the pending
  random-events question.
- **A buyer fills GE sell offers at the frozen 2009 price.** The new fork
  setting `world.ge_frozen_buyer` is on in `rl.conf`, off in `default.conf`.
  This resolves the pending GE-selling question; GE selling is an option for
  the agent again.

### Agent implementation choices (reversible; flag if wrong)
- **When it fills:** the buyer runs on the GE worker thread *after* a sell
  offer has been matched against any real player buy offers, and takes the
  whole remaining amount.
- **What it pays:** the frozen index price. It never pays above the index,
  so asks above it stay open. Asks below the index are still paid the index,
  since the buyer is treated as an older buy offer, the same rule `exchange()`
  applies between players.
- **Frozen market only:** it does nothing unless `world.ge_freeze_prices` is
  on, which avoids the upstream first-trade price bug on a live index.
- **Where the items go:** back into the GE as bot stock (`addBotOffer`), so
  they can be bought back at the same frozen price.
- **Why not reuse `exchange()`:** it would update a transient bot buy offer
  and overwrite that item's bot-stock row. The buyer mirrors the seller's side
  of `exchange()` instead.
- **Untracked items:** items with no 2009 price still have their seeded
  (high-alchemy) GE price, so the buyer paid high-alchemy value for those
  roughly 1,250 rows. **Superseded** by the user decision below.

### User decision (later on 2026-10-27)
- **The buyer only buys items with a 2009 price.**
  - The frozen GE database now carries a `historical_price_items` table
    listing the 6,070 price rows that hold a 2009 price (unnoted and noted
    ids). It is written by `scripts/build_price_tables.py`.
  - The buyer (`GrandExchange.sellToFrozenBuyer`) checks it before buying. Any
    other sell offer stays open until a real buyer appears, which in this
    world means never; those items can still go to shops or alchemy.
  - The server creates the table empty when a GE database doesn't have it, so
    with any other database the buyer buys nothing.
  - The price tables are unchanged: `prices_v2.csv` and `ge_prices_2009.csv`
    rebuilt byte-for-byte identical.

### User decision (schedule, 2026-10-27)
- **Keep the original roadmap and make up the lost time.** The agent had
  proposed re-baselining the remaining five weeks, dropping E7 and making E4
  optional; that was declined. The week dates in `ROADMAP.md` stand. On
  2026-10-27 (calendar week 4), the week-1 environment interface and option
  catalog were the next open items, followed by all of week 2 onward.

### Proposed (awaiting Caleb)
- `docs/env-contract.md` v0. Five decisions are listed there: banking inside
  activity loops, a fixed option duration (15 minutes; 5 and 45 for E5), no
  Magic training in v0, melee only, and two sell options.
- `docs/option-catalog.md` v0 (53 actions). Its **blocking** question: the
  frozen GE bot stock holds almost no gear, tools or food (145 stocked items;
  only 3 bronze axes, 45 feathers, 1 steel full helm, 2 battleaxes), so GE
  buy options would rarely fill. The agent recommends a frozen-price seller,
  the mirror of the frozen buyer.

### Related work reviewed (2026-10-27)
- **RuneBench and rs-sdk** (Max Bittker; `docs/resources.md` [18], [19]).
  They are LLM-agent tooling and a benchmark for LostCity 2004scape: a
  different game version and engine, with a faster XP curve. **Agent
  recommendation:**
  - Use them as **related work and design references**: RuneBench is the
    closest prior work on agents in RuneScape, measuring skill-XP and gold
    tasks, and the reference point for E7 option A. rs-sdk's
    effect-verifying high-level actions with typed `success` / `reason`
    results are the pattern for our option executor.
  - Do **not** use them as the environment or compare numbers with them
    directly.
  - Don't copy RuneBench code: its README claims MIT but the repo has no
    LICENSE file. rs-sdk is MIT.
- `docs/resources.md` was created as the project's running reference list,
  continuing the proposal's numbering.

### User decision (gear sourcing, 2026-10-27)
- **Gear, tools and food come from a frozen-price GE seller and from shops.**
  This answers the option catalog's blocking question with option (c),
  rather than the agent's recommendation (a).
  - **Seller:** implemented in the fork as `world.ge_frozen_seller` (on in
    `rl.conf`, off in `default.conf`), `GrandExchange.buyFromFrozenSeller`.
    After real sell offers and bot stock have matched a player's buy offer,
    it fills the rest at the frozen index price from unlimited supply. It has
    the buyer's limits: frozen market only, items with a 2009 price only, and
    never below the index. Overpayment is refunded, as `exchange()` does with
    an older sell offer.
  - **Shops:** the catalog now lists the authentic nearby shops for each
    item: Bob's axes, Nurmof's pickaxes, Zeke's scimitars, Gerrant's fishing
    supplies, and Lumbridge general store. Full armour sets and food stay
    GE-only, because no shop in reach sells them in usable form. Shops with
    150,000+ stock (including dragon scimitars) look like 2009Scape
    additions and are excluded.

### Findings
- **Shops versus the 2009 GE price:** shops are cheaper for cheap tools (fly
  rod 5 vs 77, lobster pot 20 vs 70, hammer 1 vs 13). The 2009 GE is cheaper
  for weapons, armour and high-tier pickaxes (steel scimitar 400 vs 200, rune
  pickaxe 32,000 vs 19,100). So the choice of source is a genuine
  price-versus-travel trade-off. This raises a new catalog question:
  separate actions per source, or an executor rule.
- **GE offers outlive the character that placed them.** In testing, an
  earlier test's unfilled sell offer filled a later test's buy offer as an
  ordinary player-to-player trade. That confirms `ServerEnv.reset` must
  reinstall the GE database every episode, as the env contract already says.
- **Revised recommendation (env-contract question 5):** sell by category, not
  "sell all produce". Selling everything would also sell the ores and raw
  fish meant for smelting and cooking, which breaks processing chains.

### User decisions (env contract, 2026-10-27)
1. **No banking inside activities.** Activities stop when the inventory is
   full. Banking, dropping, selling and alching are the agent's choices,
   because sometimes dropping beats walking to a bank. This overrides the
   agent's recommendation.
2. **Activity duration:** *D* = 15 game-minutes by default; 5 and 45 for E5.
   Accepted.
3. **Magic and High Level Alchemy are in v0**, because sometimes alching
   beats banking or selling. This overrides the agent's recommendation.
4. **Ranged and Magic combat are in**, and the agent should be able to fight
   **any enemy in the game**, choosing on theoretical gp/hr and XP/hr. This
   overrides the agent's melee-only recommendation.
5. **Selling:** Caleb asked why selling wouldn't be per item in quantities
   of 1 / 10 / X / all. The agent dropped the category idea and explained that
   the open point is only the number of actions. Still open.

### Agent design proposals that follow from those (Proposed; option catalog v0.2)
- **Combat candidate slots.**
  - The enemy pool comes from server data: 4,044 NPC configs with combat
    stats, spawns and 444 drop tables; reachable monsters only.
  - Each decision, the combat-rate model rates every enemy for each class.
    The 3 best by XP/hr and the 3 best by gp/hr fill fixed slots, after
    filtering out enemies whose expected damage would outrun the food held.
  - That's 30 combat actions in all: melee 6 × 3 styles, ranged 6, magic 6.
    Each slot's rates are in the observation.
- **Explicit inventory management:** `bank_deposit`, a
  `bank_withdraw_for_<activity>` per processing activity, and `drop_<item>`.
  The observation separates inventory from bank.
- **Item vocabulary *V*** ≈ 60, plus a "misc" bucket, so per-item actions
  stay finite even though monsters drop thousands of item types.
- **Selling quantity:** recommend "all of the item in the inventory". With
  frozen prices and explicit banking it loses no control, and it keeps about
  425 actions instead of about 900 for 1 / 10 / all.

### Note on scope (not a re-plan)
- The decisions above roughly triple decisions per episode (about 80–150 →
  250–400) and grow the action space from 67 to about 425. Masking keeps the
  valid actions at any moment around 30–80. Training will be slower per
  episode. The simulator's ≥ 20k decisions/s target and early sanity runs
  (week 3) will show whether that's a problem.

### User decisions (later on 2026-10-27)
- **Selling: per item, all of that item in the inventory.** This takes the
  agent's recommendation. The action space stays at about 425 instead of
  about 900. Partial quantities are handled through banking.
- **Separate buy actions for GE and shops.** This takes the agent's
  recommendation. The agent learns the price-versus-travel trade-off.
- **Combat design:** Caleb asked for more context. Option catalog §10 now
  explains each part with real monster stats and drops from the server data
  (chicken, cow, goblin, man, Al-Kharid warrior, hill giant, moss giant,
  green dragon). It adds a fourth part that follows from "no auto-banking":
  the loot rule (recommended: coins, runes, arrows, vocabulary items, and
  anything worth ≥ 100 gp). Pending.

### User decisions (combat design, 2026-10-27)
- **A. Slots:** 3 best by XP/hr + 3 best by gp/hr for each of melee, ranged
  and magic. Accepted as proposed.
- **B. Danger filter:** accepted, **plus a gear check for special damage
  types**, such as dragonfire. A monster only qualifies if the character has
  the required protection: an anti-dragon shield for dragons. Monsters that
  block a combat style are ruled out for that class. Poison goes into the
  damage estimate. The anti-dragon shield was added to the buy options (GE).
- **C. Context-driven enemy pool:** monsters reachable because of held items
  (keys) or quest progress must be available, and an agent on a quest must
  be able to complete it. Implemented as an access table (area →
  item / quest / level requirement), checked every decision.
- **D. Looting is the agent's decision.** Agent's proposed design: a
  persistent loot mode set by 4 actions (all / valuable / vocabulary / none),
  shown in the observation. Alternatives: per-combat loot variants (120
  combat actions) or per-kill decisions.

### New open question (raised by decision C)
- **Are quests agent options?** 2009Scape implements about 70 quests.
  Rewards read from the quest code include Waterfall Quest at 13,750 Attack +
  13,750 Strength XP, Fight Arena at 12,175 Attack + 2,175 Thieving, and Tree
  Gnome Village at 11,450 Attack. Each quest needs a scripted server
  walkthrough and a simulator macro-option.
- **Agent recommendation:** a curated set of 4 low-risk quests (Waterfall
  Quest, Doric's Quest, Witch's Potion, Cook's Assistant). Fight Arena and
  Tree Gnome Village are later candidates; both end in fights against
  level-100+ monsters.

### User decisions (quests, 2026-10-27)
- **Every quest should eventually be completable by the agents.** This is
  a long-term requirement. The server implements 70 quests worth 132 quest
  points.
- **For this stage, curate quests that reach 32 quest points**, the
  requirement for Dragon Slayer.
- **Dragon Slayer unlocks rune platebodies and d'hide bodies** (Caleb). The
  server confirms it: `ItemQuestRequirementListener` locks every rune
  platebody, including trimmed and god versions, and the green d'hide body,
  including trimmed. Blue, red and black d'hide bodies aren't locked. The
  rune tier of `buy_armour_*` now has a Dragon Slayer precondition.

### Findings
- **Quest points don't gate using the anti-dragon shield.** It has no equip
  requirement (`item_configs.json`), it's tradeable, and its January 2009
  price is 301 gp, so the frozen seller sells it. 32 quest points unlocks
  *starting* Dragon Slayer (via the Champions' Guild). While Dragon Slayer is
  underway, Duke Horacio gives the shield free. Raised with Caleb; the
  shield stays buyable, as it was in 2009.
- **The server's equip rules can depend on quests**
  (`ItemQuestRequirementListener`). The simulator's equip rules must read the
  same table.

### Agent curation (option catalog v0.4 §10)
- **Exactly 32 QP, no skill requirements and no hard fights:** Cook's
  Assistant 1, Romeo & Juliet 5, Goblin Diplomacy 5, Ernest the Chicken 4,
  Prince Ali Rescue 3, Druidic Ritual 4 (animated armour nearby is a risk),
  Sheep Herder 4, Murder Mystery 3, Pirate's Treasure 2, Doric's Quest 1.
- **Plus** Waterfall Quest (1 QP) for 13,750 Attack + 13,750 Strength XP.
- **Backups:** Witch's Potion, Imp Catcher, The Restless Ghost, Rune
  Mysteries, Sheep Shearer, Monk's Friend, Black Knights' Fortress, Vampire
  Slayer, Demon Slayer.
- **Next goal:** Dragon Slayer.
- Each quest is one action. Whether each is fully completable in 2009Scape
  is verified while its executor script is written.

### User decisions (later on 2026-10-27)
- **The quest set includes the backups, Waterfall Quest and Dragon Slayer:**
  21 quests worth 50 quest points in total. Any 32 of those points open
  Dragon Slayer.
- **The anti-dragon shield is only obtainable from Duke Horacio**, once
  Dragon Slayer is underway or after it's complete if the shield was lost.
  This reverses the agent's earlier choice to leave it buyable.
  - Implemented as a new fork setting, `world.ge_blocked_items`.
    `PriceIndex.canTrade` refuses listed ids, so they can't be offered on the
    GE in either direction, the frozen seller can't sell them, and bots can't
    stock them. `rl.conf` sets `"1540,1541"`; `default.conf` sets `""`.
  - Other sources checked: no authentic shop or drop table has the shield,
    and there's no ground spawn. The only shop listing it is "Magic
    Emporium" (id 185, 150,000 stock), which has no NPC attached and is among
    the inauthentic shops the catalog already excludes.
  - The valuation table still prices the shield at its January 2009 value
    (301 gp, `prices_v2`). It's a small net-worth gain when the Duke hands it
    over. It can be set to 0 if Duke-only items shouldn't carry a GE value.

### User decision (2026-10-27, evening)
- **The anti-dragon shield's value is 0.** Implemented in
  `scripts/build_price_tables.py`, which reads `ge_blocked_items` from
  `rl.conf` so the server rule is the single source of truth. GE-blocked
  items get no GE term in the valuation and are left off the frozen buyer's
  list (6,068 rows listed). Only the two shield rows of `prices_v2.csv`
  changed.
- **Start building.** First module: game data plus the combat-rate model.

### Built
- `rlscape/gamedata/server.py` reads items (bonuses, attack speed,
  requirements), NPCs (stats, styles, immunities), drop tables (with the
  server's roll rules) and spawns from the fork's configs, plus values from
  `prices_v2`.
- `rlscape/combat/formulas.py` ports the server's swing handlers line by
  line: hit chance, player and NPC attack and defence rolls, melee / ranged
  max hits, and the modern spells' max hits. All 16 spell levels and base XP
  values were checked against the server.
- `rlscape/combat/rates.py` gives kills/hr, XP/hr per skill, gp/hr, damage
  taken per hour (mean and variance), and the danger filter.
- Tests: `tests/test_combat_formulas.py` checks hand-computed values,
  including 99 Strength max hits of 11 with no bonus and 19 with a rune
  scimitar. `tests/test_gamedata.py` checks the real configs. 11 passed.
- Rating all 2,120 spawned NPC types takes 26 ms, fast enough to recompute
  candidates every decision.

### Findings from running the model on real data (need decisions or fixes)
- **Placeholder NPC stats:** 911 of 2,120 spawned NPC types have exactly
  attack / strength / defence 1, 10 HP and no bonuses. That includes real
  monsters (ice trolls, goblin variants, guards), and the server fights with
  those values. Unfiltered, ice trolls rank at 130k gp/hr for a level-1
  character with food.
- **Non-attackable NPCs are in the pool.** Configs with lifepoints include
  pickpocket and random-event NPCs (Master Farmer, Frog 2689). Attackability
  lives in the cache definitions (the "Attack" option), which the Python
  side doesn't read yet.
- **gp/hr ignores inventory capacity.** For example, undead chickens show
  36.7k gp/hr of drops, but 3 drops per kill fill 28 slots in about 9 kills.
  With no auto-banking, candidate gp/hr needs the inventory-fill and
  bank-trip cycle.
- **The danger filter as decided is strict.** With expected damage over the
  full 15 minutes + 2σ ≤ HP + food, a fresh character with its starter food
  passes only 7 NPC types. Even cows deal about 75 damage over 15 minutes to
  a level-1 character, because the filter assumes the fight runs the full
  duration. Combat options already end on low HP and no food, though.
  Raised with Caleb.

### User decisions (2026-10-27, night)
- **Apply the planned fixes:** export cache NPC definitions and clean the
  enemy pool; make gp/hr inventory-aware; add the dragonfire gear check.
- **Danger filter: retreat-aware** (option (b)), replacing the full-duration
  version (a).
  - A monster qualifies if two of its max hits stay below half the
    character's max HP (no burst from the retreat point).
  - And the damage taken during one kill + 2σ fits in the HP above half plus
    the food carried.
  - `Rates.passes_retreat_filter`. A fresh character with starter food now
    passes cows: a 13 HP budget against about 7 ± 2.3 taken per kill.

### Built
- **Fork bridge:** `item_definitions` gained `stackable`. The new
  `npc_definitions` returns every cache NPC definition (name, cache combat
  level, "Attack" option, size). Exported to `data/item_definitions.csv`
  (only the new column added; 3,755 stackable) and `data/npc_definitions.csv`
  (7,887 named NPCs, 2,717 attackable).
- `rlscape/combat/candidates.py`:
  - **Enemy pool:** attackable in the cache, stats believable against the
    cache combat level, unkillable dummies 4474 / 7891 excluded. 1,058
    entries, 403 distinct monsters.
  - **Sites:** one per map region, each with its nearest bank from the
    curated `data/banks.csv` (20 banks, approximate, to verify).
  - **Loot modes and the inventory cycle:** stackables, including summoning
    charms, cost no slot.
  - **Dragonfire / wyvern gear check:** ids from the server's NPC classes.
  - **Selection:** 3 best by XP/hr + 3 best by gp/hr per class, with
    duplicate names merged.
- `rlscape/combat/rates.py`: per-kill damage moments and the retreat-aware
  filter.
- Tests: `tests/test_candidates.py` (7), with 18 passing across the combat and
  game-data tests.

### Findings
- **Most of the placeholder-stat NPCs** (911 of 2,120 spawned) **aren't
  attackable**: bankers, shopkeepers. Among attackable spawned NPCs, only 11
  carry the placeholder signature. The "believable stats" rule flags 124, most
  of them stats far weaker than the cache level (e.g. zombies at levels 90–100
  with stats worth about 10).
- **The access table is the next blocker.** With gating not yet modelled, a
  fresh character's top gp/hr slots are monsters in gated areas: Cockroach
  drones (Stronghold of Player Safety), undead chickens and cows and Blamish
  snails (Morytania, behind Priest in Peril), Scabaras lancers (Contact!). The
  drop values themselves check out against the server's tables.
- **Cows have spawns in Zanaris** (Lost City), whose coordinates don't follow
  the 6,400-tile dungeon offset. Another case for the access table.
- **A fresh character's XP slots look right** (Rat, Man, Ram). From Lumbridge,
  the cows chosen are Lumbridge's (a 22-tick walk, a 113-tick bank trip).
- **Corrected a test-input slip:** 15 game-minutes is 1,500 ticks, not 9,000.
- **Ranking cost:** 60–100 ms for every monster and plan. That's fine for the
  server, but the simulator will need caching by character state.
- **Poison** damage isn't in the estimate yet (catalog §4.B says so).

## 2026-10-28

### User decision (morning)
- **Work on the access table** (option catalog §4.C), the blocker found the
  night before.
- **The Wilderness is in the enemy pool** (asked during the work; Claude
  recommended including it). PvP is off in `rl.conf` and training has no other
  players, so its monsters go through the same danger filter. The simulator
  must model the harsher death there: all but 3 items lost, no gravestone.

### Built
- `data/access_areas.csv` (55 curated rules) and `rlscape/combat/access.py`.
  - Each rule is a gated area (a rectangle) or a set of quest-only NPCs, with a
    requirement in a small grammar: quest / started / underway / item / level /
    coins / never.
  - The rules are checked against the character's `Progress` every decision; a
    site only counts if every rule covering it is unlocked.
  - `unlocked_rules(progress)` is the observation's access-flag vector.
- `rlscape/gamedata`: `slayer_levels()` parses the server's `Tasks.java` (all
  93 tasks, 1,127 NPC ids; the first task listing an id wins, as in
  `Tasks.forId`). `quest_names()` parses `Quests.kt`, so the table's quest names
  are validated against the server.
- `candidates.evaluate` applies the Slayer level and the access table before
  rating a monster. `Character.progress` defaults to a fresh character.
- Tests: `tests/test_access.py` (7). 25 pass, and 13 live tests are skipped.

### How the rows were chosen
- A sweep ran the candidate selection with every area open, over:
  - levels 1–99 with matching melee, ranged and magic gear
  - 18 hub towns
  - the "valuable" and "all" loot modes
- It collected every monster that reached a top-10 slot: 573 monster sites in
  202 map regions.
- Each surfaced site was checked against the server code:
  - `MapArea` borders
  - quest checks in the door, ship, ferry and dialogue handlers
  - the quest folders
- Then the table was built and the sweep re-run with the real 3 + 3 slots
  until only open-world monsters surfaced.

### Findings
- **The server doesn't enforce Slayer levels.** `NPC.isAttackable` (and
  `IdleAbstractNPC`) prints "You need a higher slayer level to know how to
  wound this monster" but has no `return false`, so a Slayer-1 character can
  fight abyssal demons. The candidate filter applies the 2009 rule on both
  backends. A one-line fork fix would make the server match; that's for Caleb
  to decide.
- **Many 2009 gates have no server check:** Ape Atoll, the Lighthouse, the
  Kalphite Lair rope, Entrana, Trollheim and others. Their rows say "not
  enforced by the server". The table still applies them, because both
  backends get their candidate list from it.
- **The server's Morytania borders start at x 3426,** but the River Salve runs
  at about x 3405. The strip in between holds Mort Myre's west edge, the Slayer
  Tower's west side and the Haunted Mine. Three rows cover it; the Paterdomus
  temple (reachable from the west) is left out.
- **Mighty banshees aren't in `Tasks.java`** (only the ordinary banshee, 1612,
  is). The table adds the 2009 Slayer-15 requirement.
- **Fresh character at Lumbridge, melee:** the gp/hr slots went from Cockroach
  drones (46,000 gp/hr), undead chickens and undead cows to cow calves, bats
  and cows (5,900–7,600 gp/hr). The XP slots are unchanged.
- **Gaps left for calibration:**
  - the entry fees (Brimhaven 875, Waterbirth 1,000) gate access but aren't
    charged in the rates yet
  - separate maps at y ≈ 4,000–6,400 (Zanaris, the God Wars Dungeon, the Chaos
    Tunnels) only stay out because the travel model puts them far away
  - Colonel Radick (1/1/1 stats, 71 HP) slips past the believability rule
  - light sources and Slayer gear aren't modelled
  - areas missing from the table count as open

### User decision (afternoon, Slayer fix)
- **Apply the Slayer fix in the fork, and commit everything.**

### Built
- Fork: `NPC.isAttackable` and `IdleAbstractNPC.isAttackable` now
  `return false` below the NPC's Slayer level. Before, they only printed the
  warning. The rule applies to every player, including the ambient bots.
- Fork: the bridge's `state` reports the character's combat `target` (the
  victim's name while attacking, otherwise null). The test needed it, and
  `ServerEnv` will too.
- `tests/test_human_player_live.py::test_slayer_level_blocks_attacks`:
  teleport a fresh character among the cave crawlers (Slayer 10, Fremennik
  Slayer Dungeon), attack, and expect no combat target.

### Validation
- **Reproduced before fixing:** on the unfixed build, the test failed with
  `target == 'Cave crawler'`.
- **After the fix:** the test passes. The full suite with the live server
  gives 39 passed, all 14 live tests included. `scripts/gate_check.py` passes:
  - G1: world speed 34.6× at 15 ms per tick
  - G2: a fresh character chops 10 logs for 250 Woodcutting XP
- The clean frozen GE database was reinstalled afterwards.

### Documentation audit and fixes (afternoon)
- **Audit** (`m002-documentation-audit`), read-only. It checked every doc
  against the code, the config, git, the logging policy and the session
  transcript, which has an instrumented timestamp for every prompt.
- **Caleb's decision: apply the fixes and commit everything**
  (`m002-doc-fixes-and-commit`):
  - **Records:**
    - every timestamp now comes from the transcript, with the old estimate
      kept in a note; nine estimates had been off by 4–10 minutes, and two
      records used "CDT" instead of the policy's CST label
    - "the commit that adds this record" now carries the SHA
    - the five PARTIAL records point to where their open questions were
      resolved
    - the missing record for the 2026-10-27 commit-and-push turn was written
      (`m002-commit-and-push`)
  - **`env-contract.md` §8** no longer claims respawn waits, consumables or
    entry fees are in the rates; they're marked "not yet".
  - **`ROADMAP.md`:**
    - the policy reference
    - the architecture box and the bridge protocol as built
    - the repo layout, marking what's built
    - the week-1 economy items and doc versions
    - Appendix A marked superseded
    - the answered open questions
    - a note that the weekly rhythm (§6) isn't followed; keeping it is
      Caleb's call
- **Still open, from the audit:**
  - sign-off of both docs and the loot-mode design
  - a PR for `env-contract-and-combat-model`
  - the week-2 build items
  - the combat-model gaps (poison, respawn, consumables, fees, Wilderness
    death, the separate maps, Colonel Radick)
  - calibration and verification items
  - binding the game port to localhost
  - citations for the access rows that rest on 2009 knowledge

### User decisions (afternoon, open-questions review)
Caleb accepted all nine recommendations
(`m002-open-decisions-accepted`):
1. **Signed off** `env-contract.md` and `option-catalog.md`, both now
   **v1.0**. Later changes need Caleb's approval and get logged here. The item
   vocabulary is chosen by the agreed rule, and Caleb checks the list.
2. **Loot modes approved** (catalog §4.D): four modes the agent sets (all,
   valuable, vocabulary, none).
3. **Death:** the character respawns in Lumbridge and the episode carries on.
   Ported from the server (`DeathTask.getContainers`, `GraveController`,
   `GraveType`):
   - the 3 most valuable items by alchemy value are kept (none if skulled,
     plus one with Protect Item)
   - outside the Wilderness, everything else goes into a 2-minute gravestone
     (200 ticks, the free memorial plaque); a new `reclaim_gravestone` option
     recovers it if the walk back fits in that time
   - in the Wilderness or when skulled there's no gravestone, and everything
     else is lost
   - the catalog grows to about 452 actions
4. **Open a PR** for `env-contract-and-combat-model`. Caleb merges it after
   review, and the simulator starts on a fresh branch.
5. **Weekly rhythm trimmed** to a 5-line Friday status entry here (done,
   blocked, changed, next, risks). No Monday goal entries or `wkN` tags.
6. **The game port is bound to localhost.** New fork setting
   `server.bind_address` (default `0.0.0.0`, as upstream); `rl.conf` sets
   `127.0.0.1`. Verified: `netstat` shows `127.0.0.1:43595 LISTENING`, and the
   full suite with the live server gives 39 passed.
7. **E7 is tentatively A, the LLM planner.** It's confirmed at the week-5
   midpoint, and only if E1–E6 are solid.
8. **Singleplayer client:** deferred to week 7, for the replay recording.
9. **Both repos stay private** for now. Revisit if the course submission
   needs public links.
- **Correction (same afternoon):** PRs #2 and #3 from
  `env-contract-and-combat-model` had already been merged by Caleb
  (2026-10-27 21:25:55 and 2026-10-28 13:54:12 CST). The audit's "a PR is
  still open" item, and recommendation 4 built on it, were wrong, because the
  audit never checked GitHub. The commits since #3 (the doc fixes, these
  decisions, and this correction) go in PR #4. Lesson: check `gh pr list`
  before reporting PR state.

### User decision (afternoon, repositories)
- **Merge upstream 2009Scape and clean up the branches**
  (`m002-upstream-sync-and-branch-cleanup`), after a check of both repos
  found everything in sync except local `main` (fast-forwarded) and found
  upstream 8 commits ahead.
- **Upstream sync:** fork `master` moved to upstream `f279da8`, and merged into
  `rl` as `1f8665b`, which is clean because none of the 8 commits touch files
  changed on `rl`. Relevant to the project:
  - the ranged-ammunition drop-pile fix (`GroundItemManager`)
  - five repaired map areas in the cache (4 LFS files)
  - the rest is minor: poisoned dragon darts and arrows, a Gnomecopter deposit
    box, a blurite crossbow fix, dart feathers, brewing offline catch-up, and
    a house-amulet menu
- **Validated on the merged build:**
  - full suite with the live server: 39 passed
  - gates: G1 34.3× at 15 ms; G2 10 logs and 250 XP
  - the game port is still `127.0.0.1:43595`
  - re-exporting the item and NPC definitions left `data/` byte-identical
    (7,324 items, 7,887 NPCs), so the cache update changed no game data the
    model uses
- **Pushing needed every intermediate LFS object:** fetching only the tip's
  objects left one version of `main_file_cache.dat2` missing, and the push
  was rejected. `git lfs fetch --all upstream` fixed it (6 objects, 184 MB
  uploaded). CLAUDE.md now says so.
- **Branches:** `env-contract-and-combat-model` and
  `ge-frozen-buyer-random-events` were deleted locally and on GitHub, after
  checking both were fully merged into `main` (PRs #4 and #1). The submodule
  bump goes on `sync-upstream-2009scape`.

### User decisions (afternoon, simulation review)
`m002-simulation-decisions`. Three rounds of questions. The env contract and
option catalog are now v1.1.

**Simulator:**
1. **Event-level sampling** (recommended). Sampled per event:
   - resources gathered over N ticks: one binomial draw
   - each kill's duration and damage
   - each drop roll
   - eating and death checked kill by kill

   Rejected: expected values only (no risk) and tick-level simulation (too
   slow for 20k decisions/s).
2. **Staging** (recommended): sim v0 covers everything except the quests;
   all 21 quests come in sim v1, before E2.
3. **Five more trainable skills.** Caleb asked why only 14 skills were
   trainable. Claude explained that it had scoped the list itself on Oct 5,
   from the proposal's examples, and never asked; sign-off only accepted it
   implicitly. Total level sums all 24 skills, and untouched skills give
   the cheapest early levels. Decision: **add Fletching, Crafting, Agility,
   Herblore and Runecrafting in sim v1**, for 19 trainable. Farming,
   Construction, Summoning, Hunter and Slayer tasks stay out, as a stated
   limitation.

**Server:**
4. **Ambient bots off** for calibration and E6 (recommended).

**Calibration:**
5. **The gate:** ±20% on mean XP/hr, gp/hr and duration per calibrated
   option (recommended), with one patch round; residual gaps are reported.
6. **Calibration characters,** Caleb's own design, refined over two rounds.
   Claude flagged blind spots before the second round:
   - untrainable skills
   - gear
   - bands that can't be reached
   - grid size
   - side effects of debug-completed quests
   - self-crowding
   - testing only the diagonal

   The design:
   - **Bands:** fresh, 11, 21, 31, 41, 51, 61, 71, 81, 91, 99. Caleb kept
     all 11, though Claude noted 81–99 can't be reached in 20 hours.
   - **Skills:** trainable skills at the band, the rest at 1.
   - **Gear:** non-fresh characters get the starter kit and
     100 gp × total level, and buy their own gear on the GE.
   - **Quests,** cumulative: 11–21 the four starter quests; 31–41 adds the
     rest of the 32-quest-point route; 51+ all 21, including Dragon Slayer.

**Baselines:**
7. **Scripted-guide baseline** (recommended): Claude drafts it from archived
   2009 guides, cites them, and Caleb reviews it before E1.

**Agent defaults (reversible; Caleb can object):**
- **Calibration runs:** each option at the bands where it's unlocked, about
  10 runs each; parallel characters never share a spot.
- **Buying rule for calibration characters:** the tool for the calibrated
  option, then the weapon, then armour by defence per gp, within level and
  quest requirements.
- **Ported from the server:** resource depletion and respawn, HP regeneration,
  and eating. Travel stays on the current model until calibration.
- **Speed:** candidate ranking is exact, made fast with caching and
  vectorisation, not approximated.
- **GE purchases** are collected to the bank, which matches the server
  executor's path.
- **The RL stack** is installed when SimEnv is wired up: CPU PyTorch for PPO,
  CUDA later only if Envelope Q or the stretch needs it.

**For Caleb to review later:**
- the item vocabulary list
- the scripted-guide routine
- the five new skills' options (catalog v1.2)

### Built (afternoon): sim v0, first slice
`m002-sim-v0-core-and-woodcutting`, on branch `sim-v0` (the merged
`sync-upstream-2009scape` branch deleted first; the simulation-decision docs
committed as `493af16`).
- `rlscape/sim/`:
  - `skills.py`: the 24 skills in the server's order; XP and levels from
    `Skills.getExperienceByLevel`, line for line; the skill measure that
    r_skill rewards
  - `state.py`: the character, with inventory stacking rules, bank,
    equipment, location, access progress and net worth
  - `options.py`: the option interface and the termination reasons
  - `engine.py`: `Simulator.reset` and `step`, which handle the time budget
    (D or what's left of the horizon), truncation, the reward vector, every
    contract `info` field and checkpoints
  - `woodcutting.py`: the first family
- **Woodcutting,** ported from `WoodcuttingListener`:
  - a swing every 3 ticks, succeeding with `getSkillSuccessChance` over the
    tree's bounds plus the axe's enum ordinal (halved for black)
  - normal trees fall after every log, others 1 time in 8
  - respawns from `getRespawnDuration` with one player online
  - the axe chosen by `SkillingTool.getHatchet`'s priority
  - sampled log by log: one geometric draw of swings per log, one Bernoulli
    for the fall; the level is re-read after every log
- **New gamedata parsers,** reading the server source:
  - `starter_kit()` from `CharacterDesign`
  - `tree_types()` from `WoodcuttingNode`'s switch, including fall-through
    labels and the never-falling `respawnRate = -1`
  - `skilling_tools()` from `SkillingTool` (all 36 constants, so the
    ordinals are right)
- **Refactor:** `rlscape/travel.py` now holds the travel model shared by
  combat and gathering; `candidates` imports it.
- **Dependency:** `numpy` (2.5.4) added, the first piece of the RL stack.
- **Tests:** `tests/test_sim.py` (10). Full suite: 35 passed, 14 skipped.

### Findings
- A fresh character fills its 10 free slots with logs in 197 ticks (walk
  included) and reaches Woodcutting 3. That matches the server's G2 gate,
  which gave the same 10 logs and 250 XP. The 18-item starter kit leaves only
  10 free slots, so banking or dropping starter items comes up early for the
  agent.
- **Speed:** about 5,700 woodcutting decisions/s on one core, reset
  included, so roughly 90k/s across 16 workers against the 20k target.
  Combat ranking is the expected bottleneck.
- **Still estimates:** the Lumbridge, Draynor-oak and Edgeville-yew tiles
  and all tree counts (the willow tile comes from the `DraynorWillows` bot).
  The server ships no scenery data, so a bridge export of scenery near each
  site is the planned source. Bird nests (1 in 282 logs) aren't modelled yet.

### Built (afternoon): sim v0, mining and fishing
`m002-sim-v0-mining-and-fishing`. The woodcutting slice was committed first
(`f2baf2c`).
- **Mining**, ported from `MiningListener`:
  - an attempt every 4 ticks (`getDelay`)
  - success is `Math.random()·100·rate < Math.random()·(1 + level − rock
    level)·(1 + pickaxe ratio)`, computed exactly as a race between two
    uniform rolls
  - every ore empties its rock, which respawns after `getRespawnDuration`
  - a gem 1 time in 282 (`roll`), uniformly one of four, because
    `GEM_REWARDS.random()` ignores the frequencies listed beside them
  - the pickaxe chosen by `getPickaxe`'s priority
- **Fishing**, ported from `FishingListener`, `FishingOption.rollFish` and
  `FishingNPC`:
  - an attempt every 5 ticks
  - the method's fish are rolled in order with `Fish.getSuccessChance`
    (linear in level), and the first that passes is caught (rainbow fish only
    with stripy feathers)
  - one bait per catch
  - spots move every `random(200, 390)` ticks among their `FishSpots` tiles,
    and the angler walks after them
  - sampled as one geometric draw for any catch and one categorical draw for
    which fish, with the server's sequential weights; redrawn after a spot
    move, since geometric waits are memoryless
- **Shared gathering loop** (`rlscape/sim/gathering.py`): sites of depleting,
  respawning resources, now used by woodcutting and mining. Woodcutting was
  refactored onto it, and its 10 tests still pass.
- **gamedata:**
  - one parser for the node enums' `switch(identifier & 0xFF)` blocks,
    across several constructors, with `identifier == N ? a : b` resolved per
    label. It now covers `WoodcuttingNode`'s farming-tree constructor (ids
    19–23), which a first draft missed.
  - new: `rock_types()`, `fish_types()`, `fishing_methods()`,
    `fish_spot_locations()`
- **Tests:** `tests/test_sim_gathering.py` (8). Full suite: 43 passed, 14
  skipped.

### Findings
- **Sources for the sites:**
  - from the server: fishing spot tiles (`FishSpots`) and the coal tile (the
    `CoalMiner` bot's Dwarven Mine zone)
  - still estimates: the copper, tin and iron tiles, and every rock count
- **A fresh character** (bronze pickaxe and small net) can chop logs, mine
  copper and tin, and net shrimp: 10 copper in 282 ticks, or 10 shrimp in
  444 ticks, walks included.
- **Speed:** about 5,600 mining and 2,900 fishing decisions/s on one core,
  reset included.

### Built (late afternoon): sim v0, pickpocketing and hitpoints
`m002-sim-v0-pickpocketing`. The mining and fishing slice was committed first
(`ae0cb7e`).
- **Pickpocketing** (`pickpocket_men`), ported from `ThievingListeners` and
  `Pickpockets`:
  - success when `randomDouble(1, 100) <= getSkillSuccessChance(low, high,
    level)`, i.e. p = (T − 1) / 99
  - a success gives 3 coins and 8 XP with a 2-tick lock
  - a failure gives a 5-tick stun and `random(1, 1)` = 1 damage
  - sampled as runs of successes ended by a failure, one geometric draw each
  - the site is the server's Man spawn nearest the spawn point, (3230, 3238)
- **Hitpoints** (`rlscape/sim/health.py`), shared with combat later:
  - regeneration from `SkillRestore`: one HP every **101** ticks (its check
    is `++ >= 100`), on a cycle carried across options
  - eating from `ConsumableListener` (2 ticks per bite) with heal amounts
    from `Consumables` (102 single-bite foods)
  - the retreat rule: eat at or below half HP, cheapest food first, and stop
    when the food runs out
  - the engine applies regeneration for options that don't handle HP
    themselves
- **gamedata:** `pickpocket_targets()` (17 targets with loot tables) and
  `food_healing()`.
- **Tests:** `tests/test_sim_thieving.py` (8). Full suite: 51 passed, 14
  skipped.

### Findings
- **A fresh character** pickpockets 27 times (81 coins, Thieving 1→4), eats
  its shrimp and bread, and stops out of food at half HP after 135 ticks. The
  option is then masked until HP regenerates or food is bought, which is the
  first real economy and health trade-off the agent meets.
- **Speed:** about 1,500 decisions/s on one core for a full 15-minute option
  (about 150 events). That's about 24k/s across 16 workers, so it's the
  first family near the target; vectorising it is the fallback.
- **Death** isn't modelled yet. Pickpocketing men can't kill (1 damage, stop
  at half HP), and the option raises if a hit ever would. The death rule
  arrives with combat.
- **Only fixed, always-dropping, stackable loot** is modelled. Targets with
  weighted or non-stackable loot raise until their table rules are ported.

### Built (late afternoon): sim v0, processing
`m002-sim-v0-processing`. The pickpocketing slice was committed first
(`32f4ed3`). Catalog §3's nine options, ported from the server's pulses:
- **Smelting** (`SmeltingPulse`, `smelting.Bar`):
  - a bar every 5 ticks; the ores are used either way
  - iron succeeds half the time (`nextBool`)
  - XP only on success (bronze 6.2, iron 12.5, steel 17.5)
- **Smithing** (`SmithingPulse`, `Bars`, `SmithingType`, `BarType`):
  - an item every 4 ticks after a first tick, with a hammer
  - each item uses its type's bars and gives the bar type's XP per bar
  - "best item" means the most bars per item the level and bars allow, then
    the most valuable per bar; leftover bars go into the next best that fits
  - dart tips and claws only after The Tourist Trap and Death Plateau, as
    the pulse checks
- **Cooking** (`StandardCookingPulse`, `CookableItems`):
  - an item every 5 ticks on a range
  - burnt if `randomDouble(100) > getSkillSuccessChance`, with the range's
    bounds; the Lumbridge castle range (object 114) needs Cook's Assistant
    and has its own bounds
  - anything `CookableItems` turns into food is cooked
- **Firemaking** (`FireMakingPulse`, `firemaking.Log`):
  - a light attempt every 3 ticks with the server's ceil formula against
    `random(99)`
  - a log lit within 2 ticks of the last fire lights at once
    (`setLastFire`), so a line of fires rolls only for the first log
- **Burying bones** (`BoneBuryListener`, `Bones`): a bone every 2 ticks.
- **Stations:** `data/stations.csv` (new, curated) with 4 furnaces, 2 anvils
  and 3 ranges. Three tiles come from server code (the Lumbridge and
  Edgeville furnaces, the Varrock south-east anvil, all from diary checks);
  the rest are estimates. An option uses the nearest station the character
  can reach.
- **gamedata:** `smelted_bars()`, `smithables()` (all 157 `Bars` entries),
  `cookables()` (with `lumbridgeRangeValues`), `log_types()`,
  `bone_experience()`, `stations()`.
- **Tests:** `tests/test_sim_processing.py` (9). Full suite: 60 passed, 14
  skipped.

### Findings (need calibration)
- **Firemaking is very fast.** Because of the 2-tick relight, 10 normal logs
  burn in 21 ticks (400 XP), about 114k Firemaking XP/hr even at level 1, and
  willows would give about 160k/hr. That is the server's code as written,
  ported faithfully. It's the first thing to check on the server
  (`CHAIN_TICKS`), because if it holds, burning logs will dominate the skill
  reward.
- **Cooking without Cook's Assistant goes to Al Kharid's range.** The Al
  Kharid toll gate (10 gp, or Prince Ali Rescue) isn't modelled, and the
  range tiles are estimates.
- **Fresh characters can't smith yet:** the starter kit has no hammer, so
  buying one is the first economy dependency.

### User decisions (late afternoon, after the processing slice)
`m002-al-kharid-toll`.
- **Firemaking's speed is normal** (Caleb). In 2009 it was seen as a
  do-nothing skill that unlocks nothing, and burned logs give nothing back.
  The model already reflects that: logs leave the inventory with no product,
  so net worth falls by their value and the wealth reward charges for it.
  No calibration flag.
- **Model the 10 gp Al Kharid toll** (Caleb). Built in
  `rlscape/sim/movement.py`, and every option now walks through it:
  - the server's rules (`TollGateOptionPlugin`, `BorderGuardDialogue`): 10
    coins from the inventory each time the gate is passed, in either
    direction; free once Prince Ali Rescue is past stage 50, counted here as
    complete
  - a walk uses the gate when one end is inside Al Kharid and the other is
    west of the fence, south of its north end
  - without 10 coins in the inventory, the walk goes round the fence's north
    end instead (as players did via the Al Kharid mine): slower, never
    stranded
  - nearest-station choices count the route, detours included
  - the fence line and its north end are estimates to verify on the server
- **Tests:** `tests/test_sim_movement.py` (6). Full suite: 66 passed, 14
  skipped.
- Work pauses for a few hours after this commit.

### User correction (late afternoon): cooking on fires
`m002-cooking-on-fires`.
- **Caleb: most food doesn't need a range; it cooks on a fire the player
  lights.** The server agrees:
  - `StandardCookingPulse` handles fires: 4 ticks an item instead of 5, with
    each food's fire bounds
  - `CookingRewrite` requires a range only for bread dough, uncooked cake
    and barley
- **Built:** `cook_fish` now lights a fire where the character stands when
  it holds a tinderbox and a log it can light:
  - it burns the cheapest such log with the firemaking roll and gains its
    Firemaking XP
  - the fire lasts `Log.life` ticks (180+), which outlasts a full inventory
  - it cooks there at the fire rate and bounds
  - range-only food, or everything when no fire can be made, still goes to
    the nearest range
- **gamedata:** `log_fire_ticks()`.
- **Effect:** at the Draynor fishing spot, 10 raw shrimp now cook in 44 ticks
  with no walk and no toll; the range route took over 95 ticks plus the toll.
  Fishing then cooking on the spot, the classic 2009 loop, is now cheap, and
  logs gain a use beyond burning or selling.
- **Tests:** 3 more in `tests/test_sim_processing.py`. Full suite: 69
  passed, 14 skipped.

### Built (evening): sim v0, inventory, alchemy and selling
`m002-sim-v0-inventory-and-selling`. Caleb: "Continue work on the project.
Try to avoid things that need my approval for now." So nothing is committed
or pushed, nothing changes in the fork, and the item vocabulary stays out of
the catalog.
- `rlscape/sim/economy.py` (catalog §5–§7):
  - **`bank_deposit`:** walk to the nearest bank and deposit everything except
    tools, food, ammunition, runes and fishing bait; banknotes go in as their
    items
  - **`bank_withdraw_for_<activity>`** (9): the activity's tool if missing,
    then its inputs in proportion up to a full inventory; for cooking, one log
    as well to make a fire
  - **`drop_<item>` / `drop_misc`:** dropped items leave net worth and are
    reported in `items_delta["dropped"]`
  - **alchemy** from `ModernListeners.alchemize`: low (Magic 21, 3 fire + 1
    nature, 31 XP) and high (Magic 55, 5 fire + 1 nature, 65 XP), 5 ticks a
    cast, the export's alchemy values, fire staves (`MagicStaff.FIRE_RUNE`)
    replacing fire runes
  - **`sell_ge_*`:** the frozen buyer pays the 2009 price for items that have
    one, and GE-blocked items never sell
  - **`sell_store_*`:** the nearest general store pays `Shop.getGPSell`'s low
    alchemy minus 3% of value per unit of overstock (at most 10), unit by
    unit, never below 1 coin
- **Vocabulary handling:** `build_catalog(vocabulary=...)` builds the per-item
  actions for any vocabulary. The default is empty, so the catalog carries
  only the misc actions until Caleb checks V. "Misc" means outside V and
  never coins or what banking keeps.
- **gamedata:** `alchemy_values()`, `unnoted_ids()`, `fire_staves()`,
  `ge_prices_2009()`, `item_base_values()`. `data/stations.csv` gains 4
  general stores (estimates).
- **Engine:** reports drops; "completed" now also means a one-shot option
  finished.
- **Tests:** `tests/test_sim_economy.py` (12). Full suite: 81 passed, 14
  skipped.

### Agent choices (reversible; for Caleb's review)
- Fishing bait is kept on deposit along with the catalog's list, treated as
  an activity's ammunition.
- A general store is assumed to start each sale at its normal stock;
  player-sold stock drains back between visits on the server.
- Timings to calibrate: 1 tick per unit dropped, 8 ticks per GE trip, 3 ticks
  per store sale.
- **Buying isn't built.** The catalog fixes its groups and sources, but the
  concrete actions ("best affordable food, up to 100", which tiers), where
  purchases land (inventory or bank), and whether bought gear is wielded are
  design calls for Caleb. A draft comes for his review.

### Built (evening): sim v0, combat part 1 (melee fights, drops, death)
`m002-sim-v0-combat-melee`, continuing under "avoid things that need my
approval".
- **Two fixes to the drop model, both bringing it in line with the server**
  (they change the candidate rates slightly):
  - **Amounts exclude the upper bound.** `WeightedItem.getItem` draws
    `random(min, max)`, which never returns max, so the mean is
    (min + max − 1) / 2; it was (min + max) / 2. That affects 882 entries.
  - **Placeholder ids aren't items.** 477 entries point to sub-tables: the
    rare drop table (31), herbs, gems, seeds, clues (`SPECIAL_DROP_SLOTS`).
    They had counted as items and as inventory slots; they now count as
    nothing until the sub-tables are ported, which understates some
    monsters' loot.
- **`rlscape/sim/equipment.py`:**
  - a fighter's bonuses come from what's worn
  - `wield_best` puts on the best weapon for the combat class (scored as
    (attack + 64)(strength + 64) / speed for melee, matching the server's
    formulas) and the best armour per slot
  - equip requirements from the item configs and quest locks from
    `ItemQuestRequirementListener` are respected (134 items: rune
    platebodies and green d'hide bodies need Dragon Slayer, the dragon
    scimitar Monkey Madness, ...); a two-handed weapon empties the shield
    slot
- **`rlscape/sim/combat.py`:**
  - **`fight`:** walk, wield, then kills until the budget, a full inventory,
    out of food, or death. Each kill samples its cumulative-damage sequence
    (one vectorised draw), and the monster's swings resolve one by one with
    eating (3 ticks of attack delay a bite) and the retreat rule (2 escape
    swings). A retreat or death mid-kill charges the time fought and the
    XP for the damage dealt. XP is 4/damage to the style skill and 1.33 to
    Hitpoints; drops go through the loot mode.
  - **`roll_drops`:** `WeightBasedTable.roll`.
  - **`die`:** your death rule, ported from `DeathTask`, `GraveController`
    and `GraveType`: keep the 3 highest high-alchemy items, the rest into a
    200-tick gravestone (or lost in the Wilderness, whose borders are
    `WildernessZone`'s five rectangles), and respawn at full HP at rl.conf's
    `home_location` (3222, 3218).
  - **`reclaim_gravestone`:** available only while the walk beats the
    timer; the engine clears expired gravestones.
- **gamedata:** `equip_quest_locks()`. The rate model's offence helpers are
  now public (`player_offence`, `npc_offence`).
- **Tests:** `tests/test_sim_combat.py` (9). Full suite: 90 passed, 14
  skipped.

### Findings
- **Sampled kill times match the rate model:** 135.5 against 134.1 fighting
  ticks per cow for a fresh character.
- **A fresh character can't sustain cows.** The server's formulas give cows
  a 52% chance of hitting it, about 7 damage per kill, so with 10 HP and
  the starter food it manages about 1.6 cows before stopping out of food,
  in every one of 200 runs, with no deaths. A level-30 fighter fills its
  inventory with hides in about 300 ticks.

### Agent choices (reversible; for Caleb's review)
- Combat options wield the best gear carried automatically (1 tick an item,
  to calibrate).
- Quest locks that only check "underway" are read as "complete".
- Protect Item isn't modelled, and stacks count as one unit when choosing
  the 3 kept items.
- Items that don't fit when reclaiming a gravestone are left behind.

### Still to come in combat
- Ranged (arrows in the ammunition slot, ammunition use) and magic (runes per
  cast).
- The candidate-slot actions. Ranking takes 60–100 ms and the mask needs it
  every step, so this needs vectorising and caching first.
- The four loot-mode actions; poison; respawn waits; the sub-tables.

### Built (evening): fast candidate ranking
`m002-fast-candidate-ranking`.
- **Profiling** one full ranking (3 classes, 5 plans, 1,058 pool entries)
  took 89 ms:
  - about half went to `loot_per_kill` rebuilding each monster's
    expected-drop dictionary on every call
  - about a fifth went to `combat_rates`
  - neither changes as the character moves
- **`rlscape/combat/ranking.py` (`CandidateRanker`):**
  - **cached:** rates per (fighter, plan), loot per (loot mode,
    vocabulary), access and Slayer per progress, and the gear check per
    shield
  - **vectorised over all sites with numpy:** walking time, the
    inventory-cycle share, the filters, best site per monster, best plan,
    one per name, and the 3 + 3 picks
  - `candidates.select_candidates` stays as the reference
- **Result:** about 1.3 ms per full ranking with a new location every call,
  about 70× faster. The ranking matches the reference exactly (ids, values,
  sites, training styles) in 18 of 18 cases across six characters,
  including all-zero gp ties, an underground start and no food. The
  reference's tie order (names first seen valid in pool order) is
  reproduced.
- **Tests:** `tests/test_ranking.py` (6 parametrised cases, warnings as
  errors). Full suite: 96 passed, 14 skipped.
- **Next:** the 30 combat-slot actions and the 4 loot-mode actions on top of
  the ranker, then ranged and magic fights.

## 2026-10-29

### Committed: economy, melee combat and fast ranking
Caleb: "Commit this and keep going with the combat-slot actions." Commit
`59d7a31` on `sim-v0` (not pushed) holds cooking on fires, inventory,
alchemy and selling, melee combat, the drop-model fixes and the fast
ranker, with their records. `m002-combat-slot-actions`.

### Built: the combat-slot and loot-mode actions
`m002-combat-slot-actions`.
- **`rlscape/sim/slots.py`:**
  - `CombatSlots` ranks once per state with the shared `CandidateRanker`
    and serves all 30 slot actions: their mask entries and their runs.
    - The fighter is the character after the fight's own wielding step
      (`wield_best` on a copy), so the ranking sees the gear the fight
      uses.
    - The ranking is cached on a fingerprint of everything it reads (tick,
      location, HP, XP, inventory, equipment, bank, loot mode, quests). The
      run after a mask check fights the candidate the mask showed.
  - `FightSlot`: ids `fight_<class>_<xp|gp><n>[_<style>]`, in the order
    melee slot by slot (accurate, aggressive, defensive), then ranged, then
    magic. Ranged and magic stay masked until those fights are built.
  - `SetLootMode`: `loot_all`, `loot_valuable`, `loot_vocabulary`,
    `loot_none`.
  - The catalog now has 71 actions: combat sits between processing and
    inventory, as in option catalog §9.
- **Access sees the whole state.** `CharacterState.access_progress()` adds
  items held (inventory, bank, worn), levels and coins to the quests.
  `access.relevant` reduces it to what the access table checks: the items
  and skills the rules name, and coins rounded down to the highest
  threshold reached. Access is unchanged, and the ranker's per-progress
  cache keeps hitting as items come and go.
- **`info["option"]`** now carries a fight's `target`, `target_name`,
  `style`, `site` and `kills`, as env contract §6 asks. This is through a
  new `OptionResult.detail`.
- **Speed:**
  - The first mask fills the caches (0.3 s per process).
  - After that, a decision costs a median of 1.1 ms for the mask and
    0.6 ms for the step.
  - Level-ups that change the fighter cost about 20 ms once (rates for the
    3 styles over 1,058 monsters).
  - Three random 20-hour episodes biased to combat ran 382 fights with no
    errors. The fights ended 162 out of food, 159 on time, 58 with a full
    inventory and 3 at the horizon.
- **Tests:**
  - `tests/test_sim_slots.py` (6):
    - the ids and their order
    - the slots equal the reference ranking for a hand-built armed
      character
    - per-style masking matches the filter, and bites with little food
    - a slot fights its monster with the chosen style
    - the loot mode is set by its action and used by fights
    - the slots follow the character
  - Two access tests in `tests/test_access.py`.
  - Full suite: 104 passed, 14 skipped.

### Agent choices (reversible; for Caleb's review)
- **A melee style is masked when it fails the retreat-aware filter on its
  own.** The slot's monster is ranked by its best style, but the filter is
  what makes starting a fight safe, so it's applied per action. With little
  food this often leaves one or two of the three styles.
- **Choosing the current loot mode is masked,** so the action is never a
  no-op. Setting a mode takes 1 tick, the minimum per decision.
- **Access counts coins and items in the bank as well as on hand.** This
  follows the access table's own "held" wording. There's no action to
  withdraw coins yet, so counting only coins on hand would lock Brimhaven
  and Waterbirth after any deposit. The fees still aren't charged.
- **Dragons only reach a slot if the shield the fight will wear protects.**
  The fight wears the best shield by defence, so a character holding a
  better shield as well as the anti-dragon shield won't see dragons. The
  ranking and the fight agree, which is conservative. Shield choice per
  target belongs with the quests slice, the only source of the shield.

### Next
Ranged fights (a bow, arrows in the ammunition slot, arrows used and
dropped) and magic fights (the best spell the runes allow, runes per cast),
which unmask the 12 ranged and magic slots. Then the Gymnasium layer.

### Committed: the combat-slot actions
Caleb: "Commit this and keep going with ranged and magic." Commit `bac2124`
on `sim-v0` (not pushed). `m002-ranged-and-magic`.

### Built: ranged and magic fights
`m002-ranged-and-magic`.
- **Read the server first:**
  - `RangeSwingHandler`: one shot per attack, the landing chance, rapid's
    1-tick saving
  - `ranged_weapon_configs.json` via `RangedConfigLoader`
  - `MagicSwingHandler`; `MagicSpell.addExperience` (the base XP on every
    cast, splash or hit)
  - `CombatPulse` (players cast every 5 ticks); `MagicSpell.meetsRequirements`
    (runes from the inventory; staves stand in)
  - the elemental spell registrations, `MagicStaff`, `Runes`
- **Server data parsed** (`rlscape/gamedata/server.py`):
  - `combat_spells` (16 spells; levels and XP match `formulas.SPELLS`)
  - `staff_runes`, `rune_ids`, `ranged_weapons`
- **Worn stacks:** `CharacterState.worn_amounts` holds arrows and bolts in
  the quiver and thrown weapons, with `worn()` and `use_worn()`. Net worth and
  death count them in full; wielding 25 arrows would otherwise have read as
  a wealth loss.
- **Gear** (`rlscape/sim/equipment.py`):
  - ranged kits: a bow or crossbow with ammunition it accepts, a thrown
    weapon (its own ammunition), or a crystal bow
  - the best kit by damage per tick; stacks go on whole and top up
  - thrown weapons ignore the quiver's ranged strength, as in the server
  - **Fixed:** wielding a two-handed weapon with a full inventory could
    make the shield vanish, since `state.add` silently drops what doesn't
    fit. Now nothing is wielded without room for what comes off.
- **Fights** (`rlscape/sim/combat.py`):
  - **Ranged:** one shot from the worn stack per attack. A shot lands with
    1 − 1/⌊5·(1 + Ranged/100)⌋ (4 in 5 at level 1) and is picked back up when
    the loot mode takes arrows.
  - **Magic:** runes paid per cast (a worn elemental staff stands in for its
    own), and the spell's base XP on every cast.
  - **Ending:** `out_of_ammo`, charging the attacks made.
- **Ammunition in the ranking:**
  - A candidate's share of the option is now capped by how long the arrows
    or runes last (`Character.attacks_held`, `Rates.attacks_per_kill`), in
    both the reference and the fast ranker, as catalog §4.A's "current ...
    ammunition" asks.
  - Without the cap, Ram topped a fresh character's magic slots at
    8,760 XP/hr though the 15 starter casts last 75 ticks. With it, the slots
    are rats, gnome children and men at about 590 XP/hr over the option.
  - The fast ranker still matches the reference in all 8 cases, including
    two new ones with finite ammunition.
- **Slots:**
  - Ranged slots rank the accurate, rapid and longrange styles; magic slots
    use the best spell.
  - Each class is ranked for the character armed for it: its own gear,
    shield and free slots.
- **Checks:**
  - **Fresh character:** a ranged fight on rats made 20 kills, and the 25
    arrows lasted 490 ticks. A magic fight cast 15 wind strikes (110.5 Magic
    XP).
  - **Random stress:** four random 20-hour episodes ran with no errors.
  - **Speed:** the mask takes a median of 1.2 ms (p95 26 ms, from level-ups
    over three classes).
- **Tests:**
  - `tests/test_sim_ranged_magic.py` (10).
  - The slot test now checks all three classes against the reference.
  - Two finite-ammunition ranker cases.
  - Full suite: 117 passed, 14 skipped.

### Agent choices (reversible; for Caleb's review)
- **Magic doesn't need a staff.** Spells are cast by hand at the autocast
  rate. The server's autocast needs a staff, and the starter kit has none,
  so otherwise magic would wait for buying. The catalog's "autocasts" is
  annotated.
- **Arrows that land are picked straight back up** when the loot mode takes
  arrows. The pick-up time sits in the per-kill overhead (to calibrate).
  With `loot_none`, every shot is gone.
- **A magic fight keeps one spell.** When its runes run out the option ends,
  and the next ranking picks the next spell the runes allow.
- **The dark bow and chinchompas are never wielded** for ranged (two hits
  per attack; multi-target).
- **Magic gear:** the fight wields the weapon with the best magic attack
  bonus (a bronze dagger's +1 beats nothing) and armour by defence, ignoring
  armour's magic penalties.

### Known gaps
- gp/hr still doesn't subtract the arrows and runes used.
- The kill in progress when the time budget ends earns nothing and uses no
  ammunition (as for melee).

### Next
Buying (needs Caleb's review) keeps ranged and magic going after the starter
arrows and runes. Then the Gymnasium layer.

### Committed: ranged and magic
Caleb: "Commit this and draft the buying actions for my review." Commit
`8eb9486` on `sim-v0` (not pushed). `m002-buying-draft`.

### Drafted: the buying actions, for Caleb's review
`docs/buying-draft.md`; `m002-buying-draft`. Nothing is built.
- **Server mechanics read for it:**
  - The frozen GE seller fills a buy at once, at the 2009 price, from
    unlimited supply, for items with a 2009 price. There are no buy limits.
  - `ge_collect` takes items as banknotes when they don't fit.
  - Shop prices climb from 100% to 130% of value as stock runs down, and the
    whole purchase needs the coins in the inventory. Stock restocks by 1 unit
    per 100 ticks and is shared (`personalized_shops = false`).
- **The proposal:**
  - 51 GE actions and 37 shop actions (66 if the shops that never beat the
    GE are trimmed), with lots, masks, wearing on purchase and a banking-rule
    change.
  - Nine questions for Caleb, each with a recommendation.
- **Findings:**
  - The buy list alone has 67 items, more than V's estimated 60, so V grows.
  - Smithing needs a hammer, which the starter kit lacks. Until buying
    exists, one comes only from drops (316 monsters, guards among them). The
    default `loot_valuable` mode skips it, since a hammer is worth 1 gp.
  - The server's item configs swap skill and level in the "requirements" of
    the fishing rod and fly rod (`{5,10}`, `{20,10}`). It's harmless: rods
    can't be worn, and fishing levels come from the fishing code.

### Decided: most of the buying questions (Caleb)
`docs/buying-draft.md` §4; `m002-buying-decisions`. Nothing is built.
- **Decisions:**
  - Q1: as recommended, a buy gets as many as the coins allow, up to a lot.
  - Q2: shop purchases land in the inventory as items. GE purchases arrive
    as banknotes unless it's a single item.
  - Q4: buys that aren't upgrades are masked.
  - Q5: armour as pieces, not sets. With sets, rune armour would wait for
    Dragon Slayer, though only the platebody needs it.
  - Q7: every shop action is kept, including the shops that never beat the
    GE on price.
  - Q8: processing inputs can be bought.
  - Q9: shop stock is tracked within an episode, and selling uses it.
- **Open for discussion:** Q3 (gear) and Q6 (food), explained in the
  draft's §5 and §6.
- **Findings:**
  - Banking already strands gear without buying. A deposit banks unworn
    gear, and no action takes gear out, so the starter kit's first deposit
    loses the bow (after melee) or the sword and shield (after ranged). My
    revised Q3 recommendation fixes the deposit rule instead of wearing gear
    on purchase.
  - My draft's food tiers included two fish that other fish beat outright.
    Cod heals as much as trout for less, and monkfish heals more than
    swordfish for less. Corrected tiers: mackerel, tuna, monkfish, shark.
  - Q2's banknotes need a way to take GE food out of the bank, and lots for
    banknoted buys, since free slots no longer cap them. Both are proposed in
    the draft.
  - The server's GE lets a player collect as items or as banknotes, so Q2 is
    the human path. The bridge's `ge_collect` needs a fork change to choose
    banknotes.

### Decided: gear withdrawals, food tiers and lots; GE collection fixed on the fork
Caleb, on the buying draft; `m002-ge-banknotes`. The simulator side isn't built.
- **Decisions:**
  - Q3a, option (b): deposits are unchanged, and `bank_withdraw_gear_<class>`
    (melee, ranged, magic) takes a class's best gear out of the bank.
  - Q3b, as a principle: gear goes on when it suits the task. Caleb's example:
    no metal armour for tasks with a lot of running, since it drains run
    energy.
  - Q6: four GE food tiers (mackerel, tuna, monkfish, shark), plus Wydin's
    bread. The alternatives were one `buy_ge_food` that picks the fish that
    heals fully at the current max HP, or all eight fish as tiers.
  - Lots for banknoted GE buys: 100 for food, 1,000 for processing inputs.
  - "Make the change(s) as appropriate to make sure that GE purchasing acts
    normally": the go-ahead for the fork change below.
- **Fork change** (`RLCommands.kt`, uncommitted):
  - `ge_collect` collects as Q2 decided: more than one of an item that has a
    banknote as banknotes; a single item, coins, runes or arrows as items.
  - **Bug found and fixed:** offers placed back to back could get the same
    slot, so the second replaced the first. A new offer reaches the
    character's records only when the GE worker thread writes it, and until
    then its slot looked free. The bridge now remembers the slots it has
    handed out.
  - A new live test covers both.
- **Findings for Q3b** (the mechanism is still Caleb's call; draft §5):
  - The simulator has no run energy or weight, so gear costs nothing outside
    combat, and Agility would do nothing.
  - The server's weight penalty is mild. Running drains 1% faster per kg, and
    full plate is about 27 kg, which makes long trips about 4% slower. A full
    inventory of ore (about 63 kg) weighs more than the armour.
  - The server character never runs: no bridge command turns run on, so it
    walks at 1 tile a tick while the simulator assumes running at 1.5. The
    ±20% gate would catch this in travel times.
- **Still open:** the Q3b mechanism, and how GE food comes out of the bank.

### Decided: run energy and weight, and food withdrawals; buying built in sim v0
Caleb: "3b should sue option a. Make the bank_withdraw_<food> actions per
tier." `m002-buying-sim`. Uncommitted.
- **Decisions:**
  - Q3b, option (a): the simulator models run energy and weight (drain by
    weight, restore by Agility), the agent gets `bank_deposit_worn`, and a
    bridge command turns run on so the server character runs as a person
    would. I read choosing (a) as the go-ahead for that run-toggle fork
    change; it comes with the energy change, not yet built. The alternatives
    were (b) a rule that fights withdraw their class's gear and every other
    option banks it first, and (c) no weight or energy at all.
  - Food: one `bank_withdraw_<food>` per GE tier (mackerel, tuna, monkfish,
    shark), not one withdrawal that picks the largest food that heals fully
    at the current max HP.
- **Built in sim v0** (`rlscape/sim/buying.py`, `rlscape/sim/shops.py`):
  - 113 buy actions (76 GE, 37 shop), 3 gear withdrawals and 4 food
    withdrawals.
  - Shop stock, prices and restocking from `Shop.kt`, tracked within an
    episode (Q9). General-store sales now use the same stock: a store's own
    stock for items it sells, otherwise the player stock all general stores
    share, which the server clears every 3 hours.
  - Processing withdrawals now bank banknotes of their inputs first, so GE
    inputs need no separate deposit.
- **Option catalog v1.2:** §8 now holds the buying decisions, which replace
  the draft's table; §1, §5, §7 and §9 are updated. `docs/buying-draft.md`
  is marked superseded.
- **Agent choices** (reversible, listed in `buying.py`):
  - For the upgrade check, "held" means usable now, wherever it is.
  - The coins withdrawn are just the shortfall. A shop trip's bank stop is
    the bank with the shortest walk overall.
  - No shield is withdrawn behind a two-handed weapon.
  - Restocks and the player-stock clear run on episode ticks. The server's
    phase is arbitrary.
- **Found:**
  - **Mithril bars can't be processed in sim v0.** There's no
    `smith_mithril` activity, so bought mithril bars can only be sold.
    That's my draft's mistake. Options: add `smith_mithril` (Smithing 50,
    one more processing action), or drop `buy_ge_2359`.
  - Zeke's shop is listed twice in `shops.json` (ids 135 and 150).
    `Shops.startup` maps the shopkeeper to the later one, so the sim uses
    150.
- **Next:** run energy and weight (3b), then the Gymnasium layer.

### Decided: `smith_mithril`; buying committed
Caleb: "Add smith_mithril and commit this." `m002-smith-mithril`.
- **Decision:** add `smith_mithril` (my recommendation), not drop
  `buy_ge_2359`. Bought mithril bars can now be smithed.
- **Built:** `Smith("smith_mithril", "MITHRIL")` and its
  `bank_withdraw_for_smith_mithril`, by the same rules as the other three
  tiers. Smithing 50 makes daggers; the bigger items open with the level.
  Mithril bars come only from the GE, since sim v0 has no mithril ore or
  smelting.
- **Option catalog v1.2:** §3, §5 and §9 (about 514 actions).
- **Committed:** the fork's GE banknote change first, then this repo (the
  submodule pointer, buying, `smith_mithril` and their records).
- **Next:** run energy and weight (3b), then the Gymnasium layer.

### Built: run energy and weight (Q3b)
Caleb: "keep going with run energy and weight". `m002-run-energy`.
- **Simulator** (`rlscape/sim/energy.py`): run energy and weight ported from
  the server's `WalkingQueue` and `Settings`.
  - Drain: 0.55 × (1 + kg / 100)% per running tick.
  - Restore: 0.6 × 100 / (175 − Agility)% per other tick.
  - Run turns off under 1%; death restores energy to 100%.
  - Weight counts each inventory slot once, plus everything worn.
  - Walks run until energy is out, then walk. `route_ticks` predicts the
    same walk, so masks and runs agree. Every tick not spent walking
    restores energy.
- **`bank_deposit_worn`:** banks the worn gear but keeps tools and
  ammunition on, as `bank_deposit` does, so the agent can't strand its axe
  or pickaxe in the bank. The server has the player's path for it (the
  banker's "deposit worn items").
- **Fork change** (`RLCommands.kt`, fork `f5844bb`): `set_run` turns run on or
  off as the run orb does. `state` now reports run energy, run on or off,
  and weight.
- **Docs:**
  - option catalog §1, §5 and §8 (still v1.2)
  - env contract v1.2: energy and weight in the observation (§3), and the
    run rule (§7)
- **Found:**
  - **The server character already spawns with run on** (`AIPlayer.init`).
    Once energy runs out, the server turns run off and nothing turns it
    back on. Catalog §8 said the character "currently walks"; that was my
    mistake, now corrected. `set_run` is still needed, to run again on
    later walks.
  - **The weight model matches the server.** It matches the server's
    weight for the starter kit. Each running and resting tick on the server
    drains or restores exactly what the sim computes (live test, one read
    per tick).
  - **Combat-slot masks are slow** (`FightSlot.available`, 91% of mask
    time; about 90 steps/s on a random policy, unchanged by this work). I
    flagged it as a separate task.
- **Agent choices** (reversible):
  - Run goes on at the start of every walk, not mid-walk once energy
    recovers, because the server leaves run off once it runs out.
  - Stairs and ladders count as rest.
  - Moving between monsters in a fight isn't modelled, so fight ticks
    restore energy.
  - Fishing-spot moves still use the average speed.
  - Observation encoding: energy / 100, and kg / 100 clipped to [0, 1].
- **Next:** the Gymnasium layer (SimEnv and the observation encoder).

### Built: the Gymnasium layer (SimEnv and the observation encoder)
Caleb: "Commit this and keep going with the Gymnasium layer". `m002-gymnasium-layer`. Run energy was committed
first: fork `f5844bb`, main repo `1b9b9b4`.
- **`SimEnv`** (`rlscape/envs/sim_env.py`): the env contract's interface (§2)
  over sim v0.
  - `reset` takes `reward_weights` as an option, as §2 has it. The
    defaults are (0.5, 0.5), the weights of the planned sweep.
  - `step` returns w_s·r_skill + w_b·r_wealth, plus the §6 info.
  - `action_masks()` and `option_catalog()`.
  - Seeding follows Gymnasium: later resets continue the seeded stream.
  - A masked action raises, as before.
  - Episodes end only by truncation.
- **`ObsEncoder`** (`rlscape/envs/encoding.py`): every §3 part.
  - 480 features in [0, 1] for today's catalog (194 actions, empty *V*).
  - Each part has a named slice, for the decision logs.
  - `ServerEnv` will share it by turning the bridge state into a
    `CharacterState`.
- **`rlscape/quests.py`:** the 21-quest set with quest points, for the
  observation now and sim v1's quest options later.
- **Dependency:** `gymnasium` 1.4.0, the first of the RL stack (resources
  [21]).
- **Agent choices** (reversible, listed in the encoder's docstring):
  - **Equipment tiers** come from item names (metal, bow wood, staff
    kind), the tool chains, and the Fishing level of fishing gear. They
    count the best item carried, worn or in the inventory, because fights
    and tools use both.
  - **Regions** are the nearest of the catalog's 11 region anchors within
    60 tiles, or "elsewhere". The anchors are banks where the catalog names
    one, otherwise estimates to verify.
  - **Candidate features** are scaled by log XP/hr, signed log gp/hr,
    damage per hour over HP plus food, and travel over 15 minutes.
  - **Prayer** reads 1, since the sim doesn't drain it.
- **Found:** Gymnasium's `check_env` stops at its first unmasked random
  action, because masked actions raise. That's the contract's choice (never
  a silent no-op); the checker's reset and space checks pass before that.
- **Next:**
  - the item vocabulary *V* for Caleb to check (the inventory and bank
    parts grow with it)
  - then the baselines and the eval harness

### Drafted: the item vocabulary *V*, for Caleb's check
Caleb: "Commit this and keep going with the item vocabulary".
`m002-vocabulary-draft`. The Gymnasium layer was committed first, as main repo
`44ad628`.
- **Draft:** `docs/vocabulary-draft.md`, with the data in
  `data/vocabulary_draft.csv`, generated by `scripts/draft_vocabulary.py`.
  It applies the agreed rule (catalog §9, plus every bought item, §8) to
  the simulator's own data.
- **Drops:** a sweep repeats the agent's candidate selection (3 + 3 slots
  per class) over the calibration bands' levels, gear and quests, from 18
  hub towns, and records each drop's expected gp/hr per fight. Noted drops
  count as their items.
- **Found:**
  - **The rule taken literally gives 208 items, not about 60.** The
    catalog's estimate predates buying, which alone adds 77 items.
  - **Each *V* item adds 7 observation features,** not 2: its inventory
    and bank counts, plus its 5 actions' mask entries.
  - All 156 recommended items have a 2009 GE price and can be alched.
- **Recommendation (156 items; 974 actions; 1,572 observation features):**
  - "common" drops: at least 1,000 gp/hr somewhere and in at least 20 of
    the sweep's fights (50 drops)
  - the 29 smithed products no other group names stay misc
  - burnt food stays out
- **Open, for Caleb (Q1–Q4 in the draft):** the meaning of "common", the
  smithed products, burnt food, and any items to add or remove by hand
  (herb seeds and grimy herbs are the largest group).
- **Next:** once Caleb has checked it, *V* becomes the catalog's default
  (catalog §9, with tests). Meanwhile, the baselines and the eval harness.

### Decided: the item vocabulary *V* (156 items)
Caleb: "Accept the recommendations, commit this, and keep going with the
baselines". `m002-baselines`.
- **Decisions (Q1–Q4 of `docs/vocabulary-draft.md`, all as recommended):**
  - common drops are those in at least 20 of the sweep's fights: 50 of the
    73 that reach 1,000 gp/hr (the alternatives: all 73, or at least 50
    fights, which keeps 39)
  - smithed products no other group names stay misc (29 items; the
    alternative put all 44 smithed products in *V*, for 185 items)
  - burnt food stays out
  - nothing added or removed by hand
- **Built:**
  - *V* is frozen in `data/vocabulary.csv`, read by `rlscape/vocabulary.py`
  - it's the default for `build_catalog()` and `SimEnv()`; an empty
    vocabulary is still available for tests
  - the catalog has 974 actions, and the observation has 1,572 features
- **Tests:**
  - `tests/test_vocabulary.py` (new)
  - two existing tests updated for the new default. The slots test now
    gives its reference ranking the same *V*: the `valuable` loot mode picks
    up every *V* item, so bones fill the inventory sooner, and the bank
    trips change the fresh character's melee XP slots (Rat, Giant spider,
    Imp, where it was Rat, Man, Ram).
- **Docs:**
  - option catalog §9: the decision and the real action counts
  - the draft marked accepted
  - env contract §3's as-built note

### Built: the random and greedy baselines (E1)
Same interaction (`m002-baselines`). *V* was committed first, as main repo
`cf050ed`.
- **`rlscape/baselines`:**
  - `RandomPolicy`: uniform over the masked actions.
  - `GreedyPolicy(objective)`: one-step lookahead on expected rates at the
    current state, as the ROADMAP describes.
    - Each allowed option runs twice on a copy of the character, with the
      policy's own random numbers, so the episode itself is untouched.
    - It takes the best mean gain per mean game tick.
    - Objectives: `skill` (r_skill), `wealth` (net worth, GP/hr) and `xp`
      (raw XP summed over skills, XP/hr).
- **`rlscape/eval/rollout.py`:** `play(env, policy, seed)` plays one
  episode and collects the contract's metrics and checkpoints. The multi-seed
  harness comes next.
- **`SimEnv.observe()`** is now public, for tests and setup that edit the
  state directly.
- **Agent choices** (reversible):
  - When nothing gains, greedy banks (`bank_deposit`) if it can, otherwise
    takes the least bad option. Without that rule, a myopic policy stalls
    at a full inventory.
  - Greedy never picks loot-mode actions. They gain nothing themselves, so
    switching back and forth would waste decisions.
  - Two lookahead samples per option.
- **First 20-hour episodes** (seed 0; one seed, so indicative only):

  | Baseline | Total level | Net worth | Decisions | Wall time |
  |---|---|---|---|---|
  | random | 183 | 6,702 | 430 | 3 s |
  | greedy skill | 236 | 5,981 | 136 | 10 s |
  | greedy wealth | 94 | 1,006,944 | 1,090 | 67 s |
  | greedy XP | 160 | 1,139 | 1,182 | 87 s |

- **Found:**
  - **Greedy on raw XP ends below random on total level.** It piles its
    XP into firemaking and woodcutting (cut, burn, repeat), while greedy on
    r_skill spreads its XP and mostly fights. The E1 "greedy XP/hr" should
    probably be the r_skill version, the quantity the skill objective
    measures; that's for Caleb.
  - **Greedy wealth mines and banks:** copper ore at first, then iron. The
    frozen January 2009 prices value copper ore at 72 gp and iron ore at
    99 gp, so a fresh character's best immediate money is mining. It makes
    over a million gp of net worth in 20 hours, a strong bar for H1 to
    beat.
- **Next:**
  - the eval harness (seeds, parquet, bootstrap CIs)
  - then the scripted-guide baseline, which Claude drafts from archived
    2009 guides for Caleb's review

### Decided: E1's greedy XP/hr baseline is greedy on raw XP
Caleb: "Go with raw XP. There should be break points where going for certain
levels in skills is very lucrative, comparatively. Going only by level will
penalize an agent for going after higher skills to reach those break
points." `m002-greedy-xp`.
- **Built:** `e1_baselines()` returns E1's set: masked random, greedy on raw
  XP (`greedy_xp`) and greedy on net worth (`greedy_wealth`). The scripted
  guide joins after Caleb's review. Greedy on r_skill stays available for
  comparison.
- **Open, raised with Caleb:** the same argument applies to the agent's own
  skill reward. r_skill is a level-based measure (env contract §4, signed
  off), chosen so that high-level XP wouldn't dominate and so the reward
  matches the reported metric. Whether to change it is Caleb's decision.

### Decided: the skill reward stays level-based; total XP is reported
Caleb: "Keep level-based reward and include total xp, but only up to the
required xp to get level 99." `m002-total-xp`. This answers the open question
from `m002-greedy-xp`.
- **Env contract v1.3** (§4, §6, decision 19): total XP is a reported metric
  at every checkpoint. It's Σ over all 24 skills of XP, each skill counted
  up to 13,034,431, the XP for level 99. r_skill is unchanged.
- **Built:**
  - `capped_total_xp` (`rlscape/sim/skills.py`) and
    `CharacterState.total_xp()`
  - `info["total_xp"]`, in checkpoints, the reset info and `Episode`
- **Agent choice:** E1's greedy XP/hr baseline now maximises the same capped
  total, so it chases exactly the metric it's reported on. Within 20 hours
  from a fresh start the cap never binds, so this changes nothing in
  practice; it keeps the two definitions identical.

### Built: the eval harness; a preliminary E1 run
Caleb: "Commit this and keep going with the eval harness". `m002-eval-harness`.
The baselines and total XP were committed first, as main repo `43887df`.
- **`rlscape/eval/harness.py`:**
  - `run(policies, seeds, env_kwargs, workers)` plays every (policy, seed)
    episode, in worker processes when asked, and returns two tables: one
    row per checkpoint (hour 0 and every 2 hours), and one row per episode.
    An episode's result depends only on its policy and seed, never on the
    number of workers (tested).
  - `summarize`: per policy, hour and metric, the mean over seeds with a
    percentile-bootstrap 95% CI.
  - `paired_difference`: policy a − b on the same seeds, per hour, with a
    CI.
  - `save` writes parquet plus `config.json`: the config, its hash, the
    git SHAs of this repo and the server submodule, whether the tree had
    uncommitted changes, and package versions.
- **`scripts/evaluate.py`:** the command line. Results go to the
  git-ignored `results/`.
- **Dependencies:** pandas 3.1 and pyarrow 26, from the ROADMAP's stack.
- **Preliminary E1 run.** This isn't the E1 deliverable: the sim isn't
  calibrated, and the scripted guide isn't written yet. It ran 3 baselines
  × 10 seeds × 20 game-hours on 14 workers, in 223 s
  (`results/eval/e1-preliminary-20261030`).

  | At hour 20 (mean [95% CI]) | Total level | Total XP | Net worth |
  |---|---|---|---|
  | random | 184 [180, 187] | 72,712 [67,628, 78,752] | 8,982 [6,798, 11,531] |
  | greedy XP | 159 [158, 160] | 767,586 [762,726, 772,094] | 1,199 [1,150, 1,241] |
  | greedy wealth | 122 [101, 143] | 213,992 [136,095, 290,864] | 687,811 [434,726, 935,678] |

- **Found: greedy wealth is bimodal.**
  - 6 of 10 seeds mine iron and bank, ending at 0.94–1.09M gp and total
    level 92–101.
  - The other 4 commit early to fighting for drops (melee gp slots) and
    never switch, ending at 118k–253k gp with total levels 157–167.
  - That's myopic lock-in: mining iron needs Mining 15 first, which greedy
    never trains once combat looks better. It's the kind of delayed payoff
    H1 is about, and the reason the CI is wide.
- **Episode cost:** in parallel, a greedy XP episode takes about 157 s, a
  greedy wealth episode about 89 s, and a random one about 6 s.
- **Next:** the scripted-guide baseline, which Claude drafts from archived
  2009 guides, with citations, for Caleb's review.

### Drafted: the scripted-guide baseline; a fight-mask fix
Caleb: "Commit this and keep going with the scripted guide". `m002-scripted-guide`.
The eval harness was committed first, as main repo `3714afa`.
- **Sources:** the RuneScape Wiki's training pages as of January 2009
  (revisions with stable links, resources [22]–[26]): Woodcutting, Fishing,
  melee and the Mining article. No January 2009 page orders the skills, so
  the schedule is Claude's proposal.
- **Draft:** `docs/scripted-guide-draft.md`, built as
  `rlscape/baselines/guide.py` (`ScriptedGuidePolicy`, run as
  `scripted_guide`). It's not in `e1_baselines()` until Caleb has reviewed
  it.
  - Methods by level come from the guides.
  - The schedule is lowest skill first, over Attack, Strength, Defence,
    Woodcutting, Mining and Fishing.
  - Upgrades: the tool, then the scimitar, then armour.
  - Produce is sold only when it pays for the next upgrade.
- **10 seeds × 20 hours (sim v0, uncalibrated):** total level 233 [230,
  236], total XP 152k, net worth 23k. Random gives 192 levels and 9k.
- **Sim fix (agent choice, reversible):** fight slots are masked while HP is
  at or below the retreat point with no food. Before, every such fight
  retreated before its first swing, and a policy could loop on 1-tick
  fights. Random's numbers move a little (184 → 192 levels at hour 20), so
  the preliminary E1 table above predates this fix.
- **Found, for Caleb (Q2 of the draft):** nothing in the catalog withdraws
  banked produce to sell it; `bank_withdraw_for_<activity>` covers
  processing inputs only. Net worth doesn't need selling, but buying gear
  needs coins.
- **Caleb, during the turn:** "The agents must be flagged as members. Do the
  agents know how to tick-manipulate for skilling and prayer flicking?"
  - **Members:** they are. 2009Scape has no per-player membership: the world
    setting `members = true` (`rl.conf`) covers every character, the
    agent's included, and no per-player members check exists in the server
    source. The sim includes members areas, banks and monsters.
  - **Prayer flicking:** it works on this server and makes prayer free.
    `Prayer.tick()` drains only on even counts of consecutive prayer ticks,
    and the count resets when no prayer is on. Neither the sim nor the
    planned executor uses prayers in combat yet, so the agents don't pray
    or flick.
  - **Tick manipulation:** options run the server's standard delays (for
    example woodcutting's 3-tick `Clocks.SKILLING`). Whether an item
    interaction can shorten the skilling clock on 2009Scape is unverified;
    that needs a live test.
  - Both are decisions for Caleb; options are in `m002-scripted-guide`.
- **Next:** Caleb's review of the draft (Q1–Q4) and of the two technique
  questions.

### Decided: a withdraw-to-sell action; found: inventories clog with kept items
Caleb: "1. Why is it only selecting from those skills? 2. Add a withdraw to sell
action. 3. Is your recommendation here only for initial evaluation? I want the
real agents to be able to utilize any skill. 4. Do you think we'll be able to
get level 99 fishing in the time allowed?" `m002-withdraw-for-sale`.
- **Decision (Q2 of the scripted-guide draft):** add a withdraw-to-sell
  action.
- **Built:**
  - **`bank_withdraw_for_sale`** (catalog §5; `rlscape/sim/buying.py`):
    walk to the nearest bank and take out produce as banknotes, most
    valuable stacks first, up to the free slots. Produce is what
    `bank_deposit` banks, apart from the gear the character would fight
    in, and apart from items that neither note nor stack.
  - **Per-item sells** (`sell_ge_<item>`, `sell_store_<item>`) now sell the
    item's banknotes too. Before, a vocabulary item's banknotes couldn't be
    sold at all.
  - The catalog is now 975 actions, and the observation 1,573 features.
  - **The guide funds upgrades from the bank,** and buys the best
    affordable tier rather than only the best usable one.
- **Answers:**
  - **Q1 and Q3:** the six skills are only the scripted guide's scope. The
    agents' action space has every sim v0 option (all 14 trainable skills'
    activities, combat in all three classes, buying, selling), and sim v1
    adds five skills and quests.
  - **Q4:** no. Level 99 needs 13,034,431 XP. Sim v0's fly fishing
    (powerfishing, uncalibrated) gives about 16k XP/hr at level 20 and
    32–36k from level 50. That's about 365 game-hours from 20 to 99, and 20
    hours of nothing but fly fishing from 20 reaches about level 68.
- **Found, for Caleb:** inventories clog with what `bank_deposit` keeps.
  "Tools stay" keeps every tool, including obsolete axes and pickaxes;
  ammunition stays even with no weapon to fire it (bolts from drops); food
  stays in every amount. On seed 1 the guide reached Attack 22 holding 28
  kept items, so nothing could be banked, bought or gathered. Agents can
  reach the same state. Recommended: keep only the best usable tool of each
  kind, and only ammunition that fits a held weapon, and bank the rest. It
  changes a signed-off catalog rule, so it waits for Caleb.

### Decided: the guide review; deposits keep the task's kit (built)
Caleb, in reply to the guide draft and `m002-withdraw-for-sale`: "1. Widen the
guide. 2. Deposit all items that are not suitable to the task at hand. 3. Go
after lowest skill for schedule. 4. For scope, include more skills. I think
Thieving, specifically will be a great money maker early on. 5. Offer the
different paths as gp/hr or xp/hr for the agents to choose from. 6. We will
implement prayer flicking and 3-tick woodcutting if they can be used."
Clarified in a follow-up question: deposits use the last activity's kit;
paths become skilling slots (XP/hr and gp/hr per skill, with rates in the
observation); prayer flicking and tick manipulation get a live test first,
which should also cover 2-tick woodcutting and fishing and mining; thieving
gets the pickpocket targets and the stalls. `m002-task-kits`.
- **Built (this slice): deposits by task.**
  - Every activity option names its task (`Option.task`), and the engine
    records the last one in `state.task`.
  - `bank_deposit` keeps that task's kit (`rlscape/sim/kits.py`) and banks
    the rest.
  - New: `bank_withdraw_for_<task>` for gathering (woodcutting, mining and
    the three fishing methods), and `bank_withdraw_food` for any food.
  - The task is a new 11-way observation part (env contract v1.4, decision
    20). The catalog is now 981 actions, and the observation 1,590 features.
  - Tests cover each task's kit, the withdrawals, and a bug they caught:
    the withdrawal ranked tools by level, so an iron axe never beat a bronze
    one; it now uses the server's tool priority.
- **The guide with kit deposits** (10 seeds × 20 hours): total level 306,
  total XP 211k, net worth 353k. Before, it was 233, 152k and 23k, stuck in
  steel by the clog. Random: 190, 86k, 10k.
- **Tick manipulation, from the server source** (Caleb pointed to the OSRS
  wiki's tick manipulation page, which shows the mechanism: an action
  resets the skilling timer):
  - **Woodcutting:** rolls whenever `Clocks.SKILLING` is ready. A roll
    every 3 ticks is already 2009Scape's default. `delayClock` overwrites
    the clock, and burying a bone sets it to 2 ticks (`BoneBuryListener`).
    So chopping, burying a bone on the same tick and clicking the tree again
    may give 2-tick woodcutting. Live test needed.
  - **Mining:** each start waits the full `getDelay` before its first roll,
    and no shared timer exists, so no manipulation is possible.
  - **Fishing:** `FishingPulse`'s first pulse only sets a 5-tick delay, so
    restarting adds delay. No manipulation is possible.
  - **Prayer flicking:** it avoids drain, by the code. Whether flicked
    protection is up on an NPC's hit tick needs a live test.
- **Remaining slices, in order:**
  1. thieving targets and stalls
  2. the wider guide
  3. skilling slots
  4. the live tests, which need bridge commands for item options and prayer
     toggles (fork changes)

### Built: pickpocket targets; tick manipulation re-checked (correction)
Caleb: "Commit this and keep going with thieving" (the guide, withdraw-to-sell
and task kits are `63ebb0d`). Mid-turn: "I've seen tick manipulation methods
with fishing and mining using either herb+tar+pestle/mortar or knife +
log/barbarian fish." `m002-thieving-targets`.
- **Built: 13 pickpocket targets** from the server's Pickpockets table (men,
  farmers, both H.A.M. members, warriors, master farmers, guards, Fremenniks,
  Knights of Ardougne, Yanille watchmen, paladins, gnomes, heroes), each at its
  server spawn nearest Lumbridge. Weighted loot, the server's canRoll rule, lost
  loot when it doesn't fit, and an eating rule that keeps a failed attempt from
  killing (heroes hit 6). The catalog is now 993 actions and the observation
  1,602 features. The parser now reads `IntStream.rangeClosed` ids and
  `insertEasyClue`.
- **No option yet:** rogues (Wilderness only), cave goblins (Dorgesh-Kaan,
  outside the travel model), bearded bandits (no spawns), desert bandits and
  Menaphite thugs (behind the Shantay Pass gate, which takes a pass going south).
- **Rates with HP to spare, while pickpocketing (no banking):** men 12k XP/h;
  H.A.M. members about 25k XP/h and 200k gp/h (grimy kwuarm, 2,911 gp in
  January 2009); master farmers 43k XP/h and 355k gp/h at level 38 (ranarr and
  snapdragon seeds); Knights of Ardougne 95k XP/h at 55; heroes 159k XP/h and
  548k gp/h at 80.
- **Stalls: open questions for Caleb.** The server's StallThiefPulse steals
  once per click (3 ticks), then the stall restocks (baker 4 ticks … gem 300).
  4 in 15 steals are noticed when a market guard (id 32) is within 8 tiles,
  and that guard attacks; no stealing in combat. Ardougne's market has 7 guard
  spawns near its stalls. The server's Stall table lacks Ardougne's spice stall
  (object 2564).
- **Correction to the tick-manipulation findings (`m002-task-kits`).** OSRS's
  methods work because an item-on-item action sets the skilling clock without
  checking it. On 2009Scape, every action that sets `Clocks.SKILLING`
  (`CraftItemWithLogScript` for knife on log, `BoneBuryListener`, the arrow,
  bolt and stringing scripts) first returns unless `clockReady`, so none can
  shorten a pending delay. Herb on tar (`HerbTarPulse`) is a pulse that never
  touches the clock, and starting it replaces the skilling action. So:
  - **Fishing:** `FishingListener` (not `FishingPulse`, which nothing in the
    live game calls) rolls on a click when the clock is ready, then sets it 5
    ticks ahead. Neither knife-on-log nor herb-on-tar can shorten that. The sim
    already models `FishingListener`.
  - **Mining:** a fixed 4-tick script delay from each click; no clock.
  - **Woodcutting:** the 2-tick method by burying a bone is **not** possible:
    burying is refused while the clock is pending. Woodcutting stays at its
    default 3 ticks.
  - **Prayer flicking** is unaffected; its live test still stands.

### Decided and built: stalls, the Shantay Pass; tick manipulation tested live
Caleb, on the three questions in `m002-thieving-targets`: "1. Go with B. 2.
Good recommendation. 3. Let's try to test it. The code may have bugs that we
can exploit for this limited use. Tick manipulation is an understood and
normal part of the game." `m002-stalls-and-tick-test`.
- **Stalls (B: run off and come back).** Five Ardougne market stalls (baker,
  silk, fur, silver, gem), from the server's Stall and StallThiefPulse:
  - a steal takes 3 ticks and a free slot, gives one reward picked uniformly,
    and empties the stall for its restock time (4 to 300 ticks)
  - 4 in 15 steals are noticed when a guard is within 8 tiles, and the market's
    guards reach every stall. A noticed steal fails, and the character takes
    the guard's swings (the combat retreat's ESCAPE_ATTACKS) and 20 ticks away
    (FLEE_TICKS, an estimate to calibrate)
  - left out: the spice stall (not in the server's Stall table)
  - rates at each stall's level, with guards: 3–6k XP/h and 9–29k gp/h, far
    below pickpocketing
- **The Shantay Pass (the recommendation).** Going south through the gate buys a
  5-coin pass from Shantay (ShantayOptionPlugin) and hands it over; north is
  free. Without 5 coins the desert is unreachable, and pickpocket and fight
  options there are masked. That adds desert bandits and Menaphite thugs: 15
  pickpocket targets. Desert heat on the walk and the magic carpets aren't
  modelled. The catalog is now 1,000 actions and the observation 1,609 features.
- **Tick manipulation, tested live** (`scripts/tick_manipulation_test.py`,
  `results/live/tick-manipulation-20261030-2023.json`). Each trial ran 45
  ticks of per-tick inputs, sent as client packets, and read the skilling
  clock and the script delay every tick, so every roll is seen, failed or not:

  | Skill | Natural interval | Shortest gap, any method | Burying a bone | Knife on log, herb on tar |
  |---|---|---|---|---|
  | Woodcutting | 3 ticks | 3 | 5–6 ticks | 3 or slower |
  | Fishing | 5 ticks | 5 | 7–8 ticks | 5–6 ticks |
  | Mining | 5 ticks | 8, or no roll at all | no roll | no roll |

  No method shortened a gap: the code's guard holds. Every action that sets the
  skilling clock first checks it's ready (burying also locks the character for
  2 ticks). "Make" queues the log craft as a weak script, which the click on the
  tree removes. The tar is a pulse that waits 4 ticks, which the click's
  movement pulse replaces. Mining restarts its wait on any click or item use.
- **Found by the test:**
  - **Mining rolls every 5 ticks on the server, not 4.** ScriptProcessor runs a
    script only when `nextExecution < ticks`, so `delayScript(4)` means 5 ticks.
    The sim's mining assumes 4 (`ATTEMPT_TICKS`), so it overstates mining by
    25%. Recommended fix: 5, Caleb's call.
  - **Bridge timing.** The bridge's commands run after the world's pulses, but a
    client's packets run before them. So a buried bone (a 1-tick pulse) landed a
    tick late through the bridge. The new `packet` option enqueues the real
    client packet instead. Recommended: the ServerEnv executor uses it.
  - **Skill dialogues.** The bridge used to close every chatbox each tick,
    including herb on tar's "how many" dialogue, which opens a tick after the
    action. It now leaves skill dialogues open for the controller to answer.
- **Fork changes** (`RLCommands.kt`, `RLBridge.kt`; uncommitted):
  - `item_option`, `use_item`, `dialogue_button`, and `schedule` (one list of
    commands per tick)
  - `interact` now follows the client's click path (it resets the character's
    scripts first, as PacketProcessor does)
  - the `packet` option on the four input commands
  - `debug_set_levels`, `debug_complete_quest` (the names env contract §7
    gives them), `debug_clocks` (tests and
    calibration only)
- **Next:** the wider guide, skilling slots, and the prayer-flicking live test,
  which the new commands make possible (it still needs a prayer-toggle command).

### Decided: mining every 5 ticks; ServerEnv inputs as client packets
Caleb: "Accept both recommendations, commit this, and keep going with the
guide". `m002-wider-guide`.
- **Mining:** the sim's attempt interval is now 5 ticks (`rlscape/sim/mining.py`,
  `ATTEMPT_TICKS`), as measured live. getDelay is 4, and delayScript's wait
  runs one tick longer. Of the other activities the sim models, only cooking's
  fire-lighting animation waits on delayScript; cooking itself is a pulse.
- **ServerEnv inputs are client packets** (env contract v1.5, decision 21): the
  bridge's `packet` option.
- **Renamed** the new calibration commands to the names env contract §7 already
  gave them: `debug_set_levels` (several skills at once) and
  `debug_complete_quest`.
- **Committed:** fork `7956207` (the bridge commands); the main repo commit adds
  the thieving targets, stalls, the Shantay Pass, the tick-manipulation test and
  the mining fix.

### Drafted: the scripted guide over every sim v0 skill
Continuing `m002-wider-guide` (Caleb: "keep going with the guide"). Details in
`docs/scripted-guide-draft.md` (second draft).
- **The routine:** the lowest of the 13 skills sim v0 trains directly comes
  next (Caleb's schedule), each by its January 2009 RuneScape Wiki guide.
  Seven new sources, [27]–[33]: Thieving, Cooking, Smithing, Prayer and Ranged
  training pages, and the Firemaking and Magic articles (neither had a
  training page yet).
  - Thieving maps the guide's path onto the new targets and stalls; The
    Feud's levels (blackjacking) stretch the neighbouring methods.
  - Processing uses the guide's own gathering, not GE inputs.
- **Results** (10 seeds × 20 hours, `results/eval/guide-wide-20261030`):
  - the 13-skill guide: total level 308, total XP 87k, net worth 55k
  - the first draft's six skills, on today's sim: 303, 205k, 330k
  - random: 184, 80k, 13k
  - Widening keeps total level but costs 58% of the XP and 83% of the
    wealth: with 13 skills at the bottom of the schedule, every skill stays
    low, where every method is slow.
  - Raised as Q5: is the 13-skill, lowest-first guide the E1 baseline?
    Recommended: (a) keep it as specified. The alternatives were (b) lowest
    first over fewer skills, and (c) both the 13-skill and the six-skill
    guide in E1.
- **Sim fixes found along the way** (each would trap an agent too; tested;
  raised as Q6):
  - magic fights take off, and don't put on or withdraw, armour that lowers
    magic attack (an iron set left a level-1 caster no target)
  - `bank_withdraw_gear_magic` takes banked runes back out
  - processing withdrawals take only inputs the level can use
  - a buy is masked when its banked coins can't reach the inventory (a full
    one): such a buy bought nothing, and the guide looped on it 7,000 times
- **Loops fixed in the guide itself** while widening it:
  - depositing a just-withdrawn input before using it
  - a thieving food withdrawal filling the slots the loot needs
  - selling the starter shortbow as misc, which stopped Ranged at 1
  - funding counted banked items it would never sell
  - The tests now bound a 20-hour episode at 1,000 decisions. The episodes
    take 519–618.

### Decided: the 13-skill guide is E1's scripted baseline; the sim fixes stay
Caleb, on Q5 and Q6 of the guide's second draft: "Apply both recommended
actions." `m002-guide-signoff`.
- **Q5 (a):** the 13-skill, lowest-first guide is E1's scripted-guide
  baseline. `e1_baselines()` now returns random, greedy XP, greedy wealth and
  the scripted guide. Env contract decision 17's review is done.
- **Q6:** the four sim fixes the guide found stay:
  - magic's armour rule
  - the magic withdrawal takes runes
  - processing withdrawals respect the level
  - the buy mask's coins rule

### Decided and built: skilling slots; the guide on members' guides with stints; fletching checked live
Caleb: "Commit this and keep going with the skilling slots" (the guide work is
main repo `7030ede`). `m002-skilling-slots`.
- **Skilling slots** (env contract v1.6, decision 22; option catalog §2). On
  the design questions:
  - Caleb's answer on the skills: "Where possible, pair gathering skills with
    their processing counterpart. Woodcutting with fletching/firemaking,
    fishing with cooking, and mining with smithing."
  - Slots: "2 by XP + 2 by gp (Recommended)".
  - The 31 fixed actions: "Replace them (Recommended)".
  - Built: 39 paths (each method kept, or burned, cooked or smelted where
    sim v0 has the counterpart; thieving's targets and stalls); 16 slot
    actions; an analytic rate model checked against the simulated paths
    within 8%; 985 actions and 1,674 observation features.
  - A ranking costs 0.7 ms per decision once its cache is warm.
  - The woodcutting kit now keeps a tinderbox (and its withdrawal takes one),
    for the chop-and-burn paths.
- **The scripted guide's sources** (mid-turn): "We need to review why we have
  the scripted guide based on f2p activities. p2p activities generally give
  better rewards, but could require more travel time, especially when skill
  hopping."
  - The F2P pages were Claude's oversight: January 2009 members' guides exist
    for melee, ranged, woodcutting, fishing, cooking and firemaking.
  - Caleb: "Members' where they exist (Recommended)"; and for the schedule,
    "Minimum stint where the goal levels are multiples of 5."
  - Built: members' sources [34]–[39]; stints to the next multiple of 5;
    gathering through the slots.
  - Guide, 10 seeds × 20 hours: total level 306, total XP 90k, net worth 58k.
    Random: 236, 108k, 10k (it was 184, 80k, 13k before the slots).
- **Fletching** (mid-turn): "We need to include fletching as a major skill to
  level. It is significantly better than firemaking for gp and can be used to
  gain xp while traveling." And: "Attaching feathers to unfinished bolts or
  darts should be a zero time action, which can be completed between any
  other actions. Unless 2009scape is weird."
  - Checked on the live server:
    - Knife on logs makes one log's worth every 3 ticks.
    - Darts make 10 per stage, every 3 ticks; bolts are coded the same way.
    - Darts need The Tourist Trap.
  - All of these are queued scripts. Any walk or new action clears them
    (`MovementPulse` and `PulseManager.run` call `removeWeakScripts` and
    `removeNormalScripts`). Live, a walk stopped log fletching after 2 logs
    and dart making after 2 stages.
  - So on 2009Scape, fletching (darts and bolts included) is neither
    zero-time nor possible while travelling: it's an activity of its own.
  - No January 2009 fletching training page exists; the Fletching skill
    article ([40]) does.
  - Proposal for Caleb in the reply: bring Fletching forward from sim v1.

### Decided and built: Fletching in sim v0; the knife spawn

- **Fletching** (Caleb, on Claude's options): "B, but do not use bowstrings to
  complete bows where the value of the bow is not greater than unfinished +
  bowstring. Take the recommended option for other fletching decisions."
  - B: cutting logs, stringing, arrows, darts and bolts, from the server's
    recipes (44; no stocks, ogre, dragon, broad, blurite or silver).
  - Stringing at prices_v2's values: only maple, yew and magic longbows and
    yew shortbows are worth more strung.
  - The recommended rest: woodcutting's chop-and-fletch paths (normal logs
    into arrow shafts, which stack; otherwise the best bow (u)), and
    Fletching's own skilling slots over bank paths, one per recipe. The guide
    trains Fletching by the Fletching article ([40]).
  - The 20 fletching inputs (knife, bowstring, arrowtips, dart tips,
    unfinished bolts) join *V* by its rule: *V* = 176, 1,110 actions, 1,860
    observation features. Env contract v1.7, decision 23.
- **The knife spawn** (mid-turn): "There should be a knife spawn in Lumbridge
  Castle, which is very convenient for a fresh starting character."
  - The server's ground spawns have two knives, at (3205, 3212, 0) and
    (3224, 3202, 0), respawning after 80 ticks.
  - Built as `take_knife`: walk to the nearest and pick it up, while no knife
    is held. A fresh character has one in under 30 ticks.
- Guide, 10 seeds × 20 hours: total level 312, total XP 94k, net worth 108k.
  Random: 235, 102k, 8k.

### Decided: an open-questions log; answered questions only here
Caleb: "Review the documentation for questions. Questions that are already
answered should exist only in the decision log. Open questions should be
migrated to an open-questions-log.md file. For future questions that are
undecided, record them in open-questions-log." `m002-open-questions`.
- **New: `docs/open-questions-log.md`,** with the six open questions found:
  - OQ-1: the stretch experiment (tentatively A)
  - OQ-2: the sim v1 skills' options and their *V* items
  - OQ-3: prayer flicking: the test's fork change, then how agents use prayer
  - OQ-4: the bridge commands for the other player paths (shop buys,
    putting gear on, bank withdrawals, `bank_deposit_worn`)
  - OQ-5: freezing the server version once calibration starts
  - OQ-6: public repos for the submission (deferred)
- **The rule** (in `CLAUDE.md`): an undecided question goes in that log when
  it comes up. Once answered, it moves here with its options and the answer,
  and leaves that log.
- **Answered questions removed from the other docs.** Each was already here;
  the alternatives some entries lacked were added above (the buying Q6, Q7 and
  Q3b, the food withdrawals, the vocabulary's Q1 and Q2, the guide's Q5).
  - `ROADMAP.md` §8: the 2026-10-05 answers and the repos; now a pointer
  - `docs/scripted-guide-draft.md`: the question section (Q5, Q6) and the
    first draft's review note (Q1–Q3)
  - `docs/vocabulary-draft.md`: Q1–Q4, now stated as the accepted readings
  - `docs/option-catalog.md`: the buying questions' tags and the list of
    decided v1.0 questions
  - `docs/env-contract.md`: the Q3b references
- **`docs/buying-draft.md` deleted** (Caleb: "Delete it (Recommended)"). It was
  superseded on 2026-10-30: option catalog §8 has the spec, and this log the
  decisions. Its last version is in commit `d72dc47`.
- **Env contract §9 kept** (Caleb: "Keep it (Recommended)"): it's the signed-off
  contract's list of what's fixed, stated as decisions.
- **Left as they are:**
  - the interaction records, which record past turns
  - this log's chronological "open" notes, each answered by a later entry
  - agent choices marked "for Caleb's review": decisions Claude made, not
    questions
  - known gaps and planned checks: the rate model's respawn waits and
    consumables, the access rows "to verify", the untested in-combat flag
- **Also fixed:** "five v1 skills" in `CLAUDE.md`, `ROADMAP.md` and env
  contract §7 (four since Fletching moved into sim v0), and the ROADMAP's
  "awaiting Caleb" on the signed-off guide.

### Committed; prayer flicking tested live (OQ-3's first part)
Caleb: "Commit this and go ahead with OQ-3." `m002-prayer-flicking`. The
skilling slots, Fletching and the open-questions log are main repo `f47b7fb`
(not pushed).
- **Answered (OQ-3's first part):** the go-ahead for the fork change the
  prayer-flicking test needs. The second part, how agents use prayer in
  combat, stays open (OQ-3, reworded).
- **Fork change** (`RLCommands.kt`, uncommitted):
  - `prayer {uid, prayer}` clicks a prayer's button on the prayer tab, as
    `PacketProcessor.processIfAction` handles a click; with `packet=true` it
    enqueues the `IfAction` packet a client's click sends.
  - `state` reports prayer points and the active prayers.
  - **Bug fixed in `debug_set_levels`:** it set a level but not the current
    hitpoints or prayer points (`setStaticLevel` leaves them), so a
    calibration character set to Hitpoints 50 still had 10 hitpoints. It now
    refills both.
- **From the source:**
  - `Prayer.tick`, in each character's tick, counts the ticks in a row with
    any prayer on, resets the count on a tick with none, and drains only on
    even counts.
  - A protection prayer is checked when the attacker swings
    (`getFormattedHit`, from `adjustBattleState`); an NPC's hit is then 0.
  - A tick runs the client packets, then the world's pulses, then the bridge,
    then the characters' ticks. So a prayer turned on by a packet in a swing's
    tick, and off by one the next tick, is counted once and never drains.
- **Live test** (`scripts/prayer_flick_test.py`,
  `results/live/prayer-flicking-20261031-0536.json`). A character with
  Prayer 43, Hitpoints 99 and Defence 1 fights a lone hill giant (a swing
  every 6 ticks) for 120 ticks per trial, over 2 rounds:

  | Protect from Melee | Hits landed | Prayer drained |
  |---|---|---|
  | none | 13, 11 | 0 |
  | on throughout | 0, 0 | 8.85 |
  | flicked: on every other tick, switching parity halfway | the half on the giant's swing ticks: 0, 0; the other: 9, 4 | 0 |
  | off and on in the same tick, every tick (the OSRS one-tick flick) | 0, 0 | 8.85 |

  - Flicking works: it costs nothing and blocks every swing that falls in a
    tick with the prayer on. Each hit that landed showed one tick after a tick
    with the prayer off, so protection counts at the swing, not when the hit
    lands.
  - The OSRS one-tick flick doesn't save anything here: `Prayer.tick` only
    ever sees the prayer on, so it drains as if left on.
  - A first run against a Falador guard (18 hitpoints) gave the same results,
    but its fourth trial's fight stopped after 37 ticks, most likely because
    the earlier trials had worn the guard down. The giant has 35.
- **Tests:** three live tests in `tests/test_bridge_inputs_live.py` (the
  prayer button, both ways; the refilled levels; a prayer on every other tick
  never drains). Full suite with the server up: 246 passed.
- **Open, for Caleb (OQ-3):** how agents use prayer in combat. Recommended:
  fights flick automatically wherever the Prayer level allows.

### Decided: fights flick prayers automatically (OQ-3); offensive flicking tested live
Caleb: "We're going to automatically flick prayers, including the accuracy and
damage options available. That includes atk and str, but also range and mage,
if those prayers exist in 2009scape." `m002-prayer-in-combat`. The options
were (a) fights flick automatically (recommended), (b) a prayer mode the agent
sets, (c) no prayer in combat.
- **They exist:** attack (Clarity of Thought 7, Improved Reflexes 16,
  Incredible Reflexes 34), strength (Burst 4, Superhuman 13, Ultimate 31),
  ranged (Sharp Eye 8, Hawk Eye 26, Eagle Eye 44: accuracy and max hit),
  magic (Mystic Will 9, Lore 27, Might 45: accuracy only); Chivalry and Piety
  need Defence 65/70 and King's Ransom, which isn't in the quest set. Each
  adds floor(L + bonus x L) to the effective level at the swing.
- **Live** (`scripts/prayer_offence_test.py`,
  `results/live/prayer-offence-20261031-0553.json`): Strength 60 punches
  reached 8 only with Ultimate Strength on in the punch's tick (5 times), never
  above 7 otherwise; nothing drained. Every gap between a giant's swing and the
  nearest punch was even: a monster starts swinging on the character's swing
  ticks. With two even attack speeds the sides never swing in adjacent ticks,
  so flicking both is free; with an odd speed some swings are adjacent, and
  flicking both there drains.
- **Built so far:** `gamedata.server.prayers()` reads PrayerType.
- **Not built yet:** the sim side (prayer bonuses in the formulas and
  Fighter, zero damage from a protected style, skipping the offensive flick on
  swings adjacent to a protection flick), its tests, env contract v1.8 and the
  catalog's §4.

### Decided and built: defence prayers; prayer flicking in the sim's fights
Caleb, on the question of defence prayers: "Defence prayers don't need to be
flicked unless an enemy has multiple damage types or the agent does not have
access to the protection prayer associated." `m002-prayer-flicking-in-fights`.
- **Built** (env contract v1.8, decision 24; option catalog §4,
  "Prayers in fights"):
  - `rlscape/combat/prayers.py`: what a fight flicks, from
    `gamedata.server.prayers()` (PrayerType); the swings that get the
    accuracy and damage prayers
  - `rlscape/combat/formulas.py`: each player roll takes its prayer's bonus,
    floor(L + bonus x L), as the swing handlers do
  - `rlscape/combat/rates.py`: `Fighter.flicks`; a protected style deals
    nothing; defence (and, against magic, Mystic) prayers raise the defence
    rolls otherwise; damage per swing mixes boosted and plain swings
  - `rlscape/sim/combat.py`: each kill's swings follow that pattern
  - `rlscape/sim/equipment.py`: `fighter_for` gives the fighter its prayers
- **Multiple damage types:** the sim gives each monster one combat style, so
  that case isn't modelled; dragonfire stays the gear check.
- **Agent choices (reversible):**
  - on a tick next to a monster swing, the monster's tick keeps its prayer
    (protection or defence) and the character's swing goes without
  - against magic the defensive flick adds the best Mystic prayer, since
    magic defence is 70% Magic
- **Tests:** `tests/test_prayers.py` (7), including Strength 60's max hit of
  7, and 8 with Ultimate Strength, as measured live.
- **E1 baselines, 10 seeds x 20 hours** (`results/eval/guide-prayer-20261031`):
  guide total level 314, total XP 96k, net worth 110k (312, 94k, 108k
  before); random 234, 102k, 11k (235, 102k, 8k). Neither raises Prayer far
  (the guide's seed 0 ended at Prayer 5), so they get only the low prayers.

### Committed; the PR for sim v0
Caleb: "Commit the changes, then create the PR." `m002-commit-and-pr`.
- Fork `99152ea` on `rl`: the `prayer` command and the `debug_set_levels` fix.
- The main repo commit after `f47b7fb` holds the prayer-flicking work, with the
  submodule bump.
- Pushed the fork's `rl` (3 commits had never been pushed, and `sim-v0`'s
  submodule pointers name them) and `sim-v0`, then opened a PR from `sim-v0`
  to `main` with all of sim v0.

### Week-2 tests, the speed benchmark, and the first calibration slice
Caleb: "Keep going with the week-2 tests and calibration".
`m002-week2-tests-and-calibration`.
- **Tests** (`tests/test_sim_properties.py`): whole 20-hour episodes of
  masked random actions run every unmasked action, take time, and never send a
  count, coins, net worth or hitpoints negative; a seeded trajectory is the
  same in processes with other string-hash seeds (training's workers).
- **Benchmark** (`scripts/benchmark_sim.py`): 83 decisions a second in one
  process, 585 with 16 workers. Caching the nearest bank (each Fletching path
  asked for it, walking a route to every bank) made it 112 and 804. The
  contract's target is 20k: OQ-7, for Caleb. Most of the rest is the combat
  ranker recomputing the enemy pool after each combat level-up.
- **Calibration, first slice** (`scripts/calibrate.py`): woodcutting at the
  site, from the site's tile until the inventory is full, at bands 1, 31, 61
  and 91, against the sim from the same state. Travel and banking wait for
  bridge commands (OQ-4, extended). Found:
  - **The swing after a log comes 4 ticks later, not 3** (180 of 185); the
    code doesn't show why. Now `AFTER_LOG_TICKS`.
  - **The sites' overheads and counts:** the ticks to the first swing and from
    a fall to the next swing, and the trees used (normal trees: 14 or more,
    not 6; oak 3, not 2; yew 2, not 3), now kept with each site
    (`Site.first_attempt`, `next_attempt`) and used by the sim and the
    skilling slots' rate model.
  - **Ambient bots were on.** `rl.conf` had `enable_bots = true` and up to 100
    bots, against Caleb's decision of 2026-10-28 (env contract §7). Now
    `enable_bots = false` (fork, uncommitted). The other trees' results came
    out the same either way, and the live tests pass.
  - **The runner gets stuck at Draynor** when both near willows are down:
    `interact` clicks the nearest willow by name, out of reach, and `walk_to`
    doesn't clear it (OQ-4).
- **Result** (bots off, 10 runs a case; `results/calibration/
  gathering-20261031-1440.json`, `-1456.json`), sim over server XP/hr:

  | Site | Band 1 | 31 | 61 | 91 |
  |---|---|---|---|---|
  | Normal trees | 1.06 | 0.84 | 0.84 | 0.84 |
  | Oak | | 0.96 | 0.95 | 0.96 |
  | Willow (runs that finished) | | 1.02 | 0.82 | 0.89 |
  | Yew | | | 0.93 | 0.97 |

  All within ±20%. A run holds only 9 or 10 logs (the starter kit fills the
  rest), so a case's spread is wide: up to 41% of the mean per run.
- **The guide stalled on Firemaking** once the new rates changed the slots: it
  cuts its normal logs into arrow shafts, so it never had logs to burn. As
  for Smithing ("nothing to smith: mine it"), it now chops and burns when it
  has none (agent fix, for Caleb's review). E1, 10 seeds:
  guide 311 / 94k / 105k; random 234 / 106k / 6k.

### Decided and built: reachable targets and walk clicks; aggressive monsters; OQ-5 and OQ-6
Caleb, on the recommendations for the stalled willow runs: "Go ahead with 1
and 2". `m002-aggressive-monsters`.
- **Built** (fork `RLCommands.kt`, uncommitted):
  - `interact` clicks the target with the shortest walk among those the
    pathfinder reaches (`Pathfinder.find`, not "move near"), searching the
    character's map region and the eight around it; "none reachable"
    otherwise. Optional `ids` (one ore at a mixed mine) and `radius`.
  - `walk_to` with `packet=true` is a client's walk click, which clears what
    the character was doing.
  - `debug_nearby` (measurement only) lists what `interact` chooses from.
  - Live tests: the shortest reachable walk among Draynor Manor's dead trees,
    some unreachable; a rock picked by id; "none reachable"; a walk click
    ending a fishing script.
- **Correction to the week-2 entry: the willow stalls weren't an unreachable
  willow.** The listing shows all five willows near the site reachable, and the
  bundled bots' `getNearestNode` already skipped "move near" targets. A trace
  of a stall: a Dark wizard (aggressive, 7 to 8 tiles from the willows)
  attacks, auto-retaliate makes the character fight it, and the willow is
  abandoned. Caleb asked whether it was a random event: it isn't (they're off
  for RL characters).
- **Decided (Caleb), for aggressive monsters:** "If an aggressive monster
  interrupts a gathering action, the agent should try to safespot the monster
  and return to gathering. If it gets to a dangerous situation, the agent
  should run to safety." And: "A dangerous situation should be read as current
  hitpoints is less than twice enemy's max hit." Its details are OQ-8.
- **OQ-5, answered:** "Yes. Freeze the server as we begin calibration." The
  server version is frozen from 2026-10-31. (Claude had recommended it; the
  alternative was approving each upstream sync as it came.)
- **OQ-6, answered:** "the repository does not need to be public for
  submission. I likely only need to submit a report." Both repos stay private.

### Decided: no fights on a gathering task unless trivial
Caleb: "Do not fight monsters if you are on a gathering task, unless it would
be trivial to defeat them. If the setup's max hit is greater than or equal to
twice the monster's hitpoints and their max hit is less than .25x the agent's
health as it enters combat." Then: "I meant if the setup's max hit is at least
half the monsters max hitpoints. My mistake." `m002-gathering-fights`.
- **The rule:** a fight is trivial when the setup's max hit is at least half
  the monster's hitpoints and the monster's max hit is under a quarter of the
  character's hitpoints as the fight starts. Only then does a gathering
  character fight; otherwise it keeps gathering, and runs to safety when its
  hitpoints are under twice the monster's max hit (Caleb's earlier rule).
- **Still open (OQ-8):** where safety is, safespotting now or later, modelling
  aggressive monsters in the sim, and the fork changes the server runner needs.
  Claude asked; Caleb answered with the correction above, so they stay open.

### Decided: safety, safespotting, the sim's aggressive monsters, auto-retaliate
Caleb, on OQ-8's choices: "Safety is the agent is out of the monster's
aggressive range. Safespotting while gathering matters most for mining,
because many mines have bats or scorpions that try to bother players and gate
low-levels out of the mine. Or in the wilderness, where everything is
aggressive. Yes, model the aggressive monsters in the sim and recalibrate the
willows. Create a command to turn auto-retaliate off. Explain what you mean by
the other two bullets." `m002-aggression-answers`.
- **Decided:**
  - safety: out of the monster's aggressive range (the alternatives were the
    nearest bank, or ending the option there)
  - safespotting: built with mining, where it matters most (and the
    Wilderness), not for woodcutting now
  - the sim models aggressive monsters at gathering sites
  - a command to turn auto-retaliate off
- **Built:** `set_retaliate {uid, on}` (fork, uncommitted), as the options
  tab's button does (`Settings.toggleRetaliating`); `state` reports it; a live
  test. The calibration runner turns it off for gathering.
- **Found, with auto-retaliate off** (12 willow runs at band 31): the character
  never fights and keeps chopping when hit (12 or 13 swings after the first
  hit). Dark wizards landed 0 to 2 hits a run, 1 to 3 hitpoints in all.
- **Willows recalibrated** (`results/calibration/gathering-20261031-1611.json`,
  10 runs a band, every run full): sim over server XP/hr 0.89, 1.07 and 0.91
  at bands 31, 61 and 91. All within ±20%.
- **The server's aggression, read for the sim's model:** a monster checks for a
  target each tick, with a 3-in-11 chance, within 4 tiles (by default); it
  picks a character whose combat level is at most twice its own; and it stops
  picking one that has been in the region for 10 minutes. That timer runs on
  wall-clock time, so a sped-up server applies it late: OQ-9.
- **Explained, for Caleb's decision:** the two other bridge changes (OQ-8).

### Decided and built: who's attacking, attacking by index, tolerance in ticks; aggressive monsters in the sim
Caleb: "Go ahead with both OQ-8 changes and OQ-9 option a".
`m002-aggression-model`.
- **OQ-8, answered (both):** `state` lists the attackers (each NPC whose
  combat target is the character: id, index, name, tile, hitpoints), and
  `interact` takes an NPC `index`. The recommendation was both.
- **OQ-9, answered (a):** aggression tolerance counts game ticks
  (`Region.TOLERANCE_TICKS = 1000`, set where the character enters a region),
  not 10 wall-clock minutes. The alternative was leaving the server and
  calibrating aggression at 600 ms ticks.
- **Bug fixed in `debug_set_levels`:** it didn't recompute the combat level, so
  every calibration character looked level 3 to aggression. Dark wizards
  (level 7) pick only characters of level 14 or less: the band 31 to 91 willow
  stalls came from this. The sim now computes the same combat level
  (`CharacterState.combat_level`, tested against the server).
- **Measured at the willows** (`scripts/aggression_test.py`,
  `results/live/aggression-20261031-1634.json`; `scripts/calibrate.py` with the
  rule): a character standing on the site's tile is "engaged" half the time but
  never hit (the wizards can't reach it there); one chopping is hit. A
  woodcutting-only character (combat 3, 10 hitpoints): 4.5 damaging hits a
  run, 4 flees in 10 runs, a Dark wizard attacking about once every 29 ticks.
  No engagement starts after 1,000 ticks (tolerance in ticks, live-tested).
- **The sim** (`rlscape/sim/aggression.py`, in the gathering and fishing
  loops): a site's aggressors (aggressive, attackable, spawned within 10
  tiles); those whose level picks the character attack while it gathers, at
  the willows' measured rate, each attack rolled with the monster's hit chance
  and max hit against the character; Caleb's rule for trivial fights and
  running away (FLEE_TICKS measured, 4 flees); tolerance after 1,000 ticks in
  the region. Other sites use the willows' rates until calibrated. The skilling
  slots' rate model doesn't price it yet.
- **Calibration:** the woodcutting-only character at the willows, sim over
  server XP/hr 0.95 (within ±20%). E1, 10 seeds: guide 310 / 92k / 97k;
  random 232 / 103k / 14k; no deaths.
- **Server runner:** `scripts/calibrate.py` applies the rule (`Safety`), and
  `--levels` sets agent-like characters (woodcutting alone).

### Decided and built: mining calibrated; iron at Al Kharid; safespots
Caleb: "Move on to mining calibration with safespotting." On Claude's two
questions: "Iron at Al Kharid (Recommended)" (the alternatives: all its ores
the sim has, or not now) and, for the bridge command, "Go ahead
(Recommended)". `m002-mining-calibration`.
- **Why the question:** none of the sim's four mines has an aggressive monster
  within reach; the classic scorpion mine, Al Kharid, wasn't a site.
- **Mining calibrated** (`results/calibration/gathering-20261031-1851.json`, 10
  runs a case, 14 cases): the server's success per roll matches the sim's
  formula. A click starts mining's script, which waits 5 ticks before its first
  roll; from an emptied rock to the next roll is 9 to 10 ticks (the sim had
  8). Rocks used: copper 2, tin 2, Varrock iron 4, coal 14 (the sim had 3, 3,
  3, 8). With those (`mining.SITES`), every case is within ±20% (0.89 to 1.12;
  1.13 to 1.43 before).
- **Iron at the Al Kharid mine** (`mine_iron_alkharid`, kept or smelted: 81
  paths): the north cluster's 5 rocks, calibrated the same way (0.92, 1.02,
  0.96 at bands 31 to 91).
- **`safespots`** (fork, uncommitted): tiles beside a resource that the
  character can walk to and no aggressive melee monster that would pick it can
  hit it on, from the server's own rules (a melee monster hits only a victim
  orthogonally next to the tiles it covers, and gives up beyond 1.5 times its
  walk radius from its spawn), any monster size. The runner tries one when
  attacked (Caleb's rule).
- **Found:** Al Kharid's iron has no safespot for a level-3 miner: five
  scorpions (level 14, size 2) reach every rock. Lumbridge Swamp's copper has 15
  safe tiles. A level-3 miner at Al Kharid: a scorpion attacks about once every
  20 ticks (max hit 1), about 4 hitpoints per 100 ticks; mining goes on (sim
  over server 0.92; the sim's hit rate 4.1 per 100 ticks against 4.2). The
  first safespot query only checked the one attacker; another scorpion guards
  the tiles it found, and a test character walking there died: now every
  eligible melee monster counts.
- **E1, 10 seeds** (`results/eval/guide-mining-20261031`): guide 311 / 98k /
  108k; random 222 / 93k / 13k (232 / 103k / 14k before: mining is slower on
  the calibrated sites).

### Decided and built: fishing calibrated; shrimp at Lumbridge Swamp too; Draynor's wizards engage
Caleb: "Calibrate fishing." Two questions came up (`AskUserQuestion`).
`m002-fishing-calibration`.
- **Where to fish shrimp.** Draynor's shrimp spots kill a level-3 fisher.
  - Two Dark wizards (level 7, magic, max hit 2) attack it, and keep casting
    as it runs away under Caleb's rule. The sim had running away as safe: in
    the first trial the server made 187 XP/h, the sim 1,225.
  - The options:
    - move `fish_shrimp` to Lumbridge Swamp (recommended)
    - fish shrimp at both sites (83 paths; Draynor then needs the danger
      modelled)
    - keep Draynor only, and model the danger
    - keep Draynor as a known gap
  - Caleb: **"Both sites"**. `fish_shrimp_swamp` uses Lumbridge Swamp's three
    net spots.
- **The scripted guide.**
  - The guide fished shrimp at Draynor at combat 4 to 11, and now died there.
    Seed 0 ended 20 hours with Fishing 4 and Cooking 2.
  - The options:
    - the swamp while the wizards would attack (combat 14 or less), then
      Draynor (recommended)
    - always the swamp below Fishing 20
    - leave it at Draynor
  - Caleb: **"Swamp below combat 15 (Recommended)"**.
- **Calibrated** (sim over server XP/hr; 10 server runs a case; 80 for
  Draynor at band 1). The fishing cases drop the starter kit, so a load is 26
  or 27 fish and the spots move during it, as in training. Every case is
  within ±20%.

  | Path | Band 1 | 31 | 61 | 91 |
  |---|---|---|---|---|
  | `fish_shrimp` (Draynor) | 1.08 | 0.96 | 0.97 | 1.00 |
  | `fish_shrimp_swamp` | 1.04 | 0.99 | 0.97 | 0.99 |
  | `fish_fly` | | 1.00 | 0.98 | 0.98 |
  | `fish_lobster` | | | 0.94 | 0.98 |

  Server runs: `results/calibration/gathering-20261031-2042.json` and
  `gathering-20261101-0126.json`, `-0134`, `-0153`, `-0203`, `-0219`.
- **Ported or measured** (`rlscape/sim/fishing.py`):
  - The first attempt comes 2 ticks after the click beside a spot. The
    attempt after a catch comes 6 ticks later, not 5 (507 of 532 catches).
    The slots' rate model counts both.
  - A spot moves only if the tile it picks has no NPC on it, itself included
    (`FishingNPC.moveSpot`). So with n spots on a group's t tiles, a move
    happens with chance 1 − n/t: never for Draynor's two spots on two tiles;
    0.6 at Barbarian Village and Lumbridge Swamp, 0.62 at Catherby.
  - The angler starts on the group's first tile with a spot of its kind.
    Tiles over 20 from it are elsewhere: Lumbridge Swamp's group has one by
    Lumbridge Castle, 90 tiles north.
- **Draynor's wizards engage** (40 traced server runs).
  - One wizard at a time engages (single-way combat). It then casts every 5
    ticks until the character runs, and goes on casting as it runs.
  - Per run away: 1.49 damaging hits, and 51% end in death. The rule runs at
    2 or 3 hitpoints, under twice the wizard's max hit of 2.
  - The sim spread attacks evenly, so a fisher healed between hits. The
    sim's aggression now takes a site's measured exposure (`SiteExposure`).
    At Draynor's shrimp spots: an engagement every 221 ticks per wizard, a
    5-tick cadence, 3.19 attacks taken per run away, and 60 ticks away and
    back.
  - The willows and Al Kharid keep their measured rates (engaged
    throughout). Checked against their saved server runs: low-level
    woodcutter 0.91, low-level miner 0.92, mining 0.89 to 1.12.
  - A character can now die of attacks while it runs, and an option that
    ends in death ends at the death, not at the start of the wait it died in.
  - Draynor's level-3 fisher: the server makes 1,292 XP/h with 0.88 deaths
    a run (80 runs); the sim makes 1,393 (1.08) with 0.82.
- **For combat calibration:** the Dark wizards' configured attack speed is
  the default 4, but they cast every 5 ticks (every gap between hits is a
  multiple of 5).
- **The runner** (`scripts/calibrate.py`):
  - fishing cases: a method's spot NPC ids; the shore tile, found by walking
    off the spot's tile; bait given at setup
  - a run ends at a death
  - hits are counted by the rule's mode
  - the trace records hitpoints, mode and attackers each tick
  - safespots are tried only against melee attackers, since a caster hits
    from range
- **E1** (`results/eval/guide-fishing-20261101`, 10 seeds): guide 316 /
  94.6k / 103k; random 215 / 90.4k / 9.3k.

### Decided and built (part): travel on the server's map, banking by clicks; boats and teleports decided
Caleb: "Commit this, then move on to travel and banking." Committed: fork
`84102f9`, main repo `346afd8`. Then, mid-work: "Make sure travel includes
charter boats and teleports." Four questions (`AskUserQuestion`);
`m002-travel-and-banking`.
- **How long walks are made on the server.** A walk click goes at most 24
  tiles in a straight line and the server's pathfinder only searches near
  the character, so a long walk is a route of clicks.
  - The options:
    - export the server's collision map and plan routes in Python, which
      the sim can use too (recommended)
    - hand-made waypoints per trip, as the bundled bots do
    - a server-side walker
  - Caleb: **"Collision map + planner (Recommended)"**.
- **Bank commands (OQ-4, answered).** OQ-4 asked for the go-ahead on the
  fork changes for shop buys, putting gear on, bank withdrawals and
  `bank_deposit_worn`.
  - The options:
    - two generic player-path commands, `interface_button` and
      `interface_item` (recommended)
    - bank-specific commands
    - deposits only for now
  - Caleb: **"Generic interface clicks (Recommended)"**. These cover bank
    deposits (worn items too), withdrawals and shop buys. Gear goes on with
    `item_option` ("Wield", "Wear").
- **Who chooses a boat or teleport.**
  - The options:
    - every walk takes the fastest way the character can use, automatically,
      paying from what it carries (recommended)
    - free transports automatic and paid ones as agent actions
    - all transports as agent actions
  - Caleb: **"Fastest usable, auto (Recommended)"**.
- **Which teleports.**
  - The options:
    - the standard spells and the home teleport (recommended)
    - also teleport jewellery and tablets, whose items join V
    - spells only
  - Caleb: **"Also jewellery and tablets"**. Which items and charges join
    V is OQ-10.
- **Built** (fork, uncommitted):
  - `debug_collision`: an area's collision flags and its doors and gates;
    tests and data export only
  - `interface_button` and `interface_item`: the client's IfAction packet
  - in the state: the open interface, the open chatbox dialogue and the
    last 20 game messages, as a player sees them (the messages are kept by
    `PacketDispatch.sendMessage` for RL characters)
  - the bridge's auto-dismissal (an earlier agent interpretation, decision
    log 2026-10-05) closed every interface each tick, the bank included. It
    now dismisses only messages, and leaves choice menus and the interfaces
    a character opens to use (bank, deposit box, shop, GE, ship charter)
    open. Reversible.
- **Built** (main repo):
  - `scripts/export_collision.py` and `data/travel/`: the surface from x 2304
    to 3839 and y 2688 to 4031, and 920 doors and gates
  - `rlscape/routes.py`: the server's step rules
    (`SmartPathfinder.checkSingleTraversal`'s masks); doors are steps that
    cost opening them; the toll gate and locked doors are excluded
  - `rlscape/bridge/walker.py`: clicks along the route, opening doors
  - `scripts/calibrate_travel.py`
- **Measured:**
  - The server walks the planned length exactly: 144 tiles planned, 144
    walked.
  - Walking: ticks ≈ steps / 2 + 2.3 + 0.083 × steps, from 15 to 166
    steps, running. The 2.3 is the start; the rest is a standing tick
    about every 18 and odd-length hops.
  - Banking: 7 ticks from clicking a booth to an empty inventory (the sim
    has 8).
  - The sim's walks against the server, on 12 site-to-bank trips: short
    trips 0.50 to 0.73, long ones 0.91 to 1.02
    (`results/calibration/travel-20261101-1336.json`). The sim's nearest
    bank by straight line is sometimes wrong: Al Kharid instead of
    Lumbridge's castle bank or Draynor; the Grand Exchange instead of
    Edgeville.
- **Found:**
  - The bridge's direct `interact` registers a click after the tick's
    pulses. Interactions run as scripts (bank booths, for one) then cancel
    themselves ("I can't reach that!"), so executors click as packets.
  - The bank opens one tile before the character arrives when the last hop
    is odd, and still stays open.
- **Next:**
  - the sim on planned routes (a table between the places it travels, with
    the measured overheads)
  - stairs and ladders (Lumbridge's castle bank), the dungeons' maps (the
    coal site), banking at the Grand Exchange
  - the transports: ships, charters, spells, the home teleport, jewellery
    and tablets
  - then recalibrate

### Decided: the state fields approved; OQ-10 answered (teleport items)
Caleb: "Approve the state fields, commit, then switch the sim to planned
routes. For OQ-10, all teleport jewelry at all charge levels are usable for
teleporting and should be purchasable at any charge level as well. Notably,
there are some teleport items that are consumable like teleport tablets".
`m002-planned-routes`.
- **The state fields** (fork): the open interface, the open chatbox dialogue
  and the last 20 game messages. Approved; committed.
- **OQ-10, answered.** The question was which teleport jewellery and tablets
  join V, at which charges. Claude's starting point: the server's teleport
  jewellery that reaches the sim's map, and the standard teleport tablets,
  each charge state its own item.
  - Caleb: every piece of teleport jewellery, at every charge level, is
    usable for teleporting and buyable at any charge level.
  - Consumable teleport items, such as teleport tablets, count too.
  - The items list comes from the server's data when the transports are
    built (a catalog and env contract change).

### Decided: the Ectophial is a transport
Caleb: "Add the ectophial." Claude had proposed leaving it out (a reusable
quest item, neither jewellery nor a consumable). `m002-planned-routes`.
- **On this server** (`EctophialListener`): it needs Ghosts Ahoy. "Empty"
  teleports to the Ectofuntus in Port Phasmatys (3658, 3517) and it refills
  itself there on arrival, so it's free and reusable without limit. It isn't
  bought: Velorina gives one, or a replacement, after the quest.
- **Left out of the transports, as Claude proposed:** the ring of life (an
  emergency teleport at low hitpoints, not travel) and the house tablet (the
  sim has no player-owned houses).
- **Gap:** neither Ghosts Ahoy nor Priest in Peril, which it needs, is in the
  21-quest set, so the Ectophial is unusable until they are (OQ-11).

### Decided: Priest in Peril and Ghosts Ahoy join the quest set (OQ-11); the Grand seed pod is a transport
Caleb: "Add both for a later episode. Also add the seed pod from The Grand
Tree." `m002-planned-routes`.
- **OQ-11, answered.** The question was whether to add Priest in Peril and
  Ghosts Ahoy (which the Ectophial needs) to the 21-quest set.
  - The options: (a) add both (recommended); (b) add neither, leaving the
    Ectophial unusable.
  - Caleb: "Add both for a later episode." Claude reads this as both joining
    the set (23 quests), as quests an episode reaches late: members, Priest
    in Peril, The Restless Ghost, Agility 25 and Cooking 20 come first. To
    confirm if "a later episode" meant a later stage of the project instead.
- **The Grand seed pod** (9469; `GrandSeedPodHandler`): a consumable
  teleport. "Squash" goes to the Grand Tree (2464, 3494); "launch" goes to
  the Ta Quir Priw glider and gives 100 Farming XP.
  - On this server it comes as a Gnome Restaurant tip. It's on the 2009 GE
    at 927 gp (stackable, members), so under OQ-10's rule it's usable and
    buyable.
  - The server has no Royal seed pod (Monkey Madness's reusable one).

### Built: the sim walks the planned routes
Caleb's "switch the sim to planned routes" (`m002-planned-routes`).
- **How:**
  - `rlscape.travel.path` gives the planned walk in steps. A table covers
    the places the sim travels between (`data/travel/places.csv`: 2,667
    tiles, 2,132 anchors), and any other tile is searched when first asked
    for. Upper floors and dungeons are taken at the surface tile they lie
    over or under, with their level changes as before.
  - A walk adds the measured overheads, 2.3 ticks to start and 0.083 a step,
    as rest for run energy (`movement.timed`). `energy.walk_plan` stays the
    server's `WalkingQueue`, tested tick by tick.
  - Off the map, or with no walk on foot, a walk is still straight line ×
    1.3, counted in `travel.unplanned`.
  - The combat ranker uses the same lengths, several at once
    (`Destinations`), exactly as `travel_ticks`.
  - The combat pool's spawn-to-bank trips take one search from each bank.
    One per spawn took about 70 s at every process start.
- **The toll gate:** a walk between Al Kharid and west of its fence goes
  round the fence on the planned route, or through the gate when that's
  shorter and the toll is waived or can be paid. The estimated fence end is
  gone. Buying's toll estimate asks the same rule (`movement.pays_toll`).
- **Checked:**
  - The 12 measured site-to-bank trips, both ways: the sim is within 0.95 to
    1.12 of the server, against 0.50 to 1.24 before. The overheads were
    fitted on the outbound legs, so the returns are the out-of-sample check.
  - Every gathering calibration, rechecked against its saved server runs, is
    unchanged and within ±20%.
  - E1 (`results/eval/planned-routes-20261101`, 10 seeds), with short trips
    now as slow as on the server: guide 301 / 85.6k / 89.2k; random 208 /
    82.0k / 12.0k (before: 316 / 94.6k / 103k and 215 / 90.4k / 9.3k).
  - Speed (OQ-7): 78 decisions a second in one process and 553 with 16
    workers, about 30% slower than before.
  - Tests: 292 passed (40 live, with the server up).
- **Found:**
  - From the spawn, 903 of the 2,280 combat sites, banks and stations can't
    be walked to, and 508 are off the map. Islands (Karamja, Entrana,
    Crandor, Mos Le'Harmless) need boats; West Ardougne, Canifis (the Salve),
    Troll country and the desert sit behind quests or gates. But the whole
    Wilderness is cut off by its ditch ("Cross"), and the Gnome Stronghold
    likely by its gate: the planner doesn't know those crossings yet. They
    come with the transports, and meanwhile fall back to the straight line.
  - A pre-existing bug, found by the speed benchmark: three items (blurite
    limbs, an oak stock, a nasturtium seed) carry a requirement on skill
    index 24, past the sim's skills, and wielding raised on them. Such a
    requirement now can't be met.

### Built: transports, teleports and crossings; travel validated
Caleb: "Add the transports, teleports, and crossings, then validate the travel."
`m002-transports`.
- **The transports** (`rlscape/gamedata/transports.py`, read from the server's
  source and data where it has them):
  - the home teleport (free) and the standard spells to Varrock, Lumbridge,
    Falador, Camelot, Ardougne (Plague City), the Watchtower, Trollheim
    (Eadgar's Ruse) and Ape Atoll (Monkey Madness): Magic level and runes,
    with elemental staves standing in for their runes
  - teleport jewellery (`EnchantedJewellery`), every piece at every charge:
    glory, glory (t), games necklace, ring of dueling, combat bracelet, skills
    necklace, ring of slaying, digsite pendant (29 destinations). A use moves
    the piece one charge down, crumbling or going uncharged at the end.
  - 20 tablets (`TeleportTablet`): the 6 city tablets and the 14 Runecrafting
    altars', with their quests; consumed
  - the Grand seed pod ("squash" and "launch") and the Ectophial (Ghosts Ahoy)
  - 5 fixed ships with their fares: Port Sarim to Musa Point and back,
    Brimhaven to Ardougne, Port Sarim to Entrana and back (no weapons or
    armour); 84 charters between 11 ports (`ShipCharter`: its fare table and
    quest-locked ports; a fare of 0 there means the trip isn't offered)
  - teleports respect the Wilderness: none above level 20, jewellery up to 30
  - 67 teleport items in all; they aren't in V yet
- **The routing rule** (Caleb's "fastest usable, auto"), the same on both
  backends: a walk takes the fastest of walking; a teleport then a walk; a walk
  to a boat, the boat, then a walk; a teleport, a walk, a boat and a walk.
  Straight-line lower bounds prune the search. Each way counts what the
  character can use now (levels, quests, the runes, coins, jewellery or
  tablets it carries) and pays for it. If none of them reaches the place, the
  straight-line estimate remains (OQ-12).
- **Estimates without a character** (the combat and skilling candidates'
  travel) take the better of the walk and the home teleport then a walk,
  except deeper than Wilderness level 20.
- **Crossings** in the planner (`rlscape/routes.py`, `data/travel/crossings.csv`,
  exported by the fork's `debug_collision` `objects`): the Wilderness ditch
  (325 pieces), the Gnome Stronghold's gate and the Grand Tree's doors, each
  between the tiles its handler moves the character, costing 2 steps; the Al
  Kharid toll gate only for a walker that pays it. Walkable from the spawn on
  foot: 1,063 of the 2,280 places (869 before), now with the Wilderness and
  the Gnome Stronghold. 709 still need a boat, a quest or a gate; 508 are off
  the map.
- **The server side** (`rlscape/bridge/travel.py`): each transport as a player
  takes it, by packet clicks. Spells from the spellbook (192); jewellery
  "Rub" and its menu; tablet "Break", seed pod "Squash", Ectophial "Empty";
  "Pay-fare" on a ship's NPC with the answers its conversation asks for (before
  Pirate's Treasure); "Charter", the destination on the charter interface (95)
  and "Ok"; then "Cross" the gangplank. The walker crosses the ditch, the
  gate, the doors and the toll gate by their options.
- **A fork change to approve** (uncommitted): the bridge's auto-dismissal now
  clicks "continue" through a conversation's messages, as a person does, and
  closes only a message box outside any conversation. Before, it closed the
  whole conversation, which ended the charter's fare dialogue before its
  choice. Choices and the interfaces a character uses stay open, as before.
- **Measured and fitted** on 14 trips (`travel-validation-20261101-1829.json`),
  as ticks from the first click to walking on: home teleport 22, a spell 6, a
  tablet 7, jewellery 10 (the menu takes a few ticks), the seed pod's squash
  14, a ship's NPC conversation 11 beyond the sailing, a charter 17, the
  gangplank 3. The fitted trips came out 0.84 to 1.15 of the server, every one
  within ±20%; the seed pod is the lowest.
- **Validated** on 13 fresh trips (`travel-validation-20261101-1828.json`): walks
  (Rimmington, Taverley, Draynor, into the Wilderness to level 5), the home
  teleport, then the toll gate, paid, into Al Kharid; the home teleport from
  Falador; the Falador spell; the Lumbridge tablet; glory to Draynor; the ring
  of dueling; the games necklace to the Barbarian Outpost; the charter from Port
  Sarim to Catherby; the ship from Brimhaven to Ardougne. The sim over the
  server: 0.94 to 1.15, all 13 within ±20%, and the sim chose the expected
  transport every time.
- **E1** (`results/eval/transports-20261101`, 10 seeds): guide 333 / 116k /
  132k; random 221 / 98.0k / 12.6k (planned routes: 301 / 85.6k / 89.2k and
  208 / 82.0k / 12.0k). Most of the gain is the free home teleport back to
  Lumbridge from wherever a task ends.
- **Speed (OQ-7):** 69 decisions a second in one process and 499 with 16
  workers (`sim-speed-20261101-1838.json`; 78 and 553 before).
- **Tests** changed by the home teleport, as the server does it: a gravestone
  deep in the Wilderness is reached on foot; returning from the toll gate and
  the desert is faster by teleport, so those tests check the walk itself. The
  guide's Prayer stint now ends at level 4 or above (the bones it buries give
  342 XP).
  The suite: 298 passed, with the server up.
- **Found:**
  - The home teleport has no cooldown on this server (2009's was 30
    minutes), so it's free and repeatable (OQ-13).
  - Ghosts Ahoy isn't implemented on this server (only named in its quest
    list), so the Ectophial can't be used there, and OQ-11's Ghosts Ahoy can't
    be played on the server (OQ-14). Priest in Peril, Pirate's Treasure and
    Plague City are implemented.
  - Captain Barnaby (Ardougne to Brimhaven) isn't spawned on this server, so
    that ship is left out; the way back runs.
  - Entrana's monks' conversation isn't validated yet, nor the seed pod's
    "launch"; their times are the source's.
  - The Zogre area (Feldip Hills) is unreachable on foot for no clear reason;
    to look at.

### Decided and built: the home teleport waits 30 minutes (OQ-13); Ghosts Ahoy and the Ectophial out (OQ-14); a place with no way is unreachable (OQ-12)
Caleb: "Ignore the Zogre area. It is for the Zogre Flesh Eaters quest. I don't
know if that quest is implemented on the server, but I don't think there is
much value to completing it. Since Ghosts Ahoy is not implemented, you can
remove the ectophial and the quest from the list. Home teleport should have a
30 minute cooldown." Then, during the work: "For OQ-12, there are a few places
that cannot be reached by foot, teleport, or boat that can be reached if you
use an item or as part of a quest. However, if there really is no way to get to
a place on the map, make it unreachable." `m002-travel-rules`.
- **OQ-13, answered: the home teleport waits 30 minutes.** The question was
  whether to keep the server's home teleport without a cooldown or add January
  2009's 30 minutes.
  - The options: (a) keep the server's behaviour (recommended: the sim
    matches the server it's validated against); (b) a 30-minute cooldown in
    the fork and the sim.
  - Caleb: **(b)**, a 30-minute cooldown.
- **OQ-14, answered: Ghosts Ahoy and the Ectophial are out.** The question was
  what to do now that the server has no Ghosts Ahoy (the Ectophial needs it).
  - The options: (a) take Ghosts Ahoy and the Ectophial out, keeping Priest
    in Peril (recommended); (b) also take Priest in Peril out; (c) implement
    Ghosts Ahoy in the fork; (d) keep it in the sim only.
  - Caleb: remove the Ectophial and Ghosts Ahoy. Priest in Peril stays as
    OQ-11 had it, a reading still to confirm. The catalog's quest set still
    lists the 21.
- **OQ-12, answered: a place with no way there is unreachable.** The question
  was what a trip does when nothing reaches its place.
  - The options: (a) unreachable, masked (recommended); (b) keep the
    straight-line estimate; (c) (a) once the remaining gaps are mapped.
  - Caleb: (a), where there's really no way. Some places that no walk,
    teleport or boat reaches can be reached with an item or as part of a
    quest; those stay reachable once their ways are in.
- **The Zogre area** is the Zogre Flesh Eaters quest's (Caleb): left alone, not
  worth completing. With OQ-12 it's unreachable.
- **Built:**
  - Fork (uncommitted): `homeTeleport` (all spellbooks share it) refuses
    within 3,000 game ticks of the last teleport: "You need to wait another N
    minutes to cast this spell." (Claude's wording; the 2009 message isn't in
    the source.) It counts game ticks, as aggression tolerance does, so a
    sped-up server behaves the same. The bridge's `state` reports
    `home_teleport_ready_in`, in ticks.
  - Sim: the character's `home_teleport_ready` tick; a walk takes the home
    teleport only when it's ready, and taking it sets the next. Estimates count
    it for trips from where the character is, when it's ready (the candidates'
    travel and the skilling rates); trips an option repeats (bank trips)
    walk.
  - The Ectophial is gone from the transports and the server executor.
  - **Unreachable** (`rlscape/travel.py`): a place no way the model knows gets
    to, for any character, has no walks: walking and the crossings, the
    Shantay gate, every teleport, every boat, from Lumbridge. Upstairs and
    underground places keep the straight-line estimate, since their stairs and
    ladders aren't mapped yet: that's a gap in the map, not "no way".
  - A walk with no way the character can use now (no fare, no runes, Entrana's
    monks turning it away) is `None`, so its option is masked. Before, it
    crossed the water on the straight line.
  - The combat ranker uses the same reach (`rlscape.sim.movement.reach`: a walk,
    a teleport the character can use, at most one boat it can pay for, the
    Shantay gate if it can buy a pass), so a slot never holds a site the mask
    then closes.
- **Measured** (the live test `test_the_home_teleport_waits_30_minutes_of_game_ticks`,
  at 15 ms ticks): cast; then refused ("You need to wait another 30
  minutes"); then cast again once the ticks the state reported had passed.
- **Cut by the rule:** 231 of the 2,792 places, 206 of them combat sites, and
  the Shilo Village bank. By area (Claude's reading, to check):
  - behind quests outside the set: West Ardougne (Plague City), Mos
    Le'Harmless, Shilo Village, Troll country, the Fremennik Isles, Tirannwn,
    the Fight Arena, Gu'Tanoth, the Zogre area
  - behind Dragon Slayer, which is in the set: Crandor (its ship, and after
    it the wall from Karamja's volcano), a way to add with the quests in sim v1
  - pens and cells: the Ardougne Zoo, Port Sarim's jail
  - behind an Agility shortcut or an item: the moss giant island by
    Brimhaven (a rope swing), Marim on Ape Atoll (a greegree), the Mage Arena
    (a lever)
  - unclear, perhaps the planner's gaps: Wilderness spots (lesser and greater
    demons, hill giants, a red dragon, battle mages, skeletons), the ice giants
    by White Wolf Mountain, Tree Gnome Village, a dwarf by Ice Mountain, a
    grizzly bear and a Monk of Zamorak north of Varrock, the Kharazi jungle
- **Found and fixed on the way:**
  - The nearest-bank cache keyed on less than a walk now depends on (the
    teleports the character can use, the home teleport, quests). The property
    test found it.
  - The combat ranker and its reference broke exact ties by float noise:
    ammunition caps many candidates at the same XP/hr, and the two compute it
    in different orders. Both now compare rates rounded to 6 decimals.
  - The speed benchmark found a walk from just off the planner's map (a rabbit
    by Isafdar, x 2297) to the Shilo Village bank counted as on foot but
    infinitely long. Off the map, a walk to a place with no way is no walk
    either (a test now covers it).
  - The character's reach cost a fifth of the time at first (a search per new
    set of boats and teleports). Each part of the map it starts from is now
    searched once and remembered.
- **Checked:**
  - Tests: 299 passed with the server up, the new live test included; after
    the last two fixes (sim only), 259 passed offline.
  - The home teleport's trips on the server, rerun: 0.96 (from Varrock), 1.06
    (from Falador), 0.96 (then the toll gate); and the charter 1.11
    (`travel-validation-20261101-2020.json`).
  - E1 (`results/eval/travel-rules-20261101`, 10 seeds): guide 322 / 102k /
    110k; random 216 / 89.7k / 12.0k (with a free home teleport: 333 / 116k /
    132k and 221 / 98.0k / 12.6k).
  - Speed (OQ-7): 71 decisions a second in one process, 489 with 16 workers
    (`sim-speed-20261101-2042.json`), as before.

### Built: combat calibrated (melee and ranged, without looting); two fork fixes; site capacity in the rates
The current plan, continued (Caleb, 2026-11-05: "Let's continue with the
current plan for now and reevaluate on Sunday"). Claude took combat
calibration first, the biggest piece left. `m002-combat-calibration`.
- **The runner** (`scripts/calibrate_combat.py`): the fights the sim's own
  ranker picks (a slot: 0 the top by XP, 3 the top by gp), for a calibration
  character at bands 1, 31, 61 and 91 with standard gear for the band and food,
  at the monster's site, a click at a time, eating at half hitpoints; Prayer at
  1 on both sides, so neither flicks (flicking was live-tested on its own); the
  accurate style; drops left (the bridge can't pick items up). `--resim`
  rescores saved server runs against the sim as it is now.
- **Two fork fixes, found by the first runs** (uncommitted; the second to
  approve):
  - The bridge's `interact` chose NPCs that were dead or waiting to respawn
    (the nearest scorpion was the one just killed). It now skips any the
    player can't see (`NPC.isHidden`, `DeathTask.isDead`), as a player would.
  - **"In combat" counted wall-clock time.** Being hit set `combat-time` to now
    + 10 seconds of wall-clock time (`CombatPulse`), which single-combat areas
    read (`MapZone.checkMulti`: "You're already under attack!"). At 50 ms ticks
    that's 200 ticks, not 17, so on the sped-up server an aggressive monster
    locked the character out of attacking another for twelve times too long.
    The scorpions' kill rate was half. Now it counts 17 game ticks (10.2 s at
    600 ms), as tolerance does (`Entity.COMBAT_TIME_TICKS`). After the fix, the
    same fight at 600 ms and at 50 ms: 13,671 and 13,352 XP/hr. This was G1's
    open item (ROADMAP §3).
- **What the sim lacked, measured:** kills slow down where a site runs short of
  the monster. Draynor's two market guards, back 60 ticks after dying, held a
  band-91 fighter to one kill every 46 ticks; the sim had 32. Now the rates and
  the sim's fights take each site's spawns of the monster within 15 tiles
  (`npc_spawns.json`) and its respawn delay (`npc_configs.json`): a kill comes
  at most every (respawn + fighting) / spawns ticks; in the sim's fights each
  monster has its own respawn, and nothing attacks during the wait. The ranker
  now prefers sites with more of the monster.
- **The overhead between kills, fitted** on the first eight cases (rats,
  scorpions, market guards): 10 ticks for melee, 8 for ranged (it attacks from
  a distance: 5 ticks at packed rats, 12 among the scorpions' rocks); magic
  taken as ranged, uncalibrated. It was a 6-tick placeholder.
- **Results, XP/hr sim over server:**
  - fit set (`combat-20261105-1936-resim.json`): 0.88 to 1.13, all 8 within
    ±20%
  - the ranker's new top-XP picks (`combat-20261105-2007-resim.json`): three
    repeat fit cases on fresh server runs, 0.93 to 1.05; the five new ones
    1.00 to 1.13, and 1.22 for ranged at poison spiders
  - its top-gp picks (`combat-20261105-2037-resim.json`): 0.99 to 1.18 for
    hobgoblins and unicorns. The four Black Knight cases got nothing on the
    server: see below.
  - So 8 of the 9 cases not fitted on are within ±20%.
- **Not right yet:**
  - **Poison isn't modelled.** At poison spiders the server's fighters ran out
    of food every run (187 to 250 eaten an hour); the sim ate 9 to 48.
  - **Ranged fighters take more damage on the server**: food eaten 1.4 to 1.8
    times the sim's (market guards at band 31, moss giants, hobgoblins).
  - **The Black Knights in a Taverley dungeon room** (id 178, 2942, 9801):
    the server takes the click and does nothing, with no message; the
    character can walk there. To investigate; meanwhile the sim offers them.
  - Looting isn't measured (no pickup command: OQ-18), nor magic (no
    cast-on-NPC click yet), nor the escape attacks on retreat.
- **The aggression cases rerun after the fix** (5 to 10 runs): the mining-only
  character at Al Kharid's iron 0.96, the fresh fisher at Draynor 1.09 (deaths
  0.90 a run, the sim 0.81). The woodcutting-only character at the willows came
  out 0.68 on short runs (10 free slots) with a death in 5: the willows'
  measured exposure (attacks a tick, flee time) dates from the wall-clock lock
  and needs measuring again.
- **Tests:** a site short of monsters slows kills as the rate model says; the
  slot test's magic character wears the bronze dagger the sim wields (+1 magic
  attack), which the capacity model made matter. 301 passed with the server
  up (the fork's fixes in it, every live test included).

### Decided and built: "in combat" in game ticks approved; the pickup command (OQ-18); Taverley's eastern Black Knights are hazards; each bridge character has its own account
Caleb, 2026-11-05: "Approve the combat-time change and the pickup command.
Remove the taverley dungeon black knights from the list of enemies that can be
fought. They should be treated as hazards, instead." `m002-looting-and-hazards`.
- **Approved: "in combat" counts 17 game ticks** (`Entity.COMBAT_TIME_TICKS`;
  the entry above), not 10 wall-clock seconds.
- **OQ-18, answered: a pickup command.** The question was whether to give the
  bridge a way to pick items up, so looting could be calibrated.
  - The options: (a) a `take` command sending the client's ground-item "Take"
    packet, then loot-on calibration runs (recommended); (b) leave looting
    uncalibrated and say so.
  - Caleb: (a).
  - Built in the fork (uncommitted):
    - `ground_items`: what the character sees on the ground within a radius,
      nearest first: its own drops while they're private to it, and the
      public ones (`GroundItemManager.get`'s rule). Each with id, name,
      amount, tile, and `own`.
    - `take`: clicks "Take" on one, by tile or the nearest it can walk to,
      handled as the client's `GroundItemAction` packet is (`packet=true`
      queues the packet itself). Both are player-facing: a person sees the
      items and clicks them.
- **Found on the way, fixed (a fork change to approve): every bridge
  character had account uid 0** (`AIPlayer`'s default) and wasn't in
  `Repository.uid_map`.
  - The game tells players apart by that uid. A kill goes to the player who
    did most damage, looked up by uid (`ImpactHandler.getMostDamageEntity`),
    so a bridge character's kill went to no one and **dropped nothing**.
    That also cost the kill's credit: Slayer tasks, quest kill counts.
  - The uid also says whose drops are private to whom, whose gravestone
    is whose, and which character the GE notifies of an offer's progress.
    Two bridge characters shared all of these.
  - Now each `RLPlayer` gets its own (`1,000,000,000` + its bridge uid), set
    before the login hooks load its GE records. It's in `uid_map` until
    despawned.
  - This is what "treated as a human by every game rule" needs. Live tests: a
    chicken's bones are its killer's, and taken from their tile; another
    character doesn't see a private drop.
  - Left as it was: the bridge uid restarts with the server, so a character
    can get a uid a character had before a restart and load that one's
    unfinished GE offers. It was worse before, with every character on 0.
    The GE database is reinstalled before experiments.
- **Hazards: Taverley dungeon's two Black Knights east of the lesser demons**
  (id 178; spawns 2942, 9801 and 2938, 9812).
  - They're never offered as targets. `HAZARDS` in
    `rlscape/combat/candidates.py` takes an NPC's spawns in an area out of the
    enemy pool.
  - They stay in the world. The aggression model reads every spawn, so they'd
    still attack a gathering character beside them (no gathering site is
    that near now).
  - Claude's scope (to confirm): only this pair. Checked live, the dungeon's
    other 12 Black Knights, by the jail, fight as usual: 842 XP in 150 ticks
    at band 61. The pair took the click, and the character never moved.
  - With the pair out, the ranker's top gp pick at bands 61 and 91 is the
    lone Black Knight by Draynor (3096, 3220).
- **New question:** a fight ignores the aggressive monsters around its site
  (OQ-19).
- **The runner loots:** `--loot` takes a loot mode (option catalog §4.D).
  - After a kill it waits for the drop, up to 6 ticks (`DeathTask`'s default
    death animation).
  - While nothing attacks it, it takes the nearest of its own drops that the
    mode keeps and has room for, arrows included.
  - It stops when the inventory is full and the mode keeps a drop that needs a
    slot.
  - Both sides report loot as gp/hr: the value of what the inventory gained,
    leaving out the ammunition.
  - The fit set's monsters (rats, scorpions, market guards) have no drop
    tables, so the loot runs use the ranker's top picks by gp.
- **The first loot runs** (`combat-20261105-2247-resim.json`; the ranker's top
  gp picks, loot mode valuable, 3 runs a case), sim over server:
  - **XP/hr and kills/hr: 0.80 to 1.15, all 8 within ±20%.** Ranged at
    band-1 hobgoblins is at the edge.
  - **The time to a full inventory: 0.81 to 1.05.** It includes the 20 to 33
    pickups a run. The sim has no pickup time of its own: the overhead between
    kills, fitted without looting, covers it so far.
  - **Loot per kill:**
    - Unicorns: the sim's is fixed at 838 gp (a horn and bones); the server
      got 819 to 957. A run ends after 6 or 7 kills, so one item more or less
      is 13% of its gp/hr.
    - Black Knights: the server's 12 runs fall between the sim's 4th and 96th
      percentiles. The mean gp/hr of 3 runs came out 0.36 to 1.97 of the sim,
      which is noise from rare drops in runs of 6 to 8 kills. What the gate
      should measure here is OQ-20.
  - **Band-1 hobgoblins** (Edgeville dungeon): the server picked up 2 items a
    run against the sim's every drop. The character was under attack almost
    throughout and ran out of food after 1 to 4 kills. The runner loots only
    while nothing attacks it (Claude's rule; a person can click "Take"
    mid-fight), and the sim's loot costs no time. A probe killing 40
    hobgoblins with a strong character found bones on every kill, as the sim's
    table has; its other counts aren't exact (items seen again after walking
    out of view).
  - The sim side's food eaten no longer counts looted food (it went negative
    where the drops include food).

### Decided and built: quests are out, and every quest the server has is complete from the start; the level-3 start stays; the uid fix, OQ-19, OQ-20 and OQ-21 answered
Caleb, 2026-11-06: "I approve the uid fix. OQ-19: Option a is fine. OQ-20.
Option a is fine here, too. After sleeping on it, I have decided that we will
cut out quests to simplify the experiment and we will also spawn the agents
with base 30 stats and 10k gp instead of a starter kit." Then, after Claude's
sanity check of the saving: "Quests should all be flagged as complete so that
they do not block any content. We can keep the level 3 start with the starter
kit." Then: "Move forward with the decisions I made. The calibration should
keep running the server faster than real time - option a on OQ21." And: "For
quests, flags only with no quest rewards, aside from quest points and unlocks.
Drop the 64 quest features from observation." `m002-quests-complete`.
- **Approved: each bridge character's own account uid** (the entry above).
- **OQ-19, answered: measure first.** The question was whether the sim's
  fights should count the aggressive monsters around a combat site.
  - The options: (a) run fights beside aggressive monsters on the server and
    model them only if the rates move beyond ±20% (recommended); (b) model them
    now with the gathering sites' exposure; (c) leave them out and say so.
  - Caleb: (a). Not run yet.
- **OQ-20, answered: gate gp/hr by its parts.** The question was how the gate
  should judge gp/hr where rare drops make up most of the loot.
  - The options: (a) check the drop tables item by item over about 200 kills
    per monster, and gate the looting overhead through kills/hr, XP/hr and the
    time to a full inventory (recommended); (b) keep the mean gp/hr gate and
    run a few hundred kills per case; (c) gate the common drops only.
  - Caleb: (a). Not run yet.
- **OQ-21, raised and answered: calibration keeps the fast tick.** Caleb took
  the fast tick to be for training only. It wasn't put to Caleb before:
  Claude's calibration scripts set 50 ms ticks (12× real time) and the live
  tests 15 ms or 100 ms; training is on the sim, which has no clock.
  - The options: (a) keep 50 ms and add a speed check to the gate, a few
    cases a family rerun at 600 ms (recommended); (b) calibrate at 600 ms, 12×
    slower; (c) keep 50 ms without a check.
  - Caleb: (a). The gate (env contract §7) now has the speed check. Not run
    yet.
  - The case for it: the game counts in ticks. Of the server's wall-clock
    timers, the three in scope already count ticks in the fork; the rest
    (rechecked) are logins, bank PINs, logging, farming, brewing, minigames,
    tormented demons, the Lumbridge tutors' free runes and the silk merchant's
    grudge. One fight at 600 and 50 ms: 13,671 and 13,352 XP/hr.
- **The start state: considered, then kept.** Caleb first proposed a start
  with every skill at 30 and 10,000 gp in place of the starter kit, to cut
  work. Claude's sanity check: cutting quests saves a week or more of the plan
  (21 quest options, each scripted through dialogue on the server for E6), but
  the new start saves little calibration (most of what's left is mechanics,
  not low levels) and costs a day or two (the start state on both backends,
  tests, the scripted guide's early stints). Caleb kept the level-3 start with
  the starter kit.
- **Quests are out, and complete from the start** (env contract v1.12, option
  catalog v1.3). No quest options; sim v1 brings only the four skills.
  - **What the server can complete:** the 68 quests it registers, worth 126
    quest points, of the `Quests` enum's 150 (`gd.implemented_quests`, from its
    source; a live test checks it against the running server). A Soul's Bane
    is marked `@Initializable` but isn't registered; While Guthix Sleeps has
    the annotation commented out.
  - **The other 82 stay incomplete.** Content behind one stays shut where the
    server checks `isQuestComplete`; where it checks
    `ContentAPI.hasRequirement`, it opens once the character meets that
    quest's own requirements (skills, quests, quest points:
    `QuestReq.evaluate`), which the sim doesn't model. So the sim keeps that
    content shut: conservative, and the agent never meets the gap. Examples:
    Watchtower, Trollheim and Ape Atoll teleports; charters to Port Tyras and
    Mos Le'Harmless; Chivalry and Piety (King's Ransom).
  - **Flags only** (Caleb): the bridge's `spawn` sets each quest's stage to
    complete, recomputes the quest points (`syncPoints`) and sets the quest
    tab's varps as login does (`syncronizeTab`), which is where the unlocks
    that read a quest's stage come from. It also sets the four unlocks quest
    endings set themselves (Lost Tribe and Restless Ghost varps; Ernest the
    Chicken's Killerwatt portal; Wolf Whistle's Summoning orb). No quest XP or
    items. Read-only `quests` command: the quest tab's complete quests and
    points.
  - **Not flagged:** the Player Safety test, a miniquest the server keeps
    outside its quest list. The Stronghold of Player Safety stays behind it.
  - **What opens for a new character** (sim and server):
    - 21 of the access table's 55 rules: Morytania and its dungeons, Crandor,
      Melzar's Maze, West Ardougne, the Fremennik Isles and their caves,
      Waterbirth, Trollheim, Keep Le Faye, the Karamja shipyard, the
      Lighthouse dungeon, the Elemental Workshop, the Tourist Trap mine and
      the Phoenix hideout. Shilo Village, Sophanem, Mos Le'Harmless and Ape
      Atoll stay shut: their quests aren't on the server.
    - quest-locked gear of 8 quests the server has (123 items): the rune
      platebody and green d'hide body (Dragon Slayer), the dragon dagger and
      longsword (Lost City), the crystal bow and shield (Roving Elves), the
      Fremennik Trials' gear, and others
    - free passage at the Al Kharid toll gate; the Lumbridge Castle range;
      darts, dart tips and claws
    - quest-locked teleports and charters (Ardougne, Port Phasmatys, the
      Shipyard)
    - Herblore and Runecrafting for sim v1 (Druidic Ritual, Rune Mysteries)
  - **Observation:** the 64 quest features are gone (Caleb): 1,796 features.
    The access part keeps its 55 rules; those decided by quests alone are now
    constant.
  - **Built:** `rlscape.combat.access.start_progress` (a new character's
    quests); `CharacterState` and the ranker's `Character` start from it;
    `rlscape/quests.py` is gone (`scripts/draft_vocabulary.py` keeps the old
    set, which *V* was drafted with). In the fork: `spawn` completes every quest
    (`RLCommands.completeEveryQuest`) and the `quests` command.
  - **Tests:** the lock tests (rune platebody, darts, the toll, the Lumbridge
    range) start their "before" character with no quests. Live
    (`tests/test_quests_live.py`): spawn's complete quests are the sim's 68,
    with all 126 points and no reward XP or items; a rune platebody can be
    worn; Morytania lets the character stay. 309 passed with the server up.
  - **Effects checked:** a level-3 fighter at Lumbridge is now offered
    Morytania's undead cows and chickens (Priest in Peril). None of the 14
    validated travel trips plans a different route. The calibration results
    so far were measured with no quests on both sides, so they stand; new
    cases run with every quest complete on both.
- **New questions:** the Duke's anti-dragon shield (OQ-22) and the items that
  quests now let the agent use (OQ-23).

### Decided and built: the anti-dragon shield on the GE (OQ-22); the vocabulary redrafted with every quest complete (OQ-23); the hazards' scope
Caleb, 2026-11-06: "Allow the anti-dragon shield to be purchased from the ge
now. Rerun both drafts with every quest complete so that we can add the
appropriate items to the vocabulary. Only the eastern pair of black knights
should be treated as hazards, rather than fightable enemies. Continue with
implementation." `m002-shield-and-vocabulary`.
- **OQ-22, answered: the shield is bought on the GE.** The question was how
  the agent gets the anti-dragon shield now that no quest option leads to
  Duke Horacio.
  - The options: (a) an option to ask the Duke (recommended); (b) start with
    it in the bank; (c) leave dragons out.
  - Caleb: none of those; the GE sells it, as in 2009. This reverses the
    2026-10-27 decision that it come only from the Duke.
  - Fork: `rl.conf` blocks nothing on the GE now (`ge_blocked_items = ""`).
  - Prices rebuilt (`scripts/build_price_tables.py`, which reads the block
    list from `rl.conf`): the shield and its note now carry their January
    2009 price, 301 gp, in `prices_v2` (they were valued at 0 while blocked)
    and join the frozen GE's `historical_price_items`, so the frozen seller
    sells it. Nothing else changed.
  - Sim: `buy_ge_1540` (one at a time; masked while one is held). Every bought
    item joins *V*.
- **Built: fights put the shield on against dragonfire.** Fights wear the
  shield with the most defence, so a character with a better kiteshield would
  never have worn it.
  - `wield_best(..., protect)`: against a monster with special damage
    (`special_damage_shields`), a carried protecting shield goes on in place
    of the best by defence. The fight passes it.
  - The ranking rates dragonfire monsters for the character wearing it
    (`dragonfire` fighters in `select_candidates` and the fast ranker, which
    still match). Only dragons: wyverns need Slayer 72, which the sim never
    reaches.
  - Deposits keep a carried anti-dragon shield with the combat kit (not behind
    a two-handed weapon), and `bank_withdraw_gear_<class>` takes one out when
    none is carried.
  - Not modelled: dragonfire's damage through the shield. The server's
    dragons breathe on about one attack in three (`ChromaticDragonNPC`), up to
    52, which the shield cuts by 90% (`calculateDragonfireMaxHit`): up to 5. The
    sim gives each monster one style.
- **OQ-23, answered: the drafts rerun with every quest complete.** The
  question was which items the quests let the agent use join the buy list and
  *V*.
  - The options: (a) rerun both drafts with every quest complete and add what
    the rule proposes (recommended); (b) keep both as they are.
  - Caleb: (a), and add the items.
  - **The buy list** isn't a script's draft but the groups of Caleb's buying
    decisions (option catalog §8). Rerun by hand with every quest complete,
    the groups gain nothing but the shield: their one quest-locked item, the
    rune platebody, was in already. The quest gear that opened is outside
    them: the dragon dagger and longsword are above the rune tier, the
    Fremennik helms aren't full helms, and the crystal bow and shield can't be
    traded. Adding any would be a new buying decision (OQ-24).
  - **The vocabulary draft** (`scripts/draft_vocabulary.py`) now gives every
    band every quest the server has, and its melee and magic fighters an
    anti-dragon shield against dragonfire, so dragons are swept. A stale line
    from before the fishing sites gained exposure no longer ran; fixed.
  - **Result** (`data/vocabulary_draft.csv`): 179 proposed. 16 aren't in *V*,
    and are added (`data/vocabulary.csv`, 192 items):
    - the anti-dragon shield (bought)
    - from dragons: dragon bones, green and blue dragonhide, adamantite ore, a
      rune dagger
    - from Morytania and Port Phasmatys: Blamish ochre and blue shells, thin
      and fat snails, raw chicken, limpwurt and poison ivy seeds, a mithril
      chainbody
    - a vial of water (the Elemental Workshop's water elementals), and a
      mithril 2h sword (a drop in 4 fights and smithed, which the rule passes,
      as for the mithril longsword already in *V*)
  - 13 items in *V* aren't proposed any more, mostly drops whose fights the
    new monsters outrank (cowhide now in 15 fights). They stay: Caleb asked
    to add.
  - Sizes: 134 buys (97 at the GE), 1,191 actions, 1,909 observation features.
- **Hazards, confirmed:** only Taverley dungeon's eastern pair of Black
  Knights; the jail's knights stay targets.
- **Tests:** `tests/test_sim_dragonfire.py` (the shield goes on against
  dragonfire only; a carried shield makes green dragons candidates, rated
  wearing it, the fast ranker matching the reference; a green dragon fight
  wears it; the buy until one is held; the kit and the withdrawal). The live
  GE test now buys the shield at 301 gp. 314 passed with the server up.

### Decided and built: the buy list takes the dragon dagger and longsword and the Fremennik helms (OQ-24)
Caleb, 2026-11-06: "Option b for OQ20", confirmed as OQ-24 (b) when Claude
asked (OQ-20 was answered (a) that morning). `m002-quest-gear-buys`.
- **OQ-24, answered (b).** The question was whether the buy list should take
  any of the gear the quests now let the agent wear.
  - The options: (a) leave the buy list as it is (recommended); (b) add the
    dragon dagger and longsword as a melee tier above rune, and the Fremennik
    helms as helms.
  - Caleb: (b).
- **Built:** six GE buys, one at a time, in groups of their own
  (`DRAGON_WEAPONS`, `FREMENNIK_HELMS` in `rlscape/sim/buying.py`), since the
  scripted guide climbs the scimitar and armour groups by position:
  - the dragon dagger (1215) and longsword (1305): Attack 60, Lost City;
    January 2009 prices 29,700 and 98,200 gp
  - the berserker (3751), archer (3749), farseer (3755) and warrior (3753)
    helms: Defence 45, the Fremennik Trials; 53,600 to 77,800 gp
  - They join *V* as bought items (198), and the vocabulary draft, rerun,
    proposes exactly them besides the 192. Sizes: 140 buys (103 at the GE),
    1,227 actions, 1,957 observation features.
- **How they rank, as the mask's upgrade check scores them:**
  - the dragon longsword beats the rune scimitar; the dragon dagger doesn't
    (2,704 against 2,943), so it's bought only by a character without a
    better weapon
  - the berserker and warrior helms beat the rune full helm on defence (123
    against 118). The archer and farseer helms score 36: fights choose armour
    by defence, so their ranged and magic bonuses count for nothing until
    armour is chosen per combat class, the limitation that keeps leather and
    robes off the list (option catalog §8).
- **Found:** the server locks the farseer helm behind no quest
  (`ItemQuestRequirementListener` lists the other three). In 2009 it needed
  the Fremennik Trials. With every quest complete it makes no difference.
- **Tests:** the dragon longsword's buy opens at Attack 60, the berserker
  helm's at Defence 45, and neither without the quests; sizes. The non-live
  suite: 266 passed (the server was running the speed check).

### Measured: the gate's speed check passes (OQ-21)
`m002-shield-and-vocabulary` (continuing Caleb's "Continue with
implementation").
- **What ran** (`scripts/speed_check.py`; `results/calibration/
  speed-check-20261106-1959.json`): the same cases on the server at 50 ms
  (12× real time) and at 600 ms, 3 runs a case of at most 1,000 ticks:
  - gathering at band 31: willows, iron, fly fishing (`scripts/calibrate.py`)
  - combat at band 31: the ranker's top melee and ranged picks, both
    scorpions by Al Kharid (`scripts/calibrate_combat.py`)
  - travel: the 13 check trips, once each (`scripts/validate_travel.py`)
- **The rule** (Claude's, reversible): XP/hr means within two standard errors
  of their difference; travel, run once a speed, within 5%.
- **Result: 18 of 18 agree.**
  - Travel: every trip the same to the tick, but the charter (1.03).
  - Gathering and combat, 600 ms over 50 ms: willows 1.08, iron 1.03, fly
    fishing 0.99, melee 1.05, ranged 1.03; at most 1.7 standard errors.
  - Four of the five lean the same way. Within the noise of 3 runs, but it
    could be the calibration script reading the state over the bridge each
    tick and clicking a tick late at 50 ms, which would put a tick or so into
    the measured overhead between kills. More runs would tell; it's far
    inside the gate's ±20%.
- Results files now name their tick when it isn't 50 ms (`-600ms`;
  `rlscape.bridge.client.speed_suffix`).

### Built: the drop tables' shared sub-tables; a drop probe (OQ-20); five more items in *V*
Continuing Caleb's "Continue with implementation", then Caleb, 2026-11-06:
"Add the five items to the vocabulary." `m002-shield-and-vocabulary`,
`m002-subtable-items`.
- **Found: the sim's drops left out the server's sub-tables.** A drop
  table's slot can stand for a shared table: the rare drop table, gems,
  herbs, uncommon, rare and allotment seeds, and CELEDT
  (`WeightBasedTable.convertWeightedItems`). The sim gave nothing for them.
- **Ported** (`gd.sub_tables`, from `data/configs/shared_tables/*.xml`;
  `rlscape.sim.combat.roll_drops`; `DropTable.expected_items`): a slot rolls
  its table once, and the herb and uncommon seed slots as many times as
  their amount (`isSpecialSlot`). The rare drop table keeps its "nothing"
  weight, which only a ring of wealth removes (not in the sim). Clue
  scrolls still give nothing.
  - Expected loot a kill: Black Knights 1,219 to 1,255 gp, hobgoblins 857 to
    888, green dragons 4,009 to 4,185 (3 to 4%); unicorns have no such slot.
  - Men and women now outrank cows for gp at Lumbridge (their herb and seed
    slots). Test: the gem table's slot gives its items at its rate; the
    herb slot rolls its amount's worth of times.
- **The vocabulary rule, rerun with them, proposes 5 more:** rune arrows, the
  tooth half of a key and a rune 2h sword (the rare drop table), an earth
  talisman and mithril bolts (fights the new values rank higher). Caleb
  added them: *V* 203, 1,252 actions, 1,992 observation features.
- **The drop probe** (`scripts/probe_drops.py`, OQ-20 (a)): a level-99 melee
  character kills about 200 of a monster, without retaliating, and every
  drop of its own is counted once by its key; the sim rolls the same kills
  2,000 times, and an item fits inside the sim's central 99%. `--rejudge`
  judges saved server counts by the sim as it is now.
  - Fork (an addition to the pickup command, uncommitted): `ground_items`
    gives each item a key, the same while it lies there
    (`System.identityHashCode`), so an item out of view and back counts once.
    Live-tested.
  - A 20-kill trial at the jail's Black Knights: 65 of 66 items fit, judged
    with the sub-tables. The miss was bones, 19 for 20 kills: the kill count
    took a knight still fighting as killed. Fixed (completed kills only, and
    12 ticks for the last drop).

### Built: poison; the calibration runners counted eat clicks, not food
Continuing Caleb's "Continue with implementation". `m002-poison`.
- **The server's rule** (`core.game.system.timer.impl.Poison`;
  `MeleeSwingHandler` and `RangeSwingHandler.adjustBattleState`;
  `ContentAPI.applyPoison`):
  - A poisonous monster's every swing, hit or miss, poisons 4 times in 10 at
    its `poison_amount` severity (27 monsters; poison spiders 30). A
    protection prayer stops the swing's damage, not its poison.
  - Poison hits every 30 ticks for floor((severity + 4) / 5), the severity
    falling by 1 a hit (severity 30: 6 five times, then 5 five times, ...;
    105 in all). A stronger poison raises a running one's severity; death
    clears it.
- **In the sim:**
  - Fights roll poison at each monster swing and land its hits between the
    swings, so eating and death see them (`rlscape.sim.combat.fight`).
  - It runs on after the fight wherever time passes (`regenerate` advances
    it, `rlscape.sim.health`). Claude's rule (reversible): a poison hit that
    leaves HP at or below the retreat point is eaten through while food
    lasts, as fights eat. It can kill: the engine handles a death outside a
    fight.
  - The rate model adds it to the damage taken per kill and per hour: while
    a poisonous monster fights the character, its swings come several times
    in each 30 ticks, so the severity stays at the monster's
    (`rlscape.combat.rates.poison_per_tick`). The danger filter and the
    candidates' damage feature see it.
- **The poison spider cases resimulated** (`results/calibration/
  combat-20261105-2007-resim.json`): the sim now runs out of food as the
  server did, at 963 ticks (melee) and 726 (ranged) against the server's 891
  to 1,049 and 697 to 735. It ran out in none of these runs before.
- **Found: the runners counted eat clicks as food eaten.** A bite lands a
  tick after its click, so a runner reading HP still low clicked again:
  every poison spider run counted 30 for its 15 lobsters. The server's
  food/hr was overstated, up to twice:
  - The poison spider runs ate 15 lobsters each: about 95 an hour, against
    the sim's 93 (melee) and 124 (ranged) now.
  - "Ranged fighters take more damage on the server" (food 1.4 to 1.8 times
    the sim's, 2026-11-05) may be this as well. To rerun.
  - Fixed in `scripts/calibrate_combat.py` and `scripts/calibrate.py`: food
    eaten is what the inventory loses between readings; clicks are counted
    apart (`eat_clicks`).
- **Tests** (`tests/test_sim_poison.py`): the timer's hits and severity; a
  weaker poison changes nothing; regeneration carries it, death clears it;
  a prayed-against poison spider fight runs out of food; the rate model's
  damage per kill is the poison's.

### Built: antipoison; tests and servers in parallel; the probe's dragon death, and flicking on the server
Caleb, 2026-11-06: "Add in anti-poison and super anti-poison potions to
counteract poisonous effects. I don't recall if I greenlit it before, but in
the interest of saving time, we can absolutely increase the number of
concurrent agents training and/or run multiple tests at once, where
possible." Then: "Why did the probe character die?" and "Make sure the dragon
fighters have protection from dragon fire and are flicking their prayers."
`m002-antipoison-and-parallel`.
- **Antipoison, from the server** (`Consumables` ANTIPOISON and SUPER_ANTIP;
  `AddTimerEffect`, `PoisonImmunity`, `Potion.consume`):
  - A dose cures the poison and makes the character immune for 150 ticks (90
    s), or 600 for the super antipoison; another dose restarts the immunity,
    not adds to it. A dose leaves the next in its slot; the last, an empty
    vial.
  - Claude's rule (reversible): options drink when a poison takes hold, or
    one carries on from before, while a dose is carried; the super first
    (cheaper a tick of immunity: 253 gp a dose for 600 ticks, against 96 for
    150), the emptiest potion first. Drinking takes 2 ticks, as a bite.
  - The ranking takes off the share of the poison the carried doses cover
    over the option (`poison_cover`), in the danger filter and the
    candidates' damage feature.
  - Deposits keep the doses with the fighting kit. The GE sells both
    four-dose potions, one a buy, so each comes as a potion, not a banknote.
  - *V* by its rule, which now counts what drinking leaves: the two bought
    potions, their six lower doses and the vial (212 items; 142 buys, 1,299
    actions, 2,057 observation features).
  - Tests: the cure and the immunity, the order, the vial; a poison spider
    fight with 3 super antipoisons eats under a third of the food; the cover.
- **In parallel:**
  - **Tests:** pytest-xdist (a dev dependency). `uv run pytest -n 8 --dist
    loadgroup` keeps every live test on one worker (`tests/conftest.py`):
    they share one server, one bridge connection and one tick speed. The rest
    ran in 68 s against 134.
  - **Servers:** `scripts/server_instances.py n ...` writes extra instances'
    configs (`results/servers/rl-<n>.conf`: world n, bridge port 43610 + n -
    1, its own GE database and server store under the fork's ignored
    `data/eco/instance-<n>`) and installs the frozen GE in each. Each world
    ticks on its own. `RL_BRIDGE_PORT` points any script or the live tests at
    one; results files name their instance (`-i2`; `run_suffix`, which was
    `speed_suffix`).
  - Training (week 3) is to run its environments in parallel too
    (`SubprocVecEnv`), as planned.
- **Why the probe's character died** (traced on instance 3): the green
  dragons' busiest site is in the Wilderness (3340, 3678). With
  auto-retaliate off, the probe clicked the nearest dragon, but another was
  attacking it, and this single-combat area refused every click ("You're
  already under attack!"). It stood unprayed while that dragon hit it, ate
  its 15 sharks and died after 2 kills (no gravestone in the Wilderness).
  The anti-dragon shield worked ("Your shield absorbs most of the fiery
  breath"). The first probe run's character went the same way and then
  clicked from Lumbridge until its cap, about 2 hours.
- **Fixed** (Caleb: dragon fighters wear dragonfire protection and flick):
  - Fork: `flick {uid, on}`, the bridge flicking a character's protection
    prayers itself. Each tick, after the pulses, it clicks on the protection
    against an attacker due to swing next tick, and off one nothing swings
    with then, as prayer-tab packets the next tick's packet phase handles
    before its pulses: on in exactly the swing ticks, so it never drains.
    The style is the monster's own config, so a dragon's breath (the shield's)
    doesn't change it. Scripted on the server because a client a tick late
    misses the swing. `state`'s attackers give their next swing's tick.
  - The probe flicks, wears the anti-dragon shield against dragons, attacks
    the probed monster attacking it before any other, and stops if it dies
    or kills nothing in 2,000 ticks; it prints its progress and saves after
    each monster.
  - In the sim, dragon fights already flick when the Prayer level allows
    (`rlscape.combat.prayers`) and wear a carried anti-dragon shield.
  - Calibration still leaves Prayer at 1 on both sides by design (the fights'
    own rates); a case can now flick on the server if it sets Prayer.
- **The probe's results so far** (instance 2, with the sub-tables): Black
  Knights, 200 kills, 67 of 68 items within the sim's 99%, nothing the sim
  never drops.
- **Several agents on one server, not one each** (Caleb: "Can we run
  multiple agents per server, rather than single thread agents on multiple
  servers?"). The bridge already controls any number of characters; what
  limited it was serving one connection at a time, so a second script waited
  for the first to disconnect.
  - Fork: `RLBridge` serves each connection on its own thread (backlog 16).
    Their requests share the game thread's queue in arrival order, so
    several scripts, each with its own characters, run against one world.
  - What still needs separate worlds: a different tick speed (the speed
    check's 600 ms runs), and the live tests, which set the tick themselves.
  - The rules for sharing one: set the world's tick first (each script puts
    back the tick it found), and keep each script's characters at their own
    site, as calibration already requires (env contract §7). E6 keeps one RL
    character per world (§7).
  - The extra instances stay for those cases; a shared server needs one JVM
    (about 3.5 GB) instead of one per script.

### Built: combat inventories in calibration; combat potions; antifire and a dragon's breath; thieving calibrated; probe results
Caleb, 2026-11-06: "Continue with implementation while these calibration
tests run." Then: "Why do these runs still not bank items that are not
relevant to the task at hand? The starter kit should not be carried when
trying to fight monsters. A good inventory for combat should be food and
potions, with empty slots for drops if the expected damage taken is low.
Since we are prayer flicking in all combat situations, any monster with a
single combat style should never damage the agent, meaning that combat
inventories should hold as many potions as it takes to boost stats while
training, if the agent opts to use potions, and open slots for loot." And:
"The only way to take no damage from green dragons is to use anti-dragonfire
potions and have an anti-dragon shield, while flicking melee overheads.
Although, I'm not sure if 100% protection was available in 2009, so check
that against the archive. It may be that super anti-dragonfire potions are
needed." `m002-combat-inventories-and-potions`.
- **Why the runs carried the kit:** the combat runner kept the starter kit at
  band 1 on purpose, as a fresh character's first fight, and left Prayer at 1
  on both sides so the fights' own rates were compared. So band-1 runs filled
  up after a few kills (the women's runs lasted 74 to 326 ticks).
- **Now, a combat inventory at every band** (`scripts/calibrate_combat.py`):
  - no starter kit; the band's gear (at band 1 the kit's own sword and shield,
    or bow and arrows); Prayer at the band's level, as env contract §7 has it
    for every trainable skill
  - both sides flick: the sim's fights flick whatever the Prayer level allows,
    and the server's bridge now does too (`flick`)
  - food only for the expected damage over the run (`food_for`: the sim's
    damage with prayers flicked, less the hitpoints above the retreat point,
    plus 2, at most 15): 2 at bands 61 and 91, where flicking leaves a
    single-style monster nothing; more at band 1 (women, chickens: 10 to 13)
  - the rest empty, for loot
- **Flicking, and when damage is still taken:** a monster of one style the
  Prayer level covers deals nothing (Protect from Melee at 43, Missiles 40,
  Magic 37). Below those, a character takes its hits; a fresh one has none.
  Poison still lands (antipoison), and a dragon's breath (antifire).
- **The agent's own banking** stays its choice (env contract §9, decision 1):
  `bank_deposit` keeps the task's kit, so the starter kit goes at the first
  deposit after a fight. Not changed.
- **Combat potions** (`rlscape/sim/potions.py`; Caleb: potions if the agent
  opts to use them), from the server's `Consumables` and `SkillEffect`:
  - attack, strength and defence (+3 and 10% of the level), their supers (+5
    and 15%), ranging (+4 and 10%), magic (+4)
  - a dose while boosted tops up to a dose's boost, no higher; the boost falls
    a level every 101 ticks (`SkillRestore`, the hitpoint regeneration cycle);
    death clears it
  - Claude's rule (reversible): before each kill, drink for each skill the
    class uses (and defence) once its boost is half gone, the super first, the
    emptiest potion first. Fights and the ranking use the boosted levels (the
    ranking, the fighter as it starts the fight, after drinking).
  - The GE sells the eight four-dose potions, one a buy; the deposit keeps the
    class's potions with the fighting kit.
- **Antifire and a dragon's breath** (`rlscape.combat.rates`; the archive:
  the RuneScape Wiki's Antifire potion page of 28 February 2009, via the
  Wayback Machine):
  - 2009: the potion alone gives "slight immunity"; with an anti-dragon shield,
    "complete immunity against dragon fire for exactly 6 minutes". The 2009
    potion list has no super antifire (Old School added one in 2018). The
    server matches: the shield takes 90% of the breath's 52, the potion 10%
    more (`calculateDragonfireMaxHit`), and a dose lasts 600 ticks, restarted
    by the next.
  - The breath is modelled now: a dragon picks each swing at random from two
    melee attacks and its breath (`MultiSwingHandler`), so one in three is
    breath; it always lands, uniform from 0 to 5 behind the shield. With the
    melee flicked, a green dragon still deals that, about 1,250 hitpoints an
    hour; with antifire, nothing.
  - Fights drink an antifire dose before a dragon kill when the last has run
    out (Claude's rule); the ranking and the damage feature take off the share
    the carried doses cover, as for antipoison. The GE sells it, one a buy.
- **Sizes:** *V* 248 (the nine potions' 36 doses by the rule that took
  antipoison's: what drinking leaves joins *V*), 151 buys, 1,488 actions,
  2,318 observation features. Whether lower doses should be in *V* at all is
  OQ-25.
- **Thieving calibrated** (`scripts/calibrate_thieving.py`, new): a server run
  pickpockets as a person does (click when idle, eat at the sim's point, the
  starter kit banked first). At Lumbridge's men the sim ran 18 to 19% fast at
  bands 1 and 31; the server's runs showed 0.41 to 0.46 ticks an attempt
  beyond the lock or stun (the click and the walk to a moving target). Fitted
  as `ATTEMPT_OVERHEAD_TICKS = 0.44` (the fight and the slots' rates): then
  0.98 and 1.00, gp/hr and food/hr alike.
- **The drop probe** (`results/calibration/drops-*.json`), with the
  sub-tables:
  - Black Knights 67 of 68 items within the sim's 99% (the miss: bones 199 for
    200 kills, the probe missing one); unicorns 2 of 2; hobgoblins 88 of 88;
    women 25 of 25.
  - Women's gp/hr in the calibration (sim 21,329 against the server's 3,664)
    was noise: band-1 runs of a few kills, herbs worth hundreds each but 0.15 a
    kill. The table is right.
  - Green dragons: 41 of 41 items in 28 kills before the character died (no
    antifire then). Rerunning with antifire and food topped up.
  - Chaos druids: the probe's tie-break picked Yanille's dungeon, where it got
    no kill in 2,000 ticks (an Agility obstacle, it seems), which the access
    table doesn't lock: to check (OQ-16). It now takes the nearer site.
- **Top-gp fights recalibrated** with the new sim (`combat-20261106-2252-
  slot3-valuable.json`; before the combat inventory): XP/hr 0.78 to 1.33,
  unicorns, Black Knights and moss giants within ±20%; the band-1 women's
  1.33 and the chaos druids' 0.78 outside. To rerun with the combat
  inventory and flicking.

### Decided and built: only four-dose potions in *V* (OQ-25); the moss giants west of the Fishing Guild are hazards
Caleb, 2026-11-06: "OQ25 - proceed with option a, so long as the lower dose
potions remain consumable." Then: "Treat those un-fightable moss giants West
of the fishing guild as hazards." `m002-potion-doses-and-moss-giants`.
- **OQ-25, answered (a).** The question was whether every dose of a potion
  should be its own item in *V*. By *V*'s rule, what drinking leaves had
  joined it: the 11 potions were 44 of *V*'s 248 items, each with five
  actions and seven features, most of which only told the policy how many
  doses it carried.
  - The options: (a) keep only the four-dose potions (bought) in *V*; the
    lower doses are misc, and the observation gets each potion's doses
    carried, inventory and bank (recommended); (b) keep every dose in *V*.
  - Caleb: (a), so long as the lower doses stay consumable.
- **Built:**
  - *V* loses the 33 lower doses and the vial: 214. The vocabulary draft no
    longer proposes what drinking leaves.
  - The lower doses stay consumable. Fights drink any dose, the emptiest
    first (`rlscape.sim.potions.DOSES`). Deposits keep every dose
    (`economy.kept_on_deposit`), so the misc actions (drop, alchemy, sale)
    never touch them. Net worth counts them at their prices, as before.
  - The observation's potions part (env contract §3): 11 potions × 2
    features, the doses in the inventory and the bank, noted doses
    included, log1p-scaled.
  - Sizes: *V* 214, 151 buys, 1,318 actions, 2,102 observation features.
- **Hazards: the moss giants west of the Fishing Guild** (id 112; spawns
  2551, 3401; 2554, 3400; 2554, 3411; 2560, 3406).
  - Found by the drop probe: no kill in 2,000 ticks, the attack click doing
    nothing, as with Taverley's eastern Black Knights. The probe then fell
    back to the next site and killed as usual.
  - `HAZARDS` takes their spawns out of the enemy pool. They stay in the
    world for the aggression model. The goblins beside them aren't in it,
    and the other moss giants (Edgeville dungeon's, which the top-gp
    calibration fought, among them) stay targets.
- **The drop probe, green dragons** (with antifire and food topped up): 200
  kills in 11,739 ticks, alive; 39 of 41 items within the sim's 99%. The two
  misses are the always-drops, bones and hide at 199 of 200: the probe missed
  a pile, as with the Black Knights' bones. Clue scrolls (4) aren't modelled
  (the sim's clue slots give nothing) and aren't counted.
- **The drop probe, moss giants** (the next site after the hazard's): 200
  kills in 8,812 ticks; 70 of 71 items fit, the miss again the always-drop
  (big bones, 199 of 200). Four monsters now with the same one-pile miss:
  the probe's accounting, to look into; no verdict hangs on it.
- **Found: the server runs in dev mode** (`dev = true`, from `default.conf`).
  The moss giants dropped 41 champion scrolls in 200 kills: dev mode makes
  them 1 in 5, not 1 in 5,000, and big fish 1 in 10. Nothing calibrated so
  far is touched. OQ-26 asks whether to turn it off.
- **The Yanille dungeon's chaos druids, looked into** (Caleb asked whether
  the Agility obstacles kept the character out):
  - The probe never walked there: it teleports onto a site. What stopped it
    was Salarin the Twisted (id 205, 70 hitpoints, aggressive), in the same
    room. Only the four strike spells hurt it (`SalarinTwistedNPC.
    checkImpact`), and in single combat, while it attacks, a click on a druid
    gets "You're already under attack!".
  - A walking character couldn't have got in either. The server's pathfinder
    reaches that room only from the far side of a pile of rubble, which takes
    Agility 67 (`YanilleAgilityDungeon.kt`). The access table's rule named
    only Salarin, and the travel model, which doesn't map dungeons, put the
    site 12 ticks under the surface tile above it.
  - The dungeon's other druids (id 7105, by the entrance) need no Agility and
    fight as usual: 30 kills, 35 of 36 items fit.
- **Decided (Caleb): the Yanille Agility Dungeon is out of the project.**
  "Ignore the yanille dungeon for this project." `IGNORED_AREAS` in
  `rlscape/combat/candidates.py` takes every spawn inside the server's zone
  for it (2544 to 2631, 9481 to 9587) out of the enemy pool: zombies, a
  giant bat, two skeletons, poison spiders, both chaos druids and Salarin.
  The same monsters elsewhere stay targets. No gathering, thieving or bank
  site is there, and no calibration case was. The access table's rule for
  Salarin stays, though nothing reads it now.
- **The chaos druid rerun** (Edgeville dungeon): 36 of 36 items. The earth
  runes' miss before was chance.
- **Tests:** the moss giants' hazard (no site there; the others stay); the
  Yanille dungeon (no site in it; the Edgeville druids stay); the lower doses
  not in *V* but drunk, kept and counted. The non-live suite: 279 passed.

### Decided and built: dev mode off (OQ-26); the overhead between kills refitted, and a pickup time a drop
Caleb, 2026-11-07: "Turn the server's dev mode off." `m002-dev-mode-and-pickups`.
- **OQ-26, answered (a).** The question was whether the experiment server
  should run with dev mode off.
  - The options: (a) `dev = false` in `rl.conf` and the instance configs,
    with the live suite rerun (recommended); (b) leave it on and note the
    two rates as a known gap; (c) leave it on and model the scrolls and big
    fish in the sim at dev mode's rates.
  - Caleb: (a).
- **Built:** `dev = false` in the fork's `worldprops/rl.conf` (uncommitted
  there); `scripts/server_instances.py` regenerated instances 2 and 3 from
  it (their GE databases reinstalled), and instance 1's GE database was
  reinstalled while it was down. Both servers restarted; each logs
  `devMode=false`. `debug = true` stays: it only lets players use the admin
  commands (and a Construction guide book), no game rule.
- **The live tests with dev mode off:** 49 passed (instance 2). Nothing in
  the bridge relied on it.
- **The bank test, fixed** (`tests/test_bridge_inputs_live.py`): it
  expected the booth to open the bank by a fixed tick. Under the full suite
  in parallel the bank opened a tick later (`[None, 762]`), twice (the
  second time with the full log). It now waits up to 6 ticks for the bank,
  then checks it stays open. The flick test's one failure in the first full
  run didn't come back (8 runs alone, the file in order, a 600-tick trace
  with no drain, and the second full run).
- **The overhead between kills, refitted** with the combat inventory and
  flicking (`combat-20261107-0001.json`, the fit set, and `-0049.json`, the
  top XP picks: 16 cases, no looting). At 10 and 8 ticks the sim ran slow at
  rats (0.68 to 0.70) and scorpions (0.82 to 0.92): a bridge character's
  kill took about three clicks on 2026-11-05 (every character had account
  uid 0) and about one now. Fitted jointly: 3 ticks for both classes (rats
  want 1, the experiments' cave about 7). Magic is taken as ranged.
- **A pickup time a drop** (new; `PICKUP_TICKS`, `with_pickups` in
  `rlscape/combat/rates.py`). The loot runs
  (`combat-20261107-0035-valuable.json`, the ranker's top gp picks) went the
  other way at the old overhead: ranged unicorns and moss giants 1.34 and
  1.35. With the overhead at 3, the server's time a kill beyond the sim's
  grew with its pickups, so the overhead can't serve both.
  - Each drop the loot mode keeps adds a pickup, after the kill: 3 ticks
    for melee, 10 for ranged (fitted; ranged's also covers walking to its
    arrows, 4 to 6 pickups a kill on the server against melee's 1.4 to 2.9,
    which the sim recovers with the kill). Magic is taken as melee.
  - The sim's fights charge it for each drop picked up. The rates take the
    expected drops kept a kill (`DropTable.expected_items(stacks=True)`,
    `candidates.pickups_per_kill`): the hourly rates fall in proportion,
    the per-kill damage the danger filter reads stays the fight's (a
    pickup's poison is a few hundredths of a hitpoint). The fast ranker does
    the same on its arrays, and still equals the reference.
- **Results, sim over server** (resimulated, the `-resim.json` files):
  - XP/hr and kills/hr, all 24 cases within ±20%: no looting 0.91 to 1.19
    (melee band-91 experiments the highest), looting 0.90 to 1.13.
  - The time to a full inventory (gated for looting, env contract §7):
    0.85 to 1.14, but Edgeville's chaos druids at 0.72. The server's runner
    picked up 1.43 drops a kill there against the sim's 1.82: it loots only
    while nothing attacks it (Claude's rule, 2026-11-05), and the druids are
    aggressive. Raised for Caleb.
- **A test changed:** the site-capacity test compares the sim with
  `site_slowdown` at the sim's own time a kill. The rate model's time to
  kill (HP over damage a tick) leaves out the last hit's overkill, a few
  ticks at a two-swing cow, which the 10-tick overhead had hidden.
- **Tests:** a pickup each drop, in the sim and the rates
  (`tests/test_sim_combat.py`); `pickups_per_kill` (`tests/test_candidates.py`).
  The non-live suite: 280 passed.

### Decided and built: the rate model's time to kill counts the last hit's overkill
Caleb, 2026-11-07: "Fix the overkill in the rate model's kill time too."
`m002-looting-and-scenery`.
- **Before:** the rate model (env contract §8; the candidate ranking and the
  danger filter) took a kill to last HP over the damage a tick. That leaves
  out the last hit's overkill: a cow killed in two swings took about 8
  ticks in the sim's fights and 4.8 in the model. The 10-tick overhead had
  hidden it; at 3 it showed (the site-capacity test).
- **Now** (`swings_to_kill`, `landed_hits_to_kill` in
  `rlscape/combat/rates.py`): the expected swings until their damage
  reaches the monster's HP, as the sim's `kill_sequence` deals it (a swing
  hits with its chance for uniform 0 to its max hit).
  - Only damaging hits count, so it's the damaging hits a kill takes over
    the chance a swing deals damage. For hits uniform from 1 to m, the
    expected number to reach h is the hit's renewal function: (1 + 1/m) **
    (h - 1) up to m + 1, then g(h) = 1 + (g(h - 1) + ... + g(h - m)) / m.
    Exact, cached per max hit.
  - Flicked and plain swings (two hit chances and max hits) are weighted by
    their shares of the damaging hits, as if mixed at random; the sim keeps
    them in their pattern.
  - The renewal approximation (H / mean plus a constant) was 32% short at
    one-hit kills, so it's computed exactly.
- **Checked** against the sim's kill sequences, 20,000 a case: 0.998 to
  1.003 plain, 1.005 to 1.008 flicked. The old formula: 0.23 (a 2-HP
  monster, max hit 15) to 0.95 (250 HP). A plan's rates for the 1,056
  monsters take 14.4 ms, from 12.4.
- **Unchanged:** the sim's fights (they always rolled whole swings), so the
  overhead and pickup fits stand. The ranking, the danger filter's damage
  per kill and the ammunition a kill costs now follow the longer kills.
- **Tests:** the kill time against the sim's kill sequences
  (`tests/test_combat_formulas.py`); the site-capacity test compares the
  sim with the model's own kill time again. The non-live suite: 286 passed.

### Fixed: the drop probe's one-pile miss
Found 2026-11-06 (the always-drops at 199 of 200 for Black Knights, green
dragons and moss giants); fixed 2026-11-07, `m002-looting-and-scenery`.
- **Two causes, opposite ways** (`scripts/probe_drops.py`):
  - The last kill's drop came after the probe stopped looking. The server
    drops a monster's loot once its death animation ends (`DeathTask`: the
    animation's length, 30 ticks at most, 6 if it has none); the probe
    waited 12. Big monsters missed a pile. It waits 31 now.
  - It clicked one more attack on the tick it reached its count, and a
    quick kill landed in the wait: 51 always-drops for 50 cows. No attack
    after the count now.
- **Checked:** 50 cows, 50 of each always-drop (7 of 7 items fit); 25 green
  dragons, 25 bones and hides (41 of 41).
- The earlier verdicts stand: their one miss each was this pile.

### Decided and built: the calibration runner loots between kills, attacked or not; the pickup time refitted
Caleb, 2026-11-07: "Go with option a for the looting rule."
`m002-looting-and-scenery`.
- **The question** (raised in `m002-dev-mode-and-pickups`): the runner
  looted only while nothing attacked it, so at aggressive monsters it left
  drops the sim picks up (Edgeville's chaos druids: the time to a full
  inventory 0.72).
  - The options: (a) loot between kills while attacked too, as the sim
    does, and rerun the loot set (recommended); (b) keep the rule and note
    the druids' 0.72 as the runner's; (c) make the sim skip loot while
    attacked.
  - Caleb: (a).
- **Built** (`scripts/calibrate_combat.py`): with its own drops on the
  ground, and standing still for 2 ticks, the runner takes the nearest
  first, attacked or not. It starts no fight with its loot on the ground,
  so a target then is one it retaliated on.
- **Rerun** (`combat-20261107-0357-valuable.json`): the server's looting
  runs got slower, ranged most (it now takes each arrow pile as it lands).
  The pickup time refitted on them: 5 ticks a drop for melee (from 3), 18
  for ranged (from 10); magic as melee.
- **Results, sim over server** (`-0357-valuable-resim.json`):
  - The time to a full inventory: 0.85 to 1.18, every case within ±20%;
    the chaos druids 0.98 (from 0.72).
  - XP/hr and kills/hr: melee 0.97 to 1.13; ranged unicorns 0.96 and moss
    giants 0.90, but Black Knights 1.21 and band-1 women 1.27. A cost a
    drop can't follow ranged's arrow piles, a few a kill: OQ-27.
  - The no-loot sets are unchanged (no pickups).

### Built: using inventory items on scenery (the bridge's `use_item_on`)
Caleb, 2026-11-07: "Make the changes required for using inventory items on
scenery." `m002-looting-and-scenery`.
- **The command** (fork, `RLCommands.kt`; `BridgeClient.use_item_on`):
  `use_item_on {uid, item, name, ids?, radius?}` sends a client's
  UseWithScenery packet with the item's inventory slot, for the scenery of
  that name the character can walk to soonest, as `interact` picks it;
  `PacketProcessor.processUseWith` does the walk and the use. A path onto
  the object's approach comes first; only without one, a "move near" path
  that ends beside one of its edges (the Edgeville furnace's kind). Packet
  only: the client's way.
- **What it needed besides** (the bridge's dialogue dismissal,
  `dismissDialogues`, which closed them before a click could land): it now
  leaves open the furnace's bars (chatbox 311), cooking's how-many
  (CookingDialogue's chatbox 307, a dialogue file, not a skill dialogue)
  and the anvil's smithing interface (300).
- **Live tests** (`tests/test_bridge_inputs_live.py`): raw shrimps on
  Lumbridge Castle's range cook; a bar on the anvil opens the smithing
  interface and two shrimps the how-many, both left open. Passed.
- **Found: the Edgeville furnace needs the Varrock Diary.**
  `FurnaceOptionPlugin` refuses object 26814, its Smelt option and ore used
  on it, until the diary's easy tasks are done, which no character does.
  The sim had it for everyone. `data/stations.csv` now marks it `never`;
  the next furnace is Lumbridge's.

### Built: the processing calibration; four fixes it found
2026-11-07, `m002-looting-and-scenery`. A new runner,
`scripts/calibrate_processing.py`: the activity alone, from the same start
on both sides, as a person does it (a click when idle, an interface's
button as soon as it's open), ending at the last XP gain once the inputs
are gone. The character per env contract §7, with a full inventory of the
option's inputs (setup only). 34 cases, 3 runs each, bands 1 to 91.
- **Results, XP/hr sim over server** (`processing-20261107-0522.json`;
  firemaking `-0525-burn_logs-b1+31+61+91.json`, resimulated with the
  step-offs; iron also `-0440-smelt_iron-b31+61+91-i3.json`, 8 runs):
  - smelting 0.95 to 1.05 (bronze, iron, steel, at the Lumbridge furnace)
  - smithing 1.00 to 1.02 (bronze to mithril, Varrock's south-east anvil)
  - cooking 0.95 to 1.00 (Lumbridge Castle's range)
  - firemaking 0.91 to 1.15; burying 1.01
  - Every case within ±20%, and the durations too (0.91 to 1.14).
- **Fixed in the sim, measured on the server:**
  - Burying: a bone every 3 ticks, not 2 (BoneBuryListener's clock is 2;
    clicked every tick, the server took 60 ticks for 20 bones, at 100 and
    600 ms). The scripted guide's Prayer, time-boxed, ends at 3 now, not 4
    (`tests/test_guide.py`'s expectation changed with the reason).
  - Smithing: "Make All" holds its item until the bars run short; the sim
    switched to a better item on a level-up partway (14 axes, then bolts).
    Starting the next item when the bars run short costs 9 ticks
    (`SMITH_NEXT_ITEM_TICKS`: the pulse runs on until it finds too few
    bars, then the anvil is opened again).
  - Firemaking: the chain was right (55 ticks for 27 logs, as the sim), but
    now and then the step aside after a fire is blocked and the character
    is left on its fire, where nothing lights. Measured: 13 times in 312
    chained logs, about 4.6 ticks each (`FIRE_BLOCKED_CHANCE`,
    `FIRE_STEP_OFF_TICKS`). The runner steps off as a person would.
  - Iron's success stays the server's coin flip (`nextBool`): a 65% at band
    91 in 3 runs came back to 0.97 to 1.11 in 8.
- **Found:** the Edgeville furnace needs the Varrock Diary (the entry
  above); rows by Falador's walls take no fire (the runner's rows are in
  the fields).
- **The speed check:** burying at 600 ms took the same 85 ticks as at 50
  ms.
- Magic, the GE and shops, and Fletching's own paths are still to
  calibrate.

### Measured: the thieving check set
2026-11-07, `m002-looting-and-scenery` (`scripts/calibrate_thieving.py`; the
fitted 0.44-tick overhead an attempt, from Lumbridge's men; 3 runs a case,
one target a band, at the first band its level allows).
- **XP/hr, sim over server:** farmers (band 11) 1.14, warriors (31) 0.98,
  guards (41) 1.05, knights of Ardougne (61) 1.05, paladins (71) 1.14,
  heroes (81) 0.91. All six within ±20%.
- **gp/hr:** 0.98 to 1.14, but heroes 0.75: their table pays mostly in rare
  items (gems, gold ore, death runes), which 3 runs can't settle, as with
  the drop tables (OQ-20). An item-by-item check of a pickpocket table,
  as the drop probe does, would settle it; to do.
- **Food/hr:** 0.99 to 1.16.
- **Found on the way:** four runners on one server crawled. Each idle tick's
  click (`interact`) pathfinds to every candidate NPC, and Ardougne's
  market is crowded with ones it can't reach. One runner a server ran
  normally. Results files are now named by target and band, as several
  runs can share a server.

### Ava's devices: the agent can buy them (Caleb)
2026-11-07, `m002-commit-and-avas-devices`. Asked whether the server has Ava's
devices, Caleb decided: "Our agents can buy them from Ava for a nominal fee."
How they're modelled is OQ-28. Found in the server's source:
- **Have them:** Ava's attractor and accumulator (`AvasDevice.kt`,
  `RangeSwingHandler.getDropRate`, `AvaDialogue.java`): cape slot,
  untradeable. Wearing one needs Animal Magnetism, which every RL character
  has. It starts without one, because the quest's `finish` gives the device
  and our completion sets flags only.
- **Getting one:** Ava, in Draynor Manor at (3093, 3357), sells an attractor
  for 999 gp, as often as asked. At 50 Ranged she upgrades it to the
  accumulator for 75 steel arrows. Her dialogue's choices should work with the
  bridge's `interact` and `dialogue_button` (untested). Getting there is
  untested too: the manor's front doors open only from outside
  (`DraynorManorPlugin`), and our travel map has no crossings in the manor.
- **Ammunition:** with either device worn, 80% of shots go back to the quiver.
  Not with chinchompas or a bolt rack, and not over a metal chest body. Of the
  other 20%, none land below Ranged 22, half land from 22 to 81, and
  two-thirds from 82. So the arrows used fall from every shot to 1 in 5, and
  the arrow piles from 80–89% of shots to at most 13% (OQ-27). Both devices
  save the same on this server.
- **Attraction:** every 300 game ticks, a worn device gives a random iron or
  steel item: about 127 gp each for the attractor and 201 for the accumulator
  (`prices_v2`). A matching ammunition item goes to the quiver; anything else
  goes to the inventory, or to the ground if the inventory is full. That's 20
  a game hour, 11 of them taking a slot for the attractor. Operating the
  device turns this off.
- **Bonuses:** the attractor +2 ranged attack and +2 magic defence; the
  accumulator +4 and +4, and +1 slash defence.

### Decided: OQ-27 (d); Ava's devices on the GE (OQ-28's first part)
Caleb, 2026-11-07: "OQ27 - Option d. Does the attractor have a required range
level for equip? Also, let's flag ava's devices as buyable at the GE - with a
price of 2,500 for attractor and 10,000 for accumulator - and add them to the
vocabulary so that we don't have to teach the agent Draynor Manor."
`m002-devices-on-the-ge`.
- **OQ-27, answered: (d).** The question was how ranged's arrow pickups are
  modelled.
  - The options:
    - (a) count the arrow piles in the sim's fights, with one pickup time
      for every class;
    - (b) keep the per-drop constant, and list the two ranged cases as known
      gaps;
    - (c) the runner picks up arrows only when nothing attacks it;
    - (d) recommended, after Caleb's account of how rangers play. Ranged
      fights safespot on both backends. A ranged candidate needs a safespot,
      unless its expected damage is trivial: no more than the hitpoints
      regenerated meanwhile. Arrows are picked up between kills when the walk
      takes no hits, otherwise just before the oldest pile despawns (200
      game ticks after its first arrow). A trip costs the walk from the
      safespot and back, plus a pickup a pile, with one pickup time for
      every class. Refit.
  - Caleb: (d). Not built yet.
- **OQ-28's first part, answered: the GE sells both devices.** The question
  was what's bought.
  - The options: (a) the attractor only, from Ava (recommended); (b) the
    attractor, and the upgrade to the accumulator from Ava.
  - Caleb: both, on the GE, at 2,500 and 10,000 gp, and in *V*, so the agent
    needn't learn Draynor Manor.
- **Caleb's question, answered from the source:** neither device needs a
  Ranged level. Their item configs have no requirements, and the only check
  is Animal Magnetism, which every character has. Ava's 50 Ranged gates only
  her upgrade, which the GE skips: a level-3 character can wear the
  accumulator (OQ-28).
- **Built:**
  - **Prices** (`scripts/build_price_tables.py`, `SET_PRICES`): the frozen
    database gets a price row for each device, as the server's `::allowge`
    would. Both join the historical list, so the frozen seller sells them
    and the frozen buyer buys them back at the same prices. `prices_v2`
    values them there (source `ge_set`). The alchemy term doesn't apply,
    since the spell refuses untradeable items. Checked against the committed
    database, nothing else changed. Installed into the three instances.
  - **Sim:** `buy_ge_10498` and `buy_ge_10499`, one at a time while nothing
    as good is held; the accumulator outranks the attractor. *V* 216.
  - **Masked actions:** the devices' alchemy and store-sale actions stay
    masked, as on the server. So does their drop: the game offers Destroy,
    not Drop (checked live; `gd.destroy_only_items`). `drop_misc` now leaves
    destroy-only items as well (59 appear in drop tables: Slayer heads and
    quest items).
  - **Not yet:** the devices' effects (OQ-28's open parts). A worn device
    saves no arrows in the sim yet.
  - **Sizes:** *V* 216, 153 buys (116 at the GE), 1,330 actions, 2,118
    observation features. Env contract v1.16 (to confirm), which also
    corrects v1.15's pickup times to the refit's 5 and 18 ticks.
  - **Tests:** the buy, its mask, and the dead actions. Live: both devices
    bought at the set prices, the attractor worn, no Drop, the accumulator
    sold back for 10,000.
  - **Agent choices (reversible):**
    - every *V* item keeps its five actions, with the devices' four dead
      ones masked, rather than a layout per item;
    - the devices can be sold back, since the frozen buyer's list is the
      seller's;
    - destroy-only misc items aren't dropped.

### Decided and built: what Ava's devices do (OQ-28); the interference rule found narrower (OQ-29)
Caleb, 2026-11-07: "Avas devices attraction effects do not work if any metal
items are equipped. That needs to be understood when modeling the behavior.
OQ28 - Wear the devices only in ranged combat. Have the item collection turned
off. Most of those items are not as valuable as the space they would
otherwise take. Modeling drop behavior because of the junk items isn't worth
the time or additional complexity. 2, option i 3, Implement a level 50 ranged
skill requirement for the accumulator, no requirement for the attractor. 4.
a" `m002-device-rules`.
- **OQ-28, answered.** The question was what the devices do once bought.
  1. **When it's worn.** The options: (a) in ranged fights, with attraction
     on (recommended); (b) always, attraction everywhere; (c) in ranged
     fights, with attraction off. Caleb: (c), because the attracted items
     aren't worth their slots or the modelling.
  2. **The accumulator's ammunition** (Caleb's question). The options: (i)
     keep the 80% catch and gather the missed shots that would land
     (recommended); (ii) use the normal roll, gathering every landing shot.
     Caleb: (i).
  3. **A Ranged level for the accumulator.** The options: (a) 50 Ranged to
     wear it (recommended); (b) none. Caleb: (a), and none for the attractor.
  4. **The observation.** The options: (a) a cape role (recommended); (b)
     the buy masks. Caleb: (a).
- **Built in the fork** (uncommitted):
  - `RangeSwingHandler.useAmmo`: with the accumulator worn, a shot its catch
    missed that would land goes back to the quiver; breaks still break. The
    attractor's still land.
  - `item_configs.json`: the accumulator requires Ranged 50, which the
    server's equip check enforces.
  - `RLCommands`: `spawn` switches the devices' attraction off, a saved
    setting as operating a device sets it. `item_definitions` exports each
    item's worn model.
- **Built in the sim:**
  - `equipment.shot_outcomes`: a shot's chances of going back to the quiver
    and of landing, ported from `getDropRate` and `useAmmo`. Fights
    (`_ammunition`) and the ranking's held shots (`slots._attacks_held`)
    use it.
  - `wield_best`: a ranged fight wears the best device carried, over any
    other cape. Other fights take it off (`hinders`).
  - The ranged gear withdrawal brings the best device out first.
  - `can_wear` reads the accumulator's Ranged 50 from the config, so its buy
    is masked below 50.
  - The cape role: E 12, 2,119 features.
- **The interference rule, found** (Caleb's note): the server's rule is
  narrower than "any metal item". OQ-29 has the details and the choice.
  - Built as the server has it: `data/ava_interference.csv`
    (`scripts/export_ava_interference.py`, the server's own models).
  - Agent choice (reversible): a ranger wearing a device leaves interfering
    chest armour off, as magic leaves metal off.
- **Measured** on the rebuilt server: at Ranged 1 the accumulator is refused
  ("You need a Ranged level of 50 to wear this."), and at 50 it goes on.
  Wearing the attractor for 305 ticks attracted nothing. Shooting cows at
  Ranged 50: with no device, 58 of the 70 arrows used landed (0.83; the
  formula's 0.86); with the attractor, 13 of 20 (0.65; the formula's 0.5,
  within the noise of 20); with the accumulator, none of the 6 used (its own
  piles counted by each pile's key; a first count by tile picked up the
  previous run's piles and missed successive piles on a tile).
- **Tests:** `tests/test_sim_avas_devices.py`: the rolls, the outcomes, the
  interference, arrows used over 20,000 shots, the level, the loadout, the
  withdrawal, the cape role.

### Fixed: the live tests' worker group under xdist
2026-11-07, `m002-device-rules`. `tests/conftest.py` marks the live tests
`xdist_group("server")` so that `-n 8 --dist loadgroup` keeps them on one
worker. The mark never took effect, because xdist's own collection hook,
which turns groups into the test ids' `@server`, ran before ours. Live tests
from different files then ran on several workers at once, each setting the
one tick speed, and a full parallel run hung (a bridge request waiting
past 20 minutes). Ours now runs first (`tryfirst`): all 53 live tests on one
worker, and the whole suite, 348 tests, passed in 4 minutes.

### Decided: OQ-29 (a), the server's rule for which armour stops Ava's devices
Caleb, 2026-11-07: "OQ29 - Option a" `m002-oq29`.
- **The question** (raised 2026-11-07 from Caleb's note that the devices
  don't work while any metal item is worn): which armour stops a device.
  The server's rule is narrower. Only the chest piece counts, and only if
  its worn model is one of the three in `AvasDevice.metalBodies`, which is
  38 pieces. The iron chainbody, the Saradomin platebody and the dragon
  chainbody aren't among them, nor is any helm, legs, shield, glove or
  boot. Interference stops only the 80% catch.
- **The options:** (a) keep the server's rule, on both backends
  (recommended); (b) fix the server's gaps in the fork, so that every metal
  chest piece interferes and interference stops the whole device; (c)
  Caleb's rule in the fork, any metal item worn, with a definition of
  metal.
- **Answer:** (a). Nothing changes: the rule as built in `m002-device-rules`
  stands (`data/ava_interference.csv`, `equipment.shot_outcomes`), and a
  ranger wearing a device leaves those chest pieces off. The option catalog
  and the env contract's Ammunition row now state it.

### Built: ranged fights from safespots and their arrow piles (OQ-27 (d)); Caleb's note on safespots and wyverns
Caleb, 2026-11-07: "Continue with implementation." Then, while it ran: "Safespots work when a monster's southwest
tile is in line of sight of our character, is in range of our weapons, and they cannot attack us. This is most
common for melee only monsters, but a "safespot" for Skeletal Wyverns exists because you can outrange their long
range attacks, once aggression has run out in their area. Skeletal Wyverns should be an incredible money maker."
`m002-safespots`.
- **Found on the server** (for the chase):
  - Monsters chase with the DUMB pathfinder (MovementPulse; no NPCBehavior overrides it), a step a tick toward the
    tile beside their target that `DestinationFlag.ENTITY` picks, until their swing handler's `canSwing` lets them
    attack. A wall or fence holds a melee monster.
  - A monster that shoots stops at its reach: `RangeSwingHandler` 7 tiles between centres, plus half the sizes. The
    skeletal wyvern's handlers (`SkeletalWyvernBehavior`, switching at 5 tiles from a player) both check that reach,
    so its chase can stick beyond its reach and a ranger outranges it, as Caleb said. A long-ranged bow reaches 9.
  - Chromatic dragons attack only in melee reach, breath included (`ChromaticDragonNPC`: its MultiSwingHandler takes
    each attack's own reach, and the dragonfire's is melee), so they can be safespotted too.
  - A ranged attack's line of sight is a clear projectile path between any tile of the character and any of the
    monster (`isProjectileClipped`), not only the south-west one: OQ-31.
  - An NPC chasing past its leash (1.5 times its walk radius from its spawn) turns home; one walking when attacked
    keeps walking until the first hit lands, and then chases from there.
- **Built in the fork** (uncommitted):
  - `ranged_safespots` runs that chase with the server's own functions on detached copies of the monster (never
    initialised, never in the world): the tiles a character can walk to and shoot from where the chase from the
    monster's spawn sticks with every tile of it in shot. For each: the monsters it holds against, where they stick,
    the walk to their arrows, the share of their wandering it holds from, and the aggressive monsters that reach it,
    which aggression running out (Caleb) lets it keep. Ranked: no threats first, then the most held, the largest
    share, the shortest walk.
  - `npcs`: the monsters a character sees, whether each is walking or fighting, and whether it would stay stuck in
    shot from the character's tile.
- **Built in the sim** (`rlscape/combat/safespots.py`):
  - A ranged target needs a safespot unless its damage over a kill is no more than the hitpoints regenerated
    meanwhile, or, from a safespot only, when the gear doesn't guard against its special damage (a bow takes no
    shield, so green dragons are ranged only from one).
  - The safespot comes from the export, for the style's range, and needs to hold from at least half the monsters'
    wandering. From it the monster does nothing, and the site's supply is the monsters it holds against.
  - Arrows lie where the monster stands: a pile per 100 ticks of shooting, which is how long a pile stays private
    and takes more. They're picked up with the drops between kills, a pickup each, plus the walk from the safespot
    and back.
  - When aggressive monsters guard the piles and aggression hasn't run out, the fight leaves them until the oldest
    would go, 200 ticks after it was dropped. The rankers take a trip after every kill.
  - One pickup time for every class: 5 ticks, melee's fit. Ranged's 18, which covered its arrows, is gone. To refit
    on the ranged runs.
- **The runner** (`scripts/calibrate_combat.py`): a case the sim safespots stands on the server's tile with
  auto-retaliate off, as rangers safespotting do, since retaliating walks them off it. It attacks only a monster the
  tile holds against, once it stands still where it holds. Ranged loots only between kills, and a safespotter walks
  back afterwards.
- **Agent choices (reversible):** the half-share threshold; the walk at a tile a tick; the rankers' trip after every
  kill; threats counted for a fresh character; the runner's standing-still rule.
- **Live, a ranger on the top tile** (Ranged 70, 99 hitpoints), attacking only held monsters:
  - no hits at Varrock sewers' moss giants, two sets of hill giants, the Taverley Black Knights (aggressive, ten of
    them), the Asgarnian Ice Dungeon's skeletal wyverns and the Wilderness green dragons;
  - west of Ardougne, a hill giant held, but most attacks didn't start;
  - a Black Knight by the Wilderness edge hit, on the tile the share ranking picked (the walk ranking's first tile
    held).
  Before the character was kept from attacking a monster that wasn't held, or a walking one, it walked off the tile.
- **The export** (`data/ranged_safespots.csv`, `scripts/export_ranged_safespots.py`; three servers): every pool
  site at both ranges.
  - **A first export was wrong.** 145 of 150 sampled tiles were inside objects (fences, trees, rocks: a clipping
    flag's 0x100). Only a teleport stands there, and no monster reaches it, so "safespots" were everywhere (93% of
    sites) and the live checks above held for that reason. `reachesTile` had accepted a walk ending beside the
    tile. Now the tile must pass the server's `RegionManager.isTeleportPermitted` and the walk must end on it
    (`walksOnto`).
  - **Re-exported:** 51% of the 2,236 sites have a range-7 safespot and 57% a range-9 one. Holding from at least
    half the wandering, 15% and 25%. At 619 of the usable ones aggressive monsters guard the piles.
  - Live again on the fixed tiles: the moss giants west of Ardougne held (no hits). The Edgeville
    dungeon's hill giants and Lumbridge's cows didn't: the character's own combat walked it off its tile, and it
    was hit. The server's chase still differs from the emulation somewhere not yet found.
  - Four sites have no answer (two quest bosses not spawned, two God Wars Dungeon monsters the teleport didn't
    reach); the export retries a teleport until it lands.
- **Raised for Caleb:** OQ-30 (what's trivial), OQ-31 (which tiles a ranger must see), OQ-32 (Slayer for the
  wyverns: they need 72, which the sim can't train).

### Decided: OQ-30 (b), OQ-31 (a), OQ-32 (c): what's trivial, what a ranger sees, no Slayer levels
Caleb, 2026-11-07: "OQ31 - Keep the server's rule. OQ 32 - Drop slayer requirements for all monsters. OQ 30 -
Option B" `m002-safespot-answers`.
- **OQ-30, what counts as trivial damage** for a ranged target without a safespot (raised in `m002-safespots`):
  - The options:
    - (a) keep the rule as built: no more damage over a kill than the hitpoints regenerated meanwhile (recommended,
      since most sites have a safespot);
    - (b) the fight needs no food: over the option (*D*), the expected damage less what regenerates fits in the
      hitpoints above the retreat point;
    - (c) the monster's max hit, after the prayers flicked, is at most 1.
  - Caleb: (b).
  - Built: `safespots.needs_safespot` takes the hitpoints above the retreat point and the option's duration, in
    both rankers, the fight and the runner. A fresh ranger has 5 to spare and regenerates about 15 over 1,500
    ticks, so a rat is still the only trivial target. A stronger one has more to spare.
- **OQ-31, which tiles of a monster a ranger must see** (Caleb's note: its south-west tile):
  - The options: (a) the server's rule, a clear projectile path between any tile of each and the centres in range
    (recommended); (b) a fork change to the south-west tile.
  - Caleb: (a). Nothing changes: the safespot search already calls the server's own functions.
- **OQ-32, skeletal wyverns** (they need Slayer 72, which the sim can't train):
  - The options:
    - (a) leave them out (recommended, with peer review three weeks off);
    - (b) Slayer tasks as options;
    - (c) drop the Slayer level requirement, in the fork and the sim.
  - Caleb: (c), for every monster.
  - Built in the fork: neither `NPC.isAttackable` nor `IdleAbstractNPC.isAttackable` refuses an attack any more.
    The fork had refused since 2026-10-28. `NPC.checkImpact` no longer cancels a player's hits on a monster above
    its Slayer level, as upstream did. The ice cooler no longer asks for Slayer 22.
  - Built in the sim: no Slayer gate in either ranker or in access.
  - Agent choice (reversible): the Slayer monsters that need gear the sim doesn't model stay out of the pool
    (`candidates.SLAYER_GEAR_NPCS`, 15 of the 35 that had a level). Before, their Slayer levels kept them out.
    Their gear: a nose peg, earmuffs, a face mask, a leaf-bladed weapon, a rock hammer, a bag of salt, an ice
    cooler, a lit bug lantern, a witchwood icon, a mirror shield, insulated boots. The other 20 are open, among
    them abyssal demons, bloodvelds, nechryaels and skeletal wyverns. Slayer item uses that need levels, such as
    Magic Dart's 55, are untouched.
  - Live test: `test_slayer_levels_lock_no_monster` (a fresh character fights cave crawlers, Slayer 10, and gains
    XP), in place of `test_slayer_level_blocks_attacks`.

### Decided: OQ-33, guarded arrows fetched with a shield; the calibration's rangers use a rune crossbow
Caleb, 2026-11-07: "OQ33 bring a shield to pick up the arrows. Or use anti dragonfire potions. Or both." Then: "Use a
rune crossbow instead of a bow." `m002-safespot-answers`.
- **OQ-33** (raised in `m002-safespots`: at the Wilderness green dragons the late trip for guarded arrows took
  dragonfire, unshielded, and every run ran out of food):
  - The options:
    - (a) at a guarded site, leave the loot until aggression runs out (recommended);
    - (b) keep the late trip and model its hits;
    - (c) rule out guarded sites unless the guards' damage on the trip is trivial.
  - Caleb: the late trip stays, with an anti-dragon shield worn for it, an antifire potion, or both.
  - **Found:** on this server the potion alone cuts dragonfire by only a tenth, 52 to 46
    (`ContentAPI.calculateDragonfireMaxHit`). The shield cuts 90%, to 5, and both together cut it to nothing.
    Protect from Magic alone cuts 60%. So the shield is what makes the trip survivable, and the potion completes
    it.
  - Built in the sim:
    - the late trip takes the guards' hits (`combat.guarded_trip`: each guard, taken as the target's kind, swings
      over the trip);
    - against dragonfire the ranger wears the shield it carries (a swap with the bow, `SWAP_TICKS`) or already
      wears (a crossbow's), and drinks an antifire dose if it has one;
    - the rankers offer a guarded safespot against special damage only to a ranger with a shield for it, worn or
      carried (`Character.shields_carried`).
  - Built in the runner: it wears the carried shield before a late trip and wields the bow again after.
- **Rune crossbow (Caleb).** A crossbow is one-handed, so the anti-dragon shield is worn throughout. Bands 61 and 91
  of the calibration fight with a rune crossbow and rune bolts (61 Ranged each) in place of the magic shortbow and
  rune arrows. Bands 1 and 31 keep their bows; the rune crossbow needs 61.
  - Every ranged calibration character carries an anti-dragon shield (agent choice, reversible): with a bow it
    stays in the inventory for the trips.
  - Neither crossbows nor bolts are in *V*, so an agent can't buy one yet.
  - The runner sets the style on the crossbow's own weapon tab (79).

### Decided and built: every crossbow and bolt joins *V* and the GE buys (Caleb)
Caleb, 2026-11-07: "What crossbows are available in 09scape?" Then: "Add all crossbows and bolts to the vocabulary."
`m002-safespot-answers`.
- **On the server:** 11 crossbows are tradeable and on the 2009 GE:
  - plain and bronze (Ranged 1), iron (26), Dorgeshuun (28, bone bolts), steel (31), black (33), mithril (36),
    adamant (46), Hunters' (50, kebbit bolts), rune (61), Karil's (70, two-handed, bolt racks);
  - left out: blurite (untradeable), Phoenix (a quest item, no 2009 price) and Karil's degraded states.
  All but Karil's are one-handed, so a shield goes with them.
- **The bolts:** 53, every tradeable bolt the crossbows fire that has a 2009 price: bronze to rune, black, silver,
  bone, kebbit, broad, the bolt rack, and the poisoned, gem-tipped and enchanted kinds. Left out: blurite bolts,
  jade bolts, and two adamant poisons (untradeable or no price).
- **Built:**
  - 63 new *V* items (mithril bolts were in already, as a drop): *V* 279. They're GE buys, one crossbow at a time
    while nothing as good is held, and bolts in lots of 100 (the arrows' rule).
  - A crossbow's equipment tier in the observation is the bows' its Ranged level allows (`encoding._bow_tier`).
  - 1,709 actions, 2,624 features.
  - Checked live: the frozen GE sells a rune crossbow at 9,927 gp and rune bolts at 610 each.
- **Not modelled:** the bolts' poison and enchantment effects; they rank by ranged strength alone. Broad bolts are
  Destroy-only, so their drop action stays masked, as Ava's devices' does.

### Decided: ranged calibration fights in the ranker's style; the ranged runs from safespots; the guards' rate
Caleb, 2026-11-07: "Yes, fight in the style the ranker picks. Rapid should be picked over accurate in most
circumstances. Longrange has the feature of splitting xp between range and def and also increases the range of the
attack." `m002-safespot-answers`.
- **The question** (raised in `m002-safespots`): ranged calibration had fought in the server's default style,
  accurate, while the ranker picks targets on its best style. A safespot can depend on long-ranged reach: the
  Wilderness green dragons' needs range 9.
  - The options: (a) fight in the ranker's style, set on the weapon tab (recommended); (b) keep accurate.
  - Caleb: (a). `scripts/calibrate_combat.py`'s `--style` now defaults to `ranked`, and melee stays accurate. The
    ranker does pick rapid in most cases, and the sim has long-ranged's split XP and reach.
- **The ranged runs** (sim over server, XP/hr; rune crossbow kit at 61 and 91, the shield worn; the runner as
  rebuilt; the corrected table):
  - Check set, the top by gp, looting:
    - cows, band 1 (rapid, safespot): 1.01 (gp 1.03), no hits;
    - unicorns, band 31 (longrange, safespot): 1.06 (gp 1.00), 1 to 7 damage a run;
    - green dragons, band 61 (rapid, safespot, guarded): 1.11 on the first sim; 0.99 (kills 1.00, gp 1.02) once the
      guards' rate was fixed (below). No food eaten on the server.
  - Fit set, the top by XP, no looting, no safespot needed: rats 1.20 (rapid; accurate gave 1.01), scorpions 1.03,
    experiments 1.02 and 1.06.
- **Fixed in the sim: a late trip's guards.** The sim had every guard swing at its attack speed for the whole trip:
  30 to 86 damage a trip at the green dragons, where the server's runs took none. The export counts as a guard any
  aggressive monster whose leash covers the arrows, and most never come. Each guard now swings at
  `aggression.ATTACKS_PER_TICK`, the rate measured while gathering (agent choice, reversible).
- **The pickup time, refit:** 5 ticks for every class, on the four melee loot cases and the two ranged safespot
  ones (mean |log ratio| 0.053, all six inside the gate; 4 and 6 do worse). It stays 5.
- **Runner fixes on the way** (`scripts/calibrate_combat.py`):
  - The stuck rule's clock starts with a fight, and there's no stuck rule on a safespot (a safespotter waits, and
    a weak one hits rarely).
  - A safespotter fetches its loot only when nothing is attacking it, waits for its loot instead of walking back
    between pickups, and clicks back onto its tile when walked off it.
  - The live safespot query uses the case's range.
  - A failed setup despawns its character.
  - Monsters stuck attacking it don't hold a safespotter back.
- **Live checks of the corrected tiles** (a ranger on the top tile, auto-retaliate off, attacking only a held monster
  standing still; no clicking back onto the tile, no wait for aggression to run out): 2 of 7 clean.
  - Held: the moss giant west of Ardougne (`test_a_ranger_on_a_ranged_safespot_takes_no_hits` now uses it) and a
    woman north of Varrock.
  - Mostly held: the hill giant west of Ardougne (2 hits, 7 hitpoints; most attacks didn't start).
  - Walked off its tile and hit: hill giants (Edgeville dungeon), cows (Lumbridge's fence), and a Black Knight by
    Draynor, which died.
  - Attacked by other aggressive dragons before its first shot, aggression not yet run out: the Wilderness green
    dragons at (3118, 3820).
  - Other aggressive giants reach every tile at Varrock sewers' moss giants.
  So the server's chase still differs from the emulation at many sites, and the sim, which takes a safespot as
  always holding, is optimistic there. The calibration cases (cows, unicorns, green dragons at another site) held
  with the runner's rules.
