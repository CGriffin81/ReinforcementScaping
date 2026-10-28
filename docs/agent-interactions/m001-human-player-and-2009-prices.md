# Agent Interaction

## Metadata

- Interaction ID: m001-human-player-and-2009-prices
- Timestamp CST: 2026-10-05 23:04:34 CST (from the session transcript's message timestamp, UTC−05:00; corrected 2026-10-28, the original estimate was ~22:58:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: fork `cf238d9` (branch `rl`) and main repo `275450a`, the commits that add this record

## Full Prompt

> 1. Make a change so that the bot trades like a human player. The bot we create should be treated as a human player always.
> 2. Let's try to find a historical basis for prices and freeze the grand exchange at those values.
> 3. The prices used to value the agent's wealth should be the highest value between High Alchemy (minus the cost of nature runes) and the Grand Exchange value that we are able to find historically (from 2009).

Context: these answer the three economy decisions raised at the end of
`m001-ge-warmup-and-price-table`: the economy model, price stability, and
valuation.

## Response Summary

### 1. Treated as a human, always (fork)

- Audited all 82 places the server distinguishes artificial players. They fall
  into two groups:
  - *Session plumbing* that must stay connection-less: ping timeout, saving,
    logout hooks, autosave, shutdown save, XP logging. These now use the new
    `Player.hasClientSession()`.
  - *Game rules* that should see a human. Every check of the `AIPlayer` type
    became an `isArtificial()` check: dialogue blocking in `ScriptProcessor`,
    the tutorial damage guard and kill credit in `ImpactHandler`, drop
    tracking, Morytania effects, and `AIPlayer.finalizeDeath`'s full restore.
- New `content/rl/RLPlayer` (extends AIPlayer). In `init()` it:
  1. clears `artificial`, so timers like AntiMacro and the login configuration
     see a human;
  2. sets the tutorial-complete flag;
  3. runs **every login hook**, as `LoginParser` does for humans;
  4. calls `super.init()`;
  5. clicks **Play** on the welcome screen.
- Each step was found by testing:
  - Without the login hooks, `GrandExchangeRecords.getInstance` handed back a
    throwaway object on every call. The GE trade completed, but its slot
    vanished.
  - With the flag set before init, `LoginConfiguration` parked the character
    on the lobby screen, where it couldn't move.
- Bridge additions:
  - Dialogues are dismissed automatically each tick, like a human clicking
    "continue".
  - `ge_offer` builds the offer as the GE interface does, calls
    `StockMarket.confirmOffer`, and requires being at the GE.
  - `ge_status`; `ge_collect` goes through `StockMarket.withdraw` and falls
    back to banknotes when the inventory is full, which a test hit with 10
    oak logs and 9 free slots.
  - `item_definitions`.
  - Setup-only `debug_teleport` and `debug_give`, never exposed to the agent.
- Config: `rl.random_events` (default true, which is human behaviour).

### 2. GE frozen at historical 2009 prices

- **Source:** the RuneScape Wiki's Weird Gloop exchange API, which has daily
  prices from May 2008.
- **Window:** 2009Scape targets content "in and around January 1st, 2009"
  (2009scape.org), so the table uses the January 2009 median. An item first
  tracked later in 2009 uses its first month with data.
- **Download:** `scripts/fetch_ge_history.py`, using the `sample` endpoint
  (about 500 points per item history, 2–4 of them in January 2009), cached and
  resumable, at a polite 4 requests/s.
  - The first pass filtered by the wiki's current item list and missed rune
    gear: RuneScape later re-issued those items under new ids. The old ids'
    history is still served (rune platebody 1127: 58,400–59,000 gp in January
    2009). The fetch now requests every unnoted tradeable id.
  - A duplicate fetch process was accidentally started in the foreground and
    later stopped. All cached files are validated before building.
- **Fork:** `world.ge_freeze_prices`. `PriceIndex.addTrade` becomes a no-op,
  and bot stock is offered at exactly the index price (no 10% markup, no
  `BotPrices` floor). `rl.conf` turns it on.
- **`scripts/build_price_tables.py`** writes `data/ge_prices_2009.csv` and
  `data/grandexchange_2009_frozen.db` (the warm-up's bot stock plus the 2009
  price index). `scripts/install_ge_db.py` installs a GE database while the
  server is stopped, backing up the old one.

### 3. Valuation

- `data/prices_v2.csv` = max(high alchemy − nature rune, January 2009 GE
  price), with coins = 1 and a floor of 0.
- The nature rune is priced from the same January 2009 table.
- The high-alchemy term follows the server's actual spell rule
  (`ModernListeners.alchemize`: tradeable or alchemizable, not coins), not
  `ItemDefinition.isAlchemizable`, which is true for only 1 of 7,324 items.
- `prices_v1` is superseded for valuation but kept.

## Documentation Changes

- `docs/decision-log.md`: the three user decisions; agent interpretations;
  findings; two open questions (random events, GE selling); the 10-hour
  snapshot marked as superseded for valuation.
- `ROADMAP.md`: the valuation-table, bot-helper and economy-option rows.
- This record.

## Code Changes

Fork, branch `rl`:
- `content/rl/RLPlayer.kt` (new).
- `content/rl/RLCommands.kt`: RLPlayer spawn, dialogue dismissal, the GE and
  item-definition commands, the debug commands.
- `content/rl/RLBridge.kt`: dismisses dialogues each tick.
- `core/game/node/entity/player/Player.java`: `hasClientSession()`; `clear`
  and `finishClear` use it.
- `core/worker/MajorUpdateWorker.kt`, `core/game/world/repository/DisconnectionQueue.kt`,
  `core/game/world/GameWorld.kt`, `core/game/system/SystemTermination.java`,
  `core/game/node/entity/player/info/PlayerMonitor.kt`: session plumbing now
  uses `hasClientSession()`.
- `core/game/interaction/ScriptProcessor.kt`,
  `core/game/node/entity/combat/ImpactHandler.java`,
  `core/game/node/entity/npc/drop/NPCDropTables.java`,
  `content/region/morytania/handlers/MorytaniaArea.kt`,
  `core/game/bots/AIPlayer.java`: game rules check `isArtificial()`.
- `core/ServerConstants.kt`, `core/game/system/config/ServerConfigParser.kt`:
  `GE_FREEZE_PRICES` and `RL_RANDOM_EVENTS`.
- `core/game/ge/PriceIndex.kt`, `core/game/ge/GrandExchange.kt`: the freeze.
- `worldprops/default.conf` (new keys, stock behaviour) and
  `worldprops/rl.conf` (regenerated: bridge on, freeze on).

Main repo:
- `rlscape/bridge/client.py`: `item_definitions`, `ge_offer`, `ge_status`,
  `ge_collect`, `debug_teleport`, `debug_give`.
- Scripts (new): `scripts/export_item_definitions.py`,
  `scripts/fetch_ge_history.py`, `scripts/build_price_tables.py`,
  `scripts/install_ge_db.py`.
- `tests/test_human_player_live.py` (new).

## Infrastructure Changes

- About 4,260 HTTP requests to `api.weirdgloop.org` (sampled price history, at
  4 requests/s), cached under `results/ge_history/` (local only).
- New data files: `data/item_definitions.csv`, `data/ge_prices_2009.csv`,
  `data/prices_v2.csv`, `data/grandexchange_2009_frozen.db`, each with
  `.meta.json` where applicable.
- Installed the frozen 2009 GE database into the local server. The previous
  database is kept as a timestamped `.bak`.

## Decisions

- **User decisions (implemented):** the RL character is always treated as
  human; the GE is frozen at historical 2009 prices; wealth is valued at
  max(high alchemy − nature rune, 2009 GE price).
- **Agent interpretations (reversible, listed in the decision log):**
  - the January 2009 median window
  - frozen bot stock sells at exactly the 2009 price
  - items with no 2009 data keep the seeded GE price
  - noted items take their unnoted item's prices
  - the alchemy term follows the spell rule
  - automatic dialogue dismissal
  - the GE-proximity requirement
  - collecting as banknotes when the inventory is full
  - setup-only debug commands
- **Pending, for the user:** random events (on, per "always human") and GE
  selling (it has no buyers in this world).

## Validation

- **Fork build:** `mvnw.cmd -B -q package -DskipTests` exit 0 on every iteration.
  The fork is committed as `cf238d9`.
- **Human treatment, found by testing and fixed one failure at a time:**
  1. The GE slot was lost even though the trade completed. The database showed
     10/10 oak at 12 gp, collectable. Fixed by running the login hooks.
  2. The character couldn't move: it was parked in the lobby. Fixed by clicking
     Play.
  3. Collecting failed: 10 unstackable logs and 9 free slots. Fixed with the
     banknote fallback.
  4. Woodcutting stalled: the welcome screen, interface 378, refused to close
     without the "login" lock. Fixed by taking the lock first.
  5. Plain message boxes weren't dismissed. Dismissal now uses the same
     condition that blocks a human.
- **Price history:** 4,261 unnoted tradeable items requested; 0 failed; all
  cached files parse. 3,276 items have a 2009 price: 3,188 from January, 88 from
  a later 2009 month. Nature rune (January 2009) is 229 gp.
- **Valuation (`prices_v2`, 7,324 rows):** 6,048 rows valued from the 2009 GE
  price, 142 from high alchemy minus a nature rune, 1,133 floored at 0 (no 2009
  data and alchemy below the rune's cost), 1 coins. Spot checks: rune platebody
  58,650; rune scimitar 29,800; cowhide 116; big bones 350; coal 177; lobster
  228.
- **Frozen GE:** 6,070 price rows set to 2009 values and 1,254 kept at the
  seeded value. The live server quoted cowhide 116, rune platebody 58,650, rune
  scimitar 29,800, coal 177, lobster 228, oak logs 26.
- **`uv run pytest -v`** against the live server on the frozen GE:
  **7 passed**. That covers spawn fidelity, unknown uids, wait, the XP-cap
  regression, the character being human (not artificial, no interface open
  after spawn, can move), a GE buy filling from bot stock at exactly the frozen
  price (coins deducted 3 × price, items received, slot cleared, price
  unchanged), and a GE sell staying unfilled.
- **`scripts/gate_check.py`:** G1 at 17.8 ms per tick when asking for 15 ms.
  G2: 38 interactions, 10 logs, 250 XP, 25 XP per log.

## Follow-Up

- The user decides on random events and on GE selling.
- Week-1 remaining: `docs/env-contract.md` and `docs/option-catalog.md` v0.
