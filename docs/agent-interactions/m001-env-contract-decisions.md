# Agent Interaction

## Metadata

- Interaction ID: m001-env-contract-decisions
- Timestamp CST: 2026-10-27 ~19:40:00 CST (estimated: follows the frozen-seller work, whose last edit was at 19:37; this work's final edits were at about 19:51)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (decisions 1–4 recorded and reflected in both docs; question 5 and the combat-candidate design await Caleb)
- Commit: main repo: the commit that adds this record, on branch `env-contract-and-combat-model`

## Full Prompt

> 1. Don't include banking inside the activities. There may be situations where it is more beneficial to drop the items collected than to run back to a bank.
> 2. I accept your recommendation for this item.
> 3. Keep it in. There may be times where it is more beneficial to alch items than bank them.
> 4. Keep range and mage as options. I also want the bots to make reasonable decisions about fighting any enemy in the game, based on their theoretical gp and xp per hour.
> 5. I don't understand the issue at hand here. By default, selling should be by item in intervals of 1, 10, x, or all, if I remember correctly. Why would we change that?

## Response Summary

- **Checked feasibility** of "any enemy … based on theoretical gp and xp per hour" against the server data
  first. `npc_configs.json` has 8,033 NPCs, 4,044 of them with combat stats (hitpoints, attack, strength,
  defence and ranged levels, often attack speed and bonuses). `drop_tables.json` has 444 tables, each
  covering several NPC ids. Spawns are in `npc_spawns.json`. That's enough to rate every reachable monster.
- **Rewrote `docs/env-contract.md` as v0.2:**
  - activities end at the first of *D*, a full inventory, inputs exhausted, out of food or ammunition, or
    death; banking is never automatic
  - the observation splits inventory (with free slots) from bank, adds prayer, and adds combat-candidate
    features
  - in-scope skills now include Ranged, Magic and Slayer (requirement checks only)
  - new termination reasons: `inventory_full`, `inputs_exhausted`, `out_of_ammo`
  - a combat-rate model section (§8)
  - questions 1–4 recorded as decided
- **Rewrote `docs/option-catalog.md` as v0.2:**
  - gathering (11) and processing from the inventory (9)
  - **combat candidate slots** (30): the enemy pool comes from server data; each decision, the 3 best by
    XP/hr and the 3 best by gp/hr per class, after a food-versus-expected-damage filter; melee × 3 styles,
    ranged, magic
  - explicit inventory management: deposit, withdraw per processing activity, drop per item
  - high and low alchemy per item
  - selling per item at the GE or a general store
  - buying per source, now including ranged and magic supplies
  - an item vocabulary of about 60 plus a "misc" bucket
  - a size estimate of about 425 actions, with about 30–80 valid at once
- **Question 5:** answered in chat and in the catalog. The category idea is dropped. The only open point is
  quantities: 1 / 10 / X / all is how the game's interface works, and nothing stops it, but each quantity is
  another policy output (about 900 actions versus about 425). With frozen prices and explicit banking, "all of
  item X in the inventory" loses no control. "X" can't be a single discrete action. Recommendation: "all in the
  inventory".
- **Scope note** (not a re-plan): decisions per episode rise to about 250–400 and actions to about 425.
  Logged as a training-cost risk to watch in the week-3 sanity runs.

## Documentation Changes

- `docs/env-contract.md`: rewritten as v0.2.
- `docs/option-catalog.md`: rewritten as v0.2. The regions and shop tables were kept from v0.
- `docs/decision-log.md`: the four user decisions, the follow-on agent proposals, and the scope note.
- `ROADMAP.md`: the week-1 lines for both docs.
- This record.

## Code Changes

None.

## Infrastructure Changes

None. Read-only parsing of the server's NPC and drop configs.

## Decisions

- **User decisions:**
  1. no banking inside activities
  2. *D* = 15 minutes (5 and 45 for E5)
  3. Magic and alchemy are in
  4. Ranged and Magic combat are in, and any enemy may be fought, chosen on theoretical gp/hr and XP/hr

  Decisions 1, 3 and 4 override the agent's earlier recommendations.
- **Agent proposals (pending):**
  - combat candidate slots (structure, "reasonable" filter, pool exclusions)
  - explicit bank / withdraw / drop actions
  - an item vocabulary plus misc
  - selling as "all of the item in the inventory"
  - separate buy actions per source

## Validation

- NPC and drop-table coverage counted directly from the server's JSON configs.
- Action-count estimates are arithmetic over the catalog's families with *V* ≈ 60. They will be exact once *V*
  is fixed from the enemy pool's drop values.
- A first attempt to write the catalog through a shell heredoc failed on quoting before writing anything; the
  file was then written with the file tool.

## Follow-Up

- Caleb decides question 5 (selling quantity), the per-source buy actions, and the candidate-slot design.
- Then build the enemy pool and combat-rate model, which feeds the simulator and the candidate features, and
  fix *V* from drop values.
