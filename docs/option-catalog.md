# Option Catalog (v0.5, Proposed)

**Status:** v0.5, 2026-10-27. Read it together with `docs/env-contract.md`; it replaces v0 and `ROADMAP.md`
Appendix A. All of its questions are decided: selling quantity, per-source buying, the combat design (§4), and
quests (§10). It's "Proposed" only until Caleb signs off the whole document.

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
| `al_kharid` | Al Kharid | Al Kharid bank | warriors around (3284, 3172); toll gate, *verify cost* |
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
| `cook_fish` | Cooking level for the fish | raw fish | cooked fish (with burn chance) |
| `burn_logs` | tinderbox, Firemaking level | logs | — |
| `bury_bones` | — | bones / big bones | — |

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

**Not implemented yet: the access table below.** The first real-data run shows why it's next. A fresh character's top
gp/hr slots are monsters in gated areas:
- Cockroach drones (Stronghold of Player Safety)
- Undead chickens and cows, and Blamish snails (Morytania, behind Priest in Peril)
- Scabaras lancers (Contact!)

| Unlock | How it's checked | Examples |
|---|---|---|
| Items that open areas | item in the inventory or bank (keys) or equipped | brass key → Edgeville Dungeon hill giants; dusty key → Taverley Dungeon |
| Quest progress | quest stage from the server's quest state | quest monsters while that quest is underway; areas a finished quest opens |
| Skill levels | current levels | Slayer-locked monsters; agility shortcuts |

An **access table** (area → requirement) is built for the gated areas that matter: dungeons behind keys, and
quest-gated regions. Areas not in it count as open unless calibration finds them closed. Minigame and instanced
monsters stay out.

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

Caleb's rule is that the agent makes looting decisions. **Proposed design: a loot mode the agent sets.** It
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

The mode starts as `loot_valuable` at spawn.

## 5. Inventory management

| Id | Effect |
|---|---|
| `bank_deposit` | walk to the nearest bank; deposit everything except tools, worn equipment, food, ammunition and runes |
| `bank_withdraw_for_<activity>` | walk to the nearest bank; withdraw the inputs one processing activity needs, up to a full inventory. One per §3 activity, so 9 actions. |
| `drop_<item>` | drop every unit of one vocabulary item from the inventory (dropped items leave net worth) |
| `drop_misc` | drop every non-vocabulary item |

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
| Inventory | 1 + 9 + 61 = 71 |
| Alchemy | 122 |
| Selling | 122 |
| Buying | about 60 |
| Quests | 21 |
| **Total** | **about 451** |

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

**Size:** 21 quest actions, about 451 actions in total.
