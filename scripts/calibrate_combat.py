"""Calibrate fights against the server (ROADMAP week 2; env contract §7), as scripts/calibrate.py does gathering: the
activity alone at the monster's site, on the live server and in the sim from the same start, against the ±20% gate.

The cases are the fights the sim would pick: for each band and class, a slot of the sim's own ranker
(rlscape.sim.slots) for a calibration character at Lumbridge: the top one by XP (`--slot 0`, the fit set the per-kill
overhead and the site capacity were fitted on, 2026-11-05) or another (`--slot 3`, the top by gp: a check set). The
character, per env contract §7 as the gathering runs have it: the band's combat levels and Prayer; and a combat
inventory (Caleb, 2026-11-06: "a good inventory for combat should be food and potions, with empty slots for drops"):
the band's standard gear (given at setup, as the tools are; at band 1 the starter kit's own weapon, shield or bow and
arrows), no starter kit, and only the food the fight needs (food_for: the sim's expected damage over the run, less
the hitpoints above the retreat point, plus FOOD_MARGIN). Both sides flick protection prayers when the Prayer level
allows: the sim's fights do (rlscape.combat.prayers), and the server's bridge does (`flick`), so a monster with one
style the prayer covers deals nothing. Both sides fight in the accurate style (the server's default), auto-retaliate
on, and loot with the case's mode (`--loot`, option catalog §4.D; the default, none, leaves every drop, as the fit set
was measured).

A server run: debug_teleport to the site's spawn (setup only), then as a person plays, a tick at a time: when the
character has no target and isn't walking, click "Attack" on the nearest monster of the case's id (in the case's
style: a ranged case in the ranker's, clicked on the weapon tab, as Caleb chose on 2026-11-07, or with --style
accurate the server's default, as before; melee in accurate); eat when
hitpoints are at or under half (the sim's rule, rlscape.sim.health); click again only after IDLE_TICKS idle, as a
person waits for the walk to start. Attacked with no target (an eat click stops the fight on this server; a monster of
another kind engaged it, OQ-35), it attacks the attacker back at once, its own kind first (2026-11-08: waiting for
auto-retaliate took 8 ticks an eat at the poison spiders, 1.28 to 1.17); stop when there's no food left to eat then
(the sim retreats), at death, or when the budget runs out. Busy STUCK_TICKS without XP, it walks back to the spawn.
A monster it sees listed alive at 0 hitpoints never dies (the server's null killer, OQ-44 (a)): the run records it
(`at_zero`) and the report flags the case, whose site is then likely a hazard.
Ranged fights safespot as the sim's do (rlscape.combat.safespots; Caleb, 2026-11-07, OQ-27 (d)): where the sim's
fight shoots from the site's safespot, the runner stands on it (setup only) with auto-retaliate off, as rangers
safespotting do (retaliating walks them off it), and attacks only a monster it holds against, once that one stands
still where it holds (the bridge's `npcs`), so the chase sticks; between kills it fetches its drops and arrows and
walks back; walked off it in a fight (the target stepped before its first hit landed), it clicks back onto it. Ranged loots only between kills (no target), so its arrows wait for the kill; while aggressive monsters
guard them and aggression hasn't run out (TOLERANCE_TICKS at the site), it leaves them until the oldest would go, and against dragons wears the
anti-dragon shield it carries for that trip, the bow back after (Caleb, OQ-33).
Magic casts by hand, as the sim assumes (option catalog §4.B): the band's spell (MAGIC) on the monster (the bridge's
`cast`, a client's spell-on-NPC packet), auto-retaliate off. A hand cast is one spell and stops the combat pulse, so
it casts again on the same monster each tick until one is taken (the server refuses a cast within 3 ticks of the
last), which then lands when the next attack is due: the autocast rate the sim assumes. The kill is when that monster
is no longer listed alive (`npcs`), or, another kind, no longer attacking; its loot waits for it, as ranged's does.
Between kills it casts on whatever attacks it, the case's kind first, as retaliating would: in single combat another
kind attacking it holds it "under attack", so it's fought back before the next (OQ-19's monsters near a fight).
Looting, as a person loots their own kills: after a kill it waits for the drop (up to DROP_WAIT_TICKS, the default
death animation, DeathTask) before the next attack; between kills, attacked or not (Caleb, 2026-11-07: the sim picks
up after every kill), it takes the nearest of its own drops the loot mode keeps and has room for (`take`, after
TAKE_IDLE_TICKS standing still), arrows included; it stops when the
inventory is full and the mode keeps something from the monster's drops that needs a slot (the sim's rule). Loot is
the value (data/prices_v2.csv) of what the inventory gained, the ammunition aside.
The sim runs its fight from the same state at the spawn, many times. Kills are counted from Hitpoints XP (1.33 per
damage, capped at the monster's hitpoints, as on both sides).

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/calibrate_combat.py [--bands 1 31 61 91] [--classes melee ranged] [--runs 3] [--slot 0]
    uv run python scripts/calibrate_combat.py --cases-from results/calibration/combat-....json   (its cases again)
Without the server, the sim's side of saved server runs again, with the sim as it is now:
    uv run python scripts/calibrate_combat.py --resim results/calibration/combat-....json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Any

import numpy as np

from rlscape.bridge.client import BridgeClient, BridgeError, run_suffix
from rlscape.combat.candidates import (ANTI_DRAGON_SHIELD, LOOT_MODES, SITE_RADIUS, enemy_pool, loot_rule,
                                       special_damage_shields)
from rlscape.combat.safespots import GROUND_TICKS, style_range, trip_ticks
from rlscape.combat.rates import HP_XP_PER_DAMAGE, Plan, combat_rates
from rlscape.gamedata import server as gd
from rlscape.sim.combat import fight, safespot_for
from rlscape.sim.equipment import fighter_for, wield_best
from rlscape.sim.health import retreat_hp
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.slots import CombatSlots
from rlscape.sim.state import SPAWN, TOLERANCE_TICKS, CharacterState
from rlscape.vocabulary import vocabulary

REPO = Path(__file__).resolve().parents[1]
GATE = 0.2
TICKS_PER_HOUR = 6000
STUCK_TICKS = 30  # a target and no XP this long: something holds the character
TAKE_IDLE_TICKS = 2  # still this long before taking the next drop: the walk to it starts a tick after the click
DROP_WAIT_TICKS = 6  # after a kill, waiting for the drop: DeathTask's default death animation
LOOT_RADIUS = 15  # tiles: the drops a person looting sees and goes for
MARK_RADIUS = 32  # tiles: a caster watches the monster it fights this far (the bridge's attackers' reach)
INVENTORY_SLOTS = 28
IDLE_TICKS = 3  # idle this long before clicking again: a click on a monster a few tiles off takes a tick or two to
# start the walk, and clicking again meanwhile restarts it (a person clicks once and waits)
COMBAT = ("attack", "strength", "defence", "hitpoints", "ranged")
XP_SKILLS = (*COMBAT, "magic")  # the XP counted (magic: a magic case's)
TROUT, LOBSTER = 333, 379
FOOD_MARGIN, MAX_FOOD = 2, 15  # food beyond the expected damage's, and at most
# The band's standard gear (no quest items: no dragon weapons, no rune platebody or green d'hide body)
MELEE = {31: (1331, 1161, 1111, 1073, 1199),  # adamant scimitar, full helm, chainbody, platelegs, kiteshield
         61: (1333, 1163, 1113, 1079, 1201), 91: (1333, 1163, 1113, 1079, 1201)}  # rune
MELEE[1] = (1277, 1171)  # the starter kit's bronze sword and wooden shield
RANGED = {1: ((841, 1), (882, 500)),  # the starter kit's shortbow, and its bronze arrows made 500
          31: ((853, 1), (890, 500), (1169, 1), (1129, 1), (1095, 1)),  # maple shortbow, adamant arrows, coif, leather
          # rune crossbow and rune bolts (Caleb, 2026-11-07: one-handed, so the anti-dragon shield is worn), coif,
          # leather body, green d'hide chaps
          61: ((9185, 1), (9144, 500), (1169, 1), (1129, 1), (1099, 1)),
          91: ((9185, 1), (9144, 500), (1169, 1), (1129, 1), (1099, 1))}
# A ranger also carries an anti-dragon shield, worn for a late pickup trip where dragons guard its arrows (Caleb,
# 2026-11-07, OQ-33); a bow takes no shield, so it stays in the inventory otherwise
RANGED = {band: (*kit, (ANTI_DRAGON_SHIELD, 1)) for band, kit in RANGED.items()}
# The band's magic gear (agent choice, reversible): band 1 none, as a fresh character has; wizard robes and a staff of
# air (31), mystic robes and a staff of fire (61, 91), with an amulet of magic; and the runes for MAGIC_CASTS casts of
# the band's spell, less the rune the staff stands in for. The spell is the best the band's Magic level casts with them.
MAGIC = {1: ((), "wind_strike"),
         31: ((579, 577, 1011, 1727, 1381), "earth_bolt"),  # wizard hat, robe, blue skirt, amulet, staff of air
         61: ((4089, 4091, 4093, 4097, 1727, 1387), "fire_blast"),  # mystic hat, top, bottom, boots, staff of fire
         91: ((4089, 4091, 4093, 4097, 1727, 1387), "fire_wave")}
MAGIC_CASTS = 400  # a 1,500-tick run casts at most 300 (one every 5 ticks)
FOOD = {1: TROUT}  # above band 1: lobsters
WEAPON_TABS = {"CROSSBOW": 79}  # the weapon tab with the weapon wielded (WeaponInterfaces.CROSSBOW; bows, BOW's 77)
BOW_TAB = 77
BOW_STYLE_BUTTONS = {"accurate": 2, "rapid": 4, "longrange": 3}  # WeaponInterface.setAttackStyle's, bows and crossbows


@dataclass(frozen=True)
class Case:
    combat_class: str
    band: int
    npc: int
    name: str
    site: tuple[int, int, int]
    hitpoints: int  # the monster's
    slot: int = 0  # the ranker's slot it came from
    loot: str = "none"  # the loot mode both sides fight with
    style: str = "accurate"  # the attack style both sides fight in

    @property
    def plan(self) -> Plan:
        return Plan(self.combat_class, self.style)


def gear(case_class: str, band: int) -> tuple[tuple[int, int], ...]:
    if case_class == "melee":
        return tuple((item, 1) for item in MELEE.get(band, ()))
    if case_class == "magic":
        items, spell = MAGIC[band]
        staves = gd.staff_runes()
        runes = {rune: n * MAGIC_CASTS for rune, n in gd.combat_spells()[spell].runes.items()
                 if not set(items) & staves.get(rune, frozenset())}
        return (*((item, 1) for item in items), *runes.items())
    return RANGED[band]


def trained(case_class: str) -> tuple[str, ...]:
    """The skills set to the band: the combat skills and Prayer, and Magic for a magic case (melee and ranged cases
    keep Magic at 1, as the fit and check sets were measured)."""
    return (*COMBAT, "prayer", *(("magic",) if case_class == "magic" else ()))


def food_item(band: int) -> int:
    return FOOD.get(band, LOBSTER)


def character(combat_class: str, band: int, food: int = MAX_FOOD) -> CharacterState:
    """The calibration character in the sim, before its fight wields anything: the band's levels and Prayer, its gear
    and `food` of the band's food, and no starter kit."""
    state = CharacterState.fresh()
    state.inventory.clear()
    if band > 1:
        for skill in trained(combat_class):
            state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[band])
        state.hp = state.max_hp()
    for item, amount in gear(combat_class, band):
        state.add(item, amount)
    if food:
        state.add(food_item(band), food)
    return state


def case_safespot(case: "Case", budget: int) -> gd.RangedSafespot | None:
    """The safespot the sim's fight shoots from in this case, if it does (rlscape.sim.combat.safespot_for)."""
    state = character(case.combat_class, case.band, food=0)
    wield_best(state, case.combat_class)
    entry = next(e for e in enemy_pool() if e.npc.id == case.npc)
    site = next(s for s in entry.sites if s.spawn == case.site)
    return safespot_for(state, case.plan, entry.npc, site, budget)


def food_for(case: "Case", budget: int) -> int:
    """The food a fight of `budget` ticks needs: the sim's expected damage over it (prayers flicked as the fight
    flicks them, so none from a monster whose one style they cover; none from a safespot), less the hitpoints above
    the retreat point, in the band's food, plus FOOD_MARGIN; at most MAX_FOOD."""
    state = character(case.combat_class, case.band, food=0)
    wield_best(state, case.combat_class)
    npc = gd.npcs()[case.npc]
    rates = combat_rates(fighter_for(state), case.plan, npc, 0.0)
    if rates is None:
        return MAX_FOOD
    taken = 0.0 if case_safespot(case, budget) is not None else rates.damage_taken_per_hour
    damage = taken * budget / TICKS_PER_HOUR - (state.hp - retreat_hp(state))
    heal = gd.food_healing()[food_item(case.band)]
    return min(max(ceil(damage / heal), 0) + FOOD_MARGIN, MAX_FOOD)


def cases(bands: list[int], classes: list[str], slot: int = 0, loot: str = "none", ranked_style: bool = False) -> list[Case]:
    """The sim ranker's slot (0: the top by XP) for each band and class, the character at Lumbridge, ranking with
    the loot mode (without looting, with the fresh character's, as the fit set was chosen). Fought in the accurate
    style, or with `ranked_style` a ranged case in the ranker's (its safespot can need a long-ranged bow's reach)."""
    slots, out = CombatSlots(VOCABULARY), []
    for band in bands:
        for combat_class in classes:
            state = character(combat_class, band)
            state.location = SPAWN
            if loot != "none":
                state.loot_mode = loot
            candidate = slots.candidate(state, combat_class, slot)
            if candidate is None:
                continue
            npc = candidate.entry.npc
            # magic: the spell is its plan's style
            ranked = combat_class == "magic" or (ranked_style and combat_class == "ranged")
            style = candidate.plan.style if ranked else "accurate"
            out.append(Case(combat_class, band, npc.id, npc.name, candidate.site.spawn, npc.hitpoints, slot, loot,
                            style))
    return out


VOCABULARY = vocabulary()


def loot_gp(before: dict[int, int], after: dict[int, int], ammo: set[int]) -> float:
    """The value of what the inventory gained, the ammunition aside."""
    values = gd.item_values()
    return float(sum(max(0, n - before.get(item, 0)) * values.get(item, 0) for item, n in after.items()
                     if item not in ammo))


def fills_inventory(case: Case) -> bool:
    """Whether the loot mode keeps something from the monster's drops that needs a slot of its own."""
    keep, stackable = loot_rule(case.loot, VOCABULARY), gd.stackable_items()
    drops = next(e for e in enemy_pool() if e.npc.id == case.npc).drops
    return any(keep(i) and i not in stackable for i in (drops.expected_items() if drops else ()))


def worn_by_the_sim(case: Case) -> list[int]:
    """What the sim's fight wields from the character's inventory (rlscape.sim.equipment.wield_best)."""
    state = character(case.combat_class, case.band)
    wield_best(state, case.combat_class)
    return list(state.equipment.values())


def xp(state: dict[str, Any], skill: str) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == skill)


def food_held(state: dict[str, Any]) -> list[int]:
    return [i["id"] for i in state["inventory"] if i["id"] in gd.food_healing()]


def food_count(state: dict[str, Any]) -> int:
    """The food items carried. What it loses between readings is food eaten: an eat click lands a tick after it's
    sent, so the runner can click twice for one bite (2026-11-06: every poison spider run counted 30 clicks for its
    15 lobsters), and clicks overstate it."""
    heals = gd.food_healing()
    return sum(i["amount"] for i in state["inventory"] if i["id"] in heals)


def holding(state: dict[str, Any]) -> dict[int, int]:
    out: dict[int, int] = {}
    for stack in state["inventory"]:
        out[stack["id"]] = out.get(stack["id"], 0) + stack["amount"]
    return out


def alive_at_zero(state: dict[str, Any], npcs: list[dict[str, Any]]) -> dict[int, int]:
    """The monsters listed alive at 0 hitpoints (index -> id): stuck there, never dying (OQ-44 (a)). A death starts
    in the same tick the hitpoints reach 0 and stops the monster's own fight (ImpactHandler.handleImpact), so a
    monster `npcs` lists (no dying ones) or one attacking the character at 0 is stuck: the server's null killer when
    its top damager has left the world, which a Kotlin MapArea zone throws on. A sign of a hazard, not a rate."""
    return {m["index"]: m["id"] for m in (*npcs, *state["attackers"]) if m["hitpoints"] <= 0}


def setup(client: BridgeClient, case: Case, budget: int) -> tuple[int, dict | None]:
    """The character for a run, at the site; with the sim's safespot for the case, on it (the server's tile the sim's
    is, found again for this world's monster indices) with the indices of those it holds against. Despawned if
    anything fails, so no character is left in the world."""
    uid = client.spawn()["uid"]
    try:
        return uid, _prepare(client, uid, case, budget)
    except BaseException:
        client.despawn(uid)
        raise


def _prepare(client: BridgeClient, uid: int, case: Case, budget: int) -> dict | None:
    if case.band > 1:
        client.debug_set_levels(uid, {skill: case.band for skill in trained(case.combat_class)})
    for item in {i["id"] for i in client.state(uid)["inventory"]}:
        client.item_option(uid, item, "Drop")  # no starter kit: a combat inventory
    client.wait(2)  # the last drops land a tick later
    assert not client.state(uid)["inventory"], "the starter kit didn't all drop"
    food = food_for(case, budget)
    for item, amount in (*gear(case.combat_class, case.band), *([(food_item(case.band), food)] if food else [])):
        client.debug_give(uid, item, amount)
    for item in worn_by_the_sim(case):
        held = {i["id"] for i in client.state(uid)["inventory"]}
        if item not in held:
            continue  # the starter kit's, already worn
        for option in ("Wield", "Wear"):
            try:
                client.item_option(uid, item, option)
                break
            except BridgeError:
                continue
        client.wait(1)
    worn = {i["id"] for i in client.state(uid)["equipment"]}
    assert set(worn_by_the_sim(case)) <= worn, f"wearing {worn}, the sim wears {worn_by_the_sim(case)}"
    if case.combat_class == "ranged" and case.style != "accurate":  # the weapon tab's button (setAttackStyle)
        weapon = next(i["id"] for i in client.state(uid)["equipment"] if i["id"] in gd.ranged_weapons())
        tab = WEAPON_TABS.get(gd.ranged_weapons()[weapon].weapon_type, BOW_TAB)
        assert client.interface_button(uid, tab, BOW_STYLE_BUTTONS[case.style]), f"no {case.style} button"
    spot = case_safespot(case, budget)
    # off for rangers safespotting (retaliating walks them off the tile) and for casters: a hand cast stops the
    # combat pulse, and retaliating then would swing the staff in melee
    client.set_retaliate(uid, spot is None and case.combat_class != "magic")
    client.flick(uid)  # protection prayers, as the sim's fights flick them (none below their levels)
    if spot is None:
        client.debug_teleport(uid, *case.site)
        client.wait(3)
        return None
    # straight onto the sim's tile, asking from there: standing at the site among aggressive monsters, one engaging
    # it would hold it "under attack" in single combat (MapZone.continueAttack) and follow it to the tile
    client.debug_teleport(uid, *spot.tile)
    client.wait(1)
    tiles = client.ranged_safespots(uid, case.name, ids=[case.npc], radius=SITE_RADIUS, range=style_range(case.plan),
                                    limit=200, at=case.site)["tiles"]
    assert tiles, f"the server finds no safespot for {case.name} at {case.site} (range {style_range(case.plan)})"
    mine = [s for s in tiles if (s["tile"]["x"], s["tile"]["y"], s["tile"]["z"]) == spot.tile]
    chosen = (mine or tiles)[0]
    tile = (chosen["tile"]["x"], chosen["tile"]["y"], chosen["tile"]["z"])
    client.debug_teleport(uid, *tile)
    client.wait(2)
    return {"tile": tile, "held": {a["index"] for a in chosen["against"]}, "guarded": spot.pickup_threats > 0,
            "trip": trip_ticks(spot), "same_tile": bool(mine)}


def server_run(client: BridgeClient, case: Case, budget: int) -> dict[str, Any]:
    """One run on the server, a tick at a time (a `schedule` step sends the click decided from the last reading)."""
    uid, spot = setup(client, case, budget)
    try:
        attack = {"cmd": "interact", "uid": uid, "name": case.name, "option": "Attack", "object": False,
                  "ids": [case.npc], "packet": True}
        magic = case.combat_class == "magic"
        if magic:  # the case's spell cast on the monster, as a hand cast: one spell a click
            attack = {"cmd": "cast", "uid": uid, "name": case.name, "object": False, "ids": [case.npc],
                      "spell": gd.combat_spells()[case.style].button}
        mark, again = None, None  # magic: the monster it fights (an index), and the cast sent again after each spell
        clicked_back_at = -2  # when it last attacked an attacker back
        home = spot["tile"] if spot else case.site
        back = {"cmd": "walk_to", "uid": uid, "x": home[0], "y": home[1], "z": home[2], "packet": True}
        looting, keep, stackable = case.loot != "none", loot_rule(case.loot, VOCABULARY), gd.stackable_items()
        fills = looting and fills_inventory(case)
        ammo = {i["id"] for i in client.state(uid)["equipment"] if i["id"] in stackable}
        pending, first, prev_hp, prev_xp, last_gain, idle, still = [attack] if not spot else [], None, 0, 0.0, 0, 0, 0
        mine: dict[tuple[int, int, int], int] = {}  # its ground items (id, x, y) -> when first seen
        fighting, ended_at, dropped_at, started_at, last_kill = False, -DROP_WAIT_TICKS, -1, 0, 0
        counts = {"clicks": 0, "no_target": 0, "eaten": 0, "eat_clicks": 0, "hits_taken": 0, "damage_taken": 0,
                  "walked_back": 0, "taken": 0, "trips": 0, "off_tile": 0, "recasts": 0, "kills": 0,
                  "other_kills": 0,  # (kills counted for magic: of the case's monster, and of others it fought back)
                  "other_engagements": 0}  # monsters of other kinds that started attacking it (OQ-35)
        others: set[int] = set()  # the indices of other kinds attacking it at the last reading
        at_zero: dict[int, int] = {}  # monsters seen listed alive at 0 hitpoints, index -> id (OQ-44 (a))
        if spot:
            counts["same_tile"] = spot["same_tile"]
        food = None  # food carried at the last reading
        ended = "completed"
        fetching = False  # a safespotter out for its drops and arrows
        late, shield_on = False, False  # out late, the guards there; its shield worn for that against special damage
        guards_shield = next(iter(special_damage_shields(gd.npcs()[case.npc]) & set(holding(client.state(uid)))),
                             None)
        bow = client.state(uid)["equipment"]
        bow = next((i["id"] for i in bow if i["id"] in gd.ranged_weapons()), None)
        while True:
            # the case's monsters near it: for magic, whether the one it fights is still alive (the bridge lists no
            # dying one); on a safespot, which it holds against; for every run, any stuck alive at 0 (OQ-44 (a))
            reads = [{"cmd": "state", "uid": uid}, {"cmd": "ground_items", "uid": uid, "radius": LOOT_RADIUS},
                     {"cmd": "npcs", "uid": uid, "name": case.name, "ids": [case.npc], "object": False,
                      "radius": LOOT_RADIUS if spot else MARK_RADIUS, "range": style_range(case.plan)}]
            step = client.schedule([[*pending, *reads]])[0]
            results = step["results"]
            state, ground = results[len(pending)]["state"], results[len(pending) + 1]["items"]
            seen = results[-1]["npcs"] if spot or magic else []
            at_zero.update(alive_at_zero(state, results[-1].get("npcs", [])))
            if pending and pending[0].get("cmd") in ("interact", "cast") and "index" not in pending[0]:
                counts["clicks" if results[0].get("ok") else "no_target"] += 1
            if magic and pending and pending[0].get("cmd") == "cast" and results[0].get("ok"):
                mark = results[0]["index"]
                again = {**pending[0], "index": mark}
            first = first or (step["tick"], state)
            offset = step["tick"] - first[0]
            for item in ground:
                key = (item["id"], item["location"]["x"], item["location"]["y"])
                if item["own"] and key not in mine:
                    mine[key] = offset
                    dropped_at = offset
            if magic and mark is not None and mark not in {n["index"] for n in seen} | {
                    a["index"] for a in state["attackers"] if a["hitpoints"] > 0}:
                # dead, or dying: the case's monster no longer listed, another kind no longer attacking
                counts["kills" if again["ids"] == [case.npc] else "other_kills"] += 1
                mark = None
            # in a fight: a target; casting, a monster it casts on (each hand cast's combat pulse stops after it)
            engaged = mark is not None if magic else state["target"] is not None
            if engaged:
                if not fighting:
                    started_at = last_gain = offset  # STUCK_TICKS counts from the fight's start (a safespotter waits)
                fighting = True
            elif fighting:  # the target is gone: killed, most likely
                fighting, ended_at, last_kill = False, offset, offset - started_at
            attacking = {a["index"] for a in state["attackers"] if a["id"] != case.npc}
            counts["other_engagements"] += len(attacking - others)
            others = attacking
            hp, gained = state["hitpoints"], sum(xp(state, s) for s in XP_SKILLS)
            now = food_count(state)
            counts["eaten"] += max((food if food is not None else now) - now, 0)  # food looted only adds
            food = now
            if offset and hp < prev_hp:
                counts["hits_taken"] += 1
                counts["damage_taken"] += prev_hp - hp
            if gained > prev_xp:
                last_gain = offset
            prev_hp, prev_xp = hp, gained
            if spot and not fetching and (state["location"]["x"], state["location"]["y"],
                                          state["location"]["z"]) != spot["tile"]:
                counts["off_tile"] += 1  # a safespotter off its tile, not out for its loot
            if hp <= 0:
                ended = "died"
                break
            if offset >= budget:
                break
            free = INVENTORY_SLOTS - len(state["inventory"])
            if fills and free == 0:
                ended = "inventory_full"
                break
            held = holding(state)
            loot = [i for i in ground if (i["id"], i["location"]["x"], i["location"]["y"]) in mine and keep(i["id"])
                    and (free > 0 or (i["id"] in stackable and i["id"] in held))] if looting else []
            if (case.combat_class == "ranged" and state["target"] is not None) or (magic and engaged):
                loot = []  # its arrows wait for the kill; a caster's loot too, as the sim's picks up between kills
            if spot and loot and not fetching:
                # out for them between kills, unless the walk would take hits: guarded, aggression not yet run out;
                # then just before the oldest would go, the next kill and the walk counted (the sim's rule)
                oldest = min(mine[(i["id"], i["location"]["x"], i["location"]["y"])] for i in loot)
                # nothing attacking it (a stuck monster would hit it off the tile), and no guards unless tolerated
                safe = not state["attackers"] and (not spot["guarded"] or offset >= TOLERANCE_TICKS)
                if safe or offset - oldest + last_kill + spot["trip"] >= GROUND_TICKS:
                    fetching, late = True, not safe
                    counts["trips"] += 1
                else:
                    loot = []
            elif spot and not fetching:
                loot = []
            waiting = looting and offset - ended_at < DROP_WAIT_TICKS and dropped_at < ended_at
            pending = []
            if state["target"] is not None or state["moving"] or (state["attackers"] and not spot):
                idle = 0  # (on a safespot, monsters stuck attacking it don't hold it back)
            still = 0 if state["moving"] else still + 1
            max_hp = next(s["level"] for s in state["skills"] if s["name"].lower() == "hitpoints")
            if hp <= max_hp // 2:  # the sim's rule: eat at or under half (retreat_hp)
                held = food_held(state)
                if not held:
                    ended = "out_of_food"
                    break
                pending = [{"cmd": "item_option", "uid": uid, "item": held[0], "option": "Eat", "packet": True}]
                counts["eat_clicks"] += 1
            elif spot and not fetching and not loot and not state["moving"] and (
                    state["location"]["x"], state["location"]["y"], state["location"]["z"]) != spot["tile"]:
                # walked off its safespot (a target that stepped before its first hit chased from where the tile
                # doesn't hold it): back on, as a ranger re-clicks the spot; that stops the fight, which starts again
                pending = [back]
                counts["walked_back"] += 1
            elif loot and late and guards_shield and not shield_on:  # the shield on for the guarded trip (OQ-33)
                pending, shield_on = [{"cmd": "item_option", "uid": uid, "item": guards_shield, "option": "Wear",
                                       "packet": True}], True
            elif loot and still >= TAKE_IDLE_TICKS:
                # loot first, attacked or not (Caleb, 2026-11-07), as the sim picks up after each kill before the next:
                # the runner starts no fight with its loot on the ground, so a target now is one it retaliated on
                item = loot[0]
                pending, idle, still = [{"cmd": "take", "uid": uid, "item": item["id"], "x": item["location"]["x"],
                                         "y": item["location"]["y"], "packet": True}], 0, 0
                counts["taken"] += 1
            elif magic and engaged and offset - last_gain > STUCK_TICKS:  # its casts refused or not landing
                pending, last_gain, mark = [back], offset, None
                counts["walked_back"] += 1
            elif magic and engaged and state["target"] is None:
                # the spell cast, the pulse stopped: the next on the same monster at once. The server refuses it
                # within the last cast's 3-tick delay, so it's sent each tick until one starts the pulse, which casts
                # when the next attack is due (5 ticks after the last): the autocast rate the sim assumes
                pending = [again]
                counts["recasts"] += 1
            elif magic and state["target"] is None and not state["moving"] and not loot and not waiting and (
                    attackers := sorted((a for a in state["attackers"] if a["hitpoints"] > 0
                                         and (not spot or a["index"] in spot["held"])),  # on a safespot, held ones
                                        key=lambda a: a["id"] != case.npc)):
                # one attacking it, the case's kind first, as retaliating would: another kind holds it "under
                # attack" in single combat, so it's fought back before the next (a monster near the site, OQ-19)
                a = attackers[0]
                pending = [{**attack, "name": a["name"], "ids": [a["id"]], "index": a["index"]}]
                counts["clicks"] += 1
            elif spot and not loot and state["target"] is None and not state["moving"] and not waiting:
                # on the safespot (walking back to it first): a held monster standing still where it holds
                here = (state["location"]["x"], state["location"]["y"], state["location"]["z"])
                fetching, late = False, False
                if shield_on and bow is not None:  # the bow back on for the fight
                    pending, shield_on = [{"cmd": "item_option", "uid": uid, "item": bow, "option": "Wield",
                                           "packet": True}], False
                    continue
                if here != spot["tile"]:
                    pending = [back]
                    continue
                idle += 1
                ready = [n for n in seen if n["index"] in spot["held"] and n["holds"]
                         and (n["attacking_me"] or not (n["fighting"] or n["moving"]))]
                if ready and idle >= IDLE_TICKS:
                    pending, idle = [{**attack, "index": ready[0]["index"]}], 0
            elif not magic and not spot and state["target"] is None and not state["moving"] and not loot \
                    and offset - clicked_back_at > 1 and (
                    attackers := sorted((a for a in state["attackers"] if a["hitpoints"] > 0),
                                        key=lambda a: a["id"] != case.npc)):
                # attacked with no target (an eat click stops the fight on this server; another kind engaged it):
                # it attacks back at once, as a person clicks, rather than waiting for a hit to retaliate on (the
                # click lands a tick later, so not again in the next)
                a = attackers[0]
                pending, idle = [{**attack, "name": a["name"], "ids": [a["id"]], "index": a["index"]}], 0
                clicked_back_at = offset
                counts["clicks"] += 1
            elif state["target"] is None and not state["moving"] and not state["attackers"]:
                idle += 1
                if not loot and not waiting and idle >= IDLE_TICKS:
                    pending, idle = [attack], 0
            elif offset - last_gain > STUCK_TICKS and not spot:  # (a safespotter's hits are just slow)
                pending, last_gain = [back], offset
                counts["walked_back"] += 1
    finally:
        client.despawn(uid)
    out = {"ticks": offset, "ended": ended, **counts, "loot_gp": loot_gp(holding(first[1]), holding(state), ammo),
           "at_zero": [{"index": index, "id": npc} for index, npc in sorted(at_zero.items())]}
    for skill in XP_SKILLS:
        out[f"xp_{skill}"] = xp(state, skill) - xp(first[1], skill)
    return out


def sim_runs(case: Case, runs: int, budget: int) -> list[dict[str, Any]]:
    entry = next(e for e in enemy_pool() if e.npc.id == case.npc)
    site = next(s for s in entry.sites if s.spawn == case.site)
    out, keep = [], loot_rule(case.loot, VOCABULARY)
    food = food_for(case, budget)
    for seed in range(runs):
        state = character(case.combat_class, case.band, food)
        state.location = case.site
        before = {skill: state.xp[SKILL_INDEX[skill]] for skill in XP_SKILLS}
        food_before = sum(n for i, n in state.inventory.items() if i in gd.food_healing())
        hp_before = state.hp
        held, looted_food = dict(state.inventory), []
        add = state.add

        def add_counting_food(item: int, amount: int = 1) -> int:
            added = add(item, amount)
            if item in gd.food_healing():
                looted_food.append(added)
            return added
        state.add = add_counting_food  # food picked up isn't food eaten (only the drops add food here)
        result = fight(state, np.random.default_rng(seed), budget, entry, case.plan, site, keep)
        food_after = sum(n for i, n in state.inventory.items() if i in gd.food_healing())
        eaten = food_before + sum(looted_food) - food_after
        ammo = {item for item in state.equipment.values() if item in gd.stackable_items()}
        out.append({"ticks": result.ticks, "ended": result.termination, "eaten": eaten, "kills": result.detail["kills"],
                    **{f"xp_{s}": state.xp[SKILL_INDEX[s]] - before[s] for s in XP_SKILLS},
                    "hp_change": state.hp - hp_before, "loot_gp": loot_gp(held, state.inventory, ammo)})
    return out


def rates(runs: list[dict[str, Any]], case: Case) -> dict[str, float]:
    ticks = sum(r["ticks"] for r in runs)
    hp_xp = sum(r["xp_hitpoints"] for r in runs)
    combat_xp = sum(sum(r.get(f"xp_{s}", 0.0) for s in XP_SKILLS) for r in runs)  # (older files: no magic)
    return {"xp_per_hour": combat_xp * TICKS_PER_HOUR / ticks,
            "kills_per_hour": hp_xp / (HP_XP_PER_DAMAGE * case.hitpoints) * TICKS_PER_HOUR / ticks,
            "food_per_hour": sum(r["eaten"] for r in runs) * TICKS_PER_HOUR / ticks,
            "gp_per_hour": sum(r.get("loot_gp", 0.0) for r in runs) * TICKS_PER_HOUR / ticks,
            "ticks": float(np.mean([r["ticks"] for r in runs])), "runs": len(runs),
            "ended": {e: sum(r["ended"] == e for r in runs) / len(runs) for e in {r["ended"] for r in runs}},
            "xp_by_skill": {s: sum(r.get(f"xp_{s}", 0.0) for r in runs) * TICKS_PER_HOUR / ticks for s in XP_SKILLS}}


def compare(server: dict[str, Any], sim: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key in ("xp_per_hour", "kills_per_hour", "gp_per_hour", "food_per_hour", "ticks"):
        if not server[key] and not sim[key]:
            out[key] = {"server": 0.0, "sim": 0.0, "sim_over_server": 1.0, "within_gate": True}
            continue
        ratio = sim[key] / server[key] if server[key] else float("inf")
        out[key] = {"server": round(server[key], 1), "sim": round(sim[key], 1), "sim_over_server": round(ratio, 3),
                    "within_gate": abs(ratio - 1) <= GATE}
    return out


def report(case: Case, row: dict[str, Any]) -> None:
    c = row["compare"]
    print(f"{case.combat_class:6s} band {case.band:2d} {case.name:18s} xp/h server {c['xp_per_hour']['server']:7.0f} "
          f"sim {c['xp_per_hour']['sim']:7.0f} ({c['xp_per_hour']['sim_over_server']:.2f})  kills/h "
          f"{c['kills_per_hour']['server']:5.0f} {c['kills_per_hour']['sim']:5.0f}  gp/h "
          f"{c['gp_per_hour']['server']:6.0f} {c['gp_per_hour']['sim']:6.0f}  food/h "
          f"{c['food_per_hour']['server']:5.1f} {c['food_per_hour']['sim']:5.1f}  ended {row['server']['ended']} / "
          f"{row['sim']['ended']}")
    stuck = [run["at_zero"] for run in row["server_runs"] if run.get("at_zero")]  # (older files: none kept)
    if stuck:
        ids = sorted({m["id"] for found in stuck for m in found})
        print(f"  !! {len(stuck)} of {len(row['server_runs'])} server runs saw a monster alive at 0 hitpoints (ids "
              f"{ids}): stuck, a hazard here? (OQ-44 (a); its rates aren't the fight's)")


def resimulate(path: Path, runs: int, budget: int) -> None:
    """The sim's side of a saved file's server runs, again, with the sim as it is now; saved beside it."""
    saved, rows = json.loads(path.read_text()), []
    for old in saved["cases"]:
        case = Case(**{**old["case"], "site": tuple(old["case"]["site"])})
        row = {"case": old["case"], "server_runs": old["server_runs"], "server": rates(old["server_runs"], case),
               "sim": rates(sim_runs(case, runs, budget), case)}
        row["compare"] = compare(row["server"], row["sim"])
        rows.append(row)
        report(case, row)
    out = path.resolve().with_name(path.stem + "-resim.json")
    out.write_text(json.dumps({"args": {"resim": str(path), "sim_runs": runs, "budget": budget}, "cases": rows},
                              indent=1))
    print(f"saved {out.relative_to(REPO)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--bands", type=int, nargs="+", default=[1, 31, 61, 91])
    parser.add_argument("--classes", nargs="+", default=["melee", "ranged"])
    parser.add_argument("--slot", type=int, default=0, help="the ranker's slot: 0 the top by XP, 3 the top by gp")
    parser.add_argument("--loot", choices=LOOT_MODES, default="none", help="the loot mode (with --cases-from too)")
    parser.add_argument("--style", choices=("accurate", "ranked"), default="ranked",
                        help="fight ranged cases in the style the ranker chose (Caleb, 2026-11-07), or accurate")
    parser.add_argument("--cases-from", type=Path, help="rerun the cases of an earlier results file instead")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--sim-runs", type=int, default=200)
    parser.add_argument("--budget", type=int, default=1500, help="ticks per run at most (D: 15 game-minutes)")
    parser.add_argument("--tick-ms", type=int, default=50)
    parser.add_argument("--resim", type=Path, help="no server: compare an earlier file's server runs with the sim now")
    args = parser.parse_args()
    if args.resim is not None:
        resimulate(args.resim, args.sim_runs, args.budget)
        return
    rows = []
    with BridgeClient(timeout=900) as client:
        old_ms = client.ping()["tick_ms"]
        client.set_tick_ms(args.tick_ms)
        try:
            chosen = cases(args.bands, args.classes, args.slot, args.loot,
                           args.style == "ranked") if args.cases_from is None else [
                Case(**{**row["case"], "site": tuple(row["case"]["site"]), "loot": args.loot})
                for row in json.loads(args.cases_from.read_text())["cases"]]
            for case in chosen:
                server = [server_run(client, case, args.budget) for _ in range(args.runs)]
                sim = sim_runs(case, args.sim_runs, args.budget)
                row = {"case": asdict(case), "server_runs": server, "server": rates(server, case),
                       "sim": rates(sim, case)}
                row["compare"] = compare(row["server"], row["sim"])
                rows.append(row)
                report(case, row)
        finally:
            client.set_tick_ms(old_ms)
    name = (f"combat-{datetime.now():%Y%m%d-%H%M}{run_suffix(args.tick_ms)}"  # the slot and loot: runs sharing a server
            + (f"-slot{args.slot}" if args.slot else "") + (f"-{args.loot}" if args.loot != "none" else "")
            + ("-accurate" if args.style == "accurate" and "ranged" in args.classes else ""))
    out = REPO / "results" / "calibration" / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": {**vars(args), "cases_from": str(args.cases_from or "")}, "cases": rows},
                              indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
