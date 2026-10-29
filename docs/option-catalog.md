# Option Catalog (v1.1, Signed off)

**Status:** v1.1, 2026-10-28. It adds five more trainable skills for sim v1 (§3.5). Their options are still to be
specified and get Caleb's review before sim v1 is built. Read it together with `docs/env-contract.md`. It replaces v0
and `ROADMAP.md` Appendix A. All of its v1.0 questions are decided:
- selling quantity
- per-source buying
- the combat design (§4), including the loot modes (§4.D)
- death (§5's `reclaim_gravestone`)
- quests (§10)

The item vocabulary *V* (§9) is chosen by the agreed rule before training, and Caleb checks the list. Any later
change needs Caleb's approval and is logged in `docs/decision-log.md`.

## 1. How options work

- **Activity options** run until the first of: *D* game-minutes (15 by default), a full inventory, inputs
  running out, out of food or ammunition, death, or the horizon. They never bank (decided). When the
  inventory is full, gathering options are masked until the agent banks, drops, sells, alchs or processes.
- **Economy and inventory options** run once: travel if needed, then the transaction.
- **Travel** between regions is part of every option's duration.
- **Preconditions** make up the action mask: levels, tools, items in the inventory, coins, location
  requirements.
- **Verify** marks a location or access detail to confirm on the server during calibration.
- Bundled bot scripts (`content/global/bots`) can supply gathering and combat logic for the server executor,
  never their economy helpers.

The world is members-enabled (`rl.conf`), so members areas are allowed.

## Regions

| Id | Region | Bank used | Notes |
|---|---|---|---|
| `lumbridge` | Lumbridge castle and grounds | castle bank (top floor) | spawn point; range in the castle kitchen |
| `lumbridge_swamp` | Lumbridge Swamp | Draynor | copper / tin mine; *verify* |
| `lumbridge_farms` | cow and chicken fields east of the river | castle bank | `CowKiller`, `ChickenKiller` |
| `draynor` | Draynor Village | Draynor bank | willows, oaks, net fishing (`DraynorWillows`, `DraynorFisher`) |
| `varrock` | Varrock | west / east banks | anvil (`VarrockSmither`), south-east mine |
| `grand_exchange` | Grand Exchange | GE bank booths | all GE trades (bridge `ge_offer` / `ge_collect`) |
| `falador` | Falador and the Dwarven Mine | Falador east bank | coal (`CoalMiner`), furnace |
| `barbarian_village` | Barbarian Village | Edgeville | fly fishing; barbarians |
| `edgeville` | Edgeville and its dungeon | Edgeville bank | yews; hill giants around (3118, 9845) behind the brass-key door, *verify access* |
| `al_kharid` | Al Kharid | Al Kharid bank | warriors around (3284, 3172); toll gate: 10 gp from the inventory each way, free after Prince Ali Rescue (server), modelled in `rlscape/sim/movement.py`; without the coins, the walk goes round the fence (*verify route*) |
| `catherby` | Catherby (members) | Catherby bank | lobsters (`LobsterCatcher`); range |

Combat targets (§4) can be anywhere reachable. Their travel times come from the same region graph, extended to
each target's spawn area.

## 2. Gathering

Each produces into the inventory until it's full.

| Id | Preconditions | Produces | Region |
|---|---|---|---|
| `wc_logs` | Woodcutting 1, axe | logs | lumbridge |
| `wc_oak` | Woodcutting 15, axe | oak logs | draynor |
| `wc_willow` | Woodcutting 30, axe | willow logs | draynor |
| `wc_yew` | Woodcutting 60, axe | yew logs | edgeville |
| `mine_copper`, `mine_tin` | Mining 1, pickaxe | copper ore / tin ore | lumbridge_swamp (*verify*) |
| `mine_iron` | Mining 15, pickaxe | iron ore | varrock |
| `mine_coal` | Mining 30, pickaxe | coal | falador |
| `fish_shrimp` | Fishing 1, small net | raw shrimps / anchovies | draynor |
| `fish_fly` | Fishing 20, fly rod, feathers in the inventory | raw trout / salmon | barbarian_village |
| `fish_lobster` | Fishing 40, lobster pot | raw lobster | catherby |
| `pickpocket_men` | Thieving 1 | coins (stackable, so it never fills the inventory) | lumbridge |

## 3. Processing

These work from the inventory and run until the inputs run out. They happen at the nearest suitable station.

| Id | Preconditions | Inventory inputs | Output |
|---|---|---|---|
| `smelt_bronze` / `smelt_iron` / `smelt_steel` | Smithing 1 / 15 / 30 | copper + tin / iron ore / iron ore + 2 coal | bars (iron 50% success) |
| `smith_bronze` / `smith_iron` / `smith_steel` | Smithing level for the best item the bars allow, hammer | bars | the best smithable item for the bars held: platebody, platelegs, etc. |
| `cook_fish` | Cooking level for the food | raw food | cooked food (with burn chance), on a fire lit where the character stands when it holds a tinderbox and a log it can light, otherwise at the nearest range; bread dough, cake and barley always need a range |
| `burn_logs` | tinderbox, Firemaking level | logs | — |
| `bury_bones` | — | bones / big bones | — |

## 3.5 Skills added for sim v1 (Caleb, 2026-10-28)

Fletching, Crafting, Agility, Herblore and Runecrafting become trainable in sim v1, before E2 (env contract §5). Their
options are **to be specified** (catalog v1.2, for Caleb's review), following the same rules as §2–§3: preconditions,
inputs, a fixed duration *D*, server formulas, and calibration. The likely shape:

| Skill | Likely options | Notes |
|---|---|---|
| Fletching | cut logs into bows and arrow shafts, string bows, make arrows | processing, like Smithing; a classic 2009 money-maker |
| Crafting | tan hides into leather, make leather armour, spin flax, cut gems | processing; uses cowhides from combat |
| Agility | course laps (Gnome Stronghold, Draynor, …) | a gathering-like activity with no product; levels open the access table's shortcuts |
| Herblore | clean herbs, make potions | needs Druidic Ritual; herbs come from drops (vocabulary) |
| Runecrafting | craft runes at an altar from essence | needs Rune Mysteries; essence from mining |

These add roughly 15–25 actions and some vocabulary items; §9 is updated when they're specified.

## 4. Combat: candidate slots

All four parts were decided by Caleb on 2026-10-27. Where Caleb's decision needs a design, the design below is
the agent's proposal.

### A. Slots (decided)

For each of the three combat classes (melee, ranged, magic), the **3 best monsters by XP/hr** and the **3 best
by gp/hr** fill six slots. They are recomputed every decision with the combat-rate model (env contract §8) for
the current stats, gear, food and ammunition.
- If the same monster would fill both lists, the next best takes its place.
- Melee slots also choose a training style (Attack / Strength / Defence). That gives 30 combat actions: melee 6
  × 3, ranged 6, magic 6.
- Ranged needs a bow and arrows. Magic autocasts the best combat spell the runes held allow.
- **Ids (sim v0, `rlscape/sim/slots.py`):** `fight_<class>_<xp|gp><n>[_<style>]`, e.g.
  `fight_melee_xp1_accurate` or `fight_magic_gp3`. A melee style is masked when it fails the filter below on its own
  (agent choice, 2026-10-29; reversible). Ranged and magic slots stay masked until those fights are built.

### B. Retreat-aware danger filter with a special-damage gear check (decided)

Combat options eat below 50% HP and retreat once the food is gone (the `out_of_food` ending), so slow damage can't
kill the character. Caleb chose a **retreat-aware filter** (2026-10-27) over the first version, which required
surviving the full *D* minutes. On real data, that version let a fresh character fight only 7 kinds of monster: even
cows deal about 75 damage over 15 minutes at level 1.

A monster can only enter a slot if all three hold (`Rates.passes_retreat_filter`, `has_special_damage_protection`):
1. **No burst from the retreat point.** Two of the monster's max hits (the attacks it can still land while the
   character disengages; calibrate) must be less than half the character's max HP.
2. **One kill is affordable.** The damage taken during one kill, plus 2 standard deviations, fits in the HP above the
   retreat point plus the healing in the food carried.
3. **The character has the protection the monster's special damage requires** (Caleb's addition).

Example: a fresh character (10 HP, 8 HP of starter food) passes cows. Its budget is 5 + 8 = 13 HP, against about
7 ± 2.3 HP taken per cow kill.

The special-damage table is built from the server's combat code and NPC configs (`protect_style`, `poisonous`,
dragon NPC handlers):

| Special damage | Protection required to qualify |
|---|---|
| Dragonfire (all dragons) | anti-dragon shield equipped. It comes only from Duke Horacio, once Dragon Slayer is underway (§10). An antifire potion is a v1 option. |
| Monsters that block a combat style (`protect_style`) | ruled out for the blocked class only |
| Poison | no gear check; poison damage is to be added to the expected-damage estimate (**not implemented yet**) |
| Slayer-gear monsters (wall beasts, banshees and so on) | already Slayer-locked; also need their item |

The dragonfire list comes from the server's NPC classes: `ChromaticDragonNPC`, `MetalDragonNPC`,
`KingBlackDragonNPC` and `ElvargNPC`. Protection follows `ContentAPI.hasDragonfireShieldProtection`: the anti-dragon
shield or a dragonfire shield, and for wyverns the elemental or mind shield instead.

### C. Context-driven enemy pool (decided)

The pool (`rlscape/combat/candidates.py`, `enemy_pool`) is built from server data, then re-filtered every decision
against what the character can actually access. Caleb's rule: monsters an agent could reach because of what it
holds or what it's doing must be available.

**Cleaning, implemented.** 1,058 entries remain (403 distinct monsters):
- the NPC's **cache definition offers "Attack"** (`data/npc_definitions.csv`, exported through the bridge). This
  removes pickpocket, random-event and other non-combat NPCs that have stats in `npc_configs.json`.
- its config stats are **believable against its cache combat level** (the stats imply at least half that level,
  minus 2). 911 spawned NPC types carry placeholder stats (1/1/1, 10 HP); the server fights with them, and without
  this rule the agent could farm, say, level-90 zombies with level-10 stats. The rule flags 124 of 1,184 attackable
  spawned NPCs.
- **unkillable training dummies are excluded:** the server fully restores ids 4474 and 7891.
- **each monster keeps one site per map region** (a spawn and its nearest bank, from `data/banks.csv`). Each decision
  picks the site with the best rate from the character's location, counting the walk there and the bank trips.

**The access table, implemented** (`rlscape/combat/access.py`, `data/access_areas.csv`, 55 rules). Each decision, a
monster site only counts if every rule covering it is unlocked by the character's progress: quests complete or
underway, items held (inventory, bank or equipped), levels and coins. There are three kinds of rule:
- **Gated areas** (a rectangle). Examples:
  - Morytania: the server's own borders, the strip east of the River Salve those borders miss, and the dungeons
    underneath
  - quest-gated places: Mos Le'Harmless, Sophanem, West Ardougne, the Fremennik Isles, Ape Atoll, Shilo Village and
    the Kharazi Jungle, Crandor and Melzar's Maze, Trollheim
  - item-gated places: the Kalphite Lair and the Lumbridge Swamp Caves (a rope); Taverley's blue dragons (the dusty key,
    or 70 Agility)
  - entry fees: Brimhaven Dungeon (875 coins and an axe); Waterbirth (1,000 coins, or free after the Fremennik Trials)
  - Entrana (no weapons or armour allowed) and the Stronghold of Player Safety
- **Quest-only NPCs** (a list of names), fought only while their quest is underway: for example the Fight Arena
  bosses, Lucien, and Berry and Twig. Elvarg is fought inside the Dragon Slayer option, so she's never in the pool.
- **Minigames** such as the Barrows tunnels are `never`.

**Slayer levels** come from the server's `Tasks.java` (93 tasks, 1,127 NPC ids). Slayer has no training options, so it
stays at 1, and every Slayer-locked monster stays out.

The requirement grammar is `quest:` / `started:` / `underway:` / `item:` / `level:` / `coins:` / `never`, combined with
`&` and ` or ` (see the module docstring).

**Where the rules come from.** Each row names the server check that enforces it, or says the server doesn't. 2009Scape
leaves many 2009 gates unenforced: no check was found for Ape Atoll, the Lighthouse, the Kalphite rope or Entrana. The
table applies the 2009 rule anyway. The candidate list is built in Python for both backends, so the server is never
asked to fight a locked monster.

**Slayer levels are now enforced in the fork too** (Caleb, 2026-10-28). Upstream, `NPC.isAttackable` and
`IdleAbstractNPC.isAttackable` printed "You need a higher slayer level to know how to wound this monster" but had no
`return false`, so the attack went ahead. The fork adds the `return false`. The live test
`test_slayer_level_blocks_attacks` shows a fresh character can no longer fight cave crawlers (Slayer 10). The change
applies to every player, including the ambient bots.

**How the rows were chosen.** Not from memory of the whole map. A sweep ran the selection with every area open, over:
- levels 1–99 with matching gear
- 18 hub towns
- two loot modes
- all three combat classes

It collected every monster that reached a top-10 slot: 573 monster sites in 202 map regions. Each site that surfaced was
checked against the server. Then the table was built, and the sweep re-run with the real 3 + 3 slots until only
open-world monsters surfaced. Rows marked "2009 knowledge" or "to verify" get checked during calibration.

**Result:** for a fresh character at Lumbridge (melee), the gp/hr slots were Cockroach drones (46,000 gp/hr), undead
chickens and undead cows. They're now cow calves, bats and cows (5,900–7,600 gp/hr). The XP slots are unchanged (Rat,
Man, Ram).

**The Wilderness is open** (Caleb, 2026-10-28). PvP is off in `rl.conf`, and the danger filter judges its monsters like
any other. Dying there loses everything but 3 items, because there's no gravestone; the simulator has to model that.

**Known gaps (for calibration):**
- Areas not in the table count as open. Likely misses: the Ardougne zoo enclosures, parts of the Yanille Agility
  Dungeon, the Mountain Camp.
- The entry fees gate access but aren't charged in the rates yet.
- Separate maps at y ≈ 4,000–6,400 (Zanaris, the God Wars Dungeon, the Chaos Tunnels) are treated by the travel model as
  far-away surface tiles, so they never reach a slot. That's conservative, but by accident; they need their own rows
  and travel links.
- Colonel Radick (stats 1/1/1, 71 HP) passes the believability rule and is offered at every level. The rule misses this
  placeholder.
- Light sources (the server has no dark zones) and Slayer gear (earmuffs, face masks) aren't modelled. Slayer gear
  doesn't matter while Slayer stays at 1.

Quests are agent options (§10). While one is underway, its monsters and the areas it opens are available.

### Inventory and travel in the rates (implemented)

A candidate's XP/hr and gp/hr cover the option's whole duration, not just the fighting:
- **Fighting time:** kills continue until the looted drops fill the free inventory slots. Stackables (coins, runes,
  arrows, banknotes, summoning charms) cost no new slot.
- **Bank trips:** each full inventory costs the round trip to the site's nearest bank, plus 8 ticks of banking.
- **Getting there:** the walk from the character's location is taken out of the option's duration.

Travel is straight-line tile distance × 1.3 at 1.5 tiles per tick, plus 12 ticks per change of plane or
underground. Dungeons sit 6,400 tiles north of the surface they lie under. All of these constants are to be
calibrated on the server.

### D. Looting decided by the agent (decided)

Caleb's rule is that the agent makes looting decisions. **The design, approved by Caleb on 2026-10-28: a loot mode the agent sets.** It
persists across fights and is shown in the observation:

| Action | What gets picked up from kills |
|---|---|
| `loot_all` | everything |
| `loot_valuable` | coins, runes, arrows, vocabulary items, and anything ≥ 100 gp |
| `loot_vocabulary` | coins, runes, arrows, and vocabulary items only |
| `loot_none` | nothing |

The agent chooses its looting behaviour with 4 actions, and changes it whenever it wants: for example, loot
everything when the bank is close, only valuables far from one. The alternatives were:
- loot variants of every combat action (30 → 120 combat actions)
- a separate decision after every kill (thousands of decisions per episode)

The mode starts as `loot_valuable` at spawn. Setting a mode takes 1 tick, and the current mode is masked, so the action
is never a no-op (agent choice, 2026-10-29).

## 5. Inventory management

| Id | Effect |
|---|---|
| `bank_deposit` | walk to the nearest bank; deposit everything except tools, worn equipment, food, ammunition and runes |
| `bank_withdraw_for_<activity>` | walk to the nearest bank; withdraw the inputs one processing activity needs, up to a full inventory. One per §3 activity, so 9 actions. |
| `drop_<item>` | drop every unit of one vocabulary item from the inventory (dropped items leave net worth) |
| `drop_misc` | drop every non-vocabulary item |
| `reclaim_gravestone` | after a death outside the Wilderness: walk back to the gravestone and take back everything in it. Masked unless a gravestone exists and the walk fits in its remaining time (it lasts 200 ticks; env contract §1). |

## 6. Magic: alchemy

| Id | Preconditions | Effect |
|---|---|---|
| `high_alch_<item>` | Magic 55, a nature rune and 5 fire runes per cast (or a fire staff) | cast on every unit of one item in the inventory |
| `low_alch_<item>` | Magic 21, a nature rune and 3 fire runes per cast | the same, at low-alchemy value |
| `high_alch_misc`, `low_alch_misc` | as above | cast on every non-vocabulary item |

A cast takes 5 ticks, so long alchemy runs are cut at *D*. Alchemy is also the main non-combat source of Magic
XP: 65 XP for high alchemy, 31 for low.

## 7. Selling

Per item, selling **all of that item in the inventory** (decided). To keep some of an item, the agent banks it or doesn't withdraw it.

| Id | Effect |
|---|---|
| `sell_ge_<item>`, `sell_ge_misc` | walk to the GE; sell; the frozen buyer pays the 2009 price for items that have one |
| `sell_store_<item>`, `sell_store_misc` | walk to the nearest general store; sell at low-alchemy value minus overstock |

## 8. Buying

Gear, tools and food come from the frozen-price GE seller and from shops (decided). There is a **separate action per
source** wherever a nearby authentic shop stocks the item (decided), so the agent learns the price-versus-travel
trade-off.

| Group | Items | Sources |
|---|---|---|
| Woodcutting / mining tools | axes and pickaxes, steel to rune | GE; Bob's (steel axe), Nurmof's (pickaxes) |
| Melee | scimitars steel to rune; armour sets iron to rune (the **rune set needs Dragon Slayer** for its platebody) | GE; Zeke's (steel and mithril scimitars) |
| Ranged | shortbows (normal / oak / willow / maple); arrows (bronze to adamant) in 100s; leather and studded body | GE; Varrock's archery shop (*verify*) |
| Magic | air / water / earth / fire / mind / chaos / nature runes in 100s; elemental staves | GE; Varrock's rune shop (*verify*) |
| Fishing | fly rod + 1,000 feathers; lobster pot | GE; Gerrant's |
| Supplies | food (best affordable, up to 100); hammer; tinderbox | GE; general store (hammer, tinderbox) |

### Shops used (from `server/Server/data/configs/shops.json`)

Shops sell at 100–130% of an item's base value. The price rises toward 130% as their stock runs down. "2009 GE"
is what the frozen seller charges.

| Shop (region) | Sells | Example: shop price vs 2009 GE |
|---|---|---|
| Bob's Brilliant Axes (lumbridge) | bronze pickaxe; bronze / iron / steel axes | steel axe 200–260 vs **100** |
| Nurmof's Pickaxe Shop (falador, Dwarven Mine) | bronze to rune pickaxes | steel **500**–650 vs 576; rune 32,000+ vs **19,100** |
| Zeke's Superior Scimitars (al_kharid) | bronze to mithril scimitars | steel 400+ vs **200**; mithril 1,040+ vs **522** |
| Gerrant's Fishy Business (Port Sarim, near draynor) | small net, fly rod, lobster pot, harpoon, feathers | fly rod **5** vs 77; lobster pot **20** vs 70; feathers 6 vs 6 |
| Lumbridge General Store (lumbridge) | hammer, tinderbox | hammer **1** vs 13 |

**Bold** marks the cheaper source. The pattern is consistent: shops win for cheap tools, the 2009 GE wins for
weapons, armour and high-tier pickaxes. So which source to use is a real trade-off between price and travel
time.

**Not used:**
- Shops that sell pieces of armour sets: Horvik's, Louie's, Peksa's and Cassie's. Assembling a set takes four
  stops, and Cassie's has no iron or steel kiteshields in stock.
- Three shops with stock of 150,000+, including dragon scimitars ("Delicious Goods", "Armour & Supplies",
  "The Fairy's Culinary Goods"). They look like 2009Scape additions, not 2009 content.

## 9. Item vocabulary and size

**Vocabulary *V*:** the items this catalog produces or consumes, plus the most valuable common drops from the
enemy pool. That's about 60 items:
- logs, ores, bars, smithed items
- raw and cooked fish
- bones, big bones, hides, feathers
- arrows and runes
- the top drops by expected gp/hr

Every other item is **misc**. It still counts in net worth, and is handled by the `*_misc` actions. *V* is fixed
before training, so the action space doesn't change during the study.

**Size (with *V* ≈ 60 and selling as "all in the inventory"):**

| Group | Actions |
|---|---|
| Gathering | 11 |
| Processing | 9 |
| Combat | 30 |
| Loot mode | 4 |
| Inventory | 1 + 9 + 61 + 1 (reclaim gravestone) = 72 |
| Alchemy | 122 |
| Selling | 122 |
| Buying | about 60 |
| Quests | 21 |
| **Total** | **about 452** |

Masking keeps it workable: at any moment only the items actually in the inventory unlock their
sell / alch / drop actions, typically around 30–80 valid actions. A 20-hour episode now runs to roughly 250–400
decisions, because activities stop at a full inventory.

## 10. Quests

### Decisions (Caleb, 2026-10-27)

- **Every quest should eventually be completable by the agents.** That's a long-term goal: the server implements
  70 quests worth 132 quest points.
- **This stage's quest set** is the curated 32-quest-point route **plus Waterfall Quest, the nine backups, and
  Dragon Slayer**. That's 21 quests.
- **Dragon Slayer unlocks rune platebodies and green d'hide bodies.** Caleb confirmed this and the server
  enforces it (`ItemQuestRequirementListener`). The exact list is every rune platebody, including trimmed and god
  versions, and the green d'hide body, including trimmed. Blue, red and black d'hide bodies aren't locked.
- **The anti-dragon shield is only obtainable from Duke Horacio,** who gives one once Dragon Slayer is underway,
  or again after it's complete if it was lost (`DukeHoracioDialogue`).
  - The fork's new setting `world.ge_blocked_items` stops the GE trading it at all: no buying from the frozen
    seller, no selling, no bot stock. `rl.conf` sets it to `1540,1541` (the shield and its banknote).
  - No authentic shop or drop table has it. The only shop that lists it ("Magic Emporium", 150,000 stock) has no
    NPC attached and is among the inauthentic shops the catalog excludes.
  - The shield has no equip requirement, so once the Duke hands it over it can be worn freely.

So the path to dragons is a chain of investments:

> 32 quest points → start Dragon Slayer → the Duke's shield → dragons in the enemy pool (green dragon bones
> 1,908 gp each) and, after Elvarg, rune platebodies.

That's the kind of delayed payoff H1 tests.

### The quest set (21 quests, all implemented in 2009Scape)

Requirements come from `core/game/requirement/Requirement.kt` (`QuestRequirements`). Quest points come from each
quest class's constructor. The "involves" column is a summary to *verify on the server* while each executor
script is written.

**The 32-quest-point route**

| Quest | QP | Where | Involves | Combat |
|---|---|---|---|---|
| Cook's Assistant | 1 | Lumbridge | egg, bucket of milk, pot of flour; 300 Cooking XP | none |
| Romeo & Juliet | 5 | Varrock | messages, cadava berries, the apothecary | none |
| Goblin Diplomacy | 5 | Goblin Village | three goblin mails, dyed | goblins, for mail |
| Ernest the Chicken | 4 | Draynor Manor | lever puzzle, oil can, pressure gauge, rubber tube | none |
| Prince Ali Rescue | 3 | Al Kharid, Draynor | disguise, key imprint, rope, beer | none |
| Druidic Ritual | 4 | Taverley | four raw meats dipped in the Taverley Dungeon cauldron | animated armour nearby (*risk*) |
| Sheep Herder | 4 | East Ardougne | protective clothing (100 gp), herd sheep | none |
| Murder Mystery | 3 | Sinclair Mansion | clues and fingerprints | none |
| Pirate's Treasure | 2 | Port Sarim, Karamja, Falador | rum smuggling, dig in Falador Park | gardener (level 4) |
| Doric's Quest | 1 | north of Falador | clay, copper and iron ore; 1,300 Mining XP | none |

**For XP**

| Quest | QP | Reward |
|---|---|---|
| Waterfall Quest | 1 | 13,750 Attack + 13,750 Strength XP; no combat |

**Former backups, now in the set**

| Quest | QP | Requirement or note |
|---|---|---|
| Witch's Potion | 1 | kill a rat; 325 Magic XP |
| Imp Catcher | 1 | four beads from imps |
| The Restless Ghost | 1 | skeleton (level 13) |
| Rune Mysteries | 1 | errand |
| Sheep Shearer | 1 | spin wool |
| Monk's Friend | 1 | errand |
| Black Knights' Fortress | 3 | needs 12 QP |
| Vampire Slayer | 3 | Count Draynor (level 34) |
| Demon Slayer | 3 | Delrith (level 27) |

**Goal**

| Quest | QP | Requirement or note |
|---|---|---|
| Dragon Slayer | 2 | needs 32 QP; three map pieces, a ship to Crandor, Elvarg (level 83); the Duke's shield is needed for Elvarg |

**Total available:** 32 + 1 + 15 + 2 = **50 quest points**. The 32 needed for Dragon Slayer can come from any mix
of them, so the agent decides which quests are worth their time.

### How quests become options

- **One action per quest**, `quest_<name>`, which runs the quest from its current stage to completion.
- It's masked until the quest's requirements are met: skills, quest points and prerequisite quests.
- Items the quest needs are bought or gathered inside the option, so its duration and coin cost include them.
- Quests whose last step is a fight (Vampire Slayer, Demon Slayer, Dragon Slayer, The Restless Ghost) only
  unlock once that fight passes the danger filter (§4.B) for the character's current stats, gear and food.
- While a quest is underway, its monsters join the enemy pool and the areas it opens join the access table (§4.C).
- The observation gets each quest's stage and the character's quest points (env contract §3).
- **Simulator:** each quest is a macro-option with a duration estimate, item and coin costs, and the server's
  rewards.
- **Real server:** each needs a scripted walkthrough in the executor. A quest that proves broken in 2009Scape is
  dropped from the set and logged.

**Size:** 21 quest actions, about 452 actions in total.
