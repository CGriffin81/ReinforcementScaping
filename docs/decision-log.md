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
  - Q7: every shop action is kept.
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
    bread.
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
    change; it comes with the energy change, not yet built.
  - Food: one `bank_withdraw_<food>` per GE tier (mackerel, tuna, monkfish,
    shark).
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
  - common drops are those in at least 20 of the sweep's fights
  - smithed products no other group names stay misc
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
