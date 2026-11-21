# e6b-pbrs-shaping: training

Published from `runs/e6b-pbrs-shaping` by `scripts/publish_training.py`: 5 runs. `runs.csv` has each run's provenance and settings, `learning_curves.csv.gz` each run's finished episodes, `configs/` each run's config.json.

| Variant | Runs | Decisions a run | Total level, last 100 episodes | Net worth (gp), last 100 episodes |
|---|---:|---:|---:|---:|
| (one config) | 5 | 2,000,896 | 221 | 110,565 |

Each number is the mean over the variant's runs of their own means. The policies' evaluations against the baselines, on E1's seeds, are the experiment's own summary beside this folder.
