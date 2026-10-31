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

### OQ-3. Prayer flicking: the live test's fork change, then whether and how agents use prayer
- **Raised:** 2026-10-30. Caleb: "We will implement prayer flicking and 3-tick woodcutting if they can be used",
  after a live test. Tick manipulation has been tested (no method works on 2009Scape). The prayer-flicking test
  needs a bridge command that toggles a prayer, which is a fork change.
- **From the source:** `Prayer.tick()` drains only on even counts of consecutive prayer ticks, so flicking would
  make prayer free on this server.
- **Questions:** (a) the go-ahead for the prayer-toggle command; (b) after the test, how prayer enters the agents'
  options. Neither the sim nor the planned executor uses prayers in combat yet.
- **Decides:** Caleb.
- **Status:** next in the plan.

### OQ-4. Bridge commands for the rest of the player's paths
- **Raised:** 2026-10-30 (option catalog §8, server side).
- **Question:** the go-ahead for the fork changes that shop buys, putting gear on, bank withdrawals and
  `bank_deposit_worn` need. Each goes through the player's path, as the rules require.
- **Decides:** Caleb, per change.
- **Needed by:** calibration (`scripts/calibrate.py` runs every option through the bridge) and `ServerEnv`
  (week 6).

### OQ-5. Freeze the server version once calibration starts?
- **Raised:** 2026-10-28, with the upstream sync (fork `master` at upstream `f279da8`). Until it's decided, each
  sync needs Caleb's approval (`CLAUDE.md`).
- **Recommendation:** yes (Claude). An upstream change after calibration could move the server away from what the
  sim was calibrated against.
- **Decides:** Caleb.
- **Needed by:** the start of calibration.

### OQ-6. Do the repositories need to be public for the course submission? (*deferred*)
- **Raised:** 2026-10-05. On 2026-10-28 Caleb decided that both repos stay private for now.
- **Reopens:** when the submission's format is known. `Requirements.md` doesn't say.
- **Note:** a public fork has to include its source (AGPLv3).
- **Decides:** Caleb.
- **Needed by:** the report, due 2026-11-30.
