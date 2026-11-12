"""The walk counter (rlscape/eval/walking.py; OQ-87 (a)): an episode is the same with it as without, and what it counts
adds up, a greedy policy's lookahead (options run on copies before it acts) not counted. It patches the sim's walks
for the rest of its process, so the episodes run in a fresh one."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from rlscape.gamedata import server as gd

REPO = Path(__file__).resolve().parents[1]
needs_server_data = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")

EPISODES = """
import json, sys
from rlscape.eval.harness import POLICIES
from rlscape.envs.sim_env import SimEnv
from rlscape.eval import walking
from rlscape.eval.rollout import TRACE, play
out = {}
for counted in (False, True):
    env = SimEnv(horizon_ticks=int(float(sys.argv[1]) * 6000))
    if counted:
        walking.install()
    episode = play(env, POLICIES[sys.argv[2]](), int(sys.argv[3]))
    out[str(counted)] = {"trace": [dict(zip(TRACE, row)) for row in episode.trace], "ticks": episode.game_ticks,
                         "walks": walking.COUNTER.walks if counted else 0}
print(json.dumps(out))
"""


@needs_server_data
@pytest.mark.parametrize("policy", ["scripted_guide", "random", "greedy_xp"])  # greedy_xp looks ahead
def test_an_episode_is_the_same_with_the_counter_and_its_walking_adds_up(policy):
    done = subprocess.run([sys.executable, "-c", EPISODES, "2", policy, "3"], cwd=REPO, capture_output=True,
                          text=True, check=True)
    runs = json.loads(done.stdout.strip().splitlines()[-1])
    without, counted = runs["False"], runs["True"]
    behaviour = ("decision", "t1", "option", "termination", "total_level", "net_worth")
    assert [[r[k] for k in behaviour] for r in without["trace"]] == [[r[k] for k in behaviour]
                                                                    for r in counted["trace"]]
    assert without["ticks"] == counted["ticks"]
    assert all(math.isnan(r["walk_ticks"]) for r in without["trace"])  # no counter: NaN, not 0
    assert counted["walks"] > 0
    walk = sum(r["walk_ticks"] for r in counted["trace"])
    lost = sum(r["walk_overhead_ticks"] for r in counted["trace"])
    assert 0 < lost < walk < counted["ticks"]
    starts = [0, *[r["t1"] for r in counted["trace"]]]
    for (start, row) in zip(starts, counted["trace"]):  # a decision walks no longer than it lasts
        assert row["walk_ticks"] + row["transport_ticks"] <= row["t1"] - start + 1e-6


def test_the_walking_shares_come_from_the_trace_and_a_trace_without_the_counter_is_left_out():
    import pandas as pd

    from rlscape.analysis import measures as ms
    rows = [  # policy, seed, decision, t1, walk, overhead, transport
        ("normalised_weights0-1/seed0", 0, 0, 600, 300.0, 30.0, 0.0),
        ("normalised_weights0-1/seed0", 0, 1, 1200, 0.0, 0.0, 60.0),
        ("normalised_weights0-1/seed1", 0, 0, 1000, 100.0, 10.0, 0.0),
        ("scripted_guide", 0, 0, 1000, 500.0, 40.0, 0.0),
        ("scripted_guide", 1, 0, 1000, float("nan"), float("nan"), float("nan")),  # no counter
    ]
    trace = pd.DataFrame(rows, columns=["policy", "seed", "decision", "t1", "walk_ticks", "walk_overhead_ticks",
                                        "transport_ticks"])
    per = ms.walking(trace).set_index(["policy", "seed"])
    first = per.loc[("normalised_weights0-1/seed0", 0)]
    assert first["ticks"] == 1200 and first["walk_share"] == 0.25 and first["overhead_share"] == 0.025
    assert first["transport_share"] == 0.05
    assert ("scripted_guide", 1) not in per.index
    summary = ms.walking_summary(per.reset_index()).set_index(["variant", "share"])
    trained = summary.loc[("normalised_weights0-1", "overhead_share")]
    assert trained["trained"] and trained["seeds"] == 2 and abs(trained["mean"] - (0.025 + 0.01) / 2) < 1e-12
    assert summary.loc[("scripted_guide", "walk_share"), "mean"] == 0.5
    assert ms.walking(trace.drop(columns=["walk_ticks"])).empty  # a trace from before the counter
