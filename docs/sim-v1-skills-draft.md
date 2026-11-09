# Sim v1 skills: Crafting, Agility, Herblore, Runecrafting (the spec, from Claude's draft)

Caleb, 2026-11-08 (OQ-2): "crafting should include leather armor, dragonhide armor, spinning, and gems. Agility
should add course laps. Herblore should add herbs and potions. Runecrafting should add runes and essence."

This began as Claude's draft of those options for Caleb to check (`m002-oq2-oq7-oq15`). Caleb answered its choices the
same day (`m002-oq2-choices`; the decision log's "Decided: OQ-2's sim v1 choices"), so it's now the spec the four
skills are built to. Each choice below keeps its options and states Caleb's answer (Choices B and G later that day,
OQ-38). Three questions the Abyss raised are open: OQ-39 to OQ-41. It follows the option catalog's rules for skilling (§2) and
processing (§3): preconditions, inputs, a fixed duration *D*, the server's formulas, and measured overheads. The
numbers below are read from the server's source (paths under `server/Server/src/main/content/global/skill/`). The
option catalog gets these options (v1.4) once their actions are fixed.

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
(a) keeps buying the agent's decision, as for fletching and smithing. **Caleb: (a).**

## 2. Crafting

All levels and XP from `crafting/armour/LeatherCrafting.java` (soft leather and dragonhide), `armour/HardCraftPulse`,
`StuddedArmourPlugin`, `spinning/SpinningItem.java`, `gem/Gems.java`; tanning from `TanningProduct.java`.

**Tanning** (a tanner: Ellis in Al Kharid, the Crafting Guild's, Sbott in Canifis; no XP; coins a hide): cowhide to
soft leather 1 gp, to hard leather 3 gp; green, blue, red and black dragonhide to dragon leather 20 gp each. As built
(2026-11-08), a fresh character reaches only Ellis: Canifis and the Ranging Guild's Leatherworker (Ranged 40) aren't in
the travel model's reach, and the Crafting Guild needs a brown apron worn, which no option gets.

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
| Studded body | 41 | 40 | a leather body and steel studs (out: Choice C) |
| Studded chaps | 44 | 42 | leather chaps and steel studs (out: Choice C) |

**Dragonhide armour** (needle and thread; vambraces 1 leather, chaps 2, body 3):

| Colour | Vambraces | Chaps | Body |
|---|---|---|---|
| Green | 57, 62 XP | 60, 124 | 63, 186 |
| Blue | 66, 70 | 68, 140 | 71, 210 |
| Red | 73, 78 | 75, 156 | 77, 234 |
| Black | 79, 86 | 82, 172 | 84, 258 |

**Spinning** (a spinning wheel: Lumbridge Castle's first floor, Seers' Village): wool to a ball of wool, level 1, 2.5
XP; flax to a bowstring, level 10, 15 XP, one every 4 ticks (`SpinningPulse`). Bowstrings feed Fletching's stringing
(§2). The server has 13 wheels (found with `debug_nearby`, 2026-11-08; `data/stations.csv`); a fresh character reaches
eight.

**Gems** (a chisel): uncut to cut. Opal 1 (10 XP), jade 13 (20), red topaz 16 (25), sapphire 20 (50), emerald 27
(67), ruby 34 (85), diamond 43 (107.5), dragonstone 55 (137.5), onyx 67 (168). On this server every cut succeeds:
`GemCutPulse` has no crushing, which 2009 had for the semi-precious three.

**The paths:**
- `tan_<leather>` (6: soft and hard leather, and the four dragon leathers; gp paths, since tanning gives no XP);
- `craft_<item>` for each armour piece (8 leather, 12 dragonhide);
- `spin_wool`, `spin_flax` at the nearest wheel, and **Choice B:** (a) *recommended*: `pick_flax_spin`, picking flax
  at Seers' Village's field and spinning it at the wheel there (a gathering path with its processing counterpart, as
  §2 pairs them; picking gives no XP), and `pick_flax` kept; (b) spinning only from bought flax. **Caleb: (a)**
  (OQ-38). Picking (`FieldPickingPlugin`): a pick every 2 ticks, no XP; each plant gives 4 to 9 picks, then is gone
  for 30 ticks. The field is south of Seers' Village (about 2737, 3441), and the wheel is on a house's first floor
  there (by 2711, 3471), as the bundled flax bot's route has them (`bots/SeersFlax.kt`). As built: 48 plants in
  (2737-2750, 3438-3452), and the wheel at (2710, 3471, 1). `pick_flax` and `pick_flax_spin` are gathering paths
  (rlscape.sim.skilling's `Path`), so they end at a full inventory, of flax or of bowstrings, as fishing's cooking
  paths do, and the agent banks (catalog §1: activity options don't bank). That differs from this draft's "banks the
  bowstrings, again" (Claude's choice, reversible).
- `cut_<gem>` (9).

**Choice C, what's in:** (a) *recommended*: everything above; (b) leave out studded armour (it needs Smithing's
steel studs), or (c) leave out snakeskin as well. Snakeskin (Morytania's swamp snakes, 15 gp to tan) and jewellery
(gold bars, moulds, a furnace) are out unless Caleb adds them: neither is in OQ-2's list. **Caleb: studded leather,
snakeskin and jewellery are left out.** Crafting is tanning, the 8 leather and 12 dragonhide pieces, spinning and gems.

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

**As built** (2026-11-08; `rlscape/gamedata/agility.py`, `rlscape/sim/agility.py`, `scripts/measure_agility.py`):
- **XP a lap:** Gnome Stronghold 86.5 (no falls); Barbarian Outpost 152.2 (the obstacles' 106 and the 46.2 bonus; the
  third low wall gives its XP but its flag is past the course's size); Wilderness 571.5 (72.5 and the 499 bonus).
- **The entries:** the Barbarian Outpost's pipe (Agility 35) gives no XP on this server (`AgilityShortcut` never awards
  a shortcut's), and the Wilderness's door and ridge (Agility 52) give 15 and can fail into the wolf pit. The
  Wilderness's pipe needs 49.
- **Falls, as the server has them:** a rope swing's fail does nothing (`AgilityHandler.fail` plays out only with an
  animation, and the swings pass none), so it's a click again; the Barbarian log's into the water, swum out; the
  Barbarian ledge's to the ground west of the net, which can't be climbed from there, so the lap goes on at the walls
  without its bonus; the Wilderness stepping stones' into the lava (26% of the hitpoints left), its log's onto the
  spikes below.
- **Times:** measured on the server, each obstacle's click to the next click as laps run, each fall's click to the next
  click, and the entries'. The Gnome Stronghold's lap is 74 ticks; the Barbarian Outpost's 71 without falls.
- Eating is thieving's rule (the retreat point, or the largest fall hit if that's higher), not the fights'.
- **The Wilderness log's spike pit** has aggressive skeletons (level 25): a fall there is attacked while the character
  climbs out, at a rate measured on the server (Caleb, OQ-46 (a)), and can kill.

**Choice D, the courses:** (a) *recommended*: Gnome Stronghold, Barbarian Outpost and Wilderness, and the Pyramid
with its top handed to Simon Templeton for coins as the server pays; (b) the same without the Pyramid. The Brimhaven
arena is out in both. **Caleb: the Pyramid and Brimhaven are left out**, so the courses are the Gnome Stronghold, the
Barbarian Outpost and the Wilderness. Barbarian Fishing trains Agility too (below).

**Choice D2, the Barcrawl:** the Barbarian Outpost course's gate (2115, 2116) needs Alfred Grimhand's Barcrawl
finished (`BarbarianOutpostCourse.kt`), a miniquest that `spawn`'s quest flags don't cover (2026-11-06's rule: every
quest the server has). (a) *recommended*: flag the Barcrawl finished at spawn too, as the quests are (flags only); (b)
leave the Barbarian course out. **Caleb: (a). Built** (`RLCommands.completeMiniquests`), and a fresh character passes
the gate on the server. **Found:** the travel model has no way to the Barbarian Outpost course tile checked (2552,
3556); the start tiles need checking on the server when they're built (OQ-16's kind).

**Barbarian Fishing** (Caleb, 2026-11-08: an Agility training method; `gather/fishing/barbfishing/`). No miniquest is
needed: `BarbFishingPulse` asks for Fishing 48, Agility 15 and Strength 15, a barbarian rod (11323) in the inventory, a
free slot, and bait (feathers, fishing bait, fish offcuts, roe or caviar).

| Fish | Fishing | Strength and Agility | XP: Fishing, Agility, Strength | Catch chance, level 1 to 99 |
|---|---|---|---|---|
| Leaping trout | 48 | 15 | 50, 5, 5 | 43% down to 35% |
| Leaping salmon | 58 | 30 | 70, 6, 6 | 25% up to 28% |
| Leaping sturgeon | 70 | 45 | 80, 7, 7 | 19% up to 25% |

Every 5 ticks the pulse tries the three in that order, each at its own chance at the character's Fishing level
(`Fish.getSuccessChance`), and the first that succeeds is caught, for one bait. Five spots move among seven tiles at
Otto's Grotto (2500–2506, 3494–3516), each after 400 to 2,000 ticks. Checked live: 8 trout in 200 ticks at Fishing 48,
each 50 Fishing, 5 Agility and 5 Strength XP.
- **The path:** `barb_fish`, a gathering path that trains Fishing, Agility and Strength: walk to the grotto, fish to a
  full inventory, then bank or drop the fish, as fishing's paths do. It joins the Fishing and Agility slots' rankings
  (§1) by its XP in each. The leaping fish go in *V* only if something uses them (Choice I); cutting them for roe and
  caviar (Cooking) is out.
- **As built** (2026-11-08, `rlscape/sim/barbfishing.py`, `scripts/calibrate_barbfishing.py`): as above, the first try
  6 ticks after the click. The pulse fishes a placeholder spot, not the one clicked, so the spots' moves don't stop it.
  Calibrated within 1.00 to 1.03 at Fishing 48, 70 and 99.
- **The rod** is untradeable, so it goes on the frozen GE at a set price, as Ava's devices did. The price is OQ-41.
  Otto's bed gives the rod only once his Barbarian Training starts, which stays unflagged, so the GE is the way to get
  one.

**Agility in travel** (built, 2026-11-08; OQ-16 (a): "Agility shortcuts with Agility"): seven of the server's
shortcuts (`agility/shortcuts/`), each both ways, are transports in travel, taken from their levels on both backends
(`rlscape/gamedata/shortcuts.py`): Falador's west wall (5), the lumberyard's fence (13), the coal trucks' log balance
(20), the River Lum's stepping stone (31), Ardougne's log balance (33), the Al Kharid pit (38) and Rellekka's log
balance (48). They're the ones whose two ends the planner joins only by a long walk round, in places the sim travels.
None can fail; the log balances give their XP on the way. Agility also raises run energy's restore (already in the
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
vial of water and the secondary, the unfinished potion made and finished in the one path. As built (2026-11-08,
`rlscape/sim/herblore.py`): a unit can also start from an unfinished potion carried or banked, and grinding takes a
pestle and mortar out with the load; the times are `HerblorePulse`'s and `GrindItemPlugin`'s, each batch after its
clicks (to measure).

**Choice E, the potions:** (a) *recommended*: the 21 above, leaving out the quest and minigame mixes (Relicym's balm,
Serum 207, Blamish oil, Sanfew, Guthix balance, weapon poisons, Summoning and Hunter potions); (b) the combat ones
alone; (c) all the server has. **Caleb: (a).**

**Choice F, grinding:** (a) *recommended*: a path grinds its secondary when the character holds the whole ingredient
(a unicorn horn, say) and a pestle and mortar, and the dust can also be bought; (b) dusts only bought. Crushed nests
need a bird's nest, which the 2009 GE doesn't price: the Saradomin brew path then needs nests from drops or the
woodcutting nests the sim already rolls. **Caleb: (a).**

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

Air to body take rune or pure essence; the rest pure essence (`RuneCraftPulse`). Entering the ruins takes the
altar's talisman (used on the ruins) or its tiara (worn). Three more altars need quests the server lacks, so it asks
those quests' own requirements (`hasRequirement`, as for the Watchtower teleport):
- **astral** (Runecrafting 40, 8.7 XP, 155 gp a rune in January 2009) is on Lunar Isle. Lokar Searunner's boat from
  Rellekka and the altar both ask Lunar Diplomacy, which unfolds to eight levels the sim trains (Magic 65, Crafting
  61, Mining 60, Woodcutting 55, Firemaking 49, Defence 40, Agility 32, Herblore 5) and four quests that are complete.
  **Out** (Caleb, OQ-39 (b)): no option goes there, and the travel model has no way there. The server would still let
  a character in;
- **death** (Runecrafting 65, 10 XP an essence, pure essence only, 271 gp a rune in January 2009) is reached by the
  Abyss's rift (below), and **opens as the server opens it** (Caleb, OQ-39 (b)): Ranged 60 and Thieving 50, Mourning's
  End Part II's own requirement. Its own ruins are in the Temple of Light, which the travel model doesn't reach;
- **blood** never opens (Legacy of Seergaze asks Construction 20).

**Caleb (OQ-39): (b),** the death altar and not the astral one.

**Essence** (`gather/mining`, `travel/EssenceTeleport.kt`): mined in the rune essence mine, which Aubury in Varrock's
rune shop (and the other wizards) teleports a character to; the mining always succeeds; 5 Mining XP each; from
Mining 30 the server gives pure essence instead (`MiningListener.calculateReward`).

**The paths:** `mine_essence` (a gathering path: to Aubury, the teleport, mine to a full inventory, the portal out,
bank; kept or sold); `rc_<rune>` (10): take essence and the talisman from the bank, walk to the ruins, enter, craft,
walk back and bank, and again; and **Choice G:** (a) *recommended*: `mine_essence_rc_<rune>` too, for the runes whose
ruins are near the mine (air, mind, water, earth, fire, body): mine a load, craft it, again (the gathering path with
its processing counterpart, §2); (b) only the separate paths. **Caleb: (b)** (OQ-38): `mine_essence` and `rc_<rune>`
only. An agent that wants both mines with one option and crafts with the next.

**As built** (2026-11-08): essence isn't mined after all (Caleb: "Rune essence is very cheap and mining it yourself
will almost always be seen as a time waste"), so there's no `mine_essence`: essence is bought on the GE or dropped.
`rc_<rune>` is built for air, mind, water, earth, fire, body, nature and law; cosmic waits for the Abyss's rift
(OQ-45 (a)). Its times at the ruins are measured on the server (`scripts/calibrate_runecrafting.py`). Chaos rune
crafting is out, by the ruins and by the Abyss (Caleb, 2026-11-09: an intentional gap, `docs/post-project-gaps.md`):
its altar is past a ladder maze, only estimated.

**Choice H, tiaras and pouches:** (a) *recommended*: talismans only (the GE sells them; a tiara needs a silver bar
crafted with the talisman, which isn't in OQ-2's list); essence pouches (the Abyss) and the Abyss's shortcut out;
(b) tiaras as well. **Caleb: the Abyss and tiaras are both in,** and the pouches as the server gives them (OQ-40
(c), below).

**Tiaras** (`TalismanEnchantingListener`): a plain tiara (5525) and the talisman, used on the altar inside the ruins,
make the rune's tiara in about 3 ticks, for Runecrafting XP:

| Tiara | Air | Mind | Water | Earth | Fire | Body | Cosmic | Chaos | Nature | Law |
|---|---|---|---|---|---|---|---|---|---|---|
| XP | 25 | 27.5 | 30 | 32.5 | 35 | 37.5 | 40 | 43.5 | 45 | 47.5 |

Worn, a tiara opens its ruins in place of the talisman (`MysteriousRuinListener.handleTiaraOrStaff`), so a trip
carries 28 essence instead of 27. Plain and elemental tiaras are tradeable (45 gp each in January 2009). A plain tiara
is cast from a silver bar in a tiara mould at a furnace, the silver crafting left out with jewellery (Choice C), so
it's bought.
- **The paths:** `make_tiara_<rune>` (10): take plain tiaras and the talisman to the ruins, enter, use them on the
  altar, again; the tiaras are kept, worn or sold. `rc_<rune>` wears the rune's tiara when the character has one, and
  otherwise carries the talisman.

**The Abyss** (`runecrafting/abyss/`):
- **Getting in:** the Mage of Zamorak in the Wilderness (3105, 3554; level 5, north of Edgeville) teleports the
  character once Enter the Abyss is done. The miniquest is flagged complete at spawn, flags only (Caleb, 2026-11-08:
  the Abyss is in; `RLCommands.completeMiniquests`). The teleport lands the character on the outer ring at a random
  point, drains its prayer to 0 and skulls it for 2,000 ticks.
- **The outer ring:** 12 obstacles, rotated so the character lands by a blocked one. A passage always lets it through.
  The others each take a tool and a skill:
  - rocks: a pickaxe, Mining;
  - tendrils: an axe, Woodcutting;
  - a boil: a tinderbox, Firemaking;
  - eyes: Thieving;
  - a gap: Agility.

  Each try passes with chance (level + 1)/100 and takes about 8 ticks. The abyssal leeches, guardians and walkers
  (2263–2265) are aggressive, and the character arrives with no prayer.
- **The inner ring's rifts** go straight to each altar, with the ruins' checks (`MysteriousRuinListener.checkReq`):
  - cosmic: Lost City (complete);
  - law: no weapons or armour (Entrana's rule);
  - chaos: lands by the chaos altar;
  - death: Ranged 60 and Thieving 50, which is Mourning's End Part II's own requirement (the server lacks the quest).
    Open (OQ-39 (b)). The death altar's portal leads to its ruins in the Temple of Light, which the travel model
    doesn't reach, so a death trip ends with a teleport from the altar: the home teleport when it's ready, or a
    teleport spell the character can cast;
  - blood: never (Legacy of Seergaze asks Construction 20).

  No talisman is needed.
- **The paths:** `abyss_rc_<rune>`, one for each altar the Abyss reaches (death among them): take essence (and a tool
  for an obstacle, where one helps) from the Edgeville bank, walk to the mage, teleport, pass an obstacle, enter the
  rift, craft, then bank (a teleport or the walk back), and again. It's a separate path from `rc_<rune>`, so the
  rankings pick whichever is faster from where the character stands, at its levels and with its tools. The obstacles'
  chances, the monsters' damage, and eating are modelled as the fights' are. The teleport skulls the character for
  2,000 ticks, so a death in the Abyss keeps no items (`DeathTask`: none when skulled, one with Protect Item).

**As built** (2026-11-08; `rlscape/sim/abyss.py`, `data/abyss/` from `scripts/export_abyss.py`): the
`abyss_rc_<rune>` paths, ten since chaos went out (Caleb, 2026-11-09).
- **The layouts:** each of the teleport's twelve segments shows its own, measured. Segments 0 to 5 have rocks beside
  the landing, and 6 to 11 a gap; the passage is always opposite.
- **The tools:** a trip carries essence and food only, so it uses the pickaxe or axe worn, never a tinderbox.
- **The monsters:** they attack at a rate fitted on the server, with their own hit chances and no prayer. The
  character eats under twice the hardest hit.
- **Times:** measured on the server (`scripts/measure_abyss.py`). Whole trips are 0.94 to 1.00 of the server's for
  every rune.
- **Chaos:** its rift lands beside the altar, and a portal on the altar's floor leads out.
- **Cosmic and death:** they leave by teleport.
- **The skull and the prayer** (Caleb, OQ-48 (a)): the skull's ticks left are in the observation; the drained
  prayer isn't modelled (the sim has no prayer points), a documented gap (`docs/post-project-gaps.md`).
- **Built since** (2026-11-09): the pouches below and the fight option. The travel model reaches the Abyss by the
  mage's teleport and leaves it by a teleport or its exit (the passage, the body rift, the body altar's portal).
  A fight there also takes the outer ring's crowd, and flicks no prayer (Caleb, OQ-49 (a); `rlscape.sim.abyss.Ring`).

**Pouches** (Caleb, 2026-11-08, OQ-40 (c): as the server gives them; `PouchManager`, `AbyssalNPC`, `DarkMageDialogue`):

| Pouch | Holds | Fill at Runecrafting | Essence before its first decay | Comes from |
|---|---|---|---|---|
| Small | 3 | 1 | never decays | Enter the Abyss: given at spawn, in the bank |
| Medium | 6 | 25 | 264 | a kill of an abyssal monster |
| Large | 9 | 50 | 186 | a kill of an abyssal monster |
| Giant | 12 | 75 | 140 | a kill of an abyssal monster |

- **The drop:** each kill of an abyssal leech, guardian or walker (2263–2265) has a 12-in-750 chance (1.6%, about 63
  kills on average) of dropping the next pouch the character lacks (small, medium, large, giant; it counts the
  inventory, bank and equipment, and a decayed pouch as the pouch). The drop is on the ground, to pick up. Holding
  all four, nothing more drops. The drop needs no Runecrafting level; filling the pouch does.
- **Decay:** filling the medium, large or giant counts the essence put in. Once the count runs out, the pouch decays:
  its capacity falls by 1, 2 or 3, and the next decay comes after 9 × the new capacity. A pouch whose capacity reaches
  0 disappears. So the medium holds 6 for 264 essence, then 5 for 45, 4 for 36, and so on; the large 9 for 186, then
  7, 5, 3 and 1; the giant 12 for 140, then 9, 6 and 3. The server keeps one state for each kind of pouch, not each
  item.
- **Repair:** the Dark Mage in the Abyss's centre repairs every pouch free, through his dialogue.
- **Use:** a pouch is filled with essence from the inventory and emptied back into it. A trip fills the pouches at the
  bank, crafts the inventory's essence, empties the pouches, and crafts again. With all four, a trip carries 30 more
  essence.
- **Value:** untradeable, not on the GE, and the alchemy spell refuses them, so net worth counts them at 0 (env
  contract §4's rule).
- **The fight option in the Abyss:** the combat pool already lists the three abyssal monsters (39, 32 and 29 spawns),
  with drops worth about 760 to 780 gp a kill in net worth, most of it noted pure essence. The travel model doesn't
  reach the Abyss yet. It needs the mage's teleport as a link, the outer ring as a fight site, and a way out (a rift
  and its altar's portal, or a teleport). A fight there is skulled, as above, and the character arrives with no
  prayer.

## 6. The vocabulary (§9) and buying (§8)

**Choice I, which items join *V*:** (a) *recommended*: the inputs the agent buys or holds (they need buy, withdraw
and hold actions), and the products only where something else uses them; the other products stay **misc**, sold and
alched by the misc actions and counted in net worth, as smithed misc items are. (b) every input and product.
**Caleb: (a).**

With (a) and the decided scope, *V* gains about 89 items (all have a 2009 GE price but the bird's nest, the
barbarian rod, which Caleb set at 1,000 gp (OQ-41), and the four pouches, which are untradeable):
- Crafting (about 21): red and black dragonhide (green and blue are in *V*), needle, thread, wool, flax, chisel, the 9
  uncut gems not yet in *V* (5), soft and hard leather and the 4 dragon leathers (the tanned intermediates are
  crafted from). As built (2026-11-08): those 18, and the GE buys all 25 inputs (`buying.CRAFTING_INPUTS`).
- Herblore (about 40): the 4 grimy herbs not yet in *V*, the 15 clean herbs, about 15 secondaries and their whole
  ingredients, a pestle and mortar, vials (empty), and the 15 unfinished potions (they're bought and sold on the GE).
  As built (2026-11-08): 51 new, 66 bought (`buying.HERBLORE_INPUTS`): vials of water, not empty ones, which the
  potions take; the 14 unfinished potions the 21 use; and the bird's nest, on the GE at Caleb's 1,765 gp.
- Runecrafting (about 26): rune and pure essence, the 8 talismans not yet in *V* (earth is), the body rune, the plain
  tiara and the 10 elemental tiaras (worn to enter the ruins), and the four pouches (held: withdraw and hold, their
  buy, sell and alchemy actions masked). The death rune is in *V* already; the astral rune stays out with its altar
  (OQ-39). The Abyss's rifts need no talisman.
- Agility: the barbarian rod (feathers are in *V*); the leaping fish stay misc.

With (b), about 160: the 32 crafted products and the 21 three-dose potions as well. OQ-25 kept only four-dose
potions in *V*; (a) keeps that rule, and the made potions stay misc (fights still drink any dose).

Each item in *V* adds about 4 actions (buy, withdraw, sell or drop) and 7 observation features: with (a) and the
decided scope, about 356 actions (1,709 → about 2,081 with the 16 slots) and 623 features, with one more for each
pouch's current capacity (2,625 → about 3,332).

## 7. Building and calibrating them

The bridge needs: a tanner's interface, the spinning wheel's, the flax's Pick, make-X dialogues (needle on leather,
chisel on gem, vial on herb), herb cleaning (an item option, as burying bones), the ruins and altar clicks (a tiara's
too), Aubury's teleport and the mine's portal, each course's obstacles in order, the barbarian fishing spot, and the
Abyss: the mage's teleport, the obstacles, the rifts, the pouches' Fill and Empty, and the Dark Mage's repair. It also
needs each pouch's current capacity in `state`, for the observation. Most are interface buttons, item uses and clicks
the bridge already sends; the courses and the Abyss are new. The bridge now finds NPCs by the form a player sees (the mage is a multi-NPC), built
2026-11-08.

Each path's time per unit is measured on the server and fitted where it differs, as the processing paths were
(2026-11-07), and gated at ±20%. Crafting's are (2026-11-08, `scripts/calibrate_crafting.py`): a few ticks of clicks
before each batch, fitted, and every case within 1.00 of the server but picking flax (0.92 to 1.00). Herblore's
too (`scripts/calibrate_herblore.py`): cleaning's first tick fitted, every stage and load 1.00.

**Rough cost** (Claude's estimate): Crafting a day, Herblore half a day, Runecrafting a day, the Abyss another and
its fights and pouches half a day more, Agility with Barbarian Fishing a day, and their calibration a day or two. Six
days or so in all, which bears on OQ-17's scope review.
