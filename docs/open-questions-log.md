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

### OQ-80. Train E3 to E6 on the GPU?
- **Raised:** 2026-11-11, Caleb: "Why are the experiments not running on GPU?" and "What are the projected time
  savings on running all of the experiments on GPU instead of CPU?" (`m002-gpu`).
- **How it got here:** Caleb chose CUDA torch on 2026-11-08 (the RL stack), and the first training measurements ran
  on the GPU. Claude then set every training config to `device: cpu` on 2026-11-09 (the tooling, E2 onwards), for
  bit-for-bit repeatability and because the simulator, not the network, takes the time. That choice wasn't put to
  Caleb.
- **Measured** (2026-11-11, the four E3 runs training at the same time):
  - **The PPO update** for one rollout at E3's settings (1,024 decisions, batch 1,024, 4 epochs, 256 × 256):
    1.12 s on the CPU (2 threads, as the runs), 0.11 s on the RTX 3050.
  - **A rollout** takes about 20 s in the runs (50 to 54 decisions a second each, four at once). So the update is
    about 5% of a run, and the rest is the simulator in the env processes, which the GPU can't take.
  - **Repeatable on the GPU:** two tiny real runs (512 decisions, 2 updates) gave the same actions and bit-identical
    weights, with and without `torch.use_deterministic_algorithms`. The earlier claim that a GPU run isn't
    repeatable was wrong for this network; deterministic mode guarantees it (an op that isn't raises an error).
- **Projected saving:** about 5 to 7% of training time: the update (about 1 s a rollout), and a little more from the
  policy's forward passes leaving the CPU to the simulator. Over the queue's remaining 110 to 125 hours, about 6 to 8
  hours.
- **Options:**
  - **(a) Recommended: switch now, all 50 runs on the GPU.** `device: cuda` in the five configs, deterministic mode
    in the trainer for CUDA runs, and E3's four seed-0 runs (started 18:01) restarted, so every run of an experiment
    shares a config. It costs those four runs' first hour, about an hour's work, and saves about 6 to 7 hours.
  - **(b) Switch the 46 runs not yet started;** E3's four seed-0 runs finish on the CPU. It saves about 7 hours, but
    E3's runs then have two configs (the device differs), which its summary shows.
  - **(c) Stay on the CPU.** No change. The queue finishes about 6 to 8 hours later, with about 2 days still before
    the analysis (Nov 19).
- **Decides:** Caleb.
