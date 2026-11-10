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

### OQ-67. Where do E3's reward weights sit, given that the wealth term's scale makes them reward skill?
- **Raised:** 2026-11-10, from E2's sweep (record `m002-e2-ladder`). The reward is w_s·r_skill + w_b·r_wealth, with
  r_skill in levels and r_wealth = Δ net worth / 100,000 gp (env contract §4). ROADMAP's technical decisions gave the
  scale as "e.g. 100k GP"; it was never compared with what a policy earns.
- **What it does at 20 hours** (E1's mean reward sums, `results/summary/e1-baselines/episodes.csv`):

  | Policy | r_skill | r_wealth |
  |---|---:|---:|
  | random | 185.4 | 0.13 |
  | greedy XP/hr | 122.5 | 0.00 |
  | greedy GP/hr | 6.4 | 18.9 |
  | the guide | 323.9 | 1.29 |

  - Even greedy GP/hr's 1.89M gp is worth less than random's levels, so a level outweighs 100,000 gp.
  - **E2's agents at (.5, .5)** learned skill only. In the evaluation their wealth reward is 0.03 to 0.13 an
    episode (3,900 to 14,000 gp), against 247 to 304 for skill.
  - **E3's grid** is (1,0), (.75,.25), (.5,.5), (.25,.75), (0,1). At (.25, .75) a skill policy scores about
    0.25 × 300 = 75 against greedy GP/hr's 0.75 × 18.9 + 0.25 × 6.4 = 16. A policy that went for wealth would score
    about 16, so only (0, 1) makes wealth worth chasing. The front would be four skill points and one wealth point.
  - Rescaling the wealth term is the same as moving the weights: scale c on r_wealth gives the same policies as
    weights (w_s, c·w_b). So the question is where E3's points sit, and whether the sim's scale changes to put them
    there.
- **Options:**
  - **(a) Recommended: normalised weights, no sim change.** E3 to E6 give their weights in units of E1's best
    20-hour gain on each objective: the guide's 324 levels and greedy GP/hr's 1.89M gp (the ideal point). A shared
    helper converts them to the env's weights, keeping a level worth w_s.
    - E3's (.75,.25), (.5,.5) and (.25,.75) become env weights (.75, 4.3), (.5, 8.6) and (.25, 12.9). As shares of
      w_s + w_b, that's w_b .85, .945 and .98.
    - E4's and E6's "(.5, .5)" means the normalised point, and E5 draws normalised weights.
    - E2 stays as run, its (.5, .5) noted as rewarding skill.
  - **(b) Change the sim's scale** (for example 5,800 gp a unit, where a level and the ideal point's gp balance). It
    picks the same policies as (a), and "(.5, .5)" keeps its plain meaning. But it's a sim change: sim-v1.2 by a main
    PR, E1's reward sums change (its metrics don't), and E2's sweep ran on the old objective.
  - **(c) Keep the scale and add wealth-heavy points to E3** (for example w_b .9, .95 and .98, 5 seeds each). The
    front is denser where the trade happens, for 15 more runs (about 30 hours at 2M decisions, four at once).
  - **(d) Keep everything,** and the report says four of E3's five points reward mostly skill.
- **Decides:** Caleb (experiment design: what RQ1 to RQ3's fronts show).
- **Needed by:** Nov 12, before E3's configs.

### OQ-68. Does E2's rung 1 pass at 94.4% and 94.9% of the optimum?
- **Raised:** 2026-11-09, by rung 1's second run (record `m002-e2-ladder`). Claude proposed the bar (every seed's mean
  discounted return at least 95% of the optimum's) with rung 1's config. Caleb didn't set it.
- **The run** (`results/summary/e2-ppo-sanity-ladder/toy/`, λ 0.99, 2M decisions): 94.9% and 94.4%, 13 trainings
  where the optimum trains 22, almost no idling. It was still rising.
- **Options:**
  - **(a) Recommended: it passes, reported with its numbers.** The rung checks that the SMDP machinery learns a
    delayed investment, and 94% is far from always working's 25%. The report gives 94.4% and 94.9% and the 13
    trainings against 22, not a bare "pass".
  - **(b) It fails at 95%,** reported as such. Rung 3 and E3 go ahead anyway, since the rung doesn't gate them.
  - **(c) Rerun it longer** (4M decisions; the 2M run took about 4 minutes a seed) and judge that run at 95%.
- **Decides:** Caleb (what the report claims).
- **Needed by:** E2's PR.

### OQ-69. Do E3 to E6 train for 1M or 2M decisions a run?
- **Raised:** 2026-11-10, by E2's curves (record `m002-e2-ladder`). OQ-65 (3) (Caleb): 1M, "revisited after E2: if
  E2's curves still rise at 1M, E3 to E6 take 2M".
- **The curves** (training reward over the last 30% of training, `results/summary/e2-ppo-sanity-ladder/training/`):

  | Variant | Seed 0 | Seed 1 |
  |---|---:|---:|
  | λ 0.95, 3e-4 (the best, what E3 to E6 use) | 132.6 → 152.6 | 129.4 → 146.5 |
  | λ 0.99, 3e-4 | 134.2 → 140.8 | 133.4 → 140.1 |
  | λ 0.95, 1e-4 | 127.2 → 128.1 | 125.6 → 127.1 |
  | λ 0.99, 1e-4 | 120.9 → 123.8 | 121.0 → 122.4 |

  The best variant is the one still rising fastest. By OQ-65 (3)'s rule, E3 to E6 take 2M.
- **The cost:** E3 to E6 are 55 runs:

  | Experiment | Runs |
  |---|---:|
  | E3 | 25 |
  | E4 | 5 |
  | E5 | 5 |
  | E6a | 10 |
  | E6b | 5 |

  At about 1M decisions an hour (four runs at once), 2M is about 110 hours and 1M about 55. E4's RND and E5's
  conditioning cost more a decision. Nov 13 to 18 is 144 hours, with E4's to E6's building alongside the runs.
- **Options:**
  - **(a) Recommended: 2M, as the rule says.** E3 runs first (about 50 hours), and the others follow as they're
    built. Every run keeps its 1M checkpoint, so a 1M comparison stays possible.
  - **(b) 1M.** Half the compute, but E3 to E6 would compare agents still learning, and the report would say so.
  - **(c) 2M for E3, 1M for E4 to E6,** compared with E3's (.5, .5) at its 1M checkpoint. RQ1 to RQ3 get learned
    agents, and the rest fits more easily.
- **Decides:** Caleb (experiment design).
- **Needed by:** Nov 12, before E3's configs.
