# Agent Interaction

## Metadata

- Interaction ID: m001-env-contract-and-option-catalog
- Timestamp CST: 2026-10-27 ~19:06:00 CST (estimated: follows the PR #1 update at about 19:05; the memory and decision-log edits at the end of this work happened around 19:13)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (both drafts written; they await Caleb's decisions, one of which is blocking)
- Commit: main repo: the commit that adds this record, on branch `env-contract-and-combat-model`

## Full Prompt

> We're going to keep the old roadmap and try to make up for the lost time.

Context: this answers the agent's offer, at the end of the earlier PR work, to
re-baseline the remaining five weeks. That offer would have dropped E7 and
made E4 optional.

## Response Summary

- Recorded the decision in the decision log and in Claude's memory (outside
  the repo): keep the original week dates and don't propose re-baselining
  again.
- Started the next critical-path items, the two remaining week-1 deliverables,
  as **Proposed** drafts.
- **`docs/env-contract.md` v0** covers:
  - time and episodes (0.6 s ticks; a 20-hour horizon truncated, not terminal;
    γ per game-hour converted to ticks)
  - the shared Gymnasium interface (`action_masks`, `option_catalog`, reward
    weights in `reset`)
  - the observation layout (time, 13 in-scope skills, total level, HP, wealth,
    owned-item counts, equipment and tool tiers, region, mask, optional
    preference)
  - the reward (fractional total level; net worth / 100k, valued with
    `prices_v2`)
  - the `info` fields
  - backend obligations and a sim-vs-server parity test
  - five decisions for Caleb
- **`docs/option-catalog.md` v0** has 11 regions and 53 actions:
  - 30 activity options: woodcutting, mining, smelting, smithing, fishing,
    cooking, firemaking, prayer, thieving, and four melee targets × three
    training styles
  - 23 economy options: two sell options, and buy options for axes,
    pickaxes, scimitars, armour sets, fishing gear, food and a hammer
  - a 36-item observation vocabulary, with a bundled-bot executor reference
    and "verify" flags for each option
- **Grounding:** locations and targets came from the bundled bots
  (`DraynorWillows`, `CowKiller`, `ChickenKiller`, `LobsterCatcher`,
  `VarrockSmither`, `CoalMiner`, `DraynorFisher`, `ManThiever`,
  `GenericSlayerBot`) and from `npc_spawns.json`. Hill giants are around
  (3118, 9845) in the Edgeville Dungeon; Al-Kharid warriors around (3284, 3172).
- **Finding:** the frozen GE's bot stock (145 items) holds almost no gear,
  tools or food: 3 bronze axes, 45 feathers, 1 steel full helm, 2 battleaxes.
  GE buy options would rarely fill on the real server. Raised as the catalog's
  blocking decision, with options (a) a frozen-price seller, (b) shops only,
  (c) both, and a recommendation of (a).
- **Self-caught gap:** the starter kit has no hammer, but smithing needs one,
  so `buy_hammer` was added (53 actions).

## Documentation Changes

- Added `docs/env-contract.md` (Proposed).
- Added `docs/option-catalog.md` (Proposed).
- `docs/decision-log.md`: the schedule decision, and the two drafts listed as
  awaiting Caleb.
- `ROADMAP.md`: the two week-1 items marked drafted / Proposed.
- This record.

## Code Changes

None.

## Infrastructure Changes

None. Only read-only queries against the frozen GE database and the server's
config files.

## Decisions

- **User decision:** keep the original roadmap dates and make up the lost
  time. The agent's re-baselining proposal is not accepted.
- **Agent recommendations (pending; listed in each doc):**
  - env contract: banking inside loops; a fixed 15-minute option duration (5
    and 45 for E5); no Magic training in v0; melee only; two sell options
  - option catalog: a frozen-price seller (blocking); the option list itself;
    a hill-giant fallback to moss giants

## Validation

- Location and target claims were checked against the bundled bot scripts and
  `data/configs/npc_spawns.json`. Items still marked "verify" (the Lumbridge
  Swamp mine, the brass-key door, the Al Kharid toll) are unconfirmed and are
  to be checked on the server during calibration.
- Bot-stock contents came from a direct read-only query of
  `data/grandexchange_2009_frozen.db`.
- The docs are design drafts, so nothing was executed.

## Follow-Up

- Caleb decides the env-contract and option-catalog questions. Gear sourcing
  blocks the economy part of sim v0.
- Then week 2: sim v0 (`rlscape/sim`), `SimEnv`, baselines, and the
  evaluation harness.
- Branching: these drafts sit in the working tree on the PR #1 branch. They
  should go in their own PR, either after PR #1 merges or stacked on it.
