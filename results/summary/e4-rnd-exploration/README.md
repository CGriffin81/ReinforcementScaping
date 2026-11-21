# e4-rnd-exploration

Published from `results/eval/e4-rnd-exploration` by `scripts/publish_summary.py`. The tables are CSV copies of the run's own (rlscape/eval/harness.py); `config.json` is the run's.

| | |
|---|---|
| Command | `uv run python scripts/evaluate.py --config configs/e4-rnd-exploration-eval.yaml` |
| Git SHA | `88b72552b691963ea8b88e28a44edf2bbef92fc0` |
| Fork SHA | `cad9743444626e56b9e758db1b78867e7fe75b86` |
| Config hash | `88ef803b56d2` |
| Created (UTC) | 2026-11-20T00:24:34+00:00 |
| Seeds | 30 |

## At hour 20: mean [95% bootstrap CI] over 30 seeds

| Policy | Total level | Total XP | Net worth (gp) |
|---|---:|---:|---:|
| random | 214 [206, 223] | 80,926 [75,825, 86,282] | 16,563 [11,766, 21,834] |
| greedy_xp | 157 [157, 157] | 699,732 [696,707, 702,701] | 1,111 [1,091, 1,131] |
| greedy_wealth | 79 [69, 89] | 43,096 [26,068, 62,440] | 1,764,896 [1,671,363, 1,849,582] |
| scripted_guide | 351 [344, 357] | 97,279 [94,665, 99,791] | 129,789 [123,945, 135,909] |
| rnd/seed0 | 217 [213, 221] | 90,313 [83,291, 97,721] | 98,041 [87,410, 108,773] |
| rnd/seed1 | 235 [232, 238] | 146,687 [127,220, 167,736] | 66,890 [59,308, 75,341] |
| rnd/seed2 | 223 [218, 228] | 102,922 [89,412, 119,571] | 177,135 [165,773, 188,309] |
| rnd/seed3 | 222 [215, 229] | 91,582 [81,869, 102,172] | 207,250 [190,301, 222,905] |
| rnd/seed4 | 233 [229, 238] | 107,829 [98,556, 117,497] | 125,263 [111,253, 140,792] |

Files:
- `summary.csv`: per policy, checkpoint hour and metric, the mean over seeds, its 95% CI and the standard deviation;
- `checkpoints.csv`: each seed's metrics at each checkpoint (hour 0 is the fresh character);
- `episodes.csv`: each episode's decisions, reward sums, final metrics, deaths, most chosen options and wall time (the only column that changes between identical runs).
- `decisions.csv.gz`: every episode's trace, a row per decision: the game tick it ended at, its option and why it ended, and the total level and net worth after it.
