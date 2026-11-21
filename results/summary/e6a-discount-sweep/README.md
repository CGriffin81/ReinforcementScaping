# e6a-discount-sweep

Published from `results/eval/e6a-discount-sweep` by `scripts/publish_summary.py`. The tables are CSV copies of the run's own (rlscape/eval/harness.py); `config.json` is the run's.

| | |
|---|---|
| Command | `uv run python scripts/evaluate.py --config configs/e6a-discount-sweep-eval.yaml` |
| Git SHA | `4ca2bed9592545b19e71c12306a89eb2b1343d76` |
| Fork SHA | `cad9743444626e56b9e758db1b78867e7fe75b86` |
| Config hash | `c2b345e83fb4` |
| Created (UTC) | 2026-11-20T00:09:11+00:00 |
| Seeds | 30 |

## At hour 20: mean [95% bootstrap CI] over 30 seeds

| Policy | Total level | Total XP | Net worth (gp) |
|---|---:|---:|---:|
| random | 214 [206, 223] | 80,926 [75,825, 86,282] | 16,563 [11,766, 21,834] |
| greedy_xp | 157 [157, 157] | 699,732 [696,707, 702,701] | 1,111 [1,091, 1,131] |
| greedy_wealth | 79 [69, 89] | 43,096 [26,068, 62,440] | 1,764,896 [1,671,363, 1,849,582] |
| scripted_guide | 351 [344, 357] | 97,279 [94,665, 99,791] | 129,789 [123,945, 135,909] |
| gamma_hr0.5/seed0 | 356 [351, 360] | 263,909 [258,261, 269,817] | 804,897 [734,068, 876,447] |
| gamma_hr0.5/seed1 | 323 [318, 329] | 287,488 [283,052, 291,461] | 1,228,805 [1,161,705, 1,297,857] |
| gamma_hr0.5/seed2 | 334 [331, 338] | 277,229 [271,303, 283,385] | 911,158 [853,407, 969,217] |
| gamma_hr0.5/seed3 | 109 [107, 112] | 22,008 [20,758, 23,250] | 4,174,805 [4,156,644, 4,189,670] |
| gamma_hr0.5/seed4 | 114 [110, 118] | 25,578 [23,242, 27,937] | 3,953,760 [3,709,851, 4,124,135] |
| gamma_hr0.9/seed0 | 321 [316, 326] | 295,929 [293,059, 298,766] | 1,206,932 [1,159,502, 1,256,814] |
| gamma_hr0.9/seed1 | 380 [375, 386] | 293,022 [286,273, 300,209] | 306,408 [271,790, 339,779] |
| gamma_hr0.9/seed2 | 316 [312, 321] | 299,410 [295,174, 303,670] | 1,205,200 [1,139,044, 1,272,791] |
| gamma_hr0.9/seed3 | 329 [324, 334] | 433,839 [407,374, 461,128] | 1,768,855 [1,706,231, 1,833,952] |
| gamma_hr0.9/seed4 | 305 [300, 311] | 288,619 [280,871, 295,983] | 1,212,961 [1,116,153, 1,294,825] |

Files:
- `summary.csv`: per policy, checkpoint hour and metric, the mean over seeds, its 95% CI and the standard deviation;
- `checkpoints.csv`: each seed's metrics at each checkpoint (hour 0 is the fresh character);
- `episodes.csv`: each episode's decisions, reward sums, final metrics, deaths, most chosen options and wall time (the only column that changes between identical runs).
- `decisions.csv.gz`: every episode's trace, a row per decision: the game tick it ended at, its option and why it ended, and the total level and net worth after it.
