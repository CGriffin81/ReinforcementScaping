"""Export the server's collision map of the surface for the travel planner (rlscape/routes.py).

The bridge's debug_collision gives each tile's collision flags (RegionManager.getClippingFlag) and the area's doors and
gates; this asks for it a map region (64 x 64 tiles) at a time over the box the sim travels in, and writes
data/travel/collision.npz (the flags, int32, rows from the box's south edge) and data/travel/doors.csv. Doors are in
their spawned state (most closed); the planner lets a route open them.

Usage, with the server running (worldprops/rl.conf):
    uv run python scripts/export_collision.py
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from rlscape.bridge.client import BridgeClient

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "travel"
BOX = (2304, 2688, 3839, 4031)  # x0, y0, x1, y1: the mainland, the Wilderness and Morytania (map regions 36-59, 42-62)
REGION = 64


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--box", type=int, nargs=4, default=BOX, metavar=("X0", "Y0", "X1", "Y1"))
    args = parser.parse_args()
    x0, y0, x1, y1 = args.box
    assert x0 % REGION == 0 and y0 % REGION == 0 and (x1 + 1) % REGION == 0 and (y1 + 1) % REGION == 0, "whole regions"
    flags = np.full((y1 - y0 + 1, x1 - x0 + 1), -1, dtype=np.int32)
    doors = []
    with BridgeClient(timeout=600) as client:
        for ry in range(y0, y1 + 1, REGION):
            for rx in range(x0, x1 + 1, REGION):
                part = client.debug_collision(rx, ry, rx + REGION - 1, ry + REGION - 1, 0)
                flags[ry - y0:ry - y0 + REGION, rx - x0:rx - x0 + REGION] = np.array(
                    part["flags"], dtype=np.int64).astype(np.int32).reshape(REGION, REGION)
                doors += part["doors"]
            print(f"rows to y {ry + REGION - 1}: {len(doors)} doors so far")
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "collision.npz", flags=flags, origin=np.array([x0, y0]))
    with open(OUT / "doors.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "x", "y", "type", "rotation"])
        writer.writeheader()
        writer.writerows(sorted(doors, key=lambda d: (d["y"], d["x"], d["id"])))
    unloaded = int((flags == -1).sum())
    print(f"saved {OUT.relative_to(REPO)}: {flags.shape[1]} x {flags.shape[0]} tiles ({unloaded} with no map), "
          f"{len(doors)} doors and gates")


if __name__ == "__main__":
    main()
