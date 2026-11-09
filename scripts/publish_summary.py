"""Publish a run's summary to results/summary/<name>/, the small copy an experiment's PR commits (rlscape/eval/publish.py).

Writes config.json, summary.csv, checkpoints.csv, episodes.csv and a README.md with the provenance and the last
checkpoint's table. Refuses a run made from a tree with uncommitted changes unless --allow-dirty, and an existing
summary unless --force.

Usage:
    uv run python scripts/publish_summary.py results/eval/e1-baselines e1-baselines
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rlscape.eval.publish import SUMMARY_ROOT, PublishError, publish


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path, help="the run's output directory (scripts/evaluate.py's --out)")
    parser.add_argument("name", help="the experiment's name: results/summary/<name>/")
    parser.add_argument("--root", type=Path, default=SUMMARY_ROOT)
    parser.add_argument("--allow-dirty", action="store_true", help="publish a run from a tree with uncommitted changes")
    parser.add_argument("--force", action="store_true", help="replace an existing summary")
    args = parser.parse_args()
    try:
        out = publish(args.run_dir, args.name, args.root, args.allow_dirty, args.force)
    except PublishError as error:
        sys.exit(f"publish_summary: {error}")
    print(out)


if __name__ == "__main__":
    main()
