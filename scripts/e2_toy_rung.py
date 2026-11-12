"""E2's rung 1: train SMDP MaskablePPO on the toy env (rlscape/envs/toy.py) and compare it with the exact optimum.

For each seed: train, then play `eval_episodes` episodes with sampled actions (torch seeded by the episode), and score
each by its discounted return (γ_hr, what PPO maximises), its undiscounted return and its trainings. Writes the models
to runs/e2-ppo-sanity-ladder/<part>/seed<k>/ (git-ignored) and the results to
results/summary/e2-ppo-sanity-ladder/<part>/ (results.csv, config.json with the provenance and the optimum, README),
<part> being the config's name after `e2-ppo-sanity-ladder-` (`toy`, `toy-lambda0.95`). Refuses a dirty tree unless
--allow-dirty.

Usage:
    uv run python scripts/e2_toy_rung.py --config configs/e2-ppo-sanity-ladder-toy.yaml
    uv run python scripts/e2_toy_rung.py --config configs/e2-ppo-sanity-ladder-toy-lambda0.95.yaml   # the first, failed
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import pandas as pd
import torch as th
import yaml
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor

from rlscape.agents.ppo import SMDPMaskablePPO
from rlscape.envs.toy import HORIZON, OPTIONS, ToyEnv, optimum, returns_of
from rlscape.eval.harness import REPO, config_hash, provenance

EXPERIMENT = "e2-ppo-sanity-ladder"


def evaluate(model: SMDPMaskablePPO, episodes: int, gamma_hr: float) -> list[dict]:
    rows = []
    for episode in range(episodes):
        env, actions = ToyEnv(), []
        obs, _ = env.reset(seed=episode)
        th.manual_seed(episode)
        truncated = False
        while not truncated:
            action, _ = model.predict(obs, action_masks=env.action_masks(), deterministic=False)
            actions.append(int(action))
            obs, _, _, truncated, _ = env.step(int(action))
        rows.append({"episode": episode, **returns_of(actions, gamma_hr),
                     "idles": sum(OPTIONS[a] == "idle" for a in actions), "decisions": len(actions)})
    return rows


def readme(config: dict, meta: dict, best: dict, results: pd.DataFrame, config_path: str) -> str:
    lines = [f"# {EXPERIMENT}: rung 1, the toy env", "",
             "SMDP MaskablePPO on the synthetic three-option env (`rlscape/envs/toy.py`, OQ-65 (1)) against its exact "
             f"optimum, {config['eval_episodes']} sampled episodes a seed, after {config['total_decisions']:,} "
             f"decisions at GAE λ {config['ppo']['gae_lambda']}. Run by `scripts/e2_toy_rung.py --config "
             f"{config_path}`.", "",
             f"Git `{meta['git_sha']}`" + (" (uncommitted changes)" if meta["git_dirty"] else "")
             + f", config hash `{meta['config_hash']}`.", "",
             f"**The optimum** (γ_hr {config['ppo']['gamma_hr']}): {best['trainings']} trainings, then work; "
             f"discounted return {best['discounted']:.2f}, undiscounted {best['undiscounted']:.2f}.", "",
             "| Seed | Discounted return | Share of the optimum | Trainings | Idles | Passes |",
             "|---|---:|---:|---:|---:|---|"]
    for seed, group in results.groupby("seed"):
        share = group.discounted.mean() / best["discounted"]
        lines.append(f"| {seed} | {group.discounted.mean():.2f} | {share:.1%} | {group.trainings.mean():.1f} | "
                     f"{group.idles.mean():.1f} | {'yes' if share >= config['pass_share'] else 'no'} |")
    passed = all(g.discounted.mean() / best["discounted"] >= config["pass_share"]
                 for _, g in results.groupby("seed"))
    lines += ["", f"**Rung 1 {'passes' if passed else 'fails'}:** every seed's mean discounted return must be at "
              f"least {config['pass_share']:.0%} of the optimum.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    part = args.config.stem.removeprefix(f"{EXPERIMENT}-")
    runs_dir, summary = REPO / "runs" / EXPERIMENT / part, REPO / "results" / "summary" / EXPERIMENT / part
    meta = {"config": config, "config_hash": config_hash(config), **provenance(), "torch": th.__version__,
            "script": "scripts/e2_toy_rung.py", "argv": sys.argv[1:]}
    if meta["git_dirty"] and not args.allow_dirty:
        sys.exit("e2_toy_rung: the tree has uncommitted changes; commit first, or pass --allow-dirty")
    gamma_hr, best = config["ppo"]["gamma_hr"], optimum(config["ppo"]["gamma_hr"])
    rows = []
    for seed in config["seeds"]:
        started = time.perf_counter()
        th.set_num_threads(4)
        vec = VecMonitor(DummyVecEnv([ToyEnv for _ in range(config["n_envs"])]))
        model = SMDPMaskablePPO("MlpPolicy", vec, seed=seed, device="cpu", verbose=0, **config["ppo"])
        model.learn(total_timesteps=int(config["total_decisions"]))
        run = runs_dir / f"seed{seed}"
        run.mkdir(parents=True, exist_ok=True)
        model.save(run / "model.zip")
        rows += [{"seed": seed, **r} for r in evaluate(model, config["eval_episodes"], gamma_hr)]
        print(f"seed {seed}: trained and evaluated in {time.perf_counter() - started:.0f}s", flush=True)
    results = pd.DataFrame(rows)
    if summary.exists():
        shutil.rmtree(summary)
    summary.mkdir(parents=True)
    results.to_csv(summary / "results.csv", index=False, lineterminator="\n")
    (summary / "config.json").write_text(json.dumps({**meta, "optimum": best, "horizon_ticks": HORIZON}, indent=2,
                                                    default=str), encoding="utf-8")
    shown = args.config.as_posix() if not args.config.is_absolute() else args.config.name
    (summary / "README.md").write_text(readme(config, meta, best, results, shown), encoding="utf-8", newline="\n")
    for seed, group in results.groupby("seed"):
        print(f"seed {seed}: {group.discounted.mean() / best['discounted']:.1%} of the optimum, "
              f"{group.trainings.mean():.1f} trainings (optimum {best['trainings']}) -> {summary}")


if __name__ == "__main__":
    main()
