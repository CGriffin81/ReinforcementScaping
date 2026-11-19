# Open Questions Log

Questions that are still undecided. Every new undecided question goes here when it comes up, including ones that
can't be decided yet (marked *deferred*, with what reopens them). When a question is answered, it moves to
`docs/decision-log.md` with its options and the answer, and its entry here is deleted. So answered questions live
only in the decision log, and open ones only here.

Each entry gives when and where the question was raised, who decides, what it blocks or when it's needed, the
options with Claude's recommendation, and its status. Ids aren't reused.

Started 2026-10-31 (Caleb), from a review of the documentation.

---

### OQ-89. What does the report say causes the looping runs?
- **Raised:** 2026-11-18, at `m002-collapse-check`'s seventh run check (the decision log's finding of that day). Logged
  here on 2026-11-19 (`m002-outstanding-tasks`).
- **Found** (36 of the 50 reruns then): the rerun's two changes, no horizon bootstrap and the 100-tick floor, ended the
  loops at γ_hr 0.5 and 0.9 (E6a: from 3 of 7 runs to none). At 0.99, 8 of 29 runs end looping, against 4 in the first
  round, and E3's alone went from 1 of 20 to 7. The floor costs a decision at least 1.15% of its value at 0.5 and
  0.017% at 0.99. `m002-loop-cause` gave "a trainer bug that was fixed" as part of the cause, and at 0.99 the counts
  don't support it.
- **Options:**
  - **(a) Recommended: report the counts by discount, for both rounds, and say the cause at 0.99 is untested.** Name
    the candidates: the horizon bootstrap's removal, and for E3 the sim's death-budget cap. Don't call the loops a bug
    that was fixed. No more training.
  - **(b) Test it first:** train about four of E3's looping configurations again with the horizon bootstrap back on and
    the floor kept, on sim v1.4. If they stop looping, the bootstrap's removal is the cause. With four runs at once,
    about 8 to 10 hours on the machine, after the evaluations. The analysis can run beside it.
  - **(c) Keep `m002-loop-cause`'s framing** (a trainer bug and a learner limitation) as it is.
- **Decides:** Caleb (what the report claims).
- **Needed by:** the draft (Nov 22). Only (b) has to start sooner, as soon as the evaluations are done.

### OQ-90. Which rule counts a run as looping, in both rounds?
- **Raised:** 2026-11-18, at `m002-collapse-check`'s seventh run check. Logged here on 2026-11-19
  (`m002-outstanding-tasks`).
- **Found:** the run checks count a run as ending looping when its last 100k-decision block averages over 1,000
  decisions an episode. By that rule, 10 of the first round's 50 end looping. The decision log's 2026-11-16 entry
  counted 8: it left out E6a's γ_hr 0.5 seed 0 (1,003 in its last block) and γ_hr 0.9 seed 2 (over 1,000 only in its
  last block).
- **Options:**
  - **(a) Recommended: the run checks' rule,** applied the same way to both rounds. The report gives two counts:
    runs that pass the marker in any block, and runs that end over it.
  - **(b) That rule plus a second test:** most of the last part's decisions short with no effect (say over half). This
    would drop marginal runs like γ_hr 0.5 seed 0.
  - **(c) The 2026-11-16 entry's count,** with its two exceptions written down.
- **Decides:** Caleb (what the report claims).
- **Needed by:** the final census, after the evaluations; the report's counts come from it.
