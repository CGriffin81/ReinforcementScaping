"""Build the 2009 GE price table, the net-worth valuation table, and the frozen GE database.

Decisions (Caleb, 2026-10-05):
  * Freeze the GE at historical 2009 prices. 2009Scape targets content "in and around January 1st, 2009",
    so the historical price is the median of the wiki's January 2009 samples; an item first tracked later
    in 2009 uses the median of its first month with data. Items with no 2009 data keep the server's seeded
    price (high-alchemy value) on the GE.
  * Value wealth at max(high alchemy - cost of a nature rune, historical 2009 GE price). The nature rune is
    priced from the same January 2009 table. The alchemy term follows the server's spell rule
    (ModernListeners.alchemize): anything tradeable or flagged alchemizable except coins, which is every item
    in this table bar coins (valued at 1).

Decision (Caleb, 2026-10-27): the frozen-price GE buyer (world.ge_frozen_buyer) only buys items with a 2009
price. The frozen database lists them in its historical_price_items table, which the server's buyer checks.

Decision (Caleb, 2026-10-27): items the GE refuses to trade (rl.conf's world.ge_blocked_items, e.g. the
anti-dragon shield, which only Duke Horacio gives out) get no GE term in the valuation and stay off the
historical list. The anti-dragon shield is therefore valued at 0.

Decision (Caleb, 2026-11-07): the GE sells Ava's devices, at prices he set (SET_PRICES), so the agent needn't learn
Draynor Manor. They're untradeable in the game, so the definitions export lacks them: their rows come from the
server's item configs. They join the frozen database as the server's ::allowge would (a price_index row) and the
historical list, so the frozen seller sells them and the frozen buyer buys them at those prices, and net worth values
them there (the alchemy spell refuses untradeable items). prices_v2's ge_price_2009 column is the frozen GE price:
the 2009 one, or a set price (source ge_set).

Inputs:  data/item_definitions.csv (scripts/export_item_definitions.py),
         results/ge_history/sample/*.json (scripts/fetch_ge_history.py),
         data/grandexchange_warmup10h.db (scripts/ge_warmup.py).
Outputs: data/ge_prices_2009.csv, data/prices_v2.csv, data/grandexchange_2009_frozen.db, plus .meta.json files.

    uv run python scripts/build_price_tables.py
"""

from __future__ import annotations

import csv
import json
import shutil
import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DEFINITIONS = Path("data/item_definitions.csv")
HISTORY = Path("results/ge_history/sample")
WARMUP_DB = Path("data/grandexchange_warmup10h.db")
GE_2009 = Path("data/ge_prices_2009.csv")
VALUATION = Path("data/prices_v2.csv")
FROZEN_DB = Path("data/grandexchange_2009_frozen.db")
RL_CONF = Path("server/Server/worldprops/rl.conf")
ITEM_CONFIGS = Path("server/Server/data/configs/item_configs.json")

# GE prices Caleb set for items the 2009 GE never traded (2026-11-07)
SET_PRICES = {10498: 2_500, 10499: 10_000}  # Ava's attractor, Ava's accumulator

COINS = 995
NATURE_RUNE = 561
TARGET_YEAR = 2009


def month_of(timestamp_ms: int) -> tuple[int, int]:
    when = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return when.year, when.month


def historical_price(points: list[dict]) -> tuple[int, int, str] | None:
    """Median price over January 2009, else over the first 2009 month with data; (price, n_points, month)."""
    by_month: dict[int, list[int]] = defaultdict(list)
    for point in points:
        year, month = month_of(point["timestamp"])
        if year == TARGET_YEAR and point.get("price"):
            by_month[month].append(point["price"])
    if not by_month:
        return None
    month = min(by_month)
    prices = by_month[month]
    return round(statistics.median(prices)), len(prices), f"{TARGET_YEAR}-{month:02d}"


def ge_blocked_items() -> set[int]:
    """world.ge_blocked_items from rl.conf, so the server's rule is the single source of truth."""
    for line in RL_CONF.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "ge_blocked_items":
            return {int(part) for part in value.strip().strip('"').split(",") if part.strip()}
    return set()


def load_definitions() -> list[dict]:
    with DEFINITIONS.open(newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key in ("id", "unnoted_id", "value", "high_alch", "low_alch"):
            row[key] = int(row[key])
        row["alchemizable"] = row["alchemizable"] == "True"
        row["tradeable"] = True  # the export lists tradeable items only
    return rows


def set_price_definitions() -> list[dict]:
    """Rows for the set-price items, which the export (tradeable items) lacks, from the server's item configs. The
    alchemy values follow ItemDefinition.getAlchemyValue: the configured one, else 60% (40%) of the value."""
    configs = {int(c["id"]): c for c in json.loads(ITEM_CONFIGS.read_text(encoding="utf-8"))
               if int(c.get("id", -1)) in SET_PRICES}
    rows = []
    for item_id in SET_PRICES:
        config = configs[item_id]
        value = int(config.get("shop_price", 0))
        rows.append({"id": item_id, "name": config["name"], "unnoted_id": item_id, "value": value,
                     "high_alch": int(config.get("high_alchemy", round(value * 0.6))),
                     "low_alch": int(config.get("low_alchemy", round(value * 0.4))),
                     "alchemizable": config.get("alchemizable") == "true",
                     "tradeable": config.get("tradeable") == "true"})
    return rows


def main() -> None:
    definitions = load_definitions() + set_price_definitions()
    names = {d["id"]: d["name"] for d in definitions}

    history: dict[int, tuple[int, int, str]] = {}
    for path in HISTORY.glob("*.json"):
        item_id = int(path.stem)
        data = json.loads(path.read_text())
        found = historical_price(data.get(str(item_id), []))
        if found:
            history[item_id] = found

    with GE_2009.open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["item_id", "name", "ge_price_2009", "samples", "month"])
        for item_id in sorted(history):
            price, n, month = history[item_id]
            out.writerow([item_id, names.get(item_id, ""), price, n, month])
    months = defaultdict(int)
    for _, _, month in history.values():
        months[month] += 1

    nature = history[NATURE_RUNE][0]
    blocked = ge_blocked_items()
    counts = defaultdict(int)
    with VALUATION.open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["item_id", "name", "unnoted_id", "high_alch", "high_alch_net",
                      "ge_price_2009", "value", "source"])
        for d in definitions:
            set_price = SET_PRICES.get(d["unnoted_id"])
            ge = set_price if set_price is not None else history.get(d["unnoted_id"], (None,))[0]
            is_blocked = d["id"] in blocked or d["unnoted_id"] in blocked
            ge_term = None if is_blocked else ge
            # the spell (ModernListeners.alchemize) takes tradeable items, and untradeable ones flagged alchemizable
            alch_net = d["high_alch"] - nature if d["tradeable"] or d["alchemizable"] else None
            if d["unnoted_id"] == COINS:
                value, source = 1, "coins"
            else:
                ge_source = "ge_set" if set_price is not None else "ge_2009"
                candidates = {k: v for k, v in (("high_alch", alch_net), (ge_source, ge_term)) if v is not None}
                if candidates:
                    source, value = max(candidates.items(), key=lambda kv: kv[1])
                    if value < 0:
                        value, source = 0, "floor_0"
                else:
                    value, source = 0, "none"
                if is_blocked and source != "high_alch":
                    source = "ge_blocked"
            counts[source] += 1
            out.writerow([d["id"], d["name"], d["unnoted_id"], d["high_alch"],
                          alch_net, ge, value, source])

    shutil.copyfile(WARMUP_DB, FROZEN_DB)
    unnoted = {d["id"]: d["unnoted_id"] for d in definitions}
    updated = kept = listed = 0
    with sqlite3.connect(FROZEN_DB) as db:
        db.execute("CREATE TABLE IF NOT EXISTS historical_price_items(item_id INTEGER PRIMARY KEY)")
        db.execute("DELETE FROM historical_price_items")
        for (item_id,) in db.execute("SELECT item_id FROM price_index").fetchall():
            ge = history.get(unnoted.get(item_id, item_id), (None,))[0]
            if ge is None:
                kept += 1
                continue
            db.execute("UPDATE price_index SET value = ?, total_value = ? WHERE item_id = ?", (ge, ge, item_id))
            if item_id not in blocked:
                db.execute("INSERT INTO historical_price_items(item_id) VALUES (?)", (item_id,))
                listed += 1
            updated += 1
        for item_id, price in SET_PRICES.items():  # as ::allowge would (PriceIndex.allowItem), at the set price
            db.execute("DELETE FROM price_index WHERE item_id = ?", (item_id,))
            db.execute("INSERT INTO price_index (item_id, value, total_value, unique_trades, last_update) "
                       "VALUES (?, ?, ?, 0, 0)", (item_id, price, price))
            db.execute("INSERT OR IGNORE INTO historical_price_items(item_id) VALUES (?)", (item_id,))
            listed += 1

    built = datetime.now().astimezone().isoformat(timespec="seconds")
    GE_2009.with_suffix(".meta.json").write_text(json.dumps({
        "description": "Historical GE prices: median of RuneScape Wiki (Weird Gloop) sampled prices in January "
                       "2009, else in the item's first 2009 month with data.",
        "source": "https://api.weirdgloop.org/exchange/history/rs/sample?id=<item>",
        "target": "2009Scape targets content in and around January 1st, 2009 (2009scape.org, About 2009Scape)",
        "built": built,
        "items_with_2009_price": len(history),
        "items_by_month": dict(sorted(months.items())),
        "items_requested": len(list(HISTORY.glob("*.json"))),
    }, indent=2) + "\n")
    VALUATION.with_suffix(".meta.json").write_text(json.dumps({
        "description": "Net-worth valuation: max(high alchemy - nature rune, historical 2009 GE price); "
                       "coins = 1; floored at 0. Alchemy applies to every tradeable item (server spell rule).",
        "decision": "Caleb, 2026-10-05 (docs/decision-log.md)",
        "nature_rune_price_2009": nature,
        "built": built,
        "items": len(definitions),
        "value_source_counts": dict(counts),
        "ge_blocked_items": sorted(blocked),
        "ge_set_prices": {str(k): v for k, v in SET_PRICES.items()},
        "ge_set_prices_decision": "Caleb, 2026-11-07: Ava's devices on the GE (ge_price_2009 holds the set price)",
        "supersedes": "data/prices_v1.csv (seeded high-alchemy values) for valuing wealth",
    }, indent=2) + "\n")
    FROZEN_DB.with_suffix(".meta.json").write_text(json.dumps({
        "description": "GE database for real-server episodes: bot stock from the 10 game-hour warm-up, price index "
                       "replaced by the historical 2009 table. Run with ge_freeze_prices = true so it never moves. "
                       "historical_price_items lists the rows with a 2009 price; the frozen-price buyer only buys those.",
        "base": str(WARMUP_DB),
        "built": built,
        "price_rows_set_to_2009": updated,
        "price_rows_kept_seeded": kept,
        "historical_price_items": listed,
        "ge_blocked_items_excluded": sorted(blocked),
        "ge_set_prices": {str(k): v for k, v in SET_PRICES.items()},
    }, indent=2) + "\n")

    print(f"2009 prices: {len(history)} items {dict(sorted(months.items()))}")
    print(f"nature rune (Jan 2009): {nature} gp")
    print(f"valuation sources: {dict(counts)}")
    print(f"frozen GE: {updated} prices set to 2009, {kept} kept at the seeded value")


if __name__ == "__main__":
    main()
