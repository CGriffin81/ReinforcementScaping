# Agent Interaction

## Metadata

- Interaction ID: m001-combat-decisions-and-quests
- Timestamp CST: 2026-10-27 ~20:00:00 CST (estimated: follows the combat-context record, written at about 19:58; this work's last edit was at 20:14)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (combat A–D recorded and designed; whether quests are agent options awaits Caleb)
- Commit: main repo: the commit that adds this record, on branch `env-contract-and-combat-model`

## Full Prompt

> A. Offer the 3 best xp/hr and the 3 best gp/hr for all three combat styles.
> B. Your recommendation here is good, but I would add a gear check for special damage types, like dragonfire.
> C. The list should be slightly context-driven. If an agent is on a quest, it should be able to complete that quest. If the agent has access to items that unlock areas, the enemies in those areas should be available to choose from.
> D. Let the agents make looting decisions.

## Response Summary

- **Checked quest support** before designing decision C, since "on a quest … complete that quest" depends on it.
  The server enum lists 150 quests. About 44 Kotlin `Quest` subclasses are implemented, among them Cook's
  Assistant, Doric's Quest, Witch's Potion, Waterfall Quest, Tree Gnome Village, Fight Arena, Dragon Slayer,
  Lost City, Druidic Ritual and Nature Spirit. There are also about 26 older Java ones. Read the actual XP
  rewards from the quest code:
  - Waterfall Quest: 13,750 Attack + 13,750 Strength
  - Fight Arena: 12,175 Attack + 2,175 Thieving
  - Tree Gnome Village: 11,450 Attack
  - Doric's Quest: 1,300 Mining
  - Witch's Potion: 325 Magic
  - Cook's Assistant: 300 Cooking
- **Option catalog v0.3, §4 rewritten as decided:**
  - **A:** 3 + 3 slots for each of melee, ranged and magic; melee × 3 training styles.
  - **B:** the danger filter plus a special-damage gear-check table: dragonfire needs an anti-dragon shield;
    style-blocking monsters (`protect_style`) are ruled out for that class; poison goes into the damage
    estimate; Slayer-gear monsters stay locked. The anti-dragon shield was added to the buy options.
  - **C:** a context-driven pool through an access table (area → item / quest / level requirement), re-checked
    every decision. Minigame and instanced monsters stay out.
  - **D:** a proposed persistent loot mode, set by 4 actions (all / valuable / vocabulary / none), starting at
    "valuable". The alternatives (loot variants of each combat action, or a decision per kill) are recorded.
- **New §10: are quests agent options?** Options:
  - (a) none
  - (b) a curated set, each quest a macro-option
  - (c) all of them (infeasible by Nov 30)

  Recommendation: (b) with 4 low-risk quests (Waterfall Quest, Doric's Quest, Witch's Potion, Cook's
  Assistant).
- **Self-correction before presenting:** the first draft recommended Fight Arena. It was replaced, because Fight
  Arena and Tree Gnome Village both end in fights against level-100+ monsters, usually won by safespotting.
- **Env contract v0.3:** the observation gained loot mode, access flags and (conditionally) quest stages;
  question 6 (combat) was added as decided; the open item is now quests.

## Documentation Changes

- `docs/option-catalog.md` → v0.3: §4 rewritten; §10 replaced with the quest question; anti-dragon shield
  added to buying; the size table gained loot mode (about 430 actions, plus one per quest).
- `docs/env-contract.md` → v0.3: observation rows added; decisions updated.
- `docs/decision-log.md`: combat decisions A–D and the quest question.
- This record.

## Code Changes

None.

## Infrastructure Changes

None. Read-only searches of the server source.

## Decisions

- **User decisions:**
  - A: 3 + 3 per class
  - B: the danger filter, plus a special-damage gear check
  - C: a context-driven pool (items, quest progress)
  - D: the agent makes looting decisions
- **Agent proposals (pending):**
  - the loot-mode design for D
  - the access-table mechanism for C
  - quests as a curated set of 4 macro-options

## Validation

- Quest implementation and rewards were read from the server source (`content/data/Quests.kt`, the quest
  classes' `rewardXP` / `addExperience` calls).
- The special-damage table rests on config fields seen in `npc_configs.json` (`protect_style` on 19 NPCs,
  `poisonous` / `poison_amount`) and on dragon combat handlers. The handler-level details are to be confirmed
  when the combat-rate model is built.

## Follow-Up

- Caleb decides whether quests are agent options, and which.
- Then: build the enemy pool, the access table and the combat-rate model; fix the item vocabulary; start
  simulator v0.
