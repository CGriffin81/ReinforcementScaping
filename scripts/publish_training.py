"""Publish an experiment's training runs to results/summary/<name>/training/ (rlscape/eval/publish.py).

Writes runs.csv (each run's provenance, decisions, wall time and settings), learning_curves.csv (every finished
episode of every run), each run's config.json and a README. Refuses runs from a tree with uncommitted changes unless
--allow-dirty, and an existing training summary unless --force.

Usage:
    uv run python scripts/publish_training.py runs/e2-ppo-sanity-ladder e2-ppo-sanity-ladder
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rlscape.eval.publish import SUMMARY_ROOT, PublishError, publish_training


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs_root", type=Path, help="the experiment's runs (scripts/train.py's out)")
    parser.add_argument("name", help="the experiment's name: results/summary/<name>/training/")
    parser.add_argument("--root", type=Path, default=SUMMARY_ROOT)
    parser.add_argument("--allow-dirty", action="store_true", help="publish runs from a tree with uncommitted changes")
    parser.add_argument("--force", action="store_true", help="replace an existing training summary")
    args = parser.parse_args()
    try:
        out = publish_training(args.runs_root, args.name, args.root, args.allow_dirty, args.force)
    except PublishError as error:
        sys.exit(f"publish_training: {error}")
    print(out)


if __name__ == "__main__":
    main()
