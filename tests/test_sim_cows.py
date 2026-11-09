"""kill_cows (Caleb, 2026-11-09): Crafting's supplies gathered by killing cows, their hides kept and their normal bones
buried, fought with the class and style that kill fastest."""

from __future__ import annotations

import numpy as np
import pytest

from rlscape.gamedata import server as gd
from rlscape.sim.economy import BankDeposit
from rlscape.sim.skilling import path_options, path_rate
from rlscape.sim.skills import SKILL_INDEX
from rlscape.sim.state import CharacterState

needs_server = pytest.mark.skipif(not gd.SERVER_CONTENT.exists(), reason="server submodule missing")
COWHIDE, BONES, RAW_BEEF = 1739, 526, 2132


@needs_server
def test_killing_cows_gathers_hides_and_buries_the_bones():
    path = {p.id: p for p in path_options()}["kill_cows"]
    state = CharacterState.fresh()
    assert path.skill == "crafting" and path.available(state)
    entry, plan, site = path.choice(state)
    assert entry.npc.name.lower() == "cow"
    result = path.run(state, np.random.default_rng(0), 6_000)
    hides, prayer = state.inventory.get(COWHIDE, 0), state.xp[SKILL_INDEX["prayer"]]
    assert hides > 0 and BONES not in state.inventory and RAW_BEEF not in state.inventory
    assert prayer == pytest.approx(gd.bone_experience()[BONES] * result.detail["buried"]) and result.detail["buried"] > 0
    assert state.xp[SKILL_INDEX["crafting"]] == 0  # no Crafting XP: it gathers
    state.task = path.task  # as the engine records it
    assert path.task == f"combat:{plan.combat_class}"
    BankDeposit().run(state, np.random.default_rng(0), 6_000)  # the deposit banks the hides
    assert COWHIDE not in state.inventory and state.bank[COWHIDE] == hides


@needs_server
def test_kill_cows_fights_with_the_fastest_kills():
    """"It will use the highest combat style so as to have faster kills": of the plans the character can fight cows
    with, the one with the most kills an hour (combat_rates)."""
    from rlscape.combat.rates import combat_rates
    from rlscape.sim.cows import cow_entries
    from rlscape.sim.equipment import fighter_for
    from rlscape.sim.slots import _armed, _plans

    path = {p.id: p for p in path_options()}["kill_cows"]
    state = CharacterState.fresh()
    state.xp[SKILL_INDEX["strength"]] = 2_000.0  # Strength 15: aggressive should be fastest
    entry, plan, _ = path.choice(state)
    best = max(r.kills_per_hour for cls in ("melee", "ranged", "magic")
               for p in _plans(_armed(state, cls), cls) for e in cow_entries()
               if (r := combat_rates(fighter_for(_armed(state, cls)), p, e.npc, 0.0)) is not None)
    chosen = combat_rates(fighter_for(_armed(state, plan.combat_class)), plan, entry.npc, 0.0)
    assert chosen.kills_per_hour == pytest.approx(best)


@needs_server
def test_kill_cows_is_a_gp_path_in_craftings_slots():
    path = {p.id: p for p in path_options()}["kill_cows"]
    rate = path_rate(path, CharacterState.fresh())
    assert rate.gather_xp == 0 and rate.process_xp == 0 and rate.gp > 0
