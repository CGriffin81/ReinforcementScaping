# Agent Interaction

## Metadata

- Interaction ID: m002-mask-speedup
- Timestamp CST: 2026-11-09 14:34:04 CST (the prompt), from the session transcript's timestamp (UTC−06:00). Caleb's
  question about E0 and E1 came mid-turn at 14:20:38 CST, and "Continue once the digest finishes." at 16:00:36 CST.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: SUCCESS (the speed-up built, proved on E1's 120 episodes and opened as a tooling PR, stacked on PR #11)
- Commit: the commit on branch `tooling/mask-speedup` (from `sim/v1.1-directional-walks` at `802de5a`) that adds this
  record

## Full Prompt

> Continue with the mask speed-up once the digest finishes.

Mid-turn, Caleb asked: "Should we have run E0 before E1?" Claude answered in chat:
- **No, E1 first is fine.** E1 has no learning, so it doesn't need the ladder.
- **The ladder needs E1:** its second rung, PPO beating random, is judged against E1's random baseline.
- **The ladder can't run yet:** it needs `train.py`.
- **The cost if the ladder finds a sim problem:** E1 reruns in about 16 minutes.

That answer led to OQ-63 (record `m002-oq63`).

## Response Summary

- **Profiled** a random 20-hour episode with warm caches. The mask is 88% of a decision. The biggest parts:
  - the skilling slots' ranking: 7.3 s an episode, with the aggression share's simulations 3.0 s of it;
  - route planning: 4.2 s, 25,439 routes;
  - the combat ranking: 3.2 s;
  - `nearest_bank`: 2.4 s, 19,371 calls.
- **Two changes, neither changing a result:**
  - `movement.route` remembers its routes by everything the plan reads (`_route_key`, with `transport.boat_key`);
  - Fletching's and the crafting stations' `available` run their cheap checks before the walk to the bank.
- **Speed:** 1.49× on E1's 120 episodes at 16 workers (15,162 → 10,200 s of episodes, 1,017 → 680 s of wall time).
- **The first proof run found sim v1's history dependence** (OQ-64, record `m002-oq64-directional-walks`): 1 of 120
  episodes differed, and not because of the speed-up. So the speed-up now sits on sim v1.1's fix.
- **Proved on sim v1.1:** with the speed-up at 12 workers, all 120 digests equal the fix's at 16 workers.
- **Left alone:**
  - the vectorised combat ranking;
  - the aggression shares' simulations;
  - their `deepcopy`.

  Each would cost more than the plan's day, or risk a difference.

## Documentation Changes

- `docs/decision-log.md`: "Built: the mask speed-up, with no result changed (tooling, OQ-61)".
- `ROADMAP.md`: the finishing plan's speed-up item, ticked.
- This record.

## Code Changes

- `rlscape/sim/movement.py`: `_ROUTES`, `ROUTE_CACHE`, `route` remembered by `_route_key`, and `_plan` (the old body).
- `rlscape/sim/transport.py`: `_boat_skills` (it fails loudly if a boat ever needs Magic, runes or an item) and
  `boat_key`.
- `rlscape/sim/fletching.py`, `rlscape/sim/crafting.py`: the cheap checks first in `available`.
- `tests/test_mask_speedup.py` (new, 2 tests):
  - the remembered route is the planned one in every state of a played guide episode;
  - a route is planned again when the coins or the tile change.

## Infrastructure Changes

- The branch `tooling/mask-speedup`, pushed, and its PR into `main`, stacked on PR #11.
- `results/digests/` (git-ignored): `main.json`, `speedup1.json`, `fix16.json` and `speedup12.json`.

## Decisions

- **User decisions (Caleb, in this turn):** OQ-63 (b) and OQ-64 (a), in their own records.
- **Agent choices (technical, for review):**
  - what to remember and the keys;
  - the cheap checks first;
  - leaving the rest;
  - proving it across worker counts.

## Validation

- **Digests:** `scripts/trajectory_digest.py --seeds 30 --workers 12 --compare results/digests/fix16.json`: 0 of 120
  episodes differ.
- **Tests:** `uv run pytest -n 8 --dist loadgroup`: 434 passed, 75 skipped (the live tests, with the servers off).

## Follow-Up

- **Caleb:** merge PRs #9, #11 and this one, in that order.
- **Claude:**
  - E1 rerun on sim v1.1 (PR #10);
  - tag `sim-v1.1` on #11's merge;
  - then `train.py` with the decision logger.
