# Buying: Draft for Caleb's Review

> **Superseded (2026-10-30):** every question here is decided, and option catalog §8 (v1.2) holds the result.
> Kept until Caleb has reviewed the catalog; then this file can be deleted.

**Status:** draft, 2026-10-29. Claude wrote it; nothing in the simulator is built. Caleb has decided Q1–Q9, the
gear-withdraw actions (Q3a), the food tiers (Q6) and the lots (§4). Two things are still open:
- **How gear suits the task (Q3b, §5):** decided as a principle; the mechanism, which needs run energy and weight,
  is still to choose.
- **How GE food comes out of the bank (§6).**

On the server, GE collection now follows Q2 (§9). Once everything is settled, the result replaces option catalog §8's
item table and this file is deleted.

**Already decided (catalog §8):**
- Gear, tools and food come from the frozen-price GE seller and from shops.
- There's a separate action per source wherever a nearby authentic shop stocks the item, so the agent learns the
  price-versus-travel trade-off.

## 1. How buying works on the server

The simulator copies these mechanics; they were read from the fork's code.

**GE** (`GrandExchange.buyFromFrozenSeller`, `world.ge_frozen_seller`):
- A buy offer fills **at once, at the 2009 index price, from unlimited supply**.
- Only items with a 2009 price (`historical_price_items`) can be bought; every item proposed below has one.
- The server has **no buy limits**.
- Collecting is the player's choice: as items or as banknotes (`StockMarket.withdraw` with `COLLECT_ITEMS_OP` or
  `COLLECT_NOTES_OP`). The bridge's `ge_collect` now collects as Q2 decided (§9). Banknotes can't be eaten or worn
  until they're unnoted at a bank.

**Shops** (`Shop.kt`, `shops.json`):
- **Price:** each unit costs ⌈value × m / 100⌉, where m rises linearly from 100% at full stock to 130% when the
  shop is empty.
- **Purchase:** the amount is capped by stock and inventory space. The coins for the **whole purchase** must be
  in the inventory, or nothing is bought.
- **Restock:** stock moves back toward normal by 1 unit per 100 ticks (the default `restockRate`).
- **Shared stock:** `personalized_shops = false` in `rl.conf`, so stock is shared.

**Price pattern** (2009 GE price vs. shop price at full stock):

| Cheaper at the GE | Cheaper at a shop |
|---|---|
| axes (iron 28 vs 56; steel 100 vs 200) | fishing rod 5 vs 60; fly rod 5 vs 77; harpoon 5 vs 47; lobster pot 20 vs 70 |
| scimitars (about half the shop price) | iron and steel pickaxes (140 vs 209; 500 vs 576) |
| bows, arrows, runes, staves (shops cost up to about 2× as much) | hammer 1 vs 13; bread 12 vs 25 |
| mithril to rune pickaxes; all fish and all armour (the GE only) | feathers and bait: about equal |

**Walking times from the Lumbridge spawn** (sim estimates):

| Destination | Ticks from spawn | Ticks from the GE |
|---|---|---|
| GE | 223 | — |
| Bob's | 23 | 246 |
| Lumbridge general store | 14 | 213 |
| Varrock shops (Lowe's, Aubury's, Zaff's) | 150–176 | 47–77 |
| Gerrant's (Port Sarim) | 191 | 227 |
| Nurmof's (Dwarven Mine) | 216 | 156 |

So the trade-off is real near home: Bob's iron axe costs twice the GE price but is a tenth of the walk.

## 2. Actions (updated for Caleb's decisions)

**Ids** follow the existing per-item style:
- `buy_ge_<item>`: buy at the GE.
- `buy_shop_<item>`: buy at the one shop listed for that item.

| Group | Items | GE | Shop | Lot |
|---|---|---|---|---|
| Axes | iron, steel, mithril, adamant, rune | all | Bob's (Lumbridge): iron, steel | 1 |
| Pickaxes | iron, steel, mithril, adamant, rune | all | Nurmof's (Dwarven Mine): all | 1 |
| Fishing | fishing rod, fly rod, harpoon, lobster pot; bait; feathers | all | Gerrant's (Port Sarim): all | 1; 200 bait or feathers |
| Hammer | hammer (smithing needs one, and the starter kit has none) | yes | Lumbridge general store | 1 |
| Scimitars | iron, steel, mithril, adamant, rune | all | Zeke's (Al Kharid): iron, steel, mithril | 1 |
| Armour pieces (Q5) | iron, steel, mithril, adamant, rune: full helm, platebody, platelegs, kiteshield | all 20 | none (decided: no piecemeal armour shops) | 1 |
| Bows | oak, willow, maple shortbow | all | Lowe's (Varrock): all | 1 |
| Arrows | bronze, iron, steel, mithril, adamant | all | Lowe's: all | 100 |
| Runes | air, water, earth, fire, mind, chaos, death, nature | all | Aubury's (Varrock): all but nature | 100 |
| Staves | staff of air, water, earth, fire | all | Zaff's (Varrock): all | 1 |
| Food | open (Q6, §6) | 4 tiers proposed | Wydin's (Port Sarim): bread | §7 |
| Processing inputs (Q8) | raw trout, lobster, swordfish; oak, willow, maple, yew logs; iron, steel, mithril bars | all 10 | none | §7 |

**Count:** 66 GE actions (20 of them armour pieces, 4 food tiers), 37 shop actions (Q7: all kept) and 10
processing-input actions: **113 buy actions**. On top of those:
- 3 gear-withdraw actions (Q3a)
- the food withdrawals (§6)
- whatever the gear mechanism adds (Q3b, §5)

**Every bought item joins the vocabulary V**, so the observation shows it and its sell, alch and drop actions exist.
The list now has 77 items; the raw fish, logs and bars overlap with what gathering produces. V grows past the
catalog's estimate of 60 either way; its draft is separate.

## 3. Mechanics

- **Payment (Q1):**
  - Each buy is **as many as the coins allow, up to the lot**.
  - Coins in the inventory pay first. If they're short, the walk includes a bank stop to withdraw the rest. The GE
    has bankers beside it, so that costs only banking time; for a shop it's a detour through the nearest bank.
- **Where purchases land (Q2):**
  - **Shops:** in the inventory, as items, limited to the free slots.
  - **GE:** as banknotes in the inventory (one slot), unless it's a single item, which arrives as the item. Stackables
    (arrows, runes, bait, feathers) have no banknote and arrive as the stack.
  - Banknoted processing inputs already work: `bank_deposit` banks them as items, and `bank_withdraw_for_<activity>`
    takes them out. Banknoted food has no way out yet (§6).
- **Gear:** bought gear lands in the inventory (a single item, so unnoted). Banking still deposits unworn gear, and
  `bank_withdraw_gear_<class>` takes the best gear for a combat class back out (Q3a). When gear goes on or comes off
  is open (Q3b, §5).
- **Masks (Q4):** a buy action is open only when all of these hold:
  - **Affordable:** at least one unit with the coins in the inventory and bank.
  - **Usable now:**
    - gear and weapons meet their wear requirements, including quest locks
    - tools meet the level to use them (for example Woodcutting 41 for a rune axe)
    - arrows meet the Ranged level to wield them
  - **An upgrade** (gear, tools, bows and weapons only): better than anything held for that role, whether worn, in
    the inventory or in the bank. A staff is open unless that staff is already held.
  - **Room:** a free inventory slot, unless the item stacks onto one already held.
  - **Shops only:** in stock.
- **Armour as pieces (Q5):** the rune full helm, platelegs and kiteshield can be bought as soon as their Defence
  level allows; only the rune platebody waits for Dragon Slayer.
- **Timing:**
  - GE buys reuse the selling constants: the walk, plus 8 ticks for the offer and collection.
  - Shop buys take the walk plus 3 ticks.
  - Both get calibrated on the server.
- **Shop stock is tracked within an episode (Q9):** it falls as the agent buys and restocks at 1 unit per 100
  ticks, as on the server. Selling to general stores switches to the same stock, replacing the current agent choice
  that every sale starts at normal stock.

## 4. Caleb's decisions (2026-10-29)

| | Question | Decision |
|---|---|---|
| Q1 | How much one buy gets | As recommended: as many as the coins allow, up to a fixed lot |
| Q2 | Where purchases land | Shops: the inventory, as items. GE: banknotes, unless it's a single item |
| Q3a | What a deposit keeps | Option (b): deposits are unchanged, and 3 `bank_withdraw_gear_<class>` actions take a class's gear out |
| Q3b | When gear goes on | Gear goes on when it suits the task at hand; for example, no metal armour for tasks with a lot of running, since it drains run energy. The mechanism is open (§5) |
| Q4 | Mask buys that aren't upgrades? | Yes |
| Q5 | Armour as sets or pieces? | Pieces. With sets, rune armour would be locked until Dragon Slayer, though only its platebody needs it |
| Q6 | Food | Four GE tiers: mackerel, tuna, monkfish, shark; plus bread at Wydin's. How GE food comes out of the bank is open (§6) |
| Q7 | Keep shops that never beat the GE on price? | Keep them all |
| Q8 | Actions that buy processing inputs? | Yes |
| Q9 | Track shop stock within an episode? | Yes |
| Lots | Banknoted GE buys | 100 for food, 1,000 for processing inputs |
| Server | GE purchasing | Make it act normally: done on the fork (§9), uncommitted |

## 5. Q3: gear the character isn't wearing

**Background (2026-10-29, checked in the simulator):**
- `bank_deposit` banks unworn gear, and until now no action took gear back out.
- So the starter kit's first deposit loses the bow (after a melee fight) or the sword and shield (after a ranged
  fight).

**Decided (3a, option b):**
- Deposits stay as they are.
- `bank_withdraw_gear_<class>` (melee, ranged, magic) walks to the nearest bank and takes out the best gear for that
  class that the character can wear and has room for.
- Fights still put on the best gear in the inventory for their class (`wield_best`), so a class switch is a withdraw
  and then a fight.

**Decided as a principle (3b):** gear goes on when it suits the task. Caleb's example: no metal armour for tasks with
a lot of running, since it drains run energy.

**What the server does with weight and run energy** (`WalkingQueue`, `Settings.updateWeight`):
- **Drain:** each running tick drains 0.55 × (1 + kg / 100) percent energy. Running covers 2 tiles a tick; walking
  covers 1.
- **Restore:** every tick spent not running (walking, standing, skilling) restores 0.6 × 100 / (175 − Agility)
  percent. That's 0.34 a tick at Agility 1, so empty to full takes about 290 ticks.
- **Weight:** worn items, plus **one of each inventory slot's item**. A stack counts once.

**Full plate weighs about 27 kg in every tier** (helm, body, legs, kiteshield; adamant 29.5, mithril 23). So:
- Plate makes running drain 27% faster.
- **From full energy:** a character runs about 360 tiles without armour and about 290 in plate. Most trips in the
  simulator are shorter; Lumbridge to the GE is about 335 tiles.
- **Over long distances:** the steady pace at Agility 1 is about 1.38 tiles a tick without armour and 1.33 in plate,
  about 4% slower.
- **Loads weigh more than armour:** a full inventory of iron ore is about 63 kg (28 × 2.25), and of logs about 56
  kg. So the biggest weight effect is on gathering trips to the bank.

**Two findings this raises:**
- **The simulator has no run energy or weight.** Travel uses one effective speed (1.5 tiles a tick, `rlscape.travel`).
  Gear therefore costs nothing outside combat, and Agility, a sim v1 skill whose main use is energy restore, would do
  nothing either.
- **The server character never runs.** A new character's run toggle is off, and no bridge command turns it on, so it
  walks at 1 tile a tick while the simulator assumes running. The ±20% gate would catch this in travel times. A person
  would turn run on.

**3b options (Caleb's call):**
- **(a) Recommended:** model run energy and weight in the simulator, and give the agent a way to bank worn gear.
  - **Simulator:** port the drain and restore formulas. Keep energy in the character state and the observation, and
    run while energy lasts, so travel time depends on weight, energy and Agility.
  - **New action:** `bank_deposit_worn` walks to a bank and banks the worn gear. Taking gear off into the inventory
    doesn't help, because the inventory's weight counts too.
  - **The agent decides:** with `bank_withdraw_gear_<class>`, it chooses when armour is worth carrying.
  - **Server:** a bridge command for the run button (a fork change, needing your go-ahead); ServerEnv turns run on as
    a person would.
  - **Honest caveat:** the server's penalty is mild (above), so the agent may rarely find banking armour worth a trip.
    The energy model is still needed for Agility, and to make travel match a running server character.
- **(b)** A rule: fights withdraw their class's gear on the way, and every other option banks it first. Simpler for
  the agent, but it hides bank trips inside options and takes the choice away.
- **(c)** No weight or energy: armour never costs anything outside combat, so 3b's example isn't reflected. Travel
  still needs fixing to match whichever speed the server character uses.
- **Timing:** either way, this is its own change after buying. Buying doesn't depend on it, because bought gear just
  lands in the inventory.

## 6. Q6: food tiers (decided: mackerel, tuna, monkfish, shark)

**What makes food better or worse:**
- **Price per HP healed.**
- **HP per inventory slot.** Food takes slots that loot could use, and a fight ends when the food runs out. More HP
  per slot means longer fights between bank trips.
- **Waste.** The sim eats at half the maximum HP, and healing stops at the maximum, so food that heals more than
  half the max wastes the rest. A character with 20 max HP eats at 10 and wastes half a shark. **The useful size
  grows with the Hitpoints level.**

**2009 GE prices for fish** (only trout, swordfish, herring and shrimps are beaten outright: cod heals the same as
trout for less, and monkfish heals more than swordfish for less):

| Fish | Heals | 2009 GE price | gp per HP | Heals fully once max HP is at least |
|---|---|---|---|---|
| Sardine | 4 | 5 | 1.2 | 8 |
| Mackerel | 6 | 10 | 1.7 | 12 |
| Cod | 7 | 23 | 3.3 | 14 |
| Salmon | 9 | 59 | 6.6 | 18 |
| Tuna | 10 | 79 | 7.9 | 20 |
| Lobster | 12 | 228 | 19.0 | 24 |
| Monkfish | 16 | 327 | 20.4 | 32 |
| Shark | 20 | 845 | 42.3 | 40 |
| *Trout (beaten by cod)* | 7 | 31 | 4.4 | 14 |
| *Swordfish (beaten by monkfish)* | 14 | 376 | 26.9 | 28 |

Bread heals 5 and costs 25 at the GE, or about 12 at Wydin's.

**The trade-off is steep.** At 40 max HP:
- an inventory of tuna heals 280 HP for about 2,200 gp
- an inventory of sharks heals 560 HP for about 23,700 gp
- so doubling the HP per trip costs about 10× the gold

A wealth-leaning agent and an XP-leaning agent should choose differently, which is the E4 question. That's the case
for offering tiers instead of one rule-picked food. My draft's tiers (trout, lobster, swordfish, shark) included two
beaten fish; corrected below.

**Which food actions:**
- **(a) Decided (Caleb, 2026-10-29):** 4 GE tiers, mackerel (6), tuna (10), monkfish (16) and shark (20), plus bread
  at Wydin's.
  - No fish heals as much as a tier for less per HP. Together they cover the fresh character's 10 max HP up to 40
    and beyond.
  - Lobster costs about the same per HP as monkfish but heals 4 less per slot.
- **(b)** One `buy_ge_food` that picks the fish that heals fully at the current max HP. One action, but the rule
  makes the gold-versus-slots choice for the agent.
- **(c)** More tiers (all eight above): finer control, four more actions.
- **A note on 2009 prices:** some gnome cooking was cheaper still (a veg ball heals 15 for 128 gp, under half
  monkfish's price per HP). Fish keep buying on the same items the agent can catch and cook, so I'd leave the
  others out.

**Getting GE food out of the bank** (a consequence of Q2; still open): GE food arrives as banknotes. A fight eats
only from the inventory, and no action takes food out of the bank.
- **(a) Recommended:** `bank_withdraw_<food>` for each GE tier (4 actions). Each fills the free slots, like
  `bank_withdraw_for_<activity>`. The agent chooses what to carry.
- **(b)** One `bank_withdraw_food` that takes the largest food that heals fully at the current max HP first.
- Either way, the first withdrawal right after a buy costs only banking time, since the GE has bankers beside it.

## 7. Follow-ups raised by the decisions

- **Lots for banknoted buys (decided):** 100 for food and 1,000 for processing inputs, each cut by what the coins
  allow. Bread from Wydin's still fills the free slots, since it lands as items.
- **The bridge's `ge_collect`** now collects banknotes for multi-item buys (done, §9).

## 8. Not proposed for now

- **Ranged and magic armour** (leather, studded, coif, wizard robes). Wielding chooses armour by defence for every
  combat class, so it would never wear them over plate. They need class-aware armour choice first, which is a
  separate change.
- **Shops behind quests, guild levels or members-only cities:**
  - the Magic Guild's store (Magic 66) and the Fishing Guild's shop (Fishing 68)
  - Lletya
  - Ali's runes (after Rogue Trader)
- **The three 150,000-stock shops,** which look like 2009Scape additions (already excluded in §8).
- **Buy limits:** the server has none.

## 9. Server side (later, needs a fork change)

- **GE buys** go through the existing bridge commands (`ge_offer` with `sell: false` at the index price, then
  `ge_collect`), the human path. Done on the fork (2026-10-29, Caleb's go-ahead; uncommitted):
  - `ge_collect` collects as Q2 decided: more than one of an item that has a banknote as banknotes (the GE's
    `COLLECT_NOTES_OP`); a single item, coins, runes or arrows as items; a banknote when a single item has no room.
  - **Bug fixed:** offers placed back to back could get the same slot, and the second replaced the first. A new
    offer reaches the character's records only when the GE worker thread writes it (`writeNew`), and until then its
    slot looked free. The bridge now remembers the slots it has handed out until the records show them.
  - A live test covers both (`test_human_player_live.py`).
- **Run toggle** (if 3b goes with option a): a bridge command for the run button, so the server character runs as a
  person would.
- **Shop buys** need a new bridge command that opens the shop and buys through `Shop.buy`, the human path.
- **Putting gear on** needs an equip command through the human equip path, if the bridge doesn't already have one.
  Fights on the server need it whatever Q3b decides. `bank_withdraw_gear_<class>` needs bank withdrawals through the
  human bank path.
- **The rest are fork changes,** so they wait for Caleb's go-ahead, like any server modification.
