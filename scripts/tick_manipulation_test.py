"""Live test: can tick manipulation speed up woodcutting, fishing or mining on 2009Scape? (Caleb, 2026-10-30)

The code says no (decision log, `m002-thieving-targets`): every action that sets the skilling clock first checks
that it's ready, herb on tar doesn't use the clock, and mining waits on its own script delay. This test tries the
OSRS methods on the live server in case the code has a gap.

Each trial spawns a fresh character, sets it up with debug commands (setup only: levels, items, a quest, a
teleport), starts the activity and lets it settle, then runs a per-tick schedule (the bridge's `schedule` command:
one list of commands per game tick). Every tick it reads `debug_clocks` and `state`, then sends that tick's inputs as
client packets (`packet=true`), so they are handled in the next tick's packet phase exactly as a client's are.

A server tick runs: client packets, then the world's pulses (a buried bone's effect is a 1-tick pulse), then the
bridge (where the readings are taken), then each character's queue and interaction scripts. So a reading at tick r
shows the scripts of tick r - 1 and the packets and pulses of tick r. How events are told apart:
- woodcutting and fishing roll when Clocks.SKILLING is ready, in the scripts, and set it 3 / 5 ticks ahead: a roll
  in tick r - 1 reads r + 2 / r + 4 at r. Burying a bone (if the clock is ready) sets it 2 ahead in the pulses of
  tick r, which also reads r + 2, and removes the bone in tick r + 1's scripts (seen at r + 2). Crafting a log sets
  it 3 ahead in the scripts and adds 15 arrow shafts (seen at the same reading). For woodcutting, whose roll also
  reads r + 2, the bone and the shafts tell the three apart.
- a click cancels what an item action started: "Make" queues the log craft as a weak script for the next tick's
  scripts, which the click's removeWeakScripts drops, and the tar is a pulse (its first step only waits 4 ticks)
  that the click's movement pulse replaces. So the item methods are also tried with the click a few ticks later.
- mining delays its own script (delayScript): an execution in tick r - 1 reads script_next = r + 3 at r. An
  execution in a tick whose packets included the click is the click's first step, which only waits; any other is a
  roll.

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/tick_manipulation_test.py [--ticks 45] [--tick-ms 100]
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any, Callable

from rlscape.bridge.client import BridgeClient

REPO = Path(__file__).resolve().parents[1]
BONES, KNIFE, LOGS, ARROW_SHAFT = 526, 946, 1511, 52
CLEAN_GUAM, SWAMP_TAR, PESTLE_AND_MORTAR = 249, 1939, 233
# Skill dialogue buttons, as the client sends them: DialogueInterpreter.handle passes button - 1 to the dialogue, and
# SkillDialogue maps that to an item and amount.
FOUR_OPTION_MAKE_1_FIRST = (305, 9)  # knife on logs: arrow shafts, shortbow, longbow, stock; "Make 1" arrow shafts
ONE_OPTION_MAKE_1 = (309, 6)  # herb on tar: "Make 1"
SETTLE_TICKS = 12  # after the first click: walk over and start
TRAILING_READINGS = 3  # readings after the last inputs, so their effects are seen


@dataclass
class Activity:
    skill: str
    level: int
    site: tuple[int, int, int]
    target: str
    option: str
    is_object: bool
    product: int
    roll_delta: int | None  # the skilling clock's step after a roll; None for mining (script delay)


ACTIVITIES = {
    "woodcutting": Activity("woodcutting", 30, (3087, 3232, 0), "Willow", "Chop down", True, 1519, 3),
    "fishing": Activity("fishing", 1, (3086, 3229, 0), "Fishing spot", "Net", False, 317, 5),
    "mining": Activity("mining", 1, (3228, 3147, 0), "Rocks", "Mine", True, 436, None),
}


def click(uid: int, a: Activity) -> dict[str, Any]:
    return {"cmd": "interact", "uid": uid, "name": a.target, "option": a.option, "object": a.is_object, "packet": True}


def bury(uid: int) -> dict[str, Any]:
    return {"cmd": "item_option", "uid": uid, "item": BONES, "option": "Bury", "packet": True}


def knife_on_log(uid: int) -> list[dict[str, Any]]:
    """Knife on logs and "Make 1" arrow shafts in the same tick: faster than a person could click, so the most
    favourable case for the trick."""
    iface, button = FOUR_OPTION_MAKE_1_FIRST
    return [{"cmd": "use_item", "uid": uid, "item": KNIFE, "with": LOGS, "packet": True},
            {"cmd": "dialogue_button", "uid": uid, "interface": iface, "button": button, "packet": True}]


def herb_on_tar(uid: int) -> list[dict[str, Any]]:
    """Herb on tar opens its dialogue a tick later (UseWithHandler runs it in a 1-tick pulse), so "Make 1" goes in
    the next tick's inputs (make_1)."""
    return [{"cmd": "use_item", "uid": uid, "item": CLEAN_GUAM, "with": SWAMP_TAR, "packet": True}]


def make_1(uid: int) -> list[dict[str, Any]]:
    iface, button = ONE_OPTION_MAKE_1
    return [{"cmd": "dialogue_button", "uid": uid, "interface": iface, "button": button, "packet": True}]


# A method: the items it needs, and the inputs for tick i of the measured window (besides the readings).
Inputs = Callable[[int, Activity, int], list[dict[str, Any]]]


@dataclass
class Method:
    name: str
    items: list[tuple[int, int]] = field(default_factory=list)
    inputs: Inputs = lambda uid, a, i: []
    herblore: bool = False


METHODS = [
    Method("baseline (one click)"),
    Method("re-click every tick", inputs=lambda uid, a, i: [click(uid, a)]),
    Method("bury, then click, every tick", [(BONES, 9)], lambda uid, a, i: [bury(uid), click(uid, a)]),
    Method("click, then bury, every tick", [(BONES, 9)], lambda uid, a, i: [click(uid, a), bury(uid)]),
    Method("bury, then click, every 2 ticks", [(BONES, 9)],
           lambda uid, a, i: [bury(uid), click(uid, a)] if i % 2 == 0 else []),
    Method("knife on log, then click, every 3 ticks", [(KNIFE, 1), (LOGS, 6)],
           lambda uid, a, i: [*knife_on_log(uid), click(uid, a)] if i % 3 == 0 else []),
    Method("knife on log; click the next tick; every 3 ticks", [(KNIFE, 1), (LOGS, 6)],
           lambda uid, a, i: knife_on_log(uid) if i % 3 == 0 else [click(uid, a)] if i % 3 == 1 else []),
    Method("knife on log; click 2 ticks later; every 3 ticks", [(KNIFE, 1), (LOGS, 6)],
           lambda uid, a, i: knife_on_log(uid) if i % 3 == 0 else [click(uid, a)] if i % 3 == 2 else []),
    Method("herb on tar; Make 1 and click the next tick; every 3 ticks",
           [(CLEAN_GUAM, 3), (SWAMP_TAR, 45), (PESTLE_AND_MORTAR, 1)],
           lambda uid, a, i: herb_on_tar(uid) if i % 3 == 0 else [*make_1(uid), click(uid, a)] if i % 3 == 1 else [],
           herblore=True),
    Method("herb on tar; Make 1 the next tick; click 7 ticks later; every 8 ticks",
           [(CLEAN_GUAM, 3), (SWAMP_TAR, 45), (PESTLE_AND_MORTAR, 1)],
           lambda uid, a, i: herb_on_tar(uid) if i % 8 == 0 else make_1(uid) if i % 8 == 1 else
           [click(uid, a)] if i % 8 == 7 else [], herblore=True),
]


def count(state: dict[str, Any], item: int) -> int:
    return sum(stack["amount"] for stack in state["inventory"] if stack["id"] == item)


def xp(state: dict[str, Any], skill: str) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == skill)


def trial(client: BridgeClient, a: Activity, method: Method, ticks: int) -> dict[str, Any]:
    uid = client.spawn()["uid"]
    try:
        client.debug_set_levels(uid, {a.skill: a.level})
        for item, amount in method.items:
            client.debug_give(uid, item, amount)
        if method.herblore:
            client.debug_set_levels(uid, {"herblore": 19})
            client.debug_complete_quest(uid, "DRUIDIC_RITUAL")
        client.debug_teleport(uid, *a.site)
        client.wait(3)
        client.interact(uid, a.target, a.option, a.is_object)
        client.wait(SETTLE_TICKS)
        steps = []
        for i in range(ticks + TRAILING_READINGS):
            inputs = method.inputs(uid, a, i) if i < ticks else []
            steps.append([{"cmd": "debug_clocks", "uid": uid}, {"cmd": "state", "uid": uid}, *inputs])
        done = client.schedule(steps)
    finally:
        client.despawn(uid)
    return analyse(a, method, done)


def analyse(a: Activity, method: Method, done: list[dict[str, Any]]) -> dict[str, Any]:
    ticks = [step["tick"] for step in done]
    assert ticks == list(range(ticks[0], ticks[0] + len(ticks))), "the schedule skipped a tick"
    clocks = [step["results"][0] for step in done]
    states = [step["results"][1]["state"] for step in done]
    clicked = {step["tick"] + 1 for step in done if any(r.get("target") for r in step["results"][2:])}  # packet tick
    failed = sorted({str(r.get("error")) for step in done for r in step["results"] if not r.get("ok")})
    bones, shafts = [count(s, BONES) for s in states], [count(s, ARROW_SHAFT) for s in states]
    rolls, buries, crafts, starts, other = [], [], [], [], []
    for i in range(1, len(done)):
        r = ticks[i]
        if a.roll_delta is not None:
            if clocks[i]["skilling"] == clocks[i - 1]["skilling"]:
                continue
            ahead = clocks[i]["skilling"] - r
            if shafts[i] > shafts[i - 1]:
                crafts.append(r - 1)
            elif ahead == 2 and i + 2 < len(done) and bones[i + 2] < bones[i + 1]:
                buries.append(r)
            elif ahead == a.roll_delta - 1:
                rolls.append(r - 1)
            else:
                other.append((r, ahead))
        else:
            nxt, before = clocks[i]["script_next"], clocks[i - 1]["script_next"]
            if nxt is None or nxt == before:
                continue
            if nxt - r != 3:
                other.append((r, nxt - r))
            elif r - 1 in clicked:
                starts.append(r - 1)
            else:
                rolls.append(r - 1)
    span = len(done) - TRAILING_READINGS
    gaps = [later - earlier for earlier, later in pairwise(rolls)]
    first, last = states[0], states[-1]
    return {
        "activity": a.skill, "method": method.name, "ticks": span,
        "rolls": len(rolls), "rolls_per_100_ticks": round(100 * len(rolls) / span, 1),
        "median_ticks_between_rolls": statistics.median(gaps) if gaps else None,
        "shortest_ticks_between_rolls": min(gaps) if gaps else None,
        "roll_ticks": rolls, "bury_ticks": buries, "craft_ticks": crafts, "start_ticks": starts,
        "unexplained": other,
        "product_gained": count(last, a.product) - count(first, a.product),
        "xp_gained": round(xp(last, a.skill) - xp(first, a.skill), 1),
        "bones_buried": bones[0] - bones[-1], "arrow_shafts_made": shafts[-1] - shafts[0],
        "fletching_xp": round(xp(last, "fletching") - xp(first, "fletching"), 1),
        "herblore_xp": round(xp(last, "herblore") - xp(first, "herblore"), 1),
        "failed_inputs": failed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ticks", type=int, default=45)
    parser.add_argument("--tick-ms", type=int, default=100)
    args = parser.parse_args()
    results = []
    with BridgeClient(timeout=600) as client:
        old_ms = client.ping()["tick_ms"]
        client.set_tick_ms(args.tick_ms)
        try:
            for a in ACTIVITIES.values():
                for method in METHODS:
                    r = trial(client, a, method, args.ticks)
                    results.append(r)
                    print(f"{r['activity']:12s} {r['method']:48s} rolls/100t {r['rolls_per_100_ticks']:5.1f}  "
                          f"gap median {r['median_ticks_between_rolls']} min {r['shortest_ticks_between_rolls']}  "
                          f"product {r['product_gained']:2d}  "
                          f"buried {r['bones_buried']} shafts {r['arrow_shafts_made']} tar xp {r['herblore_xp']} "
                          f"unexplained {r['unexplained'][:4]} errors {r['failed_inputs'][:2]}")
        finally:
            client.set_tick_ms(old_ms)
    out = REPO / "results" / "live" / f"tick-manipulation-{datetime.now():%Y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"ticks": args.ticks, "tick_ms": args.tick_ms, "trials": results}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
