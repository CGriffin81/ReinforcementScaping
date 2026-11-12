# Resources

The project's running reference list. [1]–[15] come from the proposal (`CS898BG_RL_Project_Proposal_2009Scape.pdf`,
§8) and keep its numbering, so the final report's bibliography can continue from them. Later additions
start at [16] and say how the project uses them. External code is only reused where its licence allows it,
and is credited where used.

## Papers (from the proposal)

1. Sutton, Precup & Singh (1999). Between MDPs and semi-MDPs: a framework for temporal abstraction in
   reinforcement learning. *Artificial Intelligence* 112(1–2). — the options / semi-MDP formulation.
2. Schulman et al. (2017). Proximal policy optimization algorithms. arXiv:1707.06347. — core agent.
3. Ng, Harada & Russell (1999). Policy invariance under reward transformations. *ICML*. — PBRS (E5).
4. Roijers, Vamplew, Whiteson & Dazeley (2013). A survey of multi-objective sequential decision-making.
   *JAIR* 48. — the Pareto framing (E4).
5. Hafner (2022). Benchmarking the spectrum of agent capabilities (Crafter). *ICLR*. arXiv:2109.06780.
6. Küttler et al. (2020). The NetHack Learning Environment. *NeurIPS*. arXiv:2006.13760.
7. Huang & Ontañón (2022). A closer look at invalid action masking in policy gradient algorithms. *FLAIRS*.
   arXiv:2006.14171.
8. Burda, Edwards, Storkey & Klimov (2019). Exploration by random network distillation. *ICLR*.
   arXiv:1810.12894. — E3.
9. Yang, Sun & Narasimhan (2019). A generalized algorithm for multi-objective RL and policy adaptation
   (Envelope Q-learning). *NeurIPS*. arXiv:1908.08342. — E4.
10. Hafner, Pasukonis, Ba & Lillicrap (2025). Mastering diverse control tasks through world models
    (DreamerV3). *Nature*. — stretch option B.
11. Pleines et al. (2025). Pokémon Red via reinforcement learning. arXiv:2502.19920.
12. Wang et al. (2023). Voyager: an open-ended embodied agent with large language models.
    arXiv:2305.16291. — stretch option A.

## Environments, code and data

13. Naton1. *osrs-pvp-reinforcement-learning*. https://github.com/Naton1/osrs-pvp-reinforcement-learning
    — the architecture pattern: Python trainer ↔ modified private server over a socket.
14. 2009Scape project. Server source (AGPLv3) and Singleplayer guide. https://gitlab.com/2009scape/2009scape ;
    https://2009scape.org/site/game_guide/singleplayer.html — **the environment.** Forked as
    https://github.com/CGriffin81/2009scape-rl (branch `rl`).
15. Raffin et al. (2021). Stable-Baselines3. *JMLR* 22(268). — with sb3-contrib MaskablePPO.

## Added during the project

16. **RuneScape Wiki / Weird Gloop exchange API.** https://api.weirdgloop.org/exchange/history/rs/sample?id=<item>
    — **Used (2026-10-05):** source of the historical January 2009 GE prices that freeze the GE and enter the
    net-worth valuation (`scripts/fetch_ge_history.py`, `data/ge_prices_2009.csv`).
17. **2009Scape, "About 2009Scape".** https://2009scape.org/site/game_guide/about2009scape.html — **Used:** the
    statement that 2009Scape targets build 530 "with content in and around January 1st, 2009", which sets the
    price window.
18. **Bittker, M. RuneBench** (runescape-bench). https://github.com/MaxBittker/runebench ;
    results at https://maxbittker.github.io/runebench/ — **Used as related work and a design reference.**
    - **What it is:** a benchmark of LLM coding agents playing LostCity 2004scape through rs-sdk [19] at 8×
      speed with a 25× XP multiplier. It has 16 single-skill XP tasks (15 / 30 min), scored on peak XP/min
      in any 15-second window, and gold-accumulation tasks from four starting saves (vanilla, smith + alch,
      fish, fletch + alch). Agents get a folder of wiki-derived strategy notes.
    - **For us:** the closest prior work on agents in RuneScape. It measures the same two objectives we do,
      skill and wealth, but with LLM agents and short tasks rather than RL over 20 game-hours. It's the
      natural reference point for the stretch LLM planner (E7, option A): give the planner game knowledge
      and a tool interface. Its fixed starting-condition gold tasks are a model for robustness checks of our
      wealth results.
    - **Limits:** a different game version and engine, sped-up XP, and LLM-specific scoring, so its numbers
      can't be compared with ours directly.
    - **Licence:** the README says MIT but the repo has no LICENSE file, so cite it and don't copy code.
19. **Bittker, M. rs-sdk.** https://github.com/MaxBittker/rs-sdk (MIT) — **Used as a design reference.**
    - **What it is:** a TypeScript automation SDK, agent documentation and an MCP `execute_code` tool for a
      modified fork of the LostCity 2004scape engine and client. Its server changes: faster XP curve,
      infinite run energy, no random events. It reaches the game through a browser or headless client and a
      gateway.
    - **For us:**
      - Its high-level actions observe their effects and return typed results with `success` / `reason`.
        That's the pattern for our server-side option executor and its `termination` reasons.
      - Its MCP tool interface is a template for the E7 LLM planner.
      - Its leaderboard metric, highest total level per lowest playtime, mirrors our skill objective.
      - It independently made the same environment choices we did for agents: no random events, and a
        configurable tick rate (`NODE_TICKRATE`, `::speed`).
    - **Not used as our environment:** it targets 2004-era content on a different engine, and its mechanics
      notes (`learnings/`) describe that version. Our formulas come from the 2009Scape source.
20. **LostCity.** https://github.com/LostCityRS/Server — the 2004scape engine that [18] and [19] build on.
    Cited only for context.
21. **Towers, M., Kwiatkowski, A., Terry, J., Balis, J. U., et al. (2024).** Gymnasium: A Standard Interface for
    Reinforcement Learning Environments. arXiv:2407.17032. https://github.com/Farama-Foundation/Gymnasium (MIT)
    — **Used:** `SimEnv` (`rlscape/envs/`) implements its `Env` API, version 1.4.0, as the env contract's
    interface (§2), so SB3 and sb3-contrib agents can drive it. Added 2026-10-30.
22. **RuneScape Wiki. "Free-to-play Woodcutting training",** revision 890919 (2009-01-29).
    https://runescape.wiki/w/Free-to-play_Woodcutting_training?oldid=890919 (CC BY-NC-SA 3.0) — **Used:** the
    scripted-guide baseline's woodcutting methods and axes (`docs/scripted-guide-draft.md`). Added 2026-10-30.
23. **RuneScape Wiki. "Free-to-play Fishing training",** revision 886593 (2009-01-27).
    https://runescape.wiki/w/Free-to-play_Fishing_training?oldid=886593 (CC BY-NC-SA 3.0) — **Used:** the
    scripted guide's fishing methods, gear and cooking for food. Added 2026-10-30.
24. **RuneScape Wiki. "Free-to-play melee training",** revision 898754 (2009-01-30).
    https://runescape.wiki/w/Free-to-play_melee_training?oldid=898754 (CC BY-NC-SA 3.0) — **Used:** the scripted
    guide's monsters by level band, weapon and armour tiers, and drops to collect. Added 2026-10-30.
25. **RuneScape Wiki. "Mining",** revision 899733 (2009-01-31).
    https://runescape.wiki/w/Mining?oldid=899733 (CC BY-NC-SA 3.0) — **Used:** the scripted guide's rocks by level
    and pickaxes. Added 2026-10-30.
26. **RuneScape Wiki. "Money making guide",** revision 899155 (2009-01-30).
    https://runescape.wiki/w/Money_making_guide?oldid=899155 (CC BY-NC-SA 3.0) — consulted for the scripted guide.
    Its free-to-play part only links subpages whose January 2009 text isn't in the wiki's history, so nothing is
    taken from it. Added 2026-10-30.
27. **RuneScape Wiki. "Thieving training",** revision 900070 (2009-01-31).
    https://runescape.wiki/w/Thieving_training?oldid=900070 (CC BY-NC-SA 3.0) — **Used:** the scripted guide's
    thieving methods by level (men, the baker's, silk and fur stalls, master farmers, Knights of Ardougne,
    Menaphite thugs). Added 2026-10-30.
28. **RuneScape Wiki. "Free-to-play Cooking training",** revision 885447 (2009-01-26).
    https://runescape.wiki/w/Free-to-play_Cooking_training?oldid=885447 (CC BY-NC-SA 3.0) — **Used:** the scripted
    guide's cooking (cook the fish fishing brings in). Added 2026-10-30.
29. **RuneScape Wiki. "Free-to-play Smithing training",** revision 881317 (2009-01-25).
    https://runescape.wiki/w/Free-to-play_Smithing_training?oldid=881317 (CC BY-NC-SA 3.0) — **Used:** the
    scripted guide's smithing (bronze to 14, iron from 15, mining the ores). Added 2026-10-30.
30. **RuneScape Wiki. "Free-to-play Prayer training",** revision 888578 (2009-01-28).
    https://runescape.wiki/w/Free-to-play_Prayer_training?oldid=888578 (CC BY-NC-SA 3.0) — **Used:** the scripted
    guide's prayer (bury the bones kills drop). Added 2026-10-30.
31. **RuneScape Wiki. "Free-to-play Ranged training",** revision 880633 (2009-01-25).
    https://runescape.wiki/w/Free-to-play_Ranged_training?oldid=880633 (CC BY-NC-SA 3.0) — **Used:** the scripted
    guide's ranged monsters by level, shortbows and iron arrows. Added 2026-10-30.
32. **RuneScape Wiki. "Firemaking",** revision 892441 (2009-01-29).
    https://runescape.wiki/w/Firemaking?oldid=892441 (CC BY-NC-SA 3.0) — **Used:** the scripted guide's firemaking
    (logs by level; no January 2009 training page exists). Added 2026-10-30.
33. **RuneScape Wiki. "Magic",** revision 900388 (2009-01-31).
    https://runescape.wiki/w/Magic?oldid=900388 (CC BY-NC-SA 3.0) — **Used:** the scripted guide's magic (strike
    spells, buying runes; no January 2009 training page exists). Added 2026-10-30.

34. **RuneScape Wiki. "Pay-to-play melee training",** revision 900265 (2009-01-31).
    https://runescape.wiki/w/Pay-to-play_melee_training?oldid=900265 (CC BY-NC-SA 3.0) — **Used:** the scripted
    guide's melee monsters by level band (members), replacing [24] there. Added 2026-10-31.
35. **RuneScape Wiki. "Pay-to-play Ranged training",** revision 895507 (2009-01-30).
    https://runescape.wiki/w/Pay-to-play_Ranged_training?oldid=895507 (CC BY-NC-SA 3.0) — **Used:** the scripted
    guide's ranged monsters by level band (members), replacing [31] there. Added 2026-10-31.
36. **RuneScape Wiki. "Pay-to-play Woodcutting training",** revision 892489 (2009-01-29).
    https://runescape.wiki/w/Pay-to-play_Woodcutting_training?oldid=892489 (CC BY-NC-SA 3.0) — **Used:** the
    scripted guide's trees by level (members), replacing [22] there. Added 2026-10-31.
37. **RuneScape Wiki. "Pay-to-play Fishing training",** revision 876863 (2009-01-24).
    https://runescape.wiki/w/Pay-to-play_Fishing_training?oldid=876863 (CC BY-NC-SA 3.0) — **Used:** the scripted
    guide's fishing methods (members), replacing [23] there. Added 2026-10-31.
38. **RuneScape Wiki. "Pay-to-play Cooking training",** revision 892859 (2009-01-29).
    https://runescape.wiki/w/Pay-to-play_Cooking_training?oldid=892859 (CC BY-NC-SA 3.0) — **Used:** the scripted
    guide's cooking (members), replacing [28] there. Added 2026-10-31.
39. **RuneScape Wiki. "Pay-to-play Firemaking training",** revision 881333 (2009-01-25).
    https://runescape.wiki/w/Pay-to-play_Firemaking_training?oldid=881333 (CC BY-NC-SA 3.0) — **Used:** the
    scripted guide's logs by level (members), replacing [32] there. Added 2026-10-31.
40. **RuneScape Wiki. "Fletching",** revision 882419 (2009-01-25).
    https://runescape.wiki/w/Fletching?oldid=882419 (CC BY-NC-SA 3.0) — consulted for the fletching proposal (no
    January 2009 fletching training page exists). Added 2026-10-31.

41. **Paszke, A., Gross, S., Massa, F., Lerer, A., et al. (2019).** PyTorch: An Imperative Style, High-Performance
    Deep Learning Library. *NeurIPS*. https://pytorch.org (BSD-3-Clause) — **Used:** version 2.14.1 with CUDA 13.0,
    under stable-baselines3 and sb3-contrib ([15]) for the PPO agents (`rlscape/agents/`). Added 2026-11-08.
42. **TensorBoard** (the TensorFlow authors). https://github.com/tensorflow/tensorboard (Apache-2.0) — **Used:**
    version 2.21, the training curves of the PPO runs. Added 2026-11-08.

43. **RuneScape Wiki. "Pay-to-play Crafting training",** revision 883396 (2009-01-26).
    https://runescape.wiki/w/Pay-to-play_Crafting_training?oldid=883396 (CC BY-NC-SA 3.0) — **Used:** the scripted
    guide's Crafting (OQ-53): wool to 8, hard leather bodies from 28 from cows' hides tanned at Ellis, gems cut from
    drops rather than bought. Added 2026-11-09.
44. **RuneScape Wiki. "Flax",** revision 889516 (2009-01-28). https://runescape.wiki/w/Flax?oldid=889516
    (CC BY-NC-SA 3.0) — **Used:** the scripted guide's Crafting from 10: flax picked by Seers' Village and spun into
    bowstrings at its wheel. Added 2026-11-09.
45. **RuneScape Wiki. "Agility training",** revision 895549 (2009-01-30).
    https://runescape.wiki/w/Agility_training?oldid=895549 (CC BY-NC-SA 3.0) — **Used:** the scripted guide's
    Agility: the Gnome Stronghold course to 25, Werewolf Skullball 25–52, the Wilderness course 52–80, Ape Atoll
    80+. Added 2026-11-09.
46. **RuneScape Wiki. "Herblore",** revision 875720 (2009-01-23). https://runescape.wiki/w/Herblore?oldid=875720
    (CC BY-NC-SA 3.0) — **Used:** the scripted guide's Herblore, the potions by level (January 2009 had no Herblore
    training page). Added 2026-11-09.
47. **RuneScape Wiki. "Free-to-play Runecrafting training",** revision 888316 (2009-01-28).
    https://runescape.wiki/w/Free-to-play_Runecrafting_training?oldid=888316 (CC BY-NC-SA 3.0) — **Used:** the
    scripted guide's Runecrafting: air runes to 9, earth runes from 9. Added 2026-11-09.
48. **RuneScape Wiki. "Pay-to-play Runecrafting training",** revision 832614 (2009-01-08).
    https://runescape.wiki/w/Pay-to-play_Runecrafting_training?oldid=832614 (CC BY-NC-SA 3.0) — consulted: its
    methods (Zanaris's cosmics, the ZMI altar, astral runes) aren't in the sim. Added 2026-11-09.
49. **RuneScape Wiki. "Server",** revision 893026 (2009-01-29). https://runescape.wiki/w/Server?oldid=893026
    (CC BY-NC-SA 3.0) — **Used:** 2009's worlds for OQ-57: 175 in its table, 88 free and 87 members'. Added
    2026-11-09.
50. **C. Truong, L. Oudre, N. Vayatis (2020). "Selective review of offline change point detection methods."**
    *Signal Processing* 167, 107299. Its library, **ruptures** (BSD-2-Clause), 1.1.10. — **Used:** the changepoints
    in the learning curves (OQ-78; `rlscape/analysis/measures.py`). Added 2026-11-11.
51. **R. Killick, P. Fearnhead, I. A. Eckley (2012). "Optimal detection of changepoints with a linear computational
    cost."** *Journal of the American Statistical Association* 107(500), 1590–1598. — **Used:** PELT, the search
    ruptures runs for OQ-78, with a mean shift's cost and a BIC penalty. Added 2026-11-11.
52. **J. D. Hunter (2007). "Matplotlib: A 2D graphics environment."** *Computing in Science & Engineering* 9(3),
    90–95. matplotlib 3.11.2 (its license is PSF-based). — **Used:** the report's figures
    (`rlscape/analysis/figures.py`). Added 2026-11-11.

sb3-contrib's MaskablePPO ([15]) has been in use since 2026-11-08: `SMDPMaskablePPO` and its rollout buffer
(`rlscape/agents/ppo.py`) subclass it.

## Planned (named in ROADMAP.md, not used yet)

- **CleanRL** `ppo_rnd_envpool.py`, the reference for a dual-value-head RND. E3, if needed.

No longer planned: **MORL-Baselines** (Envelope Q-learning) and **MO-Gymnasium**, for E4. OQ-17 (a′) (Caleb,
2026-11-09) replaces E4's Envelope Q with a weight-conditioned PPO.
