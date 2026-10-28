# Environment Contract (v0.5, Proposed)

**Status:** v0.5, 2026-10-27. All questions are decided by Caleb (§9); awaiting sign-off.

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
| Skills | 2 × 15 | level / 99 and fractional progress to the next level, for the in-scope skills (§5) |
| Total level | 1 | total level (all 24 skills) / 2376 |
| Hitpoints, prayer | 2 | current / max |
| Wealth | 2 | log1p(coins) / log1p(10M); log1p(net worth) / log1p(10M) |
| Inventory | V + 1 | log1p(count) / log1p(28) per vocabulary item; free slots / 28 |
| Bank | V | log1p(count) / log1p(10k) per vocabulary item |
| Equipment | E | tier index / max tier per slot: weapon (melee / ranged / staff), ammunition, head, body, legs, shield; tools (axe, pickaxe, fishing gear) |
| Region | R | one-hot over the catalog's regions |
| Combat candidates | C × 5 | for each candidate slot: XP/hr, gp/hr, expected damage taken per hour vs food held, travel minutes, Slayer / level eligibility (option catalog §4) |
| Loot mode | 4 | one-hot: all / valuable / vocabulary / none (option catalog §4.D) |
| Access | A | 0/1 per gated area in the access table: unlocked by an item held, quest progress, or a level (option catalog §4.C) |
| Quests | Q × 3 + 1 | stage one-hot (not started / underway / complete) per curated quest; quest points / 32 |
| Mask | N | the action mask |
| Preference | 2 | (w_s, w_b), for the E4 agent only |

Inventory and bank are separate because banking is now the agent's decision. *V* is the item vocabulary in the
option catalog.

**Left out on purpose:** GE prices. They're frozen, so a price snapshot would be a constant.

## 4. Reward

- **Skill:** r_skill = Δ Σ over all 24 skills of (level + fractional progress to the next level).
- **Wealth:** r_wealth = Δ net worth / 100,000 gp.
  - Net worth = coins + Σ (inventory + bank + equipment) × `data/prices_v2.csv` value.
  - Dropped items leave net worth, so dropping is a real cost the agent weighs against walking to a bank.
- **Shaping (E5 only):** F = γ^τ Φ(s′) − Φ(s), with Φ(terminal) = 0. Off by default.
- **Reported metrics** (not rewards): total level and net worth at each 2-hour checkpoint, undiscounted.

## 5. In-scope skills (v0.2)

Attack, Strength, Defence, Hitpoints, Ranged, Magic, Prayer, Slayer (requirement checks only, no tasks),
Woodcutting, Mining, Smithing, Fishing, Cooking, Firemaking, Thieving.

Magic and Ranged are trainable (decided). Magic trains through combat spells and alchemy. The other skills
count toward total level but have no options.

## 6. `info` fields (every step)

| Key | Meaning |
|---|---|
| `duration` | ticks the option took (τ) |
| `reward_vec` | `[r_skill, r_wealth]`, unweighted |
| `option` | id and name; for combat, also the chosen target and style |
| `termination` | `completed`, `inventory_full`, `inputs_exhausted`, `out_of_food`, `out_of_ammo`, `resources_exhausted`, `died`, `failed_precondition` (server only), `horizon` |
| `game_ticks` | ticks since reset |
| `total_level`, `net_worth`, `coins` | after the option |
| `xp_gained` | per-skill XP gained during the option |
| `items_delta` | per-item change, split into inventory, bank and dropped |
| `checkpoints` | (only when crossed) `{hour: {"total_level", "net_worth"}}` |

The decision logger records `obs`, `mask`, `action`, action probabilities, value estimate, and all of `info`
for every step.

## 7. Backend obligations

- **`SimEnv`:**
  - seeded `numpy.random.Generator`; same seed and same actions give the same trajectory
  - option effects come from the server's formulas (skilling, combat, drop tables) plus calibrated
    overheads (travel, banking, GE and shop trips)
  - target ≥ 20k decisions per second across `SubprocVecEnv` workers
- **`ServerEnv`:**
  - `reset` reinstalls the frozen GE database. This is required, not optional: GE offers outlive the
    character that placed them, and in testing one test's offer filled the next test's.
  - then start the server with `rl.conf` and spawn through the bridge
  - one RL character per world for validation (E6)
  - not seedable (world randomness, ambient bots); reported as such
  - options run through human-path actions only, never `debug_*`
- **Parity test:** the same scripted option sequence runs on both backends. The per-option XP, item, coin and
  duration distributions are compared; that's the sim-to-real gap (E6).

## 8. Combat-rate model

The combat candidate features (§3) and the simulator's combat outcomes come from one module, ported from the
server's combat code: accuracy and max-hit formulas, attack speeds, NPC stats from `npc_configs.json`, drops
from `drop_tables.json`, and spawns from `npc_spawns.json`.

| Quantity | How it's computed |
|---|---|
| Kills/hr | from hit chance and max hit against the NPC's defence and HP, plus respawn and walking time |
| XP/hr | combat XP and Hitpoints XP for the chosen style |
| gp/hr | expected drop value (`prices_v2`) × kills/hr − consumables used (food, arrows, runes) at 2009 prices |
| Risk | expected damage per kill, and the monster's max hit, against HP above the retreat point and the food held (the retreat-aware filter) |
| Inventory and travel | kills continue until the looted drops fill the free slots, then a bank trip; the walk to the monster is taken out of the duration (*D* = 15 game-minutes = 1,500 ticks) |

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

All questions are decided. Both documents stay "Proposed" until Caleb signs them off.
