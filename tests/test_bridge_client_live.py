"""Live checks of the bridge client's own helpers against the server.

Needs the forked server running with worldprops/rl.conf; skipped when the server is down.
"""

from __future__ import annotations

import pytest

from rlscape.bridge import BridgeClient
from test_bridge_live import bridge_reachable

pytestmark = pytest.mark.skipif(not bridge_reachable(), reason="RL bridge not running on localhost")


def test_set_tick_ms_returns_the_tick_it_replaced_so_a_script_can_set_it_back():
    """The bridge answers set_tick_ms with the new tick; the scripts keep the return as the old one to restore."""
    with BridgeClient() as client:
        client.set_tick_ms(600)
        try:
            assert client.set_tick_ms(50) == 600
            assert client.ping()["tick_ms"] == 50
            assert client.set_tick_ms(600) == 50
            assert client.ping()["tick_ms"] == 600
        finally:
            client.set_tick_ms(600)
