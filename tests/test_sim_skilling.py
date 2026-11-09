"""Tests for the skilling slots (rlscape/sim/skilling.py): paths, their rates and the slots."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.skilling import (K_GP, K_XP, SKILLS, SkillingSlots, _unit, path_options, path_rate, slot_holding)
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
TINDERBOX, STEEL_AXE, STEEL_PICKAXE, FLY_ROD, FEATHER = 590, 1353, 1269, 309, 314
LOGS, OAK_LOGS, IRON_ORE, IRON_BAR = 1511, 1521, 440, 2351


def character(inventory: dict[int, int], **levels: int) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory = dict(inventory)
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


def paths() -> dict[str, object]:
    return {p.id: p for p in path_options()}


@needs_server
def test_each_method_is_kept_or_processed_by_its_counterpart():
    ids = set(paths())
    assert {"wc_oak", "wc_oak_burn", "wc_oak_fletch", "fish_fly", "fish_fly_cook", "mine_iron", "mine_iron_smelt",
            "fletch_willow_longbow_u", "fletch_string_yew_longbow", "fletch_adamant_arrow", "fletch_rune_dart"} <= ids
    assert "fletch_string_willow_longbow" not in ids  # 192 strung < 72 unstrung + 186 bowstring (Caleb's rule)
    assert "mine_copper_smelt" not in ids and not any(i.startswith("pickpocket") and "_" in i[11:] and
                                                      i.endswith(("_burn", "_cook", "_smelt")) for i in ids)
    by_skill = {s: sum(1 for p in path_options() if p.skill == s) for s in SKILLS}
    assert by_skill == {"woodcutting": 12, "fishing": 9, "mining": 7, "thieving": 20, "fletching": 36,
                        "crafting": 39, "herblore": 36, "runecrafting": 29, "agility": 4}  # Al Kharid iron,
    # Lumbridge Swamp's shrimp: 2 each


@needs_server
@pytest.mark.parametrize("path_id, inventory, levels", [
    ("wc_oak", {STEEL_AXE: 1}, {"woodcutting": 30}),
    ("mine_iron", {STEEL_PICKAXE: 1}, {"mining": 30}),
    ("fish_fly", {FLY_ROD: 1, FEATHER: 1000}, {"fishing": 40}),
    ("pickpocket_men", {}, {"thieving": 20, "hitpoints": 99}),
])
def test_the_rate_model_matches_the_simulated_path_at_its_site(path_id, inventory, levels):
    """XP per tick at the site, before the inventory fills: the model's unit against the path's own sampling."""
    path, rng = paths()[path_id], np.random.default_rng(0)
    probe = character(inventory, **levels)
    unit = _unit(path, probe, probe.free_slots())  # one load: the path ends at a full inventory
    xp, ticks = 0.0, 0
    for _ in range(60):
        state = character(inventory, **levels)
        state.hp, state.location = state.max_hp(), path.gather.site.tile if hasattr(path.gather, "site") else (
            path.gather.start if hasattr(path.gather, "spots") else path.gather.tile)
        before = sum(state.xp)
        result = path.run(state, rng, 1_500)
        xp, ticks = xp + sum(state.xp) - before, ticks + result.ticks
    assert xp / ticks == pytest.approx(unit.xp / unit.ticks, rel=0.08)


@needs_server
def test_burning_frees_the_inventory_so_the_path_keeps_chopping():
    path = paths()["wc_logs_burn"]
    state = character({1351: 1, TINDERBOX: 1}, firemaking=10)
    state.location = path.gather.site.tile
    result = path.run(state, np.random.default_rng(1), 6_000)
    assert result.ticks == 6_000 and result.termination == "completed" and result.detail == {"path": "wc_logs_burn"}
    one_load = (28 - 2) * gd.tree_types()[1].experience
    assert state.xp[SKILL_INDEX["woodcutting"]] > 3 * one_load  # it chopped load after load
    assert state.xp[SKILL_INDEX["firemaking"]] > XP_FOR_LEVEL[10]


@needs_server
def test_smelting_iron_leaves_bars_and_keeps_mining_while_there_is_room():
    path = paths()["mine_iron_smelt"]
    state = character({STEEL_PICKAXE: 1}, mining=40, smithing=20)
    result = path.run(state, np.random.default_rng(2), 6_000)
    assert state.inventory.get(IRON_BAR, 0) > 0 and state.xp[SKILL_INDEX["smithing"]] > XP_FOR_LEVEL[20]
    assert result.termination in ("inventory_full", "completed")


@needs_server
def test_slots_hold_the_best_two_by_xp_then_the_best_two_others_by_gp():
    state = character({STEEL_AXE: 1, TINDERBOX: 1, STEEL_PICKAXE: 1, FLY_ROD: 1, FEATHER: 500},
                      woodcutting=35, firemaking=35, mining=35, smithing=20, fishing=35, cooking=30, thieving=40)
    slots = SkillingSlots()
    for skill in SKILLS:
        held = [slots.candidate(state, skill, i) for i in range(K_XP + K_GP)]
        filled = [c for c in held if c is not None]
        assert len({c.path.id for c in filled}) == len(filled)  # no path in two slots
        xp, gp = held[:K_XP], held[K_XP:]
        if xp[0] is None:
            continue  # nothing open (no fletching inputs held here)
        rest = [p for p in path_options() if p.skill == skill and p.available(state)
                and p.id not in {c.path.id for c in xp if c is not None}]
        assert [c.rate.xp for c in xp if c] == sorted((c.rate.xp for c in xp if c), reverse=True)
        best_xp = max((path_rate(p, state).xp for p in path_options() if p.skill == skill and p.available(state)))
        assert xp[0].rate.xp == pytest.approx(best_xp)
        if gp[0] is not None:
            assert gp[0].rate.gp == pytest.approx(max(path_rate(p, state).gp for p in rest))


@needs_server
def test_travel_counts_against_a_far_site():
    near, far = character({STEEL_AXE: 1}, woodcutting=30), character({STEEL_AXE: 1}, woodcutting=30)
    willows = paths()["wc_willow"]
    near.location, far.location = willows.gather.site.tile, (2650, 3300, 0)  # East Ardougne
    assert path_rate(willows, far).travel > path_rate(willows, near).travel
    assert path_rate(willows, far).xp < path_rate(willows, near).xp


@needs_server
def test_a_slot_runs_its_path_and_the_engine_records_the_paths_task():
    sim = Simulator(build_catalog())
    sim.reset(seed=0)
    ids = [o.id for o in sim.options]
    slot = slot_holding(sim.options, sim.state, "fish_shrimp")
    info = sim.step(ids.index(slot)).info
    assert info["option"]["path"] == "fish_shrimp" and sim.state.task == "fishing:SMALL_NET"
