# Agent Interaction

## Metadata

- Interaction ID: m002-access-table
- Timestamp CST: 2026-10-28, before 13:40 CDT (estimated: the shell clock read 13:40:55 CDT near the end of the work;
  the start wasn't instrumented)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the access table is implemented, tested and wired into candidate selection; gaps are listed for
  calibration)
- Commit: main repo: the commit that adds this record, on branch `env-contract-and-combat-model` (the Slayer fix that followed is fork `d49172e`)

## Full Prompt

> Let's work on the access table.

Asked during the work (AskUserQuestion), with Caleb's answer:

> Should Wilderness monsters be in the enemy pool? [...] → "Include it (Recommended)"

## Response Summary

- **Scoped by data, not memory.** A sweep ran the candidate selection with every area open, over:
  - levels 1–99 with matching gear for melee, ranged and magic
  - 18 hub towns
  - two loot modes

  It collected every monster that reached a top-10 slot: 573 monster sites in 202 map regions.
- **Checked the surfaced sites against the server code:**
  - `MapArea` borders (`MorytaniaArea`, `SmokeDungeon`)
  - quest checks in the ship, ferry, door and dialogue handlers:
    - `ShipCharter`, `RellekkaListeners`, `MainGatesListener`, `MournerHQDoors`, `SophanemPlugin`
    - `TaverleyDungeonListeners`, `SanibochDialogue`, `JarvaldDialogue`, `RangingGuildPlugin`, `KolodionDialogue`
    - the Player Safety listener
  - the quest folders, for quest-only NPCs
- **Asked Caleb one scope question** (the Wilderness). Everything else followed decisions already made: §4.C's
  context-driven pool, quest monsters while a quest is underway, minigames out, Slayer as requirement checks only.
- **Built:**
  - the access table: `data/access_areas.csv`, 55 rules, each citing its server check or saying there isn't one
  - `rlscape/combat/access.py`: the requirement grammar, `Progress`, `unlocked_rules` (the observation's access flags)
    and `can_reach`
  - the Slayer-level and quest-name loaders, parsing `Tasks.java` and `Quests.kt`
  - the integration into `candidates.evaluate`
- **Re-ran the sweep with the real 3 + 3 slots** and fixed what still surfaced:
  - the Morytania strip the server's borders miss
  - Mighty banshees
  - the Ranging Guild and Mage Arena
  - Trollheim and the Trollweiss caves
  - Keep Le Faye and the Phoenix hideout
  - the Lumbridge Swamp Caves
  - Entrana
- **Findings, reported:**
  - the server doesn't enforce Slayer levels: there's a message but no `return false`
  - many 2009 gates have no server check
  - the Morytania borders stop short of the River Salve
  - the remaining gaps: entry fees not in the rates, the separate maps at y ≈ 4,000–6,400, Colonel Radick's
    placeholder stats, light sources

## Documentation Changes

- `docs/option-catalog.md` v0.6: §4.C rewritten. It now covers:
  - the access table as implemented
  - Slayer levels and where the rules come from
  - the sweep method and the result
  - the Wilderness decision
  - the known gaps
- `docs/env-contract.md` v0.6: §3's access row (A = 55, `unlocked_rules`); §9 decision 9 (the Wilderness).
- `docs/decision-log.md`: the decisions, the build, the sweep method, the findings.
- `ROADMAP.md`: the week-2 status line.
- This record.

## Code Changes

- `rlscape/combat/access.py` (new); `rlscape/combat/candidates.py` (`Character.progress`, access checks in `evaluate`,
  docstring).
- `rlscape/gamedata/server.py` (`slayer_levels`, `quest_names`, `SERVER_CONTENT` / `SLAYER_TASKS` / `QUESTS`);
  `rlscape/gamedata/__init__.py`.
- `tests/test_access.py` (new, 7 tests).
- Data: `data/access_areas.csv` (new, curated).
- Throwaway (scratchpad, not in the repo): `sweep_candidates.py`, the sweep script.

## Infrastructure Changes

- None. The server wasn't run; everything was read from the fork's source and configs.

## Decisions

- **User decisions:**
  - work on the access table
  - the Wilderness is in (Claude's recommendation, accepted)
- **Agent choices (reversible):**
  - curated rows over computed reachability: there's no map collision data, and the gates are scattered across
    handlers
  - the 2009 rule applies even where the server doesn't enforce it
  - quest-only NPCs only while `underway`
  - Elvarg is `never`, since she's fought inside the Dragon Slayer option
  - Entrana is `never`, since no gear is allowed there
  - the Morytania strip rows
  - Mighty banshees get Slayer 15
  - every row marked "2009 knowledge" or "to verify"
- **For Caleb (not done):** a one-line fork fix so the server enforces Slayer levels, which would match 2009.

## Validation

- `uv run pytest -q`: 25 passed, 13 skipped (live server tests; server stopped). The new access tests cover:
  - the grammar
  - every quest name and NPC name in the table checked against the server data
  - all 93 Slayer tasks parsed
  - Morytania, including the strip
  - quest monsters only while underway
  - a fresh character's slots
- The sweep: the gated monsters that had surfaced dropped out, and the new picks are open-world monsters.
- Fresh character at Lumbridge (melee), gp/hr slots:
  - before: Cockroach drones about 46,200, undead chickens about 17,000, undead cows about 10,600
  - after: cow calves about 7,560, bats about 6,700, cows about 5,880
  - the XP slots stay Rat, Man, Ram

## Follow-Up

- Calibration on the server: walk to the "to verify" rows; look for areas missing from the table (the Ardougne zoo,
  the Yanille Agility Dungeon's sections, the Mountain Camp).
- Charge entry fees in the rates.
- Give the separate maps at y ≈ 4,000–6,400 proper rows and travel links.
- Fix Colonel Radick slipping past the believability rule.
- Decide on the Slayer fork fix.
- Next build step: the simulator state and options.
