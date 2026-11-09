# Agent Interaction

## Metadata

- Interaction ID: m002-oq52-question
- Timestamp CST: 2026-11-09 09:57:08 CST (the prompt), from the session transcript's timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (question answered; OQ-52 still open)
- Commit: None (uncommitted)

## Full Prompt

> OQ 52 Why does flax not add value? There should not be a tie to break between gathering an item that has value and
> an action that takes a lot of time and provides no gp.

## Response Summary

- **Flax does add value:** 90 gp each in `data/prices_v2.csv`, 2,520 gp a load of 28. Greedy GP picks it whenever it
  can. It's never tied with Agility.
- **The tie comes after a load:**
  - the inventory is full, so the flax option is masked;
  - every option still allowed gains nothing one step ahead, so every rate is 0;
  - banking would also rate 0 by itself (net worth counts the bank), which is why greedy falls back to `bank_deposit`
    when nothing gains;
  - but the deposit is masked, because the Crafting kit keeps flax as spinning's input;
  - so the tie is among zero-gain options, and the lowest action id, a 15-minute Agility stint, wins.
- **Agreed with Caleb's point:** greedy should never take a long zero-gain option when banking the flax and picking
  again is open. That's what OQ-52 (a) does:
  - the kit fix lets the deposit bank picked flax, so greedy banks and picks again, and there's no tie in this case;
  - the tie-break by shortest duration is a backstop for other full-inventory cases.
- OQ-52's "Found" now spells out the sequence.

## Documentation Changes

- `docs/open-questions-log.md`: OQ-52's "Why the stints happen", rewritten step by step.
- This record.

## Code Changes

- None.

## Infrastructure Changes

- None.

## Decisions

- **User decisions:** none yet. OQ-52 is still open.
- **Agent recommendation:** OQ-52 (a), unchanged.

## Validation

- **Flax's value:** `data/prices_v2.csv` (item 1779: GE price 90, value 90).
- **The masks and rates** at the decision after the first load come from the probe in `m002-doc-audit-pre-e1`:
  - `skill_crafting_gp1` not allowed, `bank_deposit` not allowed;
  - every rate 0.0.

## Follow-Up

- **Caleb:** OQ-52's option.
