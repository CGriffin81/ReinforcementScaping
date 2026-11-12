# e2-ppo-sanity-ladder: rung 1, the toy env

SMDP MaskablePPO on the synthetic three-option env (`rlscape/envs/toy.py`, OQ-65 (1)) against its exact optimum, 100 sampled episodes a seed, after 2,000,000 decisions at GAE λ 0.99. Run by `scripts/e2_toy_rung.py --config configs/e2-ppo-sanity-ladder-toy.yaml`.

Git `32719bac2b5b002eefe84a7f0bf5f53f44bc4955`, config hash `2c3a062efea1`.

**The optimum** (γ_hr 0.99): 22 trainings, then work; discounted return 72.74, undiscounted 82.51.

| Seed | Discounted return | Share of the optimum | Trainings | Idles | Passes |
|---|---:|---:|---:|---:|---|
| 0 | 69.01 | 94.9% | 13.3 | 0.1 | no |
| 1 | 68.69 | 94.4% | 12.9 | 0.0 | no |

**Rung 1 fails:** every seed's mean discounted return must be at least 95% of the optimum.
