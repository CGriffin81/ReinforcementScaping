# Agent Interaction

## Metadata

- Interaction ID: m001-related-work-rs-sdk-runebench
- Timestamp CST: 2026-10-27 19:18:20 CST (from the session transcript's message timestamp, UTC−05:00; corrected 2026-10-28, the original estimate was ~19:15:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS
- Commit: main repo: `846ca33`, the commit that adds this record, on branch `env-contract-and-combat-model`

## Full Prompt

> * https://github.com/MaxBittker/rs-sdk/
> * https://maxbittker.github.io/runebench/
>
>
> Check these repos to see what will be useful for our project here. If we end up using them, add them to our list of resources.

## Response Summary

- **rs-sdk** (MIT; created 2026-01; actively pushed):
  - What it is: a TypeScript automation SDK, agent docs and an MCP
    `execute_code` tool for a modified fork of the **LostCity 2004scape**
    engine. Its server changes: faster XP curve, infinite run energy, no random
    events, configurable tick rate (`NODE_TICKRATE`, `::speed`). Agents act
    through a browser or headless client and a gateway, not directly on the
    server.
  - What it offers: high-level `bot.*` actions that observe their effects and
    return typed results (`success` / `reason`); mechanics notes in
    `learnings/` (2004-specific); wiki generators.
- **RuneBench** (repo `MaxBittker/runebench`; results site):
  - What it is: LLM coding agents play through rs-sdk at 8× speed with a 25× XP
    multiplier, getting wiki-derived markdown notes and an MCP tool server.
  - Tasks: 16 single-skill XP tasks (15 / 30 min), scored on peak XP/min in any
    15-second window, and gold-accumulation tasks from four starting saves
    (vanilla, smith + alch, fish, fletch + alch).
  - The README claims MIT, but there is no LICENSE file.
- **Assessment:** neither works as our environment. They are a different game
  version and engine, with modified XP, so their numbers can't be compared with
  ours. Both are useful as:
  - related work: RuneBench is the closest prior work on agents in RuneScape,
    and measures the same skill and wealth objectives
  - design references: rs-sdk's effect-verifying actions and typed results for
    our option executor; its MCP interface and the wiki-knowledge approach for
    the E7 LLM planner; RuneBench's fixed-start gold tasks as a model for
    robustness checks
- Because the project uses them in those ways, created **`docs/resources.md`**.
  It holds the proposal's references [1]–[15] with their numbering kept, plus:
  - [16] the Weird Gloop exchange API and [17] the 2009Scape About page, both
    already used for the 2009 prices
  - [18] RuneBench, [19] rs-sdk, and [20] LostCity (context only)
  - a "planned" list (MORL-Baselines / MO-Gymnasium, CleanRL RND, sb3-contrib)

## Documentation Changes

- Added `docs/resources.md`.
- `CLAUDE.md`: points to the resources list and says when to add to it.
- `ROADMAP.md` Appendix B: a closest-prior-work note for stretch option A.
- `docs/decision-log.md`: the related-work review and the recommendation.
- This record.

## Code Changes

None.

## Infrastructure Changes

None. Read-only GitHub API calls (`gh api`) and one web fetch of the RuneBench
results page.

## Decisions

- **Agent recommendation:** use RuneBench and rs-sdk as related work and design
  references only. They are not the environment, and their results aren't
  directly comparable. RuneBench code isn't copied because of its missing
  licence file.
- **User decision:** none yet. The prompt asked for resources to be added if
  they would be used. They are listed on the basis of the recommendation above;
  Caleb can strike them.

## Validation

- Repo facts came from the GitHub API: description, licence, languages, file
  trees, README, `sdk/API.md` headings, RuneBench `generate-tasks.ts` and
  `shared/agents.md`, and the missing RuneBench LICENSE (HTTP 404).
- The RuneBench results site was summarised by web fetch. It names neither the
  tested models nor the headline numbers; the README lists the models tested.

## Follow-Up

- When the option executor is designed, model its result type on rs-sdk's
  `ActionResult` (`success` / `reason`), mapped onto the env contract's
  `termination` values.
- If stretch option A is picked at the week-5 midpoint, review RuneBench's MCP
  harness and wiki-knowledge setup in more depth.
