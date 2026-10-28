# Agent Interaction

## Metadata

- Interaction ID: m001-frozen-seller-and-decision-context
- Timestamp CST: 2026-10-27 ~19:22:00 CST (estimated: follows the related-work review, which ended at about 19:20; the server for this work started at 19:34)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: fork `fdaf116` (branch `rl`); main repo: the commit that adds this record, on branch `env-contract-and-combat-model`

## Full Prompt

> Gear, tools, and food come from a frozen-price seller and from shops.
> Where is the interface doc? I feel like I don't have enough context on the questions to accept or deny your recommendations.

## Response Summary

- **Where the doc is:** it's `docs/env-contract.md`. The chat had called it
  "the environment interface", and the file is uncommitted, so it's only in the
  local working tree. Opened it in the app's file pane.
- **Decision, part 1: the seller.** Added the fork setting
  `world.ge_frozen_seller` and `GrandExchange.buyFromFrozenSeller`, the mirror
  of the frozen buyer. It fills the rest of a player's buy offer, after real
  sellers and bot stock, at the frozen 2009 price from unlimited supply. It
  works only on a frozen market, only for items in `historical_price_items`,
  and never below the index; overpayment is refunded the way `exchange()`
  refunds against an older sell offer. The buyer's owner-notification code was
  factored into a shared `notifyOwner`. Enabled in `rl.conf`.
- **Decision, part 2: shops.** Read `data/configs/shops.json` and listed the
  authentic shops near the catalog's regions: Bob's axes, Nurmof's pickaxes,
  Zeke's scimitars, Gerrant's fishing supplies, and Lumbridge general store.
  - Price comparison: shops are cheaper for cheap tools; the 2009 GE is cheaper
    for weapons, armour and high-tier pickaxes.
  - Kept GE-only: full armour sets (no shop sells a complete set) and food
    (nearby shops stock a handful at most).
  - Excluded: three shops with 150,000+ stock that look like 2009Scape
    additions.
  - The catalog's economy section was rewritten to 67 actions, with buy
    actions per source.
- **Context for the open questions:** rewrote `docs/env-contract.md`'s
  "Decisions needed" section. Each question now has background, a concrete
  example, the options, what it changes for the study (which RQs and
  experiments), and a recommendation with reasons. Writing it out showed a flaw
  in the earlier question-5 recommendation: "sell all produce" would sell the
  ores and raw fish kept for smelting and cooking. It now recommends selling by
  category.
- **New question:** added to the catalog. Should the agent choose the source
  through separate actions, or should an executor rule decide?
- **Test finding:** the first run of the new seller test failed (11 passed, 1
  failed). An earlier test's unfilled *sell* offer for the same item, left
  after its character despawned, filled the seller test's buy offer as a real
  player-to-player trade. That's correct server behaviour, and it confirms
  that `ServerEnv.reset` must reinstall the GE database. Fixed by using a
  different item without a 2009 price (Cup of tea) and re-running on a fresh
  database.

## Documentation Changes

- `docs/env-contract.md`: the "Decisions needed" section rewritten, with
  question 5's recommendation revised to selling by category.
- `docs/option-catalog.md`: the economy section rewritten (decision recorded,
  67 actions, shop table) and a new decision on choosing a source.
- `docs/decision-log.md`: the sourcing decision, the shop-versus-GE finding,
  the GE-offer persistence finding, and the revised question-5
  recommendation.
- `ROADMAP.md`: the catalog line now says 67 actions and gives its current
  status.
- `CLAUDE.md`: the config list and the `rl.conf` description now include the
  seller.
- This record.

## Code Changes

Fork, branch `rl` (uncommitted):
- `Server/src/main/core/game/ge/GrandExchange.kt`: `buyFromFrozenSeller`, the
  shared `notifyOwner`, and its call in the worker loop.
- `Server/src/main/core/ServerConstants.kt`,
  `Server/src/main/core/game/system/config/ServerConfigParser.kt`:
  `GE_FROZEN_SELLER` / `world.ge_frozen_seller`.
- `Server/worldprops/default.conf` (`ge_frozen_seller = false`) and
  `Server/worldprops/rl.conf` (`true`; header updated).

Main repo (uncommitted):
- `tests/test_human_player_live.py`: two seller tests and a shared
  `historical_ids()` helper.

## Infrastructure Changes

- Reinstalled the clean frozen GE database into the local server before each
  test run and afterwards. The previous databases are kept as `.bak` files.

## Decisions

- **User decision (implemented):** gear, tools and food come from a
  frozen-price seller and from shops (option (c); the agent had recommended
  (a)).
- **Agent choices (reversible):**
  - the seller has the same limits as the buyer
  - overpayment is refunded
  - armour sets and food stay GE-only
  - the 150,000-stock shops are excluded
- **Agent recommendations (pending):** the env-contract questions 1–5 (with 5
  revised to selling by category) and catalog question 1 (separate actions per
  source).

## Validation

- Fork build: exit 0.
- `uv run pytest -v` on a freshly reinstalled frozen GE with `rl.conf`:
  **12 passed** in 27.5 s. That includes
  `test_frozen_seller_supplies_items_bot_stock_lacks_and_refunds_overpayment`
  (steel scimitar: no bot stock; offered 2009 price + 50; paid exactly the 2009
  price) and `test_frozen_seller_ignores_items_without_a_2009_price`.
- An earlier run gave 11 passed and 1 failed, for the cross-test GE offer
  reason above.
- Shop stock and base values were read directly from `shops.json` and compared
  with `data/item_definitions.csv` and `data/ge_prices_2009.csv`.

## Follow-Up

- Caleb answers the env-contract and catalog questions.
- Then the shop-buying path in the bridge and executor (the human shop
  interface), and the simulator's economy model.
