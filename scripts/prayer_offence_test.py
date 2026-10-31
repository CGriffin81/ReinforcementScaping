"""Live test: do flicked offensive prayers work on 2009Scape, and when do a fight's two sides swing? (OQ-3, decided by
Caleb on 2026-10-31: fights flick prayers automatically, the accuracy and damage ones included.)

From the source, a prayer's bonus enters the swing handlers' accuracy and max-hit formulas (floor(L + bonus x L) on
the effective level), computed when the attacker swings. So a flicked offensive prayer should work like a flicked
protection prayer (scripts/prayer_flick_test.py): on in the tick of the character's swing, off the next.

The check: Strength 60 punches (unarmed, accurate) for a max hit of 7, and 8 with Ultimate Strength (Strength 69 for
the hit). Damage shows as Attack XP, 4 per point, at the swing. The character fights the Edgeville dungeon's hill
giants (aggressive, so a new one takes over after a kill) with Ultimate Strength:
- none: never on.
- flicked: on every other tick, switching parity halfway (a skipped click while it's off). Unarmed punches come
  every 4 ticks, so all of them fall on one parity: one half's punches should reach 8, the other's never.

Both patterns also record when each side swings: the character's punches at Attack XP gains, the giants' swings a
tick before a hitpoints drop (prayer_flick_test). Protection and offensive prayers flicked together are only free
while the two never swing in adjacent ticks: two ticks in a row with any prayer on drain.

Setup only: debug_set_levels and debug_teleport. Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/prayer_offence_test.py [--ticks 400] [--repeats 2] [--tick-ms 100]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from rlscape.bridge.client import BridgeClient

REPO = Path(__file__).resolve().parents[1]
PRAYER = "ULTIMATE_STRENGTH"
SITE = (3115, 9838, 0)  # among the Edgeville dungeon's hill giants (npc 117)
LEVELS = {"prayer": 31, "attack": 40, "strength": 60, "defence": 20, "hitpoints": 99}  # Defence 20: giant hits to time
MAX_HIT, BOOSTED_MAX_HIT = 7, 8
SETTLE_TICKS = 12
MARGIN = 4
PATTERNS = ("none", "flicked")


def click(uid: int) -> dict[str, Any]:
    return {"cmd": "prayer", "uid": uid, "prayer": PRAYER, "packet": True}


def switch_step(ticks: int) -> int:
    """The skipped click: an even step, when the prayer is off (prayer_flick_test)."""
    return ticks // 2 + ticks // 2 % 2


def skill(state: dict[str, Any], name: str) -> float:
    return next(s["xp"] for s in state["skills"] if s["name"].lower() == name)


def trial(client: BridgeClient, pattern: str, ticks: int) -> dict[str, Any]:
    uid = client.spawn()["uid"]
    try:
        client.debug_set_levels(uid, LEVELS)
        client.debug_teleport(uid, *SITE)
        client.wait(3)
        client.request("interact", uid=uid, name="Hill Giant", option="Attack", object=False, packet=True)
        client.wait(SETTLE_TICKS)
        clicks = pattern == "flicked"
        steps = [[{"cmd": "state", "uid": uid}, *([click(uid)] if clicks and i != switch_step(ticks) else [])]
                 for i in range(ticks)]
        done = client.schedule(steps)
    finally:
        client.despawn(uid)
    return analyse(pattern, ticks, done)


def analyse(pattern: str, ticks: int, done: list[dict[str, Any]]) -> dict[str, Any]:
    tick = [step["tick"] for step in done]
    assert tick == list(range(tick[0], tick[0] + len(tick))), "the schedule skipped a tick"
    states = [step["results"][0]["state"] for step in done]
    attack_xp = [skill(s, "attack") for s in states]
    hp = [s["hitpoints"] for s in states]
    on = [PRAYER in s["prayers"] for s in states]
    punches = {i: round((attack_xp[i] - attack_xp[i - 1]) / 4) for i in range(1, len(states)) if attack_xp[i] > attack_xp[i - 1]}
    npc_swings = [i - 1 for i in range(1, len(states)) if hp[i] < hp[i - 1]]
    # the gap from each giant swing (seen by its damage) to the nearest punch (seen by its damage)
    gaps = Counter(min((s - p for p in punches), key=abs) for s in npc_swings if punches)
    result = {
        "pattern": pattern, "ticks": ticks, "first_tick": tick[0],
        "punches_landed": len(punches), "damage_counts": dict(sorted(Counter(punches.values()).items())),
        "prayer_drained": round(states[0]["prayer_points"] - states[-1]["prayer_points"], 2),
        "giant_hits": len(npc_swings), "hitpoints_left": hp[-1],
        "giant_swing_minus_nearest_punch": dict(sorted(gaps.items())),
        "damage_counts_prayer_on": dict(sorted(Counter(d for i, d in punches.items() if on[i]).items())),
        "damage_counts_prayer_off": dict(sorted(Counter(d for i, d in punches.items() if not on[i]).items())),
        "ticks_fighting": sum(s["target"] is not None for s in states),
    }
    if pattern == "flicked":
        cut = switch_step(ticks) + 1
        result["halves"] = []
        for h in (range(1, cut), range(cut + MARGIN, ticks)):
            landed = [punches[i] for i in punches if i in h]
            result["halves"].append({
                "steps": [h.start, h.stop - 1], "on_tick_parity": sorted({tick[i] % 2 for i in h if on[i]}),
                "punches_landed": len(landed), "max_damage": max(landed, default=None),
                "punches_on_prayer_ticks": sum(1 for i in punches if i in h and on[i]),
                "boosted_max_hits": landed.count(BOOSTED_MAX_HIT),
            })
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ticks", type=int, default=400)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--tick-ms", type=int, default=100)
    args = parser.parse_args()
    results = []
    with BridgeClient(timeout=900) as client:
        old_ms = client.ping()["tick_ms"]
        client.set_tick_ms(args.tick_ms)
        try:
            for _ in range(args.repeats):
                for pattern in PATTERNS:
                    r = trial(client, pattern, args.ticks)
                    results.append(r)
                    halves = "  ".join(f"half {h['steps']}: landed {h['punches_landed']}, max {h['max_damage']}, "
                                       f"8s {h['boosted_max_hits']}, on prayer ticks {h['punches_on_prayer_ticks']}"
                                       for h in r.get("halves", []))
                    print(f"{r['pattern']:8s} landed {r['punches_landed']:3d} damage with the prayer on "
                          f"{r['damage_counts_prayer_on']}, off {r['damage_counts_prayer_off']}  "
                          f"drained {r['prayer_drained']:.2f}  giant hits {r['giant_hits']} hp left {r['hitpoints_left']}"
                          f"  fighting {r['ticks_fighting']}  gaps {r['giant_swing_minus_nearest_punch']}  {halves}")
        finally:
            client.set_tick_ms(old_ms)
    out = REPO / "results" / "live" / f"prayer-offence-{datetime.now():%Y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"ticks": args.ticks, "tick_ms": args.tick_ms, "levels": LEVELS, "trials": results},
                              indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
