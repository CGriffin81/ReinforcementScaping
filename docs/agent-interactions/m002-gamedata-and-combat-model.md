# Agent Interaction

## Metadata

- Interaction ID: m002-gamedata-and-combat-model
- Timestamp CST: 2026-10-27 ~20:35:00 CST (estimated: follows the quest-set record, written at about 20:33; this work's last edit was at 20:45)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (shield value done; first build module done and tested; data-quality findings need fixes and one decision)
- Commit: main repo: the commit that adds this record, on branch `env-contract-and-combat-model`

## Full Prompt

> Set the shield value to 0 and start building.

## Response Summary

- **Shield value → 0.**
  - `scripts/build_price_tables.py` now reads `world.ge_blocked_items` from `rl.conf`, so the server rule is the
    single source of truth. GE-blocked items get no GE term in the valuation (new source label `ge_blocked`) and
    are left off `historical_price_items`.
  - Rebuilt: only the two shield rows of `prices_v2.csv` changed (301 → 0); `ge_prices_2009.csv` is unchanged;
    the frozen database lists 6,068 items.
  - A clumsy metadata count, which opened a second database connection, was replaced with a counter. A meta
    file whose only change was its build timestamp was restored.
- **Started building: week-2 work, recorded as m002.** Before writing any code, read the server's combat code:
  - `CombatSwingHandler`: hit chance, the XP award (4 per damage; 1.33 Hitpoints)
  - `MeleeSwingHandler`, `RangeSwingHandler`, `MagicSwingHandler`: accuracy, max hit, defence; the melee and
    ranged roll is 0..max; magic rolls 0..max−1, which gives an effective max equal to the spell's base
  - `SpellType` and the modern spell registrations: all 16 levels and base XP values checked
  - `NPC.configure`: an NPC attacks with its highest of stab / slash / crush; `combat_style` and
    `protect_style` are ordinals
  - `WeightBasedTable` / `NPCDropTable`: guaranteed drops, then one weighted roll each for main, charm and
    tertiary
- **New code:**
  - `rlscape/gamedata/server.py` (+ `__init__.py`): typed loaders for items, NPCs, drop tables (expected items
    and gp per kill) and spawns; values from `prices_v2`.
  - `rlscape/combat/formulas.py`: the server formulas, each function naming its source method.
  - `rlscape/combat/rates.py`: `Fighter`, `Plan`, `Rates`, `combat_rates()` (kills, XP by skill, gp, damage
    taken mean and variance) and `Rates.survivable()` (the decided danger filter). Its simplifications are
    listed in the module docstring.
  - Tests: `tests/test_combat_formulas.py` (hand-computed values, including known 99 Strength max hits) and
    `tests/test_gamedata.py` (real configs). 11 passed.
- **Ran the model on real data** for a fresh character. All 2,120 spawned NPC types were rated in 26 ms. That
  exposed four issues (decision log, 2026-10-27 evening):
  1. 911 spawned NPC types have placeholder stats (1/1/1, 10 HP, no bonuses), including real monsters
  2. non-attackable NPCs are in the pool
  3. gp/hr ignores inventory capacity and bank trips
  4. the decided danger filter passes only 7 NPC types for a fresh character with starter food

## Documentation Changes

- `docs/decision-log.md`: the shield decision, the build entry, and the four findings.
- `ROADMAP.md`: week 2 marked as started on 2026-10-27, with what's done and what's next.
- This record.

## Code Changes

- `scripts/build_price_tables.py`: reads `ge_blocked_items` from `rl.conf`; the GE-blocked valuation rule; the
  metadata counter fix.
- `rlscape/gamedata/__init__.py`, `rlscape/gamedata/server.py` (new).
- `rlscape/combat/__init__.py`, `rlscape/combat/formulas.py`, `rlscape/combat/rates.py` (new).
- `tests/test_combat_formulas.py`, `tests/test_gamedata.py` (new).

Data (rebuilt): `data/prices_v2.csv` (2 rows), `data/prices_v2.meta.json`,
`data/grandexchange_2009_frozen.db`, `data/grandexchange_2009_frozen.meta.json`.

## Infrastructure Changes

None. Read-only use of the server source and configs; no server runs.

## Decisions

- **User decisions (implemented):** the anti-dragon shield is valued at 0; start building.
- **Agent choices (reversible):**
  - read the blocked-items list from `rl.conf`
  - the rate-model simplifications in the `rates.py` docstring: time to kill = HP / damage per tick; a constant
    6-tick overhead per kill; a melee weapon attacks with its best bonus type
- **Pending, for Caleb:** the danger filter's semantics (finding 4).
- **Agent plan:**
  - **Finding 1:** export cache NPC definitions through the bridge (combat level, "Attack" option), and exclude
    placeholder-stat NPCs whose cache combat level disagrees.
  - **Finding 2:** use the same export to keep only attackable NPCs.
  - **Finding 3:** add the loot-slot and bank-trip cycle to candidate gp/hr.

## Validation

- `uv run pytest -q tests/test_combat_formulas.py tests/test_gamedata.py`: 11 passed in 0.18 s.
- Real-data run (`combat_rates` over every spawned NPC type with the starter sword and shield): 26 ms; the
  outputs quoted in the decision log.
- The spell table was compared line by line against the server's spell registrations; all 16 match.

## Follow-Up

- Caleb decides the danger-filter semantics.
- Next module:
  - a bridge `npc_definitions` export (cache combat level, attack option)
  - pool cleaning
  - inventory-aware gp/hr (needs bank distances from the region graph)
  - the gear check for special damage (dragonfire)
  - then the simulator state and options
