"""Rebuild the report's figures and tables from the summaries committed to results/summary/ (ROADMAP: "every figure
and table is rebuilt by one script"), with no training, evaluation or server. A figure whose experiments aren't
published yet is skipped, and the script says so.

Writes to --out (default results/figures/, git-ignored) each figure as <name>.pdf (for the report) and <name>.png,
with its plotted values as <name>.csv (its table view), and the measures' tables (rlscape/analysis/measures.py):
- `verdicts.csv` and `changepoints.csv`: each run's, under OQ-82 (c)'s rule and OQ-78 (a)'s;
- `discovery.csv`: each run's (OQ-76);
- `hypervolume.csv` and `hypervolume_per_seed.csv` (OQ-77);
- `training_cost_per_seed.csv` and `training_cost.csv`: E5's training cost against E3's (ROADMAP's E5). Per training
  seed, what the front `hypervolume_per_seed.csv` scores cost to train: E3's five agents at that seed, one per
  weighting, or E5's one agent. That is its runs, decisions (the SMDP's env steps), episodes and wall hours. Per method,
  the mean front's cost with a 95% CI over the seeds, and the totals;
- `sample_efficiency.csv`: each run's decisions to match the best greedy baseline at its weighting (OQ-84);
- `milestones.csv` and `milestones_summary.csv`: each evaluation episode's hours to 50% and 100% of E1's ideal point
  on each objective, and per series the share that got there and the median (OQ-83);
- `consistency.csv`: per trained series, the mean pairwise Jensen–Shannon divergence of its seeds' mixes (OQ-85);
- `rq5_walking.csv` and `rq5_walking_summary.csv`: RQ5's click-ahead bound (OQ-87 (a)), each evaluation episode's
  shares of game time on foot, in the walker's overhead and on transports, and per series their mean and CI;
- `sim_to_real_families.csv` (the report's body), `sim_to_real_cases.csv` (its appendix) and `sim_to_real_drops.csv`:
  the calibration gate's cases against sim-v1.2 (rlscape/analysis/sim_to_real.py), from `results/summary/sim-to-real/`
  (scripts/sim_to_real.py);
- `gem_store_rounds_per_seed.csv` and `gem_store_rounds.csv`: E3's first round beside its rerun at the mixed
  weightings, for the discussion (OQ-92 (b)): per trained policy, then per series and round with a CI over the
  training seeds, the hour-20 total level and net worth, the normalised gains and the share of game time buying
  uncut emeralds at the Gem Store. The first round (`e3-reward-weight-sweep-bootstrap`) is the earlier trainer's,
  evaluated on sim v1.3; nothing else reads it.

The figures:
- `learning_e3`, `learning_rq4`: learning curves with CIs and changepoints (RQ2; RQ4 against E3's (.5, .5));
- `progress`: total level and net worth at the checkpoints, E3's agents against E1's baselines (RQ1);
- `time_e3`, `time_rq4`: time allocation across training (RQ2, H2; RQ4);
- `mix`: each policy's time allocation in evaluation (H2);
- `discovery`: when each activity is discovered, E3's (.5, .5) against PPO + RND (H3);
- `pareto`: E3's agents and E5's weight-conditioned one, with E1's baselines and the hypervolumes (RQ3);
- `entropy`: the policy's entropy across training.

Usage:
    uv run python scripts/figures.py
    uv run python scripts/figures.py --summary results/summary --out results/figures
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from rlscape.analysis import figures as fg
from rlscape.analysis import measures as ms
from rlscape.analysis import sim_to_real as s2r
from rlscape.analysis.activities import OTHER
from rlscape.eval.harness import REPO

E1, E3, E4, E5 = "e1-baselines", "e3-reward-weight-sweep", "e4-rnd-exploration", "e5-weight-conditioned-ppo"
E6A, E6B = "e6a-discount-sweep", "e6b-pbrs-shaping"
TRAINED = (E3, E4, E6A, E6B, E5)
E3_FIRST = "e3-reward-weight-sweep-bootstrap"  # E3's first round: only the Gem Store table reads it (OQ-92 (b))
GEM_STORE = "buy_shop_1621"  # uncut emeralds at Hervi's Gem Store, the Gem Store loop's purchase (OQ-57 (a))
MIXED = ("normalised_weights0.75-0.25", "normalised_weights0.5-0.5", "normalised_weights0.25-0.75")
WEIGHTINGS = {"normalised_weights1-0": (1.0, 0.0), "normalised_weights0.75-0.25": (0.75, 0.25),
              "normalised_weights0.5-0.5": (0.5, 0.5), "normalised_weights0.25-0.75": (0.25, 0.75),
              "normalised_weights0-1": (0.0, 1.0)}
BASELINES = {"scripted_guide": "guide", "greedy_xp": "greedy XP/hr", "greedy_wealth": "greedy GP/hr",
             "random": "random"}
REFERENCE = "E3 (.5, .5)"  # E4, E6a and E6b are compared with it (E6a: it's the γ_hr 0.99 arm)
COLORS = {"E3 (1, 0)": fg.BLUE, "E3 (.75, .25)": fg.ORANGE, "E3 (.5, .5)": fg.AQUA, "E3 (.25, .75)": fg.YELLOW,
          "E3 (0, 1)": fg.MAGENTA, "PPO + RND": fg.GREEN, "γ_hr 0.5": fg.VIOLET, "γ_hr 0.9": fg.ORANGE,
          "PBRS": fg.BLUE, "weight-conditioned": fg.ORANGE}
METHODS = {"E3: an agent per weighting": fg.BLUE, "E5: one weight-conditioned agent": fg.ORANGE}
RQ4 = (("E4: an exploration bonus", ("PPO + RND",)),
       ("E6a: γ_hr (E3 at 0.99)", ("γ_hr 0.9", "γ_hr 0.5")),  # short: a longer title runs into E6b's
       ("E6b: potential-based shaping", ("PBRS",)))


def weighting(u: tuple[float, float]) -> str:
    def short(x: float) -> str:
        return f"{x:g}".removeprefix("0") if 0 < x < 1 else f"{x:g}"
    return f"({short(u[0])}, {short(u[1])})"


def series_name(experiment: str, variant: str) -> str:
    """A run's or an evaluated policy's series: E3's by weighting, the others by what they change."""
    if experiment == E3:
        return f"E3 {weighting(WEIGHTINGS[variant])}"
    if experiment == E6A:
        return f"γ_hr {variant.removeprefix('gamma_hr')}"
    return {E4: "PPO + RND", E6B: "PBRS", E5: "weight-conditioned"}.get(experiment, f"{experiment} {variant}")


class Summaries:
    """The committed summaries under `root`, each experiment's that's published."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def _read(self, path: Path) -> pd.DataFrame | None:
        """The table, or its gzipped copy (`learning_curves.csv.gz` from 2026-11-16; E2's is plain)."""
        for p in (path, path.with_name(path.name + ".gz")):
            if p.exists():
                return pd.read_csv(p, keep_default_na=False, dtype={"variant": str})
        return None

    def training(self, table: str) -> pd.DataFrame | None:
        """A training table of every experiment that has one, `variant` replaced by the run's series."""
        frames = []
        for experiment in TRAINED:
            frame = self._read(self.root / experiment / "training" / table)
            if frame is not None:
                frames.append(frame.assign(variant=[series_name(experiment, v) for v in frame["variant"]]))
        return pd.concat(frames, ignore_index=True) if frames else None

    def evaluation(self, experiment: str, table: str) -> pd.DataFrame | None:
        return self._read(self.root / experiment / table)

    def runs(self, experiment: str) -> pd.DataFrame | None:
        """An experiment's trained runs (`training/runs.csv`): each run's decisions, episodes and wall time."""
        return self._read(self.root / experiment / "training" / "runs.csv")


def trained_series(experiment: str, policies: pd.Series) -> pd.Series:
    """Each evaluated policy's series (a baseline keeps its name; E5's adds its weighting)."""
    def one(policy: str) -> str:
        variant, seed, u = ms.parse_label(policy)
        if seed is None:
            return variant
        name = series_name(experiment, variant)
        return f"E5 at {weighting((u, 1 - u))}" if experiment == E5 and u is not None else name
    return policies.map(one)


def best_baseline(e1: pd.DataFrame, u: tuple[float, float], among: tuple[str, ...] = tuple(BASELINES)
                  ) -> tuple[str, float]:
    """E1's best baseline `among` these at weighting u, by its mean value on the learning curves' scale."""
    g = ms.gains(e1[e1["policy"].isin(among)])
    values = (u[0] * g["skill"] + u[1] * g["wealth"]).groupby(g["policy"]).mean()
    best = values.idxmax()
    return f"best of E1: {BASELINES.get(best, best)}", float(values[best])


def series_weighting(series: str) -> tuple[float, float] | None:
    """The weighting a series trains at: E3's own, (.5, .5) for E4, E6a and E6b; None for E5's, which varies."""
    for variant, u in WEIGHTINGS.items():
        if series == series_name(E3, variant):
            return u
    return (0.5, 0.5) if series in {"PPO + RND", "γ_hr 0.5", "γ_hr 0.9", "PBRS"} else None


def save_table(table: pd.DataFrame, path: Path) -> None:
    table.to_csv(path, index=False, lineterminator="\n")


ROUND_METRICS = ("total_level", "net_worth", "skill", "wealth", "gem_store_share")


def gem_store_round(data: Summaries, experiment: str, label: str) -> pd.DataFrame | None:
    """One round of E3's evaluation at the mixed weightings (OQ-92 (b)), a row per trained policy: its means over the
    evaluation seeds of the last checkpoint's total level and net worth, of the normalised gains and of the share of
    game time on the Gem Store's purchase. None if the round's summary or its trace isn't published."""
    checkpoints, episodes, trace = (data.evaluation(experiment, t) for t in ("checkpoints.csv", "episodes.csv",
                                                                             "decisions.csv.gz"))
    if checkpoints is None or episodes is None or trace is None:
        return None
    last = checkpoints[checkpoints["hour"] == checkpoints["hour"].max()]
    table = last.groupby("policy").agg(episodes=("seed", "size"), total_level=("total_level", "mean"),
                                       net_worth=("net_worth", "mean"))
    table = table.join(ms.gains(episodes).groupby("policy")[["skill", "wealth"]].mean())
    table = table.join(ms.option_share(trace, GEM_STORE).groupby("policy")["share"].mean().rename("gem_store_share"))
    table = table.reset_index()
    parsed = [ms.parse_label(p) for p in table["policy"]]
    table["variant"], table["train_seed"] = [p[0] for p in parsed], [p[1] for p in parsed]
    table = table[table["variant"].isin(MIXED)].astype({"train_seed": int})
    meta = json.loads((data.root / experiment / "config.json").read_text(encoding="utf-8"))
    table["series"] = [series_name(E3, v) for v in table["variant"]]
    table["order"] = [MIXED.index(v) for v in table["variant"]]
    table = table.assign(round=label, git_sha=meta["git_sha"][:7]).sort_values(["order", "train_seed"])
    return table[["round", "series", "train_seed", "policy", "episodes", *ROUND_METRICS, "git_sha"]]


def round_summary(per_seed: pd.DataFrame) -> pd.DataFrame:
    """Per series and round, beside each other: each metric's mean over the training seeds and its 95% CI."""
    keys = ["series", "round"]
    table = per_seed.groupby(keys, sort=False).agg(seeds=("train_seed", "size"), git_sha=("git_sha", "first"))
    for metric in ROUND_METRICS:
        stats = ms.over_seeds(per_seed, keys, metric).set_index(keys)
        table[metric], table[f"{metric}_low"], table[f"{metric}_high"] = (stats[c] for c in ("mean", "ci_low",
                                                                                             "ci_high"))
    order = [series_name(E3, v) for v in MIXED]  # a series' two rounds next to each other, the first round first
    return table.reset_index().sort_values("series", key=lambda s: s.map(order.index), kind="stable")


def training_cost(data: Summaries) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """E5's training cost against E3's, per front: a row per method and training seed with the runs that train the
    front (E3's five at that seed, E5's one), their decisions, episodes and wall hours, and the sims' commits; then per
    method the mean front's decisions and wall hours (with a 95% CI over the seeds) and the totals. None unless both
    training summaries are published. Wall time is each run's own, and the queue trained five runs at once on one
    machine, so it's comparable between E3's runs and E5's, which shared that load, but it isn't a run's speed alone."""
    runs = {method: data.runs(experiment) for method, experiment in zip(METHODS, (E3, E5))}
    if any(r is None for r in runs.values()):
        return None
    rows = []
    for method, table in runs.items():
        for seed, group in table.groupby("seed"):
            rows.append({"method": method, "train_seed": int(seed), "runs": len(group),
                         "decisions": int(group["decisions"].sum()), "episodes": int(group["episodes"].sum()),
                         "wall_hours": group["wall_seconds"].sum() / 3600,
                         "git_sha": " ".join(sorted({sha[:7] for sha in group["git_sha"]}))})
    per_front = pd.DataFrame(rows)
    cost = per_front.groupby("method", sort=False).agg(seeds=("train_seed", "size"),
                                                       runs_per_front=("runs", "mean"),
                                                       decisions_per_front=("decisions", "mean"))
    wall = ms.over_seeds(per_front, ["method"], "wall_hours").set_index("method")
    cost["wall_hours_per_front"], cost["wall_hours_low"], cost["wall_hours_high"] = (wall[c] for c in (
        "mean", "ci_low", "ci_high"))
    totals = per_front.groupby("method", sort=False)[["runs", "decisions", "wall_hours"]].sum()
    return per_front, cost.join(totals).reset_index()


def build(summary: Path, out: Path, curve_bin: int = ms.CURVE_BIN) -> list[str]:
    """Every figure whose summaries are published, into `out`; returns their names. `curve_bin` is the learning
    curves' bin (OQ-78's 20,000 decisions; a test's tiny runs need a smaller one)."""
    data, made, skipped = Summaries(summary), [], []
    out.mkdir(parents=True, exist_ok=True)

    def save(name: str, fig, table: pd.DataFrame) -> None:
        for kind in ("pdf", "png"):
            fig.savefig(out / f"{name}.{kind}")
        plt.close(fig)
        table.to_csv(out / f"{name}.csv", index=False, lineterminator="\n")
        made.append(name)

    def attempt(name: str, needs: str, make: Callable[[], None]) -> None:
        try:
            make()
        except _Missing:
            skipped.append(f"{name} (needs {needs})")

    e1 = data.evaluation(E1, "episodes.csv")
    curves, bins, options = (data.training(t) for t in ("learning_curves.csv", "behaviour_bins.csv",
                                                         "behaviour_options.csv.gz"))
    present = set(curves["variant"]) if curves is not None else set()
    bins = ms.full_bins(bins) if bins is not None else None  # a run's half-empty last bin left out

    # --- learning curves (OQ-78) ---
    if curves is not None:
        binned = ms.binned_curve(curves, curve_bin)
        carried = ms.carried_curve(binned, curve_bin)  # the mean over seeds: an empty bin keeps its last value
        stats = ms.over_seeds(carried, ["variant", "to_step"], "value").merge(
            carried.groupby(["variant", "to_step"], as_index=False)["carried"].sum(), on=["variant", "to_step"]
        ).rename(columns={"variant": "series"})
        verdicts, changes = (t.rename(columns={"variant": "series"}) for t in ms.run_changes(binned,
                                                                                               every=curve_bin))
        save_table(verdicts, out / "verdicts.csv")
        save_table(changes, out / "changepoints.csv")
        if e1 is not None:  # OQ-84: the decisions to match the best greedy baseline at the run's weighting
            targets = {s: best_baseline(e1, u, ("greedy_xp", "greedy_wealth"))[1] for s in present
                       if (u := series_weighting(s)) is not None}
            efficiency = ms.sample_efficiency(binned, targets).rename(columns={"variant": "series"})
            save_table(efficiency, out / "sample_efficiency.csv")

    def learning_e3():
        e3 = [series_name(E3, v) for v in WEIGHTINGS if series_name(E3, v) in present]
        _need(e3)
        refs = {s: best_baseline(e1, WEIGHTINGS[v]) for v in WEIGHTINGS if (s := series_name(E3, v)) in e3} \
            if e1 is not None else None
        fig = fg.learning_curves(stats, changes, verdicts, [(s, [s]) for s in e3], COLORS, refs, cols=3)
        save("learning_e3", fig, stats[stats["series"].isin(e3)])

    def learning_rq4():
        panels = [(title, [REFERENCE, *[s for s in series if s in present]]) for title, series in RQ4
                  if any(s in present for s in series)]
        _need(panels and REFERENCE in present)
        refs = {title: best_baseline(e1, (0.5, 0.5)) for title, _ in panels} if e1 is not None else None
        fig = fg.learning_curves(stats, changes, verdicts, panels, COLORS, refs)
        shown = {s for _, series in panels for s in series}
        save("learning_rq4", fig, stats[stats["series"].isin(shown)])

    attempt("learning_e3", "E3's training summary", learning_e3)
    attempt("learning_rq4", "E3's and E4's, E6a's or E6b's training summaries", learning_rq4)

    # --- time allocation, discovery (OQ-76) and entropy ---
    shares = ms.time_shares(options, bins) if options is not None and bins is not None else None
    mixes, reached, walks = [], [], []
    for experiment in TRAINED:
        trace = data.evaluation(experiment, "decisions.csv.gz")
        if trace is None:
            continue
        walks.append(ms.walking(trace))  # RQ5's bound (OQ-87 (a)); empty for a trace without the walk counter
        mix = ms.trace_shares(trace)
        mixes.append(mix.assign(variant=trained_series(experiment, mix["policy"]),
                                train_seed=[ms.parse_label(p)[1] for p in mix["policy"]]))
        checkpoints = data.evaluation(experiment, "checkpoints.csv")
        if checkpoints is not None:  # OQ-83
            table = ms.milestones(trace, checkpoints)
            reached.append(table.assign(series=trained_series(experiment, table["policy"])))
    if reached:
        reached = pd.concat(reached, ignore_index=True).drop_duplicates(["policy", "seed", "milestone"])
        save_table(reached, out / "milestones.csv")  # each experiment's evaluation has E1's baselines too
        save_table(ms.milestone_summary(reached, ["series"]), out / "milestones_summary.csv")
    if mixes:
        per_policy = pd.concat(mixes, ignore_index=True).drop_duplicates(["policy", "seed", "activity"])
        trained = per_policy[per_policy["train_seed"].notna()]
        if len(trained):  # OQ-85
            save_table(ms.consistency(trained).rename(columns={"variant": "series"}), out / "consistency.csv")
    mix = per_policy.groupby(["variant", "activity"], as_index=False)["share"].mean() if mixes else None
    overall = pd.concat([t.groupby("activity")["share"].mean() for t in (shares, mix) if t is not None], axis=1) \
        if shares is not None or mix is not None else None
    kept = overall.mean(axis=1).drop(OTHER).nlargest(7).index.tolist() if overall is not None else []
    colors = fg.activity_colors([*kept, "other"])

    if shares is not None:
        mean = shares.groupby(["variant", "to_step", "activity"], as_index=False)["share"].mean()
        folded = fg.fold(mean, kept, ["variant", "to_step"]).rename(columns={"variant": "series"})
        mean = mean.rename(columns={"variant": "series"})
        found = ms.discovery(shares).rename(columns={"variant": "series"})
        found.to_csv(out / "discovery.csv", index=False, lineterminator="\n")

    def time_e3():
        e3 = [s for v in WEIGHTINGS if (s := series_name(E3, v)) in present]
        _need(shares is not None and e3)
        fig = fg.time_allocation(folded, [(s, s) for s in e3], colors, cols=3)
        save("time_e3", fig, mean[mean["series"].isin(e3)])

    def time_rq4():
        rq4 = [s for _, series in RQ4 for s in series if s in present]
        _need(shares is not None and rq4 and REFERENCE in present)
        shown = [REFERENCE, *rq4]
        fig = fg.time_allocation(folded, [(s, s) for s in shown], colors, cols=3)
        save("time_rq4", fig, mean[mean["series"].isin(shown)])

    def discovery():
        _need(shares is not None and {REFERENCE, "PPO + RND"} <= present)
        series = [REFERENCE, "PPO + RND"]
        fig = fg.discovery_timeline(found, series, COLORS, shares["to_step"].max())
        save("discovery", fig, found[found["series"].isin(series)])

    def entropy():
        _need(bins is not None)
        stats_e = ms.over_seeds(bins, ["variant", "to_step"], "entropy").rename(columns={"variant": "series"})
        panels = [("E3", [s for v in WEIGHTINGS if (s := series_name(E3, v)) in present])]
        panels += [(title, [REFERENCE, *[s for s in series if s in present]]) for title, series in RQ4
                   if any(s in present for s in series)]
        panels = [p for p in panels if p[1]]
        fig = fg.entropy(stats_e, panels, COLORS)
        save("entropy", fig, stats_e)

    attempt("time_e3", "E3's training summary", time_e3)
    attempt("time_rq4", "E3's and E4's, E6a's or E6b's training summaries", time_rq4)
    attempt("discovery", "E3's and E4's training summaries", discovery)
    attempt("entropy", "a training summary", entropy)

    def mix_figure():
        _need(mix is not None)
        order = [*BASELINES, *[series_name(E3, v) for v in WEIGHTINGS],
                 *[s for _, series in RQ4 for s in series], *[f"E5 at {weighting(u)}" for u in WEIGHTINGS.values()]]
        rows = [(BASELINES.get(v, v), v) for v in order if v in set(mix["variant"])]
        folded_mix = mix.assign(activity=mix["activity"].where(mix["activity"].isin(kept), "other")) \
            .groupby(["variant", "activity"], as_index=False)["share"].sum()
        fig = fg.activity_mix(folded_mix, rows, colors)
        save("mix", fig, mix)

    attempt("mix", "an evaluation summary with its traces", mix_figure)

    # --- RQ1 and RQ3 from E3's (and E5's) evaluations ---
    e3_eval = data.evaluation(E3, "checkpoints.csv")

    def progress():
        _need(e3_eval is not None)
        tables = {}
        for metric, title in (("total_level", "Total level"), ("net_worth", "Net worth (gp)")):
            table = ms.progress(e3_eval, metric)
            table["variant"] = table["variant"].map(lambda v: series_name(E3, v) if v in WEIGHTINGS else v)
            tables[title] = table
        fig = fg.progress(tables, BASELINES, COLORS, list(BASELINES))
        save("progress", fig, pd.concat([t.assign(metric=m) for m, t in tables.items()], ignore_index=True))

    def pareto():
        e3_episodes = data.evaluation(E3, "episodes.csv")
        _need(e3_episodes is not None and e1 is not None)
        pts = [ms.points(ms.gains(e3_episodes))]
        e5_episodes = data.evaluation(E5, "episodes.csv")
        if e5_episodes is not None:
            pts.append(ms.points(ms.gains(e5_episodes)))
        pts = pd.concat(pts, ignore_index=True)
        per_seed, hv = ms.hypervolumes(pts, {"E3: an agent per weighting": list(WEIGHTINGS),
                                             "E5: one weight-conditioned agent": ["e5"]})
        per_seed.to_csv(out / "hypervolume_per_seed.csv", index=False, lineterminator="\n")
        hv.to_csv(out / "hypervolume.csv", index=False, lineterminator="\n")
        methods = {}
        for method, keys in (("E3: an agent per weighting", ["variant"]), ("E5: one weight-conditioned agent",
                                                                           ["u"])):
            mine = pts[pts["variant"].isin(list(WEIGHTINGS) if method.startswith("E3") else ["e5"])]
            if mine.empty:
                continue
            skill, wealth = (ms.over_seeds(mine, keys, m).set_index(keys) for m in ("skill", "wealth"))
            table = pd.DataFrame({"skill": skill["mean"], "skill_low": skill["ci_low"],
                                  "skill_high": skill["ci_high"], "wealth": wealth["mean"],
                                  "wealth_low": wealth["ci_low"], "wealth_high": wealth["ci_high"]}).reset_index()
            if method.startswith("E3"):
                table["label"] = table["variant"].map(lambda v: weighting(WEIGHTINGS[v]))
            methods[method] = table
        fig = fg.pareto(methods, METHODS, ms.points(ms.gains(e1)), hv, BASELINES)
        save("pareto", fig, pd.concat([t.assign(method=m) for m, t in methods.items()], ignore_index=True))

    attempt("progress", "E3's evaluation summary", progress)
    attempt("pareto", "E3's evaluation summary and E1's", pareto)

    # --- E5's training cost against E3's (ROADMAP's E5), per front as the hypervolumes are ---
    cost = training_cost(data)
    if cost is not None:
        save_table(cost[0], out / "training_cost_per_seed.csv")
        save_table(cost[1], out / "training_cost.csv")
        print("made     training_cost tables")
    else:
        skipped.append("training_cost tables (needs E3's and E5's training summaries)")

    # --- OQ-92 (b): E3's first round beside the rerun at the mixed weightings, for the discussion ---
    rounds = [gem_store_round(data, experiment, label) for label, experiment in (("first round", E3_FIRST),
                                                                                 ("rerun", E3))]
    if all(r is not None for r in rounds):
        per_seed = pd.concat(rounds, ignore_index=True)
        save_table(per_seed, out / "gem_store_rounds_per_seed.csv")
        save_table(round_summary(per_seed), out / "gem_store_rounds.csv")
        print("made     gem_store_rounds tables")
    else:
        skipped.append(f"gem_store_rounds tables (needs both rounds of E3's evaluation: {E3_FIRST} and {E3})")

    # --- RQ5's click-ahead bound (OQ-1 (C′), OQ-87 (a)): the evaluated policies' walking ---
    walks = [w for w in walks if len(w)]
    if walks:
        per_episode = pd.concat(walks, ignore_index=True).drop_duplicates(["policy", "seed"])  # baselines repeat
        save_table(per_episode, out / "rq5_walking.csv")
        walk_summary = ms.walking_summary(per_episode)
        walk_summary["variant"] = walk_summary["variant"].map(
            lambda v: series_name(E3, v) if v in WEIGHTINGS else BASELINES.get(v, v))
        save_table(walk_summary, out / "rq5_walking_summary.csv")
        print("made     rq5_walking tables")
    else:
        skipped.append("rq5_walking tables (needs an evaluation trace with the walk counter)")

    # --- the sim-to-real tables: the calibration gate's cases against sim-v1.2 ---
    gate = summary / "sim-to-real"
    if (gate / "cases.csv").exists():
        cases = pd.read_csv(gate / "cases.csv", keep_default_na=False)
        speed = pd.read_csv(gate / "speed_check.csv", keep_default_na=False) \
            if (gate / "speed_check.csv").exists() else None
        save_table(s2r.family_table(cases, speed), out / "sim_to_real_families.csv")
        save_table(s2r.case_table(cases), out / "sim_to_real_cases.csv")
        if (gate / "drops.csv").exists():
            save_table(s2r.drops_row(pd.read_csv(gate / "drops.csv", keep_default_na=False)),
                       out / "sim_to_real_drops.csv")
        print("made     sim_to_real tables")
    else:
        skipped.append("sim_to_real tables (needs results/summary/sim-to-real, from scripts/sim_to_real.py)")
    for name in made:
        print(f"made     {name}")
    for name in skipped:
        print(f"skipped  {name}")
    return made


class _Missing(Exception):
    """A figure's experiments aren't all published."""


def _need(condition) -> None:
    if not condition:
        raise _Missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--summary", type=Path, default=REPO / "results" / "summary")
    parser.add_argument("--out", type=Path, default=REPO / "results" / "figures")
    args = parser.parse_args()
    build(args.summary, args.out)


if __name__ == "__main__":
    main()
