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

## Planned (named in ROADMAP.md, not used yet)

- **MORL-Baselines** (Envelope Q-learning implementation) and **MO-Gymnasium**. E4.
- **CleanRL** `ppo_rnd_envpool.py`, the reference for a dual-value-head RND. E3, if needed.
- **sb3-contrib** MaskablePPO (with [15]). E2 onward.
