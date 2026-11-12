"""A trained policy as an eval-harness policy (rlscape/eval/harness.py), so a trained agent is evaluated on the same
seeds and checkpoints as E1's baselines.

A spec is `ppo:<path to model.zip>`, or `<label>=ppo:<path>` to name it in the tables (the label defaults to the whole
spec). `TrainedPolicy` plays the model as it was trained, sampling from its masked action distribution (Caleb,
2026-11-09, OQ-65 (4): sampled, not greedy), with torch's generator seeded by the episode's seed at its start, so an
episode depends only on the model and its seed, whatever the worker played before.
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
        return spec, Path(spec[len(PREFIX):])
    label, _, rest = spec.partition("=")
    if not rest.startswith(PREFIX) or not label:
        raise ValueError(f"not a trained policy: {spec!r} (ppo:<model.zip> or <label>=ppo:<model.zip>)")
    return label, Path(rest[len(PREFIX):])


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

    def reset(self, seed: int | None) -> None:
        th.manual_seed(0 if seed is None else seed)

    def act(self, env, obs: np.ndarray) -> int:
        action, _ = self.model.predict(obs, action_masks=env.action_masks(), deterministic=False)
        return int(action)
