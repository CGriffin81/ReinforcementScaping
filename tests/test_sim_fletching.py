"""Tests for Fletching (rlscape/sim/fletching.py) and its paths."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.combat.access import Progress
from rlscape.gamedata import server as gd
from rlscape.sim import build_catalog
from rlscape.sim.fletching import FIRST_TICK, Fletch, FletchAtBank, path_recipes, worth_stringing
from rlscape.sim.economy import PICKUP_TICKS
from rlscape.sim.kits import kit
from rlscape.sim.movement import route_ticks
from rlscape.sim.skilling import path_options, path_rate
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
KNIFE, LOGS, WILLOW, SHAFT, FEATHER, BOW_U = 946, 1511, 1519, 52, 314, 58
BRONZE_DART_TIP, BRONZE_DART = 819, 806


def character(inventory: dict[int, int], bank: dict[int, int] | None = None, **levels: int) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory, state.bank = dict(inventory), dict(bank or {})
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


@needs_server
def test_the_recipes_follow_the_servers_fletching_enums():
    r = gd.fletching_recipes()
    assert (r["arrow_shaft"].per_unit, r["arrow_shaft"].experience, r["arrow_shaft"].stage_ticks) == (15, 5.0, 3)
    assert (r["yew_longbow_u"].level, r["yew_longbow_u"].experience) == (70, 75.0)
    assert (r["string_yew_longbow"].stage_ticks, r["string_yew_longbow"].inputs) == (2, ((66, 1), (1777, 1)))
    assert (r["adamant_arrow"].units_per_stage, r["rune_dart"].units_per_stage) == (15, 10)
    assert r["rune_dart"].quest == "THE_TOURIST_TRAP" and r["iron_bolts"].quest is None
    assert not any("dragon" in name or "stock" in name for name in r)


@needs_server
def test_only_bows_worth_more_strung_are_strung():
    strung = {r.name for r in path_recipes() if r.kind == "string"}
    assert strung == {"string_maple_longbow", "string_yew_shortbow", "string_yew_longbow", "string_magic_longbow"}
    assert not worth_stringing(gd.fletching_recipes()["string_willow_longbow"])


@needs_server
def test_cutting_takes_a_log_every_3_ticks_after_a_first_tick():
    """As measured live: 8 logs cut into arrow shafts at the first tick and every 3 ticks after."""
    state = character({KNIFE: 1, LOGS: 8})
    result = Fletch(gd.fletching_recipes()["arrow_shaft"]).run(state, np.random.default_rng(0), 1_000)
    assert result.ticks == FIRST_TICK + 7 * 3 and result.termination == "inputs_exhausted"
    assert state.inventory == {KNIFE: 1, SHAFT: 120} and state.xp[SKILL_INDEX["fletching"]] == 40.0


@needs_server
def test_darts_need_the_tourist_trap_and_come_ten_a_stage():
    craft = Fletch(gd.fletching_recipes()["bronze_dart"])
    state = character({FEATHER: 25, BRONZE_DART_TIP: 25})
    state.progress = Progress()  # no quests (a new character has done every quest the server has)
    assert not craft.available(state)
    state.progress = Progress(quests_complete=frozenset({"THE_TOURIST_TRAP"}))
    result = craft.run(state, np.random.default_rng(0), 1_000)
    assert state.inventory == {BRONZE_DART: 25} and result.ticks == FIRST_TICK + 2 * 3  # 10, 10, then 5


@needs_server
def test_a_bank_path_works_through_the_banked_logs_a_load_at_a_time():
    path = FletchAtBank(gd.fletching_recipes()["willow_longbow_u"])
    state = character({}, {KNIFE: 1, WILLOW: 60}, fletching=40)
    assert path.available(state) and path.load_size() == 27
    result = path.run(state, np.random.default_rng(0), 3_000)
    assert result.termination == "inputs_exhausted" and result.detail == {"path": "fletch_willow_longbow_u"}
    assert state.bank.get(BOW_U, 0) + state.inventory.get(BOW_U, 0) == 60 and WILLOW not in state.bank
    assert state.xp[SKILL_INDEX["fletching"]] == XP_FOR_LEVEL[40] + 60 * 41.5


@needs_server
def test_the_bank_path_rate_matches_its_simulation():
    path = FletchAtBank(gd.fletching_recipes()["willow_longbow_u"])
    state = character({}, {KNIFE: 1, WILLOW: 5_000}, fletching=45)
    rate = path_rate(path, state)
    sim = character({}, {KNIFE: 1, WILLOW: 5_000}, fletching=45)
    result = path.run(sim, np.random.default_rng(0), 1_500)
    xp_per_hour = (sim.xp[SKILL_INDEX["fletching"]] - XP_FOR_LEVEL[45]) * 6_000 / result.ticks
    assert rate.gather_xp == pytest.approx(xp_per_hour, rel=0.05)


@needs_server
def test_chopping_and_cutting_shafts_keeps_going_because_shafts_stack():
    path = next(p for p in path_options() if p.id == "wc_logs_fletch")
    state = character({1351: 1, KNIFE: 1})
    state.location = path.gather.site.tile
    result = path.run(state, np.random.default_rng(3), 3_000)
    assert result.ticks == 3_000 and state.inventory.get(SHAFT, 0) > 3 * 26 * 15  # load after load
    assert state.xp[SKILL_INDEX["fletching"]] > 0 and state.xp[SKILL_INDEX["woodcutting"]] > 0


@needs_server
def test_the_kits_keep_the_knife():
    state = character({1351: 1, KNIFE: 1, LOGS: 5, FEATHER: 10, 995: 50})
    assert kit(state, "woodcutting") == {1351, KNIFE}
    assert kit(state, "fletching") == {KNIFE, LOGS, FEATHER}


@needs_server
def test_a_fresh_character_takes_the_knife_in_lumbridge_castle():
    take = next(o for o in build_catalog() if o.id == "take_knife")
    state = CharacterState.fresh()
    assert take.available(state)
    result = take.run(state, np.random.default_rng(0), 1_500)
    walked = route_ticks(CharacterState.fresh(), (3205, 3212, 0))  # the planned walk through the castle
    assert state.inventory[KNIFE] == 1 and state.location == (3205, 3212, 0) and result.ticks == walked + PICKUP_TICKS
    assert not take.available(state)  # one is held
