"""Runecrafting in the sim (sim v1, docs/sim-v1-skills-draft.md §5): the runes and ruins from the server, and the
rc_<rune> paths, with the times measured on the server. Essence isn't mined (Caleb, 2026-11-08)."""

from __future__ import annotations

import re

import numpy as np
import pytest

from rlscape.gamedata import runecrafting as rcd
from rlscape.gamedata import server as gd
from rlscape.sim.kits import kit
from rlscape.sim.runecrafting import (HAT, RC_RUNES, MakeTiaraAtRuins, RunecraftAtRuins, inputs, inside_ticks,
                                      runecrafting_paths)
from rlscape.sim.skilling import SKILLS, SkillingSlots, path_options, path_rate
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import COINS, CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
BRONZE_SWORD, WEAPON = 1277, 3


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


def test_the_times_inside_the_ruins_are_the_servers():
    """scripts/calibrate_runecrafting.py, 2026-11-08 (results/calibration/runecrafting-20261108-2046-i6.json): from
    landing to standing outside again, air 13 ticks, mind 21, water 18, earth 19, fire 20, body 13, nature 13, law
    21."""
    measured = {"air": 13, "mind": 21, "water": 18, "earth": 19, "fire": 20, "body": 13, "nature": 13, "law": 21}
    for rune, ticks in measured.items():
        from rlscape.sim.runecrafting import ENTER_TICKS
        assert abs(inside_ticks(rune) - ENTER_TICKS - ticks) <= 1, rune


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
    air, nature = RunecraftAtRuins("air"), RunecraftAtRuins("nature")
    state = character({}, {rcd.RUNE_ESSENCE: 10, rcd.PURE_ESSENCE: 10, rcd.talismans()["air"]: 1}, runecrafting=11)
    air._restock(state)
    assert state.inventory.get(rcd.RUNE_ESSENCE) == 10 and rcd.PURE_ESSENCE not in state.inventory  # one kind a load
    only_rune = character({}, {rcd.RUNE_ESSENCE: 50, rcd.talismans()["nature"]: 1, 995: 60}, runecrafting=44)
    assert nature.held_units(only_rune) == 0 and not nature.available(only_rune)


@needs_server
def test_law_banks_the_arms_entranas_monks_refuse_and_nature_carries_its_fares():
    law = RunecraftAtRuins("law")
    state = character({}, {rcd.PURE_ESSENCE: 27, rcd.talismans()["law"]: 1}, runecrafting=54)
    state.equipment = {WEAPON: BRONZE_SWORD}
    assert law.station(state) is not None and law.available(state)  # reachable once the sword is banked
    law._restock(state)
    assert WEAPON not in state.equipment and state.bank.get(BRONZE_SWORD) == 1
    nature = RunecraftAtRuins("nature")
    poor = character({}, {rcd.PURE_ESSENCE: 27, rcd.talismans()["nature"]: 1, COINS: 59}, runecrafting=44)
    assert not nature.available(poor)  # the Karamja boat, 30 gp each way
    rich = character({}, {rcd.PURE_ESSENCE: 27, rcd.talismans()["nature"]: 1, COINS: 100}, runecrafting=44)
    assert nature.available(rich)
    nature._restock(rich)
    assert rich.inventory.get(COINS) == 60 and rich.inventory.get(rcd.PURE_ESSENCE) == 26


@needs_server
def test_runecrafting_has_its_slots_kit_and_rates():
    assert "runecrafting" in SKILLS and len(runecrafting_paths()) == 2 * len(RC_RUNES) + 10 == 26  # with abyss_rc_
    assert "chaos" not in RC_RUNES and not any("chaos" in p.id for p in runecrafting_paths())  # Caleb, 2026-11-09
    ids = {p.id for p in path_options()}
    assert {"rc_air", "rc_law"} <= ids and "rc_cosmic" not in ids and "mine_essence" not in ids  # OQ-45 (a): the
    # cosmic altar only by the Abyss; essence isn't mined (Caleb)
    state = character({rcd.PURE_ESSENCE: 20, rcd.talismans()["air"]: 1, COINS: 5})
    assert kit(state, "runecrafting") == {rcd.PURE_ESSENCE, rcd.talismans()["air"]} <= inputs()
    banked = character({}, {rcd.RUNE_ESSENCE: 1_000, rcd.talismans()["air"]: 1}, runecrafting=20)
    rate = path_rate(RunecraftAtRuins("air"), banked)
    assert rate.gather_xp > 0 and rate.process_xp == 0
    assert SkillingSlots().candidate(banked, "runecrafting", 0).path.id == "rc_air"


@needs_server
def test_a_paths_essence_and_talisman_are_bought_on_the_ge():
    """Essence isn't mined (Caleb), so it's bought, with the talisman (Choice A (a) and I (a)): rune essence and pure in
    lots of 1,000, talismans and plain tiaras in lots of 14 (a tiara load), a rune's tiara one at a time and not again
    while held."""
    from rlscape.sim.buying import RUNECRAFTING_INPUTS, BuyGE
    from rlscape.vocabulary import vocabulary
    assert set(RUNECRAFTING_INPUTS) <= set(vocabulary()) and len(RUNECRAFTING_INPUTS) == 19
    state, rng = character({COINS: 1_000_000}, runecrafting=1), np.random.default_rng(0)
    path, talisman = RunecraftAtRuins("air"), rcd.talismans()["air"]
    assert not path.available(state)
    for item in (talisman, rcd.RUNE_ESSENCE):
        assert BuyGE(item).run(state, rng, 10_000).termination == "completed"
    noted = gd.noted_ids()
    assert state.inventory.get(noted[talisman]) == 14 and state.inventory.get(noted[rcd.RUNE_ESSENCE]) == 1_000
    assert path.available(state)
    tiara = rcd.tiaras()["air"][0]
    BuyGE(tiara).run(state, rng, 10_000)
    assert state.inventory.get(tiara) == 1 and not BuyGE(tiara).available(state)


@needs_server
def test_a_worn_tiara_lets_the_character_in_and_the_trip_carries_28_essence():
    tiara, talisman = rcd.tiaras()["air"][0], rcd.talismans()["air"]
    path = RunecraftAtRuins("air")
    state = character({}, {rcd.RUNE_ESSENCE: 100, tiara: 1, talisman: 1}, runecrafting=1)
    state.equipment = {HAT: 1139}  # a bronze med helm, which goes to the bank
    assert path.available(state)
    path._restock(state)
    assert state.equipment[HAT] == tiara and state.bank.get(1139) == 1
    assert state.inventory == {rcd.RUNE_ESSENCE: 28} and state.bank.get(talisman) == 1  # no talisman: a 28th essence
    without = character({}, {rcd.RUNE_ESSENCE: 100, talisman: 1}, runecrafting=1)
    path._restock(without)
    assert without.inventory == {talisman: 1, rcd.RUNE_ESSENCE: 27}
    stock = {rcd.RUNE_ESSENCE: 5_000, talisman: 1}  # more than an hour uses: then the 28th essence shows
    assert path_rate(path, character({}, {**stock, tiara: 1})).gather_xp > path_rate(path, character({}, stock)).gather_xp


@needs_server
def test_a_tiara_path_makes_a_tiara_of_each_pair_and_uses_the_talisman_up():
    """TalismanEnchantingListener: a plain tiara and the talisman on the altar make the rune's tiara for its XP."""
    tiara, talisman = rcd.tiaras()["fire"], rcd.talismans()["fire"]
    path = MakeTiaraAtRuins("fire")
    assert path.id == "make_tiara_fire" and not path.available(character({}, {rcd.PLAIN_TIARA: 5}))
    state = character({}, {rcd.PLAIN_TIARA: 20, talisman: 16})
    assert path.available(state) and path.held_units(state) == 16
    result = path.run(state, np.random.default_rng(0), 5_000)
    assert result.termination == "inputs_exhausted"
    made = state.inventory.get(tiara[0], 0) + state.bank.get(tiara[0], 0)
    assert made == 16 and state.bank.get(rcd.PLAIN_TIARA, 0) + state.inventory.get(rcd.PLAIN_TIARA, 0) == 4
    assert state.xp[SKILL_INDEX["runecrafting"]] == pytest.approx(16 * tiara[1])
    assert path_rate(path, character({}, {rcd.PLAIN_TIARA: 100, talisman: 100})).gp < 0  # for the XP
