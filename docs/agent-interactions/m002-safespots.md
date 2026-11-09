# Agent Interaction

## Metadata

- Interaction ID: m002-safespots
- Timestamp CST: 2026-11-07 14:35:31 CST (first prompt) to 15:18:57 CST (last), three prompts, from the session
  transcript's message timestamps (UTC−06:00); the second and third arrived while work was running
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (built in the fork and the sim, exported, tested offline and live; the ranged calibration runs
  and the pickup-time refit remain; Caleb's answers to OQ-30 to OQ-32 are in `m002-safespot-answers`)
- Commit: fork `0c0f5dd` (branch `rl`) and the main repo commit after `2916c1e` that adds this record (branch
  `sim-v0`), both pushed 2026-11-07 with `m002-case-deltas`

## Full Prompt

> Continue with implementation.

Then, while it ran:

> Safespots work when a monster's southwest tile is in line of sight of our character, is in range of our weapons,
> and they cannot attack us. This is most common for melee only monsters, but a "safespot" for Skeletal Wyverns exists
> because you can outrange their long range attacks, once aggression has run out in their area. Skeletal Wyverns
> should be an incredible money maker.

> Work on the next feature while these tests run.

## Response Summary

- Built OQ-27 (d), which Caleb chose earlier today: ranged fights from safespots on both backends, arrow piles
  picked up between kills, one pickup time for every class.
- **The fork:**
  - `ranged_safespots` runs the server's own chase on detached copies of the monster: DUMB pathing toward
    `DestinationFlag.ENTITY`'s tile, a step a tick, until its own swing handler's `canSwing` lets it attack. A tile
    holds when the chase from the monster's spawn sticks with every tile of it in shot.
  - Per Caleb's note, monsters that shoot are outranged where their chase sticks beyond their reach: the skeletal
    wyvern's handlers both check the ranged reach. Aggressive monsters near a tile are reported, not ruled out,
    since aggression runs out.
  - `npcs` tells a safespotter which monsters would stay stuck in shot from where it stands, and which are moving.
- **The sim:** `rlscape/combat/safespots.py`, the per-site rates in both rankers, and the fight (no damage from a
  safespot, the site's supply held, arrow piles, pickup trips, waiting while guarded).
- **The runner** (`scripts/calibrate_combat.py`): safespotted ranged cases on the tile with auto-retaliate off.
- **Found:**
  - The server checks a ranged attack's line of sight between any tile of each, not only the monster's south-west
    one (Caleb's rule).
  - Chromatic dragons attack only in melee reach on this server, breath included, so they can be safespotted.
  - Skeletal wyverns need Slayer 72 here, which the sim has no way to train.

## Documentation Changes

- `docs/env-contract.md` v1.17 (to confirm): §8's pickup time and a ranged safespots row.
- `docs/option-catalog.md`: ranged fights safespot.
- `CLAUDE.md`: the fork's safespot commands.
- This record.

## Code Changes

- `rlscape/combat/safespots.py` (new): the trivial-damage rule, the table, piles, the walk.
- `rlscape/combat/rates.py`:
  - `PICKUP_TICKS` is one value for every class (5; ranged's to refit).
  - `with_pickups` takes extra ticks.
  - `unharmed` gives a safespot's rates.
  - `REGEN_TICKS` moves here from `rlscape/sim/health.py`.
- `rlscape/combat/candidates.py`: `site_rates`; `evaluate` ranks per site and picks the site by kill rate;
  `Character.arrow_piles`.
- `rlscape/combat/ranking.py`: the same per site, on arrays.
- `rlscape/sim/combat.py`: `safespot_for`; the fight's safespot, supply, piles and pickup trips; `_ammunition`
  counts the shots picked back up.
- `rlscape/sim/slots.py`: `_arrow_piles`.
- `rlscape/sim/state.py`: `TOLERANCE_TICKS` moves here from `rlscape/sim/aggression.py`.
- `rlscape/gamedata/server.py`: `RangedSafespot`, `ranged_safespots`.
- `rlscape/bridge/client.py`: `ranged_safespots`, `npcs`.
- `scripts/export_ranged_safespots.py` (new).
- `scripts/calibrate_combat.py`: safespotted ranged cases; ranged loots between kills only.
- Tests: `tests/test_sim_safespots.py` (new, 7); `test_sim_combat.py`, `test_sim_ranged_magic.py` and
  `test_sim_avas_devices.py` for the new signatures.

## Infrastructure Changes

- Fork (`server/`, uncommitted):
  - `RLCommands.kt`: `ranged_safespots`, `npcs`.
  - `RLBridge.kt`: a failed command's error names where it was thrown.
  - Built; instances 2 and 3's jar copies refreshed.
- `data/ranged_safespots.csv` (new), from the export.

## Decisions

- **User decisions:**
  - OQ-27 (d), earlier today.
  - Caleb's note on safespots and skeletal wyverns, built as the server has it.
- **Agent choices (reversible):**
  - A safespot needs to hold from at least half of its monsters' wandering (`MIN_SHARE`).
  - The walk to the arrows is at a tile a tick.
  - The rankers take a pickup trip after every kill; only the fight waits while guarded.
  - Threats are counted for a fresh character.
  - The runner turns auto-retaliate off on a safespot, and attacks only a held monster standing still where it
    holds.

## Validation

- `tests/test_sim_safespots.py`: 8 passed. With the exported table, the offline suite: 303 passed (`test_sim_slots`
  among them: a fresh ranger has six ranged slots again, the fast ranker matching the reference).
- Live, a ranger (Ranged 70, 99 hitpoints) on the top tile, auto-retaliate off, attacking only held monsters:
  - no hits at Varrock sewers' moss giants, two sets of hill giants, the Taverley Black Knights, the skeletal
    wyverns and the Wilderness green dragons;
  - a Black Knight by the Wilderness edge: no hits, once the character attacked only monsters standing still (a
    walking one, first, chased from where it stopped and hit);
  - a hill giant west of Ardougne held (no hits), but most attacks didn't start.
- Live test `test_a_ranger_on_a_ranged_safespot_takes_no_hits` (Varrock sewers' moss giants): passed.
- The export (`scripts/export_ranged_safespots.py`, three servers, about an hour):
  - 4,468 rows;
  - 93% of the sites with a safespot; 80% usable at range 7, 87% at range 9;
  - four sites without an answer;
  - 61 sites redone after a death had left the character at Lumbridge.

## Follow-Up

- The export, the ranged calibration runs from safespots, and the pickup-time refit.
- Open questions for Caleb: the trivial-damage rule, the line-of-sight rule, and Slayer for the wyverns.
