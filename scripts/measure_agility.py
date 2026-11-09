"""Measure the agility courses on the server (sim v1, `docs/sim-v1-skills-draft.md` §3 and §7: "each obstacle's
animation and walk, measured"), for the sim's lap model (rlscape.sim.agility).

A run: a calibration character (Agility at `--agility`, Hitpoints 99; setup only) teleported to the course's start,
then laps as a person runs them, a tick at a time: when it's idle (no pulse, script or walk, not locked), click the
next obstacle (the bridge's `interact`, as a client's click; by tile where the course has two alike). An obstacle is
done when its Agility XP comes (the Barbarian Outpost's ladder off the ledge, which gives none, when the character is
down off the platform). A fall is a hit taken or a drop underground: then, as a person does, climb the pit's ladder if
it's in one, and click the failed obstacle again; where that one can't be reached from there (the ledge is upstairs),
the one before it, and so on. Between laps, Hitpoints are set back to 99 (setup only), so no eating comes into the
times.

Measured, per obstacle: the ticks from its click to the next obstacle's click when it succeeds (its own time, the walk
to the next and the click), and when it fails, the ticks from its click to its next attempt's click and the Agility XP
on the way (obstacles redone); the hits; and each lap's ticks and XP.

Usage, with a server running (worldprops/rl.conf, or an instance with RL_BRIDGE_PORT):
    uv run python scripts/measure_agility.py --course gnome --agility 1 --laps 10
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rlscape.bridge.client import BridgeClient, BridgeError, run_suffix
from rlscape.gamedata.agility import COURSES, Course, Obstacle

REPO = Path(__file__).resolve().parents[1]
TICKS_PER_HOUR = 6000
UNDERGROUND_Y = 6400
STEP_TICKS = 40  # an obstacle not done in this many ticks after its click is clicked again
IDLE_RETRY = 3  # readings standing idle after a click, with no XP, before a person clicks again
LAP_TICKS = 3_000  # a lap not done in this many ticks is abandoned


def agility_xp(state: dict[str, Any]) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == "agility")


def idle(state: dict[str, Any]) -> bool:
    return not (state["busy"] or state["moving"] or state["script"] is not None or state.get("locked"))


def click(client: BridgeClient, uid: int, o: Obstacle) -> bool:
    """A client's click on the obstacle; False if the character can't reach it from where it is."""
    try:
        client.request("interact", uid=uid, name=o.name, option=o.option, object=True, ids=list(o.ids), packet=True,
                       **({"at": list(o.at)} if o.at else {}))
        return True
    except BridgeError as e:
        if "none reachable" in str(e) or "no '" in str(e):
            return False
        raise


class Runner:
    def __init__(self, client: BridgeClient, uid: int):
        self.client, self.uid, self.state, self.tick = client, uid, None, 0

    def step(self) -> dict[str, Any]:
        out = self.client.schedule([[{"cmd": "state", "uid": self.uid}]])[0]
        self.state, self.tick = out["results"][0]["state"], out["tick"]
        return self.state

    def wait_idle(self, limit: int = 60) -> None:
        for _ in range(limit):
            if idle(self.step()):
                return

    def climb_out(self) -> None:
        """Out of a pit: its ladder up, then until the character stands on the surface."""
        for _ in range(5):
            if self.state["location"]["y"] < UNDERGROUND_Y:
                return
            self.wait_idle()
            try:
                self.client.request("interact", uid=self.uid, name="Ladder", option="Climb-up", object=True,
                                    packet=True)
            except BridgeError:
                pass
            for _ in range(20):
                if self.step()["location"]["y"] < UNDERGROUND_Y:
                    break
        self.wait_idle()


def run_lap(r: Runner, course: Course) -> dict[str, Any]:
    """One lap from wherever the last left off: every obstacle in order, falls and all."""
    obstacles, events = course.obstacles, []
    i, start_tick, lap_xp0 = 0, None, agility_xp(r.state)
    retry_of: dict[int, dict[str, Any]] = {}  # a failed obstacle -> its fall event, until it's attempted again
    while i < len(obstacles):
        if start_tick is not None and r.tick - start_tick > LAP_TICKS:
            return {"abandoned": True, "events": events}
        r.wait_idle()
        o = obstacles[i]
        if not click(r.client, r.uid, o):
            if i > 0:
                i -= 1  # back to the one before it, as a person goes round again
            elif course.entry is not None and click(r.client, r.uid, course.entry):
                events.append({"obstacle": -1, "outcome": "entry", "clicked": r.tick})
                r.wait_idle()
                for _ in range(STEP_TICKS):  # through the entry
                    if idle(r.step()):
                        break
            else:
                raise RuntimeError(f"can't reach {o.name} to start a lap from {r.state['location']}")
            continue
        clicked, xp0, hp0, z0 = r.tick, agility_xp(r.state), r.state["hitpoints"], r.state["location"]["z"]
        start_tick = clicked if start_tick is None else start_tick
        if i in retry_of:  # the fall's cost ends at the next click: this obstacle again, or where the lap resumes
            fall = retry_of.pop(i)
            fall["ticks"], fall["xp_on_the_way"] = clicked - fall["clicked"], xp0 - fall["xp_after"]
        outcome, still = None, 0
        for n in range(STEP_TICKS * 4):
            s = r.step()
            still = still + 1 if o.inert_fail and n >= 2 and idle(s) and agility_xp(s) == xp0 else 0
            if still >= IDLE_RETRY:  # nothing happened (a rope swing's fail): a person clicks again
                outcome = "nothing"
                break
            gained = agility_xp(s) - xp0
            if gained >= o.xp - 1e-6 and o.xp > 0 or (o.xp == 0 and o.flag is None and s["location"]["z"] != z0):
                outcome = "ok"
                break
            if o.xp == 0 and o.flag is not None and gained > 0:  # the Wilderness rocks: the lap bonus is its XP
                outcome = "ok"
                break
            if s["hitpoints"] < hp0 or s["location"]["y"] >= UNDERGROUND_Y:
                outcome = "fall"
                break
        if outcome in (None, "nothing"):
            events.append({"obstacle": i, "outcome": outcome or "stuck", "clicked": clicked})
            if i not in retry_of:
                events[-1]["xp_after"] = agility_xp(r.state)
                retry_of[i] = events[-1]  # its cost: to the next click
            continue  # clicked again
        event = {"obstacle": i, "outcome": outcome, "clicked": clicked, "done": r.tick, "xp": agility_xp(r.state) - xp0}
        events.append(event)
        if outcome == "fall":
            event["hit"] = hp0 - min(hp0, r.state["hitpoints"])
            for _ in range(15):  # the fall's own animation and teleport play out
                r.step()
            event["hit"] = max(event["hit"], hp0 - r.state["hitpoints"])
            r.climb_out()
            event["xp_after"] = agility_xp(r.state)
            if o.resume is None:
                retry_of[i] = event  # this one again
            else:
                i, event["resumed_at"] = o.resume, o.resume  # the course goes on from there
                retry_of[i] = event
            continue
        i += 1
    r.wait_idle(10)
    return {"abandoned": False, "events": events, "ticks": r.tick - start_tick, "xp": agility_xp(r.state) - lap_xp0}


def measure(client: BridgeClient, course: Course, agility: int, laps: int) -> dict[str, Any]:
    uid = client.spawn()["uid"]
    out: list[dict[str, Any]] = []
    stopped = None
    try:
        client.debug_set_levels(uid, {"agility": agility, "hitpoints": 99})
        client.debug_teleport(uid, *course.start)
        client.wait(3)
        r = Runner(client, uid)
        r.step()
        for _ in range(laps):
            try:
                lap = run_lap(r, course)
            except RuntimeError as e:  # off the course (a death, a teleport): stop, keeping the laps so far
                s = r.step()
                stopped = {"error": str(e), "location": s["location"], "hitpoints": s["hitpoints"],
                           "messages": s["messages"][-10:]}
                print(f"  stopped: {stopped}", flush=True)
                break
            out.append(lap)
            falls = sum(e["outcome"] == "fall" for e in lap["events"])
            done = "abandoned" if lap["abandoned"] else f"{lap['ticks']} ticks, {lap['xp']:.1f} xp"
            print(f"  lap: {done}, falls {falls}", flush=True)
            client.debug_set_levels(uid, {"hitpoints": 99})  # setup only: no eating in the times
            r.step()
    finally:
        client.despawn(uid)
    return {"course": course.key, "agility": agility, "laps": out, "stopped": stopped}


def measure_entries(client: BridgeClient, course: Course, agility: int, runs: int) -> list[dict[str, Any]]:
    """The entry (the Barbarian Outpost's pipe; the Wilderness course's door and ridge), from its approach tile: the
    ticks from its click to the first obstacle's click, with any falls on the way (the ridge into the wolf pit)."""
    out = []
    uid = client.spawn()["uid"]
    try:
        client.debug_set_levels(uid, {"agility": agility, "hitpoints": 99})
        r = Runner(client, uid)
        for _ in range(runs):
            client.debug_teleport(uid, *course.approach)  # setup only
            client.wait(3)
            r.step()
            clicked, hp0, xp0, falls = None, r.state["hitpoints"], agility_xp(r.state), 0
            for _ in range(10):  # the entry, again after a fall
                r.wait_idle()
                clicked = clicked if clicked is not None else r.tick
                if not click(client, uid, course.entry):
                    break
                here = r.state["location"]
                for n in range(STEP_TICKS):
                    s = r.step()
                    moved = s["location"] != here
                    xp_done = course.entry.xp > 0 and agility_xp(s) - xp0 >= course.entry.xp - 1e-6
                    if xp_done or s["hitpoints"] < hp0 or (course.entry.xp == 0 and moved and n >= 2 and idle(s)):
                        break
                if r.state["hitpoints"] < hp0:
                    falls, hp0 = falls + 1, r.state["hitpoints"]
                    for _ in range(15):
                        r.step()
                    r.climb_out()
                    continue
                break
            r.wait_idle()
            first = click(client, uid, course.obstacles[0])
            out.append({"ticks": r.tick - clicked, "falls": falls, "xp": agility_xp(r.state) - xp0, "reached": first})
            print(f"  entry: {out[-1]}", flush=True)
            client.debug_set_levels(uid, {"hitpoints": 99})
    finally:
        client.despawn(uid)
    return out


def measure_pit(client: BridgeClient, course: Course, visits: int) -> dict[str, Any]:
    """OQ-46 (a): the pit a fall drops into, measured. A calibration character (Agility 1, so the obstacle fails;
    Hitpoints 99; its other skills 1, combat level about 25, which the Wilderness pit's skeletons pick; auto-retaliate
    off, as Caleb's rule for gathering has it) teleported to the obstacle's start (setup only) falls into the pit and
    climbs its ladder as soon as it can, as a person does. Per visit: the ticks underground, and the damaging hits and
    damage taken there after the fall's own hit."""
    i = next(k for k, o in enumerate(course.obstacles) if o.pit is not None)
    o, out = course.obstacles[i], []
    uid = client.spawn()["uid"]
    try:
        client.debug_set_levels(uid, {"agility": 1, "hitpoints": 99})
        client.set_retaliate(uid, False)
        level = client.state(uid)["combat_level"]
        r = Runner(client, uid)
        start = {2297: (3002, 3945, 0)}[o.ids[0]]  # WildernessCourse.getDestination for the log
        for _ in range(visits):
            client.debug_set_levels(uid, {"hitpoints": 99})  # setup only
            client.debug_teleport(uid, *start)
            client.wait(3)
            click(client, uid, o)
            landed = None
            for _ in range(STEP_TICKS):
                if r.step()["location"]["y"] >= UNDERGROUND_Y:
                    landed = r.tick
                    break
            if landed is None:
                continue  # it got across (1% at Agility 1)
            for _ in range(2):  # the fall's hit lands with the teleport
                r.step()
            hp, hits, damage = r.state["hitpoints"], 0, 0
            for _ in range(400):
                s = r.step()
                if s["hitpoints"] < hp:
                    hits, damage = hits + 1, damage + hp - s["hitpoints"]
                hp = s["hitpoints"]
                if s["location"]["y"] < UNDERGROUND_Y or hp <= 0:
                    break
                if idle(s):
                    try:
                        client.request("interact", uid=uid, name="Ladder", option="Climb-up", object=True,
                                       packet=True)
                    except BridgeError:
                        pass
            out.append({"ticks": r.tick - landed, "hits": hits, "damage": damage,
                        "out": r.state["location"]["y"] < UNDERGROUND_Y})
            print(f"  pit: {out[-1]}", flush=True)
    finally:
        client.despawn(uid)
    return {"course": course.key, "obstacle": i, "combat_level": level, "visits": out}


def summarise(result: dict[str, Any], course: Course) -> dict[str, Any]:
    """Per obstacle: the click-to-next-click ticks of its successes (within a lap, so the last obstacle's is to the
    next lap's first click), and its falls' costs."""
    ok: dict[int, list[int]] = {i: [] for i in range(len(course.obstacles))}
    falls: dict[int, list[dict[str, Any]]] = {i: [] for i in range(len(course.obstacles))}
    clicks = [e for lap in result["laps"] for e in lap["events"]]
    for e, nxt in zip(clicks, clicks[1:]):
        if e["outcome"] == "ok" and nxt["obstacle"] == (e["obstacle"] + 1) % len(course.obstacles):
            ok[e["obstacle"]].append(nxt["clicked"] - e["clicked"])
    for e in clicks:
        if e["outcome"] in ("fall", "nothing") and "ticks" in e:
            falls[e["obstacle"]].append({k: e.get(k, 0) for k in ("ticks", "hit", "xp_on_the_way", "outcome")})
    return {"success_ticks": {i: v for i, v in ok.items()}, "falls": {i: v for i, v in falls.items() if v},
            "attempts": {i: sum(1 for e in clicks if e["obstacle"] == i and e["outcome"] in ("ok", "fall"))
                         for i in ok}}


def compare(result: dict[str, Any], course: Course) -> dict[str, Any]:
    """The gate (env contract §7), over whole laps: the server's Agility XP per tick from the first lap's first click
    to the last lap's first click (the laps before it, falls and all), against the sim's expected lap
    (AgilityLaps.expected_rate, which the lap loop matches: tests/test_sim_agility.py) at the run's middle level, the
    first lap's first obstacle clicked from the start tile as the run's was."""
    from dataclasses import replace

    from rlscape.sim.agility import AgilityLaps
    from rlscape.sim.skills import SKILL_INDEX, XP_FOR_LEVEL, level_for_xp
    from rlscape.sim.state import CharacterState

    laps = [lap for lap in result["laps"] if not lap["abandoned"]]
    if len(laps) < 2:
        raise KeyError("fewer than two whole laps")
    starts = [lap["events"][0]["clicked"] for lap in laps]
    ticks, xp = starts[-1] - starts[0], sum(lap["xp"] for lap in laps[:-1])
    path = AgilityLaps(replace(course, entry=None, approach=None))
    state = CharacterState.fresh()
    middle = XP_FOR_LEVEL[result["agility"]] + xp / 2
    state.xp[SKILL_INDEX["agility"]] = float(middle)
    lap_xp, lap_ticks = path.expected_rate(state)
    n = len(laps) - 1
    sim_ticks = n * lap_ticks - (path.times.obstacles[0] - path.times.first)
    server, sim = xp / ticks * TICKS_PER_HOUR, n * lap_xp / sim_ticks * TICKS_PER_HOUR
    return {"laps": n, "ticks": ticks, "middle_level": level_for_xp(middle), "server_xp_per_hour": server,
            "sim_xp_per_hour": sim, "sim_over_server": sim / server, "within_gate": abs(sim / server - 1) <= 0.2}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--course", choices=sorted(COURSES), required=True)
    parser.add_argument("--agility", type=int, required=True)
    parser.add_argument("--laps", type=int, default=10)
    parser.add_argument("--entries", type=int, default=0, help="instead of laps, cross the course's entry this often")
    parser.add_argument("--pit", type=int, default=0, help="instead of laps, fall into the course's pit this often")
    parser.add_argument("--tick-ms", type=int, default=50)
    args = parser.parse_args()
    course = COURSES[args.course]
    with BridgeClient() as client:
        old_ms = client.set_tick_ms(args.tick_ms)
        try:
            if args.pit:
                result = measure_pit(client, course, args.pit)
            elif args.entries:
                result = {"course": course.key, "agility": args.agility,
                          "entries": measure_entries(client, course, args.agility, args.entries)}
            else:
                result = measure(client, course, args.agility, args.laps)
        finally:
            client.set_tick_ms(old_ms)
    if args.pit:
        v = result["visits"]
        print(f"  pit: combat level {result['combat_level']}, {len(v)} falls, {sum(x['ticks'] for x in v)} ticks "
              f"underground, {sum(x['hits'] for x in v)} hits, {sum(x['damage'] for x in v)} damage")
        out = (REPO / "results" / "calibration"
               / f"agility-pit-{datetime.now():%Y%m%d-%H%M}-{args.course}{run_suffix(args.tick_ms)}.json")
        out.write_text(json.dumps({"args": vars(args), **result}, indent=1))
        print(f"saved {out.relative_to(REPO)}")
        return
    if args.entries:
        e = result["entries"]
        print(f"  entries: mean {sum(x['ticks'] for x in e) / len(e):.1f} ticks, falls {sum(x['falls'] for x in e)}")
        out = (REPO / "results" / "calibration"
               / f"agility-{datetime.now():%Y%m%d-%H%M}-{args.course}-entry-a{args.agility}{run_suffix(args.tick_ms)}.json")
        out.write_text(json.dumps({"args": vars(args), **result}, indent=1))
        print(f"saved {out.relative_to(REPO)}")
        return
    result["summary"] = summarise(result, course)
    try:
        result["compare"] = compare(result, course)
        c = result["compare"]
        print(f"  XP/hr: server {c['server_xp_per_hour']:.0f}, sim {c['sim_xp_per_hour']:.0f} "
              f"({c['sim_over_server']:.2f})")
    except KeyError as e:  # the course's times aren't in the sim yet
        print(f"  no sim comparison: {e!r}")
    s = result["summary"]
    for i, o in enumerate(course.obstacles):
        t = s["success_ticks"][i]
        f = s["falls"].get(i, [])
        print(f"  {i} {o.name:16s} ok {len(t):3d} mean {sum(t) / len(t) if t else float('nan'):6.1f} {sorted(t)[:3]}..."
              f"  falls {len(f)}" + (f" mean {sum(x['ticks'] for x in f) / len(f):.1f} ticks" if f else ""))
    out = (REPO / "results" / "calibration"
           / f"agility-{datetime.now():%Y%m%d-%H%M}-{args.course}-a{args.agility}{run_suffix(args.tick_ms)}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(args), **result}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
