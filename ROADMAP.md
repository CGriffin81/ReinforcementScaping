# Roadmap: Learning to Climb (HRL for Skill and Wealth in 2009Scape)

Built from `CS898BG_RL_Project_Proposal_2009Scape.pdf` and `Requirements.md`.
**Week 1 starts Mon Oct 5, 2026. The final report is due Mon Nov 30, 2026.**

**Fixed design decisions** (Oct 5):
- Every episode starts from a **fresh level-3 character**.
- Training episodes are **20 game-hours**, evaluated at **checkpoints every 2 game-hours** (2, 4, …, 20).
- **Combat is in scope** and is a core part of the option catalog.
- Claude writes the code; Caleb reviews and runs it. The AI-assisted code policy from Promethean applies (`docs/ai-log-requirements.md`).

---

## 0. Guiding principles

1. **The surrogate simulator is the critical path, not the real server.** E1–E5 all run on the sim. The server is used for calibration (weeks 2–3) and validation (week 6). Sim work never waits on server work.
2. **One environment contract, two backends.** `SimEnv` and `ServerEnv` expose identical observation, action, mask and info schemas, so every policy and baseline runs on either one unchanged. Draft the contract in week 1 and freeze it at the end of week 2.
3. **Drive the server from the inside, not through the client.** 2009Scape already ships a server-side bot framework (`Server/src/main/core/game/bots/`: `AIPlayer`, `Script`, `ScriptAPI`, `SkillingBotAssembler`, …) and 28 working bot scripts in `Server/src/main/content/global/bots/` (`DraynorWillows`, `CowKiller`, `LobsterCatcher`, `VarrockSmither`, `ManThiever`, `Adventurer`, …). A Kotlin "RL bridge" can spawn an `AIPlayer`, run each option as a `Script`, and expose a socket. This needs no client, no pixels and no input injection. The client is only for watching replays.
4. **Port the formulas, measure the overheads.** Success rolls, XP values and drop tables come straight from the server source into the sim. Anything the source can't tell us (travel time, banking overhead, pathing, competition with bots for resources, GE fill time) is measured on the server.
5. **Log every decision from day one.** For each decision, record obs, mask, option, action probabilities, value estimate, duration and reward components. RQ2 analysis depends on these logs, and they can't be recreated afterward.

---

## 1. System architecture

```
┌──────────────────────────── Python package: rlscape ────────────────────────────┐
│ agents/    MaskablePPO (+SMDP buffer) · PPO+RND · Envelope Q · baselines         │
│    │                                                                            │
│ envs/      Gymnasium contract: obs vector, action_masks(),                      │
│    │       info{duration, reward_vec, option_id, termination_reason}             │
│    ├────────► SimEnv     (sim/: numpy, data-driven YAML catalog, seeded RNG)     │
│    └────────► ServerEnv ── TCP / JSON-lines ──┐                                 │
│ eval/ · analysis/ · TensorBoard + parquet decision logs                         │
└───────────────────────────────────────────────┼─────────────────────────────────┘
                                                │
┌────────────── 2009Scape server (Kotlin/Java, JDK 11, Maven; SQLite GE) ─────────┐
│ content/rl/RLBridge.kt     JSON-lines socket, commands in RLCommands.kt         │
│ content/rl/RLPlayer.kt     the agent's character: an AIPlayer treated as human  │
│ tick loop patched to a configurable interval (server.tick_ms, set_tick_ms)      │
│ GE frozen at January 2009 prices · frozen buyer and seller · ambient bots       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Bridge protocol (as built, 2026-10-28).** The full list, with payloads, is the header of
`server/Server/src/main/content/rl/RLCommands.kt`. The Python side is `rlscape/bridge/client.py`.

| Group | Commands |
|---|---|
| World | `ping`, `set_tick_ms`, `wait` |
| Character | `spawn` (a fresh level-3 character as it leaves Tutorial Island), `state`, `despawn` |
| Actions (human paths) | `walk_to`, `interact`, `run_script`, `stop_script` |
| Economy | `ge_offer`, `ge_status`, `ge_collect` (through `StockMarket`, only at the GE) |
| Data exports | `ge_snapshot`, `item_definitions`, `npc_definitions` |
| Tests and calibration only | `debug_teleport`, `debug_give`. Never exposed to the agent. |

Whole options (`reset` / `step` in the env contract) are built in Python on top of these commands. That's the
`ServerEnv` executor, planned for week 6.

---

## 2. Repository layout (as proposed; mostly built by 2026-11-09)

*As built:* `rlscape/` also has `travel.py` and `routes.py` (walking routes on the server's collision map),
`vocabulary.py`, `agents/` (`smdp.py`, `ppo.py`, `training.py`, `decision_log.py`, and E4's to E6b's `rnd.py`,
`conditioned.py` and `pbrs.py`), `analysis/` (the figures' measures), `eval/` (the harness), and `baselines/`
(`policies.py`, `guide.py`). There's no `envs/ServerEnv` or Envelope Q (cut, OQ-17). `results/` is git-ignored but
for `results/summary/`, each experiment's committed summary (`scripts/publish_summary.py`, 2026-11-09).

```
ReinforcementScaping/
├── docs/          env-contract.md, option-catalog.md, decision-log.md, resources.md, agent-interactions/
├── data/          prices_v2, the frozen 2009 GE, cache exports, curated banks and access table   (built)
├── infra/         MariaDB compose file (not needed with the current config)                      (built)
├── rlscape/
│   ├── gamedata/  server data loaders (items, NPCs, drops, spawns, Slayer, quests)               (built)
│   ├── combat/    combat formulas, rates, candidate slots, access table                         (built)
│   ├── sim/       surrogate simulator; options from docs/option-catalog.md, prices from data/
│   ├── envs/      SimEnv, ServerEnv, wrappers (reward weights, PBRS, RND, MO vector)
│   ├── bridge/    socket client for the server                                                  (built)
│   ├── agents/    SMDP rollout buffer, RND module, masked Envelope adapter
│   ├── baselines/ random, greedy_xp, greedy_gp, scripted_guide
│   ├── eval/      harness, bootstrap CIs, hypervolume, discovery metrics
│   └── analysis/  figure scripts
├── configs/       one YAML per experiment (`evaluate.py --config`; on each experiment's branch)
├── scripts/       built: gate_check, ge_warmup, price pipeline, exports, install_ge_db; planned: train.py, evaluate.py, sweep.py, calibrate.py
├── server/        fork of 2009scape (git submodule) + RL bridge
├── tests/
└── results/       (git-ignored) runs, checkpoints, logs; summary/ is committed
```

---

## 3. Technical decisions to settle early

| Issue | Why it matters | Plan |
|---|---|---|
| **SMDP discounting** | Options run for different amounts of game time. SB3 applies one γ per decision, so a 2-min bank trip is discounted the same as a 40-min woodcutting trip. That's wrong under a game-time horizon and would confound the E5 discount ablation. | The env reports `info["duration"]`. Subclass sb3-contrib's `MaskableRolloutBuffer` (plus a small `collect_rollouts` override to store τ) so GAE uses γ^τ. Define γ **per game-hour** (e.g. γ_hr ∈ {0.5, 0.9, 0.99}). |
| **PBRS in an SMDP** | Ng et al.'s policy-invariance guarantee only holds if shaping uses the agent's own discount. | F = γ^τ·Φ(s′) − Φ(s), with Φ(terminal) = 0. Candidate Φ: best GP/hr available from current unlocks, which directly encodes "investing pays off". |
| **What counts as wealth** | If equipment doesn't count toward bank value, buying an axe looks like losing money. The agent is penalized for investing, which biases the H1 test. | Wealth = GP + (bank + inventory + equipped items) × the **fixed** price table, i.e. net worth. |
| **Skill reward normalization** | Raw XP grows exponentially per level, so high-level XP would dominate. Total level is the reported metric. | Reward fractional level gained (level + progress toward the next level) to match the reported metric. Wealth reward = Δnet worth / a fixed scale (100k GP). E3 to E6 give their weights in units of E1's best 20-hour gain on each objective, converted by `rlscape/envs/weights.py` (OQ-67, 2026-11-10). |
| **Valuation table** | Runs are only comparable if net worth is computed the same way every time. | **Done (Caleb's formula):** `data/prices_v2.csv` = max(high alchemy − nature rune, January 2009 GE price from the RuneScape Wiki), coins = 1. Fixed for the whole study. `prices_v1` (the 10-hour snapshot) is superseded but kept. |
| **RND with masking** | Neither SB3 nor sb3-contrib includes RND. | v1: a VecEnv wrapper that adds a normalized, non-episodic intrinsic reward for MaskablePPO. v2, only if v1 results are ambiguous: dual value heads, using CleanRL's `ppo_rnd_envpool.py` as reference. *Built 2026-11-10 as v1 (OQ-72):* the bonus is centred and scaled per decision, since options last seconds to 15 minutes; the 20-hour limit is bootstrapped, so it isn't cut off there. |
| **Masking in Envelope Q** | MORL-Baselines' Envelope Q-learning has no action-mask support out of the box. | Patch action selection and the target max to set invalid Q to −∞, and store the next-state mask in the replay buffer. *Cut (OQ-17 (a′), 2026-11-09): a weight-conditioned PPO replaces Envelope Q.* |
| **Bot helpers cut corners** (found Oct 5) | `ScriptAPI.sellOnGE`/`sellAllOnGe` delete the items and pay nothing (`GrandExchange.addBotOffer`). `buyFromGE` never dispatches. `teleportToGE` and `withdraw` skip travel. And any GE offer from an artificial player becomes a bot offer. | **Done:** the agent's character is an `RLPlayer`, treated as a human by every game rule. The bridge trades through the human GE path (`ge_offer` / `ge_collect`, only at the GE). Gathering and combat logic can still be borrowed from the bundled scripts. |
| **Python version** | This machine has Python 3.14, and RL libraries lag new Python releases. | Use a `uv` project pinned to Python 3.12. |
| **Windows multiprocessing** | `SubprocVecEnv` uses spawn on Windows. | Put every entry point behind `if __name__ == "__main__":` and keep env construction picklable. |
| **Reproducibility** | Every comparison needs ≥5 seeds with bootstrap CIs. | Seeded `numpy.random.Generator` in the sim; each run dir stores the config, config hash and git SHA. |

### Throughput estimates (to sanity-check, not commitments)

*Superseded by measurement (2026-11-09, decision log):* one sim worker makes 70 to 80 decisions a second, a random
episode about 385 decisions, and PPO training about 1M decisions an hour on this machine. OQ-7 (a) dropped the
≥20k target. E6 is cut (OQ-17). The estimates below are kept for history.

- **Sim:** target ≥20k decisions/s on 16 threads. A 20-game-hour episode has roughly 100–300 decisions, so a 5M-decision run should take roughly 15–30 min including PPO updates, and all of E2 (25 runs) fits overnight. Small-MLP PPO runs faster on CPU (Ryzen 7 5800X) than on the GPU. Save the RTX 3050 for Envelope Q and the stretch work.
- **Real server:** at the default 600 ms tick, 1 game-hour takes 1 wall-hour. With a 10× tick and 8 RL-controlled `AIPlayer`s in one world, 1 wall-hour ≈ 80 game-hours. Then E6 (4 configs × 5 seeds × 20 game-hours = 400 game-hours) takes about 5 wall-hours. **Without the speedup it takes about 50 wall-hours**, which is why decision gate G1 matters. A fallback is to validate only the first 10 game-hours (checkpoints 2–10).
- **G1 measured (Oct 5):** 34× at a 15 ms tick with one world and 100 ambient bots. So 8 parallel RL characters would give about 270 game-hours per wall-hour, and E6's 400 game-hours fit in about 1.5 wall-hours. About 2.6 ms per tick is fixed overhead, so going much faster probably means turning down the ambient bots (not yet tried). Still open: about 160 `System.currentTimeMillis()` call sites stay on wall-clock time. Most are out of scope (farming, brewing, minigames), but the 10 s "in combat" flag (`CombatPulse.kt` / `Entity.java`) is in scope and needs checking once combat options exist.

---

## 4. Phased plan

*From Nov 9, the unfinished items of weeks 3 to 5 are part of the finishing plan in weeks 6 to 8 (OQ-17).*

### Week 1 (Oct 5–11): Foundations and decision gate
**Goal:** a go/no-go on the real server, an option catalog v0, and a Python skeleton.

*Server track*
- [x] Install JDK 11 (Temurin 11.0.32 via winget). Maven isn't needed because the repo ships `Server/mvnw.cmd`.
- [x] Fork the server: [CGriffin81/2009scape-rl](https://github.com/CGriffin81/2009scape-rl) (private, full upstream history; `master` mirrors upstream, at `bea45a9e` until it was synced to `f279da8` on 2026-10-28; our work on `rl`). Linked here as the `server/` submodule.
- [x] Build the server jar (`Server/target/server-1.0.0-jar-with-dependencies.jar`, ~3 min cold build).
- [x] Run it against MariaDB (`infra/docker-compose.db.yml`, localhost-only; no longer needed, since auth and account persistence are off). The first launch took 418 s, mostly filling the GE price index in SQLite; built-in bots start ticking right away. The game port 43595 bound to **all interfaces**. *Fixed 2026-10-28: `server.bind_address`, which `rl.conf` sets to `127.0.0.1`.*
- [ ] Install Singleplayer through the Saradomin launcher, for reference play and for watching bots. *Deferred to week 7 (Caleb, 2026-10-28). It's only needed there, to record a replay with the client attached.* *Not needed now: the finishing plan's demo replays checkpoints in the sim (OQ-17, 2026-11-09).*
- [x] Read `core/game/bots/` (`AIPlayer`, `Script`, `ScriptAPI`, `GeneralBotCreator`) and the bundled-script economy helpers.
- [x] **G1, tick and headless: PASS.** `server.tick_ms` is now configurable and changeable at runtime through the bridge. Measured with 100 ambient bots: 4.9× at 120 ms, 9.5× at 60 ms, 17.5× at 30 ms, 34× at 15 ms (about 2.6 ms of overhead per tick). The "in combat" wall-clock flag is still untested under speedup.
- [x] **G2, state and actions: PASS.** `content/rl/RLBridge.kt` + `RLCommands.kt` in the fork, and `rlscape/bridge/client.py` here. Spawns a character exactly as it leaves Tutorial Island, reads its full state, and drives authentic interactions: 600 ticks of chopping gave 10 logs and 250 XP. Covered by `scripts/gate_check.py` and `tests/test_bridge_live.py`.
- [x] **G3, GE dynamics: answered. The market is bot-stocked and prices are static.** A 10-game-hour warm-up from a fresh GE (`scripts/ge_warmup.py`) changed 0 of 7,324 prices and saw 0 trades, while bot stock grew to 19,675 units of 145 items. Nothing in this world places buy orders, so the price index never moves. See the decision log for the mechanics.
- [x] Export the fixed price table: `data/prices_v1.csv` plus `.meta.json` (the 10-hour snapshot, per Caleb's decision; identical to the seeded high-alchemy values), and `data/grandexchange_warmup10h.db` for resetting the real server's GE. *Superseded by the economy decisions below.*
- [x] Economy (Oct 5–27, Caleb's decisions; details in the decision log):
  - the RL character (`RLPlayer`) is treated as a human by every game rule
  - the GE is frozen at January 2009 prices (`data/grandexchange_2009_frozen.db`, installed by `scripts/install_ge_db.py`)
  - net worth uses `data/prices_v2.csv`: max(high alchemy − nature rune, 2009 GE price)
  - random events are off for RL characters
  - a frozen-price GE buyer and seller trade items that have a 2009 price
  - the anti-dragon shield couldn't be traded on the GE (Duke Horacio only); since 2026-11-06 the GE sells it (Caleb)

*Python track*
- [x] `git init`, and a `uv` project pinned to Python 3.12 (`rlscape` package, pytest).
- [x] Add the RL stack when the sim needs it: gymnasium, torch, stable-baselines3, sb3-contrib, morl-baselines, mo-gymnasium, tensorboard, pandas, pyarrow, matplotlib. *Done 2026-11-08 for PPO:* torch 2.14.1 with CUDA 13.0 (Caleb), stable-baselines3 and sb3-contrib 2.9.2, tensorboard; torch comes from `wheels/` (`scripts/fetch_torch_wheel.py`). morl-baselines and mo-gymnasium aren't needed: E4's Envelope Q was cut for a weight-conditioned PPO (OQ-17 (a′)).
- [x] `docs/env-contract.md` **v1.0, signed off by Caleb on 2026-10-28.** It adds the death rule: respawn and carry
  on, with a 2-minute gravestone outside the Wilderness.
- [x] `docs/option-catalog.md` **v1.0, signed off by Caleb on 2026-10-28:** about 452 actions. Every question is
  decided:
  - no auto-banking
  - Magic and alchemy
  - any-enemy combat through candidate slots and the access table
  - frozen seller plus shops
  - selling all of an item
  - per-source buying
  - the 21-quest set
  - the four loot modes (§4.D)
  - `reclaim_gravestone` after a death

**Deliverable:** a `docs/decision-log.md` entry with G1–G3 results and the chosen path: real server + sim, or sim-primary.

### Week 2 (Oct 12–18): Surrogate sim v0, environment, baselines (E1)

*Started 2026-10-27 (catching up):* `rlscape/gamedata` (server data loaders) and `rlscape/combat` (formulas ported from the server, plus the rate model), with tests. Then the cleaned NPC pool (cache definitions), inventory-aware gp/hr and the retreat-aware filter. *2026-10-28:* the access table (gated areas, quest-only NPCs, Slayer levels). Sim v0 started on branch `sim-v0`: the core (skills, character state, the step loop), then the gathering family (woodcutting, mining, fishing, pickpocketing, with hitpoint regeneration and eating) the processing family (smelting, smithing, cooking on fires or ranges, firemaking, burying bones), and the inventory, alchemy and selling options (bank, withdraw, drop, alch, sell at the GE or a general store; per-item actions wait for the vocabulary), ported from the server. Combat so far: melee fights, drops, death and gravestones, a fast candidate ranker (1.3 ms, identical to the reference), and *2026-10-29* the 30 combat-slot actions and 4 loot-mode actions, then ranged fights (arrows used and recovered) and magic fights (runes per cast), with the ranking capped by the ammunition held. The server's GE collection now follows Caleb's buying decisions (fork change). *2026-10-30:* buying (113 buy actions at the GE and shops, with shop stock tracked; gear and food withdrawals; `smith_mithril`; option catalog v1.2); run energy and weight (travel follows the server's energy rules; `bank_deposit_worn`; the bridge's `set_run`, fork change); the Gymnasium layer (`SimEnv` and the shared observation encoder). The item vocabulary *V* (156 items, accepted by Caleb; 974 actions). The random and greedy baselines, and the eval harness (a preliminary E1 run of 10 seeds took under 4 minutes). The scripted-guide baseline is drafted from the RuneScape Wiki's January 2009 guides and reviewed by Caleb; deposits keep the task's kit, and a withdraw-to-sell action exists. 15 pickpocket targets, 5 Ardougne stalls and the Shantay Pass are built, and a live test found no tick manipulation on 2009Scape. The guide's second draft covers all 13 sim v0 skills; Caleb signed it off as E1's scripted baseline. *2026-10-31:* skilling slots replace the fixed gathering actions (paths paired with their processing counterparts; env contract v1.6), and the guide follows the members' guides in stints to multiples of 5. Fletching brought forward from sim v1 (Caleb): chop-and-fletch paths, Fletching's own slots, stringing only where it adds value, and Lumbridge Castle's knife (env contract v1.7; 1,110 actions). Open questions moved to `docs/open-questions-log.md`. Prayer flicking, tested live: a prayer on only in the ticks that need it never drains, and protection and accuracy and damage prayers act at the swing. Fights now flick prayers automatically (Caleb; env contract v1.8). The week-2 property tests and the speed benchmark (804 decisions a second with 16 workers, against the contract's 20k: OQ-7). Calibration started: woodcutting at the site, within ±20% of the server at four bands after patching the measured overheads (willow again with auto-retaliate off: 0.89 to 1.07, every run finishing). Ambient bots are now off in `rl.conf`, as decided on 2026-10-28, and the server version is frozen (Caleb). The bridge's `interact` picks a reachable target and can walk with a client click (Caleb). Aggressive monsters at gathering sites follow Caleb's rule on both backends (env contract v1.9): a low-level woodcutter at the willows is within the gate (0.95). Mining is calibrated too (every case within ±20%), with iron at Al Kharid among the scorpions (Caleb) and the bridge's `safespots`. Fishing is calibrated (every case within ±20%). Draynor's Dark wizards kill a level-3 fisher there, so shrimp can be fished at Lumbridge Swamp too, and the guide fishes there until its combat level passes 14 (Caleb). Travel and banking started (Caleb): walking routes planned on the server's collision map and walked as clicks, and banking through the player's clicks. The sim now walks the planned routes with the measured overheads (every measured trip within 0.95 to 1.12 of the server, against 0.50 to 1.24 before). The transports are built on both backends (Caleb: every trip takes the fastest way the character can use; env contract v1.10): the home teleport, spells, jewellery at every charge, tablets, the seed pod, ships and charters, and the crossings (the Wilderness ditch, the Gnome Stronghold's gate, the Grand Tree's doors, the toll gate). Travel is validated: 27 trips on the server, every one within ±20% (13 fresh ones 0.94 to 1.15). Then (Caleb): the home teleport waits 30 minutes (a fork change, in game ticks); Ghosts Ahoy and the Ectophial are out (the server lacks the quest); a place with no way there is unreachable, and one the character can't get to now is masked for it (231 of 2,792 places cut, mostly behind quests outside the set; OQ-16 asks which missing ways to add). *2026-11-05:* combat calibrated for melee and ranged, drops left (`scripts/calibrate_combat.py`): two fork fixes (the bridge clicked dead monsters; "in combat" counted 10 wall-clock seconds, so a sped-up server locked fights twelve times too long: now 17 game ticks), and site capacity in the rates (kills wait for respawns where a site has few of the monster; the overhead between kills measured, 10 ticks melee, 8 ranged). XP/hr within ±20% on the 8 fit cases and on 8 of 9 cases it wasn't fitted on. Then (Caleb) the "in combat" fix approved; a pickup command (`ground_items`, `take`), with which the runner loots; Taverley dungeon's two eastern Black Knights are hazards, not targets. On the way, a fork fix: every bridge character had account uid 0, so their kills dropped nothing; each now has its own. With loot on (the ranker's top gp picks), XP/hr and kills/hr are within ±20% in all 8 cases (0.80 to 1.15), and so is the time to a full inventory (0.81 to 1.05). Loot per kill matches the sim's spread, but the mean gp/hr of a few short runs can't settle the gate where rare drops make up the loot (OQ-20). Still open: poison, ranged damage taken, magic, the willows' aggression rates, and monsters near a fight (OQ-19). *2026-11-06 (Caleb):* quests are out: every quest the server has (68 of the enum's 150) is complete from the start, as flags only (quest points and unlocks, no XP or items), on both backends; the observation loses its 64 quest features (env contract v1.12, option catalog v1.3). The level-3 start with the starter kit stays. The uid fix is approved. Calibration keeps the 50 ms tick, with a speed check at 600 ms in the gate (OQ-21); gp/hr is gated by its parts, with a drop-table probe of about 200 kills per monster (OQ-20); monsters near a fight are measured before they're modelled (OQ-19). Then (Caleb): the GE sells the anti-dragon shield, and fights against dragonfire monsters put a carried one on; the vocabulary is redrafted with every quest complete, adding 16 items; the buy list takes the dragon dagger and longsword and the Fremennik helms (OQ-24): *V* 198, 1,227 actions, 1,957 features; only Taverley's eastern pair of Black Knights are hazards. The gate's speed check passes (18 of 18 cases agree at 50 and 600 ms; OQ-21). The drop tables' shared sub-tables (rare drop table, gems, herbs, seeds) are ported, and with them *V* takes 5 more items (Caleb): 203, 1,252 actions, 1,992 features. A drop probe checks the tables item by item against the server (OQ-20). Poison (and antipoison), combat potions, antifire and a dragon's breath are modelled (Caleb; the 2009 wiki: antifire with the shield is complete immunity); fights flick on the server too (`flick`), and one server takes several agents at once. Calibration fights start with a combat inventory (no starter kit; Prayer at the band, flicked; food for the expected damage). Thieving calibrated at Lumbridge's men (0.98 and 1.00 after a fitted 0.44-tick overhead an attempt). Only the four-dose potions are in *V*, the lower doses still drunk and counted (Caleb, OQ-25): *V* 214, 1,318 actions, 2,102 features. The moss giants west of the Fishing Guild, which the server doesn't let a character attack, are hazards too, and the Yanille Agility Dungeon is out of the project (Caleb). The probe: Black Knights, unicorns, hobgoblins, women, green dragons (with antifire), moss giants and chaos druids fit. The server ran in dev mode, which makes champion scrolls and big fish common; it's off now (Caleb, OQ-26). *2026-11-07:* the overhead between kills refitted with the combat inventory (3 ticks, from 10 and 8: kills now take about one click), and a pickup time a looted drop (3 melee, 10 ranged): XP/hr within ±20% in all 24 cases (0.90 to 1.19); the time to a full inventory at Edgeville's chaos druids is 0.72 (the runner loots only while nothing attacks it). Then (Caleb): the runner loots between kills, attacked or not (every time to a full inventory within ±20%; ranged's arrow pickups are OQ-27), and the rate model's kill time counts the last hit's overkill (exact, matching the sim's kills within 0.8%). The bridge uses items on scenery (`use_item_on`), and the processing family is calibrated: every case within ±20% after fixes measured on the server (burying 3 ticks a bone; smithing's next item; firemaking's step-offs); the Edgeville furnace needs the Varrock Diary, so the sim no longer offers it. Then (Caleb): Ava's devices on the GE and in the sim; ranged fights from safespots, found by the server's own chase, with their arrow piles (OQ-27 (d), OQ-29 to OQ-33); no Slayer level requirements; every crossbow and bolt in *V* (279; env contract v1.17, confirmed). The ranged check set is within ±20% on XP/hr (0.96 to 1.19). Magic calibrated by hand casts (the bridge's `cast`; the autocast rate checked live): XP/hr 0.95 to 1.07 where no other kind of monster engages the character; where one does (the animated spades' possessed pickaxe), 1.14 and 1.33 (OQ-19's first measurement). Then (Caleb): magic safespots as ranged does (OQ-34; the table re-exported at ranges 7, 9 and 10), and the aggressive monsters of other kinds near a fight engage between kills until aggression runs out, each fought in the fight's plan (OQ-35 (a); a rate measured on the server; both rankers and the fight; env contract v1.18). Magic's fit set 0.97 to 1.12 and check set 0.95 to 1.03, but for a magic safespot holding from 61% of the wandering (OQ-36); beside neighbours 0.99 to 1.28 (the poison spiders' 1.17 once the runner attacks back after eating). *2026-11-08 (Caleb):* a usable safespot holds from 80% of the wandering (OQ-36; the cases it changed 0.84 to 1.15, after the late pickup trips' guards were refitted to the server's); the observation shows the home teleport's cooldown (OQ-15, v1.19); the rate model is vectorised (OQ-7 (a): 110 decisions a second in one process, 817 with 16 workers, 2.6 times as fast); OQ-2 sets the four sim v1 skills' scope and OQ-16 (a) the missing ways. Then: OQ-2's draft (`docs/sim-v1-skills-draft.md`, for Caleb); OQ-16's unclear places checked on the server (none walkable, as the planner has it) and the Crandor passage built (219 places without a way, from 231). Then the Rellekka ferries (the Fremennik Isles; 210 places without a way); West Ardougne stays unreachable (Caleb, OQ-37 (b): its way in needs a quest item; `docs/post-project-gaps.md`), and Trollheim is reached by its teleport (Caleb: its climbs need climbing boots, left out). The Trollheim, Watchtower and Ape Atoll teleports ask what the server asks for quests it lacks, their own requirements (Caleb, env contract v1.20): Ape Atoll's open now, Trollheim's at Herblore 31, Watchtower's at its five levels. Then Caleb answered OQ-2's draft: Crafting without studded leather, snakeskin or jewellery; the Gnome, Barbarian and Wilderness courses, and Barbarian Fishing for Agility (its rod on the GE); the 21 potions with grinding; the Abyss and tiaras; inputs in *V*. The Barcrawl and Enter the Abyss are complete from the start as flags only (env contract v1.21), and the bridge finds NPCs by the form a player sees. OQ-38 decided (Caleb): picking flax paired with spinning, and essence mined and crafted by separate paths. OQ-39 to OQ-41 decided (Caleb): the death altar opens and the astral one stays out; the pouches as the server gives them (the small pouch at spawn, in the bank: env contract v1.22; the others drop from the Abyss's monsters); the barbarian rod on the GE at 1,000 gp (built). Building sim v1: Crafting built in the sim (gems, leather and dragonhide at a bank; tanning; spinning; flax; its slots: env contract v1.23; a dead RL character now respawns at the home location, fixed in the fork), and its inputs bought on the GE (*V* 297, 1,828 actions, 2,801 features: env contract v1.24). Hardening two flaky live tests found an RL character kept only its own map region active, so monsters across a boundary stood frozen; it now keeps the regions in a client's view active, as a human does (Caleb, a fork fix), and the combat calibration sets were re-checked. Crafting is calibrated on the server (`scripts/calibrate_crafting.py`: each batch's clicks fitted, every case 1.00 but flax, 0.92 to 1.00; the bridge leaves Crafting's interfaces open, a fork fix). The animated spades' stuck magic runs were a spade the server left alive at 0 hitpoints (its killer's character despawned); the Abandoned Mine's spades are hazards (Caleb, OQ-42) and the rest a documented gap (OQ-44 (a)). Herblore built in the sim (15 cleaning and 21 potion paths, with grinding; its slots: env contract v1.25). Herblore's inputs bought on the GE (V 348, 2,157 actions, 3,274 features: env contract v1.27; the bird's nest at Caleb's 1,765 gp). Herblore is calibrated on the server (`scripts/calibrate_herblore.py`: every case 1.00 after cleaning's first tick was fitted). Agility's courses built and calibrated (the Gnome Stronghold, the Barbarian Outpost and the Wilderness, `scripts/measure_agility.py`: XP/hr 1.00 to 1.03 but the Wilderness at Agility 52, 0.86; its slots: env contract v1.28); a rope swing's fail does nothing on this server, and the Wilderness log's spike pit has aggressive skeletons, which the sim's falls now meet, at their measured rate
(Caleb, OQ-46 (a)). Barbarian Fishing built and calibrated (`barb_fish` in the Fishing and Agility slots, 1.00 to 1.03; the barbarian
rod in V and on the GE: env contract v1.31). The skilling slots now price the aggressive monsters at a gathering site (the share of XP per tick the sim's own
option keeps under them). Seven Agility shortcuts are in travel, each both ways, taken from their levels on both backends
(OQ-16 (a); measured, and validated on the server at 0.90 to 1.03: env contract v1.32). Agility's
calibrations pass the gate's 600 ms speed check (11 of 11, OQ-21), and the bridge client now sets a script's tick
back as the scripts expected. Runecrafting is built and measured on the server: `rc_<rune>` at eight ruins (entering
and inside within 0.84 to 1.01 of the server), the tiaras worn and made (env contract v1.29 and v1.30),
and the Abyss's ten `abyss_rc_<rune>` paths (whole trips 0.94 to 1.00 for every rune: env contract v1.33; the skull is in the observation and the drained prayer a documented gap: Caleb, OQ-48 (a), env contract
v1.34). Chaos rune crafting is out, an intentional gap (Caleb, env contract v1.35). The essence pouches are in as the
server gives them, decay and the Dark Mage's repair included (OQ-40 (c)), and the travel model closes the Abyss, in
by the mage's teleport and out by a teleport or its exit (validated: 0.95 in, 1.02 out), so the combat slots fight
its monsters and they drop the pouches (env contract v1.36). A fight there also takes the outer ring's crowd,
with no prayer (Caleb, OQ-49 (a); its rate fitted to the server's fights: env contract v1.37). Two of the three
cases held out of the fit pass; the leeches' food (0.68 of the server's) is a documented gap (Caleb, OQ-51 (a)).
Picked flax can be banked or spun (Caleb, OQ-52: env contract v1.38), which took greedy GP from about 144k
to about 2M net worth at hour 20. The start has Druidic Ritual's 250 Herblore XP, so Herblore can be trained (Caleb,
OQ-56, v1.39). The Gem Store's uncut gems stand for 2009's 87 members' worlds on one world (Caleb, OQ-57 (a), v1.41). Crafting gathers
hides by killing cows, their bones buried (Caleb, v1.42). The scripted guide's fifth revision trains all 18 skills
(Caleb, OQ-53, OQ-58 (a), OQ-59 (b)): total level 351, net worth 131k on E1's 30 seeds; Caleb signed it off and approved every contract version the same
day, so sim v1 is frozen.
OQ-17 is decided: (a′), with every research
question answered and a simple peer review (Caleb, 2026-11-09). The plan from here is weeks 6 to 8 below. Caleb
confirmed every env contract version (to v1.37) and option catalog v1.4 the same day.
- [x] `sim/` v0: per option, check preconditions, sample outcomes, apply XP/item/GP deltas and update state. Formulas are ported from the server source; overheads start as placeholders. Decided 2026-10-28:
  - **event-level sampling**
  - **every family except the v1 skills** (four since Fletching moved into sim v0 on 2026-10-31), which come in sim v1 before E2. Quests are out (Caleb, 2026-11-06): every quest the server has is complete from the start
  - the item vocabulary list is drafted for Caleb to check (*done 2026-10-30:* 156 items, accepted)
- [x] `envs/SimEnv`: Gymnasium API, `action_masks()`, `info["duration"]`, `info["reward_vec"]`, and reward weights. *2026-10-30:* the weights are a `reset` option, as env contract §2 has it, not a wrapper.
- [x] Baselines:
  - random (masked) (*done 2026-10-30,* `rlscape/baselines`)
  - greedy XP/hr and greedy GP/hr (one-step lookahead on expected rates at the current state) (*done 2026-10-30:*
    E1 uses raw XP for XP/hr (Caleb) and net worth for GP/hr; `e1_baselines()`)
  - scripted guide routine: Claude drafts it from archived 2009 guides, cites them in `docs/resources.md`, and Caleb reviews it before E1 runs (*drafted 2026-10-30:* `docs/scripted-guide-draft.md`; signed off by Caleb on 2026-10-31 and in `e1_baselines()`)
- [x] `eval/` harness: any policy × N seeds produces metrics at game-time checkpoints every 2 h (2, 4, …, 20), written to parquet with bootstrap 95% CIs. *2026-10-30:* `rlscape/eval/harness.py` and `scripts/evaluate.py`; metrics are total level, total XP and net worth, with paired differences between policies.
- [x] Tests: masks are always respected, GP and item counts never go negative, the same seed gives the same trajectory, plus a sim speed benchmark. *Done 2026-10-31:* `tests/test_sim_properties.py` (whole random episodes; the same trajectory under other string-hash seeds) and `scripts/benchmark_sim.py` (804 decisions a second with 16 workers; the contract's target is 20k: OQ-7).
- [x] Server: `scripts/calibrate.py` runs each option K times through the bridge and logs duration, XP, item and GP distributions. *Started 2026-10-31:* woodcutting at the site (the activity alone, from the site's tile), within ±20% at four bands. Decided 2026-10-28 (env contract §7):
  - ambient bots off
  - 11 bands of calibration characters, fresh to 99, buying their own gear with 100 gp × total level; every quest the server has is complete at every band (since 2026-11-06; graded quests before)
  - about 10 runs per option at each band where it's unlocked
  - calibration-only `debug_set_levels` and `debug_complete_quest` commands
  - the server at 50 ms ticks, with a speed check at 600 ms in the gate (Caleb, 2026-11-06, OQ-21)

**Exit:** E1 table on the sim with CIs, and calibration runs started.

### Week 3 (Oct 19–25): Masked PPO and the E2 sweep
- [x] SMDP rollout buffer, unit-tested against hand-computed returns. *Done 2026-11-08:* `rlscape/agents/smdp.py` (GAE and PBRS with γ_hr^τ) and `rlscape/agents/ppo.py` (`SMDPMaskableRolloutBuffer`, `SMDPMaskablePPO`), with a short run on the sim.
- [x] `scripts/train.py`: config files, periodic checkpoints, TensorBoard, and a decision-logger callback. *Done
  2026-11-09, in the finishing plan.*
- [x] Sanity ladder: *Done 2026-11-09 to 11-10 as the finishing plan's E2 (PR #15).*
  1. PPO solves a 3-option toy catalog with a known optimum.
  2. PPO beats random on the full catalog.
  3. Small hyperparameter sweep at w = (0.5, 0.5).
- [x] Sim v1, before E2 (built and calibrated by 2026-11-09, the speed checks passed; the gaps in `docs/post-project-gaps.md`):
  - fold in the calibration data (real duration distributions, travel and bank overheads)
  - add the four new skills (Crafting, Agility, Herblore, Runecrafting; their options are open question OQ-2). Quests are out (2026-11-06)
  - pass the **±20% sim-to-server gate** on mean XP/hr, gp/hr and duration per calibrated option, with one patch round; residual gaps are reported
- [x] **E2:** weightings (1,0), (.75,.25), (.5,.5), (.25,.75), (0,1) × 5 seeds. *Done as the finishing plan's E3,
  in normalised units (OQ-67; PR #33).*

**Exit:** first learning curves, with E2 running.

### Week 4 (Oct 26–Nov 1): Exploration (E3) and ablations (E5)
- [x] RND wrapper. **E3:** PPO vs PPO+RND at (.5,.5), 5 seeds, comparing discovery order and first-discovery time.
  *Done as the finishing plan's E4 (PR #35).*
- [x] **E5:** γ_hr sweep, raw reward vs PBRS, and option-duration granularity (short / medium / until-inventory-full).
  *Done as the finishing plan's E6a and E6b (PRs #34, #37). The granularity was cut (OQ-17 (a′)).*
- [x] Analysis utilities: time-allocation stacked areas, discovery timeline, and changepoint detection on learning
  curves (e.g. `ruptures`) for RQ2's sudden-vs-gradual question. *Done 2026-11-11: `rlscape/analysis/` and
  `scripts/figures.py`, the changepoints by ruptures' PELT (OQ-78, OQ-82).*

**Exit:** E3 and E5 results.

### Week 5 (Nov 2–8): Preference-conditioned agent (E4)
- [ ] Vector-reward env using the MO-Gymnasium API. *Cut (OQ-17 (a′), 2026-11-09): the weight-conditioned PPO that
  replaced Envelope Q needs none. SimEnv's `info["reward_vec"]` is the vector reward.*
- [ ] Envelope Q-learning from MORL-Baselines with the action-mask patch. *Cut (OQ-17 (a′)): replaced by a
  weight-conditioned PPO, the finishing plan's E5 (PR #36).*
- [x] Pareto front and hypervolume (fixed reference point) for E4 against the union of E2 agents, plus a
  training-cost comparison in env steps and wall time. *Done for the finishing plan's E5 against E3's agents
  (`scripts/figures.py`'s `pareto`, and its training-cost tables from 2026-11-21; see E5 below).*
- [x] **Midpoint review:** confirm E1–E5 are solid, then choose the stretch experiment or cut it. *Done 2026-11-09:
  the finishing plan (OQ-17 (a′)) cut the stretch.*

**Exit:** E4 Pareto figure.

### Weeks 6–8 (Nov 9–30): the finishing plan (OQ-17 (a′), Caleb, 2026-11-09)

Every research question is answered (Caleb), all on sim v1, with 5 seeds per configuration. RQ5 is bounded, not tested (OQ-1 (C′)).

**Numbering** (Caleb, 2026-11-09, OQ-63): from here on, the experiments are numbered with the sanity ladder after
E1. Everything above this plan, the approved documents and the records use the proposal's numbers:

  | The proposal's | Now (OQ-63) |
  |---|---|
  | E1, baselines | E1 |
  | (none: the sanity ladder) | E2 |
  | E2, the reward-weight sweep | E3 |
  | E3, exploration (RND) | E4 |
  | E4, the preference-conditioned agent (Envelope Q, now a weight-conditioned PPO) | E5 |
  | E5, ablations (γ_hr, PBRS; granularity cut) | E6a, E6b |
  | E6, real-server validation (cut; the calibration gate instead) | none |
  | E7, the stretch (cut; RQ5 bounded, OQ-1 (C′)) | none |

**Branches** (Caleb, OQ-61, OQ-62 and OQ-63 for the names):
- each experiment runs on its own `experiment/<name>` branch from `main`, after the `sim-v1.1` tag (`sim-v1`, PR #8's
  merge, with OQ-64's directional walks),
  its config `configs/<name>.yaml` and its summary `results/summary/<name>/`:

  | Experiment | Branch, config and summary name |
  |---|---|
  | E1, the baselines | `e1-baselines` |
  | E2, the sanity ladder | `e2-ppo-sanity-ladder` |
  | E3, the reward-weight sweep | `e3-reward-weight-sweep` |
  | E4, PPO + RND | `e4-rnd-exploration` |
  | E5, the weight-conditioned PPO | `e5-weight-conditioned-ppo` |
  | E6a, the γ_hr sweep | `e6a-discount-sweep` |
  | E6b, PBRS | `e6b-pbrs-shaping` |

- shared tooling (the mask speed-up, `train.py`, `results/summary/`) goes into `main` first;
- each experiment merges back by its own PR, its summary committed.

**Cut** (in the proposal's numbers):
- E4's Envelope Q, replaced by a weight-conditioned PPO (E5 now);
- `ServerEnv` and E6's replays, with the calibration gate's results per option as the sim-to-real evidence;
- E5's option granularity, which no research question asks about;
- E7 as planned.

The old weeks 6 to 8 (E6 on the server, the stretch, a replay with the client) are superseded.

*Nov 9–10: freeze and tooling*
- [x] Sim v1.1 (2026-11-09, OQ-64 (a), env contract v1.43): walks are directional, so an episode depends only on its
  seed. Found by the mask speed-up's proof, it's its own PR; E1 is rerun on it.
- [x] Freeze sim v1 (done 2026-11-09, a day early: Caleb approved every contract version and the guide). The Runecrafting work is all in: the Abyss's fights by OQ-49 (a) are built, with the
  leeches a documented gap (OQ-51 (a)). The gate's 600 ms speed checks for Crafting, Herblore and Runecrafting
  (OQ-21) pass, 43 of 43 (2026-11-09). Picked flax can be banked or spun (OQ-52, env contract v1.38). Caleb confirmed
  every env contract version (to v1.42), option catalog v1.4 and the guide's fifth revision on 2026-11-09.
- [x] `results/summary/` committed: `scripts/publish_summary.py` (CSV tables, `config.json`, a README; a dirty tree
  refused) and `evaluate.py --config configs/<name>.yaml` (tooling PR, 2026-11-09).
- [x] Speed up the action mask without changing its results (2026-11-09): routes remembered and the cheap checks
  first, 1.49× on E1's episodes (the mask was 88% of a decision), every digest of E1's 120 episodes unchanged.
- [x] `scripts/train.py` (2026-11-09):
  - one config file per experiment (`configs/`), its `ppo` section passed to SMDPMaskablePPO as it is;
  - periodic checkpoints, TensorBoard and a per-episode learning curve;
  - the decision logger (about 0.6 GB a 1M-decision run);
  - each run's config, its hash and the provenance taken at the start;
  - `--jobs N`, seeds in parallel: four runs of 4 envs make about 1M decisions an hour in all.

*Nov 11–12: does PPO learn?*
- [x] **E1** rerun on sim v1: random, greedy XP/hr, greedy GP/hr and the scripted guide, 30 seeds (run 2026-11-09,
  PR #10).
- [x] **E2, the sanity ladder** (after E1: its second rung is judged against E1's random; PR #15). Its design is OQ-65
  (Caleb, 2026-11-09):
  1. a synthetic 3-option env (work, train, idle) with its optimum computed exactly;
  2. PPO beats random on the full catalog, answered by the sweep's best variant, evaluated with sampled actions on
     E1's 30 seeds;
  3. the sweep at (.5, .5): GAE λ {0.95, 0.99} × learning rate {1e-4, 3e-4}, entropy 0.01, 2 seeds each, 1M
     decisions a run (2M for E3 to E6 if E2's curves still rise at 1M). OQ-66 replaced OQ-65's entropy factor with λ
     after rung 1 failed at λ 0.95 (70% of the optimum, under-investing).

  *Run 2026-11-09 to 11-10:*
  - **Rung 1 passes** (Caleb, OQ-68): at λ 0.99 and 2M decisions, 94.9% and 94.4% of the optimum, reported with its
    numbers.
  - **Rung 3, the sweep:** the best variant is λ 0.95 with learning rate 3e-4, still rising at 1M, so E3 to E6 train
    for 2M decisions (Caleb, OQ-69).
  - **Rung 2 passes:** it beats random by +59 and +55 reward an episode, paired over E1's 30 seeds. It's 11 to 15
    below the guide.
  - **At (.5, .5) the agents learn skill only:** a level outweighs 100,000 gp. E3 to E6 give their weights in
    normalised units, E1's best 20-hour gain on each objective (Caleb, OQ-67).
- [x] The tooling E2 needs, shared by E3 to E6 (2026-11-09): sweeps in `train.py`, trained policies in the eval
  harness, and `scripts/publish_training.py`.
- [x] Normalised reward weights for E3 to E6 (2026-11-10, OQ-67): `env.normalised_weights` in a config, converted to
  SimEnv's by `rlscape/envs/weights.py`.
- [x] The replay page (2026-11-10, OQ-70): `scripts/replay.py <run dir>` plays a run's checkpoints on one seed and writes
  one HTML page, with a timeline, a map, the policy's choices, the skills and the curves. It's the demo, built early.
- [x] The training queue (2026-11-11): `scripts/train_queue.py` trains several experiments' runs from one queue, each
  in its experiment's worktree (`--jobs` counts every training run on the machine), seed 0 of every experiment
  first. From the restart on sim v1.2 it trained E3's to E6's 50 runs, both rounds. The worktrees
  `D:\ReinforcementScaping-e4`, `-e6b` and `-e5` are set up like E6a's.

*Nov 13–18: the experiments* (the runs overlap the building)

*Restarted on sim v1.2 (2026-11-11, OQ-75 (c), Caleb):* woodcutting's fletch slot, so Fletching can be trained. E3
was stopped with 13 of its 25 runs done on v1.1, which are kept aside (`runs/e3-reward-weight-sweep-sim-v1.1` in its
worktree). E1 was rerun on v1.2 and OQ-67's units recomputed from it. E3 to E6 train again from one queue, all 50
runs, seed 0 of every experiment first: about 110 hours, so done around Nov 16 to 17. E2 stays on v1.1.

*Restarted after a Windows Update restart (2026-11-12):* the machine restarted at 02:29 and killed E3's four seed-0
runs, which started again from the start at 04:41 (about 6 hours lost, so the queue ends around midday Nov 16).
Windows Update was paused until the last test was done (Caleb; back on 2026-11-23). The restarted (0, 1) run
repeated the killed one's 1.0M decisions byte for byte.

*On sim v1.3 from the evening of 2026-11-12 (Caleb, `m002-death-budget`):* E3's (.5, .5) seed 1 hung from 18:54 on a
sim v1.2 stop, a Draynor fisher's kill after its option's budget. Sim v1.3 ends such an option at the budget and
equals sim v1.2 wherever sim v1.2 completes, so nothing is retrained. The run trains again, and the runs not yet
started train on sim v1.3 (`main` merged into the five worktrees, the queue relaunched at 22:42).

*Restarted after a Claude app update (2026-11-13, Caleb, `m002-app-update`):* the app updated itself at 00:13 and
killed the queue and its five runs (about 2.4 hours of the queue lost). They train again from the start, and the queue
now runs from Task Scheduler, outside the app, from 00:23. With 11 of the 50 runs done, it ends around Nov 16.

*Trained again with the trainer's two fixes (2026-11-15, Caleb, `m002-collapse-diagnosis`, `m002-rerun`):* the 50
runs finished at 12:35, but 8 ended looping options that change nothing (E6b's five, E6a γ0.9's seeds 0 and 3, E3's
(0, 1) seed 1), and every run's critic value grew through training. The fixes (env contract v1.46): the horizon isn't
bootstrapped, and each decision is discounted as at least 100 ticks. With both, E6a γ0.9 seed 0 didn't collapse to
800k decisions, where it had. All 50 runs train again, seed 0 of every experiment first, from about 01:00 on Nov 16:
about 80 hours, so done around Nov 19 morning, and the analysis moves to Nov 20–22. The first 50 are kept aside in
each worktree (`runs/<name>-bootstrap`). E2 stays as it was.

*On sim v1.4 from 2026-11-16 (Caleb, `m002-tan-guard`):* E6a's γ_hr 0.5 seed 0 failed at 05:47 on a sim v1.3 error: a
tanning path whose walk to the tanner paid a charter with every coin it carried, the fee's among them. Sim v1.4's
tanner tans nothing then, as it already did when a fare left fewer coins than the fee, and equals sim v1.3 wherever
sim v1.3 completes, so nothing else is retrained. The run trains again from the start, and the runs not yet started
train on sim v1.4.

*Finished (2026-11-19 to 11-21):* the 50 reruns finished at 10:00 on Nov 19, none failed. 14 trained on sim v1.3
(E3's seeds 0 and 1 at every weighting, and one run each of E6a, E4, E5 and E6b) and the rest on sim v1.4. Their
evaluations ran on sim v1.4 on Nov 19, and the five summaries were published by Nov 20 (`m002-rerun-evals`). Each
experiment merged into `main` by its own PR on Nov 21 (`m002-experiment-merges`). The loop census of both rounds is
in the decision log (`m002-final-census`).
- [x] **E3, the reward-weight sweep** (RQ1 to RQ3): (1,0), (.75,.25), (.5,.5), (.25,.75) and (0,1) in normalised
  units (OQ-67), 5 seeds each, 2M decisions a run (OQ-69), with E2's winner: λ 0.95, learning rate 3e-4, entropy 0.01.
  *Done (PR #33),* with the first round's evaluation beside it at the mixed weightings for the discussion (OQ-92 (b)).
- [x] **E4, PPO + RND** (RQ2, RQ4, H3): the RND wrapper, then PPO + RND at (.5,.5), 5 seeds, against E3's (.5,.5).
  - The wrapper is built (2026-11-10, `rlscape/agents/rnd.py`) with Caleb's settings (OQ-72): a bonus spread of
    0.75, centred, read from the character's state. `configs/e4-rnd-exploration.yaml` is E3's (.5,.5) plus
    RND. *Done (PR #35).*
- [x] **E5, the weight-conditioned PPO** (RQ3's second half): weights drawn each episode and given in the
  observation. Pareto coverage, hypervolume and training cost against E3's agents.
  - *Built 2026-11-10* (`rlscape/agents/conditioned.py`; Caleb, OQ-74): u ~ U[0, 1] each episode, 2M decisions a
    run, evaluated at E3's five weightings and every 0.1 (13). *Done (PR #36).* The Pareto coverage and hypervolume
    are in the figures. *Added 2026-11-21:* the training cost, per front as the hypervolumes are
    (`training_cost.csv`): E3's five agents at a seed take 10.0M decisions and 38.1 hours, E5's one 2.0M and 8.4.
- [x] **E6** (RQ4), at (.5,.5) with 5 seeds each:
  - **E6a:** two more γ_hr values (§3's set: 0.5, 0.9, 0.99). *Done (PR #34).*
  - **E6b:** raw reward against PBRS. Φ is §3's candidate, the best GP/hr the current unlocks allow, confirmed when
    it's built.
    *Built 2026-11-10* (`rlscape/agents/pbrs.py`; Caleb confirmed Φ, OQ-73): the discounted wealth reward of the
    best gathering income the levels and unlocks allow, over the time left. `configs/e6b-pbrs-shaping.yaml` is
    E3's (.5,.5) plus PBRS. *Done (PR #37).* Two of its policies' evaluation episodes stop at the
    100,000-decision cap, which its summary's README marks (OQ-91 (b)).

*Nov 19–21: analysis*
- [x] The figures:
  - learning curves with CIs and changepoints;
  - the Pareto front and hypervolume;
  - time allocation as stacked areas;
  - the discovery timeline;
  - the sim-to-real table from the calibration gate;
  - RQ5's bound (OQ-1 (C′)): prayer flicking by the scripted flick's measured effect, click-ahead pathing by
    the policies' share of game time walking (replayed in the seeded sim: the decision logs don't record it).
- [x] Every figure and table is rebuilt by one script from small summaries committed to `results/summary/`.
  *Built 2026-11-11:* `scripts/figures.py` (`rlscape/analysis/`) makes the first four, with RQ1's progress at the
  checkpoints, each policy's activity mix in evaluation and the policy's entropy, from whichever experiments are
  published, and the tables for the milestones (OQ-83), sample efficiency (OQ-84), consistency across seeds (OQ-85)
  and each run's sudden-or-gradual verdict under OQ-82's rule and OQ-78's. *Built 2026-11-12* (Caleb: re-simulated on
  sim-v1.2; a family table and a case appendix): the sim-to-real tables, from `results/summary/sim-to-real/`
  (`scripts/sim_to_real.py`: every calibration case's latest server runs against sim-v1.2, no server needed). *Added
  2026-11-12* (OQ-87 (a)): RQ5's walking tables, from the evaluation traces' walk counter. *Added 2026-11-20* (Caleb,
  OQ-92 (b)): the Gem Store tables for the discussion, E3's first round
  (`results/summary/e3-reward-weight-sweep-bootstrap/`) beside its rerun at the mixed weightings. *Done 2026-11-21:*
  with every experiment's summary on `main`, `scripts/figures.py` makes all nine figures and every table, none
  skipped.
- [x] The data the figures need (2026-11-11): each evaluation episode's trace (`decisions.csv.gz` in an experiment's
  summary) and each training run's behaviour from its decision log (`behaviour_bins.csv`, `behaviour_options.csv.gz`,
  `first_choices.csv.gz` in its training summary).

*Nov 22–25: the draft and the copy to review*
- [ ] The report answers RQ1 to RQ4 (and RQ5 as a bound, OQ-1 (C′)), with a verdict on each of H1 to H3. Negative results
  get their supporting analysis. *The verdicts (Caleb, 2026-11-22):* H1 and H2 partly supported, H3 supported.
  The reviewer's guide's claims table has each one's evidence, and `scripts/figures.py` tables what they rest on
  (`weighted_value.csv`, `mix_divergence.csv`).
- [ ] Its wording (Caleb, OQ-71 (a)): a decision is one option chosen, defined once in the method. A run's
  length is "training decisions" with its episodes beside it; an episode's count is "decisions per episode".
- [ ] The peer review kept simple (Caleb, OQ-50 (a)): the whole repo at a tagged commit, with a two-page `README.md`
  as the reviewer's guide; the report has the same map as a half-page appendix. *Drafted 2026-11-12*
  (`README.md`, PR #28; OQ-88: the check runs on Windows). Still to do: the tag it names, once the report's numbers
  are in.

*Nov 26: peer review (Thanksgiving week runs at half capacity). Nov 27–30: revisions, and the demo (sim replays of an
early, a middle and a final checkpoint: `scripts/replay.py`, built 2026-11-10, OQ-70). The report is due Mon Nov 30.*

*After the last test* (Caleb, 2026-11-12):
- [x] **Turn Windows Update back on** (Settings → Windows Update → Resume updates) once every run, evaluation and
  test is done. It's paused from Nov 12 so that a forced restart can't kill a run: one at 02:29 on Nov 12 killed the
  queue and cost about 6 hours. *Done 2026-11-23 (Caleb): the Settings page shows updates on; Windows had already
  stopped recording any pause.*

**If time runs short:** depth gives way, not a research question (from Caleb's answer):
- fewer γ_hr values or weightings, or shorter runs;
- fewer than 5 seeds goes last, since the proposal promises at least 5.

Caleb picks the cut.

**If PPO doesn't learn by Nov 12:** debug it on the ladder. If it still doesn't learn by about Nov 16, the report
covers E1 and E2 with an analysis of why, which `Requirements.md` accepts.

---

## 5. Critical path and fallbacks

- **Critical path:** env contract → sim v0 → MaskablePPO + SMDP buffer → E2. E3–E6 all reuse E2's agents or infrastructure.
- **If G1 or G2 fails:** go sim-primary. Calibrate from source formulas plus manual timing in Singleplayer, and shrink E6 to a manual spot-check.
- **If PPO hasn't beaten greedy by week 4:** that's an acceptable finding, but first check that the catalog actually contains delayed-payoff investments. If greedy is optimal by construction, H1 can't be tested. Add an investment structure (e.g. Smithing → better gear → better combat GP) before concluding.
- **If behind at the week-5 midpoint:** drop E7 first, then cut E5 down to γ and PBRS. *Superseded (2026-11-09) by
  the finishing plan's "If time runs short" (weeks 6–8).*

---

## 6. Weekly rhythm

Trimmed by Caleb on 2026-10-28. The interaction records and the decision log already give a running account, so
there are no Monday goal entries and no `wkN` tags. The Friday status entries went too (Caleb, 2026-11-09, OQ-55): the
records, the decision log and the status line above keep the account.

- Each results table goes into `results/summary/` with the exact config hash that produced it.

---

## 7. Appendix A: Option catalog v0 (draft)

*Superseded by `docs/option-catalog.md` (v0.6), which replaces this appendix. Kept for history.*

**Starting state (fixed):** a fresh level-3 character at Lumbridge: all skills 1 except Hitpoints 10. The starter kit comes from `tutisland/handlers/iface/CharacterDesign.java`:
- **Inventory:** bronze axe, tinderbox, small fishing net, shrimps, bucket, pot, bread, bronze pickaxe, bronze dagger, bronze sword, wooden shield, shortbow, 25 bronze arrows, and runes (25 air, 15 mind, 6 water, 4 earth, 2 body).
- **Bank:** 25 coins.

Since the kit includes a pickaxe, axe, net, weapons and a shield, all the early gathering and melee options are unlocked from tick 0. Gear upgrades and the cage, rod and harpoon are what have to be earned.

| Family | Example options | Preconditions / unlocks |
|---|---|---|
| **Combat** | Chickens / cows (Lumbridge), goblins, Al Kharid warriors, barbarians, hill giants, moss giants, … × attack style (Att / Str / Def) × food choice | Combat levels, weapon and armor tier, food in inventory |
| Woodcutting | Normal trees (Lumbridge), oaks / willows (Draynor) | Axe tier, WC level |
| Fishing | Shrimp (Lumbridge Swamp), trout / salmon (Barbarian Village), lobster (Karamja) | Net / rod / cage; feathers or bait from the GE |
| Mining | Copper / tin (Lumbridge Swamp), iron (Al Kharid), coal | Pickaxe tier |
| Smithing | Smelt bronze / iron bars; smith items (Varrock) | Ores from Mining or the GE |
| Cooking | Cook fish at a range | Raw fish |
| Firemaking | Burn logs | Logs, tinderbox |
| Prayer | Bury bones from combat | Bones |
| Thieving | Men / women, farmers (`ManThiever` and `FarmerThiever` already exist) | Thieving level |
| Economy | Bank all; buy tool / weapon / armor tier Y from GE bot stock or shops; sell item X at the GE (filled at the frozen 2009 price by `ge_frozen_buyer`), to shops, or by High Level Alchemy. All GE trades happen at frozen January 2009 prices. | GP, levels, Magic 55 for High Alchemy |

**Why combat matters for H1:** it creates the strongest delayed-payoff loops in the game:
- Fishing + Cooking → food → longer trips at tougher monsters.
- GP or Mining + Smithing → better gear → faster kills and better drops.
- Combat levels → higher-tier monsters (cowhides → big bones → better loot).

**How combat works in the sim:** a combat option is "fight monster M with style S until N kills or out of food". Its outcome is computed analytically from the server's own combat formulas:
- player accuracy and max hit vs the NPC's defense and HP → kills per hour
- NPC accuracy and max hit vs the player's defense → damage taken → food eaten
- death → respawn at Lumbridge with the 2009-era item-loss rules

Calibrate against the existing `ChickenKiller`, `CowKiller`, `GenericSlayerBot` and `GreenDragonKiller` scripts. **Combat fidelity is the biggest sim risk**, so calibrate it first in week 2.

---

## 8. Open questions

Open questions are in `docs/open-questions-log.md`; answered ones are in
`docs/decision-log.md`.

---

## 9. Appendix B: Stretch options (E7)

Only attempted after E1–E6 are solid. Pick at most one.

| | **A. LLM planner (Voyager-style)** | **B. DreamerV3** | **C. Learned micro-options (RQ5)** | **D. None** |
|---|---|---|---|---|
| **What it is** | An LLM (e.g. Claude) chooses the next option from a text description of the state, with a skill library and self-reflection like Voyager. No training: it reasons about the game zero-shot. | A model-based RL agent: learns a world model of the sim and trains its policy inside imagined rollouts. | Replace one scripted low-level skill (pathing or prayer flicking) with a learned policy, then check whether the high-level agent does better. | Spend week 7 on deeper analysis of E1–E6 instead. |
| **Question it answers** | Can prior knowledge of RuneScape (from pretraining) match or beat an agent that learned purely from reward? A strong non-RL comparison point for RQ1. | Is model-based RL more sample-efficient than PPO on this long-horizon, delayed-payoff problem? | RQ5: does learning at the low level add anything over scripts? | — |
| **Build effort** | Low–medium (~3–4 days). Reuses the env contract; mostly prompt design, a state-to-text formatter, and masking invalid choices. | Medium (~4–5 days). The official implementation is JAX. Needs adapting to masked discrete actions and the SMDP time structure. | High (~1.5–2 weeks). Needs a new tick-level environment, likely on the real server, which is slow. | None |
| **Compute / cost** | API cost. Roughly 150–300 decisions per 20 h episode × 5 seeds × a few variants is likely tens of dollars with a mid-size model (rough estimate; check current pricing before committing); prompt caching cuts it a lot. Runs fine on this machine. | GPU-heavy. JAX with GPU on Windows needs WSL2 (only the Docker distro is installed now). 8 GB of VRAM is tight; use a small model size. | Many tick-level samples; real-server throughput becomes the bottleneck. | — |
| **Risk** | Low. Always produces a result, and a negative one is still interesting. Watch for "did the model just recall a guide?", and frame that honestly. | Medium–high. Setup on Windows and tuning can eat the whole week. | High. Very unlikely to finish in one week. | None |
| **Report value** | High: a vivid contrast in strategy (how the LLM's activity mix compares with PPO's). | Medium–high if it works; an algorithm-comparison result. | High if it works, but it probably won't fit the schedule. | Better polish on the core RQs. |

**Closest prior work:** RuneBench (`docs/resources.md` [18]) benchmarks LLM coding agents on RuneScape skill-XP and gold tasks. rs-sdk [19] shows a tool (MCP) interface and wiki-knowledge setup that option A could follow.

*Superseded (2026-11-09): OQ-17 (a′) leaves no time for a stretch. RQ5 is bounded instead (Caleb, 2026-11-12,
OQ-1 (C′)).*

**Recommendation: A (LLM planner).** It's the cheapest, the most likely to finish, and it adds a qualitatively different comparison to RQ1. It needs an Anthropic API key and a small budget (a cap of ~$25–50 is plenty). **B** is the pick if you'd rather keep the project pure-RL and are willing to set up WSL2 Ubuntu early. **C** is best kept as "future work" in the report.
