# e2-ppo-sanity-ladder: rung 2, PPO against random

By `scripts/e2_rung2.py` from this experiment's evaluation summary (the folder above: `configs/e2-ppo-sanity-ladder-eval.yaml`, git `e3719a3`, 30 seeds, sampled actions). Reward is w_s·r_skill + w_b·r_wealth at the env's weights (0.5, 0.5).

## The variants, by mean episode reward over their runs

| Variant | Runs | Reward | By run | Total level | Total XP | Net worth (gp) |
|---|---:|---:|---|---:|---:|---:|
| gae_lambda0.95_learning_rate0.0003 | 2 | 149.63 | 151.79 147.46 | 328 | 256,900 | 8,115 |
| gae_lambda0.99_learning_rate0.0003 | 2 | 142.39 | 141.70 143.09 | 314 | 198,932 | 10,505 |
| gae_lambda0.95_learning_rate0.0001 | 2 | 127.66 | 128.60 126.72 | 286 | 251,353 | 5,765 |
| gae_lambda0.99_learning_rate0.0001 | 2 | 124.52 | 125.31 123.72 | 278 | 233,631 | 4,723 |

**The best variant is `gae_lambda0.95_learning_rate0.0003`.**

## Its runs against the baselines: mean paired difference [95% bootstrap CI] over seeds

| Run | Against | Reward | Total level | Total XP | Net worth (gp) |
|---|---|---:|---:|---:|---:|
| seed0 | random | +59.05 [+55.03, +63.35] | +119 [+111, +127] | +137,666 [+125,397, +150,184] | -6,316 [-10,561, -2,303] |
| seed0 | scripted_guide | -10.78 [-14.35, -6.81] | -18 [-26, -10] | +120,047 [+109,362, +131,669] | -121,915 [-128,137, -115,843] |
| seed1 | random | +54.72 [+50.07, +59.18] | +110 [+101, +119] | +216,814 [+202,268, +232,745] | -5,834 [-9,548, -2,430] |
| seed1 | scripted_guide | -15.11 [-18.60, -11.24] | -27 [-34, -19] | +199,195 [+185,507, +213,886] | -121,433 [-127,703, -115,160] |

**Rung 2 passes:** every run of the best variant must have a reward difference against random whose CI is above 0.

Files: `variants.csv` (every variant's means), `paired.csv` (every trained run against random and the guide, on every measure).
