# e6b-pbrs-shaping

Published from `results/eval/e6b-pbrs-shaping` by `scripts/publish_summary.py`. The tables are CSV copies of the run's own (rlscape/eval/harness.py); `config.json` is the run's.

| | |
|---|---|
| Command | `uv run python scripts/evaluate.py --config configs/e6b-pbrs-shaping-eval.yaml` |
| Git SHA | `47d2bead581b3e5f7365439e92b34b1f9c112f85` |
| Fork SHA | `cad9743444626e56b9e758db1b78867e7fe75b86` |
| Config hash | `eab185d823ab` |
| Created (UTC) | 2026-11-20T00:40:35+00:00 |
| Seeds | 30 |

## At hour 20: mean [95% bootstrap CI] over 30 seeds, except as marked

| Policy | Total level | Total XP | Net worth (gp) |
|---|---:|---:|---:|
| random | 214 [206, 223] | 80,926 [75,825, 86,282] | 16,563 [11,766, 21,834] |
| greedy_xp | 157 [157, 157] | 699,732 [696,707, 702,701] | 1,111 [1,091, 1,131] |
| greedy_wealth | 79 [69, 89] | 43,096 [26,068, 62,440] | 1,764,896 [1,671,363, 1,849,582] |
| scripted_guide | 351 [344, 357] | 97,279 [94,665, 99,791] | 129,789 [123,945, 135,909] |
| pbrs/seed0 | 260 [252, 268] | 149,370 [142,709, 155,926] | 203,658 [177,858, 231,971] |
| pbrs/seed1 | 209 [198, 218] | 311,456 [297,452, 325,689] | 120,947 [109,505, 132,742] |
| pbrs/seed2 (27 seeds) | 98 [95, 100] | 331,399 [265,676, 394,258] | 157,604 [129,433, 185,122] |
| pbrs/seed4 | 209 [202, 214] | 110,843 [104,163, 118,767] | 86,268 [65,205, 108,701] |

Short of hour 20:
- `pbrs/seed2`: 3 of its 30 episodes stop before hour 20, at the evaluation's cap of 100,000 decisions; its row is over the 27 seeds that reach it.
- `pbrs/seed3`: all 30 of its episodes stop before hour 20, at the evaluation's cap of 100,000 decisions, so it has no row.
- `episodes.csv` has each episode's decisions and game ticks.

Files:
- `summary.csv`: per policy, checkpoint hour and metric, the mean over seeds, its 95% CI and the standard deviation;
- `checkpoints.csv`: each seed's metrics at each checkpoint (hour 0 is the fresh character);
- `episodes.csv`: each episode's decisions, reward sums, final metrics, deaths, most chosen options and wall time (the only column that changes between identical runs).
- `decisions.csv.gz`: every episode's trace, a row per decision: the game tick it ended at, its option and why it ended, and the total level and net worth after it.
