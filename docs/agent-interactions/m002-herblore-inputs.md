# Agent Interaction

## Metadata

- Interaction ID: m002-herblore-inputs
- Timestamp CST: 2026-11-08 20:24:07 CST (the prompt), 20:33:26 and 20:34:46 CST (Caleb's two messages during the turn),
  from the session transcript's timestamps (UTC−06:00)
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: DONE (Herblore's inputs in *V* and on the GE; its server times not yet)
- Commit: the earlier work is main repo `6c233da` and the merge `db3f87c` (branch `sim-v0`), pushed; the fork is
  unchanged at `df2b8a6`; this turn's later work is in the main repo commit after `db3f87c`, pushed

## Full Prompt

> Commit and push the changes, then continue with implementation.

During the turn:

> Add bird's nests to the GE.

> Set the price at 1765 gp.

## Response Summary

- **Committed and pushed, beside the other sessions' work:**
  - `6c233da`: Herblore part 1, with the Runecrafting session's part 1. The shared files hold both, as the two sessions
    agreed; it was confirmed by message and staged by explicit paths. Left out: the Agility session's in-progress
    files, and the Runecrafting session's newer `scripts/calibrate_runecrafting.py`.
  - `db3f87c`: the animated spades session's branch (`claude/funny-goldstine-4ada0b`, `194ff83`) merged. The decision
    and open-questions logs kept both sides. Before the merge the Runecrafting session renumbered its question from
    OQ-42 to OQ-45, since the branch already had OQ-42 to OQ-44.
- **Built: Herblore's inputs in *V* and on the GE** (Choices A (a) and I (a)): 66 GE buys, 51 new *V* items (*V* 348),
  2,157 actions and 3,274 features (env contract v1.27, to confirm).
- **Decided (Caleb): the bird's nest on the GE.** Claude asked the price, with the crushed nest's 1,865 gp
  recommended. Caleb set 1,765 gp. Built as the rod's set price was.

## Documentation Changes

- `docs/decision-log.md`: "Decided: the bird's nest on the GE at 1,765 gp (Caleb)" (with the options) and "Built (sim
  v1, Herblore part 2): Herblore's inputs in *V* and the GE's buys". At the merge, both sides of the log were kept, in
  time order.
- `docs/open-questions-log.md`: at the merge, OQ-43 and OQ-45 both kept.
- `docs/env-contract.md`: v1.27, to confirm. `docs/option-catalog.md` §9: Herblore's items, the size row.
- `docs/sim-v1-skills-draft.md` §6: as built. `ROADMAP.md`: the status line, the spades' result too.
- `CLAUDE.md`: the bird's nest's set price.
- This record; the Commit field of `m002-commit-herblore` (before the commit).

## Code Changes

- `scripts/build_price_tables.py`: the bird's nest in `SET_PRICES`, 1,765 gp; rebuilt `data/prices_v2.csv`,
  `data/grandexchange_2009_frozen.db` and their meta files (only the nest's rows changed).
- `data/vocabulary.csv`: 51 items, and "bought" on the 15 Herblore items already in it. `rlscape/vocabulary.py`: the
  docstring.
- `rlscape/sim/buying.py`: `HERBLORE_INPUTS` and `HERBLORE_TOOLS` in `GE_ITEMS`, their lots and roles.
- **Tests:** `tests/test_sim_herblore.py` (`test_a_potion_paths_inputs_are_bought_on_the_ge`); `tests/test_vocabulary.py`
  (the counts, and the bird's nest beside Ava's devices: untradeable, so neither alchable nor sold to stores);
  `tests/test_sim_buying.py` (271 GE buys).

## Infrastructure Changes

- None: no server ran this turn. The servers' GE databases take the nest at their next `install_ge_db.py` (or
  `server_instances.py`); the other sessions were told.

## Decisions

- **User decisions:** the bird's nest on the GE at 1,765 gp (Claude's question: (a) 1,865 gp, recommended, or (b) a price
  of his own).
- **Agent choices (reversible):** the herblore inputs' lots (1,000; the pestle and mortar one).

## Validation

- Before the commit, the suite without the server on the combined tree: 357 passed (and the Runecrafting, gathering,
  Herblore and count tests, 54). After the merge: 357 passed.
- After the inputs and the nest: 358 passed.
- Speed: 76 decisions a second in one process, under the other sessions' two servers. That isn't comparable to the
  earlier 96 to 100, but 321 more actions are masked each step.

## Follow-Up

- Caleb: env contract v1.24 to v1.27 and catalog v1.4 (to confirm); OQ-17's scope review (today); OQ-43 (the magic
  runner's recasting), OQ-45 (the Runecrafting session's).
- At 1,765 gp, buying a nest and grinding it into a crushed nest (1,865) gains 100 gp, a nest every 2 ticks.
- The sim's speed with the larger *V*: measure on a quiet machine.
- Next: Herblore's times on the server (instance 7).
- Committed when Caleb asked (the next turn).
