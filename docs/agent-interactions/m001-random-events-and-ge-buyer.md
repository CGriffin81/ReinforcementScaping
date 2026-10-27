# Agent Interaction

## Metadata

- Interaction ID: m001-random-events-and-ge-buyer
- Timestamp CST: 2026-10-27 ~18:50:00 CST (estimated: the first command run for this prompt reported 18:50:45 local Central time)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: fork `e69eeed` (branch `rl`); main repo: the commit that adds this record, on branch `ge-frozen-buyer-random-events` (pull request against `main`)

## Full Prompt

> 1. Turn random events off for training.
> 2. Add a buyer that fills sell orders at the frozen 2009 price.

Follow-up prompt (~18:57 CST), the app's "Create PR" action:

> ## Overview
>
> Create a pull request for the changes in this session, ready for review (not a draft).
>
> ## Steps
>
> 1. Check for uncommitted changes. If any exist, stage and commit them with a message that describes what changed and why.
> 2. Push the branch to the remote.
> 3. Open the PR with `gh pr create`. Do not pass `--draft`: the user chose "Create PR", not "Create draft PR", for this request, and that explicit choice overrides any saved memory, standing instruction, or earlier plan to open it as a draft. When the target below names a base branch and that branch exists on origin (`git ls-remote --heads origin <base>`), pass it with `--base`; otherwise leave `--base` off and let gh infer it. Write a title that summarizes the change and a body that covers what changed, why, and anything a reviewer should know. If the repo has a PR template, follow it.
> 4. Report the PR URL when done. Wrap the URL in a `<pr-created>` tag on its own line so the UI can render a live status card, like this: `<pr-created>https://github.com/owner/repo/pull/123</pr-created>`
>
> If a PR already exists for this branch, push any new commits and report the existing URL wrapped in the same `<pr-created>` tag instead of creating a duplicate, and leave that PR's draft or ready state as it is.
>
> ## Target
>
> Repository: CGriffin81/ReinforcementScaping
> Branch: main
> Working directory: D:\ReinforcementScaping

Context: these answer the two open questions at the end of
`m001-human-player-and-2009-prices`. (1) Random events were on for the RL
character under "always human". (2) GE sell offers never filled, because
nothing in this world places buy orders.

## Response Summary

- Confirmed that both repos were clean, with no new commits since 2026-10-05.
  The "changed on disk" notices were Git line-ending conversion, not edits.
- **Random events:** `rl.conf` (the training config) now sets
  `rl.random_events = false`; `RLPlayer` already removes its AntiMacro timer in
  that case. `default.conf` keeps the human default (on). Added a
  `random_events` field to the bridge's character state so tests can check it.
- **Frozen-price GE buyer:** new fork setting `world.ge_frozen_buyer`, on in
  `rl.conf` and off in `default.conf`. Implemented as
  `GrandExchange.sellToFrozenBuyer`. It runs on the GE worker thread after a
  sell offer has matched any real player buy offers, then:
  - takes the remaining amount at the frozen index price, and never pays above
    it, so asks above the index stay open;
  - pays the index price even for lower asks, as an older buy offer would under
    `exchange()`'s own rule;
  - only operates when `ge_freeze_prices` is on;
  - returns what it buys to the GE as bot stock.

  It mirrors the seller's side of `exchange()` directly, because calling
  `exchange()` with a transient bot buy offer would overwrite that item's
  bot-stock row.
- Tests: replaced the "sell never fills" test with three new ones: a sell at
  the frozen price fills and restocks the market; a sell above the frozen price
  stays open; random events are off for a spawned character.

## Documentation Changes

- `docs/decision-log.md`: new 2026-10-27 section with both user decisions and
  the implementation choices, including that items with no 2009 price are
  bought at their seeded high-alchemy GE price.
- `CLAUDE.md`: the config list and the description of `rl.conf` as the
  training config.
- `ROADMAP.md`: the Appendix A economy row now includes selling at the GE.
- This record.

## Code Changes

Fork, branch `rl` (uncommitted):
- `Server/src/main/core/game/ge/GrandExchange.kt`: `sellToFrozenBuyer` and its
  call in the worker loop.
- `Server/src/main/core/ServerConstants.kt`,
  `Server/src/main/core/game/system/config/ServerConfigParser.kt`:
  `GE_FROZEN_BUYER` / `world.ge_frozen_buyer`.
- `Server/src/main/content/rl/RLCommands.kt`: `random_events` in the character
  state.
- `Server/worldprops/default.conf`: `ge_frozen_buyer = false`, documented.
- `Server/worldprops/rl.conf`: regenerated, with buyer on, random events off,
  and the header updated.

Main repo (uncommitted):
- `tests/test_human_player_live.py`: the buyer and random-event tests.

- **PR follow-up:** committed the fork changes on `rl` as `e69eeed`, following
  CLAUDE.md's fork-first workflow, and pushed. Because `main` can't be the
  head of its own PR, the main-repo changes went on a new branch,
  `ge-frozen-buyer-random-events`, with the submodule pointer at `e69eeed`.
  That branch was pushed and a ready-for-review PR opened against `main`.

## Infrastructure Changes

- Reinstalled the clean frozen GE database into the local server before and
  after testing. The previous databases are kept as timestamped `.bak` files.

## Decisions

- **User decision (implemented):** random events off for training.
- **User decision (implemented):** a buyer fills GE sell orders at the frozen
  2009 price.
- **Agent choices (reversible, listed in the decision log):**
  - the buyer acts after real buy offers
  - it pays the index price even for lower asks, and never more
  - frozen market only
  - bought items return to bot stock
  - items without a 2009 price are bought at their seeded high-alchemy price.
    This could be limited to items with a 2009 price if preferred.

## Validation

- Fork build: `mvnw.cmd -B -q package -DskipTests` exit 0.
- Server started on the clean frozen GE with `rl.conf` in 8.3 s, with no
  exceptions in the log.
- `uv run pytest -v`: **9 passed** in 20.6 s, including
  `test_ge_sell_fills_at_the_frozen_price_and_restocks_the_market`,
  `test_ge_sell_above_the_frozen_price_stays_open`, and
  `test_random_events_are_off_for_training`.
- `scripts/gate_check.py` (`results/gates/gate_check_20261027_185419.json`):

  | Requested ms/tick | Achieved ms/tick |
  |---|---|
  | 600 | 600.3 |
  | 120 | 121.2 |
  | 60 | 60.7 |
  | 30 | 31.4 |
  | 15 | 16.4 |

  G2: 39 interactions, 10 logs, 250 XP.
- Not separately tested: `default.conf` with the buyer off. The setting
  defaults to false, and the buyer code only runs when it is true.

## Follow-Up

- Caleb reviews the PR. The server-side diff is fork commit `e69eeed` on `rl`;
  the main-repo PR shows only the submodule pointer move for it.
- Schedule: today is in ROADMAP week 4, but the week-1 environment interface
  and option catalog, and everything from week 2 on, haven't started. The plan
  needs re-baselining.
