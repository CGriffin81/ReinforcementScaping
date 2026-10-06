# AI Interaction Logging Requirements

Adapted from the Promethean project's `ai_log_requirements.md` steering doc
(`D:\Promethean\.kiro\steering\ai_log_requirements.md`), which is the AI-assisted
code policy this project follows. The Promethean-specific sections (Pulumi
deployment records, capstone paper format) are dropped; everything else applies
as written there.

## Purpose

Materially significant AI-agent interactions must be documented, so the record
shows what was requested, what the agent produced, what changed, which agent
and model did the work, when, and what was decided. The code is written by
Claude Code and reviewed and run by Caleb; these records are how that split is
made auditable.

## When a record is required

Any interaction that materially affects the project:

- research-question, formulation, or experiment-design decisions
- architecture decisions (env contract, bridge protocol, sim design)
- code generation or modification (Python or server-side Kotlin)
- infrastructure changes (installed tools, containers, server config)
- significant debugging or refactoring
- test strategy changes
- experiment runs whose results enter the report

Simple questions with no project impact may be skipped. When uncertain,
document it.

## Location and naming

    docs/agent-interactions/m{NNN}-{short-description}.md

`NNN` is three digits, zero-padded. For this project:

- `m000`: proposal, roadmap, and planning
- `m001` … `m008`: work belonging to ROADMAP.md week 1 … week 8

Multiple records per milestone are fine when the work is distinct.

## Record format

    # Agent Interaction

    ## Metadata

    - Interaction ID:
    - Timestamp CST:
    - Agent:
    - Model:
    - Status:
    - Commit:

    ## Full Prompt
    ## Response Summary
    ## Documentation Changes
    ## Code Changes
    ## Infrastructure Changes
    ## Decisions
    ## Validation
    ## Follow-Up

Write "None" for an empty section.

## Field rules

- **Full Prompt:** the complete prompt, verbatim, never a summary. Include
  referenced files by path, user decisions, and relevant command output.
- **Timestamp:** `YYYY-MM-DD HH:MM:SS CST`. This machine runs on US Central time,
  so during daylight saving the clock is UTC−05:00; it is still labeled CST,
  following the Promethean convention. If the exact time isn't instrumented,
  give an estimate marked `~` and `(estimated)`, and say what it is based on.
- **Model:** the model the environment actually reports (for example
  `Claude Opus 5.5`). Otherwise `Unknown`. Never infer it.
- **Status:** one of `SUCCESS`, `PARTIAL`, `BLOCKED`, `FAILED`, `CANCELLED`,
  `SUPERSEDED`.
- **Commit:** the associated commit SHA, or `None`. Never fabricate one.
- **Changes:** list documentation, code, and infrastructure changes separately,
  with paths.

## Decisions

Keep these two apart:

- **Agent Recommendation:** what Claude proposed.
- **User Decision:** what Caleb accepted, changed, or rejected.

A recommendation is not a project requirement until Caleb accepts it. Track the
implementation state as Proposed → Approved → Implemented → Validated. Never
describe a recommendation as implemented, or untested code as validated.

## Secrets

Never store secrets in any record: passwords, API keys, tokens, private keys,
credentials. Replace them with `[REDACTED]`.

## Failed and superseded work

Document materially significant failures: what was attempted, why it failed,
the error, and the recovery. Never delete a record because a later decision
replaced it. Mark it `SUPERSEDED` and point to the newer record.

## Definition of done

A record is complete when it has the full prompt (with secrets redacted), the
agent, the model, a CST timestamp, a response summary, the doc/code/infra
changes, decisions, validation, follow-up, status, and commit, and none of its
metadata is fabricated.
