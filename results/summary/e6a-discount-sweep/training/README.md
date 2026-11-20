# e6a-discount-sweep: training

Published from `runs/e6a-discount-sweep` by `scripts/publish_training.py`: 10 runs. `runs.csv` has each run's provenance and settings, `learning_curves.csv.gz` each run's finished episodes, `configs/` each run's config.json.

| Variant | Runs | Decisions a run | Total level, last 100 episodes | Net worth (gp), last 100 episodes |
|---|---:|---:|---:|---:|
| gamma_hr0.5 | 5 | 2,000,896 | 246 | 2,277,736 |
| gamma_hr0.9 | 5 | 2,000,896 | 338 | 1,062,918 |

Each number is the mean over the variant's runs of their own means. The policies' evaluations against the baselines, on E1's seeds, are the experiment's own summary beside this folder.
