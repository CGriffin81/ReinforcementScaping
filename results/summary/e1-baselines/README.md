# e1-baselines

Published from `results/eval/e1-baselines` by `scripts/publish_summary.py`. The tables are CSV copies of the run's own (rlscape/eval/harness.py); `config.json` is the run's.

| | |
|---|---|
| Command | `uv run python scripts/evaluate.py --config configs/e1-baselines.yaml` |
| Git SHA | `d73e4d19d5aa5141eee1be10e1f01e13798754a4` |
| Fork SHA | `cad9743444626e56b9e758db1b78867e7fe75b86` |
| Config hash | `4fd4698dbad7` |
| Created (UTC) | 2026-11-09T20:09:59+00:00 |
| Seeds | 30 |

## At hour 20: mean [95% bootstrap CI] over 30 seeds

| Policy | Total level | Total XP | Net worth (gp) |
|---|---:|---:|---:|
| random | 215 [207, 223] | 76,322 [70,940, 82,151] | 14,552 [10,461, 19,468] |
| greedy_xp | 157 [157, 157] | 700,606 [698,093, 703,035] | 1,160 [1,133, 1,188] |
| greedy_wealth | 40 [36, 46] | 15,747 [1,639, 36,927] | 1,891,142 [1,766,299, 1,975,610] |
| scripted_guide | 351 [344, 357] | 98,285 [95,439, 101,215] | 130,567 [125,487, 135,752] |

Files:
- `summary.csv`: per policy, checkpoint hour and metric, the mean over seeds, its 95% CI and the standard deviation;
- `checkpoints.csv`: each seed's metrics at each checkpoint (hour 0 is the fresh character);
- `episodes.csv`: each episode's decisions, reward sums, final metrics, deaths, most chosen options and wall time (the only column that changes between identical runs).
