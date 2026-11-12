"""Replays (rlscape/eval/replay.py, scripts/replay.py): a replay is the evaluation's episode, recorded whole, and the
page carries it intact."""

from __future__ import annotations

import base64
import importlib.util
import io
import json
import math

import pandas as pd
import pytest

from rlscape.eval.harness import REPO
from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")

E2 = REPO / "results" / "summary" / "e2-ppo-sanity-ladder" / "episodes.csv"
BEST = REPO / "runs" / "e2-ppo-sanity-ladder" / "gae_lambda0.95_learning_rate0.0003" / "seed0" / "model.zip"


@pytest.fixture(scope="module")
def guide():
    from rlscape.envs.sim_env import SimEnv
    from rlscape.eval.harness import make_policy
    from rlscape.eval.replay import Walks, record
    return record(SimEnv(), make_policy("scripted_guide"), 0, "guide", Walks())


def evaluated(policy: str, seed: int) -> pd.Series:
    if not E2.exists():
        pytest.skip("E2's evaluation summary isn't here")
    episodes = pd.read_csv(E2)
    return episodes[(episodes.policy == policy) & (episodes.seed == seed)].iloc[0]


def test_a_replay_is_the_evaluations_episode(guide):
    row = evaluated("scripted_guide", 0)
    assert len(guide["decisions"]) == row.decisions
    assert guide["final"]["total_level"] == row.total_level and guide["final"]["net_worth"] == row.net_worth
    assert guide["reward"] == pytest.approx(row.reward, abs=1e-3)


def test_every_decision_is_recorded_end_to_end(guide):
    from rlscape.sim.engine import HORIZON_TICKS
    ds = guide["decisions"]
    assert ds[0]["t0"] == 0 and ds[-1]["t1"] == HORIZON_TICKS
    assert all(a["t1"] == b["t0"] and a["t0"] < a["t1"] for a, b in zip(ds, ds[1:]))
    assert all(sum(d["levels"]) == d["total_level"] for d in ds) and sum(guide["start"]["levels"]) == guide["start"][
        "total_level"]
    assert all(a["to"] == b["from"] for a, b in zip(ds, ds[1:]))
    walked = [d for d in ds if d["walk"]]
    assert walked, "the guide walks somewhere"
    for d in walked:  # a walk runs from where the option began to where it ended
        assert d["walk"][0] == d["from"][:2] and d["walk"][-1] == d["to"][:2]
    assert all(d["top"] is None and d["value"] is None for d in ds)  # a scripted policy has no distribution


def test_the_page_carries_the_data_and_the_map(guide):
    from PIL import Image

    from rlscape.eval.replay import page
    html = page([guide], {"title": "t", "subtitle": "s"})
    start = html.index("const DATA = ") + len("const DATA = ")
    payload = html[start:html.index(";\nconst TICKS_PER_HOUR")]
    assert "</" not in payload  # nothing in the data can close the script
    data = json.loads(payload)
    assert data["replays"][0]["decisions"] == json.loads(json.dumps(guide["decisions"]))
    image = Image.open(io.BytesIO(base64.b64decode(data["map"]["png"])))
    assert image.size == (data["map"]["width"], data["map"]["height"])
    assert set(data["families"]) >= {d["family"] for d in guide["decisions"]}


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("replay_script", REPO / "scripts" / "replay.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not (BEST.parent / "episodes.parquet").exists(), reason="E2's run isn't here (runs/ is ignored)")
def test_a_checkpoints_episodes_are_the_same_from_the_decision_log_as_from_the_finished_run(script, tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    run = BEST.parent
    n_envs = json.loads((run / "config.json").read_text(encoding="utf-8"))["config"]["n_envs"]
    parts = sorted((run / "decisions").glob("part-*.parquet"))
    (tmp_path / "decisions").mkdir()  # a run still training: its decision log, no episodes.parquet yet
    pq.write_table(pa.concat_tables([pq.read_table(p, columns=["step", "done"]) for p in parts[:-1]]),
                   tmp_path / "decisions" / "part-00000.parquet")
    finished, training = script.episodes_by(run, n_envs), script.episodes_by(tmp_path, n_envs)
    known = int(pq.read_table(parts[-2], columns=["step"])["step"].to_numpy().max()) + n_envs
    steps = [n for n in script.checkpoints(run) if n <= known]
    assert steps and all(training(n) == finished(n) for n in steps)
    assert training(known + n_envs) is None and finished(known + n_envs) is not None  # past the log written so far
    assert finished(json.loads((run / "run.json").read_text(encoding="utf-8"))["decisions"]) == json.loads(
        (run / "run.json").read_text(encoding="utf-8"))["episodes"]


def test_a_trained_replay_is_named_by_its_practice_episodes(script):
    names = script.trained_names(1_000_448, 8_638, final=True)
    assert names["label"] == "After 8,638 episodes" and "decisions" not in names["label"] + names["short"]
    assert "1,000,448 decisions" in names["about"] and names["about"].startswith("The final model")
    assert script.trained_names(100_000, None, final=False)["label"] == "Trained 100k decisions"


@pytest.mark.skipif(not BEST.exists(), reason="E2's trained model isn't here (runs/ is git-ignored)")
def test_a_trained_replay_samples_what_the_evaluation_sampled_and_shows_its_choices():
    from rlscape.envs.sim_env import SimEnv
    from rlscape.eval.harness import make_policy
    from rlscape.eval.replay import record
    replay = record(SimEnv(), make_policy(f"best=ppo:{BEST}"), 0, "best")
    row = evaluated("gae_lambda0.95_learning_rate0.0003/seed0", 0)
    assert len(replay["decisions"]) == row.decisions and replay["final"]["total_level"] == row.total_level
    assert replay["final"]["net_worth"] == row.net_worth
    for d in replay["decisions"]:
        probs = [p for _, p, _ in d["top"]]
        assert probs == sorted(probs, reverse=True) and 0 < sum(probs) <= 1 + 1e-6 and math.isfinite(d["value"])
        assert len(d["top"]) <= 5
