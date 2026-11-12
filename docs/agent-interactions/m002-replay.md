# Agent Interaction

## Metadata

- Interaction ID: m002-replay
- Timestamp CST: 2026-11-10 07:37:27 CST. That's the prompt, sent while Claude was setting up E3. Caleb's answer came
  at 07:43:59 CST. Both are the session transcript's timestamps (UTC−06:00). This record was written at about 08:05
  CST (estimated).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS. The replay page is built, checked against the evaluation and tested, and its PR is open.
- Commit: on branch `tooling/replay`, stacked on `tooling/normalised-weights` (PR #16).

## Full Prompt

> I would like to watch an agent's training session. Can we build that easily or would it cost a lot of time to our
> already time starved project?

Caleb's answer to the question Claude asked, as the app gave it:

> "How would you like to watch an agent's training? Live curves are already logged to TensorBoard for every run and
> cost nothing to view. A replay page means a script that plays one 20-hour episode from a chosen checkpoint and
> seed in the sim and writes one HTML page. It's ROADMAP's planned demo (Nov 27–30) built early, about half
> a day."="Replay page + a map"

## Response Summary

- **Answered:** watching is cheap.
  - TensorBoard's curves cost nothing: every run already logs them.
  - A replay page is about half a day, and it's the planned demo built early.
  - Watching in the game client would take 1.5 weeks or more, since ServerEnv was cut.
- **Asked (OQ-70).** Caleb took the replay page with a map.
- **Built it while E3 trained:**
  - `scripts/replay.py <run dir>` plays a run's checkpoints, the first, the middle and the final by default, and any
    baselines, on one seed. It writes one self-contained HTML page with:
    - a timeline;
    - the route on the collision map;
    - each decision with the five options the policy weighed and its value;
    - the 24 skills;
    - the level and net-worth curves;
    - a table of every decision.
  - A replay is exactly the evaluation's episode: E2's final model and the guide on seed 0 reproduce their evaluated
    rows.
- **Viewed** in the app's browser via a localhost server for `results/replays/` (`.claude/launch.json`), since the pane
  won't open git-ignored files. Fixed what the first look showed:
  - the probability bars didn't draw (inline spans);
  - a label read "1.00045M decisions".

## Documentation Changes

- `docs/decision-log.md`: "Decided: OQ-70, watching an agent: a replay page with a map, built early (Caleb)" and
  "Built: the replay page (OQ-70)".
- `ROADMAP.md`: the tooling item, and the demo item points to `scripts/replay.py`.
- `CLAUDE.md`: how to watch a run.
- This record.

## Code Changes

- `rlscape/eval/replay.py` (new): `Walks`, `record`, `map_image`, `item_names`, `page`.
- `rlscape/eval/replay.html` (new): the page's template, with plain HTML, CSS and JavaScript.
- `scripts/replay.py` (new): the command line.
- `tests/test_replay.py` (new, 4 tests).
- `.claude/launch.json` (new): the desktop app's preview server for `results/replays/` on 127.0.0.1:8765.

## Infrastructure Changes

- None in the repo. The localhost preview server ran for the look; it's stopped by the end of the turn.

## Decisions

- **User decisions (Caleb):** OQ-70 (b), the replay page with a map.
- **Agent recommendations:** OQ-70 (a), TensorBoard and the replay page. Caleb chose (b), which adds the map.
- **Agent choices:**
  - the page's layout and contents;
  - families coloured in the palette's fixed order, commonest first;
  - the followed replay's lines in ink and the others muted, so line colour never competes with family colour;
  - walks rebuilt from each option's start to its end;
  - dungeons drawn 6,400 tiles south, as rings.

## Validation

- `tests/test_replay.py`: 4 passed. That includes E2's best model's replay against its evaluated row; the model is
  in `runs/`, which is git-ignored.
- Generated E2's best run's page (three checkpoints and the guide, about 1.5 minutes), and looked at it in the app's
  browser.

## Follow-Up

- **Caleb:**
  - review and merge the stack: #13, #14, #15, #16, then this PR;
  - try the page on E2's run, or on E3's runs as their checkpoints appear.
- **Claude:** E3 trains until about 2026-11-12 10:00 CST, then its evaluation and summary.
