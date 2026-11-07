"""List the places the sim travels between, for the planner's table (rlscape/routes.py), and build the table.

The places: banks, stations, the Grand Exchange, the spawn, the gates walks pass, where teleports and boats arrive and
boats are boarded, every catalog option's tile (sites, fishing spots, thieving targets, shops) and every combat site; and, so that nothing the sim does is left out, every
tile the sim walked to or estimated a walk to over a few episodes of each baseline policy. Writes
data/travel/places.csv (committed) and builds data/travel/places.npz (local, a few minutes). A tile not listed still
gets its planned walk, searched when the sim first asks for it.

Usage:
    uv run python scripts/build_travel_places.py [--seeds 3]
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import rlscape.travel as travel
from rlscape.combat.candidates import enemy_pool
from rlscape.gamedata import server as gd
from rlscape.gamedata.transports import transports
from rlscape.routes import DATA, place_tiles, places
from rlscape.sim import build_catalog
from rlscape.sim import movement
from rlscape.sim.economy import GE_TILE
from rlscape.sim.state import SPAWN

REPO = Path(__file__).resolve().parent.parent
POLICIES = ("random", "greedy_xp", "greedy_wealth", "scripted_guide")


def listed() -> set[tuple[int, int, int]]:
    tiles = {(b.x, b.y, b.plane) for b in gd.banks()} | {s.tile for s in gd.stations()}
    tiles |= {GE_TILE, SPAWN, *movement.GATES}
    tiles |= {tile for t in transports() for tile in (t.end, t.start, t.land) if tile is not None}  # teleports, boats
    tiles |= {site.spawn for entry in enemy_pool() for site in entry.sites}
    spawns = gd.spawns()  # thieving looks for the nearest spawn of its target, any of them
    tiles |= {tuple(t) for target in gd.pickpocket_targets().values() for npc in target.npc_ids
              for t in spawns.get(npc, ())}
    for option in build_catalog():
        for attr in ("tile", "start"):
            if isinstance(getattr(option, attr, None), tuple):
                tiles.add(getattr(option, attr))
        if hasattr(option, "site") and hasattr(option.site, "tile"):
            tiles.add(option.site.tile)
        tiles.update(getattr(option, "spots", ()))
    return tiles


def walked(seeds: int) -> set[tuple[int, int, int]]:
    """Every tile a walk or a walk's estimate touched over the baselines' episodes, on the planned routes as they
    stand (with the table built so far; run again after a build to catch what the new routes lead to)."""
    from rlscape.envs.sim_env import SimEnv
    from rlscape.eval.harness import POLICIES as MAKE, play

    seen: set[tuple[int, int, int]] = set()
    real = travel.path

    def path(a, b):
        seen.update((tuple(int(v) for v in a), tuple(int(v) for v in b)))
        return real(a, b)

    travel.path = movement.path = path
    try:
        for name in POLICIES:
            for seed in range(seeds):
                play(SimEnv(), MAKE[name](), seed)
    finally:
        travel.path = movement.path = real
    return seen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seeds", type=int, default=3)
    args = parser.parse_args()
    start = time.time()
    tiles = sorted(listed() | walked(args.seeds) | set(place_tiles()))
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / "places.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x", "y", "z"])
        writer.writerows(tiles)
    print(f"{len(tiles)} places listed ({time.time() - start:.0f} s); building the table")
    places.cache_clear()
    table = places()
    print(f"table of {len(table.nodes)} anchors in {time.time() - start:.0f} s -> "
          f"{(DATA / 'places.npz').relative_to(REPO)}")


if __name__ == "__main__":
    main()
