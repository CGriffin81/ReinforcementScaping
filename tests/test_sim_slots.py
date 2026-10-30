"""Tests for the combat candidate slots: the slot and loot-mode actions, their mask, and what a slot's fight does."""

from __future__ import annotations

from math import inf

import pytest

from rlscape.combat import formulas as f
from rlscape.combat.access import Progress
from rlscape.combat.candidates import Character, enemy_pool, select_candidates
from rlscape.combat.rates import Plan, combat_rates
from rlscape.gamedata import server as gd
from rlscape.sim import Simulator, build_catalog
from rlscape.sim.equipment import fighter_for, wield_best
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.slots import MELEE_STYLES, RANGED_STYLES, CombatSlots, combat_options
from rlscape.sim.state import SPAWN, CharacterState
from rlscape.vocabulary import vocabulary

needs_data = pytest.mark.skipif(not (gd.SERVER_CONFIGS.exists() and gd.NPC_DEFINITIONS.exists()),
                                reason="server submodule or data/npc_definitions.csv missing")
SHRIMPS, BREAD, BRONZE_SWORD, WOODEN_SHIELD = 315, 2309, 1277, 1171
SHORTBOW, BRONZE_ARROW, MIND_RUNE = 841, 882, 558


def trained(level: int) -> CharacterState:
    state = CharacterState.fresh()
    for skill in ("attack", "strength", "defence", "hitpoints"):
        state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[level])
    state.hp = state.max_hp()
    return state


def ids_of(sim: Simulator) -> list[str]:
    return [o.id for o in sim.options]


def test_thirty_slot_actions_and_four_loot_modes():
    ids = [o.id for o in combat_options()]
    assert len(ids) == 34 == len(set(ids))
    assert ids[:4] == ["fight_melee_xp1_accurate", "fight_melee_xp1_aggressive", "fight_melee_xp1_defensive",
                       "fight_melee_xp2_accurate"]
    assert ids[18:30] == [f"fight_{c}_{k}{n}" for c in ("ranged", "magic") for k in ("xp", "gp") for n in (1, 2, 3)]
    assert ids[30:] == ["loot_all", "loot_valuable", "loot_vocabulary", "loot_none"]


def armed_by_hand(worn: dict[int, int], stacks: dict[int, int] = {}) -> CharacterState:  # noqa: B006
    state = CharacterState.fresh()
    for slot, item in worn.items():
        state.inventory.pop(item)
    state.equipment, state.worn_amounts = dict(worn), dict(stacks)
    return state


@needs_data
def test_slots_are_the_reference_ranking_for_the_character_as_armed():
    sim = Simulator(build_catalog())
    state = sim.reset(seed=0)
    slots = next(o for o in sim.options if o.family == "combat").slots
    # By hand, for each class: what its fight wields from the starter kit, the free slots that leaves (18 used at
    # spawn), 10 HP, 8 HP of starter food, the valuable loot mode, and fresh access.
    melee = armed_by_hand({3: BRONZE_SWORD, 5: WOODEN_SHIELD})  # 12 free
    ranged = armed_by_hand({3: SHORTBOW, 13: BRONZE_ARROW}, {13: 25})  # two-handed, so no shield; 12 free
    magic = armed_by_hand({5: WOODEN_SHIELD})  # no staff in the kit; wind strike (25 air, 15 mind runes); 11 free
    # Ammunition: unlimited for melee; 25 arrows of which 4 in 5 land and are picked back up: 125 shots in
    # expectation; 15 casts of wind strike (the mind runes run out first).
    cases = {"melee": (melee, 12, WOODEN_SHIELD, [Plan("melee", s) for s in MELEE_STYLES], inf),
             "ranged": (ranged, 12, None, [Plan("ranged", s) for s in RANGED_STYLES], 25 / (1 / 5)),
             "magic": (magic, 11, WOODEN_SHIELD, [Plan("magic", "wind_strike")], 15)}
    for combat_class, (armed, free, shield, plans, attacks) in cases.items():
        character = Character(SPAWN, 10, 10, 8, free, shield, "valuable", Progress(), attacks)
        reference = select_candidates(enemy_pool(), {combat_class: (fighter_for(armed), plans)}, character,
                                      1500, vocabulary=frozenset(vocabulary()))[combat_class]  # the catalog's V
        ours = [slots.candidate(state, combat_class, i) for i in range(len(reference))]
        assert len(reference) == 6
        assert [(c.entry.npc.id, c.site.spawn, c.plan.style) for c in ours] ==                [(c.entry.npc.id, c.site.spawn, c.plan.style) for c in reference]
    mask = dict(zip(ids_of(sim), sim.action_mask()))
    for i in range(6):  # each melee style is open exactly when it passes the filter, and every slot has one
        open_styles = [s for s in MELEE_STYLES if mask[f"fight_melee_{'xp' if i < 3 else 'gp'}{i % 3 + 1}_{s}"]]
        assert open_styles == [s for s in MELEE_STYLES if slots.candidate(state, "melee", i, s) is not None]
        assert open_styles
    assert all(mask[f"fight_{c}_{k}{n}"] for c in ("ranged", "magic") for k in ("xp", "gp") for n in (1, 2, 3))


@needs_data
def test_ranged_and_magic_slots_close_without_a_kit_or_runes():
    state = CharacterState.fresh()
    for item in (SHORTBOW, MIND_RUNE):
        state.inventory.pop(item)
    slots = CombatSlots()
    assert slots.candidate(state, "melee", 0) is not None
    assert slots.candidate(state, "ranged", 0) is None and slots.candidate(state, "magic", 0) is None


@needs_data
def test_a_style_is_masked_when_it_fails_the_retreat_filter_on_its_own():
    state = CharacterState.fresh()
    state.inventory = {k: v for k, v in state.inventory.items() if k not in (SHRIMPS, BREAD)}
    state.inventory[SHRIMPS], state.hp = 2, 6  # little food, a little hurt: some styles stop being affordable
    slots = CombatSlots()
    armed = CharacterState.fresh()
    wield_best(armed, "melee")
    fighter, partial = fighter_for(armed), 0
    for i in range(6):
        candidate = slots.candidate(state, "melee", i)
        assert candidate is not None
        passing = {s for s in MELEE_STYLES if slots.candidate(state, "melee", i, s) is not None}
        expected = {s for s in MELEE_STYLES
                    if combat_rates(fighter, Plan("melee", s), candidate.entry.npc, 0).passes_retreat_filter(10, 6, 6)}
        assert passing == expected and candidate.plan.style in passing
        partial += passing != set(MELEE_STYLES)
    assert partial > 0


@needs_data
def test_a_slot_fights_its_monster_with_the_chosen_style():
    sim = Simulator(build_catalog())
    state = sim.reset(seed=4)
    action = ids_of(sim).index("fight_melee_gp3_defensive")
    target = sim.options[action].slots.candidate(state, "melee", 5)
    info = sim.step(action).info
    assert info["option"]["target"] == target.entry.npc.id and info["option"]["style"] == f.DEFENSIVE
    assert info["option"]["site"] == target.site.spawn and info["option"]["kills"] >= 0
    assert set(info["xp_gained"]) <= {"defence", "hitpoints"} and info["xp_gained"]
    assert sim.state.equipment == {3: BRONZE_SWORD, 5: WOODEN_SHIELD}


@needs_data
def test_the_loot_mode_is_set_by_its_action_and_used_by_fights():
    sim = Simulator(build_catalog())
    sim.reset(seed=1)
    ids = ids_of(sim)
    mask = dict(zip(ids, sim.action_mask()))
    assert not mask["loot_valuable"] and mask["loot_none"]  # the current mode is masked: never a no-op
    info = sim.step(ids.index("loot_none")).info
    assert sim.state.loot_mode == "none" and info["duration"] == 1
    trained_state = trained(30)
    trained_state.loot_mode = "none"
    trained_state.tick = sim.state.tick
    sim.state = trained_state
    first_fight = next(a for a, ok in enumerate(sim.action_mask()) if ok and sim.options[a].family == "combat")
    info = sim.step(first_fight).info
    assert info["option"]["kills"] > 0 and info["termination"] != "inventory_full"
    assert not any(amount > 0 for amount in info["items_delta"]["inventory"].values())  # nothing picked up


@needs_data
def test_slots_follow_the_character():
    slots = CombatSlots()
    state = trained(30)
    at_lumbridge = [(c.entry.npc.id, c.site.spawn) for c in (slots.candidate(state, "melee", i) for i in range(6))]
    state.location = (2809, 3436, 0)  # Catherby
    at_catherby = [(c.entry.npc.id, c.site.spawn) for c in (slots.candidate(state, "melee", i) for i in range(6))]
    assert at_lumbridge != at_catherby


@needs_data
def test_fights_close_at_the_retreat_point_without_food():
    sim = Simulator(build_catalog())
    state = sim.reset(seed=0)
    fights = [o for o in sim.options if o.family == "combat"]
    state.hp = 5  # half of 10: a fight would retreat before its first swing
    food = {item: n for item, n in state.inventory.items() if item in gd.food_healing()}
    for item in food:
        state.inventory.pop(item)
    assert not any(o.available(state) for o in fights)
    state.inventory.update(food)  # with food it eats and fights on
    assert any(o.available(state) for o in fights)
