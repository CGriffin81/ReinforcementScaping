# e2-ppo-sanity-ladder: training

Published from `runs/e2-ppo-sanity-ladder` by `scripts/publish_training.py`: 8 runs. `runs.csv` has each run's provenance and settings, `learning_curves.csv` each run's finished episodes, `configs/` each run's config.json.

| Variant | Runs | Decisions a run | Total level, last 100 episodes | Net worth (gp), last 100 episodes |
|---|---:|---:|---:|---:|
| gae_lambda0.95_learning_rate0.0001 | 2 | 1,000,448 | 286 | 6,508 |
| gae_lambda0.95_learning_rate0.0003 | 2 | 1,000,448 | 328 | 8,561 |
| gae_lambda0.99_learning_rate0.0001 | 2 | 1,000,448 | 276 | 6,075 |
| gae_lambda0.99_learning_rate0.0003 | 2 | 1,000,448 | 315 | 10,135 |

Each number is the mean over the variant's runs of their own means. The policies' evaluations against the baselines, on E1's seeds, are the experiment's own summary beside this folder.
