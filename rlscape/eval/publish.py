"""Publishing a run's summary: the small, committed copy of an eval or training run that an experiment's PR carries
(OQ-61), so a reviewer can read every result without running anything.

`publish(run_dir, name)` writes `results/summary/<name>/`:
- `config.json`, copied as the run wrote it: the config, its hash, the git SHAs of this repo and the fork, whether
  the tree had uncommitted changes, package versions, and the command when the script recorded one;
- `summary.csv`, `checkpoints.csv` and `episodes.csv`, the run's three tables (rlscape/eval/harness.py) as CSV, so
  they diff and open anywhere;
- `decisions.csv.gz`, every episode's trace, a row per decision, when the run kept one (scripts/evaluate.py does);
- `README.md`: the provenance and the last checkpoint's table, each policy's mean and 95% CI.

It refuses a run made from a tree with uncommitted changes, since its git SHA wouldn't reproduce it (`allow_dirty`
publishes it anyway, and the README says so), and it never overwrites a published summary unless `force` (which
replaces its own files only, so a training summary beside it stays).

`publish_training(runs_root, name)` writes `results/summary/<name>/training/` from an experiment's training runs
(rlscape/agents/training.py), every finished run under `runs_root` (one with a `run.json`):
- `runs.csv`: a row per run: its variant and seed, its provenance (config hash, git and fork SHAs, dirty), its
  decisions, episodes and wall time, and its `ppo` and env settings (JSON);
- `learning_curves.csv`: each run's learning curve (episodes.parquet), with its variant and seed;
- `configs/`: each run's config.json;
- from the runs' decision logs, where they kept one (rlscape/eval/behaviour.py), each with its variant and seed:
  `behaviour_bins.csv` (a row per bin of decisions: game time, episodes, the policy's entropy),
  `behaviour_options.csv.gz` (a row per bin and option chosen in it: decisions, game time, episodes) and
  `first_choices.csv.gz` (when each option was first chosen);
- `README.md`: per variant, the runs and the mean of their last 100 episodes' total level and net worth.

The same refusals apply: a run from a dirty tree, and a training summary already published.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from rlscape.eval.behaviour import training_behaviour
from rlscape.eval.harness import METRICS, REPO

SUMMARY_ROOT = REPO / "results" / "summary"
TABLES = ("summary", "checkpoints", "episodes")
TRACE_FILE = "decisions.csv.gz"
OWN_FILES = ("config.json", "README.md", *(f"{t}.csv" for t in TABLES), TRACE_FILE)
GZIP = {"method": "gzip", "mtime": 0}  # the same bytes for the same table, so a republished file doesn't diff
LAST_EPISODES = 100
METRIC_NAMES = {"total_level": "Total level", "total_xp": "Total XP", "net_worth": "Net worth (gp)"}


class PublishError(RuntimeError):
    """The run can't be published as asked."""


def publish(run_dir: Path, name: str, root: Path = SUMMARY_ROOT, allow_dirty: bool = False,
            force: bool = False) -> Path:
    run_dir, out = Path(run_dir), Path(root) / name
    meta = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    if meta.get("git_dirty", True) and not allow_dirty:
        raise PublishError(f"{run_dir} was run from a tree with uncommitted changes (or without a record of it): "
                           "rerun it from a clean commit, or pass allow_dirty")
    if any((out / f).exists() for f in OWN_FILES):
        if not force:
            raise PublishError(f"{out} is already published; pass force to replace it")
        for f in OWN_FILES:
            (out / f).unlink(missing_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(run_dir / "config.json", out / "config.json")
    tables = {t: pd.read_parquet(run_dir / f"{t}.parquet") for t in TABLES}
    for table, frame in tables.items():
        frame.to_csv(out / f"{table}.csv", index=False, lineterminator="\n")
    if (run_dir / "decisions.parquet").exists():
        pd.read_parquet(run_dir / "decisions.parquet").to_csv(out / TRACE_FILE, index=False, lineterminator="\n",
                                                               compression=GZIP)
    (out / "README.md").write_text(readme(name, run_dir, meta, tables["summary"], (out / TRACE_FILE).exists()),
                                   encoding="utf-8", newline="\n")
    return out


def readme(name: str, run_dir: Path, meta: dict, summary: pd.DataFrame, traced: bool = False) -> str:
    last = summary[summary.hour == summary.hour.max()]
    metrics = [m for m in METRICS if m in set(last.metric)]
    seeds = int(last.seeds.min())
    rows = [("Git SHA", f"`{meta.get('git_sha', '')}`"
             + (" (uncommitted changes: not reproducible from this SHA)" if meta.get("git_dirty", True) else "")),
            ("Fork SHA", f"`{meta.get('server_sha', '')}`"),
            ("Config hash", f"`{meta.get('config_hash', '')}`"),
            ("Created (UTC)", meta.get("created", "")),
            ("Seeds", str(seeds))]
    if "argv" in meta:
        rows.insert(0, ("Command", f"`uv run python {meta.get('script', 'scripts/evaluate.py')} "
                                   + " ".join(meta["argv"]) + "`"))
    lines = [f"# {name}", "",
             f"Published from `{_shown(run_dir)}` by `scripts/publish_summary.py`. The tables are CSV copies of the "
             "run's own (rlscape/eval/harness.py); `config.json` is the run's.", "",
             "| | |", "|---|---|", *[f"| {k} | {v} |" for k, v in rows], "",
             f"## At hour {last.hour.max()}: mean [95% bootstrap CI] over {seeds} seeds", "",
             "| Policy | " + " | ".join(METRIC_NAMES.get(m, m) for m in metrics) + " |",
             "|---|" + "---:|" * len(metrics)]
    for policy in dict.fromkeys(last.policy):
        cells = last[last.policy == policy].set_index("metric")
        lines.append(f"| {policy} | " + " | ".join(
            f"{cells.loc[m, 'mean']:,.0f} [{cells.loc[m, 'ci_low']:,.0f}, {cells.loc[m, 'ci_high']:,.0f}]"
            for m in metrics) + " |")
    lines += ["", "Files:",
              "- `summary.csv`: per policy, checkpoint hour and metric, the mean over seeds, its 95% CI and the "
              "standard deviation;",
              "- `checkpoints.csv`: each seed's metrics at each checkpoint (hour 0 is the fresh character);",
              "- `episodes.csv`: each episode's decisions, reward sums, final metrics, deaths, most chosen options "
              "and wall time (the only column that changes between identical runs)."]
    if traced:
        lines.append(f"- `{TRACE_FILE}`: every episode's trace, a row per decision: the game tick it ended at, its "
                     "option and why it ended, and the total level and net worth after it.")
    return "\n".join(lines + [""])


def publish_training(runs_root: Path, name: str, root: Path = SUMMARY_ROOT, allow_dirty: bool = False,
                     force: bool = False) -> Path:
    runs_root = Path(runs_root)
    runs = sorted(p.parent for p in runs_root.rglob("run.json"))
    if not runs:
        raise PublishError(f"no finished runs under {runs_root}")
    metas = [json.loads((r / "config.json").read_text(encoding="utf-8")) for r in runs]
    dirty = [_shown(r) for r, m in zip(runs, metas) if m.get("git_dirty", True)]
    if dirty and not allow_dirty:
        raise PublishError(f"runs from a tree with uncommitted changes: {dirty}; rerun them from a clean commit, "
                           "or pass allow_dirty")
    out = Path(root) / name / "training"
    if out.exists():
        if not force:
            raise PublishError(f"{out} is already published; pass force to replace it")
        shutil.rmtree(out)
    (out / "configs").mkdir(parents=True)
    rows, curves = [], []
    for run, meta in zip(runs, metas):
        done = json.loads((run / "run.json").read_text(encoding="utf-8"))
        variant, seed = meta["config"].get("variant", ""), meta["seed"]
        rows.append({"variant": variant, "seed": seed, "config_hash": meta["config_hash"],
                     "git_sha": meta["git_sha"], "git_dirty": meta["git_dirty"], "server_sha": meta["server_sha"],
                     "decisions": done["decisions"], "episodes": done["episodes"],
                     "wall_seconds": done["wall_seconds"], "ppo": json.dumps(meta["config"]["ppo"], sort_keys=True),
                     "env": json.dumps(meta["env_kwargs"], sort_keys=True)})
        curve = pd.read_parquet(run / "episodes.parquet")
        curve.insert(0, "seed", seed)
        curve.insert(0, "variant", variant)
        curves.append(curve)
        shutil.copyfile(run / "config.json", out / "configs" / f"{variant + '_' if variant else ''}seed{seed}.json")
    table, curve = pd.DataFrame(rows), pd.concat(curves, ignore_index=True)
    table.to_csv(out / "runs.csv", index=False, lineterminator="\n")
    curve.to_csv(out / "learning_curves.csv", index=False, lineterminator="\n")
    behaviour = _behaviour(runs, metas)
    if behaviour:
        behaviour["bins"].to_csv(out / "behaviour_bins.csv", index=False, lineterminator="\n")
        behaviour["options"].to_csv(out / "behaviour_options.csv.gz", index=False, lineterminator="\n",
                                    compression=GZIP)
        behaviour["first"].to_csv(out / "first_choices.csv.gz", index=False, lineterminator="\n", compression=GZIP)
    (out / "README.md").write_text(training_readme(name, runs_root, table, curve), encoding="utf-8", newline="\n")
    return out


def _behaviour(runs: list[Path], metas: list[dict]) -> dict[str, pd.DataFrame]:
    """Every logged run's behaviour tables (rlscape/eval/behaviour.py), each row with its variant and seed."""
    tables: dict[str, list[pd.DataFrame]] = {"bins": [], "options": [], "first": []}
    for run, meta in zip(runs, metas):
        if not (run / "decisions").is_dir():
            continue
        for key, frame in training_behaviour(run).items():
            frame.insert(0, "seed", meta["seed"])
            frame.insert(0, "variant", meta["config"].get("variant", ""))
            tables[key].append(frame)
    return {key: pd.concat(frames, ignore_index=True) for key, frames in tables.items() if frames}


def training_readme(name: str, runs_root: Path, runs: pd.DataFrame, curves: pd.DataFrame) -> str:
    lines = [f"# {name}: training", "",
             f"Published from `{_shown(runs_root)}` by `scripts/publish_training.py`: {len(runs)} runs. `runs.csv` "
             "has each run's provenance and settings, `learning_curves.csv` each run's finished episodes, `configs/` "
             "each run's config.json.", "",
             f"| Variant | Runs | Decisions a run | Total level, last {LAST_EPISODES} episodes | "
             f"Net worth (gp), last {LAST_EPISODES} episodes |", "|---|---:|---:|---:|---:|"]
    for variant, group in runs.groupby("variant", sort=False):
        lasts = [curves[(curves.variant == variant) & (curves.seed == seed)].tail(LAST_EPISODES)
                 for seed in group.seed]
        level = sum(c.total_level.mean() for c in lasts) / len(lasts)
        worth = sum(c.net_worth.mean() for c in lasts) / len(lasts)
        lines.append(f"| {variant or '(one config)'} | {len(group)} | {int(group.decisions.mean()):,} | "
                     f"{level:,.0f} | {worth:,.0f} |")
    lines += ["", "Each number is the mean over the variant's runs of their own means. The policies' evaluations "
              "against the baselines, on E1's seeds, are the experiment's own summary beside this folder.", ""]
    return "\n".join(lines)


def _shown(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()
