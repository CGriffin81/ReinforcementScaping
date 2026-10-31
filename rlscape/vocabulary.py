"""The item vocabulary V (option catalog §9): 156 items, accepted by Caleb on 2026-10-30 (`docs/vocabulary-draft.md`),
and 20 fletching inputs added on 2026-10-31 by the same rule (every item the agent can buy), when Caleb brought
Fletching forward: 176.

Each item in V gets its own drop, alchemy and sell actions and its own inventory and bank features; everything else
is misc. V is fixed before training, so `data/vocabulary.csv` is frozen. `scripts/draft_vocabulary.py` regenerates
the draft it came from, not this file.
"""

from __future__ import annotations

import csv
from functools import cache
from pathlib import Path

VOCABULARY = Path(__file__).resolve().parents[1] / "data" / "vocabulary.csv"


@cache
def vocabulary() -> tuple[int, ...]:
    with VOCABULARY.open(newline="", encoding="utf-8") as f:
        return tuple(sorted(int(r["item_id"]) for r in csv.DictReader(f)))
