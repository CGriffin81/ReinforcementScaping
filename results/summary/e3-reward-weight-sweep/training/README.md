# e3-reward-weight-sweep: training

Published from `runs/e3-reward-weight-sweep` by `scripts/publish_training.py`: 25 runs. `runs.csv` has each run's provenance and settings, `learning_curves.csv.gz` each run's finished episodes, `configs/` each run's config.json.

| Variant | Runs | Decisions a run | Total level, last 100 episodes | Net worth (gp), last 100 episodes |
|---|---:|---:|---:|---:|
| normalised_weights0-1 | 5 | 2,000,896 | 41 | 3,691,041 |
| normalised_weights0.25-0.75 | 5 | 2,000,896 | 167 | 817,952 |
| normalised_weights0.5-0.5 | 5 | 2,000,896 | 284 | 580,671 |
| normalised_weights0.75-0.25 | 5 | 2,000,896 | 387 | 73,048 |
| normalised_weights1-0 | 5 | 2,000,896 | 390 | 11,726 |

Each number is the mean over the variant's runs of their own means. The policies' evaluations against the baselines, on E1's seeds, are the experiment's own summary beside this folder.
