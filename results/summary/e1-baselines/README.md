# e1-baselines

Published from `results/eval/e1-baselines` by `scripts/publish_summary.py`. The tables are CSV copies of the run's own (rlscape/eval/harness.py); `config.json` is the run's.

| | |
|---|---|
| Command | `uv run python scripts/evaluate.py --config configs/e1-baselines.yaml` |
| Git SHA | `4b969d1559a75dda1263b17b074e5e01c00739ff` |
| Fork SHA | `cad9743444626e56b9e758db1b78867e7fe75b86` |
| Config hash | `4fd4698dbad7` |
| Created (UTC) | 2026-11-09T22:28:18+00:00 |
| Seeds | 30 |

## At hour 20: mean [95% bootstrap CI] over 30 seeds

| Policy | Total level | Total XP | Net worth (gp) |
|---|---:|---:|---:|
| random | 214 [205, 222] | 79,660 [74,003, 85,680] | 14,190 [11,071, 17,676] |
| greedy_xp | 157 [157, 157] | 700,606 [698,093, 703,035] | 1,160 [1,133, 1,188] |
| greedy_wealth | 40 [36, 46] | 15,747 [1,639, 36,927] | 1,891,142 [1,766,299, 1,975,610] |
| scripted_guide | 351 [344, 357] | 97,279 [94,665, 99,791] | 129,789 [123,945, 135,909] |

Files:
- `summary.csv`: per policy, checkpoint hour and metric, the mean over seeds, its 95% CI and the standard deviation;
- `checkpoints.csv`: each seed's metrics at each checkpoint (hour 0 is the fresh character);
- `episodes.csv`: each episode's decisions, reward sums, final metrics, deaths, most chosen options and wall time (the only column that changes between identical runs).
