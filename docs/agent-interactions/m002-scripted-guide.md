# Agent Interaction

## Metadata

- Interaction ID: m002-scripted-guide
- Timestamp CST: 2026-10-30 15:42:25 CST (from the session transcript's message timestamp, UTC−05:00); the
  mid-turn question at 15:52:06 CST (its queue timestamp)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (harness committed; the scripted guide drafted, built and evaluated for Caleb's review; a sim
  mask fixed; Caleb's mid-turn questions answered from the server source, with decisions left to him)
- Commit: the eval harness is main repo `3714afa` (branch `sim-v0`); the guide draft is the main repo commit that adds
  this record (its SHA can only be filled in by a later commit)

## Full Prompt

> Commit this and keep going with the scripted guide

Caleb, mid-turn:

> The agents must be flagged as members. Do the agents know how to tick-manipulate for skilling and prayer flicking?

## Response Summary

- **Committed** the eval harness as `3714afa`, after the suite passed (171 passed, 18 skipped).
- **Researched the 2009 guides.**
  - The Wayback Machine had no snapshots of the guide pages Claude tried (an availability query and a web search
    both came back empty).
  - The RuneScape Wiki's API returned each training page as of January 2009: Woodcutting (890919), Fishing
    (886593), melee (898754), the Mining article (899733) and the money-making guide (899155). Each was read and
    summarised, not copied. The wiki's licence (CC BY-NC-SA 3.0) was checked on its copyright page.
  - No January 2009 page orders the skills, so the schedule is flagged as Claude's proposal.
- **Built the routine** (`ScriptedGuidePolicy`). Trial runs found five problems, each fixed in turn:
  - 1-tick "out of food" fights (21,847 in 4 hours): a sim mask gap, fixed in the sim
  - buying and selling the same pickaxe: the guide now sells only produce
  - GE trips to sell bones (17% of the time): the guide now sells only when the produce pays for an upgrade
  - cooking every catch: the guide now cooks only while under 10 pieces of food
  - depositing and withdrawing the same armour (6,425 times): the guide now withdraws gear only for a fight that can
    start, and fights right after
  - Then, Attack outran the other stats when their styles failed the danger filter. Each stat now trains only with
    its own style, and the turn otherwise passes to the next skill.
- **Evaluated** 10 seeds × 20 hours: total level 233 [230, 236], total XP 152k and net worth 23k, against random's
  192, 76k and 9k.
- **Wrote** `docs/scripted-guide-draft.md`, with sources, the mapping, the results and Q1–Q4.
- **Found a catalog gap:** no action withdraws banked produce to sell it (Q2 of the draft).
- **Answered the mid-turn question** from the server source:
  - **Membership:** a world-level setting, `members = true` in `rl.conf`. No per-player members check exists, so
    every character, the agent's included, is a member.
  - **Prayer flicking:** it works on this server and makes prayer free (the drain counter resets when no prayer is
    on). The sim and executor use no prayers in combat, so the agents neither pray nor flick.
  - **Tick manipulation:** options run the server's standard skilling delays. Whether 2009Scape lets an interaction
    shorten the skilling clock needs a live test.

## Documentation Changes

- `docs/scripted-guide-draft.md` (new): the draft for Caleb.
- `docs/resources.md`: [22]–[26], the January 2009 wiki revisions.
- `docs/decision-log.md`:
  - the draft
  - the fight-mask fix, and the note that the preliminary E1 numbers predate it
  - the catalog gap
  - the membership, flicking and tick-manipulation findings
- `ROADMAP.md`: the scripted-guide item (drafted, awaiting Caleb) and the status line.
- `m002-eval-harness`'s `Commit:` field (`3714afa`).
- This record.

## Code Changes

- `rlscape/baselines/guide.py` (new): `ScriptedGuidePolicy` and the method helpers.
- `rlscape/sim/slots.py`: fight slots are masked while HP is at or below the retreat point with no food (also noted
  in the module docstring).
- `rlscape/eval/harness.py`: `scripted_guide` in `POLICIES`, marked as a draft.
- Tests:
  - `tests/test_guide.py` (new, 2 tests): the guides' breakpoints; a deterministic, loop-free, balanced episode
  - `tests/test_sim_slots.py`: `test_fights_close_at_the_retreat_point_without_food`

## Infrastructure Changes

None. Results are in `results/eval/guide-draft-20261030`, which is git-ignored.

## Decisions

- **User decisions:**
  - commit, then work on the scripted guide
  - the agents must be members (they are; no change needed)
- **Agent choices (reversible):**
  - the January 2009 wiki revisions as the archived guides
  - the routine's mapping, schedule and logistics rules (listed in the draft)
  - masking fights that can't start
  - the guide is in `POLICIES` but not `e1_baselines()`
- **Awaiting Caleb:**
  - Q1–Q4 of the draft: schedule, selling banked produce, scope, mapping
  - prayer: (a, recommended) keep prayers out of combat for now and record it as a limitation, deciding flicking if
    prayer is ever added (on this server it makes prayer free); or (b) add prayer, and flicking, to the sim and the
    executor
  - tick manipulation: (a, recommended) leave it out (options use the server's standard delays) and record it as a
    limitation; or (b) first test live whether 2009Scape allows it, then decide

## Validation

- `uv run pytest -q`: 174 passed and 18 skipped. On their first run, two guide tests failed because their tolerances
  were too tight (one 15-minute fight gains several low levels); both were loosened, with the reason in a comment.
- Trial episodes of 4, 6 and 20 hours over several seeds, checked after each fix.
- `scripts/evaluate.py --policies scripted_guide random --seeds 10 --workers 10`: the numbers above.
- The membership and prayer findings come from reading the server source (`rl.conf`, `Prayer.java`, and a search
  for per-player members checks). They weren't tested live.

## Follow-Up

- Caleb's review: Q1–Q4, prayer and tick manipulation.
- Commit when Caleb asks.
- Then calibration, and the MaskablePPO agent with the SMDP buffer.
