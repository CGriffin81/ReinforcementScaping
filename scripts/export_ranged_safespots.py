"""Export each combat site's best ranged and magic safespot for the sim (rlscape.combat.safespots; Caleb, 2026-11-07,
OQ-27 (d) and OQ-34).

For every site of the sim's enemy pool (rlscape.combat.candidates.enemy_pool), the bridge's ranged_safespots finds the
tiles to shoot its monster from that it can't attack back from, by the server's own chase: this keeps the best one
for each attack range (7, 9 long-ranged, and magic's 10) and writes data/ranged_safespots.csv, a row a site and
range:
- found: 1 if it has one; then the tile;
- held: the site's monsters (spawned within the sim's SITE_RADIUS) it holds against; share: of their wandering it
  holds from, on average; steps: how far they chase before they stick, on average;
- walk: tiles from it to where their arrows land (the stuck tiles), on average; empty if there's no way there;
- threats: aggressive monsters that would pick a fresh character and reach the tile until aggression runs out;
  pickup_threats: the most, besides the one killed, whose leash covers a held monster's arrows.
The character is a fresh one (level 3), so every aggressive monster counts. It's teleported to each site's spawn
(setup only) with auto-retaliate off; a death there just respawns it, and the next teleport is tried again until
it lands. Sites already in the file are kept (--fresh
starts over), so an interrupted run picks up where it stopped; --shard I N does every Nth site for several servers
at once (RL_BRIDGE_PORT picks the server), whose files --merge puts together.

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/export_ranged_safespots.py [--shard 0 3] [--fresh]
    uv run python scripts/export_ranged_safespots.py --merge data/ranged_safespots-*.csv
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from rlscape.bridge.client import BridgeClient, BridgeError
from rlscape.combat.candidates import SITE_RADIUS, enemy_pool
from rlscape.combat.safespots import SAFESPOT_RANGES

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "ranged_safespots.csv"
TELEPORT_TRIES = 4
FRESH_HITPOINTS = 10  # a fresh character's Hitpoints level
FIELDS = ("npc_id", "name", "site_x", "site_y", "site_z", "range", "found", "tile_x", "tile_y", "tile_z", "held",
          "spawns", "share", "steps", "walk", "threats", "pickup_threats", "note")


def row(npc, site, tiles_range: int, result: dict | None, note: str = "") -> dict:
    out = {"npc_id": npc.id, "name": npc.name, "site_x": site.spawn[0], "site_y": site.spawn[1],
           "site_z": site.spawn[2], "range": tiles_range, "found": 0, "spawns": site.spawns, "note": note}
    tiles = (result or {}).get("tiles") or []
    if not tiles:
        return out
    best = tiles[0]
    against = best["against"]
    walks = [a["walk"] for a in against if a["walk"] is not None]
    out.update(found=1, tile_x=best["tile"]["x"], tile_y=best["tile"]["y"], tile_z=best["tile"]["z"],
               held=len(against), share=round(sum(a["share"] for a in against) / len(against), 3),
               steps=round(sum(a["steps"] for a in against) / len(against), 2),
               walk=round(sum(walks) / len(walks)) if walks else "", threats=len(best["threats"]),
               pickup_threats=max(len([g for g in a["pickup_threats"] if g != a["index"]]) for a in against))
    return out


def key(r: dict) -> tuple:
    return int(r["npc_id"]), int(r["site_x"]), int(r["site_y"]), int(r["site_z"]), int(r["range"])


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows, key=key))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--shard", type=int, nargs=2, metavar=("I", "N"), default=(0, 1))
    parser.add_argument("--fresh", action="store_true", help="start over instead of keeping the sites done")
    parser.add_argument("--merge", type=Path, nargs="+", help="merge shard files into data/ranged_safespots.csv")
    args = parser.parse_args()
    if args.merge:
        rows = {key(r): r for path in [OUT, *args.merge] for r in read(path)}
        write(OUT, list(rows.values()))
        print(f"{len(rows)} rows in {OUT.relative_to(REPO)}")
        return
    i, n = args.shard
    out = OUT if n == 1 else OUT.with_name(f"ranged_safespots-{i}of{n}.csv")
    done = {} if args.fresh else {key(r): r for r in read(out)}
    sites = [(e.npc, s) for e in enemy_pool() for s in e.sites][i::n]
    started, rows = time.time(), dict(done)
    with BridgeClient(timeout=900) as client:
        old_ms = client.ping()["tick_ms"]
        client.set_tick_ms(50)
        uid = client.spawn()["uid"]
        try:
            client.set_retaliate(uid, False)
            for k, (npc, site) in enumerate(sites):
                wanted = [r for r in SAFESPOT_RANGES if (npc.id, *site.spawn, r) not in done]
                if not wanted:
                    continue
                # hitpoints refilled (its own level, so its combat level, which decides the threats, stays), so it
                # outlasts the searches at a dangerous site
                client.debug_set_levels(uid, {"hitpoints": FRESH_HITPOINTS})
                for _ in range(TELEPORT_TRIES):  # a death at the last site leaves it respawning for a while
                    client.debug_teleport(uid, *site.spawn)
                    client.wait(1)
                    here = client.state(uid)["location"]
                    if (here["z"] == site.spawn[2] and abs(here["x"] - site.spawn[0]) <= 2
                            and abs(here["y"] - site.spawn[1]) <= 2):
                        break
                    client.wait(8)
                for tiles_range in wanted:
                    try:
                        result = client.ranged_safespots(uid, npc.name, ids=[npc.id], radius=SITE_RADIUS,
                                                         range=tiles_range, limit=1)
                        r = row(npc, site, tiles_range, result)
                    except BridgeError as e:
                        r = row(npc, site, tiles_range, None, note=str(e)[:120])
                    rows[key(r)] = r
                if k % 25 == 0:
                    write(out, list(rows.values()))
                    print(f"{k + 1}/{len(sites)} sites, {time.time() - started:.0f} s", flush=True)
        finally:
            client.despawn(uid)
            client.set_tick_ms(old_ms)
    write(out, list(rows.values()))
    found = sum(1 for r in rows.values() if str(r["found"]) == "1")
    print(f"{len(rows)} rows ({found} with a safespot) in {out.relative_to(REPO)}, {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
