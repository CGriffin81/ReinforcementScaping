# Learning to Climb: Hierarchical RL for Skill and Wealth Accumulation in 2009Scape

CS898BG Reinforcement Learning, individual project (Caleb Griffin). A high-level policy picks activity-level options
(train a skill at a site, fight a monster, bank, buy or sell on the Grand Exchange) in a semi-MDP, over a fixed
20-hour game-time budget, and is rewarded for skill and wealth gained. It trains on a simulator of the game,
calibrated option by option against a local 2009Scape server.

**Reviewing this project? Start here.** This page maps what the report claims to its results and to the figures
and code behind them. It gives a reading path through the RL code (about 2,500 of the repo's 36,000 lines of
Python), says what you can skip and why it can be trusted, and has a check you can run in about 10 minutes without a
server or a GPU.

## 1. What the report claims, and where each claim comes from

Every figure and table is rebuilt from the small summaries committed in `results/summary/` by one command,
`uv run python scripts/figures.py`, into `results/figures/` (no training, evaluation or server).

The results are each policy's evaluation: 30 seeded 20-hour episodes from a fresh character, for each of a variant's
five training seeds. Means are over the seeds, and the tables give 95% CIs. A weighting (u, 1 − u) weights skill and
wealth, each in units of E1's best 20-hour gain on it (324 levels, 1.76M gp).

| Claim | Experiments | What the results show | Figures and tables | Code |
|---|---|---|---|---|
| **RQ1** Can a learned policy beat greedy XP/hr, greedy GP/hr and a scripted guide on total level and net worth at fixed checkpoints? | E1 (baselines), E3 | At the ends, yes, from the first checkpoint on; at the mixed weightings, no. At hour 20, the all-skill agents average total level 382 against the guide's 351, the best baseline on level, and the all-wealth agents 3.74M gp against greedy GP/hr's 1.76M. At hour 2 both are already ahead of every baseline (121 levels against greedy XP/hr's 106, the best baseline on level that early; 247k gp against greedy GP/hr's 108k). On the reward's weighted value, they beat E1's best baseline at (1, 0) (1.093 against the guide's 1.000, 4 of 5 seeds above it) and at (0, 1) (2.118 against greedy GP/hr's 1.000, 5 of 5). They don't at (.75, .25) (0.754 against the guide's 0.768, 2 of 5), (.5, .5) (0.526 against greedy GP/hr's 0.571, 2 of 5) or (.25, .75) (0.453 against 0.785, 0 of 5). (.5, .5), for one, ends at 263 and 588k, against the guide's 351 and 130k and greedy GP/hr's 79 and 1.76M. | `progress`, `weighted_value.csv`, `milestones_summary.csv` | `rlscape/analysis/measures.py` (`progress`, `gains`, `milestones`); `figures.py` (`weighted_values`) |
| **RQ2** In what order are activities discovered; does the agent invest early; is learning gradual or sudden? | E3 | At (.5, .5), an activity is "discovered" when it first takes 5% of a 100k-decision block's game time. Woodcutting, agility and melee are discovered in the first block. Fishing follows by 400k–500k decisions and thieving by 500k–600k, in all five runs; banking by 0.8M–1.4M, in four. Learning is gradual at the skill end (5 of 5 runs at (1, 0), 4 of 5 at (.75, .25)) and sudden at the wealth end (5 of 5 at (0, 1)), by OQ-82 (c)'s rule. At (.5, .5), 1 run is gradual, 2 are sudden and 2 show no gain. For investing early, see H1. | `learning_e3`, `verdicts.csv`, `time_e3`, `discovery.csv`, `entropy` | `measures.py` (`run_changes`, `time_shares`, `discovery`) |
| **RQ3** How does the skill/wealth weighting shape behaviour and the trade-off frontier; can one weight-conditioned agent match five? | E3, E5 | From all skill to all wealth, the mean level at hour 20 falls from 382 to 41, and net worth rises from 11k to 3.74M gp. The mix moves from woodcutting, melee, fishing and crafting (15–22% of game time each) at (1, 0), to woodcutting (97%) at (.25, .75), to buying uncut gems in shops and selling them on the GE (93%) at (0, 1). Woodcutting counts every way of chopping, and the agents choose what happens to the logs. At (.25, .75), they chop normal logs and fletch them into arrow shafts for 92% of their game time, and the shafts (5 gp each, stacking in one slot) are 94% of their net worth at hour 20. At (1, 0), they burn about two thirds of what they chop and fletch the rest (14% and 8% of game time, over four of the five runs). One weight-conditioned agent's front has about the hypervolume of five specialists' (0.394, CI 0.360–0.456, against 0.373, 0.278–0.484) for a fifth of the training (2.0M decisions and 8.4 hours a front, against 10.0M and 38.1). It falls short at the ends: told all skill, it averages level 359, against the specialists' 382; told all wealth, 862k gp, against 3.74M. | `pareto`, `hypervolume.csv`, `training_cost.csv`, `mix`; the logs' split, from replays of the evaluation episodes (decision log, 2026-11-23) | `measures.py` (`gains`, `hypervolumes`); `figures.py` (`training_cost`); `rlscape/agents/conditioned.py`; `rlscape/sim/skilling.py` (a woodcutting slot's paths) |
| **RQ4** Do an exploration bonus, the discount and potential-based shaping change which strategies are found and how fast? | E4 (RND), E6a (γ per game-hour), E6b (PBRS), each against E3's (.5, .5) | Plain PPO at (.5, .5) (γ_hr 0.99) averages level 263 and 588k gp at hour 20. RND ends lower on both (226 and 135k), and none of its five learning curves gains. A shorter horizon learns faster and moves toward wealth: γ_hr 0.9 averages 330 and 1.14M gp, and 0.5 averages 247 and 2.21M, two of its seeds finding the Gem Store's emeralds (about 4M gp each). PBRS ends at 194 and 142k over four seeds, and none of its curves gains either; the fifth seed's episodes stop at the 100,000-decision cap. On the training curves, every run at γ_hr 0.5 reaches the best greedy baseline's weighted value (by 260k–380k decisions), and every run at 0.9 (by 440k–740k). At 0.99, 3 of 5 runs reach it (by 0.70M–1.06M), and none does with RND or PBRS. In evaluation, γ_hr 0.9 (0.787) and 0.5 (0.963) beat greedy GP/hr's 0.571 in every seed, plain PPO in 2 of 5, and RND (0.342) and PBRS (0.240) in none. | `learning_rq4`, `time_rq4`, `discovery`, `sample_efficiency.csv`, `weighted_value.csv`, `verdicts.csv` | `rlscape/agents/rnd.py`, `pbrs.py`; `ppo.gamma_hr` in the configs |
| **RQ5** Would learned low-level options (click-ahead pathing, prayer flicking) help? Bounded, not tested | E3's evaluation | A perfect click-ahead saves at most the walker's measured overhead. That is 2.6% of (.5, .5)'s game time (CI 1.4–4.0%), and 10.5% at most, for (0, 1), which spends 96% of its time walking. The scripted prayer flick never drains prayer and gets the prayer's full effect, so a learned flick can't beat it. | `rq5_walking_summary.csv` | `rlscape/eval/walking.py`; `measures.py` (`walking`) |
| **H1** Learned policies win by front-loading investments with delayed payoff | E1, E3 | **Partly supported** (Caleb, 2026-11-22). The demo's (.5, .5) run invests: it pickpockets its Thieving up to the 38 that Master Farmers need by hour 7.9, while worth 38k gp, then passes a million by hour 20 (one episode, `scripts/replay.py`). But that isn't how the agents win where they win. At both ends they lead from the first checkpoint, and the lead grows (RQ1). The all-wealth agents gain 6 levels in 20 hours: their win is the uncut-gem trade from the start. | `progress`, `weighted_value.csv`, `mix`, `milestones_summary.csv` | as RQ1 |
| **H2** Weightings give different activity mixes, not one strategy at different speeds | E3 | **Partly supported** (Caleb, 2026-11-22): on the wealth side the weighting changes the strategy, and on the skill side it's one strategy at different speeds. (1, 0) and (.75, .25) have nearly the same mix: woodcutting 22% each, melee 21% and 15%, fishing 15% and 17%, crafting 15% and 16%. The Jensen–Shannon divergence between their seeds' mixes is 0.138 bits, less than between (.75, .25)'s own seeds (0.194). (.5, .5) is 0.335 and 0.349 bits from them, about its own seeds' 0.296. (.25, .75) and (0, 1) each have their own mix (RQ3), which their seeds agree on (0.020 and 0.015 bits), 0.51–0.95 bits from every other weighting. | `mix`, `time_e3`, `consistency.csv`, `mix_divergence.csv` | `measures.py` (`trace_shares`, `consistency`, `divergence_between`) |
| **H3** An exploration bonus changes the order activities are discovered in | E3, E4 | **Supported** (Caleb, 2026-11-22). RND changes which activities are discovered, and when. Buying and selling are discovered in all five RND runs, by 100k–500k decisions; plain PPO discovers buying in none of five and selling in one. RND never discovers fishing or banking, which plain PPO discovers in 5 and 4 of 5. The change doesn't pay: RND ends lower on both objectives (RQ4). | `discovery` | `measures.py` (`discovery`) |
| **The simulator stands for the game** | the calibration gate | 533 of 548 gated metrics are within ±20%, over 236 cases, and each of the 15 outside is explained in the table's README (section 3). | `sim_to_real_families.csv`, `sim_to_real_cases.csv` | `scripts/sim_to_real.py` |
| **Limit: some runs end training in a loop** | E3 to E6b | At γ_hr 0.99, 10 of 40 runs end training repeating near-instant options that earn nothing, thousands of times an episode. These are 8 of E3's 25 (4 of 5 at (.5, .5)) and 2 of E6b's 5. Eight loop on the loot settings and two on banking. None of the 10 runs at γ_hr 0.5 or 0.9 loops. The cause is untested. | `docs/decision-log.md` (the final census, 2026-11-20), from each run's decisions per episode in `training/learning_curves.csv.gz` | OQ-90 (a)'s rule, in the decision log |
| **Limit: the trainer's two changes** (env contract v1.46) | E3, first round and rerun | E3 to E6b's 50 runs were trained again after a fix to the time-limit bootstrap and a 100-tick floor on each decision. At the mixed weightings, E3's first round found the Gem Store trade in 5 of 15 runs and the rerun in none. At (.25, .75), the first round ends at 3.36M gp and level 123, against 0.82M and 168. Why is untested. | `gem_store_rounds.csv`, `gem_store_rounds_per_seed.csv` | `figures.py` (`gem_store_round`) |

Each experiment's numbers, and the command that made them, are in `results/summary/<experiment>/README.md`. The
experiments are E1 `e1-baselines`, E2 `e2-ppo-sanity-ladder` (the PPO sanity ladder), E3 `e3-reward-weight-sweep`,
E4 `e4-rnd-exploration`, E5 `e5-weight-conditioned-ppo`, E6a `e6a-discount-sweep` and E6b `e6b-pbrs-shaping`, each
with its config in `configs/` (training, and `-eval` for its evaluation).

## 2. A reading path through the RL code

In this order (lines in brackets):

1. `rlscape/envs/sim_env.py` (77): the Gymnasium environment: options as actions, the action mask, reward and info.
2. `rlscape/envs/encoding.py` (371): the observation (character, inventory, candidate options) and the mask.
3. `rlscape/envs/weights.py` (54): the reward weights, in units of E1's best 20-hour gain on each objective.
4. `rlscape/agents/smdp.py` (72): semi-MDP discounting, γ to the power of each option's game-time duration, in GAE.
5. `rlscape/agents/ppo.py` (133): masked PPO with that rollout buffer.
6. `rlscape/agents/training.py` (291): a run from its config: envs, seeding, checkpoints, wrappers.
7. `rlscape/agents/decision_log.py` (122): every decision logged (observation, mask, option, probabilities, value,
   duration, reward parts).
8. `rlscape/agents/rnd.py`, `pbrs.py` and `conditioned.py`: E4's exploration bonus, E6b's shaping, E5's weights in
   the observation.
9. `rlscape/baselines/policies.py` (103), with `guide.py`: the baselines.
10. `rlscape/eval/harness.py` (226) and `rollout.py` (72), then `rlscape/analysis/measures.py` (440): evaluation and
    the measures the figures plot.

The scripts that drive them are `scripts/train.py`, `evaluate.py`, `publish_summary.py`, `publish_training.py` and
`figures.py`.

## 3. What to skip, and why it can be trusted

- **The simulator** (`rlscape/sim/`, `gamedata/`, `combat/`, `routes.py`, `travel.py`; about 13,000 lines): the
  game's mechanics, ported from the server's source, with the overheads (travel, banking, clicks) measured on the
  server. The sim-to-real table (`results/summary/sim-to-real/README.md`) re-runs every calibration case on
  `sim-v1.2` against the server's runs: 533 of 548 gated metrics within ±20%, and each case outside is explained
  there. The experiments ran on the frozen `sim-v1.4`, which plays out exactly as `sim-v1.2` wherever `sim-v1.2`
  completes. It changes two edge cases: a gathering option whose monsters kill the character after its budget ends
  at the budget, and a tanning trip whose fare spent every coin tans nothing. The simulator's tests are
  `tests/test_sim_*.py` (32 files).
- **The server and the bridge** (`server/`, a git submodule of the 2009Scape fork; `rlscape/bridge/`; the
  calibration scripts `scripts/calibrate_*.py`, `measure_*.py`, `validate_travel.py`, `probe_drops.py`,
  `speed_check.py`): used only to measure the game. Nothing in training, evaluation or the figures needs a server.
- **`docs/`**: the design record. `env-contract.md` specifies the environment, `decision-log.md` has every decision
  and finding with its date, and `agent-interactions/` holds the records of AI-assisted work the course's policy
  requires (`ai-log-requirements.md`).

## 4. A 10-minute check (no server, no GPU)

**It needs Windows x64.** The environment's torch is PyTorch's Windows CUDA wheel (it runs on the CPU too), so it
doesn't install on Linux or macOS; there, the code and the committed summaries can be read, but the check can't run.
Setup, once, with [uv](https://docs.astral.sh/uv/) (it fetches Python 3.12):

```
git clone --recurse-submodules <this repository>   # GIT_LFS_SKIP_SMUDGE=1: the server's cache files aren't needed
uv run --no-project python scripts/fetch_torch_wheel.py   # 1.9 GB into wheels/, resumable, its SHA-256 checked
uv sync
```

Then:

1. **The core tests** (about 2 minutes): semi-MDP discounting, PPO on a three-option task with a known optimum, and
   the environment.
   `uv run pytest tests/test_smdp.py tests/test_smdp_ppo.py tests/test_toy.py tests/test_sim_env.py -q`
2. **Every figure and table from the committed summaries** (about a minute): `uv run python scripts/figures.py`, then
   look in `results/figures/`.
3. **A short training run on the CPU** (about 3 minutes; the first run also builds the travel model's table,
   `data/travel/places.npz`, in a few minutes): 2,048 decisions of E2's configuration, which writes its provenance,
   checkpoints, TensorBoard logs and decision log.
   `uv run python scripts/train.py --config configs/e2-ppo-sanity-ladder.yaml --seed 0 --variant gae_lambda0.99_learning_rate0.0003 --total-decisions 2048 --out runs/review-check`

## 5. Reproducing the experiments

Each experiment ran on its own branch (`experiment/<name>`) from the frozen simulator and is merged into `main`
with its committed summary; the reviewed version is the tag `[to come]`. Training all of E3 to E6b (50 runs of 2M
decisions) took [about four days: to confirm when the queue ends] on one machine (Windows 11, Ryzen 7 5800X, 32 GB
RAM, RTX 3050). For an experiment:

```
uv run python scripts/train.py --config configs/<name>.yaml --jobs 4
uv run python scripts/publish_training.py runs/<name> <name>
uv run python scripts/evaluate.py --config configs/<name>-eval.yaml
uv run python scripts/publish_summary.py <run dir> <name>
uv run python scripts/figures.py
```

Runs are deterministic, on the GPU too: the same commit, config and seed give the same decisions, byte for byte.
