# Agent Interaction

## Metadata

- Interaction ID: m002-video-script
- Timestamp CST: 2026-11-20 13:44:22 CST (the prompt), the session transcript's timestamp (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (draft 1). The script is written, from a replay generated for it and the published evaluation
  summaries. What waits on the report's analysis is marked [TO FILL].
- Commit: the docs commit to `main` after `e0ce57f` (Caleb: "Commit it to main directly", 2026-11-20 17:56:18 CST),
  as draft 1.

## Full Prompt

> I am meant to submit a pdf report and a video explaining the project, along with my github link. I will need you to
> draft a script for the video that I can read over a demo video that we take of an agent performing actions.

## Response Summary

- **The script,** `docs/video-script.md`, in eight sections:
  - cold open, the question, the formulation, the simulator, the demo, the results, what went wrong and the limits,
    and the close;
  - each section has **[SCREEN]** cues and the narration under them;
  - about 1,320 words, about 9½ minutes at 140 words a minute (each section's times from its words), and about
    8 minutes without the paragraphs marked as cuts.
- **The demo** is the replay page the ROADMAP's finishing plan names (`scripts/replay.py`, OQ-70). It replays E3's
  (.5, .5) seed 0, the reference configuration for RQ4, which doesn't end looping. That's three checkpoints of one
  episode (seed 0), beside the scripted guide. It was made for the script, so the narration describes what the page
  actually shows:
  - early (538 episodes): a generalist, woodcutting and fletching, agility and melee; level 282, 21,038 gp;
  - middle (4,299): a thieving ladder; level 223, 1,540,616 gp;
  - final (5,688): the same ladder with more skill; level 280, 1,046,904 gp;
  - the scripted guide: level 337, 130,826 gp.
- **The final replay's plan:**
  - It pickpockets men at game time 2:18, farmers at 4:18 and warriors at 6:09.
  - Its Thieving reaches 38 at 7:32. After restocking food, its next pickpocketing trip, at 7:54, is on Master
    Farmers, which need 38 and drop seeds (the server's `Pickpockets.kt`).
  - Its net worth goes from 38,234 gp then to 1,046,904 at hour 20. About 1.03 million of that came from
    pickpocketing.
  - Its fishing is shrimp, caught and cooked in the Lumbridge swamp. 93 of its 124 pickpocketing trips end when the
    food runs out.
- **The results section's numbers:** each is the hour-20 mean over a configuration's 5 training seeds, each seed
  evaluated on the same 30 episodes, from the published summaries (E1 on `main`, E3, E4, E5 and E6a on their branches,
  and E6b's unpublished summary). E6b's mean is over the 4 seeds that reach hour 20 (OQ-91 (b)). The simulator's
  "533 of 548" is from `results/summary/sim-to-real/`.
- **Not claimed:** H1 to H3's verdicts, E5's hypervolume, the final loop counts and the figures' names are [TO FILL].
  The loop paragraph follows OQ-89 (a): the counts by discount, and the cause at γ_hr 0.99 untested. *Updated
  2026-11-22:* the loop counts are filled from the final census (`m002-video-loop-counts`).
- **The repository is private** (`gh repo view`). The script's header says so: the graders need access to the link.

## Documentation Changes

- `docs/video-script.md` (new).
- This record.

## Code Changes

- None. Scratch scripts read the replay's data and the summaries.

## Infrastructure Changes

- None. The replay page was copied into this worktree's git-ignored `results/replays/`, and served on localhost by
  the existing `replays` preview config to check the recording directions.

## Decisions

- **Agent recommendation:** E3's (.5, .5) seed 0 for the demo, with the scripted guide beside it. A narration that
  says only what the replay and the summaries show, with the report's verdicts left to fill. Disclosing the AI
  assistant in the video is left to Caleb, marked optional.
- **User decision:** pending (the run for the demo, the video's length limit, the disclosure line).

## Validation

- The replay's final checkpoint is the evaluation's episode: 729 decisions, level 280 and 1,046,904 gp, as E3's
  `episodes.csv` has for (.5, .5) seed 0 on seed 0.
- The thieving ladder is read from the replay's decisions, and the Master Farmer requirement and loot from the
  server's `Pickpockets.kt`.
- On the page itself, in the browser: the replay buttons, the speed menu, the decision numbers (counted from 1) and
  game times at each moment the narration names, and the panels' names.
- Each configuration's mean is recomputed from the published `checkpoints.csv` files.
- The narration's word count, by section.

## Follow-Up

- **Caleb:** the video's length limit; whether this run is the demo; the AI line; and making the repository public
  or sharing it.
- **Claude:** fill the [TO FILL] marks once the report's analysis is done.
