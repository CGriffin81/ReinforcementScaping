# Agent Interaction

## Metadata

- Interaction ID: m002-pool-cleaning-and-retreat-filter
- Timestamp CST: 2026-10-27 21:06:02 CST (from the session transcript's message timestamp, UTC−05:00; corrected 2026-10-28, the original estimate was ~21:05:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the planned fixes and the retreat-aware filter are implemented and tested; the access table is identified as the next blocker)
- Commit: fork `1223914` (branch `rl`); main repo: `846ca33`, the commit that adds this record, on branch `env-contract-and-combat-model`

## Full Prompt

> Apply the planned fixes. Add the retreat-aware filter.

Context: the planned fixes were listed at the end of `m002-gamedata-and-combat-model`:
- export cache NPC definitions through the bridge, and use them to keep only attackable NPCs and drop those with
  placeholder stats
- make gp/hr inventory-aware (bank trips)
- add the dragonfire gear check

"The retreat-aware filter" is option (b) of the danger-filter question in that interaction.

## Response Summary

- A new session had started. Checked first: nothing had been committed since 19:05, and the "changed on disk"
  notices were from the session restart. The fork's uncommitted seller and blocked-items changes were intact.
- **Read the server code before building:**
  - `NPCDefinition`: `forId`, `getCombatLevel`, `hasAction("attack")`; `Cache.getNPCDefinitionsSize`
  - `ItemDefinition.isStackable`
  - the dragonfire NPC lists in `ChromaticDragonNPC`, `MetalDragonNPC`, `KingBlackDragonNPC` and `ElvargNPC` (742)
  - `ContentAPI.hasDragonfireShieldProtection`: which shields protect against dragonfire and wyvern fire
- **Fork:** the bridge's `item_definitions` gained `stackable`, and a new `npc_definitions` returns every named cache
  NPC definition. Built, the server started, and both were exported: `data/item_definitions.csv` (only the new
  column added; 3,755 stackable) and the new `data/npc_definitions.csv` (7,887 named, 2,717 attackable).
- **Calibrated the stat-believability rule on the data:**
  - among spawned NPCs with an "Attack" option (1,184), only 11 carry the placeholder signature
  - the rule (stats imply ≥ half the cache combat level − 2) flags 124
  - it leaves level-2 NPCs (Man, Woman) alone, since level-1 stats are plausible for them
- **Python:**
  - `rlscape/combat/candidates.py` (new):
    - the enemy pool: attackable, believable, unkillable dummies 4474 / 7891 excluded
    - one site per map region with its nearest bank (curated `data/banks.csv`)
    - travel estimates
    - loot modes, and loot gp and slots per kill
    - the inventory cycle and travel folded into the rates
    - the dragonfire and wyvern gear check
    - selection: 3 best by XP/hr + 3 best by gp/hr per class, duplicate names merged
  - `rlscape/combat/rates.py`: the retreat-aware filter `passes_retreat_filter`; per-kill damage moments
  - `rlscape/gamedata`: loaders for NPC definitions, stackable items (summoning charms added; untradeable, so
    missing from the export) and banks
  - client `npc_definitions()`; `scripts/export_npc_definitions.py`; the stackable column in
    `scripts/export_item_definitions.py`
- **Found and fixed by testing and real-data runs:**
  1. summoning charms counted as inventory slots, because the export only covers tradeable items
  2. training dummies in the pool
  3. a monster's site was fixed regardless of the character's location (cows near Yanille, from Lumbridge)
  4. my own test inputs used 9,000 ticks for 15 game-minutes instead of 1,500
- **Finding, reported as the next blocker:** a fresh character's top gp/hr slots are monsters in gated areas: the
  Stronghold of Player Safety, Morytania (Priest in Peril), Contact!, and Zanaris spawns. The drop values themselves
  check out against the server's tables. The access table (option catalog §4.C) has to come next.

## Documentation Changes

- `docs/option-catalog.md`:
  - §4.B rewritten as the retreat-aware filter, with a worked example; poison marked as not implemented
  - §4.C pool cleaning as implemented, and the access table as the next step, with evidence
  - a new "Inventory and travel in the rates" section
- `docs/env-contract.md`: §8 risk and inventory rows; decision 6 now names the retreat-aware filter.
- `docs/decision-log.md`: the decisions, the build, and the findings.
- This record.

## Code Changes

Fork, branch `rl` (uncommitted): `Server/src/main/content/rl/RLCommands.kt` (`stackable`; `npc_definitions`; imports).

Main repo (uncommitted):
- `rlscape/combat/candidates.py` (new); `rlscape/combat/rates.py`; `rlscape/gamedata/server.py`;
  `rlscape/gamedata/__init__.py`; `rlscape/bridge/client.py`
- `scripts/export_npc_definitions.py` (new); `scripts/export_item_definitions.py`
- `tests/test_candidates.py` (new)
- Data: `data/npc_definitions.csv` (new), `data/banks.csv` (new, curated), `data/item_definitions.csv` (`stackable`
  column)

## Infrastructure Changes

- Rebuilt the fork, reinstalled the clean frozen GE, and ran the server once for the two exports. The server was
  stopped afterwards.

## Decisions

- **User decisions (implemented):** apply the planned fixes; the retreat-aware danger filter.
- **Agent choices (reversible, constants to calibrate):**
  - the believability threshold (≥ half the cache level − 2)
  - two escape attacks
  - eat below 50% HP
  - 1.5 tiles per tick × a 1.3 detour factor; 12 ticks per level change; 8 ticks of banking
  - the 6,400-tile dungeon offset
  - one site per map region
  - charms as stackable
  - a curated bank list
- **Next (agent plan):** the access table, then Slayer locks and quest monsters, then caching candidates for the
  simulator.

## Validation

- Fork build exit 0. Exports: 7,324 items (0 core-column changes versus before), 7,887 NPC definitions.
- `uv run pytest -q`: 18 passed, 13 skipped (the live server tests, with the server stopped). That includes 7
  candidate tests:
  - the retreat filter's burst and kill-budget arithmetic
  - travel, including plane and underground changes
  - loot rules on the real cow table
  - pool cleaning: Master Farmer, the placeholder ice troll and the dummies are all excluded
  - green dragons need the anti-dragon shield
  - a fresh character passes cows
- Real-data runs:
  - the pool built in about 160 ms
  - ranking took about 60–100 ms
  - fresh-character XP slots were Rat / Man / Ram, and cows from Lumbridge chose Lumbridge's site

## Follow-Up

- The access table (key-, quest- and training-gated areas: the Stronghold of Player Safety, Morytania, Zanaris,
  Contact!, the Mage Arena, …), Slayer requirement locks, and quest monsters while a quest is underway.
- The poison damage estimate.
- Calibrate travel, banking, the escape and overhead constants, and verify the bank tiles on the server.
- Cache candidates by character state for the simulator.
