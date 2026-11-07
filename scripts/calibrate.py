"""Calibration against the server (ROADMAP week 2; env contract §7): run an option's activity on the live server and
in the sim from the same start, and compare the rates against the ±20% gate.

First slice: gathering at the site, for woodcutting. Travel and banking come later: the bridge's walk_to only walks
straight lines (ScriptAPI.walkTo), so long walks need a waypoint walker first, and banking needs the bank commands
of OQ-4. So each run starts at the option's site and measures the activity alone, until the inventory is full:
the skilling formulas, the trees' depletion and respawn, and the site's tile and tree count, which the sim estimated.

A run, per env contract §7:
- a calibration character of the band: a fresh character, with the trainable skills (§5) set to the band's level
  for the bands above fresh (debug_set_levels, setup only);
- the best standard tool the band's level can use (debug_give, setup only). The contract has non-fresh characters
  buy their gear on the GE with 100 gp x total level, which buys every tool they can use; giving it skips the GE
  trip, which this slice doesn't measure. A fresh character keeps the starter bronze axe;
- debug_teleport to the sim's site tile (setup only), then the activity through client packets, as a person
  plays: click the nearest tree, and click again whenever the character is idle (no active script and not
  walking), until the inventory is full or the budget runs out. interact clicks the tree the character can walk to
  soonest. Auto-retaliate is off (Caleb: no fights on a gathering task unless trivial), so an aggressive monster's
  attacks don't stop the chopping. Busy for STUCK_TICKS without a swing, the character walks back to the site's tile
  with a walk click, which clears whatever held it, and clicks again. Still to come from Caleb's rule: trivial
  fights, and running out of the monster's aggressive range when hitpoints are under twice its max hit.
The sim runs its option from the same state at the site, many times.

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/calibrate.py [--bands 1 31 61 91] [--runs 3] [--sim-runs 200] [--tick-ms 50]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from rlscape.bridge.client import BridgeClient, run_suffix
from rlscape.combat import formulas as f
from rlscape.combat.prayers import flicks
from rlscape.combat.rates import npc_max_hit
from rlscape.gamedata import server as gd
from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL
from rlscape.sim.state import CharacterState
from rlscape.sim.fishing import fishing_options
from rlscape.sim.mining import PICKAXE_PRIORITY, mining_options
from rlscape.sim.woodcutting import HATCHET_PRIORITY, woodcutting_options

REPO = Path(__file__).resolve().parents[1]
BANDS = (1, 11, 21, 31, 41, 51, 61, 71, 81, 91, 99)  # env contract §7; 1 is "fresh"
TRAINABLE = ("attack", "strength", "defence", "hitpoints", "ranged", "magic", "prayer", "woodcutting", "mining",
             "smithing", "fishing", "cooking", "firemaking", "thieving", "fletching", "crafting", "agility",
             "herblore", "runecrafting")  # env contract §5
STANDARD_HATCHETS = tuple(h for h in HATCHET_PRIORITY if h != "DRAGON_AXE")  # not sold on the GE in January 2009
STANDARD_PICKAXES = tuple(h for h in PICKAXE_PRIORITY if h.endswith("_PICKAXE") and h != "DRAGON_PICKAXE")
TREE_NAMES = {1: "Tree", 7: "Oak", 8: "Willow", 15: "Yew"}  # WoodcuttingNode identifier -> the scenery's name
GATE = 0.2
TICKS_PER_HOUR = 6000
STUCK_TICKS = 20  # busy without a swing this long: something holds the character
AGGRESSION_RADIUS = 4  # AggressiveHandler's default radius: farther than this, a monster doesn't pick the character
FLEE_TILES = 10  # how far a walk click away from a monster aims
SAFESPOT_RADIUS = 10  # a safespot is a gathering tile at the site: resources this far from the character


@dataclass(frozen=True)
class Case:
    option_id: str
    band: int
    tool: int | None  # given at setup; None keeps the starter kit's
    site: tuple[int, int, int]
    target: str
    action: str
    product: int
    skill: str
    rest: int  # ticks to wait before a run, so the trees an earlier run felled are back
    levels: tuple[tuple[str, int], ...] = ()  # set instead of the band's (e.g. woodcutting alone, as an agent might)
    ids: tuple[int, ...] = ()  # the target's scenery or NPC ids, where several kinds sit together
    roll: str = "skilling"  # what moves on with each attempt: the skilling clock, or (mining) the script's next run
    is_object: bool = True  # scenery; a fishing spot is an NPC
    extras: tuple[tuple[int, int], ...] = ()  # (item, amount) given at setup besides the tool: bait
    drop_kit: bool = False  # start with an empty inventory (no starter kit), so a load takes long enough to see more


def woodcutting_cases(bands: list[int], levels: dict[str, int] | None = None) -> list[Case]:
    """A case per tree and band; with `levels`, one per tree those levels allow, at those levels instead."""
    tools, cases = gd.skilling_tools(), []
    for option in woodcutting_options():
        for band in ([levels.get("woodcutting", 1)] if levels else bands):
            if band < option.tree.level:
                continue
            best = next(tools[h] for h in STANDARD_HATCHETS if tools[h].level <= band)
            tool = None if band == 1 else best.item
            cases.append(Case(option.id, band, tool, option.site.tile, TREE_NAMES[option.tree.identifier],
                              "Chop down", option.tree.reward, "woodcutting", option.tree.respawn_max,
                              tuple(sorted(levels.items())) if levels else ()))
    return cases


def mining_cases(bands: list[int], levels: dict[str, int] | None = None) -> list[Case]:
    """A case per rock and band, as woodcutting_cases. Mining rolls when its own delayed script runs (every 5
    ticks), not on the skilling clock."""
    tools, cases = gd.skilling_tools(), []
    for option in mining_options():
        for band in ([levels.get("mining", 1)] if levels else bands):
            if band < option.rock.level:
                continue
            best = next(tools[h] for h in STANDARD_PICKAXES if tools[h].level <= band)
            tool = None if band == 1 else best.item
            cases.append(Case(option.id, band, tool, option.site.tile, "Rocks", "Mine", option.rock.reward, "mining",
                              option.rock.respawn_max, tuple(sorted(levels.items())) if levels else (),
                              tuple(sorted(gd.rock_objects()[option.rock.identifier])), "script_next"))
    return cases


FISHING_ACTIONS = {"SMALL_NET": "net", "LURE": "lure", "LOBSTER_CAGE": "cage"}  # FishingOption's option names


def land_tile(client: BridgeClient, spot: tuple[int, int, int]) -> tuple[int, int, int]:
    """The shore tile beside a fishing spot's tile (the sim's start is the spot's, in the water): the first of its
    four neighbours that a character put on the spot can walk onto. A walk can leave the water but not enter it, and a
    teleport can't tell, so each one is walked to."""
    uid = client.spawn()["uid"]
    try:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tile = (spot[0] + dx, spot[1] + dy, spot[2])
            client.debug_teleport(uid, *spot)
            client.wait(2)
            client.walk_to(uid, *tile, packet=True)
            client.wait(4)
            loc = client.state(uid)["location"]
            if (loc["x"], loc["y"], loc["z"]) == tile:
                return tile
    finally:
        client.despawn(uid)
    raise RuntimeError(f"no shore tile beside {spot}")


def fishing_cases(client: BridgeClient, bands: list[int], levels: dict[str, int] | None = None,
                  options: list[str] | None = None) -> list[Case]:
    """A case per fishing method and band, standing on the shore by the option's first spot (the sim walks to the
    spot itself), clicking spots of the method's kind (FishingSpot's NPC ids). XP is what's compared: a method catches
    several fish; `product` counts the first. The starter kit is dropped, so a load of 26 or 27 fish takes long enough
    for the spot to move (every 200 to 390 ticks) once or twice, as it will in training."""
    cases = []
    for option in fishing_options():
        if options and option.id not in options:
            continue
        method, ids = option.method, sorted(gd.fishing_spot_ids()[option.method.name])
        site = land_tile(client, option.start)
        for band in ([levels.get("fishing", 1)] if levels else bands):
            if band < method.level:
                continue
            extras = tuple((bait, 1000) for bait in method.bait[:1])  # feathers, not the stripy ones
            cases.append(Case(option.id, band, method.tool, site, "Fishing spot", FISHING_ACTIONS[method.name],
                              gd.fish_types()[method.fish[0]].item, "fishing", 0,
                              tuple(sorted(levels.items())) if levels else (), tuple(ids), "skilling", False, extras,
                              drop_kit=True))
    return cases


def setup_levels(case: Case) -> dict[str, int]:
    return dict(case.levels) if case.levels else {skill: case.band for skill in TRAINABLE} if case.band > 1 else {}


def level(state: dict[str, Any], skill: str) -> int:
    return next(s["level"] for s in state["skills"] if s["name"].lower() == skill)


def setup_max_hit(state: dict[str, Any]) -> int:
    """The character's melee max hit as it stands (accurate style, its worn strength bonus, the strength prayer a
    fight flicks): what Caleb's trivial-fight rule compares with half the monster's hitpoints."""
    items = gd.items()
    bonus = sum(items[i["id"]].bonuses[gd.MELEE_STRENGTH] for i in state["equipment"] if i["id"] in items)
    prayer = flicks(level(state, "prayer"), level(state, "defence")).strength
    return f.player_melee_max_hit(level(state, "strength"), f.ACCURATE, bonus, prayer)


class Safety:
    """Caleb's rule for an aggressive monster on a gathering task (decision log, 2026-10-31), a tick at a time:
    - auto-retaliate is off, so an attack doesn't stop the gathering;
    - fight it only if that's trivial: the setup's max hit is at least half its hitpoints and its max hit is under a
      quarter of the character's hitpoints as the fight starts (attacked by index, then back to gathering);
    - dangerous when hitpoints are under twice the attackers' max hit: walk away until nothing attacks and the
      character is beyond the monster's aggressive range, eat (or wait) until it's no longer dangerous, walk back;
    - otherwise, safespot it: gather from a tile beside the resource that the attacker can't hit the character on
      and no other aggressive melee monster can either (the bridge's safespots), within SAFESPOT_RADIUS."""

    def __init__(self, client: BridgeClient, uid: int, case: Case):
        self.client, self.uid, self.case, self.site, self.mode = client, uid, case, case.site, "gather"
        self.threat: tuple[int, int] | None = None
        self.threat_max = 0
        self.safe_from: set[int] = set()  # attackers (by index) asked about in their current attack
        self.spot: tuple[int, int] | None = None
        self.counts = {"flees": 0, "fights": 0, "eaten": 0, "eat_clicks": 0, "ticks_away": 0, "safespots": 0,
                       "no_safespot": 0}
        self.food: int | None = None  # food carried at the last reading

    def _safespot(self, attacker: dict[str, Any], here: tuple[int, int]) -> list[dict[str, Any]] | None:
        """Caleb: "try to safespot the monster and return to gathering". A tile beside the resource the attacker can't
        hit the character on (the bridge's safespots, melee attackers only); None if there's none."""
        monster = gd.npcs().get(attacker["id"])
        if attacker["index"] in self.safe_from or monster is None or monster.combat_style != "melee":
            return None  # a caster or an archer hits from range: no tile beside the resource is safe from it
        tiles = self.client.safespots(self.uid, self.case.target, list(self.case.ids) or None, SAFESPOT_RADIUS,
                                      self.case.is_object)
        if not tiles:
            self.counts["no_safespot"] += 1
            self.safe_from.add(attacker["index"])  # don't ask again for this one
            return None
        self.safe_from.add(attacker["index"])
        tile = tiles[0]["tile"]
        self.spot, self.mode = (tile["x"], tile["y"]), "safespot"
        self.counts["safespots"] += 1
        if self.spot == here:
            self.mode = "gather"
            return None
        return [{"cmd": "walk_to", "uid": self.uid, "x": tile["x"], "y": tile["y"], "packet": True}]

    def _away(self, here: tuple[int, int]) -> dict[str, Any]:
        dx, dy = here[0] - self.threat[0], here[1] - self.threat[1]
        norm = max((dx * dx + dy * dy) ** 0.5, 1e-9)
        if norm < 0.5:
            dx, dy, norm = 1, 0, 1.0
        x, y = round(here[0] + dx / norm * FLEE_TILES), round(here[1] + dy / norm * FLEE_TILES)
        return {"cmd": "walk_to", "uid": self.uid, "x": x, "y": y, "packet": True}

    def step(self, state: dict[str, Any]) -> list[dict[str, Any]] | None:
        """This tick's commands, or None to go on gathering."""
        # food eaten is what the inventory loses, not the clicks: a bite lands a tick after its click
        heals = gd.food_healing()
        now = sum(i["amount"] for i in state["inventory"] if i["id"] in heals)
        self.counts["eaten"] += max((self.food if self.food is not None else now) - now, 0)
        self.food = now
        loc = state["location"]
        here, hp, attackers = (loc["x"], loc["y"]), state["hitpoints"], state["attackers"]
        npcs = gd.npcs()
        self.safe_from &= {a["index"] for a in attackers}  # one that stopped attacking may be asked about again
        if attackers:
            worst = max(attackers, key=lambda a: npc_max_hit(npcs[a["id"]]) if a["id"] in npcs else 0)
            self.threat_max = npc_max_hit(npcs[worst["id"]]) if worst["id"] in npcs else 0
            self.threat = (worst["location"]["x"], worst["location"]["y"])
        if self.mode != "gather":
            self.counts["ticks_away"] += 1
        self.counts[f"ticks_{self.mode}"] = self.counts.get(f"ticks_{self.mode}", 0) + 1
        if self.mode == "gather":
            if not attackers:
                return None
            if hp < 2 * self.threat_max:
                self.mode = "flee"
                self.counts["flees"] += 1
                return [self._away(here)]
            monster = npcs.get(worst["id"])
            if monster and setup_max_hit(state) >= monster.hitpoints / 2 and self.threat_max < 0.25 * hp:
                self.mode = "fight"
                self.counts["fights"] += 1
                return [{"cmd": "interact", "uid": self.uid, "name": worst["name"], "option": "Attack",
                         "object": False, "index": worst["index"], "packet": True}]
            return self._safespot(worst, here)
        if self.mode == "safespot":  # walking to it; then gather from there
            if not state["moving"]:
                self.mode = "gather"
                return None
            return []
        if self.mode == "fight":
            if not attackers and state["target"] is None:
                self.mode = "gather"
                return None
            return []
        if self.mode == "flee":
            far = self.threat is None or max(abs(here[0] - self.threat[0]), abs(here[1] - self.threat[1])) > AGGRESSION_RADIUS
            if not attackers and far:
                self.mode = "heal"
            elif not state["moving"]:
                return [self._away(here)]
            return []
        if self.mode == "heal":
            if attackers:
                self.mode = "flee"
                return [self._away(here)]
            if hp >= 2 * self.threat_max:
                self.mode = "return"
                return [{"cmd": "walk_to", "uid": self.uid, "x": self.site[0], "y": self.site[1], "packet": True}]
            food = next((i["id"] for i in state["inventory"] if i["id"] in gd.food_healing()), None)
            if food is not None:
                self.counts["eat_clicks"] += 1
                return [{"cmd": "item_option", "uid": self.uid, "item": food, "option": "Eat", "packet": True}]
            return []  # no food: wait for hitpoints to come back
        # returning
        if attackers and hp < 2 * self.threat_max:
            self.mode = "flee"
            self.counts["flees"] += 1
            return [self._away(here)]
        if not state["moving"]:
            if max(abs(here[0] - self.site[0]), abs(here[1] - self.site[1])) <= 2:
                self.mode = "gather"
                return None
            return [{"cmd": "walk_to", "uid": self.uid, "x": self.site[0], "y": self.site[1], "packet": True}]
        return []


def held(state: dict[str, Any], item: int) -> int:
    return sum(s["amount"] for s in state["inventory"] if s["id"] == item)


def xp(state: dict[str, Any], skill: str) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == skill)


def server_run(client: BridgeClient, case: Case, budget: int) -> dict[str, Any]:
    """One run on the server. Each round is one tick: a `schedule` step that sends the click decided from the last
    reading (handled in the next tick's packet phase, as a client's), then reads the state and the skilling clock. So
    the character is clicked again within two ticks of going idle, as a person would."""
    client.wait(case.rest)  # the sim's runs all start with every tree standing
    uid = client.spawn()["uid"]
    try:
        if setup_levels(case):
            client.debug_set_levels(uid, setup_levels(case))
        if case.drop_kit:
            for item in {i["id"] for i in client.state(uid)["inventory"]}:
                client.item_option(uid, item, "Drop")
            client.wait(2)  # the last drops land a tick later
            assert not client.state(uid)["inventory"], "the starter kit didn't all drop"
        if case.tool is not None:
            client.debug_give(uid, case.tool, 1)
        for item, amount in case.extras:
            client.debug_give(uid, item, amount)
        client.set_retaliate(uid, False)  # Caleb: no fights on a gathering task unless trivial
        safety = Safety(client, uid, case)
        client.debug_teleport(uid, *case.site)
        client.wait(3)
        click = {"cmd": "interact", "uid": uid, "name": case.target, "option": case.action, "object": case.is_object,
                 "packet": True, **({"ids": list(case.ids)} if case.ids else {})}
        pending, clicks, waiting, trace, first, trees, stands = [click], 0, 0, [], None, set(), set()
        prev_hp = 0
        back = {"cmd": "walk_to", "uid": uid, "x": case.site[0], "y": case.site[1], "z": case.site[2], "packet": True}
        last_swing, walked_back, hits, lost, died = 0, 0, 0, 0, False
        hits_by_mode: dict[str, int] = {}
        while True:
            step = client.schedule([[*pending, {"cmd": "state", "uid": uid}, {"cmd": "debug_clocks", "uid": uid}]])[0]
            results = step["results"]
            if pending and pending[0] is click:
                if results[0].get("ok"):
                    clicks += 1
                    trees.add(tuple(results[0]["target"].values()))
                else:  # none standing in reach: wait for a respawn, as a person would
                    waiting += 1
            state, clocks = results[-2]["state"], results[-1]
            if first is not None and state["hitpoints"] < prev_hp:
                hits, lost = hits + 1, lost + prev_hp - state["hitpoints"]
                hits_by_mode[safety.mode] = hits_by_mode.get(safety.mode, 0) + 1  # the mode it was hit in
            prev_hp = state["hitpoints"]
            first = first or (step["tick"], state)
            offset = step["tick"] - first[0]
            idle = clocks["script_next"] is None and not state["moving"]
            if trace and clocks[case.roll] is not None and clocks[case.roll] != trace[-1][2]:
                last_swing = offset
            trace.append([offset, held(state, case.product), clocks[case.roll] or trace[-1][2] if trace else
                          clocks[case.roll], int(idle), state["hitpoints"], safety.mode, len(state["attackers"])])
            if not idle and not state["moving"]:
                stands.add(tuple(state["location"].values()))
            full = len(state["inventory"]) >= 28
            died = state["hitpoints"] == 0  # the run ends there, as the sim's option does
            if full or died or offset >= budget:
                break
            action = safety.step(state)
            if action is not None:  # the rule has the character fleeing, healing, returning or fighting
                pending, last_swing = action, offset
                continue
            pending = [click] if idle else []
            if not idle and offset - last_swing > STUCK_TICKS:
                pending, last_swing, walked_back = [back], offset, walked_back + 1
    finally:
        client.despawn(uid)
    return {"ticks": offset, "xp": xp(state, case.skill) - xp(first[1], case.skill),
            "items": held(state, case.product) - held(first[1], case.product), "full": full, "clicks": clicks,
            "ticks_waiting_for_a_tree": waiting, "walked_back": walked_back, "hits": hits, "hitpoints_lost": lost,
            "hits_by_mode": hits_by_mode, "died": died,
            **safety.counts, "trees_clicked": sorted(trees), "chopping_from": sorted(stands),
            **overheads(trace), "trace": trace}


def overheads(trace: list[list[int]]) -> dict[str, Any]:
    """From a run's trace (rows: tick, product held, roll marker, idle, hitpoints, the rule's mode, attackers): the
    swings (the skilling clock moving on), the gap after a swing that got a log and after
    one that didn't, the ticks from the start to the first swing, and from each tree falling (the character going
    idle) to the next swing."""
    swings = [i for i in range(1, len(trace)) if trace[i][2] != trace[i - 1][2]]
    got = {i for i in swings if trace[i][1] > trace[i - 1][1]}
    after_log = [b - a for a, b in zip(swings, swings[1:]) if a in got and not any(trace[k][3] for k in range(a, b))]
    after_miss = [b - a for a, b in zip(swings, swings[1:]) if a not in got and not any(trace[k][3] for k in range(a, b))]
    falls = [i for i in range(1, len(trace)) if trace[i][3] and not trace[i - 1][3]]
    retarget = [next(s for s in swings if s > i) - i for i in falls if any(s > i for s in swings)]
    return {"swings": len(swings), "gap_after_log": after_log, "gap_after_miss": after_miss,
            "first_swing": swings[0] if swings else None, "idle_to_next_swing": retarget}


def sim_runs(case: Case, runs: int, budget: int) -> list[dict[str, Any]]:
    option = next(o for o in (*woodcutting_options(), *mining_options(), *fishing_options()) if o.id == case.option_id)
    out = []
    for seed in range(runs):
        state = CharacterState.fresh()
        if case.drop_kit:
            state.inventory.clear()
        for skill, lv in setup_levels(case).items():
            state.xp[SKILL_INDEX[skill]] = float(XP_FOR_LEVEL[lv])
        if case.tool is not None:
            state.add(case.tool)
        for item, amount in case.extras:
            state.add(item, amount)
        state.location = case.site
        before_xp, before_items = state.xp[SKILL_INDEX[case.skill]], state.inventory.get(case.product, 0)
        result = option.run(state, np.random.default_rng(seed), budget)
        out.append({"ticks": result.ticks, "xp": state.xp[SKILL_INDEX[case.skill]] - before_xp,
                    "items": state.inventory.get(case.product, 0) - before_items,
                    "full": result.termination == "inventory_full", "died": result.termination == "died"})
    return out


def rates(runs: list[dict[str, Any]]) -> dict[str, float]:
    ticks = sum(r["ticks"] for r in runs)
    return {"xp_per_hour": sum(r["xp"] for r in runs) * TICKS_PER_HOUR / ticks,
            "items_per_hour": sum(r["items"] for r in runs) * TICKS_PER_HOUR / ticks,
            "ticks_to_full": float(np.mean([r["ticks"] for r in runs])), "runs": len(runs),
            "all_full": all(r["full"] for r in runs), "deaths": sum(r["died"] for r in runs) / len(runs)}


def compare(server: dict[str, float], sim: dict[str, float]) -> dict[str, Any]:
    out = {}
    for key in ("xp_per_hour", "items_per_hour", "ticks_to_full"):
        ratio = sim[key] / server[key] if server[key] else float("inf")
        out[key] = {"server": round(server[key], 1), "sim": round(sim[key], 1), "sim_over_server": round(ratio, 3),
                    "within_gate": abs(ratio - 1) <= GATE}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--bands", type=int, nargs="+", default=[1, 31, 61, 91])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--sim-runs", type=int, default=200)
    parser.add_argument("--budget", type=int, default=3000, help="ticks per run at most")
    parser.add_argument("--tick-ms", type=int, default=50)
    parser.add_argument("--options", nargs="*", help="option ids to calibrate (default: all)")
    parser.add_argument("--levels", nargs="*", default=[], help="skill=level pairs set instead of the bands' levels")
    args = parser.parse_args()
    levels = {k: int(v) for k, v in (pair.split("=") for pair in args.levels)} or None
    assert all(b in BANDS for b in args.bands), f"bands are {BANDS}"
    results = []
    with BridgeClient(timeout=600) as client:
        old_ms = client.ping()["tick_ms"]
        client.set_tick_ms(args.tick_ms)
        try:
            fishing = [o.id for o in fishing_options()]
            wanted_fishing = [o for o in (args.options or fishing) if o in fishing]
            for case in (*woodcutting_cases(args.bands, levels), *mining_cases(args.bands, levels),
                         *(fishing_cases(client, args.bands, levels, wanted_fishing) if wanted_fishing else [])):
                if args.options and case.option_id not in args.options:
                    continue
                server = [server_run(client, case, args.budget) for _ in range(args.runs)]
                sim = sim_runs(case, args.sim_runs, args.budget)
                row = {"case": asdict(case), "server_runs": server, "server": rates(server), "sim": rates(sim)}
                row["compare"] = compare(row["server"], row["sim"])
                results.append(row)
                c = row["compare"]
                print(f"{case.option_id:10s} band {case.band:2d}  xp/h server {c['xp_per_hour']['server']:8.0f} "
                      f"sim {c['xp_per_hour']['sim']:8.0f} ({c['xp_per_hour']['sim_over_server']:.2f})  "
                      f"ticks to full server {c['ticks_to_full']['server']:6.0f} sim {c['ticks_to_full']['sim']:6.0f}"
                      f"  full {row['server']['all_full']}  clicks {[r['clicks'] for r in server]}  "
                      f"hits {[r['hits'] for r in server]} flees {[r['flees'] for r in server]} "
                      f"fights {[r['fights'] for r in server]}  deaths a run server {row['server']['deaths']:.2f} "
                      f"sim {row['sim']['deaths']:.2f}")
        finally:
            client.set_tick_ms(old_ms)
    out = REPO / "results" / "calibration" / f"gathering-{datetime.now():%Y%m%d-%H%M}{run_suffix(args.tick_ms)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(args), "cases": results}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
