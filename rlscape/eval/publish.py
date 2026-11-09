"""Publishing a run's summary: the small, committed copy of an eval or training run that an experiment's PR carries
(OQ-61), so a reviewer can read every result without running anything.

`publish(run_dir, name)` writes `results/summary/<name>/`:
- `config.json`, copied as the run wrote it: the config, its hash, the git SHAs of this repo and the fork, whether
  the tree had uncommitted changes, package versions, and the command when the script recorded one;
- `summary.csv`, `checkpoints.csv` and `episodes.csv`, the run's three tables (rlscape/eval/harness.py) as CSV, so
  they diff and open anywhere;
- `README.md`: the provenance and the last checkpoint's table, each policy's mean and 95% CI.

It refuses a run made from a tree with uncommitted changes, since its git SHA wouldn't reproduce it (`allow_dirty`
publishes it anyway, and the README says so), and it never overwrites a published summary unless `force`.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from rlscape.eval.harness import METRICS, REPO

SUMMARY_ROOT = REPO / "results" / "summary"
TABLES = ("summary", "checkpoints", "episodes")
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
    if out.exists():
        if not force:
            raise PublishError(f"{out} is already published; pass force to replace it")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copyfile(run_dir / "config.json", out / "config.json")
    tables = {t: pd.read_parquet(run_dir / f"{t}.parquet") for t in TABLES}
    for table, frame in tables.items():
        frame.to_csv(out / f"{table}.csv", index=False, lineterminator="\n")
    (out / "README.md").write_text(readme(name, run_dir, meta, tables["summary"]), encoding="utf-8", newline="\n")
    return out


def readme(name: str, run_dir: Path, meta: dict, summary: pd.DataFrame) -> str:
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
              "and wall time (the only column that changes between identical runs).", ""]
    return "\n".join(lines)


def _shown(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()
