"""Tests for teleports and boats in the sim's walks (rlscape/gamedata/transports.py, rlscape/sim/transport.py,
rlscape/sim/movement.py): the server's data, who can use what, what it costs, and that a walk takes the fastest."""

from __future__ import annotations

import pytest

from rlscape.combat.access import Progress
from rlscape.gamedata import server as gd
from rlscape.gamedata.transports import (HOME_COOLDOWN_TICKS, HOME_TICKS, charter_ports, jewellery, tablets,
                                         transports, wilderness_level)
from rlscape.routes import DATA
from rlscape.sim.movement import route, walk
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, CharacterState
from rlscape.sim.transport import can_use, next_charge
from rlscape.travel import travel_ticks

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
needs_map = pytest.mark.skipif(not (DATA / "collision.npz").exists(), reason="no exported map")
LAW, AIR, FIRE, STAFF_OF_AIR = 563, 556, 554, 1381
GLORY4, GLORY3, GLORY, GAMES1 = 1712, 1710, 1704, 3867
VARROCK_TAB = 8007
LUMBRIDGE, VARROCK, PORT_SARIM, MUSA_POINT = (3222, 3218, 0), (3212, 3424, 0), (3028, 3218, 0), (2915, 3152, 0)


def at(tile: tuple[int, int, int], inventory: dict[int, int] | None = None, magic: int = 1,
       quests: frozenset[str] = frozenset()) -> CharacterState:
    state = CharacterState.fresh()
    state.location, state.inventory = tile, dict(inventory or {})
    state.xp[SKILL_INDEX["magic"]] = float(XP_FOR_LEVEL[magic])
    state.progress = Progress(quests_complete=quests)
    return state


def by_id(name: str):
    return next(t for t in transports() if t.id == name)


@needs_server
def test_the_servers_teleport_jewellery_tablets_and_charters():
    glory = jewellery()["AMULET_OF_GLORY"]
    assert glory[0] == ("Edgeville", "Karamja", "Draynor Village", "Al Kharid") and not glory[2]
    assert glory[3] == (GLORY4, GLORY3, 1708, 1706, GLORY)  # four charges, then uncharged
    assert next_charge()[GLORY4] == GLORY3 and next_charge()[GAMES1] is None  # the last games necklace crumbles
    assert GLORY not in by_id("jewellery:amulet_of_glory:karamja").items  # an uncharged glory can't teleport
    assert jewellery()["DIGSITE_PENDANT"][3] == (11194, 11193, 11192, 11191, 11190)
    assert tablets()["VARROCK_TELEPORT"] == (VARROCK_TAB, (3212, 3423, 0))
    assert "RING_OF_LIFE" in jewellery() and not any(t.id.startswith("jewellery:ring_of_life") for t in transports())
    catherby = charter_ports()["CATHERBY"]
    assert catherby[3] == (2797, 3414, 0) and by_id("charter:catherby-port_sarim").coins == 1000
    assert by_id("charter:port_sarim-port_phasmatys").quests == ("PRIEST_IN_PERIL",)


@needs_server
def test_a_teleport_spell_needs_its_level_and_runes_and_a_staff_stands_in():
    varrock = by_id("spell:varrock")
    runes = {LAW: 1, AIR: 3, FIRE: 1}
    assert not can_use(at(LUMBRIDGE, runes, magic=24), varrock, LUMBRIDGE, 0)
    assert can_use(at(LUMBRIDGE, runes, magic=25), varrock, LUMBRIDGE, 0)
    staffed = at(LUMBRIDGE, {LAW: 1, FIRE: 1}, magic=25)
    staffed.equipment[3] = STAFF_OF_AIR
    assert can_use(staffed, varrock, LUMBRIDGE, 0)


@needs_server
def test_quests_and_the_wilderness_limit_teleports():
    ardougne = by_id("spell:ardougne")
    runes = {563: 2, 555: 2}
    assert not can_use(at(LUMBRIDGE, runes, magic=51), ardougne, LUMBRIDGE, 0)
    assert can_use(at(LUMBRIDGE, runes, magic=51, quests=frozenset({"PLAGUE_CITY"})), ardougne, LUMBRIDGE, 0)
    deep, edge = (3100, 3700, 0), (3100, 3530, 0)
    assert wilderness_level(deep) == 23 and wilderness_level(edge) == 2
    assert not can_use(at(deep), by_id("home"), deep, 0) and can_use(at(edge), by_id("home"), edge, 0)
    glory = by_id("jewellery:amulet_of_glory:edgeville")
    assert can_use(at(deep, {GLORY4: 1}), glory, deep, 0)  # jewellery works to level 30


@needs_server
@needs_map
def test_a_walk_takes_the_fastest_way_and_pays_for_it():
    spell = at(LUMBRIDGE, {LAW: 1, AIR: 3, FIRE: 1}, magic=25)
    assert [t.id for t in route(spell, VARROCK).transports] == ["spell:varrock"]
    walk(spell, VARROCK, 10_000)
    assert not spell.inventory and spell.xp[SKILL_INDEX["magic"]] == XP_FOR_LEVEL[25] + 35
    tablet = at(LUMBRIDGE, {VARROCK_TAB: 2})
    walk(tablet, VARROCK, 10_000)
    assert tablet.inventory == {VARROCK_TAB: 1}
    worn = at((2965, 3378, 0))
    worn.equipment[2] = GLORY4
    walk(worn, MUSA_POINT, 10_000)  # Falador to Karamja: the glory
    assert worn.equipment[2] == GLORY3 and worn.location == MUSA_POINT


@needs_server
@needs_map
def test_a_boat_needs_its_fare_and_entrana_turns_away_weapons():
    fare = at(PORT_SARIM, {COINS: 30})
    assert [t.id for t in route(fare, MUSA_POINT).transports] == ["ship:port_sarim-karamja"]
    walk(fare, MUSA_POINT, 10_000)
    assert COINS not in fare.inventory
    broke = at(PORT_SARIM)
    assert route(broke, MUSA_POINT) is None  # no way there it can use: unreachable (Caleb, 2026-11-01)
    entrana = (2830, 3340, 0)
    unarmed = at((3047, 3234, 0))
    unarmed.equipment = {}
    assert [t.id for t in route(unarmed, entrana).transports] == ["ship:port_sarim-entrana"]
    armed = at((3047, 3234, 0), {1277: 1})  # a bronze sword
    assert route(armed, entrana) is None  # the only way there turns it away


@needs_server
@needs_map
def test_the_home_teleport_is_free_once_every_30_minutes():
    far = (2809, 3436, 0)  # Catherby
    assert travel_ticks(far, LUMBRIDGE, home=True) == pytest.approx(HOME_TICKS)
    assert travel_ticks(far, (2810, 3440, 0), home=True) < HOME_TICKS  # nearby, it's a walk
    assert travel_ticks(far, LUMBRIDGE) > 10 * HOME_TICKS  # an estimate without it walks
    state = at(far)
    assert [t.id for t in route(state, LUMBRIDGE).transports] == ["home"]
    walk(state, LUMBRIDGE, 10_000)
    assert state.home_teleport_ready == HOME_TICKS + HOME_COOLDOWN_TICKS  # 30 minutes from the teleport (at tick 0)
    state.location = far
    assert route(state, LUMBRIDGE).transports == ()  # it walks back
    assert route(state, LUMBRIDGE, elapsed=state.home_teleport_ready - 1).transports == ()
    assert [t.id for t in route(state, LUMBRIDGE, elapsed=state.home_teleport_ready).transports] == ["home"]


@needs_server
@needs_map
def test_the_trollheim_teleport_asks_eadgars_ruses_own_requirement():
    """Eadgar's Ruse isn't on the server, so its Trollheim teleport asks the quest's own requirement (Requirement.kt:
    Druidic Ritual, Troll Stronghold, Herblore 31; Caleb, 2026-11-08: Trollheim by its teleport, and these teleports
    open as the quests are flagged complete). From where it lands the mountain and thrower trolls can be walked to.
    The Watchtower and Ape Atoll teleports ask theirs the same way: Watchtower's levels; Ape Atoll's two quests, both
    complete from the start."""
    trollheim = by_id("spell:trollheim")
    assert trollheim.quests == ("DRUIDIC_RITUAL", "TROLL_STRONGHOLD") and trollheim.skills == (("herblore", 31),)
    assert by_id("spell:watchtower").quests == () and by_id("spell:watchtower").skills == (
        ("agility", 25), ("herblore", 14), ("magic", 14), ("mining", 40), ("thieving", 15))
    ape = by_id("spell:ape_atoll")
    assert ape.quests == ("THE_GRAND_TREE", "TREE_GNOME_VILLAGE") and ape.skills == ()
    ape_state = at(LUMBRIDGE, {FIRE: 2, 555: 2, LAW: 2, 1963: 1}, magic=64,
                   quests=frozenset({"THE_GRAND_TREE", "TREE_GNOME_VILLAGE"}))
    assert can_use(ape_state, ape, LUMBRIDGE, 0)
    quests = frozenset({"DRUIDIC_RITUAL", "TROLL_STRONGHOLD"})
    state = at(LUMBRIDGE, {FIRE: 2, LAW: 2}, magic=61, quests=quests)
    state.xp[SKILL_INDEX["herblore"]] = float(XP_FOR_LEVEL[30])
    assert not can_use(state, trollheim, LUMBRIDGE, 0)
    assert route(state, (2843, 3682, 0)) is None  # a mountain troll's site: no way there yet
    state.xp[SKILL_INDEX["herblore"]] = float(XP_FOR_LEVEL[31])
    assert can_use(state, trollheim, LUMBRIDGE, 0)
    assert route(state, (2843, 3682, 0)) is not None and route(state, (2893, 3700, 0)) is not None  # a thrower troll
