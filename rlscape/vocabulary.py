"""The item vocabulary V (option catalog §9): 156 items, accepted by Caleb on 2026-10-30 (`docs/vocabulary-draft.md`);
20 fletching inputs added on 2026-10-31 by the same rule (every item the agent can buy), when Caleb brought Fletching
forward; 16 on 2026-11-06, which the rule proposes once every quest the server has is complete and the anti-dragon
shield is bought on the GE (Caleb); the 6 quest-gear buys of the same day (OQ-24); 5 the rule proposes once the
drop tables' shared sub-tables are modelled (Caleb); the 11 four-dose potions bought on 2026-11-06 and 07 (OQ-25);
Ava's attractor and accumulator, bought on the GE (Caleb, 2026-11-07); and every tradeable crossbow and bolt on
the 2009 GE, 63 more (Caleb, 2026-11-07; mithril bolts were in already); and Crafting's inputs, 18 not in it yet,
Herblore's, 51, and Runecrafting's, 19: the essence, talismans and tiaras (sim v1, OQ-2's Choice I (a), Caleb,
2026-11-08: the inputs the agent buys or holds): 367.
Nothing has been taken out.

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
