# Agent Interaction

## Metadata

- Interaction ID: m001-ge-warmup-and-price-table
- Timestamp CST: 2026-10-05 22:25:48 CST (from the session transcript's message timestamp, UTC−05:00; corrected 2026-10-28, the original estimate was ~22:15:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: fork `a394d60` (branch `rl`); main repo: `ffb354a`, the commit that adds this record

## Full Prompt

> We should use a snapshot taken after letting the bots trade for 10 game hours.

Context: this answers the question at the end of the previous turn: should the
fixed price table be (a) the seeded starting values (high-alchemy values) or (b)
a snapshot after letting the bots trade for a set number of game-hours? The
agent had recommended (b).

## Response Summary

- **Read the GE code before running anything**, to know whether price dynamics
  run on ticks or on the wall clock:
  - Bot sales go into a `bot_offers` stock table. Only real players' buy offers
    match bot stock.
  - Nothing in the game creates buy offers: no bot calls
    `ScriptAPI.buyFromGE`, and it never dispatches anyway.
  - The price index moves only on executed trades.
  - `GrandExchange.dispatch` turns every offer from an artificial player (our
    RL character) into a bot offer on the server's account.
  - Upstream seeding bug: `unique_trades = 0` with `total_value = alch`, so an
    item's first trade jumps its price to about alch + trade price.
  - Shops buy from players at low-alchemy value minus an overstock penalty, and
    recycle player sales into GE bot stock every 180 game-minutes.
- **Fork, `a394d60`:**
  - `GEDB.populateInitialPriceIndex` now runs in one transaction. A fresh-GE
    startup takes under a second instead of about 7 minutes; the seeded values
    are unchanged.
  - New bridge command `ge_snapshot`: the whole price index, bot stock per
    item, and the number of open player offers.
- **Main repo:**
  - `BridgeClient.ge_snapshot()`.
  - `scripts/ge_warmup.py`: samples every 30 game-minutes for N game-hours,
    writes the time series to `results/ge/`, and writes the final price table
    with provenance metadata.
- **Ran it:** renamed the old GE database to
  `grandexchange.db.pre-warmup-20261005` (not deleted), started the server on a
  fresh GE, and ran 10 game-hours (60,002 ticks at 15 ms; 21.5 minutes of wall
  time).
- **Result:**
  - 0 of 7,324 prices changed and 0 items were ever traded, while bot stock
    grew from 0 to 19,675 units of 145 items.
  - The decided snapshot is therefore exactly the seeded high-alchemy table,
    so options (a) and (b) coincide in this world.
  - Saved the end-state GE database as `data/grandexchange_warmup10h.db` for
    resetting real-server episodes.
- **Three follow-on decisions raised for the user:** the economy model, price
  stability across episodes, and valuation sensitivity.

## Documentation Changes

- `docs/decision-log.md`: the price-table decision; the GE mechanics findings;
  the G3 results; the shop economics; three pending decisions with
  recommendations.
- `ROADMAP.md`: G3 and the price-table export checked off, and the
  fixed-price-table row updated.
- This record.

## Code Changes

- Fork `rl`, `a394d60`: `Server/src/main/core/game/ge/GEDB.kt` (transactional
  seeding) and `Server/src/main/content/rl/RLCommands.kt` (`ge_snapshot`).
- Main repo: `rlscape/bridge/client.py` (`ge_snapshot`) and
  `scripts/ge_warmup.py` (new). The submodule pointer moves to `a394d60`.

## Infrastructure Changes

- Local server GE database: the old `grandexchange.db` was renamed to
  `grandexchange.db.pre-warmup-20261005` (kept). It held 7,324 prices, no
  trades, no stock, and no offers. A fresh database was seeded at startup and
  now holds the 10-hour warm-up state.
- New data files in the main repo: `data/prices_v1.csv` (7,324 rows),
  `data/prices_v1.meta.json`, and `data/grandexchange_warmup10h.db` (128 KB).
- Local-only time series: `results/ge/warmup_20261005_223023_{prices,bot_stock,summary}.csv`.

## Decisions

- **User decision:** the fixed price table is the GE snapshot after 10
  game-hours of bot trading from a fresh GE. **Implemented.** The result equals
  the seeded high-alchemy values.
- **Agent decision:** start the warm-up from a freshly seeded GE, so it's
  reproducible, and keep the previous database as a backup rather than deleting
  it.
- **Agent decision:** make the fork's price seeding transactional, so a fresh
  GE is cheap to recreate.
- **Agent recommendations (pending the user's decision):**
  1. *Economy model:* sell through shops and High Level Alchemy; buy from shops
     and from GE bot stock (needs a fork change so bridge characters trade as
     players); drop the "sell at GE" options.
  2. *Price stability:* set `bots_influence_ge_price = false` in `rl.conf` and
     reset the GE database to the 10-hour snapshot at the start of each
     real-server episode.
  3. *Valuation:* keep the high-alchemy table and add a `BotPrices`-based
     sensitivity check at evaluation.

## Validation

- Fork build exit 0. Server startup on a fresh GE took 7.9 s: the "Loading
  Player Stats" and "GE Update Worker" log lines carry the same timestamp, which
  confirms instant seeding.
- Warm-up summary at 10.000 game-hours (tick 60,020): 7,324 items priced,
  0 changed, 0 ever traded, 145 bot-stock items / 19,675 units, 0 open player
  offers.
- Read the saved database directly with `sqlite3`: 7,324 price rows, 0 traded,
  145 items / 19,723 bot-stock units, 0 player offers.
- Spot-checked price rows against the item list (logs 2, oak 12, willow 24,
  coal 27, cowhide 1, raw lobster 170, steel pickaxe 300).

## Follow-Up

- The user decides the three pending economy items above.
- Then: the fork change for player-style GE trading by bridge characters (if
  accepted), the `rl.conf` change, and a GE-reset step in the server
  environment.
- Week-1 remaining: `docs/env-contract.md` and `docs/option-catalog.md` v0.
  Both depend on the economy decision.
