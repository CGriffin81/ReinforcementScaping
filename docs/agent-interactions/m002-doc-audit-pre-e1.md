# Agent Interaction

## Metadata

- Interaction ID: m002-doc-audit-pre-e1
- Timestamp CST: 2026-11-09 09:22:02 CST (the prompt), and its repeat at 09:37:12 CST, from the session transcript's
  timestamps (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (audited; the mechanical fixes made; OQ-52 to OQ-55 for Caleb)
- Commit: None (uncommitted)

## Full Prompt

> Audit the documentation for lagging entries. Is there anything else we need to do before moving into Experiment 1?

The first answer came back empty ("No response requested."), and the Claude Code process then restarted. Caleb
followed with:

> Try again

## Response Summary

- **Audited:**
  - `CLAUDE.md` and `ROADMAP.md`;
  - the env contract and the option catalog;
  - the open-questions log and the post-project gaps;
  - `docs/resources.md`;
  - the scripted guide and the sim v1 spec;
  - the interaction records' metadata, against `docs/ai-log-requirements.md`.

  Each was checked against the current state: OQ-17 (a′), sim v1 built and calibrated, and the RL stack in.
- **Fixed (facts that lagged, no decisions):**
  - `CLAUDE.md`:
    - the project line no longer says it's validated on the server, and states OQ-17's scope;
    - sim v1's four skills are built;
    - "for calibration and E6" is now "for calibration";
    - the instances' GE path is `server/Server/data/eco/instance-<n>`;
    - timing measurements run one script per server (the Agility session's finding of 2026-11-08, left "for Caleb"
      then).
  - `ROADMAP.md`:
    - §2's layout has an as-built note, and says `results/summary/` must be un-ignored;
    - §3's Envelope Q row is marked cut;
    - the throughput estimates are marked superseded by the measurement;
    - week 1's Singleplayer install isn't needed now;
    - week 2's sim v0, baselines and calibration items are ticked;
    - Appendix B's recommendation is marked superseded.
  - `docs/resources.md`:
    - PyTorch [41] and TensorBoard [42] added (in use since 2026-11-08);
    - sb3-contrib noted as used;
    - MORL-Baselines and MO-Gymnasium no longer planned (E4 cut);
    - ruptures planned.
  - `docs/post-project-gaps.md`: four references to E6 or `ServerEnv` now say they're cut.
  - **Seven records' Commit lines** said uncommitted, though git has them. Each now names the commit that added it:
    - `m000-feasibility-review`: `bc7bfec`;
    - `m002-documentation-audit`: `d65bc81`;
    - `m002-simulation-decisions`: `493af16`;
    - the four sim v0 slices: `f2baf2c`, `ae0cb7e`, `32f4ed3` and `ee6eda8`.
  - **This session's five records' Status values** now follow the policy.
- **Found before E1, for Caleb:**
  - A smoke run of E1 on sim v1 (4 baselines × 4 seeds, 103 s on 4 workers, `results/smoke-e1-simv1`) works.
  - **OQ-52:** greedy GP spends about 70% of its game time on 15-minute Agility stints that earn nothing.
    - After a load of picked flax, `bank_deposit` is masked: the Crafting kit keeps flax, spinning's input.
    - Greedy then breaks the 0-gp tie by the lowest action id.
  - **OQ-53:** the scripted guide trains sim v0's 14 skills, and none of sim v1's four.
  - **OQ-54:** E1's evaluation seeds.
  - **OQ-55:** housekeeping:
    - ROADMAP §6's Friday entries, never written;
    - 58 older records' Status values;
    - the env contract's `ServerEnv`, E4 and E6 wording.
- **The rest of the plan before E1** (ROADMAP's finishing plan, Nov 9 to 10):
  - the speed checks: running, and 28 of 28 agree so far;
  - the sim freeze;
  - the mask speed-up;
  - `train.py` with the decision logger, which E1 can use too.

## Documentation Changes

- `CLAUDE.md`, `ROADMAP.md`, `docs/resources.md` and `docs/post-project-gaps.md`, as above.
- `docs/open-questions-log.md`: OQ-52 to OQ-55 added.
- `docs/agent-interactions/`:
  - the seven records' Commit lines;
  - the Status lines of `m002-viability-reassessment`, `m002-oq17-scope`, `m002-confirm-contract`, `m002-oq51` and
    `m002-commit-all`.
- This record.

## Code Changes

- None. The probes of greedy GP were scratch scripts in the session's scratchpad.

## Infrastructure Changes

- None for the audit. The speed checks' servers are `m002-speed-checks`.

## Decisions

- **User decisions:** none yet.
- **Agent recommendations:**
  - OQ-52 (a): fix the kit and the tie-break;
  - OQ-53 (a): extend the guide where a 2009 guide puts the four skills early;
  - OQ-54 (a): 30 seeds;
  - OQ-55 (a) for all three items.
- **Left as written, on purpose:**
  - the decision log's "to confirm" in older entries, since the log is chronological;
  - ROADMAP weeks 3 to 5's unticked items, which §4's note sends to the finishing plan.

## Validation

- **The smoke run** of `scripts/evaluate.py` with all four baselines: 16 episodes, exit 0.
- **The flax loop** is shown by a probe of greedy GP at seed 0's sixth decision:
  - `bank_deposit` isn't allowed and only `bank_deposit_worn` is;
  - every rate is 0.0;
  - `skill_agility_xp1` is chosen.
- **The Status counts** come from the records' first Status lines, after this session's fixes:
  - SUCCESS 68, PARTIAL 14;
  - DONE 45, COMPLETE 7, IN PROGRESS 5, RECOMMENDATION GIVEN 1.

## Follow-Up

- **Caleb:** OQ-52 (before the freeze, for the kit), OQ-53 and OQ-54 (before E1), and OQ-55.
- **Claude:**
  - finish the speed checks (`m002-speed-checks`);
  - once the answers are in, the freeze, the mask speed-up and `train.py`.
