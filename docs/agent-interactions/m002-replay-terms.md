# Agent Interaction

## Metadata

- Interaction ID: m002-replay-terms
- Timestamp CST: 2026-11-10 13:31:55 CST, the prompt's timestamp in the session transcript (UTC−06:00). Caleb's
  answer came at 14:04:03 CST.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The page is relabelled, tested and checked in the app's browser. OQ-71 is decided (a).
- Commit: on `tooling/replay`, added to PR #17 (Caleb).

## Full Prompt

> I'm trying to understand the agent replay for e2. The final with 1m decisions has 1/166 decision, while the
> scripted guide has 1/368 decisions. I'm guessing that there are many decisions made per Decision, but reusing the
> terminology is incredibly confusing to anybody who is not deeply involved with the experiments.

Caleb's answer:

> Commit it to PR #17 and go with (a) for OQ-71

## Response Summary

- **Explained:** it's one unit at two scales. A decision is one option chosen, such as training Fishing at a spot or
  banking.
  - "1M decisions" is the model's whole training: 1,000,448 decisions over 8,638 practice episodes.
  - "1 of 166" counts one 20-hour episode's decisions. The final model made 166, and the guide 368.
  - Inside a decision, the sim plays out the activity's game actions without the policy. That's where the "many under
    one" happens. An option runs for up to 15 game-minutes (D), or seconds for a drop or a GE offer.
- **Relabelled the page:**
  - checkpoints are named by practice episodes ("After 8,638 episodes"), with the training decisions in their
    description;
  - the counter says "in this episode";
  - a "How to read this" box defines an episode and a decision, and describes each replay. The baselines are marked
    untrained.
- **Raised OQ-71:** how the report words training length. Caleb chose (a): keep "decision" as the one unit,
  defined once, with "training decisions" and the episodes for a run, and "decisions per episode" for an episode.
- **Committed** to PR #17, and OQ-71 moved to the decision log.

## Documentation Changes

- `docs/decision-log.md`: "Changed: the replay page names a checkpoint by its practice episodes", and "Decided:
  OQ-71". OQ-71 was raised in `docs/open-questions-log.md` and moved out when Caleb answered.
- `ROADMAP.md`: the report's wording item.
- This record.

## Code Changes

- `scripts/replay.py`:
  - `episodes_by(run, n_envs)`: training episodes ended by a given number of training decisions. It reads
    `episodes.parquet` for a finished run, or the decision log while one trains, up to the log's last part.
  - `trained_names`: each trained replay's label, short label and description.
  - `BASELINES`: one line per baseline.
  - `chosen` now returns the names.
  - Each replay carries `short` and `about`.
- `rlscape/eval/replay.html`:
  - the "How to read this" box, with a line for each replay;
  - the buttons' titles;
  - "in this episode" on the decision's title, its tooltip and the scrubber;
  - the timeline's label column widened (150 px, 22 characters), and the charts' end labels too (`short`, 15).
- `tests/test_replay.py` (4 → 6 tests):
  - the decision log and `episodes.parquet` give the same episodes at every checkpoint, and the log is unknown past
    its last part;
  - a trained replay is named by its episodes.

## Infrastructure Changes

- None. The `replays` preview server was started again to look at the page.

## Decisions

- **User decisions (Caleb):** OQ-71 (a); commit to PR #17.
- **Agent recommendations:** OQ-71 (a), which Caleb took.
- **Agent choices:**
  - name checkpoints by practice episodes, not training decisions;
  - read the counts from the run's own records;
  - an explainer box, open by default;
  - this left the project's unit, the configs and the logs as they are.

## Validation

- **Tests:** `uv run pytest tests/test_replay.py`: 6 passed (2 min 36 s).
- **Checked against the run:** the decision log, with its rows shifted by n_envs, gives exactly
  `episodes.parquet`'s 8,638 episode ends. At 100k, 500k and 1M decisions both give 715, 4,661 and 8,634 episodes.
- **Regenerated** E2's best run's page and looked at it in the app's browser:
  - the labels fit on the timeline and the charts' ends;
  - the episodes are 715, 5,603 and 8,638, beside the guide;
  - the replays are unchanged: 97, 118 and 166 decisions, and the guide's 368.
- **Decision lengths in those four replays:** from 0 to 15.0 game-minutes. The short ones are drops, GE offers and
  bank trips. That's what the explainer says.

## Follow-Up

- **Caleb:** merge PR #17 after #16.
- **Claude:** the report uses OQ-71's wording.
