"""Ava's devices in the sim (Caleb, 2026-11-07, OQ-28): worn in ranged fights only, attraction off, the accumulator
gathering the shots its catch misses (the fork's RangeSwingHandler), the accumulator's Ranged 50, the server's chest
interference, and the observation's cape role."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat.candidates import loot_rule
from rlscape.combat.rates import Plan
from rlscape.envs import SimEnv
from rlscape.envs.encoding import EQUIPMENT_ROLES
from rlscape.gamedata import server as gd
from rlscape.sim.buying import gear_to_withdraw
from rlscape.sim.combat import _ammunition, arrow_land_chance
from rlscape.sim.equipment import (
    AMMO,
    AVA_CATCH,
    AVA_DROP_RATE,
    AVAS_ACCUMULATOR,
    AVAS_ATTRACTOR,
    CAPE,
    CHEST,
    WEAPON,
    can_wear,
    land_chance,
    shot_outcomes,
    wield_best,
)
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
SHORTBOW, BRONZE_ARROW, BRONZE_SWORD = 841, 882, 1277
LEATHER_BODY, RUNE_PLATEBODY, IRON_CHAINBODY, RUNE_FULL_HELM = 1129, 1127, 1101, 1163


def ranger(level: int, cape: int | None = None, chest: int | None = None, arrows: int = 100) -> CharacterState:
    state = CharacterState.fresh()
    for skill in ("ranged", "defence", "attack"):
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.inventory = {}
    state.equipment = {WEAPON: SHORTBOW, AMMO: BRONZE_ARROW}
    state.worn_amounts = {AMMO: arrows}
    if cape is not None:
        state.equipment[CAPE] = cape
    if chest is not None:
        state.equipment[CHEST] = chest
    return state


def test_the_land_roll_and_the_narrower_one_for_shots_a_device_misses():
    """useAmmo: lands unless randomize(int(5 x (1 + level / 100) x rate)) is 0; the device's rate is 0.33."""
    assert land_chance(1) == arrow_land_chance(1) == pytest.approx(4 / 5)
    assert land_chance(99) == pytest.approx(8 / 9)
    assert land_chance(21, AVA_DROP_RATE) == 0 and land_chance(22, AVA_DROP_RATE) == pytest.approx(1 / 2)
    assert land_chance(81, AVA_DROP_RATE) == pytest.approx(1 / 2)
    assert land_chance(82, AVA_DROP_RATE) == pytest.approx(2 / 3)


@needs_server
def test_shot_outcomes_with_no_device_the_attractor_and_the_accumulator():
    """(back in the quiver, landed). The accumulator gathers what the attractor leaves on the ground; breaks stay."""
    assert shot_outcomes(ranger(30)) == pytest.approx((0.0, land_chance(30)))
    assert shot_outcomes(ranger(30, AVAS_ATTRACTOR)) == pytest.approx((AVA_CATCH, 0.2 * 0.5))
    assert shot_outcomes(ranger(60, AVAS_ACCUMULATOR)) == pytest.approx((AVA_CATCH + 0.2 * 0.5, 0.0))
    assert shot_outcomes(ranger(10, AVAS_ACCUMULATOR)) == pytest.approx((AVA_CATCH, 0.0))  # below 22, all 20% break
    assert shot_outcomes(ranger(90, AVAS_ACCUMULATOR)) == pytest.approx((AVA_CATCH + 0.2 * 2 / 3, 0.0))


@needs_server
def test_only_the_servers_metal_chest_pieces_interfere_and_only_with_the_catch():
    """AvasDevice.metalBodies (data/ava_interference.csv): platebodies and chainbodies, but not the iron chainbody,
    whose model isn't listed; no helm, legs or shield. Interfered, the 80% land on the normal roll."""
    interfering = gd.ava_interfering_items()
    assert RUNE_PLATEBODY in interfering and IRON_CHAINBODY not in interfering
    assert RUNE_FULL_HELM not in interfering and LEATHER_BODY not in interfering
    assert all(gd.items()[i].equipment_slot == CHEST for i in interfering)
    assert shot_outcomes(ranger(30, AVAS_ATTRACTOR, RUNE_PLATEBODY)) == pytest.approx(
        (0.0, AVA_CATCH * land_chance(30) + 0.2 * 0.5))
    assert shot_outcomes(ranger(30, AVAS_ACCUMULATOR, RUNE_PLATEBODY)) == pytest.approx(
        (0.2 * 0.5, AVA_CATCH * land_chance(30)))
    assert shot_outcomes(ranger(30, AVAS_ATTRACTOR, IRON_CHAINBODY))[0] == AVA_CATCH


@needs_server
def test_a_fight_uses_the_arrows_the_outcomes_say():
    """Over many shots, a fight's arrows lost match 1 - kept; with no loot, landed shots stay on the ground."""
    keep, none = loot_rule("valuable"), loot_rule("none")
    rng = np.random.default_rng(0)
    for state, loot, kept in ((ranger(60, AVAS_ACCUMULATOR, arrows=10**6), none, AVA_CATCH + 0.1),
                              (ranger(60, AVAS_ATTRACTOR, arrows=10**6), none, AVA_CATCH),
                              (ranger(60, AVAS_ATTRACTOR, arrows=10**6), keep, AVA_CATCH + 0.1),
                              (ranger(60, arrows=10**6), none, 0.0)):
        before = state.worn(AMMO)
        allowed, pay = _ammunition(state, Plan("ranged", "rapid"), 20_000, rng, loot)
        pay(allowed)
        assert (before - state.worn(AMMO)) / allowed == pytest.approx(1 - kept, abs=0.01)


@needs_server
def test_the_accumulator_needs_ranged_50_and_the_attractor_nothing():
    assert can_wear(ranger(1), AVAS_ATTRACTOR)
    assert not can_wear(ranger(49), AVAS_ACCUMULATOR) and can_wear(ranger(50), AVAS_ACCUMULATOR)


@needs_server
def test_ranged_fights_wear_the_best_device_and_leave_interfering_chests_off_other_fights_take_it_off():
    state = ranger(50)
    state.inventory = {AVAS_ATTRACTOR: 1, AVAS_ACCUMULATOR: 1, RUNE_PLATEBODY: 1, LEATHER_BODY: 1}
    wield_best(state, "ranged")
    assert state.equipment[CAPE] == AVAS_ACCUMULATOR and state.equipment[CHEST] == LEATHER_BODY
    assert AVAS_ATTRACTOR in state.inventory and RUNE_PLATEBODY in state.inventory
    state.inventory[BRONZE_SWORD] = 1
    wield_best(state, "melee")
    assert CAPE not in state.equipment and AVAS_ACCUMULATOR in state.inventory  # worn in ranged fights only
    assert state.equipment[CHEST] == RUNE_PLATEBODY
    plain = ranger(50)
    plain.inventory = {RUNE_PLATEBODY: 1}
    wield_best(plain, "ranged")
    assert plain.equipment[CHEST] == RUNE_PLATEBODY  # with no device, the most defence, as before


@needs_server
def test_ranged_gear_withdrawals_bring_the_best_device_first_and_no_interfering_chest():
    state = ranger(50)
    state.bank = {AVAS_ATTRACTOR: 1, AVAS_ACCUMULATOR: 1, RUNE_PLATEBODY: 1, LEATHER_BODY: 1}
    out = gear_to_withdraw(state, "ranged")
    assert out[0] == AVAS_ACCUMULATOR and LEATHER_BODY in out
    assert RUNE_PLATEBODY not in out and AVAS_ATTRACTOR not in out
    assert not {AVAS_ATTRACTOR, AVAS_ACCUMULATOR} & set(gear_to_withdraw(state, "melee"))


@needs_server
def test_the_observation_shows_a_worn_device_in_its_cape_role():
    """Caleb, 2026-11-07 (OQ-28): the equipment part's cape role, the attractor 1 and the accumulator 2 of 2."""
    encoder, cape = SimEnv().encoder, EQUIPMENT_ROLES.index("cape")
    for device, value in ((None, 0.0), (AVAS_ATTRACTOR, 0.5), (AVAS_ACCUMULATOR, 1.0)):
        assert encoder._equipment(ranger(50, device))[cape] == value
