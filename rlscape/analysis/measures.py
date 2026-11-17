"""The analysis's measures, computed from an experiment's committed summary (rlscape.eval.publish): its training
tables (`learning_curves.csv.gz`, `behaviour_bins.csv`, `behaviour_options.csv.gz`) and its evaluation's (`episodes.csv`,
`checkpoints.csv`, `decisions.csv.gz`).

- **Learning curves** (OQ-78, Caleb, 2026-11-11): a run's mean episode reward per `CURVE_BIN` (20,000) decisions,
  the episodes binned by the decision they ended at (`binned_curve`). Its `value` is the env's reward over
  SKILL_UNIT, so 1 is what E1's ideal point (the guide's levels and greedy GP/hr's wealth, OQ-67) would score at the
  run's own weighting, whatever the weighting. For the mean over seeds, a run's empty bin keeps its last value
  (Caleb, 2026-11-16, `carried_curve`), so each bin's mean and CI are over all the seeds.
- **Sudden or gradual** (OQ-78, revised by OQ-82 (c), Caleb, 2026-11-11): changepoints by ruptures' PELT on each
  run's binned curve, a mean shift's cost (`l2`) and a BIC penalty, 2σ²·ln n, with σ the curve's noise from its
  first differences (robust to the shifts; `changepoints`).
  - **The rule** (OQ-82 (c)): the first `WARMUP` (100,000) decisions are the warm-up, and the rise from the random
    start over them is reported apart (`initial_rise`). After it, rising changepoints within `MERGE` (100,000)
    decisions of the first count as one rise, so a jump PELT splits across adjacent bins is one jump. A run learns
    *suddenly* if one rise is at least half its gain after the warm-up (the last segment's mean less the warm-up's
    last), *gradually* if it gained but no rise is that big, and has *no gain* if it ended no more than
    `NOISE_FLOOR` (2) σ above where the warm-up left it (`revised_verdict`). The floor is Claude's, within OQ-82,
    confirmed by Caleb: without it a flat run's wiggle up and back down is "sudden".
  - **OQ-78 (a)'s rule,** reported beside it (OQ-82: the report shows both): one changepoint's jump of at least half
    the total gain, from the first segment (`decided_verdict`). `run_changes` gives each run's verdicts under both.
- **Sample efficiency** (OQ-84 (a)): the decisions by the end of the first bin from which a run's curve stays at or
  above a target, the best greedy baseline's value at its weighting, for `HOLD` (5) bins, or to the run's end if
  fewer remain (`sample_efficiency`).
- **Time allocation:** each training bin's share of game time per activity (rlscape.analysis.activities), from the
  behaviour tables (`time_shares`), and each evaluation episode's from its trace (`trace_shares`).
- **Consistency across seeds** (OQ-85 (a)): the mean pairwise Jensen–Shannon divergence (bits, 0 to 1) between a
  variant's training seeds' activity mixes in evaluation, each seed's mix its episodes' mean shares, with a bootstrap
  CI over the seed pairs (`consistency`).
- **Milestones** (OQ-83 (a)): the game hours an evaluation episode takes to gain 50% and 100% of E1's ideal point on
  each objective, read from its trace (`milestones`). The trace has whole levels, so the level targets are the
  guide's 20-hour gain in whole levels, 316 (`LEVEL_TARGET`), and half of it, not SKILL_UNIT's 323.87, which counts
  progress within levels: 100% is matching the guide's 20 hours either way (Claude's, confirmed by Caleb). The wealth targets are WEALTH_UNIT's
  1,763,863 gp and half of it (net worth is exact). An episode that doesn't get there within 20 hours is censored
  at infinity, so a median over episodes is Kaplan–Meier's (every censoring is at the end).
- **Discovery** (OQ-76 (a)): an activity is discovered in the first bin (the checkpoint interval, 100,000 decisions)
  in which it takes at least `DISCOVERY_SHARE` (5%) of the training episodes' game time (`discovery`).
- **The front and its hypervolume** (OQ-77 (a)): each policy's mean 20-hour gain over the fresh character in
  normalised units (`r_skill` / SKILL_UNIT, `r_wealth` / WEALTH_UNIT; `gains`), the hypervolume of a set of policies'
  points above the reference point, the fresh character's (0, 0) (`hypervolume`), computed per training seed and
  reported as the mean with a 95% CI over the seeds (`hypervolumes`).
- **RQ5's click-ahead bound** (OQ-1 (C′), OQ-87 (a), Caleb, 2026-11-12): per evaluation episode, the shares of its game
  time on foot, in the walker's measured overhead (starting a walk and the pauses between its clicks: the most a
  perfect click-ahead could save) and on transports (`walking`), from the trace's walk counter
  (rlscape.eval.walking); per variant, a trained one's mean and CI over its training seeds (each seed's mean over the
  evaluation seeds), a baseline's over its evaluation seeds (`walking_summary`).
- **Over seeds:** `over_seeds` gives each group's mean and percentile-bootstrap 95% CI over its seeds
  (rlscape.eval.harness.bootstrap_ci, a fixed rng), the same CIs as the eval summaries.

A policy's label in an evaluation (`parse_label`) is `<variant>/seed<k>` for a trained agent (E3's
`normalised_weights0.5-0.5/seed2`, E4's `rnd/seed0`), `<variant>/seed<k>@<u>` for E5's agent at skill share u, and
a baseline's name otherwise.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from itertools import combinations

import numpy as np
import pandas as pd

from rlscape.analysis.activities import ACTIVITIES, OTHER, activity
from rlscape.envs.weights import SKILL_UNIT, WEALTH_UNIT
from rlscape.eval.harness import N_BOOT, bootstrap_ci
from rlscape.sim.engine import TICKS_PER_HOUR

CURVE_BIN = 20_000  # decisions (OQ-78)
DISCOVERY_SHARE = 0.05  # of a bin's game time (OQ-76)
REFERENCE = (0.0, 0.0)  # the fresh character's gain (OQ-77)
MIN_SEGMENT = 2  # bins: a changepoint's segments are at least 40,000 decisions long
SUDDEN = 0.5  # of the total gain, in one jump (OQ-78)
WARMUP = 100_000  # decisions: the rise from the random start (OQ-82)
MERGE = 100_000  # decisions: rising changepoints this close to a rise's first are one rise (OQ-82)
NOISE_FLOOR = 2.0  # σ: a gain after the warm-up no bigger than this many bins' noise is no gain (OQ-82, Claude's)
HOLD = 5  # bins (100,000 decisions) a run's curve stays at the target to match it (OQ-84)
LEVEL_TARGET = 316.03333333333336  # whole levels: the guide's mean 20-hour gain in E1 (OQ-83; its r_skill is 323.87)
MILESTONES = {"levels_50": ("total_level", 0.5 * LEVEL_TARGET), "levels_100": ("total_level", LEVEL_TARGET),
              "gp_50": ("net_worth", 0.5 * WEALTH_UNIT * 100_000), "gp_100": ("net_worth", WEALTH_UNIT * 100_000)}
LABEL = re.compile(r"^(?P<variant>.+)/seed(?P<seed>\d+)(?:@(?P<u>[0-9.]+))?$")
ALL_ACTIVITIES = (*ACTIVITIES, OTHER)


# --- seeds ---------------------------------------------------------------------------------------------------------

def over_seeds(frame: pd.DataFrame, keys: Sequence[str], value: str, n_boot: int = N_BOOT,
               seed: int = 0) -> pd.DataFrame:
    """Per group of `keys`: its rows' count (`seeds`), the mean of `value` and its 95% bootstrap CI."""
    rng, rows = np.random.default_rng(seed), []
    for key, group in frame.groupby(list(keys), sort=True, dropna=False):
        values = group[value].to_numpy(dtype=float)
        low, high = bootstrap_ci(values, rng, n_boot)
        rows.append({**dict(zip(keys, key if isinstance(key, tuple) else (key,))), "seeds": len(values),
                     "mean": values.mean(), "ci_low": low, "ci_high": high})
    return pd.DataFrame(rows)


# --- learning curves and changepoints ------------------------------------------------------------------------------

def binned_curve(curves: pd.DataFrame, every: int = CURVE_BIN) -> pd.DataFrame:
    """Per (variant, seed, bin): the episodes that ended in the bin, their mean reward, and its `value` (reward over
    SKILL_UNIT). `to_step` is the bin's last decision; bins with no episode ending in them are left out, and so is a
    run's last bin when the run ended less than half-way into it (E2's runs end 448 decisions into their 51st)."""
    frame = curves.assign(bin=curves["step"] // every)
    last = frame.groupby(["variant", "seed"])["step"].transform("max")
    frame = frame[~((frame["bin"] == last // every) & (last % every < every / 2))]
    binned = frame.groupby(["variant", "seed", "bin"], sort=True).agg(episodes=("reward", "size"),
                                                                       reward=("reward", "mean")).reset_index()
    binned["value"] = binned["reward"] / SKILL_UNIT
    binned["to_step"] = (binned["bin"] + 1) * every
    return binned


def carried_curve(binned: pd.DataFrame, every: int = CURVE_BIN) -> pd.DataFrame:
    """`binned_curve` for the mean over seeds (Caleb, 2026-11-16): a run's bin with no episode ending in it keeps the
    run's last value, from its first bin to its variant's last, so every bin's mean and CI are over all the variant's
    seeds. Without it, a run with long episodes (E3's first-round (0, 1) seed 1, looping) leaves most bins empty and
    the mean saws between the seeds that have one and all of them. `carried` marks the filled bins. A run's own
    changepoints, verdicts and sample efficiency use `binned_curve` as it is."""
    runs = []
    for (variant, seed), run in binned.groupby(["variant", "seed"], sort=True):
        last = int(binned.loc[binned["variant"] == variant, "bin"].max())
        filled = run.set_index("bin").reindex(pd.RangeIndex(int(run["bin"].min()), last + 1, name="bin"))
        filled["carried"] = filled["value"].isna()
        filled[["reward", "value"]] = filled[["reward", "value"]].ffill()
        filled["episodes"] = filled["episodes"].fillna(0).astype(int)
        filled["to_step"] = (filled.index + 1) * every
        runs.append(filled.reset_index().assign(variant=variant, seed=seed))
    return pd.concat(runs, ignore_index=True)[[*binned.columns, "carried"]]


def noise(y: Sequence[float]) -> float:
    """A curve's noise per bin, σ, from its first differences' median absolute deviation (robust to its shifts)."""
    y = np.asarray(y, dtype=float)
    if len(y) < 3:
        return float(y.std())
    d = np.diff(y)
    sigma = 1.4826 * float(np.median(np.abs(d - np.median(d)))) / math.sqrt(2)
    return sigma if sigma > 0 else float(y.std())


def segments(y: Sequence[float], penalty: float = 1.0, min_size: int = MIN_SEGMENT) -> tuple[list[int], list[float]]:
    """PELT's segments of a curve (the module's docstring): their starts (indices) and means. `penalty` scales the
    BIC penalty."""
    import ruptures

    y = np.asarray(y, dtype=float)
    n = len(y)
    ends = [n]
    if n >= 2 * min_size:
        sigma = noise(y) or 1e-12
        ends = ruptures.Pelt(model="l2", min_size=min_size, jump=1).fit(y).predict(pen=penalty * 2 * sigma**2
                                                                                    * math.log(n))
    starts = [0, *ends[:-1]]
    return starts, [float(y[s:e].mean()) for s, e in zip(starts, ends)]


def _verdict(gain: float, largest: float, floor: float = 0.0) -> str:
    if gain <= floor:
        return "no gain"
    return "sudden" if largest >= SUDDEN * gain else "gradual"


def decided_verdict(means: Sequence[float]) -> dict:
    """OQ-78 (a): sudden if one changepoint's jump is at least half the gain from the first segment to the last.
    `jump` is the largest jump's changepoint (its index), -1 with none."""
    jumps = np.diff(means)
    gain = means[-1] - means[0]
    largest = float(jumps.max()) if len(jumps) else 0.0
    return {"gain": gain, "largest_share": largest / gain if gain > 0 else float("nan"),
            "verdict": _verdict(gain, largest), "jump": int(jumps.argmax()) if len(jumps) else -1}


def rises(steps: Sequence[int], jumps: Sequence[float], merge: int = MERGE) -> list[list[int]]:
    """The changepoints (indices) grouped into rises: consecutive rising changepoints, each within `merge` decisions
    of its rise's first. A falling changepoint ends a rise and is in none."""
    groups, current = [], []
    for i, (step, jump) in enumerate(zip(steps, jumps)):
        if jump > 0 and current and step - steps[current[0]] <= merge:
            current.append(i)
            continue
        if current:
            groups.append(current)
        current = [i] if jump > 0 else []
    return groups + ([current] if current else [])


def revised_verdict(steps: Sequence[int], means: Sequence[float], sigma: float = 0.0, warmup: int = WARMUP,
                    merge: int = MERGE) -> dict:
    """OQ-82 (c), from a curve's changepoints (`steps`: the decision each one's segment starts at) and its segments'
    means. Changepoints at or before `warmup` are the warm-up's: the segment in force after them is where the warm-up
    leaves the run, its rise from the first segment the `initial_rise`. The gain and the rises are counted after it.
    A gain of no more than `NOISE_FLOOR` times the curve's noise per bin (`sigma`) is no gain: a flat run's wiggle up
    and back would otherwise make any rise "at least half" of a near-zero gain. `rise` is the largest rise's
    changepoints (indices), empty with none."""
    jumps = list(np.diff(means))
    w = sum(step <= warmup for step in steps)  # the warm-up's changepoints come first: steps rise
    groups = [[w + i for i in g] for g in rises(steps[w:], jumps[w:], merge)]
    sizes = [sum(jumps[i] for i in g) for g in groups]
    largest = max(sizes, default=0.0)
    gain = means[-1] - means[w]
    return {"initial_rise": means[w] - means[0], "gain": gain,
            "largest_share": largest / gain if gain > 0 else float("nan"),
            "verdict": _verdict(gain, largest, NOISE_FLOOR * sigma), "rise": groups[int(np.argmax(sizes))] if groups
            else []}


def run_changes(binned: pd.DataFrame, penalty: float = 1.0, every: int = CURVE_BIN) -> tuple[pd.DataFrame,
                                                                                                 pd.DataFrame]:
    """Each run's verdicts and each changepoint, in `value`'s units.
    - Runs: variant, seed, segments; OQ-82 (c)'s initial_rise, gain, largest_share (the largest rise's) and verdict;
      and OQ-78 (a)'s gain_oq78a, largest_share_oq78a and verdict_oq78a.
    - Changepoints: variant, seed, step (the decision its segment starts at), before, after, jump; `warmup` (in the
      first 100,000 decisions); `sudden`, the first changepoint of the run's sudden rise under OQ-82 (c), and
      `sudden_oq78a`, the run's sudden jump under OQ-78 (a)."""
    runs, points = [], []
    for (variant, seed), group in binned.groupby(["variant", "seed"], sort=True):
        group = group.sort_values("bin")
        values = group["value"].to_numpy()
        starts, means = segments(values, penalty)
        bins = group["bin"].to_numpy()
        steps = [int(bins[s]) * every for s in starts[1:]]
        decided, revised = decided_verdict(means), revised_verdict(steps, means, noise(values))
        runs.append({"variant": variant, "seed": seed, "segments": len(means),
                     **{k: revised[k] for k in ("initial_rise", "gain", "largest_share", "verdict")},
                     **{f"{k}_oq78a": decided[k] for k in ("gain", "largest_share", "verdict")}})
        sudden = revised["rise"][0] if revised["verdict"] == "sudden" else -1
        for i, step in enumerate(steps):
            points.append({"variant": variant, "seed": seed, "step": step, "before": means[i], "after": means[i + 1],
                           "jump": means[i + 1] - means[i], "warmup": step <= WARMUP, "sudden": i == sudden,
                           "sudden_oq78a": decided["verdict"] == "sudden" and i == decided["jump"]})
    columns = ["variant", "seed", "step", "before", "after", "jump", "warmup", "sudden", "sudden_oq78a"]
    return pd.DataFrame(runs), pd.DataFrame(points, columns=columns)


# --- time allocation and discovery ---------------------------------------------------------------------------------

def _shares(ticks: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Each group's game-time share per activity, every activity present (0 where none), from rows of ticks."""
    table = ticks.pivot_table(index=keys, columns="activity", values="ticks", aggfunc="sum", fill_value=0)
    table = table.reindex(columns=list(ALL_ACTIVITIES), fill_value=0)
    shares = table.div(table.sum(axis=1), axis=0)
    return shares.reset_index().melt(id_vars=keys, var_name="activity", value_name="share")


def full_bins(bins: pd.DataFrame) -> pd.DataFrame:
    """The behaviour bins without a run's last when it holds under half a bin's decisions (a run of 2,000,768 decisions
    ends 768 into its 21st), as `binned_curve` leaves out a run's last half-empty bin (2026-11-16)."""
    return bins[bins["decisions"] >= (bins["to_step"] - bins["from_step"]) / 2].reset_index(drop=True)


def time_shares(options: pd.DataFrame, bins: pd.DataFrame) -> pd.DataFrame:
    """Per (variant, seed, bin, activity): its share of the bin's game time in training, with the bin's `to_step`,
    for the bins in `bins` (so `full_bins`' leave out a run's half-empty last)."""
    ticks = options.assign(activity=options["option"].map(activity))
    shares = _shares(ticks, ["variant", "seed", "bin"])
    return shares.merge(bins[["variant", "seed", "bin", "to_step"]], on=["variant", "seed", "bin"], how="inner")


def trace_shares(decisions: pd.DataFrame) -> pd.DataFrame:
    """Per (policy, seed, activity): its share of the evaluation episode's game time, from the trace (a decision
    lasts from the one before's end, the first from tick 0)."""
    frame = decisions.sort_values(["policy", "seed", "decision"])
    ticks = frame.assign(ticks=frame.groupby(["policy", "seed"], sort=False)["t1"].diff().fillna(frame["t1"]),
                         activity=frame["option"].map(activity))
    return _shares(ticks, ["policy", "seed"])


def discovery(shares: pd.DataFrame, threshold: float = DISCOVERY_SHARE) -> pd.DataFrame:
    """Per (variant, seed, activity): the first training bin in which the activity took at least `threshold` of the
    game time, and that bin's `to_step` (NaN for both if it never did)."""
    reached = shares[shares["share"] >= threshold]
    first = reached.loc[reached.groupby(["variant", "seed", "activity"])["bin"].idxmin(),
                        ["variant", "seed", "activity", "bin", "to_step"]]
    runs = shares[["variant", "seed"]].drop_duplicates()
    grid = runs.merge(pd.DataFrame({"activity": list(ALL_ACTIVITIES)}), how="cross")
    return grid.merge(first, on=["variant", "seed", "activity"], how="left")


# --- sample efficiency, consistency and milestones ----------------------------------------------------------------

def sample_efficiency(binned: pd.DataFrame, targets: Mapping[str, float], hold: int = HOLD) -> pd.DataFrame:
    """Per run of a variant in `targets` (OQ-84): the decisions by the end of the first bin from which its curve's
    `value` stays at or above the variant's target for `hold` bins, or to the run's end if fewer remain (`to_step`,
    NaN if never), and whether it `matched`."""
    rows = []
    for (variant, seed), group in binned[binned["variant"].isin(list(targets))].groupby(["variant", "seed"]):
        group = group.sort_values("bin")
        ok, ends = (group["value"] >= targets[variant]).to_numpy(), group["to_step"].to_numpy()
        first = next((i for i in range(len(ok)) if ok[i:i + hold].all()), None)
        rows.append({"variant": variant, "seed": seed, "target": targets[variant],
                     "to_step": float(ends[first]) if first is not None else float("nan"), "matched": first is not None})
    return pd.DataFrame(rows, columns=["variant", "seed", "target", "to_step", "matched"])


def js_divergence(p: Sequence[float], q: Sequence[float]) -> float:
    """The Jensen–Shannon divergence of two distributions, in bits (0 to 1)."""
    p, q = np.asarray(p, dtype=float), np.asarray(q, dtype=float)
    p, q = p / p.sum(), q / q.sum()
    m = (p + q) / 2

    def kl(a: np.ndarray) -> float:
        kept = a > 0
        return float((a[kept] * np.log2(a[kept] / m[kept])).sum())
    return (kl(p) + kl(q)) / 2


def consistency(shares: pd.DataFrame, n_boot: int = N_BOOT, seed: int = 0) -> pd.DataFrame:
    """Per variant (OQ-85): its training seeds, their pairs, and the mean pairwise Jensen–Shannon divergence of their
    activity mixes, with a bootstrap 95% CI over the pairs. `shares` has variant, train_seed, seed (the evaluation
    episode's), activity and share; a training seed's mix is its episodes' mean shares."""
    mixes = shares.groupby(["variant", "train_seed", "activity"])["share"].mean().unstack("activity", fill_value=0)
    rng, rows = np.random.default_rng(seed), []
    for variant, table in mixes.groupby(level="variant", sort=True):
        values = [js_divergence(table.iloc[i], table.iloc[j]) for i, j in combinations(range(len(table)), 2)]
        low, high = bootstrap_ci(values, rng, n_boot)
        rows.append({"variant": variant, "seeds": len(table), "pairs": len(values),
                     "js_bits": float(np.mean(values)) if values else float("nan"), "ci_low": low, "ci_high": high})
    return pd.DataFrame(rows, columns=["variant", "seeds", "pairs", "js_bits", "ci_low", "ci_high"])


def milestones(decisions: pd.DataFrame, checkpoints: pd.DataFrame) -> pd.DataFrame:
    """Per (policy, seed, milestone) of an evaluation (OQ-83): the game hours at the end of the first decision after
    which the episode's gain over its fresh character (its hour-0 checkpoint) reaches the milestone's target, inf if
    none does."""
    fresh = checkpoints[checkpoints["hour"] == 0].set_index(["policy", "seed"])
    rows = []
    for (policy, seed), trace in decisions.groupby(["policy", "seed"], sort=False):
        trace = trace.sort_values("decision")
        for name, (metric, target) in MILESTONES.items():
            reached = trace["t1"][trace[metric] - fresh.loc[(policy, seed), metric] >= target]
            rows.append({"policy": policy, "seed": seed, "milestone": name, "target": target,
                         "hours": reached.iloc[0] / TICKS_PER_HOUR if len(reached) else math.inf})
    return pd.DataFrame(rows, columns=["policy", "seed", "milestone", "target", "hours"])


def milestone_summary(table: pd.DataFrame, keys: Sequence[str]) -> pd.DataFrame:
    """Per group of `keys` and milestone: its episodes, the share that reached it, and the median hours with the
    others censored at infinity (Kaplan–Meier's median here; inf when under half got there)."""
    return table.groupby([*keys, "milestone"], sort=False).agg(
        episodes=("hours", "size"), reached=("hours", lambda h: float(np.isfinite(h).mean())),
        median_hours=("hours", "median")).reset_index()


# --- the front and its hypervolume ---------------------------------------------------------------------------------

def parse_label(policy: str) -> tuple[str, int | None, float | None]:
    """(variant, training seed, skill share u) of an evaluated policy's label; a baseline's is (name, None, None)."""
    match = LABEL.match(policy)
    if not match:
        return policy, None, None
    u = match["u"]
    return match["variant"], int(match["seed"]), float(u) if u is not None else None


def _labels(policies: pd.Series) -> tuple[list, list, list]:
    parsed = [parse_label(p) for p in policies]
    return [p[0] for p in parsed], [p[1] for p in parsed], [p[2] for p in parsed]


def gains(episodes: pd.DataFrame) -> pd.DataFrame:
    """Each evaluated episode's 20-hour gain in normalised units (OQ-67), with its policy's variant, training seed
    and u."""
    frame = episodes[["policy", "seed"]].copy()
    frame["skill"] = episodes["r_skill"] / SKILL_UNIT
    frame["wealth"] = episodes["r_wealth"] / WEALTH_UNIT
    frame["variant"], frame["train_seed"], frame["u"] = _labels(frame["policy"])
    return frame


def points(gain: pd.DataFrame) -> pd.DataFrame:
    """Each policy's point: its mean gain over the evaluation seeds (`episodes`, how many)."""
    keys = ["policy", "variant", "train_seed", "u"]
    return gain.groupby(keys, dropna=False, sort=False).agg(episodes=("seed", "size"), skill=("skill", "mean"),
                                                            wealth=("wealth", "mean")).reset_index()


def hypervolume(xy: Sequence[tuple[float, float]], reference: tuple[float, float] = REFERENCE) -> float:
    """The area the points dominate above the reference point (both objectives maximised)."""
    rx, ry = reference
    kept = sorted(((x, y) for x, y in xy if x > rx and y > ry), reverse=True)
    area, top = 0.0, ry
    for x, y in kept:  # by x, highest first: each point that reaches higher adds its strip
        if y > top:
            area += (x - rx) * (y - top)
            top = y
    return area


def front(xy: pd.DataFrame) -> pd.DataFrame:
    """The non-dominated rows of a table with `skill` and `wealth`, by skill."""
    ordered = xy.sort_values(["skill", "wealth"], ascending=False)
    kept, top = [], -math.inf
    for i, row in ordered.iterrows():
        if row["wealth"] > top:
            kept.append(i)
            top = row["wealth"]
    return xy.loc[kept].sort_values("skill")


def hypervolumes(pts: pd.DataFrame, methods: dict[str, Sequence[str]],
                 reference: tuple[float, float] = REFERENCE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per (method, training seed): the hypervolume of the method's policies at that seed (`methods` names each
    method's variants), and per method its mean with a 95% CI over the seeds."""
    rows = []
    for method, variants in methods.items():
        mine = pts[pts["variant"].isin(list(variants)) & pts["train_seed"].notna()]
        for seed, group in mine.groupby("train_seed"):
            rows.append({"method": method, "train_seed": int(seed), "policies": len(group),
                         "hypervolume": hypervolume(zip(group["skill"], group["wealth"]), reference)})
    per_seed = pd.DataFrame(rows, columns=["method", "train_seed", "policies", "hypervolume"])
    return per_seed, over_seeds(per_seed, ["method"], "hypervolume")


# --- progress at the checkpoints (RQ1) -----------------------------------------------------------------------------

def progress(checkpoints: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Per (variant, hour): a trained variant's mean and CI over its training seeds (each seed's mean over the
    evaluation seeds), and a baseline's over its evaluation seeds. `trained` says which."""
    variant, train_seed, _ = _labels(checkpoints["policy"])
    frame = checkpoints.assign(variant=variant, train_seed=train_seed)
    trained = frame[frame["train_seed"].notna()]
    per_seed = trained.groupby(["variant", "train_seed", "hour"], as_index=False)[metric].mean()
    out = [over_seeds(per_seed, ["variant", "hour"], metric).assign(trained=True),
           over_seeds(frame[frame["train_seed"].isna()], ["variant", "hour"], metric).assign(trained=False)]
    return pd.concat([o for o in out if len(o)], ignore_index=True)


# --- RQ5's click-ahead bound (OQ-87 (a)) ---------------------------------------------------------------------------

WALKING_SHARES = ("walk_share", "overhead_share", "transport_share")


def walking(decisions: pd.DataFrame) -> pd.DataFrame:
    """Per (policy, seed) of an evaluation: its game ticks, the ticks on foot, in the walker's overhead and on
    transports, and their shares of the game ticks. Decisions with no walk counter (NaN: traces from before it, or
    a play() outside the harness) are left out, and so is a trace without its columns."""
    columns = ["policy", "seed", "ticks", "walk", "overhead", "transport", *WALKING_SHARES]
    if "walk_ticks" not in decisions:
        return pd.DataFrame(columns=columns)
    walked = ("walk_ticks", "walk_overhead_ticks", "transport_ticks")  # a summary read with keep_default_na=False
    frame = decisions.assign(**{c: pd.to_numeric(decisions[c], errors="coerce") for c in walked})  # has "" for NaN
    frame = frame.dropna(subset=["walk_ticks"])
    per = frame.groupby(["policy", "seed"], sort=False).agg(
        ticks=("t1", "max"), walk=("walk_ticks", "sum"), overhead=("walk_overhead_ticks", "sum"),
        transport=("transport_ticks", "sum")).reset_index()
    per = per.assign(walk_share=per["walk"] / per["ticks"], overhead_share=per["overhead"] / per["ticks"],
                     transport_share=per["transport"] / per["ticks"])
    return per[columns]


def walking_summary(per_episode: pd.DataFrame) -> pd.DataFrame:
    """Per (variant, share): a trained variant's mean and CI over its training seeds, a baseline's over its
    evaluation seeds, as `progress` has them. `trained` says which."""
    variant, train_seed, _ = _labels(per_episode["policy"])
    frame = per_episode.assign(variant=variant, train_seed=train_seed)
    out = []
    for share in WALKING_SHARES:
        per_seed = frame[frame["train_seed"].notna()].groupby(["variant", "train_seed"], as_index=False)[share].mean()
        parts = [over_seeds(per_seed, ["variant"], share).assign(trained=True),
                 over_seeds(frame[frame["train_seed"].isna()], ["variant"], share).assign(trained=False)]
        out += [p.assign(share=share) for p in parts if len(p)]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(
        columns=["variant", "seeds", "mean", "ci_low", "ci_high", "trained", "share"])
