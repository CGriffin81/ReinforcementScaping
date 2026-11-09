# Open Questions Log

Questions that are still undecided. Every new undecided question goes here when it comes up, including ones that
can't be decided yet (marked *deferred*, with what reopens them). When a question is answered, it moves to
`docs/decision-log.md` with its options and the answer, and its entry here is deleted. So answered questions live
only in the decision log, and open ones only here.

Each entry gives when and where the question was raised, who decides, what it blocks or when it's needed, the
options with Claude's recommendation, and its status. Ids aren't reused.

Started 2026-10-31 (Caleb), from a review of the documentation.

---

### OQ-1. Which stretch experiment (E7), if any?
- **Raised:** 2026-10-05, in the plan. The options are compared in `ROADMAP.md` Appendix B.
- **Options:** A, an LLM planner (Voyager-style); B, DreamerV3; C, learned micro-options (RQ5); D, none.
- **Recommendation:** A (Claude). Caleb accepted it tentatively on 2026-10-28: it's confirmed at the midpoint,
  and only if E1–E6 are solid by then.
- **Decides:** Caleb, at the week-5 midpoint review (Nov 2–8).
- **Blocks:** week 7's plan.

### OQ-17. Peer review is in three weeks: what scope does the project finish with?
- **Raised:** 2026-11-05, by Caleb: something must go to peer review in three weeks (about Nov 26), at this tier of
  support. Record `m000-feasibility-review`.
- **Where it stands:** week 5 of 8, and the sim (week 2's work) is still being finished: sim v0 has 13 skills, combat,
  buying and the GE; gathering, travel and banking are calibrated; combat isn't. Weeks 3 to 5 haven't started: no RL
  stack installed, no SMDP buffer or training script, no E2 to E5. Nor have sim v1 (21 quests, four skills),
  `ServerEnv` or E6. Claude's estimate for all of it: six weeks or more at the recent pace.
- **Options:**
  - **(a) Recommended:** freeze the sim at v0 now (a day of combat calibration at most); then masked PPO with the
    SMDP buffer, E2 (five weightings × three seeds), one RQ4 experiment (RND or γ with PBRS), a weight-conditioned
    PPO in place of Envelope Q (RQ3's second half), and the calibration results as the sim-to-real evidence in place
    of E6. Cut sim v1, E4 as planned, E6 beyond a spot check, and E7. A draft for peer review by about Nov 24.
  - (b) Smaller: E1 and E2 with the strategy analysis (RQ1, RQ2, RQ3's first half) and nothing else.
  - (c) The full scope: not feasible in three weeks, in Claude's estimate.
- **Decides:** Caleb (scope and what the report claims).
- **Status:** *deferred* (Caleb, 2026-11-05): "Let's continue with the current plan for now and reevaluate on
  Sunday." Caleb hopes calibration was an unusually heavy lift and is nearly done. Reopens Sunday, 2026-11-08.
- **Since:** Caleb cut quests on 2026-11-06 (every quest the server has is complete from the start), so sim v1 is
  the four skills only. The level-3 start stays.
