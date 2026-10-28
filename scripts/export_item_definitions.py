"""Export every tradeable item definition from the running server to data/item_definitions.csv.

Includes the values the price tables need (base value, high/low alchemy, alchemizable), whether an item
stacks in the inventory (the combat model's loot-slot count), and the noted ->
unnoted mapping, straight from the 530 cache the server loads. The ``ge_price_at_export`` column records what
the server's GE quoted at export time and is informational only.

    uv run python scripts/export_item_definitions.py
"""

from __future__ import annotations

import csv
from pathlib import Path

from rlscape.bridge import BridgeClient

OUT = Path("data/item_definitions.csv")
FIELDS = ["id", "name", "unnoted_id", "value", "high_alch", "low_alch", "alchemizable", "members", "stackable"]


def main() -> None:
    with BridgeClient() as client:
        items = client.item_definitions()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(FIELDS + ["ge_price_at_export"])
        for item in items:
            out.writerow([item[k] for k in FIELDS] + [item["ge_price"]])
    print(f"{len(items)} tradeable items written to {OUT}")


if __name__ == "__main__":
    main()
