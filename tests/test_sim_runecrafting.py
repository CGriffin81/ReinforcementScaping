"""Runecrafting in the sim (sim v1, docs/sim-v1-skills-draft.md §5): the runes and ruins from the server, essence
mining, and the rc_<rune> paths."""

from __future__ import annotations

import re

import numpy as np
import pytest

from rlscape.gamedata import runecrafting as rcd
from rlscape.gamedata import server as gd
from rlscape.sim.kits import kit
from rlscape.sim.runecrafting import (RC_RUNES, SCRIPT_WAIT_EXTRA, MineEssence, RunecraftAtRuins, inputs,
                                      runecrafting_paths)
from rlscape.sim.skilling import SKILLS, SkillingSlots, path_options, path_rate
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
BRONZE_PICKAXE, BRONZE_SWORD = 1265, 1277


def character(inventory: dict[int, int], bank: dict[int, int] | None = None, **levels: int) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory, state.bank, state.equipment = dict(inventory), dict(bank or {}), {}
    for skill, level in levels.items():
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    return state


@needs_server
def test_the_runes_follow_the_servers_rune_table_at_revision_530():
    """rl.conf's runecrafting_formula_revision is 530, where an essence makes as many runes as the rune's multiple
    levels reached (RuneCraftPulse.getMultiplier), with no chance of one more between them."""
    conf = (gd.REPO / "server" / "Server" / "worldprops" / "rl.conf").read_text(encoding="utf-8")
    assert re.search(r"^runecrafting_formula_revision = 530$", conf, re.M)
    r = rcd.runes()
    assert (r["air"].item, r["air"].level, r["air"].experience) == (556, 1, 5.0)
    assert [r["air"].per_essence(level) for level in (1, 10, 11, 21, 22, 99)] == [1, 1, 2, 2, 3, 10]
    assert r["nature"].per_essence(90) == 1 and r["nature"].per_essence(91) == 2
    assert not any(r[n].pure_only for n in ("air", "mind", "water", "earth", "fire", "body"))
    assert all(r[n].pure_only for n in ("cosmic", "chaos", "nature", "law", "death", "blood"))


@needs_server
def test_the_ruins_talismans_and_tiaras_are_the_servers():
    ruins = rcd.ruins()
    assert (ruins["air"].base, ruins["air"].end) == ((2983, 3292, 0), (2841, 4829, 0))
    assert ruins["law"].base == (2857, 3379, 0) and ruins["cosmic"].base == (2406, 4375, 0)  # Entrana; Zanaris
    assert rcd.talismans()["air"] == 1438 and rcd.tiaras()["air"] == (5527, 25.0)
    assert rcd.essence_delays()["BRONZE_PICKAXE"] == 7 and rcd.essence_delays()["RUNE_PICKAXE"] == 2
    assert rcd.essence_wizards()["aubury"] == ((3253, 3401, 0), 553) and len(rcd.essence_landings()) == 7


@needs_server
def test_essence_is_mined_to_a_full_inventory_and_the_portal_leads_back_to_the_wizard():
    """An essence every pickaxe delay + 1 ticks, 5 Mining XP each; pure essence from Mining 30."""
    state = character({BRONZE_PICKAXE: 1}, mining=1)
    option = MineEssence()
    assert option.available(state) and option.essence_ticks(state) == 7 + SCRIPT_WAIT_EXTRA
    result = option.run(state, np.random.default_rng(0), 3_000)
    assert result.termination == "inventory_full" and state.inventory == {BRONZE_PICKAXE: 1, rcd.RUNE_ESSENCE: 27}
    assert state.xp[SKILL_INDEX["mining"]] == pytest.approx(27 * 5.0)
    assert state.location == rcd.essence_wizards()["aubury"][0]  # the nearest from Lumbridge
    pure = character({BRONZE_PICKAXE: 1}, mining=30)
    option.run(pure, np.random.default_rng(0), 3_000)
    assert pure.inventory.get(rcd.PURE_ESSENCE) == 27 and not option.available(pure)  # full
    assert not option.available(character({}))  # no pickaxe


@needs_server
def test_an_rc_path_crafts_its_essence_a_load_at_a_time_with_the_talisman():
    talisman = rcd.talismans()["air"]
    path = RunecraftAtRuins("air")
    assert path.id == "rc_air" and not path.available(character({}, {rcd.RUNE_ESSENCE: 54}))  # no talisman
    state = character({}, {rcd.RUNE_ESSENCE: 54, talisman: 1}, runecrafting=11)
    assert path.available(state)
    result = path.run(state, np.random.default_rng(0), 5_000)
    assert result.termination == "inputs_exhausted"
    runes = state.inventory.get(556, 0) + state.bank.get(556, 0)
    assert runes == 54 * 2  # two an essence from level 11
    assert state.xp[SKILL_INDEX["runecrafting"]] == pytest.approx(XP_FOR_LEVEL[11] + 54 * 5.0)


@needs_server
def test_a_normal_rune_takes_rune_essence_first_and_the_others_only_pure():
    air, chaos = RunecraftAtRuins("air"), RunecraftAtRuins("chaos")
    state = character({}, {rcd.RUNE_ESSENCE: 10, rcd.PURE_ESSENCE: 10, rcd.talismans()["air"]: 1}, runecrafting=11)
    air._restock(state)
    assert state.inventory.get(rcd.RUNE_ESSENCE) == 10 and rcd.PURE_ESSENCE not in state.inventory  # one kind a load
    only_rune = character({}, {rcd.RUNE_ESSENCE: 50, rcd.talismans()["chaos"]: 1}, runecrafting=35)
    assert chaos.held_units(only_rune) == 0 and not chaos.available(only_rune)


@needs_server
def test_law_banks_the_arms_entranas_monks_refuse_and_nature_carries_its_fares():
    law = RunecraftAtRuins("law")
    state = character({}, {rcd.PURE_ESSENCE: 27, rcd.talismans()["law"]: 1}, runecrafting=54)
    state.equipment = {"weapon": BRONZE_SWORD}
    assert law.station(state) is not None and law.available(state)  # reachable once the sword is banked
    law._restock(state)
    assert "weapon" not in state.equipment and state.bank.get(BRONZE_SWORD) == 1
    nature = RunecraftAtRuins("nature")
    poor = character({}, {rcd.PURE_ESSENCE: 27, rcd.talismans()["nature"]: 1, COINS: 59}, runecrafting=44)
    assert not nature.available(poor)  # the Karamja boat, 30 gp each way
    rich = character({}, {rcd.PURE_ESSENCE: 27, rcd.talismans()["nature"]: 1, COINS: 100}, runecrafting=44)
    assert nature.available(rich)
    nature._restock(rich)
    assert rich.inventory.get(COINS) == 60 and rich.inventory.get(rcd.PURE_ESSENCE) == 26


@needs_server
def test_runecrafting_has_its_slots_kit_and_rates():
    assert "runecrafting" in SKILLS and len(runecrafting_paths()) == len(RC_RUNES) == 9
    ids = {p.id for p in path_options()}
    assert {"mine_essence", "rc_air", "rc_law"} <= ids and "rc_cosmic" not in ids  # Zanaris: OQ-45
    state = character({rcd.PURE_ESSENCE: 20, rcd.talismans()["air"]: 1, COINS: 5})
    assert kit(state, "runecrafting") == {rcd.PURE_ESSENCE, rcd.talismans()["air"]} <= inputs()
    banked = character({}, {rcd.RUNE_ESSENCE: 1_000, rcd.talismans()["air"]: 1}, runecrafting=20)
    rate = path_rate(RunecraftAtRuins("air"), banked)
    assert rate.gather_xp > 0 and rate.process_xp == 0
    assert SkillingSlots().candidate(banked, "runecrafting", 0).path.id == "rc_air"
    miner = character({BRONZE_PICKAXE: 1})
    assert path_rate(MineEssence(), miner).gather_xp > 0
