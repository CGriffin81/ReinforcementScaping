# Agent Interaction

## Metadata

- Interaction ID: m002-potion-doses-and-moss-giants
- Timestamp CST: 2026-11-06 23:19:05 CST (first prompt) to 23:41:12 CST (last), five prompts, from the session
  transcript's message timestamps (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (built and tested offline; the chaos druid probe rerunning, the moss giant probe and the combat
  fit set running with the combat inventory)
- Commit: fork `d0a7af6` (branch `rl`) and the main repo commit that adds this record (branch `sim-v0`; its SHA
  can only be filled in by a later commit)

## Full Prompt

2026-11-06 23:19:05 CST (sent while Claude was working):

> OQ25 - proceed with option a, so long as the lower dose potions remain consumable.

2026-11-06 23:22:27 CST (sent while Claude was working):

> What is the closest landmark to the moss giants that are failing to be fought?

2026-11-06 23:27:34 CST (sent while Claude was working):

> Treat those un-fightable moss giants West of the fishing guild as hazards.

2026-11-06 23:37:24 CST:

> For Yanille dungeon chaos druids, is the agent failing to cross the agility obstacles, making it unable to reach the druids?

2026-11-06 23:41:12 CST (sent while Claude was working):

> Ignore the yanille dungeon for this project.

## Response Summary

- OQ-25 (a): only the four-dose potions are in *V* (214). The lower doses stay consumable: fights drink any dose,
  deposits keep them, the misc actions never touch them, and the observation counts each potion's doses (a new part,
  11 × 2). 1,318 actions, 2,102 features.
- The landmark: the moss giants that refuse attacks are west of the Fishing Guild (the RuneScape Wiki's Moss giant
  page of 28 February 2009 lists them as "West of Fishing Guild"; the guild's bank is 29 tiles away, and goblins
  share the spot).
- They're hazards now, like Taverley's eastern Black Knights: out of the enemy pool, still in the world.
- The green dragon probe (with antifire): 200 kills, alive; 39 of 41 items fit (the misses are bones and hide at
  199 of 200, a missed pile). The chaos druids: 35 of 36, earth runes 81 against the sim's 28 (99% high 72); about a
  15% chance that one of 36 items lands that far out, so rerun: 36 of 36 (chance, then). The moss giants at the next site: 70 of 71 (big
  bones 199 of 200, the probe's one-pile miss again).
- Found: the server runs in dev mode (`dev = true`): champion scrolls drop 1 in 5 kills (41 in 200 moss giants),
  big fish 1 in 10 catches. Nothing calibrated so far is touched; OQ-26 asks whether to turn it off.
- The Yanille dungeon's druids: the probe teleported in, so no obstacle stopped it; Salarin the Twisted (only the
  strike spells hurt it) held it in single combat. Walking, the room is past a pile of rubble that takes Agility
  67 (the server's pathfinder, live). The dungeon's other druids, by the entrance, fight as usual (30 kills).
- Caleb: the dungeon is out of the project. `IGNORED_AREAS` takes every spawn in it out of the enemy pool.

## Documentation Changes

- `docs/decision-log.md`: OQ-25 answered and built; the moss giant hazards; the probe; dev mode found.
  `docs/open-questions-log.md`: OQ-25 removed; OQ-26 (dev mode) added. `docs/option-catalog.md` §4 (hazards, the
  Yanille dungeon), §9
  (*V* 214, 1,318 actions). `docs/env-contract.md` v1.14 (to confirm): §3's potions part and sizes. `ROADMAP.md`.
  This record.

## Code Changes

- `rlscape/sim/potions.py`: `ALL_POTIONS`, `DOSES`, `doses_held`. `rlscape/sim/economy.py`: `kept_on_deposit` keeps
  every dose. `rlscape/envs/encoding.py`: the potions part. `scripts/draft_vocabulary.py`: no "drunk" group.
  `data/vocabulary.csv`: the 33 lower doses and the vial out (214).
- `rlscape/combat/candidates.py`: the moss giants west of the Fishing Guild in `HAZARDS`; `IGNORED_AREAS` (the
  Yanille Agility Dungeon).
- Tests: `tests/test_sim_potions.py` (lower doses drunk, kept, counted), `tests/test_candidates.py` (the hazard, the
  dungeon), the size tests.

## Infrastructure Changes

- None.

## Decisions

- **User decisions:** OQ-25 (a), the lower doses consumable; the moss giants west of the Fishing Guild are hazards;
  the Yanille dungeon is out of the project.
- **Agent choices (reversible):**
  - the hazard's area: the four spawns' box widened by 6 tiles (2545 to 2566, 3394 to 3417), with only id 112 in it
  - the potions part's scales (the inventory's by 28 four-dose potions, the bank's as the bank's)
  - the dungeon's area: the server's own zone for it; the access table's Salarin rule left in place
- **Raised for Caleb:** OQ-26 (dev mode off, recommended).

## Validation

- `uv run pytest -q -n 8 --ignore-glob="tests/*_live.py"`: 279 passed in 63 s.
- The probe's results (`results/calibration/drops-20261106-2315.json`, `-2324`, `-2331`, `-2340`), as above;
  the live look at Yanille (`debug_nearby` from four tiles; a fight with Salarin there).

## Follow-Up

- Continued in `m002-dev-mode-and-pickups` (dev mode off; the overhead refit and the pickup time).
- The probe's one-pile miss.
- Commit when Caleb asks.
