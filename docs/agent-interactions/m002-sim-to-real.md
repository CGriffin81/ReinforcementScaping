# Agent Interaction

## Metadata

- Interaction ID: m002-sim-to-real
- Timestamp CST: 2026-11-12 10:35:44 CST, the prompt's timestamp in the session transcript (UTC−06:00). Caleb's answers
  to the question dialog: 10:44:49 CST.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. Built, tested and merged into `main` by PR #26 (`d127073`, 11:33 CST; Caleb: "Merge PR 26 into
  main"). OQ-86 answered (b) in `m002-oq86`.
- Commit: on `tooling/sim-to-real` (from `main` at `f332029`; Caleb: "Commit it and open a PR into main", 11:19:25
  CST): `4f05ec5` (the tooling and docs), `35e48e6` (the clean-tree check fixed), and this commit, the summary made
  from `35e48e6`'s clean tree.

## Full Prompt

> Start on the sim-to-real table while the runs train

Answers in the question dialog (10:44:49 CST):

> Which sim should the table compare against the server? "Re-simulate on sim-v1.2 (Recommended)"
>
> How should the report show the roughly 200 cases? "Family table + case appendix (Recommended)"

Follow-up prompt (11:19:25 CST):

> Commit it and open a PR into main

## Response Summary

- **What was there:** no consolidated gate result. The calibration's results are about 225 git-ignored files in
  `results/calibration/`, in a dozen formats. The decision log reports each family's result where it was measured.
  Each file's sim side is the sim of its day (Oct 31 to Nov 9); v1's last changes, v1.1's directional walks and
  v1.2's fletch slot came after.
- **Caleb's choices:** the sim side re-simulated on sim-v1.2 against each case's latest server runs; the report gets a
  table per family in its body and every case in an appendix.
- **A correction to Claude's question:** it said the server "has been frozen since Oct 31, so its runs still stand".
  The upstream code was frozen then, but the fork's own rule changes went on to Nov 9. Where the decision log found
  one touched a family's measurements, it re-measured them (combat's sets after the region fix), and the table takes
  those re-measurements. Caleb was told.
- **Built:**
  - `scripts/sim_to_real.py`: for each family, the files the decision log reports; each case's last measurement among
    them; the server's rates by the runner's own function, the sim's by the runner's own sim, called now from the same
    start, 200 seeds. It writes `cases.csv`, `drops.csv`, `speed_check.csv`, `config.json` and a README into
    `results/summary/sim-to-real/`, with no server, in about 2 minutes. Into `results/summary/` it refuses a dirty
    tree, as `publish_summary.py` does.
  - `rlscape/analysis/sim_to_real.py`, called by `scripts/figures.py`: the family table (body), the case table
    (appendix) and the drop tables' row.
  - `scripts/measure_abyss.py`: the sim's side of its pass, rift and trip runs pulled out as functions, so stored runs
    can be re-simulated.
- **Results** (gated metrics, sim over server): 533 of 548 within ±20%, in 236 cases; 12 cases outside. Drop tables 371
  of 374 items over 9 monsters; the speed check 72 of 72.
  - **Ten are as the decision log has them,** or as it measured them without a gate verdict: the Draynor shrimp's
    items/hr (deaths), the heroes' gp/hr, the leeches (OQ-51), the poison spiders, ranged abyssal demons at band 91,
    melee experiments at band 91, the Abyss's hitpoints at Defence 20, the way out of the Abyss from its north,
    Agility at 15 (sampled for falls) and the walkers' run length.
  - **Two are new:** the toll-gate check trip (0.42; OQ-86 raised) and magic at the band-1 Black Knights' kills/hr
    (1.52).
- **Claude's slip, reported:** in an interim message Claude gave the total as 1,023 of 1,042 metrics, a mis-addition;
  the per-family counts it printed sum to 533 of 548. Caleb was told.

## Documentation Changes

- `docs/decision-log.md`: "Decided and built: the sim-to-real table, every calibration case re-simulated on sim-v1.2".
- `docs/open-questions-log.md`: OQ-86 (the toll-gate trip).
- `ROADMAP.md`: the sim-to-real tables built; RQ5 still to add.
- This record.

## Code Changes

- `scripts/sim_to_real.py` (new): the summary.
- `rlscape/analysis/sim_to_real.py` (new): the tables.
- `scripts/figures.py`: writes `sim_to_real_families.csv`, `sim_to_real_cases.csv` and `sim_to_real_drops.csv` when the
  summary is there.
- `scripts/measure_abyss.py`: `pass_levels`, `sim_outer_ticks`, `sim_rift_ticks`, `altar_ticks`, `trip_character`,
  `sim_trip_ticks` and `sim_trip_expected`, used by its runs and by `sim_to_real.py`.
- `tests/test_sim_to_real.py` (new): 9 tests.
- `results/summary/sim-to-real/` (new, committed): the summary, made from `35e48e6`.

## Infrastructure Changes

- The branch pushed and a PR opened into `main`.

## Decisions

- **User decisions (Caleb):** re-simulate on sim-v1.2 (Claude recommended it; the others were the sim as calibrated,
  or that plus a spot re-simulation); a family table and a case appendix (recommended; the others were the family
  table only, or every case in the body).
- **Claude's choices within them** (in the decision log and the summary's README, for Caleb's review):
  - each family's source files, from the decision log's reports, and each case's last measurement among them;
  - the gated metrics per family, from env contract §7 and OQ-20 (a);
  - what's left out (the fits' inputs, superseded runs, chaos's crossings);
  - 200 sim seeds a case;
  - the notes, quoting the decision log for each miss it explains.
- **For Caleb:** OQ-86.

## Validation

- The summary built with every family in about 2 minutes, one process beside the five training runs (available RAM
  stayed 5.7 to 6.2 GB).
- `figures.py` made the three tables from it (236 case rows, 12 outside the gate).
- Tests: `tests/test_sim_to_real.py` and `tests/test_analysis.py`, 28 passed; `tests/test_sim_abyss.py` and
  `tests/test_sim_pouches.py`, 25 passed. After the fix below, `tests/test_sim_to_real.py`: 9 passed.
- **Found on committing:** the first summary from the clean commit (`4f05ec5`) said `dirty: true`. The provenance read
  `git status` after the run had written its own files. Fixed in `35e48e6`: the check runs once at the start and
  leaves the output folder out (a rerun rewrites its committed files); a new test on a real git repo. The summary,
  made again from `35e48e6`: `dirty: false`, the same counts (533 of 548). `scripts/figures.py` made the three tables
  from `results/summary/`.
- **Cross-checks:**
  - combat, Crafting, Herblore and the Abyss's crossings re-simulate to their stored sim side, which shows the
    adapters run the same sims;
  - mining's re-simulated ratios are the decision log's after its fit (0.89 to 1.12);
  - the refactored `measure_abyss` functions reproduce the crossings' stored sim times (0.98 = 0.98, and so on).

## Follow-Up

- None. PR #26 is merged, and OQ-86 was answered (b) (`m002-oq86`): the toll-gate trip is a known gap.
