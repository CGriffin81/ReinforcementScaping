# Agent Interaction

## Metadata

- Interaction ID: m002-progress-report
- Timestamp CST: 2026-11-23 07:13:02 CST (the prompt), the session transcript's timestamp (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The progress report and its supporting results are built as PDFs, with a zip to submit that holds
  them and the proposal. Caleb reviews them before submitting.
- Commit: a commit to `main` after `a22e82e`, with `m002-woodcutting-wording`.

## Full Prompt

> I need to give a progress report today. The details of that progress report are:
> "Explain your original experiment question. Please submit a pdf summary of progress report and findings so far.
> Please include any supporting docs." Please get this requirement together while I am at work.

## Response Summary

- **The report** (`docs/progress-report/progress-report.pdf`, 9 pages), in the proposal's look and in Caleb's first
  person, as the proposal is:
  - a status box;
  - **1. The original question:** the motivation, the main question, RQ1 to RQ5, H1 to H3 and the proposal's test of
    success, quoted from the proposal;
  - **2. What was built:** the server and its bridge, the decision gate's results, the calibrated simulator, and the
    formulation as built (options, observation, reward, semi-MDP discount, learner, evaluation);
  - **3. Changes from the proposal:** each with its reason, from the decision log (the scope decision of November 9,
    Envelope Q-learning replaced, the cuts, quests, the sanity check, normalised weights, the trainer's fix);
  - **4. Progress against the plan:** the proposal's weeks against what happened, with dates from the ROADMAP;
  - **5. Findings so far:** RQ1 to RQ5 and H1 to H3, with five figures and two tables. Every number is the reviewer's
    guide's claims table's or a table `scripts/figures.py` writes;
  - **6. Problems and limitations;** **7. Remaining work;** **8. Supporting documents**;
  - a short note on how the work was done, with an AI coding assistant, every interaction logged.
- **The supporting results** (`supporting-results.pdf`, 11 pages): the experiments as run, every policy at hours 2
  and 20, the weighted values, RQ4's variants, the hypervolumes and training cost, the per-run verdicts, the mix
  divergences, RQ5's bound, the calibration gate per family, E3's first round against its rerun, and all nine
  figures with captions.
- **The zip to submit** (`progress-report-submission.zip`, git-ignored as every zip is): the two PDFs and the
  original proposal, numbered in reading order.
- **Found while checking the numbers:** the reviewer's guide's RQ1 row compares hour 2's levels with the guide's 97,
  but at hour 2 the best baseline on level is greedy XP/hr (106). The agents lead either way (121). The report says
  "at most 106 for a baseline".

## Documentation Changes

- `docs/progress-report/progress-report.html`: the report, written by hand.
- `docs/progress-report/report.css`: the print style both documents share.
- `docs/progress-report/supporting-results.html`, `progress-report.pdf`, `supporting-results.pdf` and the zip:
  built by the script (untracked; whether to commit the PDFs is Caleb's call).
- This record.

## Code Changes

- `scripts/progress_report.py`: builds the supporting results' tables from `results/figures/` and the committed
  summaries (RQ4's levels and net worth by `measures.progress`, as the `progress` figure has E3's), prints both
  pages to PDF with headless Edge (a profile of its own; it waits for the file, since Edge can return first), and
  zips them with the proposal.
- Scratch scripts in the session's scratchpad: `report_numbers.py` (the numbers, from the figure tables),
  `pdf_pages.py` (each PDF page to an image, to check the layout) and `edge_debug.py`.

## Infrastructure Changes

- None. `uv run --no-project --with pypdfium2` rendered the pages for checking; nothing was installed in the project.

## Decisions

- **User decisions (Caleb):** a progress report as a PDF, explaining the original question, with the findings so far
  and supporting documents (the prompt).
- **Agent choices** (Caleb was at work, so none of these was asked):
  - the form: one report of about 9 pages, a separate supporting-results PDF, the proposal, and a zip of the three;
  - HTML printed by Edge rather than reportlab, for tables, figures and page numbers;
  - only results Caleb has already decided or that the committed tables hold: H1 to H3's verdicts are Caleb's
    (2026-11-22), and no new claim is made;
  - first person, as Caleb's own report;
  - **the "How the work was done" note** on the AI assistant, which Caleb should keep, change or delete;
  - the repository's link, with "private at the time of writing".

## Validation

- `uv run python scripts/progress_report.py` builds both PDFs and the zip.
- Every page of both PDFs was rendered and looked at; the figures were checked for legibility at a larger scale.
- The numbers: the report's tables and text against `results/figures/*.csv` (`report_numbers.py`) and the reviewer's
  guide; the supporting results' RQ4 table matches the guide's numbers (263/588k, 226/135k, 330/1.14M, 247/2.21M,
  194/142k over 4 seeds).
- The dates against the ROADMAP and the decision log.
- `git diff --check` is clean; the script and the stylesheet have no line over 120 characters (the report's two
  longer lines are table rows).

## Follow-Up

- **Caleb:** read the report, keep or change the "How the work was done" note, and submit the zip (or the PDFs); the
  repository is private, so the link only works for people given access; whether to commit any of it.
- **Claude:** the reviewer's guide's hour-2 comparison (the guide's 97 against greedy XP/hr's 106): fixed at Caleb's
  request (`m002-readme-hour2`).
