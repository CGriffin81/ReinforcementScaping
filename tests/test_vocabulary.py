"""Tests for the item vocabulary V (option catalog §9), accepted by Caleb on 2026-10-30 and grown by its rule since."""

from __future__ import annotations

import pytest

from rlscape.envs import SimEnv
from rlscape.gamedata import server as gd
from rlscape.sim import build_catalog
from rlscape.sim.buying import AVAS_DEVICES, GE_ITEMS, SHOP_ITEMS
from rlscape.sim.economy import alchable
from rlscape.sim.state import COINS
from rlscape.vocabulary import vocabulary

BROAD_BOLTS = 13280

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
PER_ITEM = ("drop_", "high_alch_", "low_alch_", "sell_ge_", "sell_store_")


def test_v_is_the_accepted_list():
    v = vocabulary()
    # 156 accepted, 20 fletching inputs added; on 2026-11-06, 16 from the redraft with every quest complete, 6
    # quest-gear buys, 5 the drop sub-tables brought, and 11 four-dose potions (their lower doses are misc: OQ-25);
    # on 2026-11-07, Ava's attractor and accumulator, bought on the GE, and every tradeable crossbow and bolt on the
    # 2009 GE, 63 (Caleb)
    assert len(v) == len(set(v)) == 279 and COINS not in v


@needs_server
def test_every_item_in_v_is_a_real_tradeable_item_with_live_actions():
    v, unnoted, ge = vocabulary(), gd.unnoted_ids(), gd.ge_prices_2009()
    assert all(unnoted.get(item, item) == item for item in v)  # no banknote ids
    assert all(item in ge for item in v)
    # so no per-item action is always masked, but for Ava's devices: untradeable, so the spell and the stores refuse
    # them and the game offers Destroy, not Drop; the GE sells and buys them at Caleb's prices (2026-11-07); and broad
    # bolts (Caleb's every bolt, 2026-11-07), tradeable but Destroy too
    assert all(alchable(item) and (item not in gd.destroy_only_items() or item == BROAD_BOLTS) for item in v
               if item not in AVAS_DEVICES)
    assert not any(alchable(item) for item in AVAS_DEVICES) and set(AVAS_DEVICES) <= gd.destroy_only_items()
    assert set(GE_ITEMS) | set(SHOP_ITEMS) <= set(v)  # every bought item (catalog §8)


@needs_server
def test_the_catalog_and_observation_grow_by_5_actions_and_7_features_per_item():
    v, catalog, empty = vocabulary(), build_catalog(), build_catalog(())
    ids = {o.id for o in catalog}
    assert len(catalog) == len(empty) + 5 * len(v) == 1_713
    assert all(f"{prefix}{item}" in ids for item in v for prefix in PER_ITEM)
    assert SimEnv().encoder.size == SimEnv(vocabulary=()).encoder.size + 7 * len(v) == 2_650
