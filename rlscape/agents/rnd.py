"""Random network distillation (Burda, Edwards, Storkey & Klimov 2019, [8]) for E4, PPO + RND (RQ2, RQ4, H3; ROADMAP
§3's v1: a VecEnv wrapper that adds a normalised intrinsic reward for MaskablePPO).

`RNDReward` wraps the training envs. After every step it scores how unfamiliar each env's next state is: the squared
error, per feature, of a trained *predictor* network against a fixed, randomly initialised *target* network, both
reading the parts of the observation the config names (`features`). The bonus

    r_intrinsic = coef × (error − μ) / σ

is added to the reward PPO learns from. μ and σ are the error's recent mean and standard deviation per decision, so
`coef` is the bonus's spread in reward units. At each rollout's end the predictor is trained on that rollout's states,
so states the agent keeps reaching stop paying, and new ones (an item never held, a region never visited, a level
never reached) pay until they're familiar.

**Centred** (`centre`, the default): taking μ off makes the bonus average zero per decision. Novel states pay, and
familiar ones cost a little. Decisions here last from seconds (a drop, a GE offer) to 15 game-minutes, so a bonus with
a positive mean would pay the agent for making more, shorter decisions. Burda's steps are all one length; its bonus
isn't centred, and it's scaled by the spread of the bonus's discounted return. `centre: false` leaves μ in.

**Recent, not cumulative** (Caleb, 2026-11-11, OQ-79 (a)): a centred bonus's μ and σ are an exponential moving
average over about the last `ema_rollouts` rollouts (10), bias-corrected as Adam's moments are (`RecentStats`). The
predictor keeps learning, so its errors fall, and a bonus centred on a mean that remembers higher errors sits below
zero: a small cost on every decision, which centring was meant to avoid. A recent mean forgets them within the window.
Measured at E4's scale (4 envs, rollouts of 256 steps, random actions): the error falls from 0.98 to about 0.3 over
the first 10 rollouts, while both centrings average about −0.5 spreads; over rollouts 12 to 20 the recent one averages
about −0.2 and the cumulative one −0.3. So the drift is in the first one or two percent of a run, while the
predictor learns fastest, and the recent mean ends it sooner. `centre: false` keeps the cumulative statistics.

- **One value head (v1).** The bonus is part of the reward. Episodes end only at the 20-hour limit (the sim never
  terminates one, env contract §1). Until 2026-11-15 every run bootstrapped that limit (rlscape.agents.ppo), so the
  bonus wasn't cut off there. From env contract v1.46 the limit is the task's end (`ppo.bootstrap_horizon: false`):
  one value head can't treat the bonus apart from the env's reward, so the bonus too stops at 20 hours, as an
  episodic bonus does. ROADMAP §3's v2, a second value head, is for if v1's results are ambiguous.
- **Inputs** are normalised per feature by a running mean and standard deviation and clipped to ±5, as Burda's are. A
  feature that has never varied makes any change from it strongly novel (clipped at 5). The first rollout pays no
  bonus: it fills those statistics.
- **Kept apart:** each step's infos get `reward_extrinsic` (the env's weighted reward) and `r_intrinsic` (the bonus),
  so the learning curve and the decision log report them separately (rlscape.agents.training, decision_log).
- **Seeded:** the networks' initial weights and the minibatch order come from the run's seed; on the CPU a run is
  repeatable.
- **Networks** (Burda's shapes as MLPs): target in→256→256→128, frozen; predictor in→256→256→256→128; ReLU,
  orthogonal initialisation; Adam.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import torch as th
from stable_baselines3.common.running_mean_std import RunningMeanStd
from stable_baselines3.common.vec_env import VecEnv, VecEnvWrapper

CLIP = 5.0
EPS = 1e-8
DEFAULTS = {"centre": True, "ema_rollouts": 10, "hidden": 256, "out": 128, "learning_rate": 1e-4, "epochs": 4,
            "batch_size": 256}
KEYS = {"coef", "features", *DEFAULTS}


def check_rnd(rnd: Mapping, parts: Sequence[str] | None = None) -> None:
    """Refuse an rnd section with an unknown key, no positive `coef`, or no `features` (or one not in `parts`)."""
    unknown = sorted(set(rnd) - KEYS)
    if unknown:
        raise ValueError(f"config: unknown rnd keys {unknown}; known: {sorted(KEYS)}")
    if not isinstance(rnd.get("coef"), (int, float)) or rnd["coef"] <= 0:
        raise ValueError("config: rnd.coef must be a positive number")
    features = rnd.get("features")
    if not isinstance(features, list) or not features or not all(isinstance(f, str) for f in features):
        raise ValueError("config: rnd.features must list the observation's parts RND reads")
    if parts is not None and set(features) - set(parts):
        raise ValueError(f"config: rnd.features {sorted(set(features) - set(parts))} aren't parts of the "
                         f"observation: {list(parts)}")


class RecentStats:
    """An exponential moving average of a quantity's mean and second moment over about `window` updates, each a batch
    (one step of every env), bias-corrected as Adam's moments are, so the first updates aren't pulled towards 0. It
    follows a level that drifts, as a learning predictor's error does (OQ-79 (a))."""

    def __init__(self, window: float):
        if window < 1:
            raise ValueError(f"an average over {window} updates")
        self.alpha = 1.0 / float(window)
        self.m1 = self.m2 = 0.0
        self.weight = 0.0  # 1 − (1 − alpha)^updates: what the bias correction divides by

    def update(self, x: np.ndarray) -> None:
        a = self.alpha
        self.m1 = (1 - a) * self.m1 + a * float(np.mean(x))
        self.m2 = (1 - a) * self.m2 + a * float(np.mean(np.square(x)))
        self.weight = (1 - a) * self.weight + a

    @property
    def mean(self) -> float:
        return self.m1 / self.weight if self.weight else 0.0

    @property
    def var(self) -> float:
        return max(self.m2 / self.weight - self.mean ** 2, 0.0) if self.weight else 1.0


def _mlp(sizes: Sequence[int], generator: th.Generator) -> th.nn.Sequential:
    layers: list[th.nn.Module] = []
    for i, (a, b) in enumerate(zip(sizes, sizes[1:])):
        linear = th.nn.Linear(a, b)
        th.nn.init.orthogonal_(linear.weight, gain=np.sqrt(2), generator=generator)
        th.nn.init.zeros_(linear.bias)
        layers.append(linear)
        if i < len(sizes) - 2:
            layers.append(th.nn.ReLU())
    return th.nn.Sequential(*layers)


class RNDReward(VecEnvWrapper):
    """Adds RND's bonus to the training envs' rewards; trains its predictor every `rollout` steps (PPO's n_steps)."""

    def __init__(self, venv: VecEnv, parts: Mapping[str, slice], features: Sequence[str], coef: float, seed: int,
                 rollout: int, centre: bool = True, ema_rollouts: float = 10, hidden: int = 256, out: int = 128,
                 learning_rate: float = 1e-4, epochs: int = 4, batch_size: int = 256):
        super().__init__(venv)
        check_rnd({"coef": coef, "features": list(features)}, list(parts))
        self.features, self.coef, self.rollout, self.centre = list(features), float(coef), int(rollout), bool(centre)
        self.epochs, self.batch_size = int(epochs), int(batch_size)
        self.index = np.concatenate([np.arange(parts[f].start, parts[f].stop) for f in self.features])
        generator = th.Generator().manual_seed(int(seed))
        n = len(self.index)
        self.target = _mlp([n, hidden, hidden, out], generator).requires_grad_(False)
        self.predictor = _mlp([n, hidden, hidden, hidden, out], generator)
        self.optimizer = th.optim.Adam(self.predictor.parameters(), lr=learning_rate)
        self.rng = np.random.default_rng(int(seed))
        self.obs_rms = RunningMeanStd(shape=(n,))
        # the error's statistics: recent for a centred bonus (OQ-79 (a)), cumulative for Burda's uncentred one
        self.error_rms = RecentStats(ema_rollouts * self.rollout) if self.centre else RunningMeanStd(shape=())
        self.ready = False  # the first rollout only fills the input statistics
        self.pending: list[np.ndarray] = []
        self.steps = 0
        self.stats = {"bonus": [], "error": [], "loss": float("nan")}

    def reset(self) -> np.ndarray:
        return self.venv.reset()

    def _normalised(self, x: np.ndarray) -> th.Tensor:
        z = (x - self.obs_rms.mean) / np.sqrt(self.obs_rms.var + EPS)
        return th.as_tensor(np.clip(z, -CLIP, CLIP), dtype=th.float32)

    def errors(self, x: np.ndarray) -> np.ndarray:
        """The predictor's squared error against the target, per row of RND's inputs (not yet normalised)."""
        with th.no_grad():
            z = self._normalised(x)
            return ((self.predictor(z) - self.target(z)) ** 2).mean(dim=1).numpy().astype(np.float64)

    def step_wait(self):
        obs, rewards, dones, infos = self.venv.step_wait()
        following = np.array(obs, dtype=np.float32, copy=True)  # each env's next state
        for i, done in enumerate(dones):  # a finished episode's is its last, not the next one's first
            if done and infos[i].get("terminal_observation") is not None:
                following[i] = infos[i]["terminal_observation"]
        x = following[:, self.index]
        bonus = np.zeros(len(rewards), dtype=np.float64)
        if self.ready:
            error = self.errors(x)
            self.error_rms.update(error)
            centred = error - self.error_rms.mean if self.centre else error
            bonus = self.coef * centred / np.sqrt(self.error_rms.var + EPS)
            self.stats["error"].extend(error.tolist())
        self.stats["bonus"].extend(bonus.tolist())
        for i, info in enumerate(infos):
            info["reward_extrinsic"], info["r_intrinsic"] = float(rewards[i]), float(bonus[i])
        self.pending.append(x)
        self.steps += 1
        if self.steps % self.rollout == 0:
            self.train_predictor()
        return obs, (rewards + bonus).astype(rewards.dtype), dones, infos

    def train_predictor(self) -> None:
        """Update the input statistics with the rollout's states, then fit the predictor to them."""
        batch = np.concatenate(self.pending)
        self.pending = []
        self.obs_rms.update(batch)
        self.ready = True
        z = self._normalised(batch)
        with th.no_grad():
            goal = self.target(z)
        losses = []
        for _ in range(self.epochs):
            order = self.rng.permutation(len(z))
            for start in range(0, len(z), self.batch_size):
                rows = th.as_tensor(order[start:start + self.batch_size])
                loss = ((self.predictor(z[rows]) - goal[rows]) ** 2).mean()
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                losses.append(float(loss.detach()))
        self.stats["loss"] = float(np.mean(losses))

    def take_stats(self) -> dict[str, float]:
        """The means since the last call (TensorBoard's `rnd/*`, once a rollout), and resets them."""
        bonus, error = self.stats["bonus"], self.stats["error"]
        out = {"bonus": float(np.mean(bonus)) if bonus else 0.0, "bonus_std": float(np.std(bonus)) if bonus else 0.0,
               "error": float(np.mean(error)) if error else 0.0, "predictor_loss": self.stats["loss"],
               "error_std": float(np.sqrt(self.error_rms.var))}
        self.stats["bonus"], self.stats["error"] = [], []
        return out
