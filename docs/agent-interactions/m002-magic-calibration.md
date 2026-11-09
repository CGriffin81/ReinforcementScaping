# Agent Interaction

## Metadata

- Interaction ID: m002-magic-calibration
- Timestamp CST: 2026-11-07 21:43:17 CST, from the session transcript's message timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (built and measured; two new questions for Caleb, OQ-34 and OQ-35)
- Commit: fork `1a36c9e` (branch `rl`) and the main repo commit after `21365bd` (branch `sim-v0`), both pushed

## Full Prompt

> The env contract v1.17 looks good. Continue with implementation.

## Response Summary

- **Env contract v1.17 marked confirmed.** v1.11 and v1.14 to v1.16 still carry "to confirm"; asked Caleb whether
  his confirmation covers them.
- **Next calibration item: magic,** which needed a way for the server runner to cast on a monster.
  - Fork: the bridge's `cast`, a client's spell-on-NPC packet; `npcs` reports hitpoints.
  - Checked live: a hand cast is one spell, and casting again each tick lands spells 5 ticks apart, the autocast
    rate the sim assumes.
  - Runner: magic kits per band, auto-retaliate off, casting again after each spell, and casting on whatever attacks
    it between kills.
- **Results, sim over server XP/hr:**
  - rats 1.00, poison spiders 1.07, unicorns 1.03, Black Knights 1.07, abyssal demons 0.95 and 0.95;
  - gp/hr off where rare drops dominate (OQ-20's kind).
- **The animated spades:**
  - Found: an aggressive possessed pickaxe there holds the character "under attack" in single combat. That's OQ-19's
    question: the sim doesn't see other kinds of monster at a fight's site.
  - Fighting back: 1.14 at band 61 (7 runs) and 1.33 at band 31.
  - Such monsters are near a quarter to a half of all combat sites.
- **New questions:** OQ-35 (how to treat monsters of another kind near a fight; recommended: model them as the
  gathering sites' aggressors) and OQ-34 (should magic safespot as ranged does; recommended: yes).

## Documentation Changes

- `docs/env-contract.md`: v1.17 confirmed.
- `docs/decision-log.md`: "Decided: env contract v1.17 confirmed. Built and measured: magic calibration by hand
  casts; OQ-19's first measurement (OQ-34, OQ-35)".
- `docs/open-questions-log.md`: OQ-34, OQ-35.
- `docs/option-catalog.md`: the hand-casting choice checked live; the overhead between kills as refitted.
- `ROADMAP.md`: the status line through 2026-11-07, and what's next.
- This record.

## Code Changes

- `rlscape/gamedata/server.py`: each combat spell's spellbook button.
- `rlscape/bridge/client.py`: `cast`.
- `rlscape/combat/rates.py`: the overhead's comment (magic's calibration).
- `scripts/calibrate_combat.py`: magic cases:
  - the kits (`MAGIC`);
  - `trained`: Magic set to the band in magic cases only;
  - the cast and its recasts;
  - kills read from `npcs`;
  - fighting back whatever attacks it;
  - kills counted for magic.
- `tests/test_bridge_inputs_live.py`: `test_a_hand_cast_is_one_spell_and_casting_again_each_tick_keeps_the_autocast_rate`.
- `tests/test_sim_ranged_magic.py`: the spells' buttons.

## Infrastructure Changes

- Fork (`server/`, uncommitted), `RLCommands.kt`: the `cast` command; `npcs`' `hitpoints`. Built.
- Results: `results/calibration/combat-20261107-2208.json` (fit set), `-2217.json` (the spades, fighting back),
  `-2224-slot3-valuable.json` (check set).
- The server was started for the runs and stopped after (by its PID).

## Decisions

- **User decision:** env contract v1.17 confirmed; continue.
- **Agent choices (reversible):**
  - the magic calibration kits;
  - Magic at the band only in magic cases;
  - auto-retaliate off for casters;
  - the runner fights back whatever attacks it between kills.
- **For Caleb:** OQ-34, OQ-35; whether v1.17's confirmation covers v1.11 and v1.14 to v1.16.

## Validation

- Full suite with the server up: 359 of 360 passed. The new cast test failed on its own counting and passed 3 of 3
  after the fix. Offline: 305 passed.
- The calibration runs above; 4 traced band-61 spade runs (14 to 21 kills) didn't repeat the low-damage run.

## Follow-Up

- Caleb: OQ-34, OQ-35, and the earlier contract versions.
- The willows' aggression rates; OQ-17's scope review on Sunday 2026-11-08.
- Commit when Caleb asks (fork first, then the submodule pointer).
