# Option Catalog (v1.3, Signed off; v1.4 being built)

**v1.4** (2026-11-08, building sim v1 per OQ-2 and `docs/sim-v1-skills-draft.md`; to confirm when the four skills
are built): Crafting's skilling slots and paths (§2), and XP slots hold only paths that give XP; Crafting's inputs in
*V* and the GE buys (§8, §9); Herblore's skilling slots and paths (§2); Agility's skilling slots and laps (§2);
Runecrafting's skilling slots and paths (§2), and its essence and talismans in *V* and the GE buys (§8, §9);
Barbarian Fishing (§2) and the barbarian rod in *V* and the GE buys (§8, §9); seven Agility shortcuts in travel
(§4).

**Status:** v1.3, 2026-11-06: quests are out, and every quest the server has is complete from the start (Caleb;
§10); the anti-dragon shield, the dragon dagger and longsword and the Fremennik helms are bought on the GE (§4.B,
§8), and *V* has 27 more items (§9). v1.2, 2026-10-30, replaces §8's buying table with Caleb's buying decisions (2026-10-29 and 30): the
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
| `lumbridge_swamp` | Lumbridge Swamp | Draynor | copper / tin mine; *verify*; net fishing |
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
agents choose a path, not a fixed method. Nine skills (Woodcutting, Fishing, Mining, Thieving, Fletching, Crafting,
Herblore, Runecrafting, Agility) × 2 slots by XP/hr + 2 by gp/hr = 36 actions, `skill_<skill>_xp1/xp2/gp1/gp2`. They replace the 31 fixed gathering and thieving
actions.
A path in an XP slot doesn't also fill a gp slot (the next best takes its place, as in combat), and slots are
recomputed every decision. The observation carries each slot's rates (env contract §3). A gathering path's rate
counts its site's aggressive monsters (2026-11-08): it keeps the share of XP per tick that the sim's own option keeps
under their attacks (`aggression.gathering_share`), so a fresh character's slots rank Lumbridge Swamp's shrimp above
Draynor's, where the Dark wizards are.

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

**Crafting** (sim v1, v1.4; Caleb, 2026-11-08, OQ-2; `rlscape/sim/crafting.py`) has paths at a bank as Fletching's
are, one per recipe: `cut_<gem>` (9, with a chisel, a gem a tick) and `craft_<item>` (the 8 leather and 12
dragonhide pieces, with a needle and thread, a piece every 5 ticks). The recipes are the server's (`Gems`,
`LeatherCrafting`, `HardCraftPulse`). Thread goes as the server's `decayThread` takes it: a reel every 5 items,
its charges saved on the character. Tanning and spinning work between the nearest bank and the nearest usable
station: `tan_<leather>` (6, at a tanner, for its fee and no XP) and `spin_wool`, `spin_flax` (at a wheel, one every 4
ticks). Flax is picked in Seers' Village's field (`pick_flax`, kept, no XP) or picked and spun at the Seers' wheel
(`pick_flax_spin`), both ending at a full inventory. The agent buys the inputs on the GE (§9).

**Herblore** (sim v1, v1.4; Caleb, 2026-11-08, OQ-2's Choices E (a) and F (a); `rlscape/sim/herblore.py`) has paths
at a bank too: `clean_<herb>` (15, the grimy herb cleaned, a herb a tick, for its XP) and `potion_<potion>` (the 21
standard potions). A potion path takes out as many units as fit (3 slots a unit, 2 from unfinished potions, and one
for a pestle and mortar if it grinds) and makes each from what's there: an unfinished potion, or a vial of water and the herb (clean, or grimy and cleaned first, for
its XP too); and the secondary, or its whole ingredient ground first, with a pestle and mortar taken out for it. The
stages are the server's (`HerblorePulse`, `GrindItemPlugin`): the unfinished potions one a tick, the finished ones
one every 3 ticks, grinding one every 2, each batch after its clicks. The product has three doses.

**Agility** (sim v1, v1.4; Caleb, 2026-11-08, OQ-2 Choice D; `rlscape/sim/agility.py`) has course laps:
`agility_gnome` (Agility 1), `agility_barbarian` (35, entered by the outpost's pipe) and `agility_wilderness` (52,
by the door and ridge). A path walks to the course and runs laps until the option's time is up, at the server's
times: each obstacle's XP, the lap bonus at the lap's last flag, and on the two courses that can fail, each failing
obstacle rolled at the character's Agility (`AgilityHandler.hasFailed`), a fall's hit and its measured recovery. It
eats as thieving does, and stops when it's out of food then. No gp: a lap path fills only XP slots. A fall into the
Wilderness log's pit is attacked by its skeletons (OQ-46 (a)). **Barbarian Fishing** (`barb_fish`,
`rlscape/sim/barbfishing.py`) fishes Otto's Grotto with the barbarian rod (bought on the GE) to a full inventory,
for Fishing, Agility and Strength XP; it ranks in the Fishing and the Agility slots by its XP in each. Agility
levels open seven of the server's shortcuts in travel (§4).

**Runecrafting** (sim v1, v1.4; Caleb, 2026-11-08, OQ-2; `rlscape/sim/runecrafting.py`) has `rc_<rune>` for the nine
runes whose ruins the travel model reaches: air, mind, water, earth, fire, body, chaos, nature and law. A path works
between the nearest bank and the ruins, as tanning does: it takes out the talisman and a load of one kind of essence
(rune essence first for air to body; pure only for the rest), enters the ruins, crafts every essence at the altar,
and leaves by the portal. An essence makes as many runes as the rune's multiple levels the character has reached
(rl.conf's formula revision 530). Law's path banks the weapons and armour Entrana's monks refuse; nature's carries the
Karamja boat's 60 gp. The times inside the ruins are the server's. Essence isn't mined (Caleb: it's cheap, and mining
it wastes the time); the agent buys it (§9). A path wears the rune's tiara when the character has one, in place of the
talisman, and carries 28 essence. `make_tiara_<rune>` (nine) uses pairs of a plain tiara and the talisman on the altar,
14 a trip, for the tiaras' XP (the talisman used up; a loss in gold, as the GE sells the tiaras for less). The cosmic
altar waits for the Abyss's rift (OQ-45 (a)), as does the death altar.

A path that gives no XP (tanning, picking flax) fills only a gp slot: the XP slots take the best paths that give XP
(v1.4).

That's 83 paths in sim v0: woodcutting 12, fishing 8, mining 7, thieving 20, fletching 36; and in sim v1 crafting's
39, herblore's 36, runecrafting's 18 and agility's 3. Mining's include iron at the Al
Kharid mine (Caleb, 2026-10-31), kept or smelted, beside Varrock's: scorpions roam it, so it costs a low-level miner
hitpoints (below). Fishing's include shrimp at Lumbridge Swamp (Caleb, 2026-11-01), kept or cooked, beside
Draynor's: Draynor's spots are next to the bank, but its Dark wizards make them dangerous for a character of combat
level 14 or less.

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
| `fish_shrimp_swamp` | Fishing 1, small net | raw shrimps / anchovies | lumbridge_swamp (its three net spots) |
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
| Runecrafting | craft runes at an altar from essence | needs Rune Mysteries; essence bought (not mined: Caleb, 2026-11-08) |

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
    server's autocast does, and the starter kit has none. *Checked live (2026-11-07):* a hand cast is one spell, and
    casting again as soon as the server takes it (3 ticks after the last) lands the spells 5 ticks apart, the
    autocast rate.
- **Ranged fights safespot (2026-11-07, OQ-27 (d), Caleb):** a monster without a safespot is a bad ranged target
  unless its damage is trivial (below). Otherwise a ranged
  slot offers it only at sites with a safespot from the server (`data/ranged_safespots.csv`, the bridge's
  `ranged_safespots`): a tile it can be shot from where, chasing, it gets stuck short of attacking, holding from at
  least 80% of its wandering (Caleb, 2026-11-08, OQ-36 (a); half before), and which no aggressive monster
  reaches. Melee monsters
  are held by walls and fences; skeletal wyverns, which shoot, are outranged (Caleb). From there it does no damage,
  and only the site's monsters the safespot holds against count. Arrows lie where the monster stands, a pile per
  100 ticks of shooting, picked up with the drops between kills, plus the walk from the safespot and back. While
  aggressive monsters guard the piles and aggression hasn't run out, the fight leaves them until the oldest would
  go. The pickup time is one for every class. Trivial damage (Caleb, OQ-30 (b)): the fight needs no food, its
  expected damage over the option less what regenerates fitting in the hitpoints above the retreat point. A bow
  takes no shield, so a monster with special damage, such as a dragon, is ranged only from a safespot.
- **Magic fights safespot too (2026-11-07, OQ-34, Caleb),** by the same rules, at magic's range of 10 tiles
  (`MagicSwingHandler.canSwing` is ranged's test with distance 10). Casting leaves no piles: only the drops are
  fetched from the safespot.
- **Monsters of other kinds near a fight (2026-11-07, OQ-35 (a), Caleb).** Away from a safespot, a site's aggressive
  monsters of other kinds (spawned within 10 tiles) whose level would pick the character engage it between kills,
  while nothing attacks it (the overhead to the next monster, the pickups, a wait for a respawn), each spawn at a
  rate measured on the server (0.045 a tick, at the animated spades' possessed pickaxe), until the region's
  aggression runs out. In single combat it must kill one before the next target, so each engagement is a kill of
  that monster in the fight's plan, its time, damage, XP and drops counted. The slots count the expected fights; a
  site where one can't be hurt by the plan, or fails the danger filter below, is left out while aggression lasts.
  From a usable safespot none reaches the character. Not modelled: multi-combat areas, where they attack at once,
  and the ammunition the neighbour fights use (the slots' cap counts the target's only; the fight pays it).

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
| Dragonfire (all dragons) | an anti-dragon shield worn or carried: a fight against a dragonfire monster puts a carried one on (`wield_best`'s `protect`), and the ranking rates the monster for the character wearing it. Bought on the GE since 2026-11-06 (Caleb; §8). Behind the shield a third of a dragon's swings are breath, 0 to 5 each (`rlscape.combat.rates`); an antifire potion carried stops it (shield and potion: complete immunity, as in 2009), and the ranking takes off the share its doses cover |
| Monsters that block a combat style (`protect_style`) | ruled out for the blocked class only |
| Poison | no gear check; its damage is in the expected damage (2026-11-06): a poisonous monster's swings poison 4 times in 10, hit or miss, so a protection prayer doesn't stop it, and the poison hits every 30 ticks (`rlscape.combat.rates`). Antipoison carried (§8) takes off the share its doses cover: a dose cures it and keeps it off for 150 ticks, or 600 for the super, and fights drink one when poisoned |
| Slayer-gear monsters (banshees, dust devils, turoths and so on) | never offered: their gear isn't modelled (`SLAYER_GEAR_NPCS`), and since 2026-11-07 no Slayer level keeps them out |

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
- **hazards aren't targets where they spawn** (`HAZARDS`, Caleb, 2026-11-05): Taverley dungeon's two Black
  Knights east of the lesser demons, whom the server doesn't let a character attack; only that pair (Caleb,
  2026-11-06), since the dungeon's other Black Knights fight as usual. The four moss giants west of the Fishing
  Guild too (Caleb, 2026-11-06), for the same reason; the other moss giants stay targets. And the animated spades on
  the Abandoned Mine's first floor (Caleb, 2026-11-08, OQ-42): there, one that a character who has since left dealt
  more than half its hitpoints can't be killed, and stays alive at 0. The possessed pickaxe beside them and the
  spades in the Chaos Tunnels stay targets.
- **the Yanille Agility Dungeon is out of the project** (`IGNORED_AREAS`, Caleb, 2026-11-06): no monster in it is a
  target (zombies, a giant bat, skeletons, poison spiders, chaos druids, Salarin the Twisted); the same monsters
  elsewhere are. Its inner room is past a pile of rubble that takes Agility 67, and Salarin there, whom only the
  strike spells hurt, holds a character in single combat. They stay in the world, so as aggressive
  monsters they still attack a gathering character near them (§2); a fight ignores them, as it does every monster
  but its target. Monsters near a fight are measured on the server before they're modelled (OQ-19, answered).
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

**Slayer levels lock nothing** (Caleb, 2026-11-07, OQ-32: dropped for every monster, in the fork too). Slayer has no
training options, so it stays at 1. The Slayer monsters whose gear the sim doesn't model stay out: 15 of the 35 in
the pool that had a level. The other 20 are open, among them abyssal demons, bloodvelds, nechryaels and skeletal
wyverns.

The requirement grammar is `quest:` / `started:` / `underway:` / `item:` / `level:` / `coins:` / `never`, combined with
`&` and ` or ` (see the module docstring).

**Where the rules come from.** Each row names the server check that enforces it, or says the server doesn't. 2009Scape
leaves many 2009 gates unenforced: no check was found for Ape Atoll, the Lighthouse, the Kalphite rope or Entrana. The
table applies the 2009 rule anyway. The candidate list is built in Python for both backends, so the server is never
asked to fight a locked monster.

**Slayer levels are dropped in the fork too** (Caleb, 2026-11-07, OQ-32). From 2026-10-28 the fork refused attacks
above the attacker's Slayer level (`NPC.isAttackable`, `IdleAbstractNPC.isAttackable`). Now neither refuses, and
`NPC.checkImpact` no longer cancels the hits (upstream had). The ice cooler no longer asks for Slayer 22. The live
test `test_slayer_levels_lock_no_monster` has a fresh character fight cave crawlers (Slayer 10) and gain XP.

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
- Light sources (the server has no dark zones) and Slayer gear (earmuffs, face masks) aren't modelled, so the
  monsters that need the gear aren't offered.

Quests aren't options (§10): every quest the server has is complete from the start, so the areas those quests open are
available, and the monsters fought only while a quest is underway never are.

### Inventory and travel in the rates (implemented)

A candidate's XP/hr and gp/hr cover the option's whole duration, not just the fighting:
- **Fighting time:** kills continue until the looted drops fill the free inventory slots. Stackables (coins, runes,
  arrows, banknotes, summoning charms) cost no new slot.
- **Bank trips:** each full inventory costs the round trip to the site's nearest bank, plus 8 ticks of banking.
- **Getting there:** the walk from the character's location is taken out of the option's duration.
- **Between kills** (measured on the server): 3 ticks to find and reach the next monster, for every class (refitted
  on 2026-11-07 from 10 for melee and 8 for ranged on 2026-11-05; magic's calibration the same day bears it out).
  Where a site has few of the monster, kills wait for respawns: at most
  one every (respawn + fighting) / spawns ticks, with the spawns within 15 tiles and the monster's respawn delay. So
  of two sites, the one with more of the monster can be worth the longer walk.

Travel (Caleb, 2026-11-01) is the planned route on the server's own collision map (`rlscape/routes.py`,
`data/travel/`) in steps, at 1.5 tiles per tick for estimates (walks use run energy), plus the measured overheads
(2.3 ticks to start, 0.083 a step) and 12 ticks per change of plane or underground. Upper floors and dungeons are
anchored at the surface tile they lie over or under (dungeons sit 6,400 tiles north of it). The planner crosses the
Wilderness ditch, the Gnome Stronghold's gate and the Grand Tree's doors, and the Al Kharid toll gate when the toll
is paid. Off its map, or upstairs or underground where it can't join two places (their stairs and ladders aren't
mapped yet), it's still straight-line distance × 1.3. The server walker clicks along the same routes.

**Unreachable places (Caleb, 2026-11-01).** A place no way the model knows reaches, for any character, is
unreachable: walking, the crossings, the Shantay gate, every teleport and every boat, from Lumbridge. That's 231 of
the 2,792 places the sim travels to, mostly quest areas no way the model knows reaches, and pens and cells. A place the character
can't get to now (an island without the fare or a teleport) is unreachable for it until it can: its options are
masked, and the combat slots skip it. Ways the model doesn't know yet (some items, quest steps) are OQ-16.

**Agility shortcuts (OQ-16 (a), 2026-11-08; built; which seven is Claude's choice, to confirm).** Seven of the
server's shortcuts, each both ways, are transports in travel, taken from their Agility levels like any other way
(`rlscape/gamedata/shortcuts.py`): Falador's west wall (5), the lumberyard's fence (13), the coal trucks' log balance
(20), the River Lum's stepping stone (31), Ardougne's log balance (33), the Al Kharid pit (38) and Rellekka's log
balance (48). Each was measured on the server: 4 to 7 ticks a crossing (the stepping stone 13), and 3 more in a trip
(fitted). None can fail, and the log balances give their XP on the way (5 at the coal trucks, 1 at the others). Both
backends: the bridge clicks the shortcut as a player does (`rlscape/bridge/travel.py`).

**Transports (Caleb, 2026-11-01; built).** Travel includes the home teleport, the standard teleport spells, every
teleport jewellery item at every charge (usable and buyable at any charge), the teleport tablets, the Grand seed pod,
the fixed ships and the charters (`rlscape/gamedata/transports.py`, from
the server's source and data). Every walk takes the fastest way the character can use at the time, paying for it,
on both backends: walking; a teleport, then a walk; a walk to a boat, the boat, then a walk; or a teleport, a walk,
a boat and a walk. What it can use depends on its levels, its quests, and the runes (or staves), coins, jewellery
or tablets it carries; teleports aren't possible above Wilderness level 20 (jewellery: 30), and Entrana's boat
takes no one with weapons or armour. Jewellery loses a charge per use; tablets and seed pods are used up. The home
teleport is free, once every 30 minutes (Caleb, 2026-11-01; a fork change, counted in game ticks). Travel estimates
for candidates take the better of walking and the home teleport then a walk, when it's ready; trips an option repeats
(bank trips) walk. The Ectophial is left out: this server doesn't implement Ghosts Ahoy (Caleb, 2026-11-01). The times are measured on the server: 27 trips, every one within ±20% (decision log, 2026-11-01). The
teleport items aren't in *V* yet.

### Aggressive monsters at gathering sites (Caleb, 2026-10-31; implemented)

A gathering option (woodcutting, mining, fishing) follows Caleb's rule when an aggressive monster attacks
(`rlscape/sim/aggression.py`):
- auto-retaliate is off, so attacks don't stop the gathering (checked on the server);
- it fights only a trivial monster: the setup's max hit is at least half the monster's hitpoints, and the monster's
  max hit is under a quarter of the character's hitpoints as the fight starts;
- when its hitpoints fall under twice the monster's max hit, it runs out of the monster's aggressive range, eats
  (or waits) until that's no longer so, and walks back.

Which monsters: the aggressive, attackable ones spawned within 10 tiles of the site, that pick a character whose
combat level is at most twice their own, until it has spent 1,000 ticks in the map region (the server's tolerance,
in game ticks on the fork). How often they attack and how long running away takes are measured at Draynor's willows
(a Dark wizard: once every 29 ticks), at Al Kharid's iron (a scorpion: once every 20 ticks) and at Draynor's shrimp
spots, where nothing blocks the wizards: one engages a low-level fisher about once every 221 ticks, casts every 5
ticks until the fisher runs, and goes on casting as it runs, so about half its runs away end in death. Other sites use
the willows' until calibrated. Safespotting (Caleb): the server runner gathers from a tile no aggressive melee monster
that would pick the character can hit (the bridge's `safespots`), when there's one at the site; the sim has it in
the measured attack rate. Al Kharid's iron has none for a low-level miner: its five scorpions reach every rock.

### Prayers in fights (Caleb, 2026-10-31; implemented)

Every fight flicks prayers on its own, with no actions for it (`rlscape/combat/prayers.py`). On 2009Scape a prayer
that's on only in the ticks that need it never drains (checked live), so prayer points stay full:
- **On the monster's swing ticks:** the protection prayer for its style if the Prayer level has it (Magic 37,
  Missiles 40, Melee 43): its hits deal nothing. Otherwise the best defence prayer, and against magic the best Mystic
  prayer too (Caleb: defence prayers only "unless an enemy has multiple damage types or the agent does not have
  access to the protection prayer associated"; the sim gives each monster one style).
- **On the character's swing ticks:** the best accuracy and damage prayers for the class: attack and strength, the
  ranged prayers (accuracy and max hit) or the Mystic prayers (accuracy). Not on a tick next to a monster swing,
  since two ticks in a row would drain. A monster starts swinging on the character's swing ticks, so with two even
  attack speeds that never happens.
- Chivalry and Piety need King's Ransom, which the server doesn't have, so they stay locked.

The candidate rates, the danger filter and the sim's fights all use it, so a monster whose style the character can
protect against deals no damage, and training Prayer opens harder monsters.

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
| `drop_<item>` | drop every unit of one vocabulary item from the inventory (dropped items leave net worth); masked for items the game offers Destroy for, not Drop (Ava's devices) |
| `drop_misc` | drop every non-vocabulary item, but those the game offers Destroy for |
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

**Actions** (151 buys; every shop kept, including those that never beat the GE on price):

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
| Anti-dragon shield (2026-11-06) | the anti-dragon shield, masked while one is held | yes | none | 1 |
| Quest weapons (2026-11-06, OQ-24) | dragon dagger and longsword (Attack 60, Lost City), a melee tier above rune | both | none | 1 |
| Quest helms (2026-11-06, OQ-24) | berserker, archer, farseer and warrior helms (Defence 45, the Fremennik Trials) | all 4 | none | 1 |
| Antipoison (2026-11-06) | antipoison(4) and super antipoison(4), one a buy so each comes as a potion | both | none | 1 |
| Combat potions (2026-11-06) | attack, strength, defence, their supers, ranging, magic (4); fights drink to keep the boost (`rlscape.sim.potions`) | all 8 | none | 1 |
| Antifire (2026-11-06) | antifire potion(4); fights against dragons drink one when the last runs out | yes | none | 1 |

That's 114 GE actions and 37 shop actions. A knife is also free: `take_knife` (§5) picks up Lumbridge Castle's. Every bought item joins the vocabulary *V* (§9), so its sell, alch and
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
- **The quest gear** is scored like the rest: the dragon longsword beats the rune scimitar, the dragon dagger
  doesn't; the berserker and warrior helms beat the rune full helm on defence. The archer and farseer helms' ranged
  and magic bonuses count for nothing until armour is chosen per combat class (see "Not used").

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
before training, so the action space doesn't change during the study. Sim v1's four skills will add items; *V* is
revisited when they're specified (`docs/open-questions-log.md`, OQ-2).

**Redrafted with every quest complete (Caleb, 2026-11-06; OQ-23).** The rule, rerun with every quest the server has
complete and an anti-dragon shield against dragonfire, proposes 179 items. The 16 not in *V* were added: the shield;
from dragons, dragon bones, green and blue dragonhide, adamantite ore and a rune dagger; from Morytania and Port
Phasmatys, Blamish shells, snails, raw chicken, two seeds and a mithril chainbody; a vial of water and a mithril 2h
sword. Nothing was taken out, though 13 items in *V* aren't proposed now (decision log). The quest gear the buy
list took on (OQ-24) joined as bought items, and once the drop tables' shared sub-tables were modelled (the rare
drop table, gems, herbs, seeds), the rule proposed 5 more, added by Caleb: rune arrows, the tooth half of a key, a
rune 2h sword, an earth talisman and mithril bolts. Then the potions (Caleb): antipoison, super antipoison, the
eight combat potions and antifire, the four-dose potions alone (OQ-25, Caleb). The lower doses aren't in *V* but
stay consumable: fights drink any dose, deposits keep them, the misc actions leave them be, and the observation
counts each potion's doses (env contract §3). Then Ava's attractor and accumulator, which the GE sells at Caleb's
prices (2026-11-07). They're untradeable in the game, so their alchemy, store-sale and drop actions stay masked (the
game offers Destroy, not Drop); the GE buys them back at the same prices. A ranged fight wears the best device
carried (no other fight does), with its attraction off: it saves ammunition, and the accumulator, which needs
Ranged 50, also gathers the shots its catch misses that would land (Caleb, OQ-28). The 38 metal chest pieces the
server lists stop the catch (`data/ava_interference.csv`), so a ranger wearing a device leaves them off (Caleb,
OQ-29). Then every tradeable crossbow and bolt on the 2009 GE (Caleb, 2026-11-07): 11 crossbows, one-handed but
Karil's, so a shield goes with them, and 53 bolts with their poisoned, gem-tipped and enchanted kinds, whose effects
aren't modelled (they rank by ranged strength); mithril bolts were in already. Broad bolts are Destroy-only, so their
drop stays masked. 279 in all.

Sim v1 (v1.4, to confirm; OQ-2's Choice I (a), Caleb): the inputs the agent buys or holds join *V*, and the products
only where something else uses them. Crafting's (2026-11-08): the uncut gems, the soft, hard and dragon leathers, the
hides tanned, wool, flax, thread, a needle and a chisel, 25 in all, which the GE sells (§8, Choice A (a)); 18 weren't
in *V* (cowhide, the green and blue dragonhides and four uncut gems were). The cut gems, the armour, and balls of wool
stay misc; bowstrings were in *V* already. 297 in all. Herblore's (2026-11-08): the 15 herbs grimy and clean, the 14
unfinished potions the 21 potions use, the 15 secondaries and the 5 whole ingredients ground into them, vials of water
and a pestle and mortar, 66 in all, which the GE sells (§8, Choice A (a)); the bird's nest at Caleb's 1,765 gp, as it's
untradeable on this server and had no 2009 price, and the alchemy spell and stores refuse it. 51 weren't in *V*. The
made potions stay misc (three doses; OQ-25 keeps four-dose potions alone in *V*). 348 in all. Runecrafting's
(2026-11-08): rune and pure essence, which isn't mined (Caleb), in lots of 1,000; the nine runes' talismans and plain
tiaras, in lots of 14 (a tiara load); and the nine runes' tiaras, one each; 21 in all, which the GE sells. 19 weren't
in *V* (the mind and earth talismans were). The runes made were in *V* for magic but body runes, which stay misc. 367
in all.

**Size (*V* = 279: the 156 accepted, 20 fletching inputs added by the same rule on 2026-10-31, 38 on 2026-11-06 and 65
on 2026-11-07;
selling as "all in the inventory"):**

| Group | Actions |
|---|---|
| Skilling slots | 20 (5 skills × 2 by XP/hr + 2 by gp/hr; they replace the 31 fixed gathering and thieving actions) |
| Processing | 10 |
| Combat | 30 |
| Loot mode | 4 |
| Inventory | 2 deposits + 10 processing withdrawals + 5 gathering-kit withdrawals + 1 take knife + 280 drops (279 + misc) + 1 reclaim gravestone + 3 gear + 4 food tiers + 1 any food + 1 for sale = 308 |
| Alchemy | 560 (high and low, 280 each) |
| Selling | 560 (GE and store, 280 each) |
| Buying | 217 (180 at the GE, with the knife, 19 fletching inputs, the anti-dragon shield, 6 quest items, 2 antipoisons, 8 combat potions and antifire, Ava's 2 devices, 11 crossbows and 53 bolts; 37 at shops) |
| **Total in sim v0** | **1,709** |
| Sim v1 so far (v1.4) | Crafting's 4 skilling slots; Crafting's 25 GE buys (needle and chisel one each, the rest in lots of 1,000) and its 18 new *V* items' 90 actions: 1,828; Herblore's and Runecrafting's 4 skilling slots each; Herblore's 66 GE buys (the pestle and mortar one, the rest in lots of 1,000) and its 51 new *V* items' 255 actions: 2,157; Agility's 4 skilling slots: 2,161; Runecrafting's 21 GE buys (the essence in lots of 1,000, the talismans and plain tiaras in lots of 14, a rune's tiara one) and its 19 new *V* items' 95 actions: **2,277** |

Each *V* item adds 7 observation features: its inventory and bank counts, and its 5 actions' mask entries (env
contract §3).

Masking keeps it workable: at any moment only the items actually in the inventory unlock their
sell / alch / drop actions, typically around 30–80 valid actions. A 20-hour episode now runs to roughly 250–400
decisions, because activities stop at a full inventory.

## 10. Quests

**Out of the experiment (Caleb, 2026-11-06).** There are no quest options. Every quest the server has is complete from
the start, so no quest blocks content (env contract §1, v1.12):
- **Which:** the 68 quests the server registers, worth 126 quest points (`gd.implemented_quests`). The `Quests` enum
  lists 150; the server can't complete the other 82, and the sim keeps the content behind them shut (the decision
  log has the server's rule for them).
- **Flags only:** the quest points and the unlocks come with them, no quest XP or items. The bridge's `spawn` sets
  them (`RLCommands.completeEveryQuest`).
- **What that opens:** 21 of the access table's 55 rules (Morytania, Crandor, West Ardougne, the Fremennik Isles,
  Waterbirth, Trollheim and others), 123 quest-locked items (the rune platebody and green d'hide body, the dragon
  dagger and longsword, the crystal bow and shield, the Fremennik Trials' gear), the toll gate, the Lumbridge Castle
  range, darts, and quest-locked teleports and charters. Herblore and Runecrafting need no quest work in sim v1.
- **The anti-dragon shield is bought on the GE** (Caleb, 2026-11-06, OQ-22), at its January 2009 price of 301 gp,
  reversing the 2026-10-27 decision that it come only from Duke Horacio. `rl.conf` blocks nothing on the GE now. The
  Duke would still give one (`DukeHoracioDialogue`), but there's no option to ask him (§4.B, §8).

The quest set this section planned before (21 quests and their options, decided 2026-10-27; 23 with OQ-11's two on
2026-11-01) is in the decision log. OQ-11's open reading ("a later episode") no longer matters.
