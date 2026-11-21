# e3-reward-weight-sweep

Published from `results/eval/e3-reward-weight-sweep` by `scripts/publish_summary.py`. The tables are CSV copies of the run's own (rlscape/eval/harness.py); `config.json` is the run's.

| | |
|---|---|
| Command | `uv run python scripts/evaluate.py --config configs/e3-reward-weight-sweep-eval.yaml` |
| Git SHA | `7d0917e2d6b663a4b21d79ca94fffccdf43a25e5` |
| Fork SHA | `cad9743444626e56b9e758db1b78867e7fe75b86` |
| Config hash | `77e8a2d290a0` |
| Created (UTC) | 2026-11-19T23:08:15+00:00 |
| Seeds | 30 |

## At hour 20: mean [95% bootstrap CI] over 30 seeds

| Policy | Total level | Total XP | Net worth (gp) |
|---|---:|---:|---:|
| random | 214 [206, 223] | 80,926 [75,825, 86,282] | 16,563 [11,766, 21,834] |
| greedy_xp | 157 [157, 157] | 699,732 [696,707, 702,701] | 1,111 [1,091, 1,131] |
| greedy_wealth | 79 [69, 89] | 43,096 [26,068, 62,440] | 1,764,896 [1,671,363, 1,849,582] |
| scripted_guide | 351 [344, 357] | 97,279 [94,665, 99,791] | 129,789 [123,945, 135,909] |
| normalised_weights1-0/seed0 | 392 [390, 394] | 321,442 [305,682, 338,646] | 14,327 [11,600, 17,377] |
| normalised_weights1-0/seed1 | 388 [384, 392] | 249,909 [236,086, 266,134] | 16,543 [13,692, 19,427] |
| normalised_weights1-0/seed2 | 392 [390, 394] | 273,099 [260,881, 285,428] | 11,999 [8,159, 16,763] |
| normalised_weights1-0/seed3 | 344 [340, 348] | 259,970 [250,422, 269,603] | 3,341 [2,491, 4,424] |
| normalised_weights1-0/seed4 | 396 [392, 398] | 332,861 [316,983, 349,871] | 9,899 [8,215, 11,651] |
| normalised_weights0.75-0.25/seed0 | 273 [269, 278] | 207,292 [194,935, 220,570] | 83,956 [68,772, 100,390] |
| normalised_weights0.75-0.25/seed1 | 342 [338, 346] | 231,422 [214,976, 249,000] | 74,053 [68,363, 79,374] |
| normalised_weights0.75-0.25/seed2 | 400 [396, 404] | 366,084 [343,012, 390,109] | 16,119 [12,858, 19,621] |
| normalised_weights0.75-0.25/seed3 | 341 [338, 345] | 309,150 [296,913, 321,487] | 78,375 [69,078, 89,189] |
| normalised_weights0.75-0.25/seed4 | 393 [390, 395] | 302,896 [290,039, 316,033] | 123,656 [117,759, 130,312] |
| normalised_weights0.5-0.5/seed0 | 294 [289, 300] | 285,286 [281,733, 288,816] | 1,168,462 [1,106,558, 1,228,183] |
| normalised_weights0.5-0.5/seed1 | 278 [270, 285] | 247,241 [240,425, 255,802] | 960,631 [857,754, 1,062,189] |
| normalised_weights0.5-0.5/seed2 | 250 [243, 256] | 124,472 [117,594, 131,631] | 107,521 [100,459, 114,980] |
| normalised_weights0.5-0.5/seed3 | 243 [240, 246] | 140,354 [134,241, 146,506] | 132,098 [127,398, 136,893] |
| normalised_weights0.5-0.5/seed4 | 251 [243, 258] | 346,063 [336,933, 355,247] | 569,915 [541,245, 597,607] |
| normalised_weights0.25-0.75/seed0 | 166 [165, 167] | 378,318 [376,714, 379,798] | 931,714 [925,141, 936,799] |
| normalised_weights0.25-0.75/seed1 | 162 [160, 164] | 379,467 [376,838, 382,030] | 904,847 [896,376, 912,883] |
| normalised_weights0.25-0.75/seed2 | 201 [199, 203] | 349,367 [347,749, 351,073] | 806,006 [802,349, 809,511] |
| normalised_weights0.25-0.75/seed3 | 155 [152, 157] | 298,761 [297,562, 300,017] | 726,221 [721,851, 729,928] |
| normalised_weights0.25-0.75/seed4 | 156 [155, 156] | 298,531 [298,089, 298,974] | 727,282 [726,217, 728,382] |
| normalised_weights0-1/seed0 | 35 [35, 36] | 1,509 [1,470, 1,549] | 4,116,824 [4,051,621, 4,173,689] |
| normalised_weights0-1/seed1 | 45 [41, 49] | 3,284 [2,486, 4,142] | 2,592,189 [2,540,539, 2,636,232] |
| normalised_weights0-1/seed2 | 45 [41, 50] | 3,421 [2,382, 4,878] | 4,025,711 [3,966,051, 4,081,916] |
| normalised_weights0-1/seed3 | 38 [37, 39] | 1,871 [1,716, 2,050] | 3,939,154 [3,875,592, 3,999,891] |
| normalised_weights0-1/seed4 | 41 [38, 44] | 2,437 [2,016, 2,919] | 4,014,939 [3,948,039, 4,074,474] |

Files:
- `summary.csv`: per policy, checkpoint hour and metric, the mean over seeds, its 95% CI and the standard deviation;
- `checkpoints.csv`: each seed's metrics at each checkpoint (hour 0 is the fresh character);
- `episodes.csv`: each episode's decisions, reward sums, final metrics, deaths, most chosen options and wall time (the only column that changes between identical runs).
- `decisions.csv.gz`: every episode's trace, a row per decision: the game tick it ended at, its option and why it ended, and the total level and net worth after it.
