"""Write a replay page for a training run: one episode on one seed for each of its chosen checkpoints, and for any
baselines beside them (rlscape/eval/replay.py; Caleb, 2026-11-10, OQ-70).

Each episode is the one the evaluation harness plays for that policy and seed: sampled actions, torch seeded by the
seed (OQ-65 (4)), the env made as the run was trained (its reward weights and horizon). The page is one HTML file with
no network use. Open it in a browser.

Usage:
    uv run python scripts/replay.py runs/e2-ppo-sanity-ladder/gae_lambda0.95_learning_rate0.0003/seed0
    uv run python scripts/replay.py <run dir> --checkpoints 100000 1000000 final --also scripted_guide --seed 3

By default the checkpoints are the first, the one nearest the middle, and the final model. The page goes to
results/replays/<experiment>_<variant>_seed<k>_episode<seed>.html (git-ignored) unless --out says where.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from rlscape.envs.sim_env import SimEnv
from rlscape.eval.harness import POLICIES, REPO, make_policy
from rlscape.eval.replay import Walks, page, record

CHECKPOINT = re.compile(r"^ppo_(\d+)_steps\.zip$")


def checkpoints(run: Path) -> dict[int, Path]:
    found = {}
    for path in (run / "checkpoints").glob("ppo_*_steps.zip"):
        match = CHECKPOINT.match(path.name)
        if match:
            found[int(match.group(1))] = path
    return dict(sorted(found.items()))


def decisions_label(n: int) -> str:
    return f"{n / 1e6:.3g}M decisions" if n >= 1_000_000 else f"{round(n / 1000)}k decisions"


def chosen(run: Path, wanted: list[str] | None) -> list[tuple[str, Path]]:
    """(label, model path) for each checkpoint asked for: a number of decisions, or `final` (model.zip)."""
    saved = checkpoints(run)
    finished = json.loads((run / "run.json").read_text(encoding="utf-8")) if (run / "run.json").exists() else None
    final = run / "model.zip"
    if not wanted:
        steps = list(saved)
        wanted = ([str(steps[0]), str(steps[len(steps) // 2])] if steps else []) + (["final"] if final.exists() else [])
        wanted = list(dict.fromkeys(wanted))
    out = []
    for item in wanted:
        if item == "final":
            if not final.exists():
                sys.exit(f"replay: {run} has no model.zip yet (still training?)")
            label = f"final ({decisions_label(finished['decisions'])})" if finished else "final"
            out.append((label, final))
        else:
            n = int(item)
            if n not in saved:
                sys.exit(f"replay: no checkpoint at {n:,} decisions in {run / 'checkpoints'}; saved: {list(saved)}")
            out.append((decisions_label(n), saved[n]))
    return out


def env_from(meta: dict) -> SimEnv:
    kwargs = dict(meta.get("env_kwargs") or {})
    if "reward_weights" in kwargs:
        kwargs["reward_weights"] = tuple(kwargs["reward_weights"])
    return SimEnv(**kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run", type=Path, help="a training run's directory (runs/<experiment>/[<variant>/]seed<k>)")
    parser.add_argument("--checkpoints", nargs="+", help="decisions of saved checkpoints, or final")
    parser.add_argument("--also", nargs="+", default=[], choices=sorted(POLICIES), help="baselines to replay beside it")
    parser.add_argument("--seed", type=int, default=0, help="the episode's seed (E1's evaluation seeds are 0 to 29)")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    meta = json.loads((run / "config.json").read_text(encoding="utf-8"))
    config = meta["config"]
    parts = run.relative_to(REPO / "runs").parts if run.is_relative_to(REPO / "runs") else run.parts[-3:]
    name = "_".join(parts)
    out = args.out or REPO / "results" / "replays" / f"{name}_episode{args.seed}.html"

    env, walks, replays = env_from(meta), Walks(), []
    specs = [(label, f"{label}=ppo:{path}") for label, path in chosen(run, args.checkpoints)]
    specs += [(baseline.replace("_", " "), baseline) for baseline in args.also]
    for label, spec in specs:
        started = time.perf_counter()
        replays.append(record(env, make_policy(spec), args.seed, label, walks))
        r = replays[-1]
        print(f"{label}: {len(r['decisions'])} decisions, total level {r['final']['total_level']}, net worth "
              f"{r['final']['net_worth']:,} gp ({time.perf_counter() - started:.0f}s)", flush=True)

    env_section = config.get("env") or {}
    weights = (f"normalised weights {tuple(env_section['normalised_weights'])}, the env's "
               f"({meta['env_kwargs']['reward_weights'][0]:g}, {meta['env_kwargs']['reward_weights'][1]:.3g})"
               if "normalised_weights" in env_section else
               f"weights {tuple(meta.get('env_kwargs', {}).get('reward_weights', (0.5, 0.5)))}")
    info = {"title": f"Replay: {' / '.join(parts)}",
            "subtitle": f"Episode seed {args.seed} · {weights} · git {meta['git_sha'][:7]}"
                        + (" (dirty)" if meta.get("git_dirty") else "")
                        + f" · made {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "run": str(args.run), "seed": args.seed, "config_hash": meta.get("config_hash"),
            "git_sha": meta.get("git_sha")}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(replays, info), encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
