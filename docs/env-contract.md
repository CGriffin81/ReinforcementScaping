# Environment Contract (v1.24, Signed off)

**Status:** v1.24, 2026-11-08. Any change needs Caleb's approval and is logged in `docs/decision-log.md`.
- **v1.24** (2026-11-08, building sim v1's Crafting per OQ-2's Choices A (a) and I (a); to confirm) adds Crafting's
  inputs: 25 GE buys (§2) and the 18 of them not yet in *V* (*V* 297), each with its 5 actions and 2 features. 1,828
  actions, 2,801 features.
- **v1.23** (2026-11-08, building sim v1's Crafting per OQ-2; to confirm) adds Crafting's 4 skilling slots (§3): 4
  actions, their 20 candidate features and 4 mask entries, and a crafting task. 1,713 actions, 2,650 features.
- **v1.22** (2026-11-08, Caleb: OQ-40 (c), the pouches as the server gives them; to confirm) gives Enter the
  Abyss's small pouch at spawn, in the bank (§1). The miniquest's other rewards still aren't given.
- **v1.21** (2026-11-08, Caleb: OQ-2's Choice D and H) adds two miniquests to the start state, complete as flags
  only (§1): Alfred Grimhand's Barcrawl (the Barbarian Outpost course) and Enter the Abyss (the Mage of Zamorak's
  teleport), without Enter the Abyss's rewards.
- **v1.20** (2026-11-08, Caleb) opens the Watchtower, Trollheim and Ape Atoll teleports as the server does for
  quests it lacks: by the quests' own requirements (§1), so Ape Atoll's now (its two quests are complete), Trollheim's
  at Herblore 31 and Watchtower's at its five levels. Trollheim's climbs, which need climbing boots, stay out.
- **v1.19** (2026-11-08, Caleb) shows the home teleport's cooldown in the observation (§3, OQ-15): one feature,
  the time until it's ready over its 30 minutes. 2,625 features.
- **v1.18** (2026-11-07; to confirm) has magic safespot as ranged does (OQ-34, Caleb: range 10, no piles), and fights
  count the site's aggressive monsters of other kinds (OQ-35 (a), Caleb): away from a safespot, while aggression
  lasts, they engage between kills and are fought in the fight's plan, in place of target kills (§8). A usable
  safespot holds from 80% of the wandering, not half (OQ-36 (a), Caleb). No change to the observation or the
  actions.
- **v1.17** (2026-11-07, confirmed by Caleb the same day) fights ranged from safespots (OQ-27 (d), Caleb): a ranged target whose damage
  isn't trivial (the fight would need food, OQ-30 (b)) needs the site's safespot, from which it does none; arrows
  lie in piles picked up between kills, with one pickup time for every class (§8). Slayer levels lock no monster
  (OQ-32, Caleb; §5). Every tradeable crossbow and bolt on the 2009 GE joins *V* and the GE buys (Caleb; 11 and 53,
  mithril bolts already in): *V* 279, 1,709 actions, 2,624 features. A crossbow's equipment tier is the bows' its
  Ranged level allows.
- **v1.16** (2026-11-07; to confirm) adds Ava's attractor and accumulator to *V* and the GE buys (Caleb: the GE
  sells them at 2,500 and 10,000 gp), and a cape role to the equipment part for them (OQ-28): 1,330 actions,
  2,119 features.
- **v1.15** (2026-11-07; to confirm) refits the combat-rate model's per-kill overhead (§8: 3 ticks, from 10 and 8)
  and adds a measured pickup time for each drop the loot mode keeps (5 ticks melee, 18 ranged); the time to kill
  counts the last hit's overkill (Caleb).
- **v1.14** (2026-11-06; to confirm) puts poison and a dragon's breath in the combat-rate model's risk (§8), ported
  from the server, less the shares the antipoison and antifire carried cover, and combat potions' boosts in the
  fighter (Caleb added the potions); a potions part in §3, each potion's doses carried, with only the four-dose
  potions in *V* (OQ-25, Caleb); *V* 214 (§3's sizes).
- **v1.13** (2026-11-06, Caleb) sells the anti-dragon shield on the GE (§9, decision 8) and grows *V* to 192 by its
  rule with every quest complete, then 198 with the quest gear the buy list took on (OQ-24), then 203 with what the
  drop tables' sub-tables bring (§3's sizes).
- **v1.12** (2026-11-06, Caleb) takes quests out: every quest the server has is complete from the start, as flags
  only (§1), the observation loses its quest part (§3), and sim v1 brings only the four skills (§7). The gate keeps
  the fast tick with a speed check, and judges gp/hr by its parts (§7).
- **v1.11** (2026-11-05; to confirm) measures the combat-rate model's per-kill overhead and adds respawn waits at
  sites short of monsters (§8), from the combat calibration.
- **v1.10** (2026-11-01, Caleb) has every trip take the fastest way the character can use, teleports and boats
  included, paying for it; the home teleport waits 30 minutes, and a place with no way there is unreachable (§7).
- **v1.9** (2026-10-31, Caleb) has gathering options follow Caleb's rule for aggressive monsters (§7).
- **v1.8** (2026-10-31, Caleb) has fights flick prayers (§8).
- **v1.7** (2026-10-31, Caleb) brings Fletching forward into sim v0 (§5), with Fletching skilling slots, a
  fletching task (§3) and 20 fletching inputs in *V*.
- **v1.6** (2026-10-31, Caleb) replaces the fixed gathering actions with skilling slots and adds their rates to
  the observation (§3).
- **v1.5** (2026-10-30, Caleb) has `ServerEnv` send its inputs as client packets (§7), after the live
  tick-manipulation test found that the bridge's direct commands land a tick late against the world's pulses.
- **v1.4** (2026-10-30) adds the last task to the observation (§3), because Caleb's deposit rule makes what a
  deposit keeps depend on it.
- **v1.3** (2026-10-30, Caleb) adds total XP to the reported metrics (§4, §6).
- **v1.2** (the same day) adds run energy and weight to the observation (§3) and the run rule to the backends
  (§7), from Caleb's buying decision on gear and running (option catalog §8).
- **v1.1** (approved by Caleb on 2026-10-28) adds the simulation decisions: five more trainable skills (§5),
  event-level sampling, the ambient-bots setting, and the calibration gate and characters (§7).
- **v1.0** added the death rule (§1) to v0.6.

Both backends implement this contract exactly: `SimEnv` (the surrogate simulator) and `ServerEnv` (2009Scape
through the bridge). Any policy, baseline or logger written against it runs on either one.

## 1. Time and episodes

- **Game time:** 1 tick = 0.6 s. Durations are reported in ticks.
- **Episode:** `reset(seed)` produces a fresh level-3 character exactly as it leaves Tutorial Island, at
  Lumbridge (3233, 3230), with the starter kit, and 25 coins and the small pouch (v1.22, below) in the bank.
- **Quests:** every quest the server has (68, worth 126 quest points) is complete from the start (Caleb, 2026-11-06),
  as flags only: the quest points and the unlocks come with them, no quest XP or items. There are no quest options.
  The quests the server lacks stay incomplete, and so does the content behind them in the sim, except where the
  server checks one with `ContentAPI.hasRequirement`, which the quest's own requirement meets: the Watchtower,
  Trollheim and Ape Atoll teleports, which the sim gates the same way (v1.20, Caleb). Two miniquests are complete
  too, as flags only (v1.21, Caleb, 2026-11-08): Alfred Grimhand's Barcrawl, which opens the Barbarian Outpost
  course, and Enter the Abyss, which gives the Mage of Zamorak's teleport to the Abyss. Of its rewards, only the
  small pouch is given, in the bank (v1.22, Caleb, 2026-11-08: the pouches as the server gives them; the others
  drop from the Abyss's monsters); its 1,000 Runecrafting XP and notes aren't. The rest stay incomplete: Barbarian Training's stages, for one, which nothing
  in sim v1 needs.
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
| Home teleport | 1 | the ticks until the home teleport is ready again / its 30-minute cooldown; 0 when ready (v1.19, OQ-15) |
| Wealth | 2 | log1p(coins) / log1p(10M); log1p(net worth) / log1p(10M) |
| Inventory | V + 1 | log1p(count) / log1p(28) per vocabulary item; free slots / 28 |
| Bank | V | log1p(count) / log1p(10k) per vocabulary item |
| Potions | 11 × 2 | each potion's doses (antipoison, super antipoison, the eight combat potions, antifire; any dose, noted or not): log1p(doses) / log1p(112) in the inventory, / log1p(10k) in the bank. Only the four-dose potions are in *V* (OQ-25) |
| Equipment | E | tier index / max tier per slot: weapon (melee / ranged / staff), ammunition, head, body, legs, shield; tools (axe, pickaxe, fishing gear); cape (Ava's devices: attractor 1, accumulator 2) |
| Region | R | one-hot over the catalog's regions |
| Combat candidates | C × 5 | for each candidate slot: XP/hr, gp/hr, expected damage taken per hour vs food held, travel minutes, Slayer / level eligibility (option catalog §4) |
| Skilling candidates | 24 × 5 | per skilling slot (option catalog §2; Crafting's 4 since v1.23): the gathering skill's XP/hr, its processing counterpart's XP/hr, gp/hr, travel, open; scaled as the combat candidates |
| Loot mode | 4 | one-hot: all / valuable / vocabulary / none (option catalog §4.D) |
| Task | 13 | one-hot: the last activity's task (none, woodcutting, mining, the three fishing methods, thieving, fletching, crafting, processing, the three combat classes), which decides what `bank_deposit` keeps (option catalog §5) |
| Access | A | 0/1 per access rule (`data/access_areas.csv`, A = 55 today; `access.unlocked_rules`): unlocked by quests, items held, levels or coins (option catalog §4.C). Rules decided by quests alone are constant, since the quests are complete from the start |
| Mask | N | the action mask |
| Preference | 2 | (w_s, w_b), for the E4 agent only |

Inventory and bank are separate because banking is now the agent's decision. *V* is the item vocabulary in the
option catalog.

**As built** (`rlscape/envs/encoding.py`, 2026-10-30): E = 12 roles (weapons for melee, ranged and magic,
ammunition, head, body, legs, shield, axe, pickaxe, fishing gear), R = 12 (the catalog's 11 regions and
"elsewhere"), C = 18 slots (6 per combat class). The encoder's docstring lists how each part is scaled. With the
catalog as built (1,828 actions, *V* = 297) the vector has 2,801 features (v1.12 dropped the quest part's 64; v1.13
added 7 buys and 27 items; v1.14 11 buys, 11 items and the potions part's 22; v1.16 2 buys, 2 items and the cape role;
v1.17 64 buys and 63 items; v1.19 the home teleport's wait; v1.23 Crafting's slots and task; v1.24 25 buys and 18
items).

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
- from sim v0 (15): Attack, Strength, Defence, Hitpoints, Ranged, Magic, Prayer, Woodcutting, Mining, Smithing,
  Fishing, Cooking, Firemaking, Thieving, and Fletching (brought forward by Caleb, 2026-10-31)
- added in sim v1, before E2 (4): Crafting, Agility, Herblore, Runecrafting (Caleb, 2026-10-28).
  Herblore needs Druidic Ritual and Runecrafting needs Rune Mysteries, both complete from the start (§1). Agility
  levels also open the Agility shortcuts in the access table.

**Slayer:** there are no tasks, so it stays at 1, and Slayer levels lock no monster (Caleb, 2026-11-07, OQ-32; the
fork drops them too). Monsters that need Slayer gear the sim doesn't model stay out
(`candidates.SLAYER_GEAR_NPCS`).

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
  - **aggressive monsters at gathering sites** (Caleb, 2026-10-31; option catalog §4): attacks don't stop the
    gathering, only trivial monsters are fought, and the character runs out of a monster's aggressive range when
    its hitpoints fall under twice that monster's max hit. Both backends: `ServerEnv` turns auto-retaliate off
    for gathering (the bridge's `set_retaliate`).
  - **travel** (Caleb, 2026-11-01; option catalog §4): every trip takes the fastest way the character can use
    then, paying for it: walking on the server's collision map, the home teleport, teleport spells, jewellery,
    tablets, the seed pod, ships and charters. The home teleport can be cast once every 30 minutes (a fork change,
    counted in game ticks). A place nothing the character can use reaches is unreachable for it: its options are
    masked. Both backends: `ServerEnv` takes the same transports by the player's clicks (`rlscape/bridge/travel.py`).
  - **staged:** sim v0 has every family except the four v1 skills, which sim v1 adds before E2. Quests are out
    (v1.12).
  - **aggressive monsters near a combat site** (Caleb, 2026-11-06, OQ-19; 2026-11-07, OQ-35 (a)): measured on the
    server, they moved the rates beyond ±20%, so the site's aggressive monsters of other kinds engage between kills
    until aggression runs out, each fought in the fight's plan (§8).
  - speed: no fixed target (Caleb, 2026-11-08, OQ-7 (a), in place of ≥ 20k decisions a second): the combat-rate
    model is vectorised over the enemy pool, and E2's budget is sized to the measured speed (2026-11-08: 110 a
    second in one process, 817 across 16 workers)
- **`ServerEnv`:**
  - `reset` reinstalls the frozen GE database. This is required, not optional: GE offers outlive the
    character that placed them, and in testing one test's offer filled the next test's.
  - then start the server with `rl.conf` and spawn through the bridge
  - one RL character per world for validation (E6)
  - **ambient bots off** for calibration and E6 alike (Caleb, 2026-10-28). The gap then measures the model, not
    crowding.
  - not seedable (world randomness); reported as such
  - options run through human-path actions only, never `debug_*`
  - its inputs (clicks, item options, item-on-item, item-on-scenery, dialogue choices) go as client packets (the bridge's
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
    the GE. They buy the best their levels allow, in this priority: the tool for the option being calibrated, then
    the weapon, then armour by defence per gp.
  - **Quests:** at every band, every quest the server has is complete, as `spawn` makes it (§1).
  - **Setup only:** stats are set by a calibration-only bridge command (`debug_set_levels`), never exposed to the
    agent. Each quest unlock the sim relies on is live-tested before it's relied on (so far the rune platebody and
    Morytania's border).
  - **Tick speed** (Caleb, 2026-11-06, OQ-21): calibration runs the server at 50 ms ticks, 12× real time. The gate
    includes a speed check: a few cases from each calibrated family rerun at 600 ms, which must agree with the fast
    runs within their run-to-run noise.
  - **gp/hr where rare drops make up the loot** (Caleb, 2026-11-06, OQ-20): the mean of about 10 short runs can't
    settle it, so the gate takes its parts. The drop tables are checked item by item over about 200 kills per
    monster, and the looting overhead is gated through kills/hr, XP/hr and the time to a full inventory.
  - **Runs:** each option is calibrated at the bands where it's unlocked, about 10 runs each. Parallel calibration
    characters never share a spot.

## 8. Combat-rate model

The combat candidate features (§3) and the simulator's combat outcomes come from one module, ported from the
server's combat code: accuracy and max-hit formulas, attack speeds, NPC stats from `npc_configs.json`, drops
from `drop_tables.json`, and spawns from `npc_spawns.json`.

| Quantity | How it's computed |
|---|---|
| Kills/hr | from hit chance and max hit against the NPC's defence and HP (the expected swings until their damage reaches its HP, the last hit's overkill included, as the simulator's fights deal it), plus a measured overhead per kill for finding and reaching the next target (3 ticks, every class; magic's calibration bears it out), and a measured pickup time for each ground item the loot mode keeps, a drop or a pile of arrows (5 ticks, one time for every class; ranged's to refit on safespot runs). A site short of the monster holds kills to one every (respawn + fighting) / spawns ticks: spawns of it within 15 tiles (`npc_spawns.json`), its `respawn_delay` (`npc_configs.json`). In the simulator each of a site's monsters has its own respawn, and nothing attacks while the character waits. |
| XP/hr | combat XP and Hitpoints XP for the chosen style, plus the spell's base XP on every magic cast |
| gp/hr | expected value (`prices_v2`) of the drops the loot mode keeps × kills/hr. **Not yet subtracted:** consumables used (food, arrows, runes) and entry fees (Brimhaven, Waterbirth). |
| Risk | expected damage per kill, poison included (the server's Poison timer; prayer doesn't stop it) and a dragon's breath behind the shield (one swing in three, 0 to 5), less the shares the antipoison and antifire carried cover, and the monster's max hit, against HP above the retreat point and the food held (the retreat-aware filter). The fighter's levels are as its carried potions boost them at the fight's start |
| Inventory and travel | kills continue until the looted drops fill the free slots, then a bank trip; the walk to the monster is taken out of the duration (*D* = 15 game-minutes = 1,500 ticks) |
| Prayer | fights flick prayers (option catalog §4): a style the Prayer level can protect against deals nothing, defence prayers count otherwise, and the character's swings get its accuracy and damage prayers except those next to a monster swing. Prayer points never drain. |
| Ranged and magic safespots | a ranged or magic target needs a safespot unless its damage is trivial: the fight needs no food, its expected damage over the option less the hitpoints regenerated meanwhile fitting in those above the retreat point (OQ-30 (b)), and unless the gear guards against its special damage (a bow takes no shield). The safespots are the server's, by its own chase (the bridge's `ranged_safespots`, exported to `data/ranged_safespots.csv`): a tile the monster, chasing, gets stuck short of attacking from, with it in shot (range 7, long-ranged 9, magic 10: OQ-34), holding from at least 80% of its wandering (OQ-36 (a)), with no aggressive monster reaching it. From one the monster deals nothing, and the site's supply is the monsters it holds against. Casting leaves no piles. Arrows land where the monster stands: a pile per 100 ticks of shooting, picked up between kills with the drops, a pickup each, plus the walk from the safespot and back; when aggressive monsters guard them and aggression hasn't run out, the simulator's fight leaves them until the oldest would go (200 ticks). `rlscape.combat.safespots` |
| Monsters near a fight | away from a safespot, a site's aggressive monsters of other kinds (spawned within 10 tiles) whose level would pick the character engage it between kills (the overhead to the next monster, the pickups, a wait for a respawn: when nothing attacks it, as `AggressiveBehavior` needs outside multi-combat areas), each spawn at 0.045 a tick (measured at the animated spades' possessed pickaxe), until the region's tolerance runs out (1,000 ticks after arriving). Each engagement is a kill of that monster in the fight's plan, its time, damage, XP and drops, before the next target (single combat). The rankers count the expected fights per target kill; a site where one can't be hurt by the plan or fails the danger filter is no site while aggression lasts (OQ-35 (a)). `rlscape.combat.neighbours` |
| Ammunition | fighting stops when the arrows or runes run out. Arrows that land and are picked back up stretch the arrows held, and so do Ava's devices: worn, a device sends 80% of shots back to the quiver, and the accumulator also gathers the shots it misses that would land (`equipment.shot_outcomes`, from `RangeSwingHandler`). The server's metal chest pieces stop the catch (`data/ava_interference.csv`), and a ranger wearing a device leaves them off. Melee and crystal bows are unlimited. |

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
   Slayer unlocks rune platebodies and green d'hide bodies. *Superseded by 27 (v1.12): quests are out.*
8. **The anti-dragon shield comes only from Duke Horacio** (once Dragon Slayer is underway). `rl.conf` sets
   `world.ge_blocked_items = "1540,1541"`, so the GE won't trade it. *Superseded by 29 (v1.13): the GE sells it.*

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
13. **Staging:** quests and the five new skills arrive in sim v1, before E2. *Fletching came into sim v0 (v1.7);
    quests are out (v1.12).*
14. **Five more trainable skills:** Fletching, Crafting, Agility, Herblore, Runecrafting (§5), for 19 in all.
15. **Ambient bots off** on the server for calibration and E6 (§7).
16. **The sim-to-server gate** before E2 is ±20%, and the calibration characters are as described in §7.
17. **The scripted-guide baseline** (E1) is drafted by Claude from archived 2009 guides, cited in `docs/resources.md`,
    and reviewed by Caleb before E1 runs. Reviewed 2026-10-31: the 13-skill, lowest-first second draft
    (`docs/scripted-guide-draft.md`).

### Decided (Caleb, 2026-10-30, buying): v1.2
18. **Run energy and weight** (option catalog §8): travel follows the server's run energy, which weight drains
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

### Decided (Caleb, 2026-10-30 and 31, skilling slots): v1.6
22. **Skilling slots** (option catalog §2): Woodcutting, Fishing, Mining and Thieving each offer their 2 best paths by
    XP/hr and 2 by gp/hr as actions, replacing the fixed gathering actions; a path pairs a gathering method with its
    processing counterpart where sim v0 has it. Their rates are in the observation (§3).

### Decided (Caleb, 2026-10-31, fletching): v1.7
23. **Fletching is in sim v0** (§5; option catalog §2): woodcutting's logs can be cut where they're chopped, and
    Fletching has its own skilling slots over the server's recipes (bows, stringing where the strung bow is worth
    more than its parts, arrows, darts, bolts). Its bought inputs join *V* by *V*'s rule (option catalog §9).

### Decided (Caleb, 2026-10-31, prayers): v1.8
24. **Fights flick prayers automatically** (§8; option catalog §4): protection, accuracy and damage prayers, and
    defence prayers where the monster's style can't be protected against. Flicking costs nothing on 2009Scape
    (checked live), so it's no action of the agent's; training Prayer is what it decides.

### Decided (Caleb, 2026-10-31, aggressive monsters): v1.9
25. **Gathering options follow Caleb's rule for aggressive monsters** (§7; option catalog §4): no fights unless
    trivial, and running out of a monster's aggressive range when it's dangerous. The server's aggression tolerance
    counts game ticks (fork), so a sped-up server behaves the same.

### Decided (Caleb, 2026-11-01, travel and banking): v1.10
26. **Travel takes the fastest usable way, automatically** (§7; option catalog §4): walks, teleports (the home
    teleport, the standard spells, every teleport jewellery item at every charge, tablets, the Grand seed pod) and
    boats (the fixed ships and the charters), whichever is fastest for what the character can use, paid from what it
    carries. They aren't agent actions. Which teleport items join *V* follows OQ-10's answer (decision log,
    2026-11-01). The home teleport waits 30 minutes between casts (OQ-13), and a place with no way there is
    unreachable (OQ-12).

### Decided (Caleb, 2026-11-06, quests out): v1.12
27. **Quests are out of the experiment, and complete from the start** (§1): every quest the server has, as flags only,
    so no quest blocks content. The level-3 start with the starter kit stays (a start at level 30 with 10,000 gp was
    considered and dropped). The observation's quest part goes (§3). Supersedes 7, and 13 for quests.
28. **The gate keeps the fast tick, with a speed check, and judges gp/hr by its parts** (§7; OQ-21, OQ-20).

### Decided (Caleb, 2026-11-06, the shield and V): v1.13
29. **The anti-dragon shield is bought on the GE** at its 2009 price (OQ-22), and fights against dragonfire monsters
    put on a carried one (option catalog §4.B). Supersedes 8.
30. ***V* is redrafted by its rule with every quest complete** (OQ-23): 16 items added, none taken out (option
    catalog §9). The buy list takes the dragon dagger and longsword and the Fremennik helms (OQ-24), which join *V*,
    and so do the 5 items the rule proposes once the drop tables' sub-tables are modelled.

### Decided (Caleb, 2026-11-07, safespots and monsters near a fight): v1.17 and v1.18
31. **Ranged and magic fights safespot** (§8; OQ-27 (d), OQ-30 (b), OQ-34): a target whose damage isn't trivial is
    fought from the site's safespot, from which it deals nothing.
32. **Monsters of other kinds near a fight are fought** (§8; OQ-35 (a)): away from a safespot, while aggression lasts,
    a site's aggressive monsters of other kinds engage between kills, and each is killed before the next target.
