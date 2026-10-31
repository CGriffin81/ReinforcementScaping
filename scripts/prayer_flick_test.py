"""Live test: does prayer flicking work on 2009Scape? (OQ-3; Caleb, 2026-10-30: "We will implement prayer flicking and
3-tick woodcutting if they can be used", after a live test.)

From the source:
- Prayer.tick, in each character's tick after the world's pulses, counts the ticks in a row with any prayer on,
  resets the count on a tick with none on, and drains only on even counts.
- A protection prayer is checked when the attacker swings (Entity.getFormattedHit, from adjustBattleState): an NPC's
  hit is then 0, however late it lands.
So a prayer that's on in the tick of a swing and off the next should block it and cost nothing. This test checks it.

Each trial spawns a fresh character, sets Prayer 43 (Protect from Melee), Hitpoints 99 and Attack, Strength and
Defence 1 (setup only: debug_set_levels and debug_teleport), puts it beside a lone hill giant (npc 117: 35
hitpoints, a melee swing every 6 ticks) and attacks it. In a first run against a Falador guard (18 hitpoints), the
fourth trial's fight stopped after 37 ticks, most likely because the earlier trials had worn the guard down. Once the fight has settled, a per-tick schedule (the bridge's `schedule`) reads the
state each tick and sends that tick's prayer clicks as client packets, handled in the next tick's packet phase as a
client's are. A reading at tick r comes after tick r's packets and pulses and before its characters' ticks, so it
shows the prayers the tick's swings and drain saw.

Patterns:
- none: no prayer.
- on: one click, so the prayer stays on.
- flicked: a click every tick, so the prayer is on every other tick. Halfway, one click is skipped while the prayer
  is off, which costs nothing and moves the on-ticks to the other parity. The giant swings every 6 ticks, so all
  its swings fall on one parity: one half should block every hit and the other none, both at no cost.
- off and on: the OSRS one-tick flick, both clicks in the same tick, every tick. The prayer is never off when a tick
  ends, so it should drain as if left on.

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/prayer_flick_test.py [--ticks 120] [--repeats 2] [--tick-ms 100]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rlscape.bridge.client import BridgeClient

REPO = Path(__file__).resolve().parents[1]
PRAYER = "PROTECT_FROM_MELEE"
SITE, TARGET = (2439, 3214, 0), "Hill Giant"  # npc 117's lone spawn there
LEVELS = {"prayer": 43, "hitpoints": 99, "attack": 1, "strength": 1, "defence": 1}
SETTLE_TICKS = 12  # walk over, and the first swings
MARGIN = 4  # readings after the flicked pattern's switch that count for neither half (a swing's hit lands later)
PATTERNS = ("none", "on", "flicked", "off and on")


def click(uid: int) -> dict[str, Any]:
    return {"cmd": "prayer", "uid": uid, "prayer": PRAYER, "packet": True}


def inputs(pattern: str, uid: int, i: int, ticks: int) -> list[dict[str, Any]]:
    """The clicks of step i. After the click of step i (handled at the next tick), the prayer is on for even i."""
    if pattern == "on":
        return [click(uid)] if i == 0 else []
    if pattern == "flicked":
        return [] if i == switch_step(ticks) else [click(uid)]
    if pattern == "off and on":
        return [click(uid)] if i == 0 else [click(uid), click(uid)]
    return []


def switch_step(ticks: int) -> int:
    """The flicked pattern's skipped click: an even step, when the prayer is off, so it stays off a second tick."""
    return ticks // 2 + ticks // 2 % 2


def trial(client: BridgeClient, pattern: str, ticks: int) -> dict[str, Any]:
    uid = client.spawn()["uid"]
    try:
        client.debug_set_levels(uid, LEVELS)
        client.debug_teleport(uid, *SITE)
        client.wait(3)
        client.request("interact", uid=uid, name=TARGET, option="Attack", object=False, packet=True)
        client.wait(SETTLE_TICKS)
        steps = [[{"cmd": "state", "uid": uid}, *inputs(pattern, uid, i, ticks)] for i in range(ticks)]
        done = client.schedule(steps)
    finally:
        client.despawn(uid)
    return analyse(pattern, ticks, done)


def analyse(pattern: str, ticks: int, done: list[dict[str, Any]]) -> dict[str, Any]:
    tick = [step["tick"] for step in done]
    assert tick == list(range(tick[0], tick[0] + len(tick))), "the schedule skipped a tick"
    states = [step["results"][0]["state"] for step in done]
    hp = [s["hitpoints"] for s in states]
    on = [PRAYER in s["prayers"] for s in states]
    hits = [(i, hp[i - 1] - hp[i]) for i in range(1, len(hp)) if hp[i] < hp[i - 1]]
    failed = sorted({str(r.get("error")) for step in done for r in step["results"] if not r.get("ok")})
    result = {
        "pattern": pattern, "ticks": ticks, "first_tick": tick[0],
        "hits": len(hits), "damage": sum(d for _, d in hits),
        "prayer_drained": round(states[0]["prayer_points"] - states[-1]["prayer_points"], 2),
        "ticks_prayer_on": sum(on), "ticks_fighting": sum(s["target"] is not None for s in states),
        "hit_steps": [i for i, _ in hits], "on_steps": [i for i, o in enumerate(on) if o],
        "failed_inputs": failed,
    }
    if pattern == "flicked":
        cut = switch_step(ticks) + 1
        halves = [range(1, cut), range(cut + MARGIN, ticks)]
        result["halves"] = [{
            "steps": [h.start, h.stop - 1],
            "on_tick_parity": sorted({tick[i] % 2 for i in h if on[i]}),
            "hits": sum(1 for i, _ in hits if i in h),
            "hit_tick_parity": sorted({tick[i] % 2 for i, _ in hits if i in h}),
        } for h in halves]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ticks", type=int, default=120)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--tick-ms", type=int, default=100)
    args = parser.parse_args()
    results = []
    with BridgeClient(timeout=600) as client:
        old_ms = client.ping()["tick_ms"]
        client.set_tick_ms(args.tick_ms)
        try:
            for _ in range(args.repeats):
                for pattern in PATTERNS:
                    r = trial(client, pattern, args.ticks)
                    results.append(r)
                    halves = "  ".join(f"half {h['steps']}: hits {h['hits']}, on parity {h['on_tick_parity']}, "
                                       f"hit parity {h['hit_tick_parity']}" for h in r.get("halves", []))
                    print(f"{r['pattern']:11s} hits {r['hits']:2d} damage {r['damage']:3d}  "
                          f"prayer drained {r['prayer_drained']:5.2f}  on {r['ticks_prayer_on']:3d}/{r['ticks']} ticks  "
                          f"fighting {r['ticks_fighting']:3d}  {halves}  errors {r['failed_inputs'][:2]}")
        finally:
            client.set_tick_ms(old_ms)
    out = REPO / "results" / "live" / f"prayer-flicking-{datetime.now():%Y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"ticks": args.ticks, "tick_ms": args.tick_ms, "levels": LEVELS, "trials": results},
                              indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
