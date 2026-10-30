# Scripted-Guide Baseline: Draft for Caleb's Review

> **Caleb's review (2026-10-30):**
> - Q1, the schedule: lowest skill first, as drafted.
> - Q2: a withdraw-to-sell action, built.
> - Q3, the scope: widen the guide to more skills, with thieving as an early money-maker. That needs the thieving
>   targets and stalls added to the sim first, which is decided and comes next.
> - Also decided: deposits keep only the kit of the task at hand (built; it ended the inventory clog), and skilling
>   is offered as XP/hr and gp/hr slots (to come).
>
> With the kit deposits, 10 seeds × 20 hours give the guide total level 306 [304, 307], total XP 211k and net worth
> 353k [302k, 407k] (`results/eval/guide-kits-20261030`). Random gives 190 levels and 10k. The tables below are from
> before the kit deposits.

**Status:** draft, 2026-10-30. Env contract decision 17 says Claude drafts the E1 scripted-guide baseline from
archived 2009 guides, cites them in `docs/resources.md`, and Caleb reviews it before E1 runs. The routine is built
(`rlscape/baselines/guide.py`, `ScriptedGuidePolicy`) so its numbers can inform the review. It's not in
`e1_baselines()` until Caleb signs off; the eval harness can run it as `scripted_guide`.

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
| [26] | Money making guide | 899155, 2009-01-30 | consulted only: its free-to-play part just links subpages whose January 2009 text isn't in the wiki's history |

Missing, as far as the history shows: a January 2009 Mining training page (it was created later), the money-making
subpages, and any beginner's guide that orders the skills. So **no 2009 source says how to split time between
skills**. That part of the routine is Claude's proposal (Q1).

## The routine

**From the guides,** mapped onto sim v0's actions:

| Skill | Guide's method by level | Sim action |
|---|---|---|
| Woodcutting [22] | normal trees 1–14; oaks 15–40; willows 41+ (not yews at 60: "logs come very slowly") | `wc_logs`, `wc_oak`, `wc_willow` |
| Mining [25] | iron from 15, "the best ore for experience"; clay or essence before 15 | copper and tin to 14, alternately (no clay or essence in sim v0); `mine_iron` from 15 |
| Fishing [23] | small net to 19; fly fishing from 20, the fastest method at every level | `fish_shrimp`; `fish_fly` once a fly rod and feathers are bought |
| Melee [24] | monsters by the trained stat's level: 1–15 goblins, cows, chickens, men …; 16–30 barbarians, Al-Kharid warriors, minotaurs …; 31–45 hill giants, hobgoblins, zombies …; and so on to 99 | the melee slot whose monster is on the band's list, otherwise the top XP slot |
| Gear [22][24][25] | the best axe and pickaxe the level allows; scimitars, as the fastest F2P weapon; the best armour tier the Defence level allows; collect cowhides and bones | GE buys of those items; the default `valuable` loot mode keeps cowhides and bones |
| Food [23] | cook trout and salmon for food | `cook_fish` while fewer than 10 pieces of food are held |

**Claude's choices, to review:**
- **Schedule (Q1):** train the lowest of Attack, Strength, Defence, Woodcutting, Mining and Fishing next, one option
  at a time.
- **Combat styles:** each stat is trained only with its own style (accurate, aggressive, defensive). If the danger
  filter allows no fight in that style, the turn passes to the next skill.
- **Upgrades:** bought in priority order when affordable: the skill's tool, the scimitar, then armour. That's the
  calibration characters' order (env contract §7).
- **A full inventory (Q2):**
  - Cook raw fish if under 10 pieces of food.
  - Sell produce on the GE only when what's carried pays for the next upgrade. Produce means vocabulary items that
    aren't gear, tools, food, ammunition or runes. The guides fund gear by selling cowhides and logs.
  - Otherwise bank.
- **Not in the routine:** Smithing, Firemaking, Thieving, ranged and magic. The guides cover them, but they'd make the
  draft longer without changing its character (Q3).

## Results (sim v0, uncalibrated; 10 seeds, 20 game-hours)

| At hour 20 (mean [95% CI]) | Total level | Total XP | Net worth |
|---|---|---|---|
| scripted guide (draft) | 233 [230, 236] | 152,435 [138,330, 167,742] | 23,202 [18,439, 28,102] |
| random | 192 [188, 196] | 76,290 [70,798, 81,013] | 9,182 [5,938, 12,583] |

From `results/eval/guide-draft-20261030`. For reference, the preliminary E1 run gave greedy XP 159 levels and 768k
XP, and greedy wealth 688k gp. That run was before the fight-mask fix (below), so its numbers are slightly stale.

What it does, on seed 0:
- Combat stats climb together to about 40.
- Woodcutting, Mining and Fishing reach 12–21, because each gathering option ends at a full inventory, while a
  fight lasts 15 minutes.
- Its gear stays at a steel scimitar with iron and steel armour.

Why the gear stays at steel: it banks its produce and never sells it again (Q2). That points to a gap in the action
set that affects agents too (below).

## Questions for Caleb

**Q1. The schedule.** No 2009 source orders the skills.
- **(a) Recommended:** lowest skill first, as drafted. It's simple, balanced, and stays faithful to each skill's
  guide.
- (b) Combat first to a target (say 30/30/30), then skilling. This is common advice, but not in the January 2009
  sources found.
- (c) Fixed time shares per skill.

**Q2. Selling banked produce.** *Decided (Caleb, 2026-10-30): add a withdraw-to-sell action.* Built as
`bank_withdraw_for_sale` (catalog §5), and the guide uses it to fund upgrades. The original question follows. The
catalog can sell only what's in the inventory. Nothing withdraws banked
produce to sell it: `bank_withdraw_for_<activity>` covers processing inputs only. Net worth doesn't need selling,
because banked items count at their value. Buying gear does need coins, though, so an agent (or this guide) that
banks its produce can't fund upgrades from it.
- **(a) Recommended:** add a `bank_withdraw_<item>` per vocabulary item, or one `bank_withdraw_for_sale` that takes
  out the most valuable produce. It's a catalog change.
- (b) Keep the catalog. Agents learn to sell from the inventory instead of banking, and the guide keeps its current
  rule.

**Q3. Scope of the routine.** Add Smithing, Firemaking, Thieving, ranged or magic from the 2009 guides, or keep the
six skills. Recommended: keep six for E1. The guide's job is a credible human plan, not coverage.

**Q4. Anything in the mapping to change?** For example, the melee guide's monster bands, or using fly fishing to 99
rather than lobsters at 40 (the guide says fly fishing is fastest for experience and to fish other things "only for
profit").

## Changes made alongside

The guide found two sim problems, both now fixed:
- **Fight slots were open when they couldn't start.** With HP at or below the retreat point and no food, every fight
  retreated before its first swing. A routine could loop on them (21,847 one-tick fights in 4 hours). The slots are
  now masked in that state.
- **The guide's own early drafts looped.** It bought and sold the same pickaxe, and deposited and withdrew the same
  armour. Fixed in the routine: it sells only produce, and withdraws gear only for a fight that can start. Tests
  check that an episode stays under 600 decisions in 6 hours.
