# Agent Interaction

## Metadata

- Interaction ID: m002-figures
- Timestamp CST: 2026-11-11 22:15:54 CST, the prompt's timestamp in the session transcript (UTC−06:00). OQ-82 to
  OQ-85 were answered later in the same turn, through the app's question dialog (the dialog's time isn't in the
  transcript).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: COMPLETE. The figure script is built, and OQ-82 to OQ-85 are decided (Caleb, each as recommended) and built.
  Caleb confirmed Claude's two choices within them, OQ-82's noise floor and OQ-83's whole-level targets, and asked
  for the commit and push (23:49:06 CST).
- Commit: on `tooling/figures` (from `tooling/units-v1.2`), pushed. The first try was blocked by the app's permission
  check until Caleb asked.

## Full Prompt

> Yes, start the figure script

Caleb's answers in the question dialog, verbatim:

> OQ-82 … Revise the rule? = "Merge + warm-up (Recommended)"
> OQ-83 … Which milestones, read from each evaluation episode's trace? = "50% and 100% of ideal (Recommended)"
> OQ-84 … How is 'match' read from each run's learning curve …? = "Best greedy, sustained (Recommended)"
> OQ-85 … How should it be measured? = "Jensen-Shannon of mixes (Recommended)"

Follow-up (2026-11-11 23:49:06 CST):

> Both choices are fine, commit and push it

## Response Summary

- **Built:** `scripts/figures.py` with `rlscape/analysis/`: the activities, the measures and the figures. It rebuilds
  every figure the published summaries allow, writing PDF, PNG and a CSV of each figure's values, with the measures'
  tables, and names the figures it skipped. The decision log's "Built: the figure script" and "Decided: OQ-82 to
  OQ-85" have the details.
- **The figures:**
  - learning curves with CIs and changepoints, for E3 and for RQ4 against E3's (.5, .5);
  - RQ1's progress at the checkpoints;
  - time allocation across training, for E3 and for RQ4;
  - each policy's activity mix in evaluation;
  - the discovery timeline, E3's (.5, .5) against PPO + RND;
  - the Pareto front with its hypervolumes;
  - the policy's entropy.
- **The tables:**
  - verdicts and changepoints, under both rules;
  - discovery;
  - the hypervolumes;
  - sample efficiency;
  - milestones;
  - consistency.
- **Tried on real data:** E3's seed-0 runs part-way, read-only, and their 700k checkpoints evaluated on 3 seeds
  (scratch only).
  - (.25, .75) jumps at 580k to 660k decisions to 1.43 of E1's ideal: the gem trade, 3.3M gp in 20 hours. It reaches
    1.76M gp gained in a median of 12.2 game hours, and matches greedy GP/hr at 640k decisions.
  - (1, 0) and (.5, .5) level off under the guide and greedy GP/hr. (.5, .5) hasn't matched greedy GP/hr at its
    weighting.
- **OQ-82 to OQ-85:** asked with recommendations; Caleb took each. While building them, two things the questions
  hadn't settled, both Claude's choices, to confirm:
  - **OQ-82, the noise floor:** a gain after the warm-up of no more than 2σ is "no gain". Without it, (1, 0)'s flat
    curve (a wiggle up and back, net +0.0009) was "sudden".
  - **OQ-83, whole levels:** the trace has whole levels, in which the guide gains 316.03 in 20 hours, not 323.87. So
    the level milestones are 158 and 316, not the 162 and 324 put in the question.
- **Found in the full suite:** `test_replay`'s E2 replay fails on sim v1.2. E2's model is v1.1 (3,482 features); v1.2
  has 3,488. It's left from the v1.2 change, and was flagged as a separate task.

## Documentation Changes

- `docs/decision-log.md`: "Built: the figure script" and "Decided: OQ-82 to OQ-85".
- `docs/open-questions-log.md`: OQ-82 to OQ-85 were added, then moved to the decision log when answered.
- `ROADMAP.md`: the analysis's figure item says what's built and what's still to add (the sim-to-real table, RQ5).
- `docs/resources.md`: [50] ruptures (Truong et al.), [51] PELT (Killick et al.), [52] matplotlib (Hunter). ruptures
  leaves "Planned".
- This record.

## Code Changes

- `rlscape/analysis/__init__.py`, `activities.py`, `measures.py`, `figures.py` (new).
  - `measures.py`, for OQ-82 to OQ-85: `segments`, `noise`, `decided_verdict`, `rises`, `revised_verdict`,
    `sample_efficiency`, `js_divergence`, `consistency`, `milestones` and `milestone_summary`.
- `scripts/figures.py` (new).
- `tests/test_analysis.py` (new, 20 tests).
- `pyproject.toml`, `uv.lock`: matplotlib 3.11.2 and ruptures 1.1.10.

## Infrastructure Changes

- The main checkout is on the new branch `tooling/figures`, and its venv has matplotlib and ruptures. The training
  runs use their own worktrees' venvs, so they're untouched.
- The scratch evaluation (21 episodes, 2 workers, 9 minutes) ran beside the queue's four runs. Its files and the
  figures tried are in the session's scratchpad, not in the repo.
- A scratch HTTP server on 127.0.0.1:8799 served the dataviz palette validator to the browser pane (Node isn't
  installed). It was stopped afterwards (PIDs 1892, 24732).
- OQ-81's commit (`9bf1df4`) was pushed to `tooling/units-v1.2` (PR #24) and merged here, so the open questions stay
  in one sequence.

## Decisions

- **Agent recommendations:** OQ-82 (c), OQ-83 (a), OQ-84 (a), OQ-85 (a).
- **User decisions (Caleb):** OQ-82 (c), OQ-83 (a), OQ-84 (a), OQ-85 (a).
- **Claude's choices within decided definitions** (Caleb confirmed the noise floor and the whole-level targets, "Both
  choices are fine"):
  - learning-curve values over SKILL_UNIT, so curves at different weightings share a scale;
  - the BIC penalty and 2-bin segments;
  - OQ-82's noise floor (2σ);
  - OQ-83's level targets in whole levels (158 and 316);
  - a skill slot counts for its skill, so chop-and-fletch is woodcutting;
  - the time-allocation figures keep the 7 largest activities and fold the rest into "other" (the dataviz method's
    cap).

## Validation

- `tests/test_analysis.py`: 20 passed.
- The full suite on one worker, before OQ-82 to OQ-85's code: 483 passed, 75 skipped, and 1 failed (the E2 replay
  above, reproduced on its own).
- The figures were rendered and looked at.
  - Fixed: a layout collapse caused by empty marker lines, colliding end labels, and the Pareto legend and front.
- Palettes: checked with the dataviz validator, as the figures module's docstring lists.
- Lint (`ruff`, line length 120): clean apart from two `noqa: E402` kept for linters that check it.

## Follow-Up

- **Caleb:**
  - whether to open a PR for `tooling/figures` (stacked on #24), and its review;
  - OQ-81 (deferred), OQ-1 by Nov 19 and OQ-50 by Nov 22.
- **Claude:** after the runs, the figures from the published summaries; the sim-to-real table and RQ5.
