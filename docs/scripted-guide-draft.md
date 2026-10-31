# Scripted-Guide Baseline: Draft for Caleb's Review

> **Reviewed by Caleb (2026-10-31):** "Apply both recommended actions": Q5 (a), this 13-skill guide is E1's
> scripted-guide baseline (now in `e1_baselines()`); Q6, the four sim fixes stay.

**Status:** second draft, 2026-10-30, widened to every skill sim v0 trains (Caleb: "Widen the guide", "Go after
lowest skill for schedule", "include more skills", thieving as an early money-maker). Env contract decision 17 says
Claude drafts the E1 scripted-guide baseline from archived 2009 guides, cites them in `docs/resources.md`, and Caleb
reviews it before E1 runs. The routine is `rlscape/baselines/guide.py` (`ScriptedGuidePolicy`), in
`e1_baselines()` since Caleb's review; the eval harness runs it as `scripted_guide`.

> **Caleb's review of the first draft (2026-10-30):** Q1, the schedule: lowest skill first. Q2: a withdraw-to-sell
> action (built). Q3, the scope: widen the guide to more skills, with thieving as an early money-maker (this draft).
> Also decided then: deposits keep the task's kit (built), and skilling is offered as XP/hr and gp/hr slots (to
> come).

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

No 2009 source says how to split time between skills; Caleb chose lowest first.

## The routine

**Schedule (Caleb):** the lowest of the 13 skills sim v0 trains directly (all but Hitpoints, which rises with
combat) is trained next, one option at a time. A skill that can't be trained right now (no bones, no runes, nothing
to smith) passes the turn to the next lowest.

| Skill | Guide's method by level | Sim action |
|---|---|---|
| Woodcutting [22] | normal trees 1–14; oaks 15–40; willows 41+ | `wc_logs`, `wc_oak`, `wc_willow` |
| Mining [25] | copper and tin before 15; iron from 15 | `mine_copper`, `mine_tin` alternately; `mine_iron` |
| Fishing [23] | small net to 19; fly fishing from 20 | `fish_shrimp`; `fish_fly` once a fly rod and feathers are bought |
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

## Questions for Caleb

**Q5. Is the 13-skill lowest-first guide the E1 baseline you want?** *Decided (Caleb, 2026-10-31): (a).* It does what was asked: every skill trained,
lowest first, by the 2009 guides. The cost is XP and wealth, so E1's agents will beat it easily on both.
- **(a) Recommended:** keep it. It's the specified plan, and its balance is what makes it a fair "new player"
  reference on total level.
- (b) Lowest first, but over fewer skills (for example the first draft's six plus thieving).
- (c) Report both in E1: the 13-skill guide and the six-skill one.

**Q6. The four sim fixes above** *Decided (Caleb, 2026-10-31): keep them.* change the agents' options too (magic's armour, the magic withdrawal, the
processing withdrawals, the buy mask). None changes the action count. Recommended: keep them.
