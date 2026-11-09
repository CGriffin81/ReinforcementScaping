# Agent Interaction

## Metadata

- Interaction ID: m002-combat-inventories-and-potions
- Timestamp CST: 2026-11-06 22:37:44 CST (first prompt) to 23:05:03 CST (last), five prompts, from the session
  transcript's message timestamps (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS for these prompts (built and tested offline). The follow-ups, and Caleb's answer to OQ-25, continue
  in `m002-potion-doses-and-moss-giants`.
- Commit: fork `d0a7af6` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA
  can only be filled in by a later commit)

## Full Prompt

2026-11-06 22:37:44 CST:

> Logically, I don't see that we need four servers to run four agents on four different enemy types. Can we run multiple agents per server, rather than single thread agents on multiple servers?

2026-11-06 22:40:16 CST:

> Go ahead with that plan

2026-11-06 22:49:48 CST:

> Continue with implementation while these calibration tests run.

2026-11-06 23:00:57 CST (sent while Claude was working):

> Why do these runs still not bank items that are not relevant to the task at hand? The starter kit should not be carried when trying to fight monsters. A good inventory for combat should be food and potions, with empty slots for drops if the expected damage taken is low. Since we are prayer flicking in all combat situations, any monster with a single combat style should never damage the agent, meaning that combat inventories should hold as many potions as it takes to boost stats while training, if the agent opts to use potions, and open slots for loot.

2026-11-06 23:05:03 CST (sent while Claude was working):

> The only way to take no damage from green dragons is to use anti-dragonfire potions and have an anti-dragon shield, while flicking melee overheads. Although, I'm not sure if 100% protection was available in 2009, so check that against the archive. It may be that super anti-dragonfire potions are needed.

## Response Summary

- Several agents per server: the bridge serves each connection on its own thread (fork), built with the flicking;
  one shared server at 50 ms ran the dragon probe and both combat calibration sets at once, a second the live suite
  (321 passed). The rules for sharing are logged.
- Thieving calibration (new runner): the sim ran 18 to 19% fast at Lumbridge's men; a 0.44-tick overhead an attempt
  was measured and fitted, then 0.98 and 1.00.
- The calibration runs now start with a combat inventory: no starter kit, the band's gear, Prayer at the band and
  flicking on both sides, food only for the expected damage, the rest free for loot. The agent's own banking stays
  its choice (decision 1).
- Combat potions (eight, from the server's formulas), kept up by fights; antifire, and a dragon's breath now
  modelled. The 2009 wiki (Wayback, 28 February 2009): the potion with the shield gives complete immunity for 6
  minutes; no super antifire then.
- The drop probe: Black Knights, unicorns, hobgoblins and women fit the sim's tables (the women's calibration gap was
  noise); green dragons and chaos druids rerunning after fixes (antifire and food; the starter kit; the site).

## Documentation Changes

- `docs/decision-log.md`: several agents a server; the combat inventories, potions, antifire and the breath,
  thieving, the probe. `docs/open-questions-log.md`: OQ-25 (lower doses in *V*). `docs/option-catalog.md` §4.B, §8,
  §9. `docs/env-contract.md` v1.14 (to confirm): the breath and the boosts in §8; §3's sizes. `CLAUDE.md`: sharing
  a server. This record.

## Code Changes

- `rlscape/sim/potions.py` (new): the combat potions, antifire, the drinking rules and the cover.
  `rlscape/sim/state.py`: `boosts`, `boosted`, `antifire_until`. `rlscape/sim/health.py`: boosts wear off on the
  regeneration cycle. `rlscape/sim/equipment.py`: the fighter's boosted levels. `rlscape/sim/combat.py`: fights
  drink, a dragon's breath, death clears both.
- `rlscape/combat/rates.py`: the breath (`DRAGONFIRE_NPCS` moved here, `BREATH_CHANCE`, `breath_max`), its share
  of the damage, the filter's antifire cover. `rlscape/combat/candidates.py`, `rlscape/combat/ranking.py`: the
  cover, still matching. `rlscape/sim/slots.py`, `rlscape/envs/encoding.py`: the fighter after its potions, the
  cover.
- `rlscape/sim/kits.py`, `rlscape/sim/buying.py`: the potions kept and bought. `scripts/draft_vocabulary.py`;
  `data/vocabulary.csv` (+36), `data/vocabulary_draft.csv`.
- `rlscape/sim/thieving.py`, `rlscape/sim/skilling.py`: `ATTEMPT_OVERHEAD_TICKS`. `scripts/calibrate_thieving.py`
  (new).
- `scripts/calibrate_combat.py`: the combat inventory (`food_for`), Prayer, flicking; results named by slot and loot.
  `scripts/probe_drops.py`: any id of the monster, its attacker, no counting after a death, antifire and food,
  the starter kit dropped, the nearer site.
- Tests: `tests/test_sim_potions.py` (new); `tests/test_sim_thieving.py` (the overhead); the size tests.

## Infrastructure Changes

- Fork (`server/`, uncommitted): `RLBridge.kt` (a thread per connection, backlog 16). Built with the flicking;
  instance 1 shared at 50 ms; instance 2 (its own jar copy) for the live tests.

## Decisions

- **User decisions:** several agents a server; a combat inventory, not the starter kit, for calibration fights;
  potions as the agent's option; antifire, checked against 2009.
- **Agent choices (reversible):**
  - the food rule in calibration (expected damage less the hitpoints above the retreat point, plus 2, at most 15)
  - the potion rule (drink when half the boost is gone; the super first; the class's skills and defence); the
    ranking at the fight's start, boosted
  - antifire drunk before a dragon kill when it has run out; the breath one swing in three for every dragon class
  - the lower doses in *V* by the rule (OQ-25 asks)
  - the thieving overhead fitted from 4 runs at one target
- **Raised for Caleb:** OQ-25; the Yanille chaos druids (an access gap, to check).

## Validation

- `uv run pytest -q -n 8 --ignore-glob="tests/*_live.py"`: 277 passed in 64 s. ruff (pyflakes): passed.
- The full suite on instance 2 (the build before the potions): 321 passed.
- The thieving runs; the probe's results; the archive's page, as above.

## Follow-Up

- The dragon and chaos druid probes; rerun both combat sets with the combat inventory; the thieving check set (other
  targets) and stalls; the live suite on the new build.
- Commit when Caleb asks.
