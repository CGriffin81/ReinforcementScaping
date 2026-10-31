# Item Vocabulary *V*: How It Was Built

**Status:** accepted by Caleb on 2026-10-30 (the questions and answers are in `docs/decision-log.md`). *V* is the
156 items below, frozen in `data/vocabulary.csv` and the catalog's default (option catalog §9). On 2026-10-31 the
20 fletching inputs joined by the same rule, for 176 (catalog §9).

The rule: option catalog §9, "the items this catalog produces or consumes, plus the most valuable common drops from
the enemy pool", and, from buying (§8), every item the agent can buy. This page applies it to the simulator's data
and gives the accepted readings of its two loose words, "common" and "produces".

- **Data:** `data/vocabulary_draft.csv`, one row per item the rule names. It holds the groups that put the item
  there, its value, its best drop gp/hr and where, and `proposed` (yes or no) with a note when no.
- **Script:** `scripts/draft_vocabulary.py`, which regenerates the CSV after any change to the rule or the sim.

## What *V* controls

Each *V* item gets:
- **5 actions:** `drop_<item>`, `high_alch_<item>`, `low_alch_<item>`, `sell_ge_<item>` and `sell_store_<item>`.
  Each is masked unless the item is in the inventory.
- **7 observation features:** its inventory and bank counts, plus those 5 mask entries, because the mask is part of
  the observation.
- **Pickups** in the `vocabulary` and `valuable` loot modes (§4.D).

Everything else is **misc**. It still counts in net worth, and the `*_misc` actions sell, alch or drop all of it at
once, except what banking keeps: tools, food, ammunition, runes and bait.

| *V* | Actions | Observation features |
|---|---|---|
| empty (before *V*) | 194 | 480 |
| 60 (catalog §9's estimate, made before buying) | 494 | 900 |
| **156 (accepted)** | **974** | **1,572** |
| 208 (the rule taken literally, burnt food aside) | 1,234 | 1,936 |

Quests add 21 actions in sim v1. All 156 items have a 2009 GE price and can be alched, so none of their
actions is always masked.

## How the list was made

- **Gathered:** the logs, ores and fish the gathering options yield, and the gems mining rolls.
- **Processed:** smelted bars, and cooked food from every raw food in *V*.
- **Smithed:** every item the smithing options can make, at any level and with any number of bars.
- **Consumed:** the inputs to smelting, smithing and cooking.
- **Bought:** all 77 items with a buy action (§8).
- **Drops:** a sweep repeats the candidate selection the agent sees, 3 monsters by XP/hr and 3 by gp/hr per combat
  class:
  - over the calibration bands (levels 1, 11, …, 99), with the gear and quests env contract §7 gives each band
  - from 18 hub towns
  - with loot mode `all`: up to 3,564 selected fights (11 bands × 18 hubs × 18 slots)
  - each drop's expected gp/hr is recorded in every fight. A drop is **valuable** if its best gp/hr reaches 1,000
    somewhere, and **common** if it drops in at least 20 of the selected fights.
- Noted drops count as their items, since banking turns banknotes back into items. Coins are never in *V*: they're
  always picked up and are the currency.

## The accepted readings

- **"Common" drops** reach 1,000 gp/hr somewhere and drop in at least 20 of the selected fights: 50 of the 73 that
  reach 1,000 gp/hr.
- **Smithed products** that no other group names stay misc (29 items): the agent sells or alches them in bulk
  through the misc actions, not per item.
- **Burnt food** stays out (8 items).
- Nothing added or removed by hand. The largest groups that were weighed: herb seeds and grimy herbs (23 items,
  only for selling until Herblore arrives in sim v1), black armour and weapons (7), the near misses under
  1,000 gp/hr, and raw beef and raw chicken (which cooking can use).

## The accepted *V* (156)

Each item appears once, under the first group that names it.

**Gathered (18):** raw shrimps, raw anchovies, raw salmon, raw trout, raw lobster, raw rainbow fish, copper ore, tin
ore, iron ore, coal, logs, oak logs, willow logs, yew logs, uncut sapphire, uncut emerald, uncut ruby, uncut diamond.

**Processed (12):** shrimps, anchovies, salmon, trout, swordfish, lobster, rainbow fish, cooked chicken, cooked meat,
bronze bar, iron bar, steel bar.

**Smithed and also bought or dropped (15):** iron platelegs, iron platebody, steel platebody, mithril platebody,
mithril full helm, mithril sq shield, mithril kiteshield, iron pickaxe, steel pickaxe, mithril pickaxe, mithril
longsword, steel 2h sword, steel axe, mithril axe, steel mace.

**Consumed (4):** raw swordfish, raw beef, raw chicken, mithril bar.

**Bought (57 more):**
- fishing: lobster pot, fishing rod, fly fishing rod, harpoon, fishing bait, feather
- food: mackerel, tuna, monkfish, shark, bread
- runes: air, water, earth, fire, mind, chaos, death, nature
- ranged: oak, willow and maple shortbows; bronze, iron, steel, mithril and adamant arrows
- armour: iron, steel, adamant and rune full helms and kiteshields; steel, mithril, adamant and rune platelegs;
  adamant and rune platebodies
- weapons and tools: iron to rune scimitars; iron, adamant and rune axes; adamant and rune pickaxes; the four
  elemental staves; hammer
- maple logs

**Common drops (50),** by best gp/hr (the number of fights they drop in is in brackets):
- unicorn horn (564), wolf bones (184), grimy ranarr (1,126), big bones (39), law rune (965), bones (1,906), cowhide
  (48), limpwurt root (452), unicorn horn dust (46), blood rune (281), cosmic rune (905), grapes (457),
  strawberry (46)
- seeds: ranarr (475), papaya tree (46), snapdragon (455), kwuarm (474), watermelon (844), strawberry (844),
  sweetcorn (844), torstol (455), dwarf weed (475), lantadyme (475), toadflax (475), cadantine (475)
- grimy herbs: kwuarm, guam, dwarf weed, harralander, avantoe, irit, tarromin, lantadyme, cadantine, marrentill
  (866–1,127 each)
- gear: rune med helm (20), iron battleaxe (47), steel longsword (557), black sq shield (34), black 2h sword (365),
  black platebody (364), steel med helm (141), black platelegs (364), bronze spear (456), black kiteshield (46),
  black sword (381), mithril sword (34), black full helm (380), mithril spear (34)
- mind talisman (111)

## Left out, and why

**Rare drops (23; valuable, but in fewer than 20 fights):** spider carcass, skeletal gloves and boots, steel bolts
(p), rune chainbody, ribcage, skull and fibula pieces, steel dart (p), fire and water talismans, black knife, black
longsword, pure essence, adamantite bar, steel chainbody, rune dagger, adamant 2h sword, adamant mace, black robe,
steel battleaxe, black axe, black dagger (p).

**Smithed products only (29):** steel and mithril arrowtips; bronze, iron, steel and mithril bolts (unf); bronze
and steel plateskirts; bronze and iron chainbodies; bronze platebody; bronze full helm; iron, steel and mithril
daggers; bronze longsword; bronze and mithril 2h swords; bronze scimitar; bronze, iron, steel and mithril
warhammers; bronze axe; iron and mithril maces; bronze wire; iron nails; iron spit.

**Burnt food (8).**

**Drops under 1,000 gp/hr (the closest 39, in the CSV):** for example body rune (731 gp/hr, 833 fights), iron
spear, steel spear, iron sword, earth talisman, mithril ore, trading sticks.

## Caveats

- The drop ranking comes from the rate model, so its gp/hr values are expected values to calibrate (E6), not
  measurements. Its high-level picks (unicorns, desert wolves, thieves at level 99) come from the sweep's reference
  gear, not from a trained agent.
- Sim v1's four skills and quests will add items (crafting materials, potions, quest items). *V* is revisited
  when they're specified (`docs/open-questions-log.md`, OQ-2).
