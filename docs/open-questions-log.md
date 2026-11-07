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
  laps; herbs and potions (Druidic Ritual) and runes from essence (Rune Mysteries), both quests complete from the
  start since 2026-11-06 (Caleb: quests are out, flagged complete). Their items join *V* by catalog §9's rule.
- **Decides:** Caleb, on Claude's draft (a new option-catalog version).
- **Needed by:** before sim v1 is built, which is before E2.
- **Status:** not drafted.

### OQ-7. The sim is far below the contract's 20k decisions a second: optimize, or size E2 to it?
- **Raised:** 2026-10-31, by the week-2 benchmark (`scripts/benchmark_sim.py`; env contract §7 sets the target).
- **Measured** (masked random actions, `results/benchmark/sim-speed-20261031-1304.json`): 112 decisions a second in
  one process, 684 with 8 workers, 804 with 16 (8 cores, so the extra 8 threads add little). Caching the nearest
  bank had already raised it from 83 and 585. A 20-hour episode is about 450 decisions.
- **Since planned routes** (2026-11-01, `results/benchmark/sim-speed-20261101-1557.json`): 78 decisions a second in
  one process, 284 with 4 workers, 553 with 16, about 30% slower (a path is remembered once asked for; each worker
  also builds the map's graph, about 4 s). The options' estimates below scale down by as much.
- **Since the transports** (2026-11-01, `results/benchmark/sim-speed-20261101-1838.json`): 69 decisions a second in
  one process and 499 with 16 workers, another 10% slower (each walk also weighs the teleports and boats the
  character can use).
- **Since the unreachable rule and the home teleport's cooldown** (2026-11-01,
  `results/benchmark/sim-speed-20261101-2042.json`): 71 a second in one process and 489 with 16 workers, unchanged.
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

### OQ-15. Should the observation show when the home teleport is ready?
- **Raised:** 2026-11-01, building the home teleport's 30-minute cooldown (decision log, "the home teleport waits 30
  minutes").
- **Now:** the agent doesn't see the cooldown. The candidates' travel (env contract §3) counts the teleport only when
  it's ready, so it shows the effect now, but not how long until it's ready again. The rest of the state can't tell
  it either.
- **Options:**
  - **(a) Recommended:** one more observation feature: the minutes until the home teleport is ready, over 30 (0 when
    ready). Env contract v1.11. It decides how long the next trips take, so a policy can plan around it.
  - (b) Leave it out: the travel features already change when it's ready.
- **Decides:** Caleb (the observation; env contract §3).
- **Needed by:** before training starts (week 3's sanity ladder).

### OQ-16. Which ways the travel model lacks should it get, and when?
- **Raised:** 2026-11-01, making places with no way unreachable (OQ-12, answered). Caleb: some places that no walk,
  teleport or boat reaches can be reached with an item or as part of a quest.
- **Now unreachable** (231 of the sim's 2,792 places; the areas are in the decision log): mostly behind quests
  outside the set, and pens and cells. But some have a way the model doesn't know yet:
  - behind a quest now complete from the start (2026-11-06): Crandor (Dragon Slayer; the way back is the wall
    from Karamja's volcano)
  - an Agility shortcut or an item: the moss giant island by Brimhaven (a rope swing), the Mage Arena (a lever)
  - unclear, perhaps the planner's gaps: Wilderness spots, the ice giants by White Wolf Mountain, Tree Gnome Village,
    a dwarf by Ice Mountain, north of Varrock, the Kharazi jungle
  - Upstairs and underground places keep the straight-line estimate until their stairs and ladders are mapped (on the
    plan already).
- **Options:**
  - **(a) Recommended:** check the unclear places on the server first (walk there with the bridge; a few minutes
    each), then add each way with what needs it: Crandor and the lever as transports now, Agility shortcuts with
    Agility (sim v1). Since every quest the server has is complete from the start, the areas they open (decision log,
    2026-11-06) get the same check: a way only where the ranker would send a character in 20 hours.
  - (b) Only the quests' ways in sim v1; leave the rest unreachable.
- **Decides:** Caleb (which content the agent can reach).
- **Needed by:** sim v1, before E2.

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

### OQ-29. Which armour stops Ava's devices?
- **Raised:** 2026-11-07. Caleb noted that the devices don't work while any metal item is worn. The server's rule is
  narrower (decision log).
- **The server's rule** (`AvasDevice.isInterfered`, `RangeSwingHandler.getDropRate`):
  - Only the chest piece counts, and only if its worn model is one of three (`AvasDevice.metalBodies`). That's 38
    pieces (`data/ava_interference.csv`): the metal platebodies and chainbodies, trimmed, gilded, Zamorak and Guthix,
    white, and the Temple Knight hauberks.
  - It leaves out the iron chainbody, the Saradomin platebody and the dragon chainbody, whose models aren't listed,
    and every helm, legs, shield, glove and boot.
  - Interference stops only the device's 80% catch. The other 20% of shots still take the device's narrower roll, and
    the accumulator still gathers those.
  - Ava's own dialogue on the server says the device won't work with "certain metallic chest armours".
- **Now:** the server's rule on both backends. A ranger wearing a device leaves interfering chest armour off, so
  in the sim the device always works.
- **Options:**
  - **(a) Recommended:** keep the server's rule. Both backends agree, and the loadout keeps the device working.
  - (b) Fix the server's gaps (a fork change): interference stops the whole device, and every metal chest piece
    interferes, adding the three left out. Still chest only, as Ava says.
  - (c) Caleb's rule (a fork change): any metal item worn stops the device. It needs a definition of metal, such as
    the metals in item names (bronze to dragon). A ranger wearing a device would then leave all metal off.
- **Decides:** Caleb (a game rule on both backends).
- **Needed by:** before the combat gate closes.
