# e3-reward-weight-sweep-bootstrap

Published from `results/eval/e3-reward-weight-sweep-bootstrap` by `scripts/publish_summary.py`. The tables are CSV copies of the run's own (rlscape/eval/harness.py); `config.json` is the run's.

| | |
|---|---|
| Command | `uv run python scripts/evaluate.py --config configs/e3-reward-weight-sweep-eval.yaml --workers 8` |
| Git SHA | `ba9d8ec306e38e13ff705306240b61a55cac7bc6` |
| Fork SHA | `cad9743444626e56b9e758db1b78867e7fe75b86` |
| Config hash | `77e8a2d290a0` |
| Created (UTC) | 2026-11-15T17:34:35+00:00 |
| Seeds | 30 |

## At hour 20: mean [95% bootstrap CI] over 30 seeds

| Policy | Total level | Total XP | Net worth (gp) |
|---|---:|---:|---:|
| random | 214 [206, 223] | 80,926 [75,825, 86,282] | 16,563 [11,766, 21,834] |
| greedy_xp | 157 [157, 157] | 699,732 [696,707, 702,701] | 1,111 [1,091, 1,131] |
| greedy_wealth | 79 [69, 89] | 43,096 [26,068, 62,440] | 1,764,896 [1,671,363, 1,849,582] |
| scripted_guide | 351 [344, 357] | 97,279 [94,665, 99,791] | 129,789 [123,945, 135,909] |
| normalised_weights1-0/seed0 | 346 [342, 349] | 208,775 [199,933, 217,909] | 12,872 [10,047, 16,045] |
| normalised_weights1-0/seed1 | 330 [326, 334] | 242,625 [235,827, 249,113] | 11,964 [8,205, 16,106] |
| normalised_weights1-0/seed2 | 339 [336, 342] | 207,478 [200,584, 213,697] | 11,135 [8,168, 14,784] |
| normalised_weights1-0/seed3 | 336 [332, 340] | 249,070 [239,071, 258,383] | 11,499 [7,279, 17,187] |
| normalised_weights1-0/seed4 | 341 [338, 343] | 210,544 [201,559, 220,149] | 9,867 [8,031, 11,875] |
| normalised_weights0.75-0.25/seed0 | 343 [340, 345] | 195,743 [188,548, 202,378] | 89,754 [82,453, 96,641] |
| normalised_weights0.75-0.25/seed1 | 344 [340, 347] | 193,842 [188,645, 198,844] | 104,630 [95,719, 113,646] |
| normalised_weights0.75-0.25/seed2 | 343 [340, 346] | 189,630 [185,499, 193,918] | 89,517 [79,764, 98,733] |
| normalised_weights0.75-0.25/seed3 | 347 [343, 351] | 241,731 [229,544, 253,616] | 74,469 [65,846, 82,557] |
| normalised_weights0.75-0.25/seed4 | 348 [345, 351] | 230,759 [222,160, 239,625] | 60,926 [50,852, 71,526] |
| normalised_weights0.5-0.5/seed0 | 331 [328, 334] | 153,788 [148,220, 159,655] | 183,083 [163,230, 201,628] |
| normalised_weights0.5-0.5/seed1 | 197 [186, 207] | 65,886 [56,659, 75,559] | 3,048,571 [2,883,424, 3,208,491] |
| normalised_weights0.5-0.5/seed2 | 361 [357, 364] | 179,051 [174,411, 183,508] | 199,548 [190,244, 208,564] |
| normalised_weights0.5-0.5/seed3 | 317 [309, 325] | 151,178 [145,233, 157,309] | 213,042 [195,660, 229,642] |
| normalised_weights0.5-0.5/seed4 | 344 [341, 348] | 192,750 [187,602, 198,074] | 145,525 [135,424, 155,729] |
| normalised_weights0.25-0.75/seed0 | 111 [103, 120] | 27,455 [22,351, 32,698] | 3,872,792 [3,791,044, 3,952,786] |
| normalised_weights0.25-0.75/seed1 | 97 [86, 109] | 20,543 [15,839, 25,527] | 3,992,056 [3,899,977, 4,076,992] |
| normalised_weights0.25-0.75/seed2 | 230 [225, 235] | 108,843 [103,010, 115,088] | 833,706 [752,891, 910,039] |
| normalised_weights0.25-0.75/seed3 | 87 [76, 98] | 19,393 [13,804, 25,670] | 4,044,937 [3,975,095, 4,113,262] |
| normalised_weights0.25-0.75/seed4 | 89 [81, 98] | 16,330 [13,048, 19,874] | 4,058,723 [4,001,179, 4,113,389] |
| normalised_weights0-1/seed0 | 55 [53, 58] | 5,614 [4,608, 6,810] | 3,862,761 [3,808,014, 3,922,792] |
| normalised_weights0-1/seed1 | 37 [36, 38] | 1,647 [1,484, 1,878] | 1,649 [1,192, 2,279] |
| normalised_weights0-1/seed2 | 57 [54, 60] | 6,243 [5,314, 7,193] | 3,885,950 [3,818,436, 3,954,833] |
| normalised_weights0-1/seed3 | 59 [56, 61] | 6,782 [5,771, 8,023] | 3,880,171 [3,821,926, 3,942,838] |
| normalised_weights0-1/seed4 | 53 [49, 56] | 4,999 [3,950, 6,194] | 4,148,421 [4,108,586, 4,188,000] |

Files:
- `summary.csv`: per policy, checkpoint hour and metric, the mean over seeds, its 95% CI and the standard deviation;
- `checkpoints.csv`: each seed's metrics at each checkpoint (hour 0 is the fresh character);
- `episodes.csv`: each episode's decisions, reward sums, final metrics, deaths, most chosen options and wall time (the only column that changes between identical runs).
- `decisions.csv.gz`: every episode's trace, a row per decision: the game tick it ended at, its option and why it ended, and the total level and net worth after it.

## E3's first round (added by hand, 2026-11-20)

This is E3's first round, published to be shown beside the rerun at the mixed weightings (OQ-92 (b)). E3's results
are the rerun's, in `results/summary/e3-reward-weight-sweep/`.
- **Trainer:** the one before 2026-11-15's two fixes (env contract v1.46: no bootstrap at the horizon, a 100-tick
  discount floor). Its configs predate the two settings, so they don't name them.
- **Sim:** 19 of its 25 runs trained on `ba9d8ec` (sim v1.3), and six on `b29de68` (sim v1.2): (1, 0) seeds 0 and 1,
  and seed 0 at each other weighting. sim v1.3 is sim v1.2 wherever sim v1.2 completes (2026-11-12). The evaluation
  ran on `ba9d8ec`, with the rerun's 30 seeds; the rerun's ran on sim v1.4.
- **The model paths in `config.json`** are where the models were when it ran. When the rerun started, they moved to
  `runs/e3-reward-weight-sweep-bootstrap/` in E3's worktree (git-ignored); `runs/e3-reward-weight-sweep/` now holds
  the rerun's.
