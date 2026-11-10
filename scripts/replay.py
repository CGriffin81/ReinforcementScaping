"""Write a replay page for a training run: one episode on one seed for each of its chosen checkpoints, and for any
baselines beside them (rlscape/eval/replay.py; Caleb, 2026-11-10, OQ-70).

Each episode is the one the evaluation harness plays for that policy and seed: sampled actions, torch seeded by the
seed (OQ-65 (4)), the env made as the run was trained (its reward weights and horizon). The page is one HTML file with
no network use. Open it in a browser.

Usage:
    uv run python scripts/replay.py runs/e2-ppo-sanity-ladder/gae_lambda0.95_learning_rate0.0003/seed0
    uv run python scripts/replay.py <run dir> --checkpoints 100000 1000000 final --also scripted_guide --seed 3

By default the checkpoints are the first, the one nearest the middle, and the final model. The page names each by the
practice episodes it had played (its training's decisions are in its description). The page goes to
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

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

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


def episodes_by(run: Path, n_envs: int):
    """A function from training decisions to the training episodes that had ended by then (None where unknown).

    It reads episodes.parquet once the run has finished, or the decision log while it trains: a log row's `step` is
    the run's decisions before that step, so an episode ending at it is counted n_envs decisions later, as in
    episodes.parquet (the two agree on E2's runs). The log is only known up to its last part written.
    """
    if (run / "episodes.parquet").exists():
        ended, known = pd.read_parquet(run / "episodes.parquet", columns=["step"])["step"].to_numpy(), None
    else:
        parts = sorted((run / "decisions").glob("part-*.parquet"))
        if not parts:
            return lambda n: None
        log = pd.concat([pq.read_table(p, columns=["step", "done"]).to_pandas() for p in parts])
        ended, known = log.loc[log["done"], "step"].to_numpy() + n_envs, int(log["step"].max()) + n_envs
    ended = np.sort(ended)
    return lambda n: None if known is not None and n > known else int(np.searchsorted(ended, n, side="right"))


def trained_names(decisions: int, episodes: int | None, final: bool) -> dict:
    """A trained replay's label (buttons, timeline), short label (chart ends) and one-line description.

    It's named by the practice episodes the model had played, not by its training decisions: the page also counts one
    episode's decisions (a few hundred), and two counts of decisions side by side read as the same kind of number.
    """
    which = "The final model" if final else "A checkpoint"
    if episodes is None:
        return {"label": f"Trained {decisions_label(decisions)}", "short": decisions_label(decisions),
                "about": f"{which}, after {decisions:,} decisions of training."}
    return {"label": f"After {episodes:,} episodes", "short": f"{episodes:,} episodes",
            "about": f"{which}, after {episodes:,} practice episodes ({decisions:,} decisions in all)."}


def chosen(run: Path, wanted: list[str] | None, n_envs: int) -> list[tuple[dict, Path]]:
    """(names, model path) for each checkpoint asked for: a number of decisions, or `final` (model.zip)."""
    saved = checkpoints(run)
    finished = json.loads((run / "run.json").read_text(encoding="utf-8")) if (run / "run.json").exists() else None
    final = run / "model.zip"
    if not wanted:
        steps = list(saved)
        wanted = ([str(steps[0]), str(steps[len(steps) // 2])] if steps else []) + (["final"] if final.exists() else [])
        wanted = list(dict.fromkeys(wanted))
    episodes = episodes_by(run, n_envs)
    out = []
    for item in wanted:
        if item == "final":
            if not final.exists():
                sys.exit(f"replay: {run} has no model.zip yet (still training?)")
            names = (trained_names(finished["decisions"], finished["episodes"], final=True) if finished else
                     {"label": "Final model", "short": "final", "about": "The final model."})
            out.append((names, final))
        else:
            n = int(item)
            if n not in saved:
                sys.exit(f"replay: no checkpoint at {n:,} decisions in {run / 'checkpoints'}; saved: {list(saved)}")
            out.append((trained_names(n, episodes(n), final=False), saved[n]))
    return out


BASELINES = {  # E1's baselines, untrained (rlscape/baselines)
    "random": "An E1 baseline, not trained: picks at random among the options open.",
    "greedy_xp": "An E1 baseline, not trained: picks the option that looks set to gain the most XP per game-minute.",
    "greedy_wealth": "An E1 baseline, not trained: picks the option that looks set to gain the most net worth per "
                     "game-minute.",
    "greedy_skill": "An E1 baseline, not trained: picks the option that looks set to gain the most skill reward per "
                    "game-minute.",
    "scripted_guide": "An E1 baseline, not trained: follows the RuneScape Wiki's January 2009 training guides, raising "
                      "its lowest skill to the next multiple of 5 each time.",
}


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
    specs = [(names, f"{names['label']}=ppo:{path}") for names, path in chosen(run, args.checkpoints, config["n_envs"])]
    for b in args.also:
        name = b.replace("_", " ")
        specs.append(({"label": name, "short": name, "about": BASELINES.get(b, "An E1 baseline.")}, b))
    for names, spec in specs:
        started = time.perf_counter()
        replays.append(record(env, make_policy(spec), args.seed, names["label"], walks) | names)
        r = replays[-1]
        print(f"{names['label']}: {len(r['decisions'])} decisions in the episode, total level "
              f"{r['final']['total_level']}, net worth {r['final']['net_worth']:,} gp "
              f"({time.perf_counter() - started:.0f}s)", flush=True)

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
