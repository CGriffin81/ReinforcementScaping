# Agent Interaction

## Metadata

- Interaction ID: m002-open-questions
- Timestamp CST: 2026-10-31 05:10:40 CST (from the session transcript's message timestamp, UTC−05:00); Caleb's
  answers to Claude's two questions at 05:15:45 CST
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the open-questions log made; answered questions removed from the other docs; the buying draft
  deleted)
- Commit: the commit that adds this record holds this work (main repo, branch `sim-v0`; its SHA can only be
  filled in by a later commit)

## Full Prompt

> Review the documentation for questions. Questions that are already answered should exist only in the decision
> log. Open questions should be migrated to an open-questions-log.md file. For future questions that are undecided,
> record them in open-questions-log.

Claude asked two questions (`AskUserQuestion`); Caleb's answers:
- `docs/buying-draft.md`, all answered questions and superseded: "Delete it (Recommended)".
- Env contract §9's list of decisions: "Keep it (Recommended)".

## Response Summary

- **Reviewed:** `ROADMAP.md`, `CLAUDE.md`, the env contract, the option catalog, the buying, vocabulary and
  scripted-guide drafts, `docs/resources.md` and the decision log (for questions raised there and never answered).
- **Open questions found, now in `docs/open-questions-log.md`:**
  - OQ-1: E7
  - OQ-2: the sim v1 skills' options
  - OQ-3: prayer flicking
  - OQ-4: the remaining player-path bridge commands
  - OQ-5: freezing the server version at calibration (a recommendation in `CLAUDE.md` that was never decided)
  - OQ-6: public repos (deferred)
- **Answered questions:** each was checked against the decision log, and the alternatives some entries lacked were
  added there. Then they were removed from ROADMAP §8, the guide and vocabulary pages, the catalog's buying tags and
  header, and the contract's Q3b references.
- **The rule for later** is in `CLAUDE.md`: undecided questions go in the open-questions log, and answered ones
  move to the decision log.

## Documentation Changes

- `docs/open-questions-log.md` (new).
- `docs/buying-draft.md`: deleted (last version in `d72dc47`).
- `docs/decision-log.md`:
  - today's entry
  - the alternatives added to the buying Q3b, Q6 and Q7, the food withdrawals, the vocabulary Q1 and Q2, and the
    guide Q5
  - a resolution note on the 2026-10-05 pending recommendations
- `docs/scripted-guide-draft.md`: retitled; the question section and the first draft's review note removed; the
  sign-off note without question numbers.
- `docs/vocabulary-draft.md`: retitled; the status rewritten; Q1–Q4 replaced by the accepted readings; "five" v1
  skills now four.
- `docs/option-catalog.md`: the header's list of decided questions replaced by pointers; §3.5 and §9 point to OQ-2;
  §8's question tags removed (and "113 buys" corrected to 133).
- `docs/env-contract.md`: the Q3b references reworded; §7's "five v1 skills" now four.
- `ROADMAP.md`: §8 is a pointer; the guide's "awaiting Caleb" is now its sign-off; "five" v1 skills now four.
- `CLAUDE.md`: the open-questions rule, the four sim v1 skills, and OQ-5 in place of the recommendation.
- This record.

## Code Changes

- `rlscape/sim/buying.py`, `rlscape/sim/energy.py`: the docstrings say the question numbers they cite are in the
  decision log.
- `rlscape/baselines/guide.py`: the docstring no longer cites the removed Q5; a 123-character line rewrapped.

## Infrastructure Changes

None.

## Decisions

- **User decisions:**
  - an open-questions log, with answered questions only in the decision log
  - delete the buying draft
  - keep env contract §9
- **Agent choices (reversible):**
  - what counts as a question: anything framed as a question or as options to choose from, or marked as awaiting a
    decision. Decisions stated as design, known gaps and planned checks stay where they are.
  - the interaction records aren't edited, since they record past turns
  - the decision log's own chronological "open" notes stay, since later entries answer them
  - the six entries and their wording, including OQ-5, which was a recommendation and not yet a question

## Validation

- A search of the docs and code (outside the decision log and the records) finds no question numbers except in
  the code's docstrings and a live test, which cite the decision log's buying questions. It finds no "Questions"
  sections, "awaiting", "still open" or "to be specified".
- `uv run pytest -q`: 218 passed, 24 skipped (live tests; the server was down).
- `uvx ruff check --select F401,F811,F841 rlscape tests scripts`: passed.

## Follow-Up

- Caleb's answers to OQ-1 to OQ-6 as they come due. OQ-3 and OQ-4 come first.
- Commit when Caleb asks; fill in the Commit fields of this record, `m002-fletching` and `m002-skilling-slots` then.
