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

### OQ-2. What options do Crafting, Agility, Herblore and Runecrafting get in sim v1, and which items join *V*?
- **Raised:** 2026-10-28, in the simulation review, which made these skills trainable from sim v1 (env contract
  §5). Fletching, the fifth, was brought into sim v0 on 2026-10-31.
- **Starting point:** option catalog §3.5's likely options: tanning, leather armour, spinning and gems; course
  laps; herbs and potions after Druidic Ritual; runes from essence after Rune Mysteries. Their items join *V* by
  catalog §9's rule.
- **Decides:** Caleb, on Claude's draft (a new option-catalog version).
- **Needed by:** before sim v1 is built, which is before E2.
- **Status:** not drafted.

### OQ-7. The sim is far below the contract's 20k decisions a second: optimize, or size E2 to it?
- **Raised:** 2026-10-31, by the week-2 benchmark (`scripts/benchmark_sim.py`; env contract §7 sets the target).
- **Measured** (masked random actions, `results/benchmark/sim-speed-20261031-1304.json`): 112 decisions a second in
  one process, 684 with 8 workers, 804 with 16 (8 cores, so the extra 8 threads add little). Caching the nearest
  bank had already raised it from 83 and 585. A 20-hour episode is about 450 decisions.
- **Where the time goes** (one process): the combat ranker recomputing the whole enemy pool after each combat
  level-up (about 60%: some 26 ms each, every third step for a random agent), the observation's candidate features
  (about 25%), and running the options themselves (about 5%).
- **Options:**
  - **(a) Recommended:** vectorize the rate model over the enemy pool (numpy, tested identical to the scalar model),
    which should roughly double the speed, to about 1.5k decisions a second with 16 workers. Then size E2's budget
    to the measured speed: at 1.5k a second, 2M decisions per run take about 25 minutes, and E2's 25 runs about 10
    hours. (How many decisions PPO needs here isn't known until the sanity ladder runs.)
  - (b) Go further toward 20k: incremental masks and features, candidates recomputed only when their inputs change,
    perhaps numba. Days of work, with an uncertain result.
  - (c) Keep today's 800 a second and size E2 to it: about 42 minutes per 2M-decision run, 17 hours for E2.
- **Decides:** Caleb (the contract's target and E2's budget).
- **Needed by:** before training starts (week 3's sanity ladder).
