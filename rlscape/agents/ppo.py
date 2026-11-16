"""MaskablePPO with SMDP discounting (ROADMAP §3: "Subclass sb3-contrib's MaskableRolloutBuffer (plus a small
`collect_rollouts` override to store τ) so GAE uses γ^τ. Define γ per game-hour").

- `SMDPMaskableRolloutBuffer` stores each decision's duration τ (ticks, `info["duration"]`) beside the usual rollout,
  and computes advantages and value targets with `rlscape.agents.smdp.smdp_gae`: a decision that took τ game-hours is
  discounted by γ_hr^τ.
- `SMDPMaskablePPO` is MaskablePPO with that buffer. Its `collect_rollouts` is the parent's with two changes: it reads
  τ from the step's infos into the buffer, and a time limit's bootstrap (sb3's `TimeLimit.truncated`, the episode's
  20 game-hours, env contract §1) is discounted by γ_hr^τ, not by one γ a decision. sb3's per-decision `gamma` is set
  to 1 and unused.
- `decision_logger` (rlscape.agents.decision_log), when set, gets every step of the rollout: what the policy saw,
  its whole action distribution (one more pass of the policy, which draws no random numbers, so the run is the same
  with or without it), its value, and what the env returned. It isn't saved with the model.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch as th
from gymnasium import spaces
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.buffers import MaskableRolloutBuffer
from sb3_contrib.common.maskable.utils import get_action_masks, is_masking_supported
from stable_baselines3.common.buffers import RolloutBuffer
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.utils import obs_as_tensor
from stable_baselines3.common.vec_env import VecEnv

from rlscape.agents.decision_log import DecisionLogger
from rlscape.agents.smdp import option_discounts, smdp_gae


class SMDPMaskableRolloutBuffer(MaskableRolloutBuffer):
    """A MaskableRolloutBuffer that also stores each decision's duration, and discounts by game time."""

    def __init__(self, *args: Any, gamma_hr: float = 0.99, discount_floor_ticks: float = 0.0, **kwargs: Any):
        self.gamma_hr, self.discount_floor_ticks = gamma_hr, discount_floor_ticks
        super().__init__(*args, **kwargs)

    def reset(self) -> None:
        self.durations = np.zeros((self.buffer_size, self.n_envs), dtype=np.float64)
        super().reset()

    def add(self, *args: Any, durations: np.ndarray | None = None, **kwargs: Any) -> None:
        if durations is None:
            raise ValueError("an SMDP rollout needs each decision's duration (info['duration'], in ticks)")
        self.durations[self.pos] = np.asarray(durations, dtype=np.float64)
        super().add(*args, **kwargs)

    def compute_returns_and_advantage(self, last_values: th.Tensor, dones: np.ndarray) -> None:
        """smdp_gae over the rollout. sb3 marks an episode's first decision (`episode_starts`); smdp_gae wants the
        decision an episode ended at: the one before each start, and, for the rollout's last, `dones`."""
        ended = np.zeros(self.episode_starts.shape, dtype=bool)
        ended[:-1] = self.episode_starts[1:].astype(bool)
        ended[-1] = np.asarray(dones, dtype=bool)
        advantages, returns = smdp_gae(self.rewards, self.values, self.durations, ended,
                                       last_values.clone().cpu().numpy().flatten(), self.gamma_hr, self.gae_lambda,
                                       self.discount_floor_ticks)
        self.advantages[:] = advantages
        self.returns = returns.astype(np.float32)


class SMDPMaskablePPO(MaskablePPO):
    """MaskablePPO whose discount is γ_hr per game-hour of each decision's duration (rlscape.agents.smdp)."""

    def __init__(self, policy: Any, env: Any, gamma_hr: float = 0.99, bootstrap_horizon: bool = True,
                 discount_floor_ticks: float = 0.0, **kwargs: Any):
        """`bootstrap_horizon`: whether the 20-hour horizon's step gets γ_hr^τ·V(final observation) added, as a time
        limit's would. True is how every run to 2026-11-15 trained. False treats the horizon as the task's end, with
        nothing left to earn (2026-11-15, the collapse diagnosis): the observation carries the time left, and with
        the bootstrap nothing pins the critic's value at the end, so it can drift (decision log).

        `discount_floor_ticks`: each decision is discounted as if it took at least this many ticks (rlscape.agents.smdp,
        the decision floor). 0, how every run to 2026-11-15 trained, is the plain γ_hr^τ."""
        if "gamma" in kwargs:
            raise ValueError("SMDPMaskablePPO discounts by gamma_hr per game-hour; sb3's per-decision gamma is unused")
        self.gamma_hr = gamma_hr
        self.bootstrap_horizon = bootstrap_horizon
        self.discount_floor_ticks = discount_floor_ticks
        self.decision_logger: DecisionLogger | None = None
        kwargs.setdefault("rollout_buffer_class", SMDPMaskableRolloutBuffer)
        kwargs["rollout_buffer_kwargs"] = {**(kwargs.get("rollout_buffer_kwargs") or {}), "gamma_hr": gamma_hr,
                                           "discount_floor_ticks": discount_floor_ticks}
        super().__init__(policy, env, gamma=1.0, **kwargs)

    def _excluded_save_params(self) -> list[str]:
        return [*super()._excluded_save_params(), "decision_logger"]

    def collect_rollouts(self, env: VecEnv, callback: BaseCallback, rollout_buffer: RolloutBuffer,
                         n_rollout_steps: int, use_masking: bool = True) -> bool:
        """MaskablePPO.collect_rollouts (sb3-contrib 2.9), storing each decision's duration, with a time limit's
        bootstrap discounted by γ_hr^τ."""
        assert isinstance(rollout_buffer, SMDPMaskableRolloutBuffer), "SMDPMaskablePPO needs its SMDP rollout buffer"
        assert self._last_obs is not None, "No previous observation was provided"
        self.policy.set_training_mode(False)
        n_steps, action_masks = 0, None
        rollout_buffer.reset()
        if use_masking and not is_masking_supported(env):
            raise ValueError("Environment does not support action masking. Consider using ActionMasker wrapper")
        callback.on_rollout_start()
        while n_steps < n_rollout_steps:
            with th.no_grad():
                obs_tensor = obs_as_tensor(self._last_obs, self.device)  # type: ignore[arg-type]
                if use_masking:
                    action_masks = get_action_masks(env)
                actions, values, log_probs = self.policy(obs_tensor, action_masks=action_masks)
                probs = None
                if self.decision_logger is not None:
                    probs = self.policy.get_distribution(obs_tensor, action_masks=action_masks).distribution.probs
            actions = actions.cpu().numpy()
            new_obs, rewards, dones, infos = env.step(actions)
            if self.decision_logger is not None:
                if action_masks is None:
                    raise ValueError("the decision logger records the mask: train with masking")
                self.decision_logger.record(self.num_timesteps, self._last_obs, action_masks, actions,
                                            probs.cpu().numpy(), log_probs.cpu().numpy(),
                                            values.cpu().numpy().flatten(), rewards, dones, infos)
            self.num_timesteps += env.num_envs
            callback.update_locals(locals())
            if not callback.on_step():
                return False
            self._update_info_buffer(infos, dones)
            n_steps += 1
            if isinstance(self.action_space, spaces.Discrete):
                actions = actions.reshape(-1, 1)
            durations = np.array([info["duration"] for info in infos], dtype=np.float64)
            for idx, done in enumerate(dones):  # a time limit: bootstrap the cut-off value (sb3 issue #633)
                if self.bootstrap_horizon and done and infos[idx].get("terminal_observation") is not None \
                        and infos[idx].get("TimeLimit.truncated", False):
                    terminal_obs = self.policy.obs_to_tensor(infos[idx]["terminal_observation"])[0]
                    with th.no_grad():
                        terminal_value = self.policy.predict_values(terminal_obs)[0]
                    rewards[idx] += float(option_discounts(durations[idx : idx + 1], self.gamma_hr,
                                                           self.discount_floor_ticks)[0]) * float(terminal_value)
            rollout_buffer.add(self._last_obs, actions, rewards, self._last_episode_starts, values, log_probs,
                               action_masks=action_masks, durations=durations)
            self._last_obs = new_obs  # type: ignore[assignment]
            self._last_episode_starts = dones
        with th.no_grad():
            values = self.policy.predict_values(obs_as_tensor(new_obs, self.device))  # type: ignore[arg-type]
        rollout_buffer.compute_returns_and_advantage(last_values=values, dones=dones)
        callback.on_rollout_end()
        return True
