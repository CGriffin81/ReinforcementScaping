# Agent Interaction

## Metadata

- Interaction ID: m001-buyer-historical-items
- Timestamp CST: 2026-10-27 19:00:06 CST (from the session transcript's message timestamp, UTC−05:00; corrected 2026-10-28, the original estimate was ~19:00:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: fork `b9d3da0` (branch `rl`); main repo: `403cd29`, the commit that adds this record, on `ge-frozen-buyer-random-events` (PR #1)

## Full Prompt

> Limit the buyer to only items with a 2009 price.

Follow-up prompt, after the agent asked whether to add the change to PR #1:

> Yes, add it to the PR

Context: an open choice raised in `m001-random-events-and-ge-buyer` and in the
body of PR #1. The frozen-price buyer paid the seeded high-alchemy GE price for
the roughly 1,250 item rows with no 2009 price.

## Response Summary

- The server didn't know which items have a historical price, since the frozen
  database stored only values. Rather than adding a separate file for the
  server to load, the eligibility list goes into the frozen GE database itself,
  so installing the database also installs which items the buyer may buy:
  - Fork: `GEDB.expectedTables` declares `historical_price_items(item_id
    INTEGER PRIMARY KEY)`. The server creates it empty for any GE database
    that lacks it, so with such a database the buyer buys nothing.
  - Fork: `GrandExchange.sellToFrozenBuyer` returns early unless the item is in
    that table (new `hasHistoricalPrice`). The config comments for
    `ge_frozen_buyer` say so.
  - `scripts/build_price_tables.py` fills the table with every price row it
    sets to a 2009 value: 6,070 rows, unnoted and noted ids.
- Rebuilt `data/grandexchange_2009_frozen.db` and its metadata.
  `data/prices_v2.csv` and `data/ge_prices_2009.csv` rebuilt byte-for-byte
  identical.
- New live test: an item with no 2009 price (Empty oyster, 409, with that
  precondition asserted from the data file) offered at its GE price stays
  unsold. The existing buyer test still sells a bronze axe at its frozen price.
- A first attempt to patch the builder with an inline Python script stopped on
  an escaping mismatch before saving anything, and the rebuild that followed
  produced a database without the table. That was caught by the table check,
  and the builder was then patched with exact edits.

- **PR follow-up:** committed the fork change on `rl` as `b9d3da0` and pushed.
  Committed the main-repo change on `ge-frozen-buyer-random-events` with the
  submodule pointer at `b9d3da0`, pushed (updating PR #1), and updated the PR
  description: the untracked-items reviewer note was replaced by the decision.

## Documentation Changes

- `docs/decision-log.md`: the user decision. The earlier untracked-items note
  is marked superseded.
- This record.

## Code Changes

Fork, branch `rl` (uncommitted):
- `Server/src/main/core/game/ge/GEDB.kt`: the `historical_price_items` table.
- `Server/src/main/core/game/ge/GrandExchange.kt`: the eligibility check and
  `hasHistoricalPrice`.
- `Server/worldprops/default.conf`, `Server/worldprops/rl.conf`: the
  `ge_frozen_buyer` comment.

Main repo (uncommitted, on branch `ge-frozen-buyer-random-events`):
- `scripts/build_price_tables.py`: writes the table, and records its size in
  the metadata.
- `data/grandexchange_2009_frozen.db`, `data/*.meta.json`: rebuilt.
- `tests/test_human_player_live.py`:
  `test_ge_buyer_ignores_items_without_a_2009_price`.

## Infrastructure Changes

- Installed the rebuilt frozen GE into the local server before and after
  testing. The previous databases are kept as `.bak` files.

## Decisions

- **User decision (implemented):** the frozen-price buyer only buys items with
  a 2009 price.
- **Agent choice (reversible):** store the eligibility list in the frozen GE
  database rather than in a separate config file. With any database that lacks
  the list, the buyer buys nothing.

## Validation

- Fork build: `mvnw.cmd -B -q package -DskipTests` exit 0.
- Table check: `historical_price_items` has 6,070 rows (cowhide 1739 present),
  out of 7,324 price rows.
- `cmp` confirmed `prices_v2.csv` and `ge_prices_2009.csv` are identical to
  before the rebuild.
- `uv run pytest -v` against the live server, on the reinstalled frozen GE with
  `rl.conf`: **10 passed** in 23.1 s.
- The new test can only pass because of the restriction. The offer is placed at
  the item's own index price (a zero price would have been rejected outright),
  and the same path fills for an item with a 2009 price.

## Follow-Up

- Caleb reviews PR #1. The server-side diffs are fork commits `e69eeed` and
  `b9d3da0` on `rl`.
