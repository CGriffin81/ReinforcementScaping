# Environment Contract (v1.5, Signed off)

**Status:** v1.5, 2026-10-30. Any change needs Caleb's approval and is logged in `docs/decision-log.md`.
- **v1.5** (2026-10-30, Caleb) has `ServerEnv` send its inputs as client packets (§7), after the live
  tick-manipulation test found that the bridge's direct commands land a tick late against the world's pulses.
- **v1.4** (2026-10-30) adds the last task to the observation (§3), because Caleb's deposit rule makes what a
  deposit keeps depend on it.
- **v1.3** (2026-10-30, Caleb) adds total XP to the reported metrics (§4, §6).
- **v1.2** (the same day) adds run energy and weight to the observation (§3) and the run rule to the backends
  (§7), from Caleb's buying decision Q3b (option catalog §8).
- **v1.1** (approved by Caleb on 2026-10-28) adds the simulation decisions: five more trainable skills (§5),
  event-level sampling, the ambient-bots setting, and the calibration gate and characters (§7).
- **v1.0** added the death rule (§1) to v0.6.

Both backends implement this contract exactly: `SimEnv` (the surrogate simulator) and `ServerEnv` (2009Scape
through the bridge). Any policy, baseline or logger written against it runs on either one.

## 1. Time and episodes

- **Game time:** 1 tick = 0.6 s. Durations are reported in ticks.
- **Episode:** `reset(seed)` produces a fresh level-3 character exactly as it leaves Tutorial Island, at
  Lumbridge (3233, 3230), with the starter kit and 25 coins in the bank.
- **Horizon:** 20 game-hours = 120,000 ticks. Checkpoints every 2 game-hours (12,000 ticks).
- **Decision structure:** a semi-MDP. Each `step(option)` runs one option until it ends and returns its
  duration τ in ticks.
  - **Activity options** (gathering, processing, combat, thieving, training spells) end at the first of:
    - the activity's fixed duration *D* (decided: 15 game-minutes by default; 5 and 45 for the E5 ablation)
    - a full inventory
    - inputs running out
    - out of food or ammunition
    - death
    - the horizon
  - **Banking is never automatic** (decided). When the inventory fills, the agent chooses what to do: bank,
    drop, sell, alch, process, or keep going with something else.
- **Death doesn't end the episode** (decided, 2026-10-28). The option ends with `died`, the character respawns in
  Lumbridge, and the episode carries on. Items follow the server's rules (`DeathTask.getContainers`,
  `GraveController`):
  - the **3 most valuable items** (by alchemy value) from the inventory and equipment are kept. A skulled character
    keeps none, and Protect Item adds one.
  - **outside the Wilderness**, everything else goes into a gravestone that lasts **2 minutes** (200 ticks; the
    free memorial plaque). The `reclaim_gravestone` option (option catalog §5) walks back and takes it all back, if
    it gets there in time.
  - **in the Wilderness** (or when skulled) there is no gravestone, and everything else is lost.
  - lost items leave net worth, just like dropped ones.
- **Horizon cut-off:** an option that would run past the horizon is cut off there. The episode ends as
  *truncated* (not terminal), so value bootstrapping is handled correctly.
- **Discounting:** γ^τ, with γ set **per game-hour** and converted to ticks (γ_tick = γ_hr^(1/6000)). This
  applies in GAE and in PBRS.

## 2. Interface

```python
class RSEnv(gymnasium.Env):
    def reset(self, seed: int | None = None, options: dict | None = None) -> tuple[np.ndarray, dict]
    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]   # obs, reward, terminated, truncated, info
    def action_masks(self) -> np.ndarray        # bool[N_ACTIONS], for sb3-contrib MaskablePPO
    def option_catalog(self) -> list[OptionSpec] # docs/option-catalog.md, same order as the action ids
```

- **`reset` options:** `reward_weights=(w_s, w_b)`. For the preference-conditioned agent (E4) the weights are
  also appended to the observation.
- **`step` reward:** the scalar w_s·r_skill + w_b·r_wealth. The unweighted pair is in `info["reward_vec"]`.
- **Masked action:** passing one to `step` is an error, never a silent no-op.

## 3. Observation

A flat `float32` vector built from the named parts below, by one shared `ObsEncoder`. Features are scaled to
roughly [0, 1].

| Part | Size | Encoding |
|---|---|---|
| Time | 2 | elapsed / horizon; remaining / horizon |
| Skills | 2 × 20 | level / 99 and fractional progress to the next level, for the 19 trainable skills plus Slayer (§5). The v1 skills read 1 in sim v0. |
| Total level | 1 | total level (all 24 skills) / 2376 |
| Hitpoints, prayer | 2 | current / max |
| Run energy, weight | 2 | energy / 100; weight in kg / 100, clipped to [0, 1] (option catalog §8) |
| Wealth | 2 | log1p(coins) / log1p(10M); log1p(net worth) / log1p(10M) |
| Inventory | V + 1 | log1p(count) / log1p(28) per vocabulary item; free slots / 28 |
| Bank | V | log1p(count) / log1p(10k) per vocabulary item |
| Equipment | E | tier index / max tier per slot: weapon (melee / ranged / staff), ammunition, head, body, legs, shield; tools (axe, pickaxe, fishing gear) |
| Region | R | one-hot over the catalog's regions |
| Combat candidates | C × 5 | for each candidate slot: XP/hr, gp/hr, expected damage taken per hour vs food held, travel minutes, Slayer / level eligibility (option catalog §4) |
| Loot mode | 4 | one-hot: all / valuable / vocabulary / none (option catalog §4.D) |
| Task | 11 | one-hot: the last activity's task (none, woodcutting, mining, the three fishing methods, thieving, processing, the three combat classes), which decides what `bank_deposit` keeps (option catalog §5) |
| Access | A | 0/1 per access rule (`data/access_areas.csv`, A = 55 today; `access.unlocked_rules`): unlocked by quests, items held, levels or coins (option catalog §4.C) |
| Quests | Q × 3 + 1 | stage one-hot (not started / underway / complete) per curated quest; quest points / 32 |
| Mask | N | the action mask |
| Preference | 2 | (w_s, w_b), for the E4 agent only |

Inventory and bank are separate because banking is now the agent's decision. *V* is the item vocabulary in the
option catalog.

**As built** (`rlscape/envs/encoding.py`, 2026-10-30): E = 11 roles (weapons for melee, ranged and magic,
ammunition, head, body, legs, shield, axe, pickaxe, fishing gear), R = 12 (the catalog's 11 regions and
"elsewhere"), C = 18 slots (6 per combat class). The encoder's docstring lists how each part is scaled. With the
catalog as built (1,000 actions, *V* = 156) the vector has 1,609 features.

**Left out on purpose:** GE prices. They're frozen, so a price snapshot would be a constant.

## 4. Reward

- **Skill:** r_skill = Δ Σ over all 24 skills of (level + fractional progress to the next level).
- **Wealth:** r_wealth = Δ net worth / 100,000 gp.
  - Net worth = coins + Σ (inventory + bank + equipment) × `data/prices_v2.csv` value.
  - Dropped items leave net worth, so dropping is a real cost the agent weighs against walking to a bank.
- **Shaping (E5 only):** F = γ^τ Φ(s′) − Φ(s), with Φ(terminal) = 0. Off by default.
- **Reported metrics** (not rewards), undiscounted, at each 2-hour checkpoint:
  - total level
  - **total XP:** Σ over all 24 skills of XP, each skill counted only up to level 99's 13,034,431 (Caleb,
    2026-10-30). The skill reward stays level-based; total XP shows progress toward levels that are worth
    climbing to, which the level-based reward values less per XP.
  - net worth

## 5. In-scope skills (v1.1)

**Trainable (19):**
- from sim v0 (14): Attack, Strength, Defence, Hitpoints, Ranged, Magic, Prayer, Woodcutting, Mining, Smithing,
  Fishing, Cooking, Firemaking, Thieving
- added in sim v1, before E2 (5): Fletching, Crafting, Agility, Herblore, Runecrafting (Caleb, 2026-10-28).
  Herblore needs Druidic Ritual and Runecrafting needs Rune Mysteries, both in the quest set. Agility levels also
  open the Agility shortcuts in the access table.

**Requirement checks only:** Slayer. There are no tasks, so it stays at 1 and Slayer-locked monsters stay out.

**Out of scope:** Farming, Construction, Summoning, Hunter. Each is a whole system (growth timers, the player-owned
house, familiars, traps). They stay at 1 and still count toward total level. The report lists this as a limitation.

Magic trains through combat spells and alchemy.

## 6. `info` fields (every step)

| Key | Meaning |
|---|---|
| `duration` | ticks the option took (τ) |
| `reward_vec` | `[r_skill, r_wealth]`, unweighted |
| `option` | id and name; for combat, also the chosen target and style |
| `termination` | `completed`, `inventory_full`, `inputs_exhausted`, `out_of_food`, `out_of_ammo`, `resources_exhausted`, `died`, `failed_precondition` (server only), `horizon` |
| `game_ticks` | ticks since reset |
| `total_level`, `total_xp`, `net_worth`, `coins` | after the option (`total_xp` as §4 defines it) |
| `xp_gained` | per-skill XP gained during the option |
| `items_delta` | per-item change, split into inventory, bank and dropped |
| `checkpoints` | (only when crossed) `{hour: {"total_level", "total_xp", "net_worth"}}` |

The decision logger records `obs`, `mask`, `action`, action probabilities, value estimate, and all of `info`
for every step.

## 7. Backend obligations

- **`SimEnv`:**
  - seeded `numpy.random.Generator`; same seed and same actions give the same trajectory
  - option effects come from the server's formulas (skilling, combat, drop tables, run energy) plus
    calibrated overheads (travel paths, banking, GE and shop trips)
  - **event-level sampling** (Caleb, 2026-10-28). Outcomes are sampled per event, not per tick and not as
    averages:
    - resources gathered over N ticks: one binomial draw
    - each kill's duration and damage taken
    - each drop roll
    - eating and death checked kill by kill
  - resource depletion and respawn come from the server's data. Competition from other players isn't modelled,
    because ambient bots are off on the server too.
  - **staged:** sim v0 has every family except quests and the five v1 skills. Sim v1 adds the 21 quests and those
    skills before E2.
  - target ≥ 20k decisions per second across `SubprocVecEnv` workers
- **`ServerEnv`:**
  - `reset` reinstalls the frozen GE database. This is required, not optional: GE offers outlive the
    character that placed them, and in testing one test's offer filled the next test's.
  - then start the server with `rl.conf` and spawn through the bridge
  - one RL character per world for validation (E6)
  - **ambient bots off** for calibration and E6 alike (Caleb, 2026-10-28). The gap then measures the model, not
    crowding.
  - not seedable (world randomness); reported as such
  - options run through human-path actions only, never `debug_*`
  - its inputs (clicks, item options, item-on-item, dialogue choices) go as client packets (the bridge's
    `packet` option), so the server handles them in its packet phase, before the world's pulses, exactly as a
    client's. Handled directly, a bridge command runs after the pulses, and an item option's effect lands a
    tick late (Caleb, 2026-10-30)
  - turns run on (`set_run`) at the start of each walk, as the simulator assumes. The server turns it off when
    energy drops under 1%.
- **Parity test:** the same scripted option sequence runs on both backends. The per-option XP, item, coin and
  duration distributions are compared; that's the sim-to-real gap (E6).
- **Calibration and the gate before E2** (Caleb, 2026-10-28):
  - **The gate:** each calibrated option's mean XP/hr, gp/hr and duration must be within **±20%** of the server's.
    Misses get one round of patching; anything still outside is listed as a known gap in the report.
  - **Bands:** calibration characters come in 11 bands: fresh, 11, 21, 31, 41, 51, 61, 71, 81, 91, 99.
  - **Skills:** the trainable skills (§5) are set to the band level, the rest stay at 1. Fresh means all 1s with
    10 Hitpoints.
  - **Gear:** non-fresh characters spawn with the starter kit and 100 gp × total level, and buy their own gear on
    the GE. They buy the best their levels and quests allow, in this priority: the tool for the option being
    calibrated, then the weapon, then armour by defence per gp.
  - **Quests,** cumulative by band:
    - fresh: none
    - 11–21: Cook's Assistant, Sheep Shearer, Rune Mysteries, Romeo & Juliet
    - 31–41: adds the rest of the 32-quest-point route
    - 51 and up: all 21, including Dragon Slayer
  - **Setup only:** stats and quests are set by calibration-only bridge commands (`debug_set_levels`,
    `debug_complete_quest`), never exposed to the agent. Each unlock that a debug-completed quest grants (rune
    platebody, Crandor, the Duke's shield) is live-tested before it's relied on.
  - **Runs:** each option is calibrated at the bands where it's unlocked, about 10 runs each. Parallel calibration
    characters never share a spot.

## 8. Combat-rate model

The combat candidate features (§3) and the simulator's combat outcomes come from one module, ported from the
server's combat code: accuracy and max-hit formulas, attack speeds, NPC stats from `npc_configs.json`, drops
from `drop_tables.json`, and spawns from `npc_spawns.json`.

| Quantity | How it's computed |
|---|---|
| Kills/hr | from hit chance and max hit against the NPC's defence and HP, plus a fixed 6-tick overhead per kill for finding and reaching the next target. **Respawn waits aren't modelled yet.** |
| XP/hr | combat XP and Hitpoints XP for the chosen style, plus the spell's base XP on every magic cast |
| gp/hr | expected value (`prices_v2`) of the drops the loot mode keeps × kills/hr. **Not yet subtracted:** consumables used (food, arrows, runes) and entry fees (Brimhaven, Waterbirth). |
| Risk | expected damage per kill, and the monster's max hit, against HP above the retreat point and the food held (the retreat-aware filter) |
| Inventory and travel | kills continue until the looted drops fill the free slots, then a bank trip; the walk to the monster is taken out of the duration (*D* = 15 game-minutes = 1,500 ticks) |
| Ammunition | fighting stops when the arrows or runes run out. Arrows that land and are picked back up stretch the arrows held; melee and crystal bows are unlimited. |

These are *theoretical* rates (expected values). The real server measures the actual ones during calibration
(E6).

## 9. Decisions

### Decided (Caleb, 2026-10-27)
1. **No banking inside activities.** Activities stop when the inventory is full. Banking, dropping, selling
   and alching are separate choices, because sometimes dropping beats walking to a bank.
2. **Fixed activity duration:** *D* = 15 game-minutes by default; 5 and 45 for the E5 ablation.
3. **Magic and High Level Alchemy are in:** Magic training and alchemy options, because sometimes alching
   beats banking or selling.
4. **Ranged and Magic combat are in**, and the agent should be able to fight **any enemy in the game**,
   choosing on theoretical gp/hr and XP/hr. The proposed mechanism is the candidate slots in option catalog
   §4.

5. **Selling:** per item, selling all of that item in the inventory. To keep some, the agent banks it or doesn't
   withdraw it.

6. **Combat (option catalog §4):**
   - 3 best by XP/hr + 3 best by gp/hr per class
   - a **retreat-aware** danger filter (no burst from half HP; one kill affordable on the HP and food at hand), plus a
     gear check for special damage such as dragonfire
   - a context-driven enemy pool: items that unlock areas, quest progress, levels
   - looting decided by the agent (proposed design: a loot mode it sets)

7. **Quests:** every quest should eventually be completable. This stage's set is 21 quests: the 32-quest-point
   route, Waterfall Quest, nine more quests, and Dragon Slayer. One action per quest (option catalog §10). Dragon
   Slayer unlocks rune platebodies and green d'hide bodies.
8. **The anti-dragon shield comes only from Duke Horacio** (once Dragon Slayer is underway). `rl.conf` sets
   `world.ge_blocked_items = "1540,1541"`, so the GE won't trade it.

### Decided (Caleb, 2026-10-28)
9. **The Wilderness is in the enemy pool.** PvP is off in `rl.conf` and training has no other players, so its monsters
   are judged by the same danger filter. The simulator models the harsher death there: all but 3 items are lost,
   with no gravestone.
10. **Death respawns the character and the episode continues** (§1): 3 items kept, a 2-minute gravestone outside the
    Wilderness, nothing recoverable inside it. The alternatives were ending the episode at death (too harsh, and
    not how 2009 worked) and ignoring gravestones.
11. **Looting is four loot modes the agent sets** (option catalog §4.D), approved as proposed.

Caleb signed off both documents on 2026-10-28 (v1.0).

### Decided (Caleb, 2026-10-28, simulation review): v1.1
12. **Event-level sampling** in the simulator (§7).
13. **Staging:** quests and the five new skills arrive in sim v1, before E2.
14. **Five more trainable skills:** Fletching, Crafting, Agility, Herblore, Runecrafting (§5), for 19 in all.
15. **Ambient bots off** on the server for calibration and E6 (§7).
16. **The sim-to-server gate** before E2 is ±20%, and the calibration characters are as described in §7.
17. **The scripted-guide baseline** (E1) is drafted by Claude from archived 2009 guides, cited in `docs/resources.md`,
    and reviewed by Caleb before E1 runs.

### Decided (Caleb, 2026-10-30, buying): v1.2
18. **Run energy and weight** (option catalog §8, Q3b): travel follows the server's run energy, which weight drains
    faster and Agility restores faster. Energy and weight are in the observation (§3), and on both backends every
    walk starts with run on (§7). The observation's encoding is Claude's choice.

### Decided (Caleb, 2026-10-30, baselines): v1.3
19. **The skill reward stays level-based, and total XP is reported** (§4): each skill's XP up to level 99's. Caleb's
    reason: some levels are breakpoints worth climbing to, and a level-only view undervalues the higher skills
    that reach them. E1's greedy XP/hr baseline maximises the same capped total.

### Decided (Caleb, 2026-10-30, the guide review): v1.4
20. **Deposits keep the task's kit** (option catalog §5): a deposit banks everything that isn't suitable to the task
    at hand, the last activity. So that a deposit's outcome is visible to the policy, the last task is part of the
    observation (§3).

### Decided (Caleb, 2026-10-30, the tick-manipulation test): v1.5
21. **`ServerEnv` inputs are client packets** (§7): the bridge enqueues the packet a click would send rather than
    handling the click itself, so input timing matches a real client's to the tick.
