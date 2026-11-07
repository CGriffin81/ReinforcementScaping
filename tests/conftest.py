"""The live tests share one server: one bridge connection at a time, and one tick speed for the whole world. Under
pytest-xdist (`-n`, with `--dist loadgroup`) they all go to one worker, and the rest spread over the others (Caleb,
2026-11-06: run tests at once where possible)."""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.path.name.endswith("_live.py"):
            item.add_marker(pytest.mark.xdist_group("server"))
