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
character has no target and isn't walking, click "Attack" on the nearest monster of the case's id; eat when
hitpoints are at or under half (the sim's rule, rlscape.sim.health); click again only after IDLE_TICKS idle, as a
person waits for the walk to start; stop when there's no food left to eat then
(the sim retreats), at death, or when the budget runs out. Busy STUCK_TICKS without XP, it walks back to the spawn.
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
from rlscape.combat.candidates import LOOT_MODES, enemy_pool, loot_rule
from rlscape.combat.rates import HP_XP_PER_DAMAGE, Plan, combat_rates
from rlscape.gamedata import server as gd
from rlscape.sim.combat import fight
from rlscape.sim.equipment import fighter_for, wield_best
from rlscape.sim.health import retreat_hp
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.slots import CombatSlots
from rlscape.sim.state import SPAWN, CharacterState
from rlscape.vocabulary import vocabulary

REPO = Path(__file__).resolve().parents[1]
GATE = 0.2
TICKS_PER_HOUR = 6000
STUCK_TICKS = 30  # a target and no XP this long: something holds the character
TAKE_IDLE_TICKS = 2  # still this long before taking the next drop: the walk to it starts a tick after the click
DROP_WAIT_TICKS = 6  # after a kill, waiting for the drop: DeathTask's default death animation
LOOT_RADIUS = 15  # tiles: the drops a person looting sees and goes for
INVENTORY_SLOTS = 28
IDLE_TICKS = 3  # idle this long before clicking again: a click on a monster a few tiles off takes a tick or two to
# start the walk, and clicking again meanwhile restarts it (a person clicks once and waits)
COMBAT = ("attack", "strength", "defence", "hitpoints", "ranged")
TROUT, LOBSTER = 333, 379
FOOD_MARGIN, MAX_FOOD = 2, 15  # food beyond the expected damage's, and at most
# The band's standard gear (no quest items: no dragon weapons, no rune platebody or green d'hide body)
MELEE = {31: (1331, 1161, 1111, 1073, 1199),  # adamant scimitar, full helm, chainbody, platelegs, kiteshield
         61: (1333, 1163, 1113, 1079, 1201), 91: (1333, 1163, 1113, 1079, 1201)}  # rune
MELEE[1] = (1277, 1171)  # the starter kit's bronze sword and wooden shield
RANGED = {1: ((841, 1), (882, 500)),  # the starter kit's shortbow, and its bronze arrows made 500
          31: ((853, 1), (890, 500), (1169, 1), (1129, 1), (1095, 1)),  # maple shortbow, adamant arrows, coif, leather
          61: ((861, 1), (892, 500), (1169, 1), (1129, 1), (1099, 1)),  # magic shortbow, rune arrows, coif, leather
          91: ((861, 1), (892, 500), (1169, 1), (1129, 1), (1099, 1))}  # body, green d'hide chaps
FOOD = {1: TROUT}  # above band 1: lobsters


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

    @property
    def plan(self) -> Plan:
        return Plan(self.combat_class, "accurate")


def gear(case_class: str, band: int) -> tuple[tuple[int, int], ...]:
    if case_class == "melee":
        return tuple((item, 1) for item in MELEE.get(band, ()))
    return RANGED[band]


def food_item(band: int) -> int:
    return FOOD.get(band, LOBSTER)


def character(combat_class: str, band: int, food: int = MAX_FOOD) -> CharacterState:
    """The calibration character in the sim, before its fight wields anything: the band's levels and Prayer, its gear
    and `food` of the band's food, and no starter kit."""
    state = CharacterState.fresh()
    state.inventory.clear()
    if band > 1:
        for skill in (*COMBAT, "prayer"):
            state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[band])
        state.hp = state.max_hp()
    for item, amount in gear(combat_class, band):
        state.add(item, amount)
    if food:
        state.add(food_item(band), food)
    return state


def food_for(case: "Case", budget: int) -> int:
    """The food a fight of `budget` ticks needs: the sim's expected damage over it (prayers flicked as the fight
    flicks them, so none from a monster whose one style they cover), less the hitpoints above the retreat point,
    in the band's food, plus FOOD_MARGIN; at most MAX_FOOD."""
    state = character(case.combat_class, case.band, food=0)
    wield_best(state, case.combat_class)
    npc = gd.npcs()[case.npc]
    rates = combat_rates(fighter_for(state), case.plan, npc, 0.0)
    if rates is None:
        return MAX_FOOD
    damage = rates.damage_taken_per_hour * budget / TICKS_PER_HOUR - (state.hp - retreat_hp(state))
    heal = gd.food_healing()[food_item(case.band)]
    return min(max(ceil(damage / heal), 0) + FOOD_MARGIN, MAX_FOOD)


def cases(bands: list[int], classes: list[str], slot: int = 0, loot: str = "none") -> list[Case]:
    """The sim ranker's slot (0: the top by XP) for each band and class, the character at Lumbridge, ranking with
    the loot mode (without looting, with the fresh character's, as the fit set was chosen)."""
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
            out.append(Case(combat_class, band, npc.id, npc.name, candidate.site.spawn, npc.hitpoints, slot, loot))
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


def setup(client: BridgeClient, case: Case, budget: int) -> int:
    uid = client.spawn()["uid"]
    if case.band > 1:
        client.debug_set_levels(uid, {skill: case.band for skill in (*COMBAT, "prayer")})
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
    client.set_retaliate(uid, True)
    client.flick(uid)  # protection prayers, as the sim's fights flick them (none below their levels)
    client.debug_teleport(uid, *case.site)
    client.wait(3)
    return uid


def server_run(client: BridgeClient, case: Case, budget: int) -> dict[str, Any]:
    """One run on the server, a tick at a time (a `schedule` step sends the click decided from the last reading)."""
    uid = setup(client, case, budget)
    try:
        attack = {"cmd": "interact", "uid": uid, "name": case.name, "option": "Attack", "object": False,
                  "ids": [case.npc], "packet": True}
        back = {"cmd": "walk_to", "uid": uid, "x": case.site[0], "y": case.site[1], "z": case.site[2], "packet": True}
        looting, keep, stackable = case.loot != "none", loot_rule(case.loot, VOCABULARY), gd.stackable_items()
        fills = looting and fills_inventory(case)
        ammo = {i["id"] for i in client.state(uid)["equipment"] if i["id"] in stackable}
        pending, first, prev_hp, prev_xp, last_gain, idle, still = [attack], None, 0, 0.0, 0, 0, 0
        mine: set[tuple[int, int, int]] = set()  # its drops (id, x, y), still its own once they turn public
        fighting, ended_at, dropped_at = False, -DROP_WAIT_TICKS, -1
        counts = {"clicks": 0, "no_target": 0, "eaten": 0, "eat_clicks": 0, "hits_taken": 0, "damage_taken": 0,
                  "walked_back": 0, "taken": 0}
        food = None  # food carried at the last reading
        ended = "completed"
        while True:
            reads = [{"cmd": "state", "uid": uid}, {"cmd": "ground_items", "uid": uid, "radius": LOOT_RADIUS}]
            step = client.schedule([[*pending, *reads]])[0]
            results, state, ground = step["results"], step["results"][-2]["state"], step["results"][-1]["items"]
            if pending and pending[0] is attack:
                counts["clicks" if results[0].get("ok") else "no_target"] += 1
            first = first or (step["tick"], state)
            offset = step["tick"] - first[0]
            for item in ground:
                key = (item["id"], item["location"]["x"], item["location"]["y"])
                if item["own"] and key not in mine:
                    mine.add(key)
                    dropped_at = offset
            if state["target"] is not None:
                fighting = True
            elif fighting:  # the target is gone: killed, most likely
                fighting, ended_at = False, offset
            hp, gained = state["hitpoints"], sum(xp(state, s) for s in COMBAT)
            now = food_count(state)
            counts["eaten"] += max((food if food is not None else now) - now, 0)  # food looted only adds
            food = now
            if offset and hp < prev_hp:
                counts["hits_taken"] += 1
                counts["damage_taken"] += prev_hp - hp
            if gained > prev_xp:
                last_gain = offset
            prev_hp, prev_xp = hp, gained
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
            waiting = looting and offset - ended_at < DROP_WAIT_TICKS and dropped_at < ended_at
            pending = []
            if state["target"] is not None or state["moving"] or state["attackers"]:
                idle = 0
            still = 0 if state["moving"] else still + 1
            max_hp = next(s["level"] for s in state["skills"] if s["name"].lower() == "hitpoints")
            if hp <= max_hp // 2:  # the sim's rule: eat at or under half (retreat_hp)
                held = food_held(state)
                if not held:
                    ended = "out_of_food"
                    break
                pending = [{"cmd": "item_option", "uid": uid, "item": held[0], "option": "Eat", "packet": True}]
                counts["eat_clicks"] += 1
            elif loot and still >= TAKE_IDLE_TICKS:
                # loot first, attacked or not (Caleb, 2026-11-07), as the sim picks up after each kill before the next:
                # the runner starts no fight with its loot on the ground, so a target now is one it retaliated on
                item = loot[0]
                pending, idle, still = [{"cmd": "take", "uid": uid, "item": item["id"], "x": item["location"]["x"],
                                         "y": item["location"]["y"], "packet": True}], 0, 0
                counts["taken"] += 1
            elif state["target"] is None and not state["moving"] and not state["attackers"]:
                idle += 1
                if not loot and not waiting and idle >= IDLE_TICKS:
                    pending, idle = [attack], 0
            elif offset - last_gain > STUCK_TICKS:
                pending, last_gain = [back], offset
                counts["walked_back"] += 1
    finally:
        client.despawn(uid)
    out = {"ticks": offset, "ended": ended, **counts, "loot_gp": loot_gp(holding(first[1]), holding(state), ammo)}
    for skill in COMBAT:
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
        before = {skill: state.xp[SKILL_INDEX[skill]] for skill in COMBAT}
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
                    **{f"xp_{s}": state.xp[SKILL_INDEX[s]] - before[s] for s in COMBAT},
                    "hp_change": state.hp - hp_before, "loot_gp": loot_gp(held, state.inventory, ammo)})
    return out


def rates(runs: list[dict[str, Any]], case: Case) -> dict[str, float]:
    ticks = sum(r["ticks"] for r in runs)
    hp_xp = sum(r["xp_hitpoints"] for r in runs)
    combat_xp = sum(sum(r[f"xp_{s}"] for s in COMBAT) for r in runs)
    return {"xp_per_hour": combat_xp * TICKS_PER_HOUR / ticks,
            "kills_per_hour": hp_xp / (HP_XP_PER_DAMAGE * case.hitpoints) * TICKS_PER_HOUR / ticks,
            "food_per_hour": sum(r["eaten"] for r in runs) * TICKS_PER_HOUR / ticks,
            "gp_per_hour": sum(r.get("loot_gp", 0.0) for r in runs) * TICKS_PER_HOUR / ticks,
            "ticks": float(np.mean([r["ticks"] for r in runs])), "runs": len(runs),
            "ended": {e: sum(r["ended"] == e for r in runs) / len(runs) for e in {r["ended"] for r in runs}},
            "xp_by_skill": {s: sum(r[f"xp_{s}"] for r in runs) * TICKS_PER_HOUR / ticks for s in COMBAT}}


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
            chosen = cases(args.bands, args.classes, args.slot, args.loot) if args.cases_from is None else [
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
            + (f"-slot{args.slot}" if args.slot else "") + (f"-{args.loot}" if args.loot != "none" else ""))
    out = REPO / "results" / "calibration" / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": {**vars(args), "cases_from": str(args.cases_from or "")}, "cases": rows},
                              indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
