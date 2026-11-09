"""Digest every decision of every (policy, seed) episode, to prove a change leaves the simulator's results as they were.

Each episode's digest is a SHA-256 over every decision's observation, action mask, action, reward and info (the
option and its detail, the duration, the termination, the checkpoints). Two runs whose digests all match played the
same trajectories, decision for decision. Two runs of the same code at different worker counts check that an episode
depends only on its policy and seed, not on what its worker played before (OQ-64). A run also records each episode's
wall time, so the same comparison measures a speed-up.

Usage:
    uv run python scripts/trajectory_digest.py --seeds 30 --workers 16 --out results/digests/main.json
    uv run python scripts/trajectory_digest.py --seeds 30 --workers 16 --out results/digests/new.json \\
        --compare results/digests/main.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from rlscape.envs.sim_env import SimEnv
from rlscape.eval.harness import POLICIES, provenance
from rlscape.eval.rollout import play
from rlscape.sim.engine import TICKS_PER_HOUR

E1_POLICIES = ["random", "greedy_xp", "greedy_wealth", "scripted_guide"]


class DigestEnv(SimEnv):
    """SimEnv that hashes what it hands the policy at every reset and step."""

    def reset(self, **kwargs):
        obs, info = super().reset(**kwargs)
        self.digest = hashlib.sha256()
        self._feed(obs, info)
        return obs, info

    def step(self, action):
        obs, reward, terminated, truncated, info = super().step(action)
        self._feed(obs, (int(action), reward, terminated, truncated, info))
        return obs, reward, terminated, truncated, info

    def _feed(self, obs: np.ndarray, rest) -> None:
        self.digest.update(np.ascontiguousarray(obs).tobytes())
        self.digest.update(self._mask.tobytes())
        self.digest.update(repr(rest).encode())


_env: DigestEnv | None = None


def _init(env_kwargs: dict) -> None:
    global _env
    _env = DigestEnv(**env_kwargs)


def _episode(policy: str, seed: int) -> tuple[str, dict]:
    started = time.perf_counter()
    episode = play(_env, POLICIES[policy](), seed)
    return f"{policy}/{seed}", {"digest": _env.digest.hexdigest(), "decisions": episode.decisions,
                                "seconds": round(time.perf_counter() - started, 2)}


def compare(new: dict, base: dict) -> list[str]:
    """The episodes whose digests differ, or that only one run has."""
    a, b = new["episodes"], base["episodes"]
    return sorted(k for k in a.keys() | b.keys() if k not in a or k not in b or a[k]["digest"] != b[k]["digest"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--policies", nargs="+", default=E1_POLICIES, choices=sorted(POLICIES))
    parser.add_argument("--seeds", type=int, default=30, help="seeds 0 .. N-1 (E1's 30 by default)")
    parser.add_argument("--hours", type=float, default=20.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--compare", type=Path, help="a digest file to check this run against")
    args = parser.parse_args()

    env_kwargs = {"horizon_ticks": round(args.hours * TICKS_PER_HOUR)}
    tasks = [(policy, seed) for policy in args.policies for seed in range(args.seeds)]
    at_start, started = provenance(), time.perf_counter()
    with ProcessPoolExecutor(args.workers, initializer=_init, initargs=(env_kwargs,)) as pool:
        episodes = dict(pool.map(_episode, *zip(*tasks)))
    result = {"policies": args.policies, "seeds": args.seeds, "env": env_kwargs, **at_start,
              "wall_seconds": round(time.perf_counter() - started, 1),
              "episode_seconds": round(sum(e["seconds"] for e in episodes.values()), 1), "episodes": episodes}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"{len(episodes)} episodes, {result['episode_seconds']}s of episodes in {result['wall_seconds']}s "
          f"-> {args.out}")
    if args.compare is not None:
        base = json.loads(args.compare.read_text(encoding="utf-8"))
        differ = compare(result, base)
        for policy in args.policies:
            mine = sum(e["seconds"] for k, e in episodes.items() if k.startswith(f"{policy}/"))
            theirs = sum(e["seconds"] for k, e in base["episodes"].items() if k.startswith(f"{policy}/"))
            print(f"  {policy:14s} {theirs:8.1f}s -> {mine:8.1f}s ({theirs / mine:.2f}x)" if mine else policy)
        print(f"{len(differ)} of {len(episodes)} episodes differ from {args.compare}" + (": " + ", ".join(differ[:10])
                                                                                       if differ else ""))
        sys.exit(1 if differ else 0)


if __name__ == "__main__":
    main()
