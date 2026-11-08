# Agent Interaction

## Metadata

- Interaction ID: m002-case-deltas
- Timestamp CST: 2026-11-07 18:54:34 CST (first prompt) to 19:09:16 CST (second), from the session transcript's
  message timestamps (UTC−06:00); the second arrived while work was running
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: DONE (committed and pushed what there was; the case deltas investigated and fixed, the fixes committed
  with `m002-check-set-rerun`)
- Commit: the earlier work is fork `0c0f5dd` (branch `rl`) and main repo `8229e12` (branch `sim-v0`), both pushed.
  The investigation's fixes are fork `f5d1aba` and the next main repo commit, pushed with `m002-check-set-rerun`.

## Full Prompt

> Commit and push the changes, then investigate the case deltas.

Then, while it ran:

> The safespot issue at cows may be because you are trying to fight them outside of their agro radius, so they try
> to pull back to get the attacker to get inside their radius.

## Response Summary

- **Committed and pushed:** fork `0c0f5dd` and main repo `8229e12`, which add to PR #7.
- **The calibration deltas:**
  - the rats' 1.20 was noise (1.11 over 8 runs);
  - the abyssal demons are at 1.16, inside the gate;
  - the green dragons are at 0.99 since the guards' rate was fixed.
- **The safespot failures, four causes found in tick traces:**
  - The leash (Caleb's pull-back): a monster past 1.5 times its walk radius from its spawn walks home and refuses
    attacks. Now checked from the chase's start too, and reported by `npcs`.
  - The setup: standing at the site among the monsters left the character "under attack". It now goes straight to
    its tile and asks with `at`.
  - Threatened tiles: aggressive monsters reach them before aggression runs out, and they killed the checking
    character twice. Usable safespots now need none.
  - The step race: a monster starting a step as it's clicked. The runner clicks back onto its tile.
- **After the fixes:** no hits at the usable sites checked.

## Documentation Changes

- `docs/decision-log.md`: "Investigated: the case deltas".
- `docs/env-contract.md`, `docs/option-catalog.md`: a usable safespot needs no threats.
- This record. The Commit fields of `m002-oq29`, `m002-safespots` and `m002-safespot-answers`.

## Code Changes

- `rlscape/combat/safespots.py`: `safespot` requires no threats.
- `rlscape/bridge/client.py`: `ranged_safespots`' `at`.
- `scripts/calibrate_combat.py`: setup goes straight to the sim's tile and asks with `at` (a limit of 200).

## Infrastructure Changes

- Fork (`server/`, uncommitted), `RLCommands.kt`:
  - `holdsFrom` checks the leash at the chase's start;
  - `npcs` reports `returning` and the walk radius;
  - `ranged_safespots` takes `at`.
  Built; the instances run it.

## Decisions

- **User decisions:** commit and push; investigate the case deltas.
- **Agent choices (reversible):**
  - a usable safespot needs no threats (205 of 2,185 sites at range 7, 365 at range 9);
  - the runner's setup goes straight to the tile.

## Validation

- The offline suite: 305 passed.
- Live, the seven sites:
  - before the fixes, 2 clean;
  - after them, at the 3 sites still usable, no hits (the cows' check walked off its tile once, unhit), and the
    other 4 have no usable tile.
- The rats over 8 runs: 1.11.

## Follow-Up

- The check set rerun and the commit: `m002-check-set-rerun`.
