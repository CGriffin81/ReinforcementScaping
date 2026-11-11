# Agent Interaction

## Metadata

- Interaction ID: m002-wealth-neglect
- Timestamp CST: 2026-11-11 16:58:48 CST, the message's timestamp in the session transcript (UTC−06:00). It came in
  while OQ-75 to OQ-78 were being asked.
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: ANSWERED from E3's 13 finished runs. Nothing changed. Whether the gem trade below stays is for Caleb, with
  the sim change (OQ-75).
- Commit: on `tooling/analysis-data`, with `m002-analysis-data`.

## Full Prompt

> I also do not like that the agents are neglecting wealth so much. Did rejecting GP break points influence that
> issue, or is ignoring wealth a feature of the tests we have been running?

## Response Summary

**How much wealth E3's agents make depends on their weighting.** These are means of each finished run's last 200
training episodes (sampled actions, not the evaluation):

| Weighting (skill, wealth) | Runs finished | Total level | Net worth (gp) |
|---|---:|---:|---:|
| (1, 0) | 5 | 336 | 9,182 |
| (.75, .25) | 5 | 338 | 18,604 |
| (.5, .5) | 2 | 357 | 237,923 |
| (.25, .75) | 1 | 91 | 4,077,635 |

E1's baselines at hour 20 (evaluation, 30 seeds):
- scripted guide: 351 total level, 129,789 gp;
- greedy GP/hr: 40 total level, 1,891,142 gp;
- random: 214 total level, 14,190 gp.

**The (.25, .75) agent makes twice greedy GP/hr's wealth with a trade.** In its last full bin it spends:
- 57% of its game time buying uncut emeralds (item 1621) at the Gem Store;
- 20% selling them on the GE, whose frozen January 2009 price is 985 gp;
- 16% banking.

The Gem Store's stock stands for 87 worlds (OQ-57), and the frozen GE buyer takes what's offered at that price.

**At (.5, .5) the agents leave about half their own reward unclaimed.** Their skill-heavy play earns about 185 a
20-hour episode, by the env's reward at that weighting (u·r_skill + (1−u)·17.13·r_wealth). The gem trade's outcome
(58.4 levels' r_skill and 40.8 r_wealth) would earn about 379. So their neglect of wealth isn't what the reward asks
for. They haven't found the trade: a local optimum, which is RQ2's and RQ4's subject and what E4's exploration bonus
tests. At (.75, .25), skill play (about 233) does beat the trade (about 219). There, and at (1, 0), neglecting wealth
is what the weighting asks.

**The break points:** on 2026-10-30 Caleb kept the skill reward level-based, though some levels are break points
(m002-greedy-xp, m002-total-xp). That doesn't cause the neglect:
- The wealth term already rewards reaching a lucrative level, through the gp the level earns afterwards.
- What the level-based reward does is count every skill's level the same. So skill-weighted agents spread over
  cheap levels (Firemaking by chop-and-burn, for one) rather than climbing to a money break point such as 38 Thieving.
- E2's skill-only result at the raw (.5, .5) was a scale problem: a level outweighed 100,000 gp. The normalised units
  (OQ-67) fixed it, and E3's (.5, .5) does make wealth (238k gp, above the guide's 130k).

## Documentation Changes

- This record.

## Code Changes

- None.

## Infrastructure Changes

- None. E3's finished runs (episodes.parquet, decision logs) were only read.

## Decisions

- **Agent observations for Caleb:**
  - The neglect at (1, 0) and (.75, .25) is the weighting's.
  - At (.5, .5) it's the agents' failure to find the gem trade.
  - The gem trade's size comes from OQ-57's 87 worlds and the frozen GE buyer.
- **User decision:** pending (with OQ-75's reruns): keep the gem trade as it is, or look at the GE buyer and the Gem
  Store's numbers first.

## Validation

- **Runs:** E3's 13 finished runs (`run.json`), 2,000,896 decisions each.
- **Time shares** from `rlscape/eval/behaviour.py` on (.25, .75) seed 0 and (.5, .5) seed 0, their last full
  100,000-decision bin.
- **The rewards at (.5, .5)** recomputed from the table's r_skill and r_wealth means, with WEALTH_FACTOR 17.1348.

## Follow-Up

- **Caleb:** with the sim change (OQ-75), whether the gem trade stays.
- **Claude:** the restart plan once OQ-75's details are decided.
