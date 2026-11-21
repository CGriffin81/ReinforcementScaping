# Agent Interaction

## Metadata

- Interaction ID: m002-roadmap-boxes
- Timestamp CST: 2026-11-21 14:35:42 CST (the prompt), the session transcript's timestamp (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. ROADMAP's boxes and its stale lines match `main` after the experiment merges, and the four
  experiment-build records no longer say their experiment "trains when E3 frees the machine".
- Commit: a docs commit to `main` after `b04ea22` (Caleb: "Commit it to main directly", 2026-11-21 17:23:02 CST).

## Full Prompt

> Update the ROADMAP's boxes and the stale lines

## Response Summary

- **The finishing plan's boxes:**
  - E3, E4, E5 and E6 are ticked, each with its PR (#33 to #37). The three "It trains when E3 frees the machine" lines
    are replaced. A new paragraph, *Finished (2026-11-19 to 11-21)*, ends the runs' story: the 50 reruns finished
    at 10:00 on Nov 19, none failed; 14 on sim v1.3 and the rest on sim v1.4; evaluated on Nov 19, published by Nov 20;
    merged on Nov 21.
  - E5's line says its training cost isn't tabled yet. Each run's decisions and wall time are in its summary's
    `training/runs.csv`, but no figure or table compares E5's cost with E3's.
  - E6b's line notes the two policies whose evaluation episodes stop at the cap (OQ-91 (b)).
  - The figures and the one-script boxes are ticked. `scripts/figures.py` makes every figure and table from `main`'s
    summaries. "Still to add: RQ5" is replaced by when RQ5's walking tables were added (2026-11-12, OQ-87 (a)).
  - The peer-review box stays open, with its state: the guide is drafted (PR #28), and the tag it names is still to
    come.
  - The report's two boxes and Windows Update's stay open.
- **The old plan's weeks 3 to 5,** superseded by the finishing plan on 2026-11-09 but never closed. Each box now says
  where it went, in the proposal's numbers as those sections use them:
  - ticked: `train.py`, the sanity ladder (E2 now), the sweep (E3 now), RND (E4 now), the γ_hr and PBRS ablations
    (E6a and E6b now; the granularity cut), the analysis utilities, and the midpoint review (OQ-17 (a′));
  - left open with *Cut*: the MO-Gymnasium env and Envelope Q, as week 1's Singleplayer box was left open with *Not
    needed now*;
  - left open: the Pareto front and hypervolume box, since its training-cost comparison isn't done (as E5's line).
- **Other stale lines:**
  - §2's layout: `agents/` had "RND to come"; it now lists the agents package's files and `analysis/`;
  - week 1's RL stack: "morl-baselines and mo-gymnasium wait for E4" is now that they aren't needed (Envelope Q cut);
  - the training queue's line: "it trains" is now "it trained", both rounds;
  - Appendix B: "Claude recommends (C′)" is now Caleb's (C′), 2026-11-12.
- **The four records** `m002-e4-rnd`, `m002-e5-conditioned`, `m002-e6b-pbrs` and `m002-e6a-config`:
  - Each Status stays PARTIAL, which is still true of its own interaction: the experiment was built, not trained.
  - Its "trains when E3 frees the machine" is now a dated update pointing to the records of its training, evaluation
    and merge.
  - Their Follow-Up lists were the plan at the time and stay as written.

## Documentation Changes

- `ROADMAP.md`: as above.
- `docs/agent-interactions/m002-e4-rnd.md`, `m002-e5-conditioned.md`, `m002-e6b-pbrs.md`, `m002-e6a-config.md`: the
  Status lines.
- This record.

## Code Changes

- None.

## Infrastructure Changes

- None.

## Decisions

- **Agent recommendation:** keep a cut box open with *Cut*, following week 1's precedent, and keep the old records'
  PARTIAL statuses with a dated update rather than rewriting them.
- **User decision:** none needed; these are status updates. The training-cost table is Caleb's to decide (Follow-Up).

## Validation

- Every claim is from the repo: the PR numbers and merges (`m002-experiment-merges`), the 14 runs on sim v1.3 (the
  decision log, 2026-11-16), the evaluation dates (`m002-rerun-evals`), the figures (`m002-experiment-merges`'s
  `figures.py` run on `main`), RQ5's tables (`dfa15db`, 2026-11-12), and E4's first training (`m002-oq79-rnd-centring`).
- The training cost: `grep` finds no comparison in `rlscape/analysis/`, `scripts/figures.py` or E5's summaries; only
  `runs.csv`'s `decisions` and `wall_seconds`.
- `grep` finds no "frees the machine" left as a current status in `ROADMAP.md` or the records. Three records about this
  work quote it (this one among them), and four Follow-Up lists keep it.
- `git diff --check` is clean. No added line is over 120 characters, except week 1's RL-stack bullet, whose section
  keeps every bullet on one line.

## Follow-Up

- **Caleb:** asked whether to commit; "Commit it to main directly" (17:23:02 CST). Done, as under Commit. Still open:
  whether E5's training cost against E3's should be a table in `scripts/figures.py` (from each summary's
  `training/runs.csv`), as the plan has it.
- **Claude:** the video script's [TO FILL] loop counts; the reviewer guide's claims table, its tag and RQ5's numbers.
