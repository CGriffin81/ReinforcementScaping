"""Tests for the item vocabulary V (option catalog §9), accepted by Caleb on 2026-10-30."""

from __future__ import annotations

import pytest

from rlscape.envs import SimEnv
from rlscape.gamedata import server as gd
from rlscape.sim import build_catalog
from rlscape.sim.buying import GE_ITEMS, SHOP_ITEMS
from rlscape.sim.economy import alchable
from rlscape.sim.state import COINS
from rlscape.vocabulary import vocabulary

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
PER_ITEM = ("drop_", "high_alch_", "low_alch_", "sell_ge_", "sell_store_")


def test_v_is_the_accepted_list():
    v = vocabulary()
    assert len(v) == len(set(v)) == 156 and COINS not in v


@needs_server
def test_every_item_in_v_is_a_real_tradeable_item_with_live_actions():
    v, unnoted, ge = vocabulary(), gd.unnoted_ids(), gd.ge_prices_2009()
    assert all(unnoted.get(item, item) == item for item in v)  # no banknote ids
    assert all(item in ge and alchable(item) for item in v)  # so no per-item action is always masked
    assert set(GE_ITEMS) | set(SHOP_ITEMS) <= set(v)  # every bought item (catalog §8)


@needs_server
def test_the_catalog_and_observation_grow_by_5_actions_and_7_features_per_item():
    v, catalog, empty = vocabulary(), build_catalog(), build_catalog(())
    ids = {o.id for o in catalog}
    assert len(catalog) == len(empty) + 5 * len(v) == 1_000
    assert all(f"{prefix}{item}" in ids for item in v for prefix in PER_ITEM)
    assert SimEnv().encoder.size == SimEnv(vocabulary=()).encoder.size + 7 * len(v) == 1_609
