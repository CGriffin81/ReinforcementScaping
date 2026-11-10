"""The decision logger. CLAUDE.md: "Log every agent decision (obs, mask, option, action probabilities, value,
duration, reward components)". ROADMAP: RQ2's analysis reads these logs, and they can't be made again afterwards.

`DecisionLogger.record` takes one step of the training envs (SMDPMaskablePPO.collect_rollouts calls it) and keeps a
row per env. Every `rows_per_part` rows go to `<dir>/part-NNNNN.parquet` (zstd). A 1M-decision run is well under a
gigabyte: an observation has about 217 non-zero features of 3,482, and the parts compress them across rows.

The columns:
- **Where:** `step` (the run's decisions before this step: sb3's num_timesteps), `env`, `episode` (that env's
  episode number, from 0) and `decision` (its number in the episode, from 0).
- **What the policy saw and did:**
  - `obs`: the observation (float32, env contract §3; it holds the mask too);
  - `mask`: the action mask as packed bits (`unpack_mask`);
  - `action`: the catalog index (the run's options.json names each, with its family);
  - `probs`: the policy's probability of each available action, in the mask's order, summing to 1;
  - `log_prob` of the action and `value` of the state, the policy's at that moment.
- **What happened:**
  - `reward` (weighted), `r_skill` and `r_wealth` (info["reward_vec"]);
  - `duration` in ticks;
  - `termination`;
  - `option`, the info's option record as JSON (the path a slot ran, the target and style of a fight).
- **After the step:** `game_ticks`, `total_level`, `total_xp`, `net_worth` and `coins`, and `done` (the episode
  ended at it, terminated or truncated).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

SCALARS = {
    "step": pa.int64(), "env": pa.int16(), "episode": pa.int32(), "decision": pa.int32(), "action": pa.int16(),
    "log_prob": pa.float32(), "value": pa.float32(), "reward": pa.float32(), "r_skill": pa.float32(),
    "r_wealth": pa.float32(), "duration": pa.int32(), "termination": pa.string(), "option": pa.string(),
    "game_ticks": pa.int32(), "total_level": pa.int16(), "total_xp": pa.float64(), "net_worth": pa.float64(),
    "coins": pa.int64(), "done": pa.bool_(),
}


class DecisionLogger:
    def __init__(self, out_dir: Path, n_envs: int, rows_per_part: int = 50_000):
        self.dir = Path(out_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.rows_per_part, self.part = rows_per_part, 0
        self.episode = np.zeros(n_envs, dtype=np.int64)
        self.decision = np.zeros(n_envs, dtype=np.int64)
        self._clear()

    def _clear(self) -> None:
        self.columns: dict[str, list] = {name: [] for name in (*SCALARS, "obs", "mask", "probs")}

    def __len__(self) -> int:
        return len(self.columns["step"])

    def record(self, step: int, obs: np.ndarray, masks: np.ndarray, actions: np.ndarray, probs: np.ndarray,
               log_probs: np.ndarray, values: np.ndarray, rewards: np.ndarray, dones: np.ndarray,
               infos: list[dict]) -> None:
        """One step of every env: what each env's policy saw (`obs`, `masks`) and chose, with the full action
        distribution `probs` (n_envs × actions), and the env's reward, end and info after it."""
        c = self.columns
        for i, info in enumerate(infos):
            mask = np.asarray(masks[i], dtype=bool)
            c["step"].append(step)
            c["env"].append(i)
            c["episode"].append(int(self.episode[i]))
            c["decision"].append(int(self.decision[i]))
            c["action"].append(int(actions[i]))
            c["log_prob"].append(float(log_probs[i]))
            c["value"].append(float(values[i]))
            c["reward"].append(float(rewards[i]))
            c["r_skill"].append(float(info["reward_vec"][0]))
            c["r_wealth"].append(float(info["reward_vec"][1]))
            c["duration"].append(int(info["duration"]))
            c["termination"].append(str(info["termination"]))
            c["option"].append(json.dumps(info["option"], default=str))
            for key in ("game_ticks", "total_level", "total_xp", "net_worth", "coins"):
                c[key].append(info[key])
            c["done"].append(bool(dones[i]))
            c["obs"].append(np.asarray(obs[i], dtype=np.float32))
            c["mask"].append(np.packbits(mask).tobytes())
            c["probs"].append(np.asarray(probs[i], dtype=np.float32)[mask])
            if dones[i]:
                self.episode[i] += 1
                self.decision[i] = 0
            else:
                self.decision[i] += 1
        if len(self) >= self.rows_per_part:
            self.flush()

    def flush(self) -> None:
        """Write the rows held as the next part."""
        if not len(self):
            return
        c = self.columns
        obs = np.stack(c["obs"])
        arrays = {name: pa.array(c[name], type=kind) for name, kind in SCALARS.items()}
        arrays["obs"] = pa.FixedSizeListArray.from_arrays(pa.array(obs.ravel(), type=pa.float32()), obs.shape[1])
        arrays["mask"] = pa.array(c["mask"], type=pa.binary())
        arrays["probs"] = pa.array(c["probs"], type=pa.list_(pa.float32()))
        pq.write_table(pa.table(arrays), self.dir / f"part-{self.part:05d}.parquet", compression="zstd")
        self.part += 1
        self._clear()


def read_decisions(log_dir: Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Every part of a run's decision log, in order."""
    parts = sorted(Path(log_dir).glob("part-*.parquet"))
    return pd.concat([pq.read_table(p, columns=columns).to_pandas() for p in parts], ignore_index=True)


def unpack_mask(packed: bytes, n_actions: int) -> np.ndarray:
    return np.unpackbits(np.frombuffer(packed, dtype=np.uint8))[:n_actions].astype(bool)
