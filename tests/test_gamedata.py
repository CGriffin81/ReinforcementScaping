"""Checks that the game data loads from the server fork as the server reads it. Skipped without the submodule."""

from __future__ import annotations

import pytest

from rlscape.gamedata import server as gd

pytestmark = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule not checked out")

COW, BONES, COWHIDE, RAW_BEEF, RUNE_SCIMITAR = 81, 526, 1739, 2132, 1333


def test_cow_stats_match_the_config():
    cow = gd.npcs()[COW]
    assert (cow.hitpoints, cow.attack, cow.strength, cow.defence, cow.attack_speed) == (8, 1, 1, 1, 5)
    assert cow.combat_style == "melee" and cow.protect_style is None


def test_cow_drops_bones_hide_and_beef_every_kill():
    table = gd.drop_tables()[COW]
    expected = table.expected_items()
    assert expected[BONES] == expected[COWHIDE] == expected[RAW_BEEF] == pytest.approx(1.0)
    values = gd.item_values()
    assert table.expected_value(values) == pytest.approx(values[BONES] + values[COWHIDE] + values[RAW_BEEF])


def test_rune_scimitar_bonuses_and_requirement():
    scim = gd.items()[RUNE_SCIMITAR]
    assert scim.bonuses[gd.SLASH] == 45 and scim.bonuses[gd.MELEE_STRENGTH] == 44
    assert scim.requirements == {0: 40} and scim.attack_speed == 4


def test_cows_have_spawns_and_combat_npcs_are_plentiful():
    assert gd.spawns()[COW]
    assert len(gd.npcs()) > 4000
