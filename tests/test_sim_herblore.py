"""Herblore in the sim (sim v1, docs/sim-v1-skills-draft.md §4): cleaning herbs and the 21 standard potions, with
grinding, as the server's HerbCleanListener, HerblorePulse and GrindItemPlugin make them."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim.herblore import (CLEAN_TICKS, START_TICKS, CleanAtBank, PotionAtBank, finished_ticks, grind_ticks,
                                  unfinished_ticks)
from rlscape.sim.kits import kit
from rlscape.sim.skilling import SKILLS, SkillingSlots, path_options, path_rate
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState
from rlscape.travel import BANKING_TICKS

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
VIAL, PESTLE = gd.VIAL_OF_WATER, gd.PESTLE_AND_MORTAR
GRIMY_GUAM, GUAM, GUAM_UNF, EYE_OF_NEWT, ATTACK_3 = 199, 249, 91, 221, 121
IRIT, UNICORN_HORN, UNICORN_DUST, SUPER_ANTIPOISON_3 = 259, 237, 235, 181


def character(inventory: dict[int, int], bank: dict[int, int] | None = None, herblore: int = 1) -> CharacterState:
    state = CharacterState.fresh()
    state.inventory, state.bank = dict(inventory), dict(bank or {})
    state.xp[SKILL_INDEX["herblore"]] = float(XP_FOR_LEVEL[herblore])
    return state


def made(state: CharacterState, item: int) -> int:
    return state.inventory.get(item, 0) + state.bank.get(item, 0)


def herblore_xp(state: CharacterState, level: int) -> float:
    return state.xp[SKILL_INDEX["herblore"]] - XP_FOR_LEVEL[level]


@needs_server
def test_the_herbs_potions_and_dusts_follow_the_servers_enums():
    herbs, potions = gd.herbs(), gd.herblore_potions()
    assert len(herbs) == 15 and (herbs["guam"].level, herbs["guam"].experience) == (3, 2.5)
    assert (herbs["torstol"].grimy, herbs["torstol"].clean, herbs["torstol"].level) == (219, 269, 75)
    assert len(potions) == 21  # Choice E (a): the standard potions
    attack = potions["attack"]
    assert (attack.herb, attack.unfinished, attack.secondary, attack.level, attack.experience, attack.product) == (
        GUAM, GUAM_UNF, EYE_OF_NEWT, 3, 25.0, ATTACK_3)
    assert potions["saradomin_brew"].secondary == gd.grindings()[5075]  # crushed nest, from a bird's nest
    assert gd.grindings()[UNICORN_HORN] == UNICORN_DUST and potions["super_antipoison"].secondary == UNICORN_DUST


def test_the_pulses_timing():
    """HerblorePulse: a batch of unfinished potions one a tick; a lone potion, unfinished or finished, after 4 ticks
    (no how-many); finished ones from 4 ticks, then every 3. Grinding every 2. A batch starts with its clicks."""
    assert unfinished_ticks(1) == 4 and finished_ticks(1) == 4
    assert unfinished_ticks(9) == START_TICKS + 1 + 8 and finished_ticks(9) == START_TICKS + 4 + 8 * 3
    assert grind_ticks(9) == START_TICKS + 2 + 8 * 2


@needs_server
def test_a_cleaning_path_cleans_the_banked_herbs_a_load_at_a_time_for_their_xp():
    path = CleanAtBank(gd.herbs()["guam"])
    assert path.id == "clean_guam" and not path.available(character({}, {GRIMY_GUAM: 50}, herblore=2))
    state = character({}, {GRIMY_GUAM: 50}, herblore=3)
    result = path.run(state, np.random.default_rng(0), 3_000)
    assert result.termination == "inputs_exhausted" and made(state, GUAM) == 50 and made(state, GRIMY_GUAM) == 0
    assert herblore_xp(state, 3) == pytest.approx(50 * 2.5)


@needs_server
def test_a_potion_path_cleans_mixes_and_finishes_nine_a_load():
    """From grimy guam, vials and eyes of newt: 9 a load (3 slots each), the herbs cleaned for their XP too."""
    path = PotionAtBank(gd.herblore_potions()["attack"])
    state = character({}, {VIAL: 27, GRIMY_GUAM: 27, EYE_OF_NEWT: 27}, herblore=3)
    assert path.id == "potion_attack" and path.held_units(state) == 27
    result = path.run(state, np.random.default_rng(0), 5_000)
    assert result.termination == "inputs_exhausted" and made(state, ATTACK_3) == 27
    assert herblore_xp(state, 3) == pytest.approx(27 * (25 + 2.5))
    assert not any(made(state, i) for i in (VIAL, GRIMY_GUAM, GUAM, GUAM_UNF, EYE_OF_NEWT))


@needs_server
def test_a_potion_path_starts_from_unfinished_potions_and_grinds_with_a_pestle():
    """Bought unfinished potions skip the herb (2 slots a unit); a whole unicorn horn counts only with a pestle and
    mortar, which the load takes out to grind it (Choice F (a))."""
    path = PotionAtBank(gd.herblore_potions()["super_antipoison"])
    irit_unf = gd.herblore_potions()["super_antipoison"].unfinished
    assert path.held_units(character({}, {irit_unf: 10, UNICORN_HORN: 10}, herblore=48)) == 0  # no pestle
    state = character({}, {irit_unf: 10, UNICORN_HORN: 6, UNICORN_DUST: 4, PESTLE: 1}, herblore=48)
    assert path.held_units(state) == 10
    path.run(state, np.random.default_rng(0), 5_000)
    assert made(state, SUPER_ANTIPOISON_3) == 10 and made(state, UNICORN_HORN) == 0 and made(state, PESTLE) == 1
    assert herblore_xp(state, 48) == pytest.approx(10 * 106.3)
    assert not PotionAtBank(gd.herblore_potions()["super_antipoison"]).available(
        character({}, {irit_unf: 10, UNICORN_DUST: 10}, herblore=47))  # the potion's level


@needs_server
def test_herblore_has_its_slots_kit_and_a_rate():
    assert "herblore" in SKILLS
    ids = {p.id for p in path_options() if p.skill == "herblore"}
    assert len(ids) == 36 and {"clean_torstol", "potion_saradomin_brew"} <= ids
    state = character({PESTLE: 1, GRIMY_GUAM: 5, VIAL: 5, 995: 10})
    assert kit(state, "herblore") == {PESTLE, GRIMY_GUAM, VIAL}
    banked = character({}, {VIAL: 270, GRIMY_GUAM: 270, EYE_OF_NEWT: 270}, herblore=3)
    rate = path_rate(PotionAtBank(gd.herblore_potions()["attack"]), banked, 3_000)
    load_ticks = CLEAN_TICKS * 9 + unfinished_ticks(9) + finished_ticks(9) + BANKING_TICKS
    loads = min(270 / 9, (3_000 - rate.travel) / load_ticks)  # a load of 9, from grimy herbs
    assert rate.xp == pytest.approx(loads * 9 * (25 + 2.5) * 6_000 / 3_000)
    assert SkillingSlots().candidate(banked, "herblore", 0).path.id == "potion_attack"
