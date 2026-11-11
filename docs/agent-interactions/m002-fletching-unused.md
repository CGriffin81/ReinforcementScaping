# Agent Interaction

## Metadata

- Interaction ID: m002-fletching-unused
- Timestamp CST: 2026-11-11 16:40:10 CST, the message's timestamp in the session transcript (UTC−06:00). It came in
  while the analysis data was being built (`m002-analysis-data.md`).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: ANSWERED. What to do about it is Caleb's decision, asked after this.
- Commit: on `tooling/analysis-data`, with `m002-analysis-data`. No code changed.

## Full Prompt

> Why don't any of the runs do anything with fletching?

## Response Summary

Fletching is reachable two ways, and the agents use neither:

1. **Fletching's own options** (`skill_fletching_xp1`, `xp2`, `gp1`, `gp2`) work at a bank from inputs already held
   (`FletchAtBank.available`: logs, bowstrings and so on, carried, banked or noted). A fresh character holds none.
   The agents' woodcutting burns its logs, and they rarely buy logs on the GE. So the options are closed nearly all
   the time:
   - E2's best run: `xp1` open in 1.0% of decisions, `xp2` 0.1%, the gp options about never.
   - E3's skill-only (1, 0) seed 0: any fletching option open in 5.9% of its first 100,000 decisions (exploration
     buys the odd batch of logs) and 1.2% of its last 50,896. It chose one 101 times early and 4 times late, and
     bought logs 282 times early and 58 late.
   - E3's (.75, .25) seed 0: the same, 4.9% open early and 0.4% late.
2. **Woodcutting's chop-and-fletch paths** (`wc_<tree>_fletch`) compete for woodcutting's two XP slots, which are
   ranked by XP/hr counting the processing's XP (`rlscape/sim/skilling.py`). Chop-and-burn earns more total XP than
   chop-and-fletch at these levels, so the slots offer burn paths:
   - E2's agent ran `wc_oak_burn` and `wc_logs_burn` only;
   - E3's (1, 0) and (.75, .25) agents ran only `wc_oak_burn`, `wc_logs_burn` and `wc_willow_burn`.

So Fletching stays at level 1. In E2's replay it's 1 at every checkpoint, while Woodcutting reaches 32 to 37. The
scripted guide, which picks paths to raise its lowest skill, cuts arrow shafts (`wc_logs_fletch`) and reaches
Fletching 11. None of E1's baselines has fletching in any episode's five most chosen options.

Both ways also need a knife held (chop-and-fletch: `skilling.py`'s check of the inventory; the bank paths: carried or
banked), which a fresh character takes from the Lumbridge Castle spawn (`take_knife`). The agents do take it
sometimes: E2's best run 361 times in its first 100,000 decisions and 46 to 96 in each later bin (about 1,000
episodes a bin); E3's (1, 0) seed 0 514 times in its first 100,000 and 26 in its last 50,896. Holding it doesn't
change the woodcutting slots, which chop-and-burn still wins.

This isn't a bug: the mask and the slots do what they were designed to. To fletch, an agent needs a plan of two or
three steps (take the knife; get logs, banked from a woodcutting path that keeps them or bought on the GE; then
fletch), and it hasn't learned one. That is a finding for RQ2 (investments with a delayed payoff). Since every skill's level counts the same, the
skill-only agent leaves cheap Fletching levels unused.

## Documentation Changes

- This record only. Where it goes in the docs (the decision log, `docs/post-project-gaps.md`, the report) waits for
  Caleb's decision.

## Code Changes

- None.

## Infrastructure Changes

- None. E2's and E3's decision logs and E2's replay page were only read. Nothing in E3's worktree changed.

## Decisions

- **Agent recommendation:** keep the sim as it is (frozen at `sim-v1.1`, with E3 half trained), and report it:
  - as a finding: the agents never learn get-logs-then-fletch;
  - as a gap in `docs/post-project-gaps.md`: an option that buys a recipe's inputs and crafts them, or woodcutting
    slots that always offer each counterpart (burn, fletch).
- **User decision:** pending.

## Validation

- **Mask rates** from the decision logs' packed masks: E2's best run, every 4th part (250,448 decisions); E3's two
  runs, their first two and last two parts.
- **Paths** from the logs' option records.
- **Levels** from E2's replay page (each decision's skill levels).

## Follow-Up

- **Caleb:** decide whether to keep it as a finding and a post-project gap (recommended), or change the sim.
