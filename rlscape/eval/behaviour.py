"""What a training run's policy did as it learned, read from its decision log (rlscape/agents/decision_log.py) into
small tables an experiment's training summary carries (rlscape.eval.publish.publish_training). The proposal's
time-allocation plot across training, its first-discovery timeline and its action entropy are read from them (§6),
since the logs themselves (about 1.2 GB a 2M-decision run) stay out of git.

`training_behaviour(run, bin_decisions)` returns three tables. A bin is `bin_decisions` of the run's decisions, by
default its checkpoint interval, so each bin ends at a saved checkpoint:
- **bins:** a row per bin: its decisions, game ticks and episodes (those with a decision in it, and those that ended
  in it); the policy's mean entropy (nats) over the options open, and the mean number of options open;
- **options:** a row per (bin, option chosen in it): its decisions, its game ticks, and the episodes that chose it.
  The analysis groups options into activities and decides what counts as taking one up;
- **first:** a row per option ever chosen: the run's decisions before it was first chosen (`step`, the log's), and
  the env and episode that chose it.

Each table names options by their catalog id and family (the run's options.json).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

COLUMNS = ["step", "env", "episode", "action", "duration", "done", "probs"]
DEFAULT_BIN = 100_000


def entropy(probs: pa.ChunkedArray) -> tuple[np.ndarray, np.ndarray]:
    """Each row's entropy (nats) and length, for a column of probability lists (the log's `probs`: the policy's
    probability of each open option, summing to 1)."""
    entropies, lengths = [], []
    for chunk in probs.chunks:
        offsets = chunk.offsets.to_numpy()  # into chunk.values, a slice's included
        p = chunk.values.to_numpy(zero_copy_only=False).astype(np.float64)
        terms = np.zeros_like(p)
        np.multiply(-p, np.log(p, where=p > 0, out=np.zeros_like(p)), out=terms, where=p > 0)
        sums = np.concatenate([[0.0], np.cumsum(terms)])
        entropies.append(sums[offsets[1:]] - sums[offsets[:-1]])
        lengths.append(np.diff(offsets))
    return np.concatenate(entropies), np.concatenate(lengths)


def read_log(run: Path) -> pd.DataFrame:
    """The log's columns the tables need, a part at a time (the observations are never read), with each decision's
    entropy and options open."""
    parts = sorted((Path(run) / "decisions").glob("part-*.parquet"))
    if not parts:
        raise FileNotFoundError(f"{run} has no decision log")
    frames = []
    for part in parts:
        table = pq.read_table(part, columns=COLUMNS)
        frame = table.drop(["probs"]).to_pandas()
        frame["entropy"], frame["open"] = entropy(table.column("probs"))
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def training_behaviour(run: Path, bin_decisions: int | None = None) -> dict[str, pd.DataFrame]:
    """The run's bins, options and first choices (see the module's docstring)."""
    run = Path(run)
    if bin_decisions is None:
        config = json.loads((run / "config.json").read_text(encoding="utf-8"))["config"]
        bin_decisions = int(config.get("checkpoint_every") or DEFAULT_BIN)
    catalog = pd.DataFrame(json.loads((run / "options.json").read_text(encoding="utf-8")))
    ids, families = catalog.set_index("index")["id"], catalog.set_index("index")["family"]
    log = read_log(run)
    log["bin"] = log["step"] // bin_decisions
    log["ep"] = log["env"].astype(np.int64) * 1_000_000_000 + log["episode"]

    bins = log.groupby("bin").agg(decisions=("action", "size"), ticks=("duration", "sum"),
                                  episodes=("ep", "nunique"), ended=("done", "sum"), entropy=("entropy", "mean"),
                                  open=("open", "mean")).reset_index()
    bins.insert(1, "from_step", bins["bin"] * bin_decisions)
    bins.insert(2, "to_step", (bins["bin"] + 1) * bin_decisions)

    options = log.groupby(["bin", "action"]).agg(decisions=("ep", "size"), ticks=("duration", "sum"),
                                                 episodes=("ep", "nunique")).reset_index()
    first = log.loc[log.groupby("action")["step"].idxmin(), ["action", "step", "env", "episode"]]
    first = first.sort_values(["step", "env", "action"], ignore_index=True)
    for table in (options, first):
        position = table.columns.get_loc("action")
        table.insert(position + 1, "option", table["action"].map(ids))
        table.insert(position + 2, "family", table["action"].map(families))
    return {"bins": bins, "options": options, "first": first}
