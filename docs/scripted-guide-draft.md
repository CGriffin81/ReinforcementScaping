# Scripted-Guide Baseline

> **Fifth revision (2026-11-09), signed off by Caleb the same day** as E1's scripted-guide baseline. Sim v1's four skills join the schedule (Caleb,
> OQ-53), each by its January 2009 page ([43]–[48]), with the rules Caleb set while it was built:
> - **Agility** ([45]): the Gnome Stronghold course to 51, the Wilderness course from 52. The page's Werewolf
>   Skullball (25–52) and Ape Atoll (80+) aren't in the sim, so the courses beside them stretch.
> - **Crafting** ([43], [44]):
>   - below 10, soft leather (the best item the level allows) from cows' hides, tanned at Ellis. The hides come from
>     `kill_cows`, a new Crafting gathering path in the sim. It fights cows in the style that kills fastest and buries
>     their bones (Caleb).
>   - from 10, flax picked by Seers' Village and spun into bowstrings;
>   - hard leather bodies from 28 while hides are held;
>   - gems cut only as drops bring them ("buying uncut gems for cutting is not worthwhile").
>
>   The page's wool (spun to 8) was tried and taken out (Caleb): a spin loses 112 gp.
> - **Herblore** ([46]): from 3 (Druidic Ritual's XP, now in the start: Caleb, OQ-56), the best potion the level
>   allows, its herb, vial and secondary bought.
> - **Runecrafting** ([47], [48]): air runes to 9, then earth runes, at the ruins, the talisman and rune essence
>   bought.
> - **The schedule** (OQ-58 (a)): a stint whose skill can't be trained passes to the skill trained instead. Before,
>   Prayer's stint held about 414 of some 470 decisions once bones ran out, in the signed-off guide too.
> - **The coins:**
>   - an upgrade takes at most half of them;
>   - the inputs of the skills that lose gp are bought whenever due;
>   - when the stint's inputs cost more than the coins, flax picked by Seers' Village pays for them (OQ-59 (b)). It's
>     banked until it covers them and the GE trip's two fares (the sim's way to the field is a 1,000 gp charter),
>     sold in one trip, and the inputs are bought before any upgrade: the money-maker carries through the stint.
> - **Loot:** half of each item obtained is sold and half kept for processing, a whole stack at a time. What it buys
>   to use is never sold.
> - **Banking:** before gathering or a fight, it deposits if that banks 5 or more slots the coming task doesn't use,
>   and never deposits straight after a withdrawal while anything else can be done.
>
> Results below: on 30 seeds, total level 351 [344, 357] and net worth 131k [125k, 136k], every skill trained. The
> decision log's entries of 2026-11-09 have each choice and the loops found on the way.

> **Fourth revision (2026-10-31):** Fletching, brought forward into sim v0 (Caleb), is the guide's 14th skill,
> trained by the Fletching article's methods ([40]; January 2009 had no Fletching training page): arrow shafts from
> normal logs to 25, then oak, willow and maple bows (u), and from 70 yew longbows, strung (the only bows here worth
> more strung than their parts). It cuts the logs where it chops them while its woodcutting allows, otherwise works
> banked logs at a bank. Its knife is Lumbridge Castle's (Caleb: "very convenient for a fresh starting
> character"). Results below.

> **Third revision (2026-10-31), from Caleb's review the same day:** the members' guides where January 2009 had
> them (melee [34], ranged [35], woodcutting [36], fishing [37], cooking [38], firemaking [39]); the schedule trains
> the lowest skill in a stint to the next multiple of 5 ("Minimum stint where the goal levels are multiples of
> 5"); gathering goes through the new skilling slots (option catalog §2), taking the slot that holds the guide's
> method. Results below. The rest of this page describes the second draft, except where these change it.

> **Signed off by Caleb (2026-10-31)** as E1's scripted-guide baseline (now in `e1_baselines()`), with the four sim
> fixes below kept. The questions and answers behind each revision are in `docs/decision-log.md`.

**Status:** second draft, 2026-10-30, widened to every skill sim v0 trains (Caleb: "Widen the guide", "Go after
lowest skill for schedule", "include more skills", thieving as an early money-maker). Env contract decision 17 says
Claude drafts the E1 scripted-guide baseline from archived 2009 guides, cites them in `docs/resources.md`, and Caleb
reviews it before E1 runs. The routine is `rlscape/baselines/guide.py` (`ScriptedGuidePolicy`), in
`e1_baselines()` since Caleb's review; the eval harness runs it as `scripted_guide`.

## Sources

The guides are the RuneScape Wiki's training pages exactly as they stood at the end of January 2009, the month the
GE prices are frozen at. The wiki kept its full Wikia-era history, so each revision has a stable link (licence CC
BY-NC-SA 3.0; cited and paraphrased here, not copied):

| Ref | Page | Revision | Used for |
|---|---|---|---|
| [22] | Free-to-play Woodcutting training | 890919, 2009-01-29 | trees by level, axes |
| [23] | Free-to-play Fishing training | 886593, 2009-01-27 | methods by level, gear, cooking for food |
| [24] | Free-to-play melee training | 898754, 2009-01-30 | monsters by level band, weapon and armour tiers, drops |
| [25] | Mining (the skill article) | 899733, 2009-01-31 | rocks by level, pickaxes |
| [26] | Money making guide | 899155, 2009-01-30 | consulted only: its January 2009 subpages aren't in the history |
| [27] | Thieving training | 900070, 2009-01-31 | targets and stalls by level |
| [28] | Free-to-play Cooking training | 885447, 2009-01-26 | cook the fish you catch |
| [29] | Free-to-play Smithing training | 881317, 2009-01-25 | bronze to 14, iron from 15, mine your own ores |
| [30] | Free-to-play Prayer training | 888578, 2009-01-28 | bury the bones kills drop |
| [31] | Free-to-play Ranged training | 880633, 2009-01-25 | monsters by Ranged level, shortbows, iron arrows |
| [32] | Firemaking (the skill article) | 892441, 2009-01-29 | logs by level (no training page yet) |
| [33] | Magic (the skill article) | 900388, 2009-01-31 | strike spells, buying runes (no training page yet) |
| [34] | Pay-to-play melee training | 900265, 2009-01-31 | members' monsters by level band (third revision) |
| [35] | Pay-to-play Ranged training | 895507, 2009-01-30 | members' monsters by Ranged level (third revision) |
| [36] | Pay-to-play Woodcutting training | 892489, 2009-01-29 | oaks 15–29, willows 30+ (third revision) |
| [37] | Pay-to-play Fishing training | 876863, 2009-01-24 | small net, fly fishing from 20 (third revision) |
| [38] | Pay-to-play Cooking training | 892859, 2009-01-29 | cook the catch (third revision) |
| [39] | Pay-to-play Firemaking training | 881333, 2009-01-25 | logs by level (third revision) |
| [43] | Pay-to-play Crafting training | 883396, 2009-01-26 | wool to 8, hard leather from 28, gems (fifth) |
| [44] | Flax | 889516, 2009-01-28 | flax picked by Seers' Village and spun from 10 (fifth) |
| [45] | Agility training | 895549, 2009-01-30 | courses by level (fifth) |
| [46] | Herblore (the skill article) | 875720, 2009-01-23 | potions by level; no training page yet (fifth) |
| [47] | Free-to-play Runecrafting training | 888316, 2009-01-28 | air runes to 9, earth from 9 (fifth) |
| [48] | Pay-to-play Runecrafting training | 832614, 2009-01-08 | consulted: its methods aren't in the sim |

No 2009 source says how to split time between skills; Caleb chose lowest first.

## The routine

**Schedule (Caleb):** the lowest of the 13 skills sim v0 trains directly (all but Hitpoints, which rises with
combat) is trained next, one option at a time. A skill that can't be trained right now (no bones, no runes, nothing
to smith) passes the turn to the next lowest.

| Skill | Guide's method by level | Sim action |
|---|---|---|
| Woodcutting [22] | normal trees 1–14; oaks 15–40; willows 41+ | `wc_logs`, `wc_oak`, `wc_willow` |
| Mining [25] | copper and tin before 15; iron from 15 | `mine_copper`, `mine_tin` alternately; `mine_iron` |
| Fishing [23] | small net to 19; fly fishing from 20 | `fish_shrimp_swamp` while Draynor's Dark wizards would attack (combat level 14 or less; Caleb, 2026-11-01), then `fish_shrimp`; `fish_fly` once a fly rod and feathers are bought |
| Melee [24] | monsters by the trained stat's level band; scimitars; the best armour tier the Defence level allows | each stat in its own style, on the melee slot whose monster is in the band, otherwise the top XP slot |
| Ranged [31] | monks, goblins, chickens to 19; wizards, minotaurs, barbarians from 20; flesh crawlers, moss giants from 30; lesser demons, ankou late; the best shortbow; iron arrows | the ranged slot whose monster is in the band, otherwise the top XP slot; bows and arrows bought |
| Magic [33] | earth strike at 9, fire strike at 13, …; buy the runes | the top magic XP slot, with runes bought for the best strike or bolt the level allows. The article's curse (19), telekinetic grab (33), crumble undead (39) and high alchemy (55) aren't sim v0 options |
| Prayer [30] | bury the bones kills drop | `bury_bones` (bones are never sold) |
| Firemaking [32] | the best logs the level allows | `burn_logs` on what woodcutting brings in |
| Cooking [28] | cook the fish you catch (shrimp, then trout and salmon) | `cook_fish` on what fishing brings in |
| Smithing [29] | smelt and smith bronze to 14; iron from 15; mine your own ores | `smelt_*`, `smith_*`; with nothing to smith, it mines the ore |
| Thieving [27] | men 1–4; the baker's stall 5–19; the silk stall 20–29; The Feud 30–37; the fur stall 37–38; master farmers 38–45; blackjacking bandits 45–55; Knights of Ardougne 55–65; blackjacking Menaphite thugs 65–91 | men to 4; the baker's stall 5–19; the silk stall 20–34; the fur stall 35–37; master farmers 38–54; knights 55–64; pickpocketing the thugs from 65. The Feud and blackjacking aren't in the sim, so neighbouring methods stretch over those levels |

**Claude's choices, to review:**
- **Upgrades:** bought on the GE in the calibration characters' order (env contract §7): the skill's own (tool;
  ranged's bow and arrows; magic's scarcest rune; smithing's hammer), then the scimitar, then armour, each the best
  affordable tier. A skill's own buys are also tried just before it is, so a skill further down isn't left without
  them while the lowest can't be trained.
- **Processing uses the guide's own gathering, not the GE,** as the guides do (cook what you fish, and so on). A GE
  buy takes as many as the coins allow, up to 1,000, which would spend everything on one input.
- **Funding:** an unaffordable upgrade is paid for by selling produce carried or banked (`bank_withdraw_for_sale`),
  at GE prices. Bones are kept for Prayer. Items outside V (the baker's stall's cakes) stay banked, since
  `sell_ge_misc` sells every misc item carried, the starter shortbow included, and Ranged can't restart without it
  (the GE's first bow needs level 5).
- **A full inventory:** cook raw fish while under 10 pieces of food, then use what's carried (burn, bury, smelt,
  smith), then bank.
- **Thieving's food:** whatever food is carried. A food withdrawal fills every free slot, which leaves no room for
  the loot, so thieving stops when HP runs low and the schedule moves on.

## Results (sim v0, uncalibrated; 10 seeds, 20 game-hours)

**Fifth revision** (sim v1, calibrated; 30 seeds, the E1 seeds of OQ-54; `results/eval/guide-v5b-20261109` for the
guide, `results/eval/guide-v5-20261109` for the others, the same sim):

| At hour 20 (mean [95% CI]) | Total level | Total XP | Net worth |
|---|---|---|---|
| scripted guide | 351 [344, 357] | 98,285 [95,467, 101,201] | 130,567 [125,400, 135,895] |
| random | 215 [207, 223] | 76,322 [70,940, 82,151] | 14,552 [10,461, 19,468] |
| greedy XP | 157 [157, 157] | 700,606 [698,093, 703,035] | 1,160 [1,133, 1,188] |
| greedy GP | 40 [36, 46] | 15,747 [1,639, 36,927] | 1,891,142 [1,766,299, 1,975,610] |

- **The guide:** every one of its 18 skills is trained. In 8 earlier seeds of the same version: Herblore 11–16,
  Runecrafting 8–16, Crafting 4–16, Agility 10–17, Prayer 10–22. At most 519 decisions an episode, no deaths. The
  signed-off 14-skill guide, on seeds 0 and 1 the same day: total level 335 and 339, net worth 112k and 123k.
- **Greedy GP** picks and banks flax all episode (about 99k gp an hour, OQ-52), and greedy XP chops and burns. The
  guide is the only baseline that trains broadly.

**Fourth revision** (with Fletching; `results/eval/guide-fletching-20261031`):

| At hour 20 (mean [95% CI]) | Total level | Total XP | Net worth |
|---|---|---|---|
| scripted guide | 312 [307, 316] | 94,137 [91,854, 96,342] | 107,825 [102,322, 113,002] |
| random | 235 [227, 243] | 101,804 [92,906, 110,677] | 8,398 [5,132, 12,023] |

Fletching nearly doubles the guide's net worth (58k before), all from arrow shafts: Fletching stays below 25, so the
guide never reaches bows. Seed 0 ends at Fletching 20 holding 13,205 arrow shafts (66k of its 106k net worth, at
5 gp each) and 400 headless arrows (3k).

**Third revision** (members' guides, stints, skilling slots; `results/eval/guide-slots-20261031`):

| At hour 20 (mean [95% CI]) | Total level | Total XP | Net worth |
|---|---|---|---|
| scripted guide | 306 [305, 308] | 89,527 [87,177, 92,061] | 57,704 [54,756, 61,008] |
| random | 236 [230, 243] | 108,293 [101,748, 115,381] | 9,797 [5,922, 13,988] |

The guide is about where the second draft was. Random gained most from the skilling slots (184 levels and 80k XP
before): every slot it can pick is now one of a skill's best paths, and the chop-and-burn paths give a lot of XP.

**Second draft:**

| At hour 20 (mean [95% CI]) | Total level | Total XP | Net worth |
|---|---|---|---|
| scripted guide, 13 skills (this draft) | 308 [302, 314] | 87,147 [83,191, 90,882] | 55,071 [52,198, 58,304] |
| the first draft's 6 skills, on today's sim | 303 | 204,849 | 329,604 |
| random | 184 [179, 188] | 79,735 [73,972, 86,673] | 12,952 [9,173, 17,032] |

From `results/eval/guide-wide-20261030`. The six-skill row is the same routine restricted to the first draft's
schedule (Attack, Strength, Defence, Woodcutting, Mining, Fishing), means only.

**What widening costs:** about the same total level, but 58% less XP and 83% less net worth. With 13 skills at the
bottom of the schedule, every skill stays low (most finish in the 20s), where every method is slow: the guide's
methods average 2–6k XP/h (thieving at the baker's stall 2.3k, fishing shrimp 2.5k, melee 5.9k). Money goes on
runes, arrows and a hammer, and the thieving that pays (master farmers, from 38) isn't reached. Seed 0 ends with
combat at 25–26, gathering at 23–24, cooking 28, smithing 22, ranged 16, magic 13, thieving 22 and prayer 9.

## Changes made alongside

Widening the guide found four sim problems that would trap an agent too. Each is fixed and tested:
- **Magic fights wore metal armour.** The fight gear rule puts on the best-defence armour, and an iron set's magic
  attack penalty (−65) left a low-level caster no target. Magic now takes off, and doesn't put on or withdraw,
  armour that lowers magic attack (`rlscape.sim.equipment.hinders`).
- **Banked runes never came back.** A deposit for another task banks runes, and `bank_withdraw_gear_magic` didn't
  take them; it now does, as the ranged withdrawal takes arrows.
- **Processing withdrawals took inputs the level can't use** (willow logs at Firemaking 5), filling the inventory
  with logs `burn_logs` wouldn't touch. They now take only what the level allows.
- **A buy could be open when its coins couldn't reach the inventory** (all in the bank, no free slot): each trip
  bought nothing. The buy mask now checks that the coins can be withdrawn.

Earlier, the first draft found two others: fight slots open when they couldn't start, and the guide's own buy/sell
and deposit/withdraw loops.
