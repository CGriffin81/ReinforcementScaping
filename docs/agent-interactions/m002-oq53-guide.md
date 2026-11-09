# Agent Interaction

## Metadata

- Interaction ID: m002-oq53-guide
- Timestamp CST: 2026-11-09 10:20:28 CST (the prompt). Later prompts: "Try again" 10:38:03, then two instructions sent
  while Claude was working, 11:18:52 and 11:28:42 CST. From the session transcript's timestamps (UTC−06:00).
- Agent: Claude Code (desktop app, Code tab)
- Model: Claude Opus 5.5 (`claude-opus-5-5`)
- Status: PARTIAL (the extension built, with Caleb's instructions; OQ-58 and OQ-59 open, and two guide tests failing
  until they're answered; the draft's fifth revision not yet written)
- Commit: None (uncommitted; the fork's changes too)

## Full Prompt

> OQ 53 - Extend the guide.

Claude asked how, in four questions. Caleb answered three:

> Herblore: "Give Druidic's 250 XP (Recommended)". Schedule: "All join lowest-first (Recommended)". Crafting 1-9:
> "Cowhides from cows (Recommended)". Essence: "Is the price for rune essence 44 gp or is that for pure essence? Air
> runes can be crafted with either."

> Try again

Claude answered (rune essence is 44 gp, pure essence 137) and asked again. Caleb chose "After affordable upgrades
(Recommended)". Then, while Claude was building:

> Add wool buying and spinning to early crafting.

> Change behavior such that half of loots are sold and half are preserved for processing. Similarly, half of gp
> should be preserved for training skills that are net negative on gp, when making upgrade decisions.

After Claude's report on OQ-58 and OQ-59 (11:42:28 CST):

> Add cow killing as a gathering method for crafting supplies. It will use the highest combat style so as to have
> faster kills. Bury all normal bones gathered.

While Claude was building it (11:54:05 CST):

> Is wool -> ball of wool gp positive?

## Response Summary

- **Later, the cow path:**
  - `kill_cows` is built as Crafting's gathering path. It uses the plan with the fastest kills whose ammunition lasts a
    load, keeps hides and normal bones, and buries the bones as the inventory fills.
  - The guide takes it below Crafting 10.
  - Prayer rises to 18–25, but total level falls to 240–314: the guide spends 37% of seed 0 at cows.
- **The answer on wool:** no. A spin loses 112 gp (123 to 11) for 2.5 XP.

- **Finished the speed checks first:** 43 of 43 (`m002-speed-checks`).
- **Read the January 2009 wiki pages by revision** ([43] to [48]).
- **Found that no policy could train Herblore**, which led to OQ-56 (Druidic Ritual's XP), built on both backends.
- **Built the extension** in `rlscape/baselines/guide.py`. The four skills join the lowest-first schedule:
  - **Agility:** the Gnome course to 51, then the Wilderness course.
  - **Crafting:**
    - gems cut when drops bring them;
    - hard leather bodies from 28;
    - flax picked and spun from 10;
    - below 10, wool bought and spun (Caleb), and soft leather from cows' hides (cows fought from whichever combat
      slot holds them).
  - **Herblore:** the best potion the level allows, with its inputs bought.
  - **Runecrafting:** air runes, then earth from 9, at the ruins only, with the talisman and rune essence bought.
- **Caleb's two economy rules:**
  - upgrades take at most half the coins;
  - inputs used up are bought whenever due;
  - an item's loot is sold while under half of it has been.

  Whole-stack trades make the halves approximate.
- **Found and fixed:**
  - **The sim:** `abyss_rc_<rune>` was open when the hitpoints and food couldn't cover the crossing, so each pick did
    nothing. Now it's masked.
  - **The guide:** it sold its talisman (now kept), and it fell back to the Abyss (now ruins only).
- **Found: the signed-off guide's stints stall on Prayer** (about 414 of 470 decisions). Built a fix behind a flag
  (OQ-58: pass the stint on). It's measured better on 4 seeds, and the default stays as signed off.
- **Found: the three skills that buy their inputs barely train.** The guide holds 10 to 250 coins, and its inputs are
  dear. OQ-59 covers it, and two guide tests fail on it.

## Documentation Changes

- `docs/decision-log.md`:
  - "Decided: OQ-56 …" and "Decided: OQ-53 …";
  - "Found and fixed: abyss_rc_<rune> was open …";
  - "Decided (Caleb): the guide's early Crafting buys wool; half the loot …".
- `docs/open-questions-log.md`: OQ-53 removed; OQ-58 and OQ-59 added.
- `docs/env-contract.md`: v1.39 (the start).
- `CLAUDE.md`: the quest exception, and the spawn's Herblore XP.
- `docs/resources.md`: [43] to [49].
- This record.

## Code Changes

- `rlscape/sim/state.py`: `DRUIDIC_RITUAL_XP`.
- `server/Server/src/main/content/rl/RLCommands.kt` (the fork): the spawn's 250 Herblore XP.
- `rlscape/sim/runecrafting.py`: `AbyssRunecraft._can_cover`, in `available`.
- `rlscape/baselines/guide.py`:
  - the four skills' tables and branches, the tool chains and the consumables;
  - `units`, `upgrade_budget`, `kept_for_skills`, `_for_sale`, `_banked_for_sale`, `_count_sale`;
  - the plan yielding each option's skill, and `pass_stints`.
- **The cow path:**
  - `rlscape/sim/cows.py` (new): `KillCows`, `cow_entries`, `LOOT`;
  - `rlscape/sim/skilling.py`: registered among Crafting's paths and in `path_rate`;
  - the guide's `_cow_fights` replaced by the path.
- **Tests:**
  - `tests/test_sim.py`, `tests/test_bridge_live.py`: the start;
  - `tests/test_sim_abyss.py`: the crossing's mask;
  - `tests/test_sim_cows.py` (new, 3);
  - `tests/test_sim_gathering.py` and `tests/test_sim_skilling.py`: the counts (Crafting's 40 paths, the open paths and
    slots).
- **Docs:** env contract v1.42, option catalog §2 (the cow path), and the decision log's "Decided and built:
  kill_cows …".

## Infrastructure Changes

- **The fork rebuilt.** Instance 7 ran the live spawn test, then was stopped by PID.
- **The wiki** was read through its API in the built-in browser.

## Decisions

- **User decisions (Caleb):**
  - OQ-56 (a);
  - OQ-53 (a), with the schedule, the cowhides and, at first, essence after affordable upgrades;
  - wool buying and spinning;
  - half the loot sold, and half the coins kept from upgrades. This replaced "after affordable upgrades".
- **Agent choices (reversible, for Caleb's review):**
  - **Methods where the 2009 pages name one the sim lacks:**
    - Agility: the Gnome course stretches over Werewolf Skullball;
    - Runecrafting: earth runes past 30;
    - Crafting: flax from 10, with hard leather and gems only from what's held.
  - **Used-up inputs:** the essence rule applied to every input used up.
  - **What's loot:** hides, leathers, uncut gems and herbs, half sold. What it buys is never sold.
  - **Runecrafting** without the top-slot fallback.
  - **Agent recommendations:** OQ-58 (a), OQ-59 (a).

## Validation

- **The suite without the server,** the two guide balance tests left out: 421 passed, 75 skipped (with the cow
  path). Those two fail: OQ-59.
- **With the cow path** (4 seeds, OQ-58 both ways): total level 240–314, net worth 22k–68k, Prayer 18–25, Crafting
  5–9. At seed 0, 44,585 ticks in 42 cow runs.
- **Guide episodes** (scratch scripts), 4 seeds × 20 hours, OQ-58 both ways:
  - (a): total level 350–366, net worth 116k–173k;
  - (b): 336–341 and 107k–122k.
- **The Abyss masking test** failed first, then passed.

## Follow-Up

- **Caleb:** OQ-58 and OQ-59, before E1; confirm v1.38.
- **Claude:** once they're answered:
  - set the guide's default;
  - update `tests/test_guide.py`;
  - write `docs/scripted-guide-draft.md`'s fifth revision with results on 30 seeds;
  - then the freeze, the mask speed-up and `train.py`.
