# Agent Interaction

## Metadata

- Interaction ID: m002-reviewer-claims
- Timestamp CST: 2026-11-22 21:23:07 CST (the prompt), the session transcript's timestamp (UTC−06:00). The question
  dialog's answers: 22:26:01 CST, the tool result's timestamp.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The reviewer's guide's claims table has every claim's results and H1 to H3's verdicts (Caleb's),
  and `scripts/figures.py` has two more tables behind them.
- Commit: a commit to `main` after `af3e863` (Caleb: "Commit it to main directly", 2026-11-22 23:47:32 CST).

## Full Prompt

> Make the reviewer guide's claims table

Answers in the question dialog (22:26:01 CST):

> H1's verdict: "Partly supported"
> H2's verdict: "Partly supported (Recommended)"
> H3's verdict: "Supported (Recommended)"
> The two tables for `scripts/figures.py`: "Add both (Recommended)"

## Response Summary

- **The table** (`README.md`, section 1) gains a column, "What the results show": each claim's numbers from the
  committed summaries and `scripts/figures.py`'s tables, at hour 20 of evaluation unless it says so. A paragraph
  above it says what a result is: 30 seeded episodes for each of a variant's five training seeds, means over the
  seeds, and the weightings' units.
  - **RQ1:** at the ends, the learned agents beat the best baseline from hour 2 on. On the reward's weighted value,
    they don't at the mixed weightings: (.5, .5) is at 0.526 against greedy GP/hr's 0.571, and (.25, .75) at 0.453
    against 0.785.
  - **RQ2:** the discovery order at (.5, .5), and the gradual-or-sudden verdicts by weighting.
  - **RQ3:** the mixes from all skill to all wealth. E5's hypervolume (0.394) is about E3's (0.373) for a fifth of
    the training, but E5 falls short at the ends (level 359 against 382, 862k gp against 3.74M).
  - **RQ4:** each variant at hour 20, how fast each reaches the best greedy baseline, and its weighted value. γ_hr 0.9
    and 0.5 beat greedy GP/hr in every seed; RND and PBRS in none.
  - **RQ5:** the bound. A perfect click-ahead saves at most 2.6% of (.5, .5)'s game time, and 10.5% of (0, 1)'s.
  - **H1 to H3:** each one's verdict (Caleb), then its evidence.
  - **The simulator:** 533 of 548 metrics within ±20% over 236 cases.
  - **Two new rows, the limits:**
    - the loops at γ_hr 0.99 (10 of 40, the final census);
    - the trainer's two changes: E3's first round found the Gem Store trade in 5 of 15 mixed-weight runs, and the
      rerun in none (OQ-92 (b)).
- **The verdicts.** Claude asked for them with each one's evidence and a recommendation, since they are what the
  report claims:
  - **H1:** partly supported. Claude recommended not supported; supported was the third option.
  - **H2:** partly supported, the recommendation. The other options were supported and not supported.
  - **H3:** supported, the recommendation. The other options were partly supported and not supported.

  Each is logged with its evidence in `docs/decision-log.md`.
- **Two tables in `scripts/figures.py`**, so that every number behind the verdicts is rebuilt (Caleb: both):
  - **`weighted_value_per_seed.csv` and `weighted_value.csv`** (`weighted_values`): each agent trained at one weighting
    (E3, E4, E6a, E6b), at its 20-hour value on the reward's scale, against E1's best baseline at that weighting, with
    how many seeds are above it. The values are in the decision log's entry.
  - **`mix_divergence.csv`** (`measures.divergence_between`): per pair of E3's weightings, the mean Jensen–Shannon
    divergence between a seed of each over all 25 pairs, with a bootstrap CI, to read beside `consistency.csv`. For
    example, (1, 0) and (.75, .25) are 0.138 bits apart, less than (.75, .25)'s own seeds (0.194).
- **Also fixed in the guide:**
  - Section 3 called `sim-v1.2` the frozen simulator. The sim-to-real table is on `sim-v1.2`, but the experiments
    ran on `sim-v1.4`. It now says that `sim-v1.4` plays out as `sim-v1.2` wherever that completes, and names its
    two edge cases.
  - The intro's long line is rewrapped.
- **Found:** the all-wealth agents spend 45% of their game time buying `1621` (uncut emeralds) in a shop and 30%
  selling them on the GE, 12% and 6% on `1623`, and 4% banking. They do the same in their first two hours.

## Documentation Changes

- `README.md`: the claims table's results column, the verdicts and the two limit rows; the paragraph above it;
  section 3's simulator versions; the intro's rewrap.
- `docs/decision-log.md`: "Decided: H1 to H3's verdicts, and two tables behind them".
- `ROADMAP.md`: the verdicts beside the report's item.
- This record.

## Code Changes

- `rlscape/analysis/measures.py`: `divergence_between`.
- `scripts/figures.py`:
  - `baseline_values`, which `best_baseline` now calls;
  - `weighted_values` and `FIXED`;
  - the two tables written in `build`;
  - the docstring's table list.
- `tests/test_analysis.py`:
  - `test_the_divergence_between_two_variants_is_the_mean_over_every_pair_of_a_seed_of_each`, on known mixes;
  - `test_each_agent_at_one_weighting_is_scored_against_e1s_best_baseline_at_that_weighting`, on a synthetic summary;
  - the end-to-end figure test checks both tables.
- Scratch analysis in the session's scratchpad (`claims_*.py`), which found the evidence first.

## Infrastructure Changes

- None. `results/figures/` was rebuilt (git-ignored).

## Decisions

- **User decisions (Caleb):** make the claims table (the prompt); H1 and H2 partly supported, H3 supported; add both
  tables.
- **Agent choices:**
  - one results column in the existing table, rather than a second table;
  - only numbers that a committed table or summary holds;
  - the two limit rows;
  - the `sim-v1.4` fix in section 3;
  - the tables' scope: `weighted_value` covers the agents trained at one weighting, and leaves out E5's, which the
    `pareto` figure shows; `mix_divergence` covers E3's weightings only.

## Validation

- `uv run pytest tests/test_analysis.py -n 8`: 26 passed.
- `uv run python scripts/figures.py` rebuilt every figure and table, none skipped. The two new tables match the
  scratch analysis, and `mix_divergence`'s within-weighting reference matches `consistency.csv`.
- Each number in the claims table was read again from its table, at three decimals where it quotes them.
- `git diff --check` is clean. Outside the tables, the only line over 120 characters is the existing training
  command.

## Follow-Up

- **Caleb:** committed to `main` (23:47:32 CST).
- **Claude:** the video script's H1 to H3 and hypervolume [TO FILL]s from these; the guide's tag and the queue's
  total time; RQ5's numbers in the report.
