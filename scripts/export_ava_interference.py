"""Export the chest armour that stops Ava's devices working, from the running server, to data/ava_interference.csv.

The server's rule (AvasDevice.isInterfered and RangeSwingHandler.getDropRate): a worn device saves no ammunition (and
attracts nothing) while the chest piece's male worn model is one of AvasDevice.metalBodies. Only the chest slot
counts: metal helms, legs and shields don't interfere. The models come from the 530 cache, through the bridge's
item_definitions (tradeable items; every metal chest piece is tradeable), so the sim reads the server's own list.

    uv run python scripts/export_ava_interference.py
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from rlscape.bridge import BridgeClient
from rlscape.gamedata import server as gd

OUT = Path("data/ava_interference.csv")
DEVICE = gd.SERVER_CONTENT / "region" / "misthalin" / "draynor" / "quest" / "anma" / "AvasDevice.kt"
CHEST = 4  # EquipmentContainer.SLOT_CHEST


def metal_bodies() -> frozenset[int]:
    """AvasDevice.metalBodies: the chest models that interfere."""
    found = re.search(r"val metalBodies = intArrayOf\(([^)]*)\)", DEVICE.read_text(encoding="utf-8"))
    return frozenset(int(m) for m in found.group(1).split(","))


def main() -> None:
    models, items = metal_bodies(), gd.items()
    with BridgeClient() as client:
        definitions = client.item_definitions()
    rows = sorted((d["id"], d["name"], d["worn_model"]) for d in definitions
                  if d["worn_model"] in models and items.get(d["id"]) is not None
                  and items[d["id"]].equipment_slot == CHEST)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        out = csv.writer(f)
        out.writerow(["item_id", "name", "worn_model"])
        out.writerows(rows)
    print(f"{len(rows)} interfering chest pieces (models {sorted(models)}) written to {OUT}")


if __name__ == "__main__":
    main()
