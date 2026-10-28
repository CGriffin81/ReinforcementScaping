# Roadmap: Learning to Climb (HRL for Skill and Wealth in 2009Scape)

Built from `CS898BG_RL_Project_Proposal_2009Scape.pdf` and `Requirements.md`.
**Week 1 starts Mon Oct 5, 2026. The final report is due Mon Nov 30, 2026.**

**Fixed design decisions** (Oct 5):
- Every episode starts from a **fresh level-3 character**.
- Training episodes are **20 game-hours**, evaluated at **checkpoints every 2 game-hours** (2, 4, …, 20).
- **Combat is in scope** and is a core part of the option catalog.
- Claude writes the code; Caleb reviews and runs it. The AI-assisted code policy from Promethean applies (reference pending).

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
┌────────────── 2009Scape server (Kotlin/Java, JDK 11, Maven, MySQL) ────────────┐
│ content/rl/RLBridge.kt     socket server: reset / options / step / state        │
│ content/rl/options/*.kt    one Script per option, adapted from global/bots/*    │
│ AIPlayer (no client) · tick loop patched to a configurable interval             │
│ Grand Exchange (bots_influence_ge_price) · adventurer bots                      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Bridge protocol (draft)**

| Message       | Payload                       | Returns |
|---------------|-------------------------------|---------|
| `reset`       | start-template id, seed       | full state |
| `options`     | —                             | option catalog + current mask |
| `step`        | option id                     | state after the option ends, ticks elapsed, XP/item/GP deltas, termination reason |
| `state`       | —                             | levels, XP, inventory, bank, equipment, region, GP, GE snapshot |
| `set_tick_ms` | int                           | ack |

---

## 2. Repository layout (proposed)

```
ReinforcementScaping/
├── docs/          proposal, env-contract.md, option-catalog.md, decision-log.md
├── rlscape/
│   ├── sim/       surrogate simulator; catalog/*.yaml (options, items, prices_v1)
│   ├── envs/      SimEnv, ServerEnv, wrappers (reward weights, PBRS, RND, MO vector)
│   ├── bridge/    socket client for the server
│   ├── agents/    SMDP rollout buffer, RND module, masked Envelope adapter
│   ├── baselines/ random, greedy_xp, greedy_gp, scripted_guide
│   ├── eval/      harness, bootstrap CIs, hypervolume, discovery metrics
│   └── analysis/  figure scripts
├── configs/       one YAML per experiment family
├── scripts/       train.py, evaluate.py, sweep.py, calibrate.py
├── server/        fork of 2009scape (git submodule) + RL bridge
├── tests/
└── results/       (git-ignored) runs, checkpoints, logs
```

---

## 3. Technical decisions to settle early

| Issue | Why it matters | Plan |
|---|---|---|
| **SMDP discounting** | Options run for different amounts of game time. SB3 applies one γ per decision, so a 2-min bank trip is discounted the same as a 40-min woodcutting trip. That's wrong under a game-time horizon and would confound the E5 discount ablation. | The env reports `info["duration"]`. Subclass sb3-contrib's `MaskableRolloutBuffer` (plus a small `collect_rollouts` override to store τ) so GAE uses γ^τ. Define γ **per game-hour** (e.g. γ_hr ∈ {0.5, 0.9, 0.99}). |
| **PBRS in an SMDP** | Ng et al.'s policy-invariance guarantee only holds if shaping uses the agent's own discount. | F = γ^τ·Φ(s′) − Φ(s), with Φ(terminal) = 0. Candidate Φ: best GP/hr available from current unlocks, which directly encodes "investing pays off". |
| **What counts as wealth** | If equipment doesn't count toward bank value, buying an axe looks like losing money. The agent is penalized for investing, which biases the H1 test. | Wealth = GP + (bank + inventory + equipped items) × the **fixed** price table, i.e. net worth. |
| **Skill reward normalization** | Raw XP grows exponentially per level, so high-level XP would dominate. Total level is the reported metric. | Reward fractional level gained (level + progress toward the next level) to match the reported metric. Wealth reward = Δnet worth / a fixed scale (e.g. 100k GP). |
| **Valuation table** | Runs are only comparable if net worth is computed the same way every time. | **Done (Caleb's formula):** `data/prices_v2.csv` = max(high alchemy − nature rune, January 2009 GE price from the RuneScape Wiki), coins = 1. Fixed for the whole study. `prices_v1` (the 10-hour snapshot) is superseded but kept. |
| **RND with masking** | Neither SB3 nor sb3-contrib includes RND. | v1: a VecEnv wrapper that adds a normalized, non-episodic intrinsic reward for MaskablePPO. v2, only if v1 results are ambiguous: dual value heads, using CleanRL's `ppo_rnd_envpool.py` as reference. |
| **Masking in Envelope Q** | MORL-Baselines' Envelope Q-learning has no action-mask support out of the box. | Patch action selection and the target max to set invalid Q to −∞, and store the next-state mask in the replay buffer. |
| **Bot helpers cut corners** (found Oct 5) | `ScriptAPI.sellOnGE`/`sellAllOnGe` delete the items and pay nothing (`GrandExchange.addBotOffer`). `buyFromGE` never dispatches. `teleportToGE` and `withdraw` skip travel. And any GE offer from an artificial player becomes a bot offer. | **Done:** the agent's character is an `RLPlayer`, treated as a human by every game rule. The bridge trades through the human GE path (`ge_offer` / `ge_collect`, only at the GE). Gathering and combat logic can still be borrowed from the bundled scripts. |
| **Python version** | This machine has Python 3.14, and RL libraries lag new Python releases. | Use a `uv` project pinned to Python 3.12. |
| **Windows multiprocessing** | `SubprocVecEnv` uses spawn on Windows. | Put every entry point behind `if __name__ == "__main__":` and keep env construction picklable. |
| **Reproducibility** | Every comparison needs ≥5 seeds with bootstrap CIs. | Seeded `numpy.random.Generator` in the sim; each run dir stores the config, config hash and git SHA. |

### Throughput estimates (to sanity-check, not commitments)

- **Sim:** target ≥20k decisions/s on 16 threads. A 20-game-hour episode has roughly 100–300 decisions, so a 5M-decision run should take roughly 15–30 min including PPO updates, and all of E2 (25 runs) fits overnight. Small-MLP PPO runs faster on CPU (Ryzen 7 5800X) than on the GPU. Save the RTX 3050 for Envelope Q and the stretch work.
- **Real server:** at the default 600 ms tick, 1 game-hour takes 1 wall-hour. With a 10× tick and 8 RL-controlled `AIPlayer`s in one world, 1 wall-hour ≈ 80 game-hours. Then E6 (4 configs × 5 seeds × 20 game-hours = 400 game-hours) takes about 5 wall-hours. **Without the speedup it takes about 50 wall-hours**, which is why decision gate G1 matters. A fallback is to validate only the first 10 game-hours (checkpoints 2–10).
- **G1 measured (Oct 5):** 34× at a 15 ms tick with one world and 100 ambient bots. So 8 parallel RL characters would give about 270 game-hours per wall-hour, and E6's 400 game-hours fit in about 1.5 wall-hours. About 2.6 ms per tick is fixed overhead, so going much faster probably means turning down the ambient bots (not yet tried). Still open: about 160 `System.currentTimeMillis()` call sites stay on wall-clock time. Most are out of scope (farming, brewing, minigames), but the 10 s "in combat" flag (`CombatPulse.kt` / `Entity.java`) is in scope and needs checking once combat options exist.

---

## 4. Phased plan

### Week 1 (Oct 5–11): Foundations and decision gate
**Goal:** a go/no-go on the real server, an option catalog v0, and a Python skeleton.

*Server track*
- [x] Install JDK 11 (Temurin 11.0.32 via winget). Maven isn't needed because the repo ships `Server/mvnw.cmd`.
- [x] Fork the server: [CGriffin81/2009scape-rl](https://github.com/CGriffin81/2009scape-rl) (private, full upstream history; `master` = upstream `bea45a9e`, our work on `rl`). Linked here as the `server/` submodule.
- [x] Build the server jar (`Server/target/server-1.0.0-jar-with-dependencies.jar`, ~3 min cold build).
- [x] Run it against MariaDB (`infra/docker-compose.db.yml`, localhost-only). The first launch took 418 s, mostly filling the GE price index in SQLite; built-in bots start ticking right away. The game port 43595 binds to **all interfaces**, so restrict it to localhost before leaving the server up for long stretches.
- [ ] Install Singleplayer through the Saradomin launcher, for reference play and for watching bots.
- [x] Read `core/game/bots/` (`AIPlayer`, `Script`, `ScriptAPI`, `GeneralBotCreator`) and the bundled-script economy helpers.
- [x] **G1, tick and headless: PASS.** `server.tick_ms` is now configurable and changeable at runtime through the bridge. Measured with 100 ambient bots: 4.9× at 120 ms, 9.5× at 60 ms, 17.5× at 30 ms, 34× at 15 ms (about 2.6 ms of overhead per tick). The "in combat" wall-clock flag is still untested under speedup.
- [x] **G2, state and actions: PASS.** `content/rl/RLBridge.kt` + `RLCommands.kt` in the fork, and `rlscape/bridge/client.py` here. Spawns a character exactly as it leaves Tutorial Island, reads its full state, and drives authentic interactions: 600 ticks of chopping gave 10 logs and 250 XP. Covered by `scripts/gate_check.py` and `tests/test_bridge_live.py`.
- [x] **G3, GE dynamics: answered. The market is bot-stocked and prices are static.** A 10-game-hour warm-up from a fresh GE (`scripts/ge_warmup.py`) changed 0 of 7,324 prices and saw 0 trades, while bot stock grew to 19,675 units of 145 items. Nothing in this world places buy orders, so the price index never moves. See the decision log for the mechanics and the pending economy decisions.
- [x] Export the fixed price table: `data/prices_v1.csv` plus `.meta.json` (the 10-hour snapshot, per Caleb's decision; identical to the seeded high-alchemy values), and `data/grandexchange_warmup10h.db` for resetting the real server's GE.

*Python track*
- [x] `git init`, and a `uv` project pinned to Python 3.12 (`rlscape` package, pytest).
- [ ] Add the RL stack when the sim needs it: gymnasium, torch, stable-baselines3, sb3-contrib, morl-baselines, mo-gymnasium, tensorboard, pandas, pyarrow, matplotlib.
- [~] `docs/env-contract.md` **v0.2 (2026-10-27):** questions 1–4 decided by Caleb; question 5 (selling quantity) open.
- [~] `docs/option-catalog.md` **v0.2, Proposed (2026-10-27):** about 425 actions, rebuilt around Caleb's decisions (no auto-banking, Magic and alchemy, any-enemy combat through candidate slots, frozen seller plus shops). Open: selling quantity, buy actions per source, the candidate-slot design.

**Deliverable:** a `docs/decision-log.md` entry with G1–G3 results and the chosen path: real server + sim, or sim-primary.

### Week 2 (Oct 12–18): Surrogate sim v0, environment, baselines (E1)

*Started 2026-10-27 (catching up):* `rlscape/gamedata` (server data loaders) and `rlscape/combat` (formulas ported from the server, plus the rate model), with tests. Then the cleaned NPC pool (cache definitions), inventory-aware gp/hr and the retreat-aware filter. *2026-10-28:* the access table (gated areas, quest-only NPCs, Slayer levels). Next: the simulator state and options.
- [ ] `sim/`: per option, check preconditions, sample a duration, apply XP/item/GP deltas and update state. Formulas are ported from the server source; overheads start as placeholders.
- [ ] `envs/SimEnv`: Gymnasium API, `action_masks()`, `info["duration"]`, `info["reward_vec"]`, and a reward-weight wrapper.
- [ ] Baselines:
  - random (masked)
  - greedy XP/hr and greedy GP/hr (one-step lookahead on expected rates at the current state)
  - scripted guide routine (hand-written from a 2009-era training guide)
- [ ] `eval/` harness: any policy × N seeds produces metrics at game-time checkpoints every 2 h (2, 4, …, 20), written to parquet with bootstrap 95% CIs.
- [ ] Tests: masks are always respected, GP and item counts never go negative, the same seed gives the same trajectory, plus a sim speed benchmark.
- [ ] Server: `scripts/calibrate.py` runs each option K times through the bridge and logs duration, XP, item and GP distributions.

**Exit:** E1 table on the sim with CIs, and calibration runs started.

### Week 3 (Oct 19–25): Masked PPO and the E2 sweep
- [ ] SMDP rollout buffer, unit-tested against hand-computed returns.
- [ ] `scripts/train.py`: config files, periodic checkpoints, TensorBoard, and a decision-logger callback.
- [ ] Sanity ladder:
  1. PPO solves a 3-option toy catalog with a known optimum.
  2. PPO beats random on the full catalog.
  3. Small hyperparameter sweep at w = (0.5, 0.5).
- [ ] Sim v1: fold in the calibration data (real duration distributions, travel and bank overheads).
- [ ] **E2:** weightings (1,0), (.75,.25), (.5,.5), (.25,.75), (0,1) × 5 seeds.

**Exit:** first learning curves, with E2 running.

### Week 4 (Oct 26–Nov 1): Exploration (E3) and ablations (E5)
- [ ] RND wrapper. **E3:** PPO vs PPO+RND at (.5,.5), 5 seeds, comparing discovery order and first-discovery time.
- [ ] **E5:** γ_hr sweep, raw reward vs PBRS, and option-duration granularity (short / medium / until-inventory-full).
- [ ] Analysis utilities: time-allocation stacked areas, discovery timeline, and changepoint detection on learning curves (e.g. `ruptures`) for RQ2's sudden-vs-gradual question.

**Exit:** E3 and E5 results.

### Week 5 (Nov 2–8): Preference-conditioned agent (E4)
- [ ] Vector-reward env using the MO-Gymnasium API.
- [ ] Envelope Q-learning from MORL-Baselines with the action-mask patch.
- [ ] Pareto front and hypervolume (fixed reference point) for E4 against the union of E2 agents, plus a training-cost comparison in env steps and wall time.
- [ ] **Midpoint review:** confirm E1–E5 are solid, then choose the stretch experiment or cut it.

**Exit:** E4 Pareto figure.

### Week 6 (Nov 9–15): Real-server validation (E6)
- [ ] `envs/ServerEnv` over the bridge, using the same contract.
- [ ] Replay the best checkpoint for each E2 weighting, plus the best baseline, on the server: ≥5 seeds, short horizon.
- [ ] Measure the sim-to-real gap per metric and per option (residual table). Report whether policy rankings hold (rank correlation makes a good headline number), patch the biggest gaps into sim v2, and recheck.

**Exit:** E6 gap report.

### Week 7 (Nov 16–22): Stretch experiment and behavior analysis
- [ ] **One stretch only**, chosen at the week-5 midpoint. See [Appendix B](#9-appendix-b-stretch-options-e7) for the options.
- [ ] Final figures: learning curves with CIs and annotated jumps, Pareto front, stacked-area time allocation, discovery timeline.
- [ ] Replays of an early, a middle and a final checkpoint on the same fixed scenario. Record one on the real server with the client attached.

### Week 8 (Nov 23–29): Write-up and demo
- [ ] Report that answers RQ1–RQ4 (RQ5 if attempted) explicitly, with a verdict on each of H1–H3. Negative results get their supporting analysis.
- [ ] Demo video, plus a reproducibility README with one command per experiment.
- [ ] Note: Nov 26 is Thanksgiving. Treat this week as half capacity and buffer.

---

## 5. Critical path and fallbacks

- **Critical path:** env contract → sim v0 → MaskablePPO + SMDP buffer → E2. E3–E6 all reuse E2's agents or infrastructure.
- **If G1 or G2 fails:** go sim-primary. Calibrate from source formulas plus manual timing in Singleplayer, and shrink E6 to a manual spot-check.
- **If PPO hasn't beaten greedy by week 4:** that's an acceptable finding, but first check that the catalog actually contains delayed-payoff investments. If greedy is optimal by construction, H1 can't be tested. Add an investment structure (e.g. Smithing → better gear → better combat GP) before concluding.
- **If behind at the week-5 midpoint:** drop E7 first, then cut E5 down to γ and PBRS.

---

## 6. Weekly rhythm

- Monday: write the week's goals in `docs/decision-log.md`.
- Friday: a 5-line status entry (done, blocked, changed) and a commit tag `wkN`.
- Each results table goes into `results/summary/` with the exact config hash that produced it.

---

## 7. Appendix A: Option catalog v0 (draft)

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

Answered Oct 5: due date (Nov 30), division of labor (Claude codes, Caleb reviews and runs), installs approved, fresh level-3 start, 20 h episodes with 2 h checkpoints, combat in.

Still open:
1. **Promethean AI-assisted code policy:** reference text needed so commits, disclosure and review follow it.
2. **Remote repo:** GitHub or GitLab, public or private? The modified server is an AGPLv3 fork, so a public fork has to include its source.
3. **Stretch (E7):** choose at the week-5 midpoint. See Appendix B.

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

**Recommendation: A (LLM planner).** It's the cheapest, the most likely to finish, and it adds a qualitatively different comparison to RQ1. It needs an Anthropic API key and a small budget (a cap of ~$25–50 is plenty). **B** is the pick if you'd rather keep the project pure-RL and are willing to set up WSL2 Ubuntu early. **C** is best kept as "future work" in the report.
