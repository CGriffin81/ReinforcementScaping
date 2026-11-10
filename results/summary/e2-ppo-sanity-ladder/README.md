# e2-ppo-sanity-ladder

Published from `results/eval/e2-ppo-sanity-ladder` by `scripts/publish_summary.py`. The tables are CSV copies of the run's own (rlscape/eval/harness.py); `config.json` is the run's.

| | |
|---|---|
| Command | `uv run python scripts/evaluate.py --config configs/e2-ppo-sanity-ladder-eval.yaml` |
| Git SHA | `e3719a3da39b90ff48cf0488d260c717f31fef6f` |
| Fork SHA | `cad9743444626e56b9e758db1b78867e7fe75b86` |
| Config hash | `22b13ab52e37` |
| Created (UTC) | 2026-11-10T10:51:37+00:00 |
| Seeds | 30 |

## At hour 20: mean [95% bootstrap CI] over 30 seeds

| Policy | Total level | Total XP | Net worth (gp) |
|---|---:|---:|---:|
| random | 214 [205, 222] | 79,660 [74,003, 85,680] | 14,190 [11,071, 17,676] |
| scripted_guide | 351 [344, 357] | 97,279 [94,731, 99,791] | 129,789 [123,933, 135,671] |
| gae_lambda0.95_learning_rate0.0001/seed0 | 287 [285, 290] | 261,534 [244,969, 278,573] | 6,119 [4,920, 7,383] |
| gae_lambda0.95_learning_rate0.0001/seed1 | 284 [282, 286] | 241,172 [229,884, 252,307] | 5,412 [4,242, 6,687] |
| gae_lambda0.95_learning_rate0.0003/seed0 | 333 [330, 336] | 217,326 [207,098, 228,239] | 7,874 [6,255, 9,631] |
| gae_lambda0.95_learning_rate0.0003/seed1 | 324 [320, 327] | 296,473 [282,872, 310,423] | 8,356 [6,997, 9,912] |
| gae_lambda0.99_learning_rate0.0001/seed0 | 280 [276, 284] | 233,280 [219,841, 246,114] | 3,928 [2,674, 5,366] |
| gae_lambda0.99_learning_rate0.0001/seed1 | 276 [271, 281] | 233,982 [217,363, 251,220] | 5,517 [3,656, 8,132] |
| gae_lambda0.99_learning_rate0.0003/seed0 | 312 [305, 317] | 177,815 [170,373, 185,193] | 14,007 [10,597, 18,080] |
| gae_lambda0.99_learning_rate0.0003/seed1 | 315 [313, 318] | 220,048 [207,184, 234,536] | 7,003 [5,338, 8,871] |

Files:
- `summary.csv`: per policy, checkpoint hour and metric, the mean over seeds, its 95% CI and the standard deviation;
- `checkpoints.csv`: each seed's metrics at each checkpoint (hour 0 is the fresh character);
- `episodes.csv`: each episode's decisions, reward sums, final metrics, deaths, most chosen options and wall time (the only column that changes between identical runs).
