"""Tests for Crafting's paths at a bank (rlscape/sim/crafting.py): gems, leather and dragonhide armour."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim.crafting import (DRAGON_BATCH, MAKE_START_TICKS, THREAD_CHARGES, Craft, CraftAtBank, craft_ticks,
                                  thread_capacity)
from rlscape.sim.kits import kit
from rlscape.sim.skilling import SKILLS, SkillingSlots, path_options, path_rate
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
CHISEL, NEEDLE, THREAD, SOFT, HARD = 1755, 1733, 1734, 1741, 1743
UNCUT_SAPPHIRE, SAPPHIRE, GREEN_LEATHER, GREEN_BODY, GLOVES = 1623, 1607, 1745, 1135, 1059


def character(inventory: dict[int, int], bank: dict[int, int] | None = None, **levels: int) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory, state.bank = dict(inventory), dict(bank or {})
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


@needs_server
def test_the_recipes_follow_the_servers_crafting_enums():
    """Gems, the 8 leather pieces and the 12 dragonhide ones, as the spec has them (OQ-2's Choice C): no studded
    armour, snakeskin or jewellery."""
    r = gd.crafting_recipes()
    assert len(r) == 29 and {x.kind for x in r.values()} == {"gem", "leather", "dragonhide"}
    assert sum(x.kind == "gem" for x in r.values()) == 9 and sum(x.kind == "leather" for x in r.values()) == 8
    assert (r["sapphire"].inputs, r["sapphire"].level, r["sapphire"].experience) == (((UNCUT_SAPPHIRE, 1),), 20, 50.0)
    assert (r["sapphire"].first_ticks, r["sapphire"].stage_ticks, r["sapphire"].tool) == (1, 1, CHISEL)
    assert (r["hardleather_body"].inputs, r["hardleather_body"].level, r["hardleather_body"].experience) == (
        ((HARD, 1),), 28, 35.0)
    body = r["green_d_hide_body"]
    assert (body.inputs, body.level, body.experience, body.stage_ticks, body.thread) == (
        ((GREEN_LEATHER, 3),), 63, 186.0, 5, True)
    assert not any("studded" in name or "snake" in name for name in r)


def test_a_reel_of_thread_sews_five_items():
    """decayThread: a thread is taken when the reel's charges run out, and every item needs one held."""
    assert thread_capacity(0, 5) == 0
    assert thread_capacity(1, 5) == 5 and thread_capacity(2, 5) == 10 and thread_capacity(1, 2) == 2
    assert thread_capacity(1, 0) == 1  # a spent reel sews one more, then takes the thread


@needs_server
def test_a_gem_is_cut_every_tick():
    state = character({CHISEL: 1, UNCUT_SAPPHIRE: 10}, crafting=20)
    result = Craft(gd.crafting_recipes()["sapphire"]).run(state, np.random.default_rng(0), 1_000)
    assert result.ticks == MAKE_START_TICKS + 1 + 9 * 1 and result.termination == "inputs_exhausted"
    assert state.inventory == {CHISEL: 1, SAPPHIRE: 10}
    assert state.xp[SKILL_INDEX["crafting"]] == XP_FOR_LEVEL[20] + 10 * 50.0


@needs_server
def test_leather_is_sewn_every_5_ticks_and_uses_a_thread_every_5_items():
    state = character({NEEDLE: 1, THREAD: 2, SOFT: 12})
    result = Craft(gd.crafting_recipes()["leather_gloves"]).run(state, np.random.default_rng(0), 1_000)
    assert result.ticks == MAKE_START_TICKS + 5 + 9 * 5  # 10 pairs: the two threads' charges, then no thread
    assert state.inventory == {NEEDLE: 1, SOFT: 2, GLOVES: 10} and state.thread_charges == THREAD_CHARGES


@needs_server
def test_a_dragonhide_body_takes_three_leathers_and_its_level():
    craft = Craft(gd.crafting_recipes()["green_d_hide_body"])
    state = character({NEEDLE: 1, THREAD: 1, GREEN_LEATHER: 7}, crafting=62)
    assert not craft.available(state)
    state = character({NEEDLE: 1, THREAD: 1, GREEN_LEATHER: 7}, crafting=63)
    craft.run(state, np.random.default_rng(0), 1_000)
    assert state.inventory == {NEEDLE: 1, THREAD: 1, GREEN_LEATHER: 1, GREEN_BODY: 2} and state.thread_charges == 3


@needs_server
def test_the_servers_measured_times_a_batch_starts_with_its_clicks():
    """scripts/calibrate_crafting.py (2026-11-08), every case exact: a gem load of 27 takes 30 ticks, 26 leather gloves
    133, a hard leather body load 134, 13 green dragonhide chaps 73 (two "Make 10" batches) and 8 black bodies 44."""
    r = gd.crafting_recipes()
    assert craft_ticks(r["opal"], 27) == 30 and craft_ticks(r["leather_gloves"], 26) == 133
    assert craft_ticks(r["hardleather_body"], 26) == 134
    assert craft_ticks(r["green_d_hide_chaps"], 13) == 73 and craft_ticks(r["black_d_hide_body"], 8) == 44
    assert craft_ticks(r["green_d_hide_chaps"], DRAGON_BATCH + 1) - craft_ticks(r["green_d_hide_chaps"], DRAGON_BATCH) == 9


@needs_server
def test_a_bank_path_sews_the_banked_leather_a_load_at_a_time():
    path = CraftAtBank(gd.crafting_recipes()["leather_gloves"])
    state = character({}, {NEEDLE: 1, THREAD: 12, SOFT: 60})
    assert path.id == "craft_leather_gloves" and path.available(state) and path.load_size() == 26
    result = path.run(state, np.random.default_rng(0), 3_000)
    assert result.termination == "inputs_exhausted" and result.detail == {"path": "craft_leather_gloves"}
    assert state.bank.get(GLOVES, 0) + state.inventory.get(GLOVES, 0) == 60 and SOFT not in state.bank
    assert state.inventory.get(THREAD, 0) + state.bank.get(THREAD, 0) == 0  # 12 threads sew exactly 60
    assert state.xp[SKILL_INDEX["crafting"]] == pytest.approx(60 * 13.8)


@needs_server
def test_a_bank_path_needs_its_tool_and_thread():
    gloves = CraftAtBank(gd.crafting_recipes()["leather_gloves"])
    assert not gloves.available(character({}, {THREAD: 5, SOFT: 10}))  # no needle
    assert not gloves.available(character({}, {NEEDLE: 1, SOFT: 10}))  # no thread
    gem = CraftAtBank(gd.crafting_recipes()["opal"])
    assert gem.id == "cut_opal" and gem.available(character({}, {CHISEL: 1, 1625: 5}))


@needs_server
def test_a_crafting_paths_inputs_are_bought_on_the_ge():
    """Choice A (a) and I (a) (Caleb): the inputs join *V* and the GE buy actions. A fresh character with coins buys
    a needle, thread and leather (1,000, the inputs' lot), and then the glove path can run; the needle is a tool, one a
    buy, and not bought again while it's held."""
    from rlscape.sim.buying import CRAFTING_INPUTS, BuyGE
    from rlscape.sim.state import COINS
    from rlscape.vocabulary import vocabulary
    assert set(CRAFTING_INPUTS) <= set(vocabulary()) and len(CRAFTING_INPUTS) == 25
    state, rng = character({COINS: 1_000_000}), np.random.default_rng(0)
    gloves = CraftAtBank(gd.crafting_recipes()["leather_gloves"])
    assert not gloves.available(state)
    for item in (NEEDLE, THREAD, SOFT):
        assert BuyGE(item).run(state, rng, 10_000).termination == "completed"
    held = lambda item: state.inventory.get(item, 0) + state.inventory.get(gd.noted_ids().get(item, -1), 0)  # noqa: E731
    assert held(NEEDLE) == 1 and held(THREAD) == 1_000 and held(SOFT) == 1_000
    assert gloves.available(state) and not BuyGE(NEEDLE).available(state)


@needs_server
def test_crafting_has_its_slots_and_kit():
    assert "crafting" in SKILLS
    assert {p.id for p in path_options() if p.skill == "crafting"} >= {"cut_sapphire", "craft_green_d_hide_body"}
    state = character({CHISEL: 1, UNCUT_SAPPHIRE: 5, NEEDLE: 1, THREAD: 3, 995: 10})
    state.task = "crafting"
    assert kit(state, "crafting") == {CHISEL, UNCUT_SAPPHIRE, NEEDLE, THREAD}
    banked = character({}, {CHISEL: 1, UNCUT_SAPPHIRE: 100}, crafting=20)
    slots = SkillingSlots()
    assert slots.candidate(banked, "crafting", 0).path.id == "cut_sapphire"


@needs_server
def test_a_gem_paths_rate_counts_the_loads_and_the_gain():
    state = character({}, {CHISEL: 1, UNCUT_SAPPHIRE: 1_000}, crafting=20)
    rate = path_rate(CraftAtBank(gd.crafting_recipes()["sapphire"]), state)
    values = gd.item_values()
    assert rate.gather_xp > 0 and rate.process_xp == 0
    assert rate.gp == pytest.approx(rate.gather_xp / 50.0 * (values[SAPPHIRE] - values[UNCUT_SAPPHIRE]))


# Part 2: tanning and spinning between a bank and a station, and flax picked at Seers' Village.

COWHIDE, LEATHER, FLAX, BOWSTRING, WOOL = 1739, 1741, 1779, 1777, 1737


@needs_server
def test_tanning_and_spinning_follow_the_servers_enums():
    tan, spin = gd.tanning_recipes(), gd.spinning_recipes()
    assert {(r.hide, r.product, r.fee) for r in tan.values()} == {
        (COWHIDE, LEATHER, 1), (COWHIDE, HARD, 3), (1753, GREEN_LEATHER, 20), (1751, 2505, 20), (1749, 2507, 20),
        (1747, 2509, 20)}  # no snakeskin (Choice C)
    assert (spin["flax"].need, spin["flax"].product, spin["flax"].level, spin["flax"].experience) == (
        FLAX, BOWSTRING, 10, 15.0)
    assert (spin["wool"].level, spin["wool"].experience) == (1, 2.5)


@needs_server
def test_a_fresh_character_tans_at_ellis_and_never_in_the_crafting_guild():
    """The Crafting Guild needs a brown apron worn, which no option gets; Canifis and the Ranging Guild aren't in the
    travel model's reach."""
    from rlscape.sim.crafting import usable_station
    assert usable_station(CharacterState.fresh(), "tanner").name == "Al Kharid (Ellis)"
    assert usable_station(CharacterState.fresh(), "spinning_wheel").name == "Lumbridge Castle"


@needs_server
def test_a_tanning_path_tans_the_banked_hides_for_the_fee_and_no_xp():
    from rlscape.sim.crafting import TanAtTanner
    path = TanAtTanner(gd.tanning_recipes()["leather"])
    state = character({}, {COWHIDE: 40, 995: 100})
    assert path.id == "tan_leather" and path.available(state) and path.held_units(state) == 40
    result = path.run(state, np.random.default_rng(0), 9_000)
    assert result.termination == "inputs_exhausted"
    assert state.inventory.get(LEATHER, 0) + state.bank.get(LEATHER, 0) == 40 and state.coins() == 60
    assert state.xp[SKILL_INDEX["crafting"]] == 0


@needs_server
def test_a_spinning_path_spins_a_flax_every_4_ticks_from_level_10():
    from rlscape.sim.crafting import SPIN_TICKS, Spin, SpinAtWheel
    path = SpinAtWheel(gd.spinning_recipes()["flax"])
    assert path.id == "spin_flax" and not path.available(character({}, {FLAX: 10}, crafting=9))
    state = character({FLAX: 10}, crafting=10)
    result = Spin(gd.spinning_recipes()["flax"]).run(state, np.random.default_rng(0), 1_000)
    assert result.ticks == MAKE_START_TICKS + 4 + 9 * SPIN_TICKS and state.inventory == {BOWSTRING: 10}
    state = character({}, {FLAX: 60}, crafting=10)
    path.run(state, np.random.default_rng(0), 9_000)
    assert state.inventory.get(BOWSTRING, 0) + state.bank.get(BOWSTRING, 0) == 60
    assert state.xp[SKILL_INDEX["crafting"]] == pytest.approx(XP_FOR_LEVEL[10] + 60 * 15.0)


def test_a_flax_plant_gives_4_to_9_picks():
    from rlscape.sim.crafting import flax_plant_goes, mean_flax_picks
    rng, counts = np.random.default_rng(0), []
    for _ in range(5_000):
        picks = 1
        while not flax_plant_goes(picks, rng):
            picks += 1
        counts.append(picks)
    assert min(counts) == 4 and max(counts) == 9
    assert np.mean(counts) == pytest.approx(mean_flax_picks(), abs=0.05) and mean_flax_picks() == pytest.approx(5.77,
                                                                                                                abs=0.01)


@needs_server
def test_picking_flax_fills_the_inventory_for_no_xp_and_spinning_it_trains_crafting():
    paths = {p.id: p for p in path_options()}
    state = character({}, crafting=10)
    state.location = (2726, 3485, 0)  # Seers' Village's bank
    result = paths["pick_flax"].run(state, np.random.default_rng(0), 9_000)
    assert result.termination == "inventory_full" and state.inventory == {FLAX: 28}
    assert state.xp[SKILL_INDEX["crafting"]] == XP_FOR_LEVEL[10]
    state = character({}, crafting=10)
    state.location = (2726, 3485, 0)
    result = paths["pick_flax_spin"].run(state, np.random.default_rng(0), 9_000)
    assert result.termination == "inventory_full" and state.inventory == {BOWSTRING: 28}
    assert state.xp[SKILL_INDEX["crafting"]] == pytest.approx(XP_FOR_LEVEL[10] + 28 * 15.0)
    rate = path_rate(paths["pick_flax_spin"], state)
    assert rate.gather_xp == 0 and rate.process_xp > 0 and rate.gp > 0


@needs_server
def test_a_path_without_xp_goes_to_a_gp_slot_only():
    """A fresh character's only Crafting path is picking flax, which gives no XP: it's in a gp slot, the XP slots
    stay empty."""
    slots, state = SkillingSlots(), CharacterState.fresh()
    held = [slots.candidate(state, "crafting", i) for i in range(4)]
    assert held[0] is None and held[1] is None and held[2].path.id == "pick_flax"
