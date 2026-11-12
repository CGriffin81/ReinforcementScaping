# e2-ppo-sanity-ladder: rung 1, the toy env

SMDP MaskablePPO on the synthetic three-option env (`rlscape/envs/toy.py`, OQ-65 (1)) against its exact optimum, 100 sampled episodes a seed. Run by `scripts/e2_toy_rung.py --config configs/e2-ppo-sanity-ladder-toy.yaml`.

Git `57a31ae0c6f53d17e308e00fdc4e0b56a83cd504`, config hash `933c7466655b`.

**The optimum** (γ_hr 0.99): 22 trainings, then work; discounted return 72.74, undiscounted 82.51.

| Seed | Discounted return | Share of the optimum | Trainings | Idles | Passes |
|---|---:|---:|---:|---:|---|
| 0 | 50.98 | 70.1% | 7.5 | 1.7 | no |
| 1 | 50.93 | 70.0% | 7.4 | 1.7 | no |

**Rung 1 fails:** every seed's mean discounted return must be at least 95% of the optimum.
