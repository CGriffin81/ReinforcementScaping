"""Training (scripts/train.py): SMDP MaskablePPO on the sim from one experiment's config, with periodic checkpoints,
TensorBoard, the decision logger and the run's provenance (ROADMAP's finishing plan; OQ-61's one config and one
command per experiment).

**The config** (`configs/<name>.yaml`, on the experiment's branch). Its keys:
- `seeds`: the runs' seeds; each seed is a run;
- `total_decisions`: decisions per run, over all envs;
- `n_envs`: the training envs;
- `vec_env`: `subproc` (each env in its own process) or `dummy` (all in this one);
- `device`: torch's (`cpu`, `cuda`, `auto`). On the GPU a run isn't bit-for-bit repeatable;
- `torch_threads`: torch's CPU threads in the run's own process (its envs are processes of their own). Several runs
  at once share the machine's 16 threads with their envs, so each wants a few;
- `env`: SimEnv's settings. `reward_weights` [w_skill, w_wealth] in SimEnv's units, or `normalised_weights`
  [u_skill, u_wealth] summing to 1, in units of E1's best 20-hour gain on each objective (OQ-67,
  rlscape.envs.weights; one or the other); `hours` (the horizon), `activity_minutes` (D) and `preference_in_obs`;
  SimEnv's defaults where one is left out;
- `ppo`: SMDPMaskablePPO's own arguments, passed as they are (`gamma_hr`, `n_steps`, `batch_size`, `n_epochs`,
  `learning_rate`, `ent_coef`, `policy_kwargs`, ...). Nothing here sets one: what isn't in the config is sb3's
  default;
- `checkpoint_every`: decisions between checkpoints;
- `decision_log`: record every decision (rlscape.agents.decision_log);
- `out`: where the runs go (default `runs/<name>`, git-ignored);
- `rnd` (E4): RND's exploration bonus (rlscape.agents.rnd): `coef`, the observation's parts it reads (`features`), and
  optionally its networks' and training's settings. Its predictor trains once a rollout (`ppo.n_steps`);
- `sweep`: a grid of variants, `{key: [values]}`, a key being `ppo.<argument>`, `env.<setting>`, `rnd.<setting>` or
  one of the keys above. Each combination is a variant, named by its values (`learning_rate0.0001_ent_coef0.01`), with
  its own runs.

**A run** (`<out>/seed<k>/`, or `<out>/<variant>/seed<k>/` in a sweep):
- `config.json`: the config, its hash, the seed, the provenance taken at the start (git SHAs, dirty, versions) and
  the command line;
- `options.json`: the catalog (index, id, family);
- `checkpoints/ppo_<decisions>_steps.zip`, then `model.zip`;
- `tb/`: TensorBoard. sb3's own curves, and `sim/*`: the means of the rollout's finished episodes; with RND, `rnd/*`
  (the bonus, the predictor's error and loss);
- `episodes.parquet`: the learning curve, a row per finished episode. Its `reward` is the env's weighted reward; what a
  training wrapper adds to it is apart (`REWARD_PARTS`);
- `decisions/`: the decision log;
- `run.json`: written at the end (decisions, episodes, wall time).

**Reward parts.** A wrapper that adds to the env's reward during training (E4's RND bonus, E6b's PBRS shaping) puts
the env's own reward in its step's info as `reward_extrinsic`, and its addition as one of `REWARD_PARTS`. The learning
curve sums each apart, and the decision log records them (rlscape.agents.decision_log); without a wrapper they're 0.

The same config and seed give the same run on the CPU: the envs are seeded from the seed (sb3's VecEnv seeding), and
an episode depends only on its seed (OQ-64).
"""

from __future__ import annotations

import copy
import itertools
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
import sb3_contrib
import stable_baselines3
import torch as th
import yaml
from stable_baselines3.common.callbacks import BaseCallback, CallbackList, CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecEnv, VecMonitor

from rlscape.agents.decision_log import DecisionLogger
from rlscape.agents.ppo import SMDPMaskablePPO
from rlscape.agents.rnd import KEYS as RND_KEYS
from rlscape.agents.rnd import RNDReward, check_rnd
from rlscape.envs.sim_env import SimEnv
from rlscape.envs.weights import env_weights
from rlscape.eval.harness import REPO, config_hash, provenance
from rlscape.sim.engine import TICKS_PER_HOUR

KEYS = {"seeds", "total_decisions", "n_envs", "vec_env", "device", "torch_threads", "env", "ppo", "checkpoint_every",
        "decision_log", "out", "sweep", "variant", "rnd"}
UNSWEPT = {"seeds", "out", "sweep", "variant"}  # a sweep can't vary these
REQUIRED = {"seeds", "total_decisions", "n_envs", "ppo"}
ENV_KEYS = {"reward_weights", "normalised_weights", "hours", "activity_minutes", "preference_in_obs"}
REWARD_PARTS = ("r_intrinsic", "r_shaping")  # added by a training wrapper: RND's bonus (E4), PBRS's shaping (E6b)


def load_config(path: Path) -> dict:
    return check_config(yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {})


def check_config(config: dict) -> dict:
    """Refuse a key the trainer doesn't know, a missing required one, and a number YAML read as text."""
    unknown, missing = sorted(set(config) - KEYS), sorted(REQUIRED - set(config))
    if unknown or missing:
        raise ValueError(f"config: unknown keys {unknown}, missing {missing}")
    env = config.get("env") or {}
    unknown_env = sorted(set(env) - ENV_KEYS)
    if unknown_env:
        raise ValueError(f"config: unknown env keys {unknown_env}; known: {sorted(ENV_KEYS)}")
    if "reward_weights" in env and "normalised_weights" in env:
        raise ValueError("config: env gives reward_weights or normalised_weights, not both")
    if "normalised_weights" in env:
        env_weights(env["normalised_weights"])  # refuses weights that aren't two non-negatives summing to 1
    for key, value in (config["ppo"] or {}).items():
        if isinstance(value, str):
            try:
                float(value)
            except ValueError:
                continue
            raise ValueError(f"config: ppo.{key} is the text {value!r}: YAML reads 3e-4 as text, so write 3.0e-4")
    if config.get("vec_env", "subproc") not in ("subproc", "dummy"):
        raise ValueError("config: vec_env is subproc or dummy")
    if config.get("rnd") is not None:
        check_rnd(config["rnd"])
    for key, values in (config.get("sweep") or {}).items():
        section, _, field = key.partition(".")
        known = (field and (section == "ppo" or (section == "env" and field in ENV_KEYS)
                            or (section == "rnd" and field in RND_KEYS))) or \
            (not field and section in KEYS - UNSWEPT)
        if not known or not isinstance(values, list) or not values:
            raise ValueError(f"config: sweep.{key} must be a known key with a list of values")
    return config


def variants(config: dict) -> list[tuple[str, dict]]:
    """The config's sweep as (variant, config) pairs: the grid's combinations in the order the sweep gives them,
    each the config with those values set, named by them; without a sweep, the one config, unnamed."""
    base = {k: v for k, v in config.items() if k != "sweep"}
    sweep = config.get("sweep") or {}
    if not sweep:
        return [("", base)]
    out = []
    for values in itertools.product(*sweep.values()):
        variant, parts = copy.deepcopy(base), []
        for key, value in zip(sweep, values):
            section, _, field = key.partition(".")
            if field:
                variant[section] = {**(variant.get(section) or {}), field: value}
            else:
                variant[section] = value
            parts.append(f"{field or section}{_named(value)}")
        variant["variant"] = "_".join(parts)
        out.append((variant["variant"], check_config(variant)))
    return out


def _named(value) -> str:
    if isinstance(value, (list, tuple)):
        return "-".join(_named(v) for v in value)
    return f"{value:g}" if isinstance(value, float) else str(value)


def env_kwargs(config: dict) -> dict:
    """SimEnv's keyword arguments from the config's `env`."""
    env, out = dict(config.get("env") or {}), {}
    if "reward_weights" in env:
        out["reward_weights"] = tuple(float(w) for w in env["reward_weights"])
    if "normalised_weights" in env:
        out["reward_weights"] = env_weights(env["normalised_weights"])
    if "hours" in env:
        out["horizon_ticks"] = round(float(env["hours"]) * TICKS_PER_HOUR)
    if "activity_minutes" in env:
        out["activity_ticks"] = round(float(env["activity_minutes"]) * 100)
    if "preference_in_obs" in env:
        out["preference_in_obs"] = bool(env["preference_in_obs"])
    return out


def make_vec_env(config: dict) -> VecEnv:
    factories = [partial(SimEnv, **env_kwargs(config)) for _ in range(int(config["n_envs"]))]
    vec = SubprocVecEnv(factories) if config.get("vec_env", "subproc") == "subproc" else DummyVecEnv(factories)
    return VecMonitor(vec)


class EpisodeTable(BaseCallback):
    """The learning curve: at each episode's end, a row with its decisions, its reward sums (the env's weighted
    reward, skill, wealth, and each of REWARD_PARTS), its deaths and its final metrics; and in TensorBoard, `sim/*`,
    their means over the rollout's episodes."""

    LOGGED = ("total_level", "net_worth", "total_xp", "r_skill", "r_wealth", "reward", *REWARD_PARTS, "decisions",
              "deaths")

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        self._recent: list[dict] = []

    def _on_training_start(self) -> None:
        n = self.training_env.num_envs
        self._sums = np.zeros((n, 3 + len(REWARD_PARTS)))
        self._decisions, self._deaths = np.zeros(n, int), np.zeros(n, int)

    def _on_step(self) -> bool:
        rewards, dones, infos = self.locals["rewards"], self.locals["dones"], self.locals["infos"]
        for i, info in enumerate(infos):
            extrinsic = info.get("reward_extrinsic", float(rewards[i]))
            self._sums[i] += (extrinsic, *info["reward_vec"], *(info.get(part, 0.0) for part in REWARD_PARTS))
            self._decisions[i] += 1
            self._deaths[i] += info["termination"] == "died"
            if dones[i]:
                row = {"step": self.num_timesteps, "env": i, "decisions": int(self._decisions[i]),
                       "reward": self._sums[i, 0], "r_skill": self._sums[i, 1], "r_wealth": self._sums[i, 2],
                       **{part: self._sums[i, 3 + k] for k, part in enumerate(REWARD_PARTS)},
                       "deaths": int(self._deaths[i]), "game_ticks": info["game_ticks"],
                       "total_level": info["total_level"], "total_xp": info["total_xp"],
                       "net_worth": info["net_worth"]}
                self.rows.append(row)
                self._recent.append(row)
                self._sums[i], self._decisions[i], self._deaths[i] = 0.0, 0, 0
        return True

    def _on_rollout_end(self) -> None:
        if self._recent:
            for key in self.LOGGED:
                self.logger.record(f"sim/{key}", float(np.mean([row[key] for row in self._recent])))
            self.logger.record("sim/episodes", len(self._recent))
            self._recent = []

    def table(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["step", "env", "decisions", "reward", "r_skill", "r_wealth",
                                                *REWARD_PARTS, "deaths", "game_ticks", "total_level", "total_xp",
                                                "net_worth"])


class RNDStats(BaseCallback):
    """TensorBoard's `rnd/*` once a rollout: the bonus and the predictor's error (means since the last), its loss."""

    def _on_step(self) -> bool:
        return True

    def _on_rollout_end(self) -> None:
        for key, value in self.training_env.take_stats().items():
            self.logger.record(f"rnd/{key}", value)


def with_rnd(vec: VecEnv, config: dict, seed: int) -> VecEnv:
    """The training envs with RND's bonus when the config has `rnd`, its predictor trained once a rollout."""
    if not config.get("rnd"):
        return vec
    parts = vec.get_attr("encoder", indices=[0])[0].parts
    rnd = config["rnd"]
    return RNDReward(vec, parts, seed=seed, rollout=int((config["ppo"] or {}).get("n_steps", 2048)), **rnd)


def run_dir(config: dict, name: str, seed: int) -> Path:
    root = Path(config.get("out") or REPO / "runs" / name)
    return (root / config["variant"] if config.get("variant") else root) / f"seed{seed}"


def train(config: dict, name: str, seed: int, out: Path | None = None, force: bool = False,
          argv: list[str] | None = None) -> Path:
    """One run of the experiment `name` with `seed` (one variant: expand a sweep with `variants` first); returns its
    directory."""
    config = check_config(config)
    if config.get("sweep"):
        raise ValueError("train takes one variant: expand the sweep with variants()")
    run = Path(out) if out is not None else run_dir(config, name, seed)
    if run.exists():
        if not force:
            raise FileExistsError(f"{run} exists; pass force to replace it")
        shutil.rmtree(run)
    run.mkdir(parents=True)
    meta = {"name": name, "seed": seed, "config": config, "config_hash": config_hash(config),
            "env_kwargs": env_kwargs(config), **provenance(), "torch": th.__version__,
            "stable_baselines3": stable_baselines3.__version__, "sb3_contrib": sb3_contrib.__version__,
            "script": "scripts/train.py", "argv": list(sys.argv[1:] if argv is None else argv)}
    (run / "config.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

    started = time.perf_counter()
    if config.get("torch_threads"):
        th.set_num_threads(int(config["torch_threads"]))
    vec = make_vec_env(config)
    try:
        vec = with_rnd(vec, config, seed)
        catalog = vec.env_method("option_catalog", indices=[0])[0]
        (run / "options.json").write_text(json.dumps([{"index": o.action, "id": o.id, "family": o.family}
                                                      for o in catalog], indent=0), encoding="utf-8")
        kwargs = dict(config["ppo"])
        if "device" in config:
            kwargs["device"] = config["device"]
        model = SMDPMaskablePPO("MlpPolicy", vec, seed=seed, tensorboard_log=str(run / "tb"), verbose=0, **kwargs)
        if config.get("decision_log", True):
            model.decision_logger = DecisionLogger(run / "decisions", vec.num_envs)
        n_envs = vec.num_envs
        episodes = EpisodeTable()
        callbacks = [episodes] + ([RNDStats()] if config.get("rnd") else [])
        if config.get("checkpoint_every"):
            callbacks.append(CheckpointCallback(max(int(config["checkpoint_every"]) // n_envs, 1),
                                                str(run / "checkpoints"), name_prefix="ppo"))
        model.learn(total_timesteps=int(config["total_decisions"]), callback=CallbackList(callbacks),
                    tb_log_name="ppo")
        model.save(run / "model.zip")
        if model.decision_logger is not None:
            model.decision_logger.flush()
        episodes.table().to_parquet(run / "episodes.parquet", index=False)
        (run / "run.json").write_text(json.dumps({
            "decisions": int(model.num_timesteps), "episodes": len(episodes.rows),
            "wall_seconds": round(time.perf_counter() - started, 1),
            "finished": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=2), encoding="utf-8")
    finally:
        vec.close()
    return run
