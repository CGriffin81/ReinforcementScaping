"""E2's rung 2: pick the sweep's best variant by evaluated reward, and test it against random, paired by seed.

Reads the committed evaluation summary (`results/summary/e2-ppo-sanity-ladder/episodes.csv` and `checkpoints.csv`,
written by `scripts/publish_summary.py`), so it needs no runs. A trained policy's label is `<variant>/seed<k>`.

- **The best variant** has the highest mean episode reward (w_s·r_skill + w_b·r_wealth at the env's weights) over all
  its seeds' episodes (OQ-65 (2)).
- **Against random and the guide:** each trained policy's paired difference on the same evaluation seeds, for the
  episode reward and the three metrics at hour 20, with a percentile-bootstrap 95% CI over seeds
  (`rlscape/eval/harness.py`'s `bootstrap_ci`).
- **The rung passes** when, for every seed of the best variant, the reward difference's CI against random is above 0.

Writes `results/summary/e2-ppo-sanity-ladder/rung2/` (variants.csv, paired.csv, README.md).

Usage:
    uv run python scripts/e2_rung2.py
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from rlscape.eval.harness import METRICS, N_BOOT, REPO, bootstrap_ci

EXPERIMENT = "e2-ppo-sanity-ladder"
SUMMARY = REPO / "results" / "summary" / EXPERIMENT
BASELINES = ("random", "scripted_guide")
MEASURES = ("reward",) + tuple(METRICS)


def outcomes(episodes: pd.DataFrame, checkpoints: pd.DataFrame) -> pd.DataFrame:
    """One row per (policy, seed): the episode's reward and its metrics at the last checkpoint."""
    last = checkpoints[checkpoints.hour == checkpoints.hour.max()][["policy", "seed", *METRICS]]
    return episodes[["policy", "seed", "reward"]].merge(last, on=["policy", "seed"], validate="one_to_one")


def variants(table: pd.DataFrame) -> pd.DataFrame:
    trained = table[~table.policy.isin(BASELINES)].copy()
    trained["variant"] = trained.policy.str.rsplit("/", n=1).str[0]
    rows = []
    for variant, group in trained.groupby("variant"):
        per_seed = group.groupby("policy").reward.mean()
        rows.append({"variant": variant, "runs": len(per_seed), "episodes": len(group),
                     "reward": group.reward.mean(), "reward_by_run": " ".join(f"{v:.2f}" for v in per_seed),
                     **{m: group[m].mean() for m in METRICS}})
    return pd.DataFrame(rows).sort_values("reward", ascending=False, ignore_index=True)


def paired(table: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    wide = {m: table.pivot(index="seed", columns="policy", values=m) for m in MEASURES}
    rows = []
    for policy in [p for p in table.policy.unique() if p not in BASELINES]:
        for against in BASELINES:
            for m in MEASURES:
                both = wide[m][[policy, against]].dropna()
                diff = (both[policy] - both[against]).to_numpy()
                low, high = bootstrap_ci(diff, rng, N_BOOT)
                rows.append({"policy": policy, "against": against, "measure": m, "seeds": len(diff),
                             "mean_difference": diff.mean(), "ci_low": low, "ci_high": high})
    return pd.DataFrame(rows)


def readme(best: str, ranked: pd.DataFrame, diffs: pd.DataFrame, meta: dict, passed: bool) -> str:
    lines = [f"# {EXPERIMENT}: rung 2, PPO against random", "",
             "By `scripts/e2_rung2.py` from this experiment's evaluation summary (the folder above: "
             f"`configs/e2-ppo-sanity-ladder-eval.yaml`, git `{meta['git_sha'][:7]}`, {meta['seeds']} seeds, "
             "sampled actions). Reward is w_s·r_skill + w_b·r_wealth at the env's weights "
             f"{tuple(meta['reward_weights'])}.", "",
             "## The variants, by mean episode reward over their runs", "",
             "| Variant | Runs | Reward | By run | Total level | Total XP | Net worth (gp) |",
             "|---|---:|---:|---|---:|---:|---:|"]
    for r in ranked.itertuples():
        lines.append(f"| {r.variant} | {r.runs} | {r.reward:.2f} | {r.reward_by_run} | {r.total_level:.0f} | "
                     f"{r.total_xp:,.0f} | {r.net_worth:,.0f} |")
    lines += ["", f"**The best variant is `{best}`.**", "",
              "## Its runs against the baselines: mean paired difference [95% bootstrap CI] over seeds", "",
              "| Run | Against | Reward | Total level | Total XP | Net worth (gp) |", "|---|---|---:|---:|---:|---:|"]
    for (policy, against), group in diffs[diffs.policy.str.startswith(best + "/")].groupby(["policy", "against"]):
        cell = {r.measure: r for r in group.itertuples()}
        fmt = {"reward": "{:+.2f}", "total_level": "{:+.0f}", "total_xp": "{:+,.0f}", "net_worth": "{:+,.0f}"}
        cells = [f"{fmt[m].format(cell[m].mean_difference)} [{fmt[m].format(cell[m].ci_low)}, "
                 f"{fmt[m].format(cell[m].ci_high)}]" for m in MEASURES]
        lines.append(f"| {policy.rsplit('/', 1)[1]} | {against} | " + " | ".join(cells) + " |")
    lines += ["", f"**Rung 2 {'passes' if passed else 'fails'}:** every run of the best variant must have a reward "
              "difference against random whose CI is above 0.", "",
              "Files: `variants.csv` (every variant's means), `paired.csv` (every trained run against random and the "
              "guide, on every measure).", ""]
    return "\n".join(lines)


def main() -> None:
    episodes = pd.read_csv(SUMMARY / "episodes.csv")
    checkpoints = pd.read_csv(SUMMARY / "checkpoints.csv")
    config = json.loads((SUMMARY / "config.json").read_text(encoding="utf-8"))
    table = outcomes(episodes, checkpoints)
    ranked = variants(table)
    best = ranked.variant.iloc[0]
    diffs = paired(table, np.random.default_rng(0))
    vs_random = diffs[diffs.policy.str.startswith(best + "/") & (diffs.against == "random")
                      & (diffs.measure == "reward")]
    passed = bool((vs_random.ci_low > 0).all())
    out = SUMMARY / "rung2"
    out.mkdir(exist_ok=True)
    ranked.to_csv(out / "variants.csv", index=False, lineterminator="\n")
    diffs.to_csv(out / "paired.csv", index=False, lineterminator="\n")
    meta = {"git_sha": config["git_sha"], "seeds": len(config["config"]["seeds"]),
            "reward_weights": config["config"]["reward_weights"]}
    (out / "README.md").write_text(readme(best, ranked, diffs, meta, passed), encoding="utf-8", newline="\n")
    print(f"best variant {best}; rung 2 {'passes' if passed else 'fails'} -> {out}")


if __name__ == "__main__":
    main()
