"""A trained policy as an eval-harness policy (rlscape/eval/harness.py), so a trained agent is evaluated on the same
seeds and checkpoints as E1's baselines.

A spec is `ppo:<path to model.zip>`, or `<label>=ppo:<path>` to name it in the tables (the label defaults to the whole
spec). E5's weight-conditioned agents take a weighting too, `<label>=ppo:<path>@<u>`: the normalised skill share u (the
wealth share is 1 − u), appended to each observation as in training (rlscape.agents.conditioned).

`TrainedPolicy` plays the model as it was trained, sampling from its masked action distribution (Caleb, 2026-11-09,
OQ-65 (4): sampled, not greedy), with torch's generator seeded by the episode's seed at its start, so an episode
depends only on the model and its seed, whatever the worker played before.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch as th

from rlscape.agents.ppo import SMDPMaskablePPO

PREFIX = "ppo:"
_MODELS: dict[Path, SMDPMaskablePPO] = {}  # one load a process


def is_trained(spec: str) -> bool:
    return spec.partition("=")[2].startswith(PREFIX) or spec.startswith(PREFIX)


def split(spec: str) -> tuple[str, Path]:
    """(label, model path) of a spec."""
    if spec.startswith(PREFIX):
        return spec, Path(_strip_preference(spec[len(PREFIX):])[0])
    label, _, rest = spec.partition("=")
    if not rest.startswith(PREFIX) or not label:
        raise ValueError(f"not a trained policy: {spec!r} (ppo:<model.zip> or <label>=ppo:<model.zip>)")
    return label, Path(_strip_preference(rest[len(PREFIX):])[0])


def _strip_preference(path: str) -> tuple[str, float | None]:
    """A spec's path and the skill share after an `@`, if it gives one."""
    head, at, tail = path.rpartition("@")
    if not at:
        return path, None
    u = float(tail)
    if not 0.0 <= u <= 1.0:
        raise ValueError(f"a preference's skill share is in [0, 1], not {u}")
    return head, u


def preference(spec: str) -> np.ndarray | None:
    """The normalised weighting (u, 1 − u) a spec gives its weight-conditioned agent, or None."""
    u = _strip_preference(spec.partition("=")[2] if not spec.startswith(PREFIX) else spec)[1]
    return None if u is None else np.array([u, 1.0 - u], dtype=np.float32)


def load(path: Path) -> SMDPMaskablePPO:
    path = Path(path).resolve()
    if path not in _MODELS:
        th.set_num_threads(1)  # an eval worker is one of many processes
        _MODELS[path] = SMDPMaskablePPO.load(path, device="cpu")
    return _MODELS[path]


class TrainedPolicy:
    def __init__(self, spec: str):
        self.name, self.path = split(spec)
        self.model = load(self.path)
        self.preference = preference(spec)

    def reset(self, seed: int | None) -> None:
        th.manual_seed(0 if seed is None else seed)

    def observation(self, obs: np.ndarray) -> np.ndarray:
        """The observation as the model sees it: a weight-conditioned agent's has its weighting appended, as
        rlscape.agents.conditioned.with_preference appends it in training. The replay reads the model's choices
        through this too."""
        return obs if self.preference is None else np.concatenate([obs, self.preference])

    def act(self, env, obs: np.ndarray) -> int:
        action, _ = self.model.predict(self.observation(obs), action_masks=env.action_masks(), deterministic=False)
        return int(action)
