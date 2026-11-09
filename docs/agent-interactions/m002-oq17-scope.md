# Agent Interaction

## Metadata

- Interaction ID: m002-oq17-scope
- Timestamp CST: 2026-11-09 08:04:42 CST (the prompt), from the session transcript's timestamp (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: DECISION RECORDED; OQ-1 (RQ5) and OQ-50 (the peer review's form) await Caleb
- Commit: the main repo commit after `dc92982` (branch `sim-v0`) that adds this record (`m002-commit-all`)

## Full Prompt

> OQ 17 - Let's pair things down a bit to option a'. I still want to answer all of the research questions we
> initially identified. However, I want to make sure that the peer review is as simple as it can be. I do not envy
> anybody who is handed this project to review, as they may not be overly aware of what is important for them to look
> at and they may get lost in the ocean of code that has been created for these experiments.

## Response Summary

- **Checked (a′) against the proposal's research questions** (RQ1 to RQ5, read from
  `CS898BG_RL_Project_Proposal_2009Scape.pdf`). Two gaps:
  - **RQ4** asks about three things: an exploration bonus, the discount factor and potential-based shaping. (a′)
    answered it with E3 (RND) alone, the γ_hr sweep only if compute allowed, and PBRS cut. So E5's γ_hr sweep and
    PBRS are now in, and only E5's option granularity stays cut, since no research question asks about it.
  - **RQ3's second half** (one preference-conditioned agent against separate agents) was (a′)'s first part to cut.
    Now it stays.

  So if time runs short, depth gives way instead of a research question.
- **RQ5** (learned micro-options, "exploratory, time permitting") can't be answered as asked: it needs a tick-level
  environment, 1.5 to 2 weeks. OQ-1 is rewritten around it:
  - (C′) recommended: bound RQ5 from the existing pieces, in about half a day:
    - the scripted prayer flick is already as good as a flick can be (tested live);
    - E2's walking share and the measured overhead per click bound what click-ahead pathing could save;
  - (D) report it as not attempted.
- **The cost:** about 60 to 70 runs, which is 2.5 to 6 days of the machine within Nov 12 to 21, and about 14 days of
  building (half a day more than (a′), for PBRS's potential).
- **The peer review:** the repo has no README. It holds about 29,000 lines of Python, of which the RL layer is about
  1,400 (5%). New OQ-50 asks what the reviewer gets:
  - (a) recommended: the whole repo at a tag, with a `README.md` that's a two-page reviewer's guide:
    - the claims mapped to their evidence;
    - a reading path through the 8 to 10 files of the RL layer;
    - what to skip and why it can be trusted;
    - a 10-minute check with no server or GPU;
  - (b) a slim copy;
  - (c) the report alone.

  Meanwhile, each experiment gets one config and one command, and each figure comes from committed summaries. That
  suits every option.
- **The schedule** (in ROADMAP weeks 6 to 8):
  - Nov 9 to 10: the freeze and tooling;
  - Nov 11 to 12: the ladder and E1;
  - Nov 13 to 18: E2, E3, E5 and the weight-conditioned PPO;
  - Nov 19 to 21: the analysis;
  - Nov 22 to 25: the draft and the reviewer's guide;
  - Nov 26: peer review;
  - Nov 27 to 30: revisions.

## Documentation Changes

- `docs/decision-log.md`: "Decided: OQ-17, the finishing scope is (a′) with every research question answered, and a
  simple peer review (Caleb)". It gives the question, the options, Caleb's answer and what it changes, the plan
  question by question, the compute and what stays cut. It's appended at the end, after the Runecrafting session's
  uncommitted entries, which were left as they were.
- `docs/open-questions-log.md`:
  - OQ-17 deleted;
  - OQ-1 rewritten for RQ5 under (a′), with options (C′) (recommended), (D), (C), and (A) or (B);
  - OQ-50 added (the peer review's form), after OQ-49.
- `ROADMAP.md`:
  - week 2's status line now ends with OQ-17's answer (a sentence inside the Runecrafting session's uncommitted hunk,
    which it was told about);
  - a note at the top of §4;
  - weeks 6 to 8 replaced by the finishing plan;
  - §5's midpoint fallback marked as superseded.
- `docs/agent-interactions/m002-viability-reassessment.md`: its status now points here.
- This record.

## Code Changes

- None.

## Infrastructure Changes

- None. No server was started.

## Decisions

- **User decisions (Caleb):**
  - OQ-17: (a′);
  - every research question answered;
  - the peer review as simple as it can be.
- **What Claude read into "every research question":** RQ4 in full (the γ_hr sweep and PBRS in), and RQ3's second
  half kept. So the cuts go by depth, never by research question. Both follow from the proposal's own wording of the
  questions. Caleb can correct this.
- **Agent recommendations, for Caleb:**
  - OQ-1 (C′), a bound for RQ5;
  - OQ-50 (a), the whole repo at a tag with a README that's a reviewer's guide.

## Validation

- **The research questions' wording** was read from the proposal PDF (pypdf).
- **The line counts** come from `wc -l` over the tree on 2026-11-09.
- **The compute and day counts** are Claude's estimates, built on the throughput measured in
  `m002-viability-reassessment`. They aren't measured.

## Follow-Up

- **Caleb:**
  - OQ-1 (RQ5) and OQ-50, neither needed before Nov 19;
  - OQ-49, before tomorrow's freeze;
  - the env contract's versions to confirm (v1.18, and v1.22 onward) and option catalog v1.4;
  - the two GAE choices in `m002-smdp-ppo`.
- **Claude, next:** the sim freeze's speed checks, the mask speed-up, then `scripts/train.py`.
