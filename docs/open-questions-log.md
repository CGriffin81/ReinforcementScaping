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

### OQ-43. The caster held "under attack" in the middle of a fight: fight the holder back at once?
- **Raised:** 2026-11-08, `m002-spade-zero-hitpoints`, from the spade traces. When a possessed pickaxe engaged the
  character in the middle of a spade fight, the casts on the spade were refused ("You're already under attack!",
  `MapZone.checkMulti`). The runner's magic loop keeps recasting until `STUCK_TICKS` (30 ticks without XP) walks it
  back, and only then fights the other monster. That cost 50 to 124 ticks a run (3% to 8%) in the three good spade
  runs. In the sim, such an engagement is a kill in the fight's plan with no wait (`FightNeighbours`).
- **Options:**
  - **(a) Recommended:** the runner does as a person who reads the message does: when a cast on its target is
    refused and a monster of another kind is attacking it, it casts on that monster at once, and takes up its
    target again after. Also, `STUCK_TICKS` waits for damage (hitpoints XP), not any XP, so a target that takes no
    damage is left (a 0-damage swing still gives base Magic XP).
  - (b) Keep the runner as it is and give the sim the same wait, measured (a sim model change).
  - (c) Keep both as they are, and report the bias at sites with neighbours.
- **Decides:** Caleb (it changes what the server side measures).
- **Blocks:** no gate case since the spades became hazards (OQ-42): no other magic case in the fit or check sets
  meets a monster of another kind. It matters for server runs at sites with neighbours (E6's spot checks).

### OQ-45. Should the cosmic altar also be reached through Zanaris?
- **Raised:** 2026-11-08, building Runecrafting (sim v1, `rlscape/sim/runecrafting.py`). Record
  `m002-runecrafting`.
- **The problem:** the cosmic ruins are in Zanaris (2406, 4375). A character enters Zanaris by the shed in Lumbridge
  Swamp with a dramen staff wielded (`LostCityListeners`; Lost City is complete from the start). The travel model has
  no map of Zanaris: it's off the surface map, where route planning only has a straight-line estimate. So `rc_cosmic`
  isn't built; the other nine runes' ruins are. The dramen staff has no January 2009 GE price in
  `data/prices_v2.csv`; a character would cut one from the dramen tree on Entrana.
- **Options:**
  - **(a) Recommended:** the cosmic altar only by the Abyss's cosmic rift, once the Abyss is built (the draft's §5).
    No Zanaris route. Cosmic runes then need the Abyss's skull, its monsters and an obstacle.
  - (b) Zanaris too: check the shed on the server, export Zanaris's collision map, add the shed as a travel link,
    and give the dramen staff a way in (a set GE price, as the barbarian rod's, or the Entrana tree). About a day.
  - (c) Leave cosmic runes out entirely.
- **Decides:** Caleb (scope).
- **Blocks:** `rc_cosmic` only.
- **Status:** open.
