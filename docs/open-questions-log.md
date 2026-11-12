# Open Questions Log

Questions that are still undecided. Every new undecided question goes here when it comes up, including ones that
can't be decided yet (marked *deferred*, with what reopens them). When a question is answered, it moves to
`docs/decision-log.md` with its options and the answer, and its entry here is deleted. So answered questions live
only in the decision log, and open ones only here.

Each entry gives when and where the question was raised, who decides, what it blocks or when it's needed, the
options with Claude's recommendation, and its status. Ids aren't reused.

Started 2026-10-31 (Caleb), from a review of the documentation.

---

### OQ-1. Which stretch experiment (the proposal's E7), if any, and how is RQ5 answered?
- **Raised:** 2026-10-05, in the plan. The options are compared in `ROADMAP.md` Appendix B. Caleb tentatively
  accepted A on 2026-10-28, to be confirmed at the midpoint and only if the proposal's E1–E6 were solid by then.
- **Now (2026-11-09):** OQ-17's (a′) leaves no week for a stretch, and no experiment had run. Caleb wants every
  research question answered. RQ5 asks: "Do learned low-level options (click-ahead pathing, prayer flicking) improve
  high-level results over scripted versions?" The proposal marked it "exploratory, time permitting". Only C answers
  it as asked, and C needs a tick-level environment on the server: 1.5 to 2 weeks (Appendix B), more than (a′)'s
  slack.
- **Options:**
  - **(C′) Recommended: bound RQ5 instead of testing it, with no new environment.** About half a day, during the
    analysis (Nov 19 to 21).
    - **Prayer flicking:** a learned flick can't beat the scripted one. The scripted flick never drains prayer and
      gets the prayer's full effect (tested live on this server, env contract v1.8), so it's already the best a flick
      can do.
    - **Click-ahead pathing:** E3's decision logs (the reward-weight sweep, in OQ-63's numbers) give the share of
      game time spent walking. The travel model's measured overhead per click gives the part of that walking a
      perfect click-ahead could save, at most.
    - The report says this is a bound, not a test of learned options.
  - **(D) None:** the report says RQ5 wasn't attempted, as "time permitting" allows, with what it would take. It goes
    in `docs/post-project-gaps.md`.
  - **(C) Learned micro-options as planned:** 1.5 to 2 weeks. It doesn't fit.
  - **(A) the LLM planner or (B) DreamerV3:** these add to RQ1, not RQ5, and (a′) has no room for them.
- **Decides:** Caleb (what the report claims).
- **Needed by:** Nov 19, the analysis days. Nothing before then waits on it.

### OQ-50. What does the peer reviewer get, and how is it made easy to review?
- **Raised:** 2026-11-09, in Caleb's answer to OQ-17: "I want to make sure that the peer review is as simple as it can
  be. I do not envy anybody who is handed this project to review, as they may not be overly aware of what is
  important for them to look at and they may get lost in the ocean of code." Record `m002-oq17-scope`.
- **Found:** the repo has no README.
  - **Its size:**
    - about 29,000 lines of Python (`rlscape/` 14,700, `scripts/` 6,600, `tests/` 7,800);
    - 1,700 lines of Kotlin in the fork's `content/rl/`, on top of the server itself;
    - 8,500 lines of docs and 134 interaction records.
  - **The RL layer** (`envs/`, `agents/`, `baselines/`, `eval/`) is about 1,400 lines, 5% of the Python. With
    `train.py`, RND, PBRS, the weight-conditioned agent and the analysis it may reach about 3,000.
  - **Everything else** is the simulator and its calibration. The results rest on it, but a reviewer can take it on
    the evidence of the gate's table and the tests.
- **Not known (Caleb):** what the course's peer review covers (the report, the code or both), and how long a
  reviewer has.
- **Options:**
  - **(a) Recommended: the whole repo at a tagged commit, with a `README.md` that's a two-page reviewer's guide.**
    The report gets the same map as a half-page appendix. The guide has four parts:
    - **What the report claims:** one table that takes each research question and hypothesis to its result, the
      figure or table, the command that rebuilds it, and the code behind it.
    - **A reading path:** the 8 to 10 files of the RL layer, in order, with their sizes.
    - **What to skip, and why it can be trusted:** the server fork, the bridge, `gamedata/`, `combat/`, `sim/`'s
      mechanics and the calibration scripts. The gate's table per option and the tests stand in for them.
    - **A 10-minute check with no server or GPU:** the SMDP tests, the figures rebuilt from committed summaries, and
      a short training run.
  - **(b) A slim review copy:** the RL layer, the results and the guide, in a separate branch or archive. There's less
    to look at. But it hides the simulator the results depend on, can't run training, and is a second copy to keep in
    step.
  - **(c) The report alone,** with a link to the code and no guide. It's the least work, but it leaves the reviewer
    lost in the code.
- **Decides:** Caleb.
- **Needed by:** Nov 22, when the guide is written alongside the draft. Nothing before then waits on it, since one
  config and one command per experiment suits every option.

### OQ-79. E4's centred RND bonus drifts below zero while the predictor learns: centre it on a recent mean?
- **Raised:** 2026-11-11, when E4's own tests ran on sim v1.2 before E4's restart (`m002-restart-v1.2`).
  `tests/test_rnd.py`'s check that the centred bonus averages about zero (|mean| < 0.5 × its spread) failed: on 64
  bonuses after the first rollout, the mean is −0.53 spreads and 55 of the 64 are negative. On v1.1's episodes the
  same check had passed.
- **Why:** the bonus is coef × (error − μ) / σ, with μ and σ the predictor error's running mean and spread over
  every decision so far (`RunningMeanStd`, a cumulative mean). The predictor trains every rollout, so its errors fall,
  and the current error sits below the all-time mean. While it learns, the centred bonus is a small cost on every
  decision, the opposite of the per-decision pay that centring was chosen to remove (OQ-72 (b)). The bias fades about
  as 1/t as the errors level off, but it's there through the early part of every run, where RND is meant to matter
  most.
- **Options:**
  - **(a) Recommended: centre on a recent mean,** an exponential moving average of the error over about the last 10
    rollouts (σ likewise). The bonus then averages about zero at every stage of training, as OQ-72 (b) meant. It's a
    few lines in `rlscape/agents/rnd.py`, with the test kept as it is.
  - **(b) Keep the cumulative mean** as built, and report the early drift.
  - **(c) Don't centre** (Burda et al.'s way). It's positive everywhere, which pays for short decisions: the reason
    OQ-72 chose (b).
- **Blocks:** E4's runs. The training queue was started on 2026-11-11 without E4 (E3, E6a, E6b and E5's 45 runs).
  E4's 5 runs join it once this is decided; restarting the queue with E4 added leaves the runs it's training alone.
- **Decides:** Caleb.
