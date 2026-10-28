"""Export every cache NPC definition from the running server to data/npc_definitions.csv.

npc_configs.json holds placeholder stats (attack / strength / defence 1, 10 HP, no bonuses) for hundreds of NPCs,
including real monsters. The cache's combat level, the one the game client shows, and its "Attack" option are the
independent check the enemy pool uses (rlscape/combat/candidates.py).

    uv run python scripts/export_npc_definitions.py
"""

from __future__ import annotations

import csv
from pathlib import Path

from rlscape.bridge import BridgeClient

OUT = Path("data/npc_definitions.csv")
FIELDS = ["id", "name", "combat_level", "attackable", "size"]


def main() -> None:
    with BridgeClient() as client:
        npcs = client.npc_definitions()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(FIELDS)
        for npc in npcs:
            out.writerow([npc[k] for k in FIELDS])
    print(f"{len(npcs)} NPC definitions written to {OUT} ({sum(n['attackable'] for n in npcs)} attackable)")


if __name__ == "__main__":
    main()
