# Learning to Climb: Hierarchical RL for Skill and Wealth Accumulation in 2009Scape

CS898BG Reinforcement Learning, individual project (Caleb Griffin). A high-level policy picks activity-level options
(train a skill at a site, fight a monster, bank, buy or sell on the Grand Exchange) in a semi-MDP, over a fixed
20-hour game-time budget, and is rewarded for skill and wealth gained. It trains on a simulator of the game,
calibrated option by option against a local 2009Scape server.

**Reviewing this project? Start here.** This page maps what the report claims to the figures and the code behind
them, gives a reading path through the RL code (about 2,500 of the repo's 36,000 lines of Python), says what you can skip and
why it can be trusted, and has a check you can run in about 10 minutes without a server or a GPU.

## 1. What the report claims, and where each claim comes from

Every figure and table is rebuilt from the small summaries committed in `results/summary/` by one command,
`uv run python scripts/figures.py`, into `results/figures/` (no training, evaluation or server).

| Question | Experiments | Figures and tables | Code |
|---|---|---|---|
| **RQ1** Can a learned policy beat greedy XP/hr, greedy GP/hr and a scripted guide on total level and net worth at fixed checkpoints? | E1 (baselines), E3 | `progress`, `milestones_summary.csv`, `sample_efficiency.csv` | `rlscape/analysis/measures.py` (`progress`, `milestones`, `sample_efficiency`) |
| **RQ2** In what order are activities discovered; does the agent invest early; is learning gradual or sudden? | E3 | `learning_e3`, `verdicts.csv`, `time_e3`, `discovery.csv`, `entropy` | `measures.py` (`run_changes`, `time_shares`, `discovery`) |
| **RQ3** How does the skill/wealth weighting shape behaviour and the trade-off frontier; can one weight-conditioned agent match five? | E3, E5 | `pareto`, `hypervolume.csv`, `mix` | `measures.py` (`gains`, `hypervolumes`); `rlscape/agents/conditioned.py` |
| **RQ4** Do an exploration bonus, the discount and potential-based shaping change which strategies are found and how fast? | E4 (RND), E6a (γ per game-hour), E6b (PBRS), each against E3's (.5, .5) | `learning_rq4`, `time_rq4`, `discovery` | `rlscape/agents/rnd.py`, `pbrs.py`; `ppo.gamma_hr` in the configs |
| **RQ5** Would learned low-level options (click-ahead pathing, prayer flicking) help? Bounded, not tested | E3's evaluation | `rq5_walking_summary.csv` | `rlscape/eval/walking.py` |
| **H1** Learned policies win by front-loading investments with delayed payoff | E1, E3 | `progress`, `mix`, `milestones_summary.csv` | as RQ1 |
| **H2** Weightings give different activity mixes, not one strategy at different speeds | E3 | `mix`, `time_e3`, `consistency.csv` | `measures.py` (`trace_shares`, `consistency`) |
| **H3** An exploration bonus changes the order activities are discovered in | E3, E4 | `discovery` | `measures.py` (`discovery`) |
| **The simulator stands for the game** | the calibration gate | `sim_to_real_families.csv`, `sim_to_real_cases.csv` | `scripts/sim_to_real.py` |

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
  server. The sim-to-real table (`results/summary/sim-to-real/README.md`) re-runs every calibration case on the
  frozen simulator (git tag `sim-v1.2`) against the server's runs: 533 of 548 gated metrics within ±20%, and each
  case outside is explained there. The simulator's tests are `tests/test_sim_*.py` (32 files).
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
