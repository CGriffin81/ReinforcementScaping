# Option Catalog (v1.2, Signed off)

**Status:** v1.2, 2026-10-30. It replaces §8's buying table with Caleb's buying decisions (2026-10-29 and 30): the
buy actions, the gear and food withdrawals (§5), and run energy and weight for travel. It also adds `smith_mithril`
(§3), so bought mithril bars can be smithed. v1.1 (2026-10-28) added five more trainable skills for sim v1 (§3.5);
Fletching has since been brought into sim v0 (2026-10-31, §2), and the other four's options are an open question
(`docs/open-questions-log.md`, OQ-2). Read it together with `docs/env-contract.md`. It replaces v0 and
`ROADMAP.md` Appendix A. The decisions behind it are in `docs/decision-log.md`.

The item vocabulary *V* (§9) is chosen by the agreed rule before training, and Caleb checks the list. Any later
change needs Caleb's approval and is logged in `docs/decision-log.md`.

## 1. How options work

- **Activity options** run until the first of: *D* game-minutes (15 by default), a full inventory, inputs
  running out, out of food or ammunition, death, or the horizon. They never bank (decided). When the
  inventory is full, gathering options are masked until the agent banks, drops, sells, alchs or processes.
- **Economy and inventory options** run once: travel if needed, then the transaction.
- **Travel** between regions is part of every option's duration. It depends on run energy, weight and Agility
  (§8).
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

## 2. Gathering: skilling slots

**Skilling slots** (Caleb, 2026-10-30/31; `rlscape/sim/skilling.py`). Like the combat slots (§4), each gathering
skill offers its best **paths** by XP/hr and by gp/hr at the current levels, gear and position, as actions, and
agents choose a path, not a fixed method. Five skills (Woodcutting, Fishing, Mining, Thieving, Fletching) × 2 slots
by XP/hr + 2 by gp/hr = 20 actions, `skill_<skill>_xp1/xp2/gp1/gp2`. They replace the 31 fixed gathering and thieving
actions.
A path in an XP slot doesn't also fill a gp slot (the next best takes its place, as in combat), and slots are
recomputed every decision. The observation carries each slot's rates (env contract §3).

A **path** is a gathering method plus what happens to its produce. Caleb: "pair gathering skills with their
processing counterpart". Each method is either kept (the method below alone, ending at a full inventory) or
processed where the sim has the counterpart: woodcutting's logs burned where they're cut (`wc_<tree>_burn`,
Firemaking; it keeps chopping while burning frees room) or cut with a knife (`wc_<tree>_fletch`, Fletching: arrow
shafts from normal logs, which stack, so it keeps chopping; otherwise the best bow (u) the level allows),
fishing's catch cooked (`fish_<method>_cook`, Cooking; it ends at a full inventory of cooked fish) and mining's
iron smelted (`mine_iron_smelt`, Smithing; it keeps mining while there's room). Thieving's paths are its targets
and stalls.

**Fletching** (Caleb, 2026-10-31: brought forward from sim v1; `rlscape/sim/fletching.py`) has its own paths, one per
recipe (`fletch_<recipe>`): at the nearest bank, take out the recipe's inputs, craft them, bank the products, and
again, until the inputs (banked or carried) or the time run out. The recipes are the server's: logs cut into arrow
shafts or unstrung bows (a log every 3 ticks), bows strung (every 2 ticks), headless arrows and arrows (15 every 3
ticks), darts (10 every 3 ticks, after The Tourist Trap) and bolts (10 every 3 ticks). A bow is strung only where
the strung bow is worth more than the unstrung bow and the bowstring (Caleb): maple, yew and magic longbows and yew
shortbows. On 2009Scape every one of these is a queued script that a walk or any other action clears (checked
live), so fletching can't be done on the move or between other actions.

That's 79 paths: woodcutting 12, fishing 6, mining 5, thieving 20, fletching 36.

**Rates** come from an analytic model of the same mechanics, over an option of D ticks, as the combat ranker values
fights: the time, XP and value (`data/prices_v2.csv`) of a unit at the site; for trees and rocks that deplete, a
load replayed under the gathering loop's rules; the processing's time, XP and value; one bank trip per load (the
slots a deposit leaves after the task's kit); and travel to the site, taken out of D. Bait is costed; thieving's
hitpoints aren't (a target the character can't sustain is masked). Tests check the model against the simulated
paths within 8%.

The paths' gathering methods (their ids are the path ids of the kept paths):

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
| `pickpocket_men` | Thieving 1 | 3 coins (stackable, so it never fills the inventory) | lumbridge |
| `pickpocket_farmers` | Thieving 10 | 9 coins and a potato seed | lumbridge_farms |
| `pickpocket_ham_women` / `pickpocket_ham_men` | Thieving 15 / 20 | one weighted pick: coins, herbs, gems, pickaxes, H.A.M. clothing, junk | H.A.M. hideout under Lumbridge (the trapdoor's lock, 1 in 3 per try, is a travel overhead to calibrate) |
| `pickpocket_warriors` | Thieving 25 | 18 coins | al_kharid |
| `pickpocket_master_farmers` | Thieving 38 | one weighted pick of 38 seeds (ranarr, snapdragon, …) | between Lumbridge and Varrock (server spawn 3241, 3345) |
| `pickpocket_guards` | Thieving 40 | 30 coins | varrock |
| `pickpocket_fremenniks` | Thieving 45 | 40 coins | Rellekka |
| `pickpocket_desert_bandits` | Thieving 53 | one weighted pick: 1–49 coins, an antipoison, a lockpick | the Bandit Camp, in the desert (a Shantay pass on the way, below) |
| `pickpocket_knights` | Thieving 55 | 50 coins | East Ardougne |
| `pickpocket_watchmen` | Thieving 65 | 60 coins and a bread | Yanille |
| `pickpocket_menaphite_thugs` | Thieving 65 | 60 coins | Pollnivneach, in the desert |
| `pickpocket_paladins` | Thieving 70 | 80 coins and 2 chaos runes | East Ardougne |
| `pickpocket_gnomes` | Thieving 75 | one weighted pick: 300 coins, earth runes, gold ore, fire orbs, swamp toads, king worms | Tree Gnome Village area (server spawn 2558, 3228) |
| `pickpocket_heroes` | Thieving 80 | one weighted pick: 200–299 coins, death and blood runes, fire orbs, diamonds, gold ore, wine | East Ardougne |
| `steal_bakers_stall` | Thieving 5 | a cake, bread or chocolate slice | the Ardougne market |
| `steal_silk_stall` | Thieving 20 | silk | the Ardougne market |
| `steal_fur_stall` | Thieving 35 | fur or grey wolf fur | the Ardougne market |
| `steal_silver_stall` | Thieving 50 | silver ore | the Ardougne market |
| `steal_gem_stall` | Thieving 75 | an uncut sapphire, emerald, ruby or diamond | the Ardougne market |

Pickpocketing (`rlscape/sim/thieving.py`, Caleb 2026-10-30: "Targets and stalls") follows the server's Pickpockets
table and ThievingListeners. A success rolls the target's table: every guaranteed item, then one weighted pick
(the H.A.M. tables' clue slot gives nothing, as in combat drops); loot that doesn't fit is lost. An attempt needs
the guaranteed items to fit or a free slot, so non-stackable loot ends the option at a full inventory. The
character eats at half HP or at the target's largest hit, whichever is higher. Each target is at its server spawn
nearest Lumbridge, outside the Wilderness and the access table's areas. No option for: rogues (Wilderness only),
cave goblins (Dorgesh-Kaan, outside the travel model), bearded bandits (no spawns).

The desert targets are south of the Shantay Pass (Caleb, 2026-10-30: model it like the Al Kharid toll). Going south,
a walk buys a pass from Shantay for 5 coins and hands it to the gate's guard; going north is free. Without 5 coins
in the inventory the desert is unreachable, and options whose site is there are masked (`rlscape/sim/movement.py`).
Desert heat on the walk from the gate and the magic carpets aren't modelled.

Stalls (Stall, StallThiefPulse) are in the Ardougne market, each at its merchant's spawn (an estimate to verify).
A steal takes 3 ticks and a free slot, gives one of the stall's rewards, and empties the stall for its restock time
(baker 4 ticks, silk 13, fur 25, silver 50, gem 300). 4 in 15 steals are noticed by a market guard within 8 tiles,
and every stall has one. Then the steal fails and the character runs off and comes back (Caleb, 2026-10-30),
taking the guard's swings while it disengages and 20 ticks away (both to calibrate). The spice stall is left out:
the server's Stall table doesn't list Ardougne's spice stall (object 2564).

## 3. Processing

These work from the inventory and run until the inputs run out. They happen at the nearest suitable station.

| Id | Preconditions | Inventory inputs | Output |
|---|---|---|---|
| `smelt_bronze` / `smelt_iron` / `smelt_steel` | Smithing 1 / 15 / 30 | copper + tin / iron ore / iron ore + 2 coal | bars (iron 50% success) |
| `smith_bronze` / `smith_iron` / `smith_steel` / `smith_mithril` | Smithing level for the best item the bars allow (mithril: 50), hammer | bars | the best smithable item for the bars held: platebody, platelegs, etc. Mithril bars come from the GE (§8); sim v0 has no mithril ore or smelting. |
| `cook_fish` | Cooking level for the food | raw food | cooked food (with burn chance), on a fire lit where the character stands when it holds a tinderbox and a log it can light, otherwise at the nearest range; bread dough, cake and barley always need a range |
| `burn_logs` | tinderbox, Firemaking level | logs | — |
| `bury_bones` | — | bones / big bones | — |

## 3.5 Skills added for sim v1 (Caleb, 2026-10-28)

Crafting, Agility, Herblore and Runecrafting become trainable in sim v1, before E2 (env contract §5); Fletching was
brought forward into sim v0 (Caleb, 2026-10-31; §2). Their
options are an open question (`docs/open-questions-log.md`, OQ-2): Claude drafts them in a later catalog version for
Caleb's review, following the same rules as §2–§3: preconditions,
inputs, a fixed duration *D*, server formulas, and calibration. The likely shape:

| Skill | Likely options | Notes |
|---|---|---|
| Fletching | brought forward into sim v0 (Caleb, 2026-10-31): see §2 | |
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
  (agent choice, 2026-10-29; reversible).
- **Ranged and magic in sim v0 (2026-10-29):**
  - A ranged slot is open while the character has a kit: a bow or crossbow with ammunition it accepts, a thrown
    weapon, or a crystal bow. It is ranked by the best of accurate, rapid and longrange.
  - A magic slot uses the highest-level elemental spell the Magic level allows and the runes pay for.
  - Each shot uses one arrow. The arrows that land are picked back up when the loot mode takes arrows. Each cast
    pays its runes, and a worn elemental staff stands in for its own.
  - Fights end `out_of_ammo`, and a candidate's rates are capped by how long the ammunition lasts.
  - **Agent choice (reversible):** spells are cast by hand at the autocast rate, so magic doesn't need a staff. The
    server's autocast does, and the starter kit has none.

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
| `bank_deposit` | walk to the nearest bank; deposit everything that isn't the kit of the task at hand, the last activity the character did (Caleb, 2026-10-30; `rlscape/sim/kits.py`). Worn items stay worn. The kits: the best usable axe (and a tinderbox and a knife, for the chop-and-burn and chop-and-fletch paths) or pickaxe; a Fletching path's knife and inputs; a fishing method's tool and bait; food for thieving; a processing activity's tools and inputs; for a fight, food, what the class's fight would wear from the inventory, and runes for magic. With no task yet, everything goes. |
| `bank_withdraw_for_<task>` (gathering) | woodcutting, mining, fish_shrimp, fish_fly, fish_lobster: walk to the nearest bank and take out the task's kit: the best usable axe (with a tinderbox and a knife, if banked) or pickaxe if none as good is held, or the fishing method's tool and all its bait. 5 actions. |
| `bank_withdraw_food` | walk to the nearest bank and take out food, the best healing first, into the free slots, whatever it is (cooked catches as well as the four GE tiers) |
| `take_knife` | walk to the nearest knife spawn (the server's ground spawns: in and beside Lumbridge Castle) and pick it up; offered while no knife is held anywhere. Caleb, 2026-10-31: "very convenient for a fresh starting character". |
| `bank_withdraw_for_<activity>` | walk to the nearest bank; withdraw the inputs one processing activity needs, up to a full inventory. Banknotes of the inputs held (from GE buys) are banked first. Interchangeable inputs are only those the level allows: logs Firemaking can burn, raw food Cooking can cook (2026-10-30, found by the scripted guide). One per §3 activity, so 10 actions. |
| `bank_withdraw_gear_<class>` | melee, ranged, magic: walk to the nearest bank; withdraw the gear that beats what the character carries for that combat class (the weapon, for ranged with its ammunition, then armour, the biggest defence gain first), up to the free slots. For magic it also takes every banked rune, which a deposit for another task banks (2026-10-30, found by the scripted guide). Fights put it on from the inventory. 3 actions (§8). |
| `bank_withdraw_<food>` | one per GE food tier (mackerel, tuna, monkfish, shark): walk to the nearest bank, bank the banknotes held of that food, and withdraw it into the free slots. 4 actions (§8). |
| `bank_deposit_worn` | walk to the nearest bank; bank the worn gear (the banker's "deposit worn items"), except what `bank_deposit` keeps (tools, ammunition), so a worn axe or pickaxe stays on. Masked unless something else is worn (§8). |
| `bank_withdraw_for_sale` | walk to the nearest bank and take out produce to sell, as banknotes (the bank's withdraw-as-note setting), so each item's stack fits in one slot, the most valuable stacks first, up to the free slots. Produce is what `bank_deposit` banks, apart from the gear the character would take out to fight (`bank_withdraw_gear_<class>`) and items that neither note nor stack. Caleb, 2026-10-30. |
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
| `sell_ge_<item>`, `sell_ge_misc` | walk to the GE; sell; the frozen buyer pays the 2009 price for items that have one. A per-item sell also sells the item's banknotes. |
| `sell_store_<item>`, `sell_store_misc` | walk to the nearest general store; sell at low-alchemy value minus overstock. Overstock is tracked within an episode (§8): the store's own stock for items it sells, otherwise the player stock every general store shares, which the server clears every 3 hours. |

## 8. Buying

Decided by Caleb, 2026-10-27 to 2026-10-30 (`docs/decision-log.md`); built in sim v0 (`rlscape/sim/buying.py`;
run energy and weight in `rlscape/sim/energy.py`).

**Sources** (from the fork's code):
- **GE** (`buy_ge_<item>`): the frozen seller fills a buy at once, at the 2009 price, from unlimited supply. The
  server has no buy limits. Only items with a 2009 price can be bought; every item below has one.
- **Shops** (`buy_shop_<item>`): a separate action wherever a nearby authentic shop stocks the item (decided), so the
  agent learns the price-versus-travel trade-off.
  - **Price:** ⌈value × m / 100⌉ a unit, with m rising from 100% at normal stock to 130% when sold out; each further
    unit of a purchase is priced at one less in stock.
  - **Stock:** shared (`personalized_shops = false`) and tracked within an episode. It restocks 1 unit per 100
    ticks.
  - **Paying:** the coins for the whole purchase must be in the inventory.

**Actions** (133 buys; every shop kept, including those that never beat the GE on price):

| Group | Items | GE | Shop | Lot |
|---|---|---|---|---|
| Axes | iron, steel, mithril, adamant, rune | all | Bob's (Lumbridge): iron, steel | 1 |
| Pickaxes | iron, steel, mithril, adamant, rune | all | Nurmof's (Dwarven Mine): all | 1 |
| Fishing | fishing rod, fly rod, harpoon, lobster pot; bait; feathers | all | Gerrant's (Port Sarim): all | 1; 200 bait or feathers |
| Hammer | hammer (smithing needs one; the starter kit has none) | yes | Lumbridge general store | 1 |
| Scimitars | iron, steel, mithril, adamant, rune | all | Zeke's (Al Kharid): iron, steel, mithril | 1 |
| Armour pieces | iron to rune: full helm, platebody, platelegs, kiteshield | all 20 | none | 1 |
| Bows | oak, willow, maple shortbow | all | Lowe's (Varrock): all | 1 |
| Arrows | bronze, iron, steel, mithril, adamant | all | Lowe's: all | 100 |
| Runes | air, water, earth, fire, mind, chaos, death, nature | all | Aubury's (Varrock): all but nature | 100 |
| Staves | staff of air, water, earth, fire | all | Zaff's (Varrock): all | 1 |
| Food | mackerel, tuna, monkfish, shark; bread | the 4 fish | Wydin's (Port Sarim): bread | 100 |
| Processing inputs | raw trout, lobster, swordfish; oak, willow, maple, yew logs; iron, steel, mithril bars | all 10 | none | 1,000 |
| Fletching (2026-10-31) | knife | yes | none | 1 |
| Fletching inputs (2026-10-31) | bowstring; bronze to rune arrowtips and dart tips; bronze to runite unfinished bolts (19) | all | none | 1,000 |

That's 96 GE actions and 37 shop actions. A knife is also free: `take_knife` (§5) picks up Lumbridge Castle's. Every bought item joins the vocabulary *V* (§9), so its sell, alch and
drop actions exist.

**How a buy works:**
- **Amount:** as many as the coins allow, up to the lot. A shop buy is also capped by its stock and the free
  slots.
- **Paying:** coins in the inventory pay first. If they're short, the trip starts with a bank stop to withdraw the
  rest. The GE has bankers beside it, so there the stop costs only the banking time.
- **Where purchases land:**
  - Shops: in the inventory, as items.
  - GE: banknotes for more than one of an item that has a banknote. A single item, or a stack (runes, arrows, bait,
    feathers), comes as itself; a single item with no room comes as a banknote.
  - Banknotes can't be eaten or worn. The withdrawals (§5) bank them and take out the items.
- **Timing:** the walk, plus 8 ticks at the GE or 3 at a shop (the selling constants; calibrate).
- **Mask:** a buy is open only when all of these hold:
  - **Affordable:** at least one unit, with the coins in the inventory and the bank. Banked coins count only if
    they can reach the inventory, onto coins carried or into a free slot; otherwise the trip couldn't withdraw
    them (2026-10-30, found by the scripted guide, which looped on such a buy).
  - **Usable now:** gear and weapons meet their wear requirements, including quest locks; axes and pickaxes meet
    their skill level; arrows meet their Ranged level.
  - **An upgrade** (gear, tools, bows and weapons only): better than anything held and usable now for that role,
    whether worn, in the inventory or in the bank. A fishing tool, the hammer or a staff is open unless the same
    item is held.
  - **Room:** a free inventory slot, unless the purchase stacks onto one held.
  - **Shops only:** in stock.
- **Armour as pieces:** the rune full helm, platelegs and kiteshield can be bought at Defence 40; only the rune
  platebody waits for Dragon Slayer.

**Food:** four GE tiers and bread.

| Food | Heals | 2009 GE price | gp per HP | Heals fully once max HP is at least |
|---|---|---|---|---|
| Mackerel | 6 | 10 | 1.7 | 12 |
| Tuna | 10 | 79 | 7.9 | 20 |
| Monkfish | 16 | 327 | 20.4 | 32 |
| Shark | 20 | 845 | 42.3 | 40 |
| Bread (Wydin's) | 5 | about 12 | 2.4 | 10 |

- No other fish heals as much as a tier for less per HP.
- The trade-off is gold against HP per slot. Doubling the HP per trip (tuna to shark) costs about 10× the gold.
- The sim eats at half the maximum HP and healing stops at the maximum, so the useful size grows with Hitpoints.

**Gear and the task:**
- **Withdrawals:** deposits are unchanged, so `bank_deposit` banks unworn gear. `bank_withdraw_gear_<class>`
  (§5) takes a class's best gear back out, and fights put it on from the inventory.
- **Run energy and weight (built 2026-10-30):** gear goes on when it suits the task. For example,
  no metal armour for tasks with a lot of running. The sim has the server's run energy (`WalkingQueue`, `Settings`),
  checked tick by tick against the server:
  - **Drain:** each running tick drains 0.55 × (1 + kg / 100)% energy. Running covers 2 tiles a tick; walking
    covers 1. Under 1% energy, the server turns run off.
  - **Restore:** each tick not running, walking or not, restores 0.6 × 100 / (175 − Agility)%: empty to full in
    about 290 ticks at Agility 1. Death restores it to 100%.
  - **Weight:** worn items, plus one of each inventory slot's item (a stack counts once; banknotes weigh nothing).
  - **Walks:** each walk starts with run on and runs until energy is under 1%, then walks the rest. Energy is in the
    character state and the observation (env contract §3).
  - `bank_deposit_worn` (§5) lets the agent leave armour in the bank. Taking it off into the inventory wouldn't help,
    because the inventory's weight counts too.
  - On the server, the bridge's `set_run` turns run on at the start of each walk, as a person would. The character
    spawns with run on (`AIPlayer.init`), but once energy first runs out the server leaves it off.
  - **How much it matters:** from full energy at Agility 1, a character runs about 360 tiles unencumbered, 290 in
    full rune (27 kg) and 230 carrying 28 iron ore (63 kg). Shorter trips aren't slowed at all; a 400-tile trip
    takes about 18% longer in full rune and 32% longer with the ore. A 15-minute activity restores energy fully, so
    weight matters most for trips back to back (banking, the GE).

**Shops used** (`server/Server/data/configs/shops.json`):

| Shop (region) | Bought here | Example: shop price at normal stock vs 2009 GE |
|---|---|---|
| Bob's Brilliant Axes (lumbridge) | iron, steel axes | iron axe 56 vs **28** |
| Nurmof's Pickaxe Shop (Dwarven Mine) | iron to rune pickaxes | iron **140** vs 209; rune 32,000 vs **19,100** |
| Gerrant's Fishy Business (Port Sarim) | rods, harpoon, lobster pot, bait, feathers | fly rod **5** vs 77; lobster pot **20** vs 70 |
| Lumbridge General Store | hammer | hammer **1** vs 13 |
| Zeke's Superior Scimitars (al_kharid) | iron, steel, mithril scimitars | steel 400 vs **200** |
| Lowe's Archery Emporium (Varrock) | shortbows, arrows | bows and arrows up to about 2× the GE |
| Aubury's Rune Shop (Varrock) | runes but nature | up to about 2× the GE |
| Zaff's staff shop (Varrock) | elemental staves | up to about 2× the GE |
| Wydin's Food Store (Port Sarim) | bread | bread **12** vs 25 |

**Bold** marks the cheaper source. Shops win for cheap tools and bread; the GE wins for weapons, armour, runes,
arrows and high-tier pickaxes.

**Not used:**
- Shops that sell pieces of armour sets: Horvik's, Louie's, Peksa's and Cassie's.
- Three shops with stock of 150,000+, including dragon scimitars ("Delicious Goods", "Armour & Supplies",
  "The Fairy's Culinary Goods"). They look like 2009Scape additions, not 2009 content.
- Shops behind quests, guild levels or members-only cities: the Magic Guild's store, the Fishing Guild's shop,
  Lletya, Ali's runes.
- Ranged and magic armour (leather, studded, coif, wizard robes): fights choose armour by defence for every combat
  class, so they'd never be worn over plate. They need class-aware armour choice first.

**Server side:** GE buys use the bridge's `ge_offer` and `ge_collect`, which collects as "Where purchases land" says (fork change,
2026-10-29). Walks use `set_run` (fork change, 2026-10-30). Shop buys, putting gear on, bank withdrawals and
`bank_deposit_worn` each need a bridge command through the player's path: fork changes, each with Caleb's go-ahead.

## 9. Item vocabulary and size

**Vocabulary *V*:** the items this catalog produces or consumes, every item the agent can buy (§8), and the most
valuable common drops from the enemy pool.

**Decided (Caleb, 2026-10-30): 156 items,** frozen in `data/vocabulary.csv` (`rlscape/vocabulary.py`). It's the
catalog's default. `docs/vocabulary-draft.md` shows how the rule was applied and lists the items. The readings
Caleb accepted:
- **"Common" drops** are worth at least 1,000 gp/hr in some fight the agent would be offered and drop in at least
  20 of the sweep's fights: 50 drops.
- **Smithed products** that no other group names stay misc: 29 items, sold or alched in bulk.
- **Burnt food** stays out.

The groups: 18 gathered, 12 processed (bars and cooked food), 15 smithed items that can also be bought or drop, 4
consumed, 57 more bought, and the 50 drops. Noted items count as their items; coins are never in *V*. All 156 have
a 2009 GE price and can be alched.

Every other item is **misc**. It still counts in net worth, and is handled by the `*_misc` actions. *V* is fixed
before training, so the action space doesn't change during the study. Sim v1's four skills and quests will add
items; *V* is revisited when they're specified (`docs/open-questions-log.md`, OQ-2).

**Size (*V* = 176: the 156 accepted and 20 fletching inputs added by the same rule on 2026-10-31; selling as "all
in the inventory"):**

| Group | Actions |
|---|---|
| Skilling slots | 20 (5 skills × 2 by XP/hr + 2 by gp/hr; they replace the 31 fixed gathering and thieving actions) |
| Processing | 10 |
| Combat | 30 |
| Loot mode | 4 |
| Inventory | 2 deposits + 10 processing withdrawals + 5 gathering-kit withdrawals + 1 take knife + 177 drops (176 + misc) + 1 reclaim gravestone + 3 gear + 4 food tiers + 1 any food + 1 for sale = 205 |
| Alchemy | 354 (high and low, 177 each) |
| Selling | 354 (GE and store, 177 each) |
| Buying | 133 (96 at the GE, with the knife and 19 fletching inputs; 37 at shops) |
| **Total in sim v0** | **1,110** |
| Quests (sim v1) | 21 |

Each *V* item adds 7 observation features: its inventory and bank counts, and its 5 actions' mask entries (env
contract §3).

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
