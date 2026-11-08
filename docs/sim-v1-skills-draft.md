# Sim v1 skills: Crafting, Agility, Herblore, Runecrafting (draft for Caleb)

Caleb, 2026-11-08 (OQ-2): "crafting should include leather armor, dragonhide armor, spinning, and gems. Agility
should add course laps. Herblore should add herbs and potions. Runecrafting should add runes and essence."

This is Claude's draft of those options, for Caleb to check before they're built (`m002-oq2-oq7-oq15`). It follows
the option catalog's rules for skilling (§2) and processing (§3): preconditions, inputs, a fixed duration *D*, the
server's formulas, and measured overheads. The numbers below are read from the server's source (paths under
`server/Server/src/main/content/global/skill/`). Where something needs Caleb's call, the choice is marked
**Choice**, with Claude's recommendation first.

## 1. How the four skills fit the catalog

Each skill gets **4 skilling slots** (`skill_<skill>_xp1/xp2/gp1/gp2`), as the five sim v0 skilling skills have
(§2): its best paths by XP/hr and by gp/hr at the current levels, gear and position. That's 16 more actions, and 16 ×
5 = 80 more observation features (env contract §3's skilling candidates).

Most of the new paths work like Fletching's (§2): at the nearest bank, take out the recipe's inputs, make them,
bank the products, and again, until the inputs (banked or carried) or the time run out. Some need a place (a tanner,
a spinning wheel, an altar, a course). Rates come from the same analytic model as the other skilling paths, checked
against the simulated paths, and every path's time per unit is measured on the server before E2 (env contract §7's
gate).

**Choice A, the inputs:** (a) *recommended*: a path uses inputs the character holds or has banked, and the agent buys
them with the GE buy actions (§8), which these inputs join; (b) a path also buys its own inputs as it goes.
(a) keeps buying the agent's decision, as for fletching and smithing.

## 2. Crafting

All levels and XP from `crafting/armour/LeatherCrafting.java` (soft leather and dragonhide), `armour/HardCraftPulse`,
`StuddedArmourPlugin`, `spinning/SpinningItem.java`, `gem/Gems.java`; tanning from `TanningProduct.java`.

**Tanning** (a tanner: Ellis in Al Kharid, the Crafting Guild's, Sbott in Canifis; no XP; coins a hide): cowhide to
soft leather 1 gp, to hard leather 3 gp; green, blue, red and black dragonhide to dragon leather 20 gp each.

**Leather armour** (a needle and thread; a thread lasts 5 items, as the server counts it):

| Item | Level | XP | Leather |
|---|---|---|---|
| Leather gloves | 1 | 13.8 | 1 soft |
| Leather boots | 7 | 16.3 | 1 soft |
| Leather cowl | 9 | 18.5 | 1 soft |
| Leather vambraces | 11 | 22 | 1 soft |
| Leather body | 14 | 25 | 1 soft |
| Leather chaps | 18 | 27 | 1 soft |
| Hardleather body | 28 | 35 | 1 hard |
| Coif | 38 | 37 | 1 soft |
| Studded body | 41 | 40 | a leather body and steel studs |
| Studded chaps | 44 | 42 | leather chaps and steel studs |

**Dragonhide armour** (needle and thread; vambraces 1 leather, chaps 2, body 3):

| Colour | Vambraces | Chaps | Body |
|---|---|---|---|
| Green | 57, 62 XP | 60, 124 | 63, 186 |
| Blue | 66, 70 | 68, 140 | 71, 210 |
| Red | 73, 78 | 75, 156 | 77, 234 |
| Black | 79, 86 | 82, 172 | 84, 258 |

**Spinning** (a spinning wheel: Lumbridge Castle's first floor, Seers' Village): wool to a ball of wool, level 1, 2.5
XP; flax to a bowstring, level 10, 15 XP. Bowstrings feed Fletching's stringing (§2).

**Gems** (a chisel): uncut to cut. Opal 1 (10 XP), jade 13 (20), red topaz 16 (25), sapphire 20 (50), emerald 27
(67), ruby 34 (85), diamond 43 (107.5), dragonstone 55 (137.5), onyx 67 (168). On this server every cut succeeds:
`GemCutPulse` has no crushing, which 2009 had for the semi-precious three.

**The paths:**
- `tan_<hide>` (4: soft, hard, dragon leather from green/blue, red/black hides; gp paths, since tanning gives no XP);
- `craft_<item>` for each armour piece (10 leather, 12 dragonhide);
- `spin_wool`, `spin_flax` at the nearest wheel, and **Choice B:** (a) *recommended*: `pick_flax_spin`, picking flax
  at Seers' Village's field and spinning it at the wheel there (a gathering path with its processing counterpart, as
  §2 pairs them; picking gives no XP), and `pick_flax` kept; (b) spinning only from bought flax;
- `cut_<gem>` (9).

**Choice C, what's in:** (a) *recommended*: everything above; (b) leave out studded armour (it needs Smithing's
steel studs), or (c) leave out snakeskin as well. Snakeskin (Morytania's swamp snakes, 15 gp to tan) and jewellery
(gold bars, moulds, a furnace) are out unless Caleb adds them: neither is in OQ-2's list.

## 3. Agility

Courses on this server (`agility/`): the Gnome Stronghold (level 1), the Agility Pyramid (30), the Barbarian Outpost
(35) and the Wilderness (52), plus the Brimhaven Agility Arena (tickets, a moving target). The others of 2009 aren't
implemented here (Ape Atoll, Werewolf, Penguin).

| Course | Level | XP a lap | Notes |
|---|---|---|---|
| Gnome Stronghold | 1 | 86.5 (7 obstacles, 47.5, and the lap bonus 39) | no failing obstacles |
| Agility Pyramid | 30 | by level, plus the pyramid top (Simon Templeton, `region/desert/dialogue/SimonTempleton.java`, pays coins for it) | falls and rolling blocks |
| Barbarian Outpost | 35 | obstacles and a 46.2 lap bonus (to read in full when built) | failing obstacles deal damage |
| Wilderness | 52 | obstacles and a 499 lap bonus | Wilderness level 50; failing obstacles; the Wilderness's PvP is off |

**The paths:** `agility_<course>`: walk to the course, run laps until *D* ends, as the server times them (each
obstacle's animation and walk, measured), with the failure chances and damage `AgilityHandler` gives (eating as the
fights do).

**Choice D, the courses:** (a) *recommended*: Gnome Stronghold, Barbarian Outpost and Wilderness, and the Pyramid
with its top handed to Simon Templeton for coins as the server pays; (b) the same without the Pyramid. The Brimhaven
arena is out in both.

**Choice D2, the Barcrawl:** the Barbarian Outpost course's pipe needs Alfred Grimhand's Barcrawl finished
(`BarbarianOutpostCourse.kt`), a miniquest that `spawn`'s quest flags don't cover (2026-11-06's rule: every quest the
server has). (a) *recommended*: flag the Barcrawl finished at spawn too, as the quests are (flags only); (b) leave
the Barbarian course out. **Found:** the travel model has no way to the Barbarian Outpost course and the Agility Pyramid
tiles checked (2552, 3556 and 3354, 2830); the start tiles need checking on the server when they're built (OQ-16's
kind).

**Agility in travel:** with Agility trainable, the shortcuts the server has (`agility/shortcuts/`: log balances,
stepping stones, rope swings, the Al Kharid pit, grapples, …) can join the travel model's crossings at their levels,
as OQ-16 (a) puts it ("Agility shortcuts with Agility"). Agility also raises run energy's restore (already in the
sim: `rlscape.sim.energy`).

## 4. Herblore

From `herblore/Herbs.java`, `UnfinishedPotion.kt`, `FinishedPotion.kt` (Druidic Ritual is complete from the start).

**Herbs:** cleaning a grimy herb (an item option, anywhere):

| Herb | Level | XP | Herb | Level | XP |
|---|---|---|---|---|---|
| Guam | 3 | 2.5 | Avantoe | 48 | 10 |
| Marrentill | 5 | 3.8 | Kwuarm | 54 | 11.3 |
| Tarromin | 11 | 5 | Snapdragon | 59 | 11.8 |
| Harralander | 20 | 6.3 | Cadantine | 65 | 12.5 |
| Ranarr | 25 | 7.5 | Lantadyme | 67 | 13.1 |
| Toadflax | 30 | 8 | Dwarf weed | 70 | 13.8 |
| Spirit weed | 35 | 7.8 | Torstol | 75 | 15 |
| Irit | 40 | 8.8 | | | |

**Potions:** a clean herb in a vial of water makes the unfinished potion (no XP), and a secondary finishes it, at
the finished potion's level and XP. The standard ones:

| Potion | Level | XP | Herb | Secondary |
|---|---|---|---|---|
| Attack | 3 | 25 | guam | eye of newt |
| Antipoison | 5 | 37.5 | marrentill | unicorn horn dust |
| Strength | 12 | 50 | tarromin | limpwurt root |
| Restore | 22 | 62.5 | harralander | red spiders' eggs |
| Energy | 26 | 67.5 | harralander | chocolate dust |
| Defence | 30 | 45 | ranarr | white berries |
| Agility | 34 | 80 | toadflax | toad's legs |
| Combat | 36 | 84 | harralander | goat horn dust |
| Prayer | 38 | 87.5 | ranarr | snape grass |
| Super attack | 45 | 100 | irit | eye of newt |
| Super antipoison | 48 | 106.3 | irit | unicorn horn dust |
| Fishing | 50 | 112.5 | avantoe | snape grass |
| Super energy | 52 | 117.5 | avantoe | mort myre fungus |
| Super strength | 55 | 125 | kwuarm | limpwurt root |
| Super restore | 63 | 142.5 | snapdragon | red spiders' eggs |
| Super defence | 66 | 160 | cadantine | white berries |
| Antifire | 69 | 157.5 | lantadyme | dragon scale dust |
| Ranging | 72 | 162.5 | dwarf weed | wine of zamorak |
| Magic | 76 | 172.5 | lantadyme | potato cactus |
| Zamorak brew | 78 | 175 | torstol | jangerberries |
| Saradomin brew | 81 | 180 | toadflax | crushed nest |

The server makes three-dose potions. Dusts are ground with a pestle and mortar (`GrindingItem.java`: unicorn horn,
chocolate bar, goat horn, blue dragon scale, bird's nest).

**The paths:** `clean_<herb>` (15); `potion_<potion>` (21): from the clean herb (or grimy, cleaned on the way), a
vial of water and the secondary, the unfinished potion made and finished in the one path.

**Choice E, the potions:** (a) *recommended*: the 21 above, leaving out the quest and minigame mixes (Relicym's balm,
Serum 207, Blamish oil, Sanfew, Guthix balance, weapon poisons, Summoning and Hunter potions); (b) the combat ones
alone; (c) all the server has.

**Choice F, grinding:** (a) *recommended*: a path grinds its secondary when the character holds the whole ingredient
(a unicorn horn, say) and a pestle and mortar, and the dust can also be bought; (b) dusts only bought. Crushed nests
need a bird's nest, which the 2009 GE doesn't price: the Saradomin brew path then needs nests from drops or the
woodcutting nests the sim already rolls.

## 5. Runecrafting

From `runecrafting/Rune.java`, `RunecraftingData.kt`, `RuneCraftPulse.java` (Rune Mysteries is complete from the
start).

**Runes** (level, XP an essence, and the levels where an essence makes one more rune):

| Rune | Level | XP | More runes at | Altar's ruins |
|---|---|---|---|---|
| Air | 1 | 5 | 11, 22, 33, … 99 | south of Falador (2983, 3292) |
| Mind | 2 | 5.5 | 14, 28, … 98 | north of Falador (2980, 3514) |
| Water | 5 | 6 | 19, 38, 57, 76, 95 | Lumbridge Swamp (3183, 3163) |
| Earth | 9 | 6.5 | 26, 52, 78 | north-east of Varrock (3304, 3475) |
| Fire | 14 | 7 | 35, 70 | Al Kharid's desert (3312, 3253) |
| Body | 20 | 7.5 | 46, 92 | west of Edgeville (3051, 3443) |
| Cosmic | 27 | 8 | 59 | Zanaris (Lost City) |
| Chaos | 35 | 8.5 | 74 | the Wilderness (3058, 3589) |
| Nature | 44 | 9 | 91 | north of Shilo Village (2869, 3021) |
| Law | 54 | 9.5 | — | Entrana (no weapons or armour) |

Air to body take rune or pure essence; the rest pure essence (`RuneCraftPulse`). The death and blood altars need
quests the server doesn't have, and astral's needs Lunar Diplomacy (not in the server's 68): out. Entering the ruins
takes the altar's talisman (used on the ruins) or its tiara (worn).

**Essence** (`gather/mining`, `travel/EssenceTeleport.kt`): mined in the rune essence mine, which Aubury in Varrock's
rune shop (and the other wizards) teleports a character to; the mining always succeeds; 5 Mining XP each; from
Mining 30 the server gives pure essence instead (`MiningListener.calculateReward`).

**The paths:** `mine_essence` (a gathering path: to Aubury, the teleport, mine to a full inventory, the portal out,
bank; kept or sold); `rc_<rune>` (10): take essence and the talisman from the bank, walk to the ruins, enter, craft,
walk back and bank, and again; and **Choice G:** (a) *recommended*: `mine_essence_rc_<rune>` too, for the runes whose
ruins are near the mine (air, mind, water, earth, fire, body): mine a load, craft it, again (the gathering path with
its processing counterpart, §2); (b) only the separate paths.

**Choice H, tiaras and pouches:** (a) *recommended*: talismans only (the GE sells them; a tiara needs a silver bar
crafted with the talisman, which isn't in OQ-2's list); essence pouches (the Abyss) and the Abyss's shortcut out;
(b) tiaras as well.

## 6. The vocabulary (§9) and buying (§8)

**Choice I, which items join *V*:** (a) *recommended*: the inputs the agent buys or holds (they need buy, withdraw
and hold actions), and the products only where something else uses them; the other products stay **misc**, sold and
alched by the misc actions and counted in net worth, as smithed misc items are. (b) every input and product.

With (a), *V* gains about 75 items (all have a 2009 GE price but the bird's nest):
- Crafting (about 24): red and black dragonhide (green and blue are in *V*), needle, thread, steel studs, wool, flax,
  chisel, the 9 uncut gems not yet in *V* (5), soft and hard leather and the 4 dragon leathers (the tanned
  intermediates are crafted from), leather body and chaps (studded's inputs).
- Herblore (about 40): the 4 grimy herbs not yet in *V*, the 15 clean herbs, about 15 secondaries and their whole
  ingredients, a pestle and mortar, vials (empty), and the 15 unfinished potions (they're bought and sold on the GE).
- Runecrafting (11): rune and pure essence, the 8 talismans not yet in *V* (earth is), and the body rune.
- Agility: none (the pyramid top is untradeable; it's handed in for coins).

With (b), about 160: the 32 crafted products and the 21 three-dose potions as well. OQ-25 kept only four-dose
potions in *V*; (a) keeps that rule, and the made potions stay misc (fights still drink any dose).

Each item in *V* adds about 4 actions (buy, withdraw, sell or drop) and 7 observation features: with (a), about
300 actions (1,709 → about 2,030 with the 16 slots) and 525 features (2,625 → about 3,230).

## 7. Building and calibrating them

The bridge needs: a tanner's interface, the spinning wheel's, make-X dialogues (needle on leather, chisel on gem,
vial on herb), herb cleaning (an item option, as burying bones), the ruins and altar clicks, Aubury's teleport and
the mine's portal, and each course's obstacles in order. Most are interface buttons and item uses the bridge already
sends; the courses are new.

Each path's time per unit is measured on the server and fitted where it differs, as the processing paths were
(2026-11-07), and gated at ±20%.

**Rough cost** (Claude's estimate): Crafting a day, Herblore half a day, Runecrafting a day, Agility a day, and their
calibration a day or two. Four to five days in all, which bears on OQ-17's scope review.
