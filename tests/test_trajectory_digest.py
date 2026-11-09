"""Tests for scripts/trajectory_digest.py: an episode's digest is fixed by its policy and seed, whatever ran before."""

from __future__ import annotations

import importlib.util

import pytest

from rlscape.eval.harness import REPO
from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")


@pytest.fixture(scope="module")
def digest():
    spec = importlib.util.spec_from_file_location("trajectory_digest", REPO / "scripts" / "trajectory_digest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._init({"horizon_ticks": 6_000})  # one game-hour
    return module


def test_a_digest_depends_on_the_policy_and_seed_only(digest):
    first = digest._episode("scripted_guide", 0)
    digest._episode("random", 1)  # something else played in between, as in a worker
    again = digest._episode("scripted_guide", 0)
    other = digest._episode("scripted_guide", 1)
    assert first[0] == again[0] == "scripted_guide/0" and first[1]["digest"] == again[1]["digest"]
    assert other[1]["digest"] != first[1]["digest"] and first[1]["decisions"] > 0


def test_compare_names_the_episodes_that_differ_or_are_missing(digest):
    base = {"episodes": {"a/0": {"digest": "x"}, "a/1": {"digest": "y"}}}
    new = {"episodes": {"a/0": {"digest": "x"}, "a/1": {"digest": "z"}, "a/2": {"digest": "w"}}}
    assert digest.compare(new, base) == ["a/1", "a/2"] and digest.compare(base, base) == []
