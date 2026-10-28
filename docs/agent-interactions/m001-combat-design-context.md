# Agent Interaction

## Metadata

- Interaction ID: m001-combat-design-context
- Timestamp CST: 2026-10-27 ~19:53:00 CST (estimated: follows the env-contract decisions record, written at about 19:51; this work's last edit was at 19:58)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (two decisions recorded; the combat design is explained and awaits Caleb)
- Commit: main repo: the commit that adds this record, on branch `env-contract-and-combat-model`

## Full Prompt

> 5. All of that item in the inventory is acceptable.
>
> Separate buy actions for GE v shops
> Give me more context about the combat design question.

## Response Summary

- Recorded two decisions in both docs and in the decision log: selling per item (all of the item in the
  inventory), and separate buy actions for the GE and for shops. Env contract question 5 is now decided.
- **More context on the combat design.** Pulled real stats (HP, attack / strength / defence, attack speed,
  aggressiveness) and drops worth ≥ 50 gp at `prices_v2` from the server's `npc_configs.json` and
  `drop_tables.json`. The monsters: chicken, cow, goblin, man, Al-Kharid warrior, hill giant, moss giant, green
  dragon. Combat levels were approximated with the standard melee formula, since the configs have no
  combat-level field.
- Replaced option catalog §10 with a full explanation. It starts with why a mechanism is needed at all (a fixed
  number of policy outputs versus hundreds of monsters), then four parts. Each has the problem, a worked example
  from the table, alternatives, and a recommendation:
  - **A. Slots:** 3 best by XP/hr + 3 best by gp/hr per class. Alternatives: one formula-chosen action per
    class (removes the choice RQ2 wants to see), more slots, a third ranking.
  - **B. Danger filter:** expected damage + 2σ over *D* minutes must not exceed HP plus food healing; eat
    below 50% HP; retreat when out of food. Food then becomes an investment that unlocks better targets (H1).
    Alternatives: no filter, a combat-level rule, risk shown but not filtered.
  - **C. Enemy pool:** built from server data, excluding quest, minigame and instanced monsters, with Slayer
    locks and a blocklist built up during calibration. Alternatives: a hand-picked whitelist (reverses "any
    enemy"), no exclusions.
  - **D. Loot rule (new):** a consequence of "no auto-banking" that the first draft didn't surface. Loot
    coins, runes, arrows, vocabulary items, and anything ≥ 100 gp. Alternatives: loot everything, or make
    looting an agent choice (triples the combat actions).
- XP/hr and gp/hr in the examples are reasoned qualitatively from the real stats and drop values. No rates were
  computed: the combat-rate model isn't built yet.

## Documentation Changes

- `docs/option-catalog.md`: status line updated; §7 and §8 record the two decisions; §10 replaced with the
  combat-design context.
- `docs/env-contract.md`: status line updated; question 5 moved to decided; the open item points to the
  combat design.
- `docs/decision-log.md`: both decisions and the pending combat design.
- This record.

## Code Changes

None.

## Infrastructure Changes

None. Read-only parsing of the server's NPC and drop configs.

## Decisions

- **User decisions:** selling per item, all of the item in the inventory; separate buy actions for the GE and
  for shops. Both take the agent's recommendations.
- **Agent recommendations (pending):** combat parts A–D as summarised in catalog §10, "In short".

## Validation

- Monster stats and drops were read directly from the server configs. Drop values come from
  `data/prices_v2.csv`.
- The combat levels shown are approximations. Rates are qualitative until the combat-rate model exists.

## Follow-Up

- Caleb decides combat parts A–D.
- Then build the enemy pool and combat-rate model, fix the item vocabulary, and start simulator v0.
