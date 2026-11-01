"""Live measurement: how aggressive monsters engage a character at a gathering site (Caleb, 2026-10-31: the sim
models aggressive monsters at gathering sites; decision log).

A calibration character of a band (debug_set_levels, setup only) is teleported from Lumbridge to the site (so it
enters the site's map region, starting the region's aggression tolerance), turns auto-retaliate off (Caleb: no fights
on a gathering task unless trivial), and stands on the site's tile for a number of ticks. Each tick the bridge reports
the monsters whose combat target is the character (`state` attackers) and its hitpoints. From that: when engagements
start, how long they last, the hitpoints lost, and whether they stop after the server's 1,000-tick tolerance.

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/aggression_test.py [--site 3087 3232 0] [--bands 1 31] [--runs 20] [--ticks 1100]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rlscape.bridge.client import BridgeClient

REPO = Path(__file__).resolve().parents[1]
TRAINABLE = ("attack", "strength", "defence", "hitpoints", "ranged", "magic", "prayer", "woodcutting", "mining",
             "smithing", "fishing", "cooking", "firemaking", "thieving", "fletching", "crafting", "agility",
             "herblore", "runecrafting")  # env contract §5
STEP = 50  # ticks of readings per schedule


def run(client: BridgeClient, site: tuple[int, int, int], band: int, ticks: int) -> dict[str, Any]:
    uid = client.spawn()["uid"]
    try:
        if band > 1:
            client.debug_set_levels(uid, {skill: band for skill in TRAINABLE})
        client.set_retaliate(uid, False)
        client.debug_teleport(uid, *site)
        rows = []
        while len(rows) < ticks:
            done = client.schedule([[{"cmd": "state", "uid": uid}] for _ in range(min(STEP, ticks - len(rows)))])
            for step in done:
                s = step["results"][0]["state"]
                rows.append((sorted((a["index"], a["id"]) for a in s["attackers"]), s["hitpoints"]))
        combat_level = client.state(uid)["combat_level"]
    finally:
        client.despawn(uid)
    engagements, open_since = [], {}
    for t, (attackers, _) in enumerate(rows):
        now = {i for i, _ in attackers}
        for i in now - open_since.keys():
            open_since[i] = t
        for i in set(open_since) - now:
            engagements.append({"index": i, "start": open_since.pop(i), "end": t})
    engagements += [{"index": i, "start": s, "end": ticks} for i, s in open_since.items()]
    hp = [h for _, h in rows]
    return {"band": band, "combat_level": combat_level, "engagements": engagements,
            "npc_ids": sorted({n for a, _ in rows for _, n in a}), "hits": sum(1 for a, b in zip(hp, hp[1:]) if b < a),
            "hitpoints_lost": sum(max(a - b, 0) for a, b in zip(hp, hp[1:])),
            "ticks_engaged": sum(1 for a, _ in rows if a)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--site", type=int, nargs=3, default=[3087, 3232, 0])
    parser.add_argument("--bands", type=int, nargs="+", default=[1, 31])
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--ticks", type=int, default=1100)
    parser.add_argument("--tick-ms", type=int, default=20)
    args = parser.parse_args()
    site = tuple(args.site)
    results = []
    with BridgeClient(timeout=900) as client:
        old_ms = client.ping()["tick_ms"]
        client.set_tick_ms(args.tick_ms)
        try:
            for band in args.bands:
                for _ in range(args.runs):
                    r = run(client, site, band, args.ticks)
                    results.append(r)
                    starts = [e["start"] for e in r["engagements"]]
                    print(f"band {band:2d} (combat {r['combat_level']}): {len(starts)} engagements, starting {starts}, "
                          f"lasting {[e['end'] - e['start'] for e in r['engagements']]}, hits {r['hits']}, "
                          f"hp lost {r['hitpoints_lost']}, npcs {r['npc_ids']}")
        finally:
            client.set_tick_ms(old_ms)
    out = REPO / "results" / "live" / f"aggression-{datetime.now():%Y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"args": vars(args), "runs": results}, indent=1))
    print(f"saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
