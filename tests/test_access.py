"""Tests for the access table: the requirement grammar, the curated rules against server data, Slayer levels, and
what a fresh character is offered."""

from __future__ import annotations

import pytest

from rlscape.combat import formulas as f
from rlscape.combat.access import (
    MINIQUESTS,
    Progress,
    access_rules,
    can_reach,
    meets_slayer_level,
    parse_requirement,
)
from rlscape.combat.candidates import Character, enemy_pool, select_candidates
from rlscape.combat.rates import Fighter, Plan
from rlscape.gamedata import server as gd

needs_data = pytest.mark.skipif(not (gd.SERVER_CONFIGS.exists() and gd.NPC_DEFINITIONS.exists()),
                                reason="server submodule or data/npc_definitions.csv missing")


def test_requirement_grammar():
    fee_or_quest = parse_requirement("quest:THE_FREMENNIK_TRIALS or coins:1000")
    assert not fee_or_quest.met(Progress(coins=999))
    assert fee_or_quest.met(Progress(coins=1000))
    assert fee_or_quest.met(Progress(quests_complete=frozenset({"THE_FREMENNIK_TRIALS"})))

    fee_and_axe = parse_requirement("coins:875&item:1351|1359")
    assert not fee_and_axe.met(Progress(coins=875))
    assert fee_and_axe.met(Progress(coins=875, items_held=frozenset({1359})))

    assert parse_requirement("level:agility:70").met(Progress(levels=(("agility", 70),)))
    assert not parse_requirement("level:agility:70").met(Progress())
    assert not parse_requirement("never").met(Progress(coins=10**9))


def test_started_includes_complete_but_underway_does_not():
    done = Progress(quests_complete=frozenset({"DRAGON_SLAYER"}))
    doing = Progress(quests_underway=frozenset({"DRAGON_SLAYER"}))
    assert parse_requirement("started:DRAGON_SLAYER").met(done)
    assert parse_requirement("started:DRAGON_SLAYER").met(doing)
    assert parse_requirement("underway:DRAGON_SLAYER").met(doing)
    assert not parse_requirement("underway:DRAGON_SLAYER").met(done)


@needs_data
def test_every_rule_names_real_quests_and_npcs():
    quests = gd.quest_names() | MINIQUESTS
    spawned_names = {npc.name for npc_id, npc in gd.npcs().items() if npc_id in gd.spawns()}
    for rule in access_rules():
        rule.requires.met(Progress())  # every term kind is known
        for terms in rule.requires.alternatives:
            for term in terms:
                if term[0] in ("quest", "started", "underway"):
                    assert term[1] in quests, (rule.name, term)
        assert rule.npcs <= spawned_names, (rule.name, rule.npcs - spawned_names)
        assert rule.npcs or rule.bounds, rule.name  # a rule with neither would lock every NPC


@needs_data
def test_slayer_levels_come_from_every_task():
    text = gd.SLAYER_TASKS.read_text(encoding="utf-8")
    assert len(gd._TASK.findall(text)) == text.count("new int[]")
    levels = gd.slayer_levels()
    assert levels[1615] == 85 and levels[1612] == 15 and levels[81] == 1  # abyssal demon, banshee, cow
    assert not meets_slayer_level(1615, Progress())
    assert meets_slayer_level(1615, Progress(levels=(("slayer", 85),)))


@needs_data
def test_morytania_needs_priest_in_peril():
    undead_cow = (3624, 3530, 0)
    blamish_snail_west_of_server_borders = (3417, 3291, 0)
    done = Progress(quests_complete=frozenset({"PRIEST_IN_PERIL"}))
    for name, spawn in (("Undead cow", undead_cow), ("Ochre Blamish Snail", blamish_snail_west_of_server_borders)):
        assert not can_reach(name, spawn, Progress())
        assert can_reach(name, spawn, done)


@needs_data
def test_quest_monsters_only_while_the_quest_is_underway():
    melzar = (2935, 9649, 0)  # Melzar's Maze basement
    assert not can_reach("Melzar the Mad", melzar, Progress())
    assert can_reach("Melzar the Mad", melzar, Progress(quests_underway=frozenset({"DRAGON_SLAYER"})))
    assert not can_reach("Bouncer", (2600, 3150, 0), Progress(quests_complete=frozenset({"FIGHT_ARENA"})))


@needs_data
def test_fresh_character_is_offered_reachable_monsters_only():
    starter = tuple(map(sum, zip(gd.items()[1277].bonuses, gd.items()[1171].bonuses)))
    fresh = Fighter(1, 1, 1, 10, 1, 1, starter, 4)
    plans = {"melee": (fresh, [Plan("melee", f.AGGRESSIVE), Plan("melee", f.ACCURATE)])}
    lumbridge = Character((3222, 3218, 0), 10, 10, 8, 26, None)
    names = {c.entry.npc.name for c in select_candidates(enemy_pool(), plans, lumbridge, 1500)["melee"]}
    assert "Cow" in names
    assert not names & {"Cockroach drone", "Undead chicken", "Undead cow"}  # the gated gp/hr slots before the table
