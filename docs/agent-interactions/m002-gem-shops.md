# Agent Interaction

## Metadata

- Interaction ID: m002-gem-shops
- Timestamp CST: 2026-11-09 10:49:16 CST (the prompt, sent while Claude was working), from the session transcript's
  timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (investigated; OQ-57 for Caleb before building)
- Commit: None (uncommitted)

## Full Prompt

> A potentially important change I want to make to the server: gem vendors sell uncut gems for less gp than they buy
> cut gems for. Ironmen in OSRS often use this feature to make some quick gp and crafting xp by buying the uncut
> gems, cutting them, and selling them back to the vendors. This is only really viable because there are many worlds
> that a character can hop to to find fresh stock.
>
> I want you to investigate that the gem vendors on this server maintain that same pattern. If they do buy cut for
> more than they sell uncut for, I want to simulate having the same number of worlds that would have been available
> in 2009 by multiplying the stock and replenishment rate by the number of 2009 worlds. Having this as a viable
> method is potentially a really good xp/hr method for crafting that is not net negative gp.

## Response Summary

- **The server's gem shops** (`data/configs/shops.json`, `core/game/shops/Shop.kt`):
  - seven shops;
  - only the Gem Store (shop 92) sells gems for gp at its normal stock: 1 uncut sapphire and 1 uncut emerald,
    restocking a
    unit every 100 ticks;
  - a shop sells at the item's value, and buys at the alch value (Herquin's high alch), less 3% of the value for
    each unit over its normal stock.
- **The pattern holds:** an uncut sapphire is sold for 25 gp, and the cut one bought for 150 (an emerald 50 and
  300).
- **But the frozen GE prices uncut gems higher still:** uncut sapphire 616 gp, cut 393. Net worth and the frozen
  buyer use those prices. So shop-bought uncut gems would be an arbitrage on the GE, cutting would lower net worth,
  and multiplying the Gem Store's stock would make it dwarf every other method.
- **2009's worlds:** 175, of which 87 were members' (the wiki's Server page, January 2009).
- **Corrected later the same day:** this record first called shop 92 Shilo Village's Gem Store, going by its
  title. Its shopkeeper is Hervi (NPC 2157), whose only spawn is in Keldagrim, also members-only. See
  `m002-oq54-55-57`.
- **Not built, since it changes the economy and Caleb's net-worth formula.** OQ-57's options:
  - **(a)** as asked, with the GE arbitrage;
  - **(b) recommended:** the shops' own loop, with gems off the frozen GE and valued at what the shops pay, about a
    day, the freeze moving to about Nov 11;
  - **(c)** after the project.

## Documentation Changes

- `docs/open-questions-log.md`: OQ-57.
- This record.

## Code Changes

- None.

## Infrastructure Changes

- None. The wiki was read through its API in the built-in browser.

## Decisions

- **User decisions:** none yet. OQ-57 is open.
- **Agent recommendation:** OQ-57 (b).

## Validation

- **Prices and stock** read from the server's source and config. They weren't measured in the game.
- **The GE prices** come from `data/prices_v2.csv`. The world counts come from the wiki revision 893026.

## Follow-Up

- **Caleb:** OQ-57, before the freeze unless (c).
