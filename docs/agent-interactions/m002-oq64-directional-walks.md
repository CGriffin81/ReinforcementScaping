# Agent Interaction

## Metadata

- Interaction ID: m002-oq64-directional-walks
- Timestamp CST: 2026-11-09 14:43:34 CST (the prompt). Caleb's answer to OQ-64 came at 15:37:07 CST. Both are from
  the session transcript's timestamps (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (sim v1.1's fix built, tested and proved history-independent, opened as its own PR for Caleb)
- Commit: the commit on branch `sim/v1.1-directional-walks` (from `tooling/results-summary` at `73b1b69`) that adds
  this record

## Full Prompt

> Continue once the speed-up digest finishes.

The answer to the question this raised (AskUserQuestion: how walk lengths should work, directional, symmetric, or
left and documented): Caleb chose "Directional (Recommended)".

## Response Summary

- **The speed-up's digest** matched `main` on 119 of E1's 120 episodes. The guide's seed 21 didn't.
- **The speed-up isn't the cause:**
  - seed 21 is identical, decision for decision, in a fresh process on both versions;
  - after guide seeds 0 to 20 in the same process, both versions give the same other digest.

  So sim v1 itself depends on what a process played before.
- **Bisected by clearing caches after that history:**
  - no single cache in the first list restored it, nor did clearing all of them, nor a fresh env;
  - clearing everything did, and of the module groups, only `rlscape.travel`'s;
  - the culprit is `rlscape.routes.Places.steps`, which caches a walk between two tiles off the places' table under
    the unordered pair, from the first direction asked. `_path` in `rlscape.travel` caches it from there.
- **The map is directed:** 834,294 of its 5,127,219 edges are one-way, and about 1 random pair in 42 has walks that
  differ by direction. In the Wilderness, (3125, 3831) to (3050, 3910) is 279 steps and 115 back.
- **Three lookups were also read backwards** (history-independent):
  - a place's walk to a tile off the table;
  - the Abyss's walks;
  - the combat pool's trips to the banks.
- **Asked Caleb** (OQ-64): directional, symmetric, or leave it documented. Caleb took (a), directional.
- **The fix (sim v1.1, env contract v1.43):** every walk is searched from its start. Where a lookup searched from the
  target, it now searches the reversed graph (`Map.lengths_to`).
- **The guide on the fixed sim:**
  - 28 of 30 seeds change, but the means don't: total level 350.7 → 351.0, net worth 130.6k → 129.8k;
  - its 20-hour test's seed 0 is now one of the 3 seeds in 30 whose Crafting stint spends hours on cows (seeds 11,
    15 and 28 were before), so that test's Thieving bound is 10, not 15.
- **The digest tool** (`scripts/trajectory_digest.py`, written for the speed-up) is in this PR. It is the proof that
  the fix removed the history dependence, and has its own tests.

## Documentation Changes

- `docs/env-contract.md`: v1.43, and §7's travel bullet.
- `docs/decision-log.md`: "Found: sim v1's walks depended on the process's history; decided: OQ-64 (a), directional
  walks (Caleb)", with the options.
- `ROADMAP.md`: sim v1.1 in the finishing plan; the branches start after `sim-v1.1`.
- `CLAUDE.md`: the branch rule names `sim-v1.1`.
- This record.

## Code Changes

- `rlscape/routes.py`:
  - `Map.lengths_to`, a search on the reversed graph;
  - `Places.columns`;
  - `Places.steps`: the pairs cached by `(a, b)`, and a place's walk to a tile off the table by the search to it.
- `rlscape/travel.py`: `_abyss_steps` and `travel_ticks_from_many` use `lengths_to`.
- `scripts/trajectory_digest.py` (new): the per-decision digest of every (policy, seed) episode, and `--compare`.
- Tests:
  - `tests/test_routes.py`: `lengths_to` on a one-way wall, and the walk from its start whichever was asked first,
    for both Wilderness pairs. It failed before the fix: (279, 279) and (530, 530).
  - `tests/test_trajectory_digest.py` (new): a digest depends on the policy and seed only, and `compare`.
  - `tests/test_guide.py`: the 20-hour seed-0 bound, with the reason.

## Infrastructure Changes

- The branch `sim/v1.1-directional-walks`, pushed, and its PR into `main`, stacked on PR #9.
- The speed-up's work is stashed, and goes onto this branch next.

## Decisions

- **User decision (Caleb):** OQ-64 (a), directional walks.
- **Agent recommendation:** (a), which Caleb took.
- **Agent choices (technical, for review):**
  - the backwards lookups are fixed too, so every walk follows (a), not only the one that depended on history;
  - the digest tool is in this PR, as the proof of history-independence.

## Validation

- `uv run pytest tests/test_routes.py tests/test_travel.py`: 17 passed. The new walk test failed on the old code as
  found.
- **Guide seed 21:** digest `3b0b936a9d40` both fresh and after guide seeds 0 to 20 (before the fix: `2c4b0917d518`
  fresh, `6a45e8f6ae6f` after).
- `uv run pytest -n 8 --dist loadgroup`: 432 passed, 75 skipped (the live tests, with the servers off).
- **E1's 120 episodes on the fixed sim** at 16 workers: `results/digests/fix16.json` (14,755 s of episodes in 987 s).
  The speed-up's PR compares them with a run at another worker count.

## Follow-Up

- **Caleb:** confirm env contract v1.43's wording; merge PR #9, then this PR. Claude tags `sim-v1.1` on the merge.
- **Claude:**
  - the speed-up PR, on this branch, proved by E1's digests at another worker count;
  - E1 rerun on sim v1.1 (PR #10).
