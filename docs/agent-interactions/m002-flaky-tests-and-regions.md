# Agent Interaction

## Metadata

- Interaction ID: m002-flaky-tests-and-regions
- Timestamp CST: 2026-11-08 17:01:53 CST (the prompt), 17:02:41 CST (the message during the turn) and 17:33:55 CST
  (the answer to Claude's question), from the session transcript's timestamps (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: DONE (the two flaky tests fixed; the region fix built and the combat sets re-checked; Crafting's inputs in
  *V*)
- Commit: the earlier work is fork `0af2cc4` (branch `rl`) and main repo `2ef7288` (branch `sim-v0`), both pushed; this
  turn's work is fork `321d759` (the region fix) and the main repo commit after `2ef7288`, both pushed

## Full Prompt

> Commit and push the changes, then continue with implementation.

During the turn:

> Do this task here: “Harden two flaky live bridge tests”

Claude's question during the turn, and Caleb's answer: on how to handle the region gap (below), "Fix in the fork
(Recommended)".

## Response Summary

- **Committed and pushed:** fork `0af2cc4` (a dead RL character respawns at the home location) and main repo `2ef7288`
  (Crafting in the sim, and the submodule pointer).
- **The hand-cast test's flake:** a cow keeps the damage an earlier run left, and one at 1 or 2 hitpoints died to the
  first wind strike. The test now casts at a cow at its full 8 hitpoints.
- **Found on the way: an RL character kept only its own map region active.** `AIPlayer.update` does nothing, so
  `MapChunkRenderer`, which keeps a client's view active, never ran. Monsters across a region boundary stood frozen
  and couldn't be attacked: 65% of the combat sites have a boundary within 15 tiles. Caleb chose the fork fix:
  `RLPlayer.update` keeps the regions in a client's view active, as a human's are.
- **The ranger test's flake:** the character died on the safespot. The likely cause is the click landing a tick after
  the reading, so the moss giant could step out of shot and the ranger walked after it, with nothing to walk it back.
  The giant's tile holds from only 51.5% of its wandering. The test now clicks back onto the tile, as a person does,
  and uses the ogre at (2504, 2984), whose tile holds from all its wandering.
- **The re-check** of the combat calibration sets after the fix: see Validation.
- **Built: Crafting's inputs in *V*** (sim v1, OQ-2's Choices A (a) and I (a)): 25 GE buys, 18 new items, *V* 297.

## Documentation Changes

- `docs/decision-log.md`: "Decided and built: RL characters keep the regions in a client's view active (Caleb); the two
  flaky live tests explained" (with the question's options and Caleb's answer) and "Built (sim v1, Crafting part 3):
  Crafting's inputs in *V* and the GE's buys".
- `docs/env-contract.md`: v1.24, to confirm (1,828 actions, 2,801 features).
- `docs/option-catalog.md`: §9's sim v1 items and size row; the v1.4 note.
- `docs/sim-v1-skills-draft.md`: the Crafting items as built.
- `CLAUDE.md`: the RL character keeps the regions in a client's view active. `ROADMAP.md`: the status line.
- This record; the Commit field of `m002-commit-crafting` (before the commit).

## Code Changes

- **Fork** `Server/src/main/content/rl/RLPlayer.kt`: `update` (the regions of the client's build area count it as a
  viewer and stay active) and `clear` (it stops viewing them on despawn).
- `rlscape/sim/buying.py`: `CRAFTING_INPUTS` (from `crafting.inputs()`) in `GE_ITEMS`, their lots, the needle and
  chisel as tools.
- `data/vocabulary.csv`: 18 items; `rlscape/vocabulary.py`: its docstring.
- **Tests:**
  - `tests/test_bridge_inputs_live.py`: the hand-cast test picks a cow at full hitpoints; the ranger test uses the
    ogre and clicks back onto its tile; new `test_the_monsters_in_the_regions_a_human_would_see_are_live`;
  - `tests/test_sim_crafting.py`: `test_a_crafting_paths_inputs_are_bought_on_the_ge`;
  - counts: `test_vocabulary`, `test_sim_buying`.

## Infrastructure Changes

- The fork rebuilt, and server 1 restarted several times, always stopped by its own PID. Servers 2 and 3 were set up
  (`scripts/server_instances.py 2 3`) for the re-check. Instance 4 ran a build of the fork before the fix (`0af2cc4`,
  from a git worktree in the scratchpad) for the A/B runs. All were stopped at the end.

## Decisions

- **User decisions:** the region gap. The options were (a) fix in the fork (recommended), (b) leave it and document a
  gap, (c) make the sim match. Caleb: (a), then re-check the server measurements that involve monsters near the
  character.
- **Agent choices (reversible):**
  - the hand-cast test's cow at full hitpoints;
  - the ranger test's walk back and its monster (the ogre);
  - not re-measuring gathering: every aggressor the sim counts at a gathering site is in the site's own region;
  - the crafting inputs' lots (1,000, the tools one), as Fletching's.

## Validation

- Reproduced first:
  - the hurt cows (3, 5 and 1 hitpoints at the first cast);
  - the frozen regions (live, before and after the fix);
  - the ranger's death (a full parallel run: 0 hitpoints of 59).
- Ruled out for the ranger: the giant's own aggression (4 runs of 950 ticks on the tile without attacking, never hit).
  Two traced runs of the old test (3,100 readings) didn't catch a step off the tile, so its cause is the likely one,
  not one seen.
- Tests:
  - alone: the hand-cast test 4 of 4, the ranger test 3 of 3, the region test passing;
  - the full suite (`-n 8 --dist loadgroup`, the server up): 407 passed, after one run with the old ranger test
    failing (the reproduction) and one passing;
  - speed: 96 decisions a second in one process, unchanged.
- The re-check (decision log):
  - 24 cases on the fixed server; 20 within 0.92 to 1.08 of their stored runs;
  - an A/B against the build before the fix moved none of the others by more than about two standard errors;
  - 21 of 24 inside the ±20% gate. Outside: the animated spades, whose stuck runs happen on both builds; ranged
    abyssal demons at 1.29 (server noise on a borderline case); melee experiments at band 91 at 1.20 (the sim has
    changed since the stored run).

## Follow-Up

- Caleb: env contract v1.24 and catalog v1.4 (to confirm); OQ-17's scope review (today).
- The animated spades' stuck runs, offered as a task of their own; the two cases now just outside the gate.
- Next: the server's measured Crafting times, then Herblore, Agility and Runecrafting.
- Committed when Caleb asked (the next turn): the fork first, then the submodule pointer.
