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

### User decision (2026-10-28)
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

### User decision (2026-10-28, afternoon)
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
