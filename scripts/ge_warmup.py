"""Gate G3 and the fixed price table: let the ambient bots trade, logging the GE as they go.

Decision (Caleb, 2026-10-05): the fixed price table used for net worth is a snapshot of the GE price
index after the bots have traded for 10 game-hours, starting from a freshly seeded GE.

Fresh GE: stop the server, move server/Server/data/eco/grandexchange.db aside, start the server
with worldprops/rl.conf (it re-seeds the price index at startup), then run:

    uv run python scripts/ge_warmup.py [--hours 10] [--tick-ms 15] [--sample-minutes 30]

Writes the full time series to results/ge/ and the final snapshot to data/prices_v1.csv with
provenance in data/prices_v1.meta.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from rlscape.bridge import DEFAULT_PORT, BridgeClient

TICKS_PER_GAME_MINUTE = 100  # 600 ms ticks


def server_commit() -> str:
    try:
        return subprocess.run(
            ["git", "-C", "server", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "Unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--hours", type=float, default=10.0, help="game-hours of bot trading")
    parser.add_argument("--tick-ms", type=int, default=15)
    parser.add_argument("--sample-minutes", type=int, default=30, help="game-minutes between snapshots")
    parser.add_argument("--prices-out", type=Path, default=Path("data/prices_v1.csv"))
    args = parser.parse_args()

    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    series_dir = Path("results/ge")
    series_dir.mkdir(parents=True, exist_ok=True)
    prices_path = series_dir / f"warmup_{stamp}_prices.csv"
    stock_path = series_dir / f"warmup_{stamp}_bot_stock.csv"
    summary_path = series_dir / f"warmup_{stamp}_summary.csv"

    total_ticks = int(args.hours * 60 * TICKS_PER_GAME_MINUTE)
    sample_ticks = args.sample_minutes * TICKS_PER_GAME_MINUTE
    started = datetime.now().astimezone()
    wall_start = time.perf_counter()

    with BridgeClient(port=args.port) as client, \
            prices_path.open("w", newline="") as pf, stock_path.open("w", newline="") as sf, \
            summary_path.open("w", newline="") as mf:
        prices_csv, stock_csv, summary_csv = csv.writer(pf), csv.writer(sf), csv.writer(mf)
        prices_csv.writerow(["game_hours", "item_id", "value", "unique_trades"])
        stock_csv.writerow(["game_hours", "item_id", "amount"])
        summary_csv.writerow(["game_hours", "tick", "items_priced", "items_changed", "items_ever_traded",
                              "bot_stock_items", "bot_stock_units", "open_player_offers", "wall_seconds"])

        client.set_tick_ms(args.tick_ms)
        start_tick = client.wait(0)
        initial: dict[int, int] = {}
        snapshot: dict = {}
        elapsed = 0
        while True:
            snapshot = client.ge_snapshot()
            tick = snapshot["tick"]
            elapsed = tick - start_tick
            hours = round(elapsed / (60 * TICKS_PER_GAME_MINUTE), 3)
            if not initial:
                initial = {p["id"]: p["value"] for p in snapshot["prices"]}
            for p in snapshot["prices"]:
                prices_csv.writerow([hours, p["id"], p["value"], p["unique_trades"]])
            for s in snapshot["bot_stock"]:
                stock_csv.writerow([hours, s["id"], s["amount"]])
            summary = [
                hours, tick, len(snapshot["prices"]),
                sum(1 for p in snapshot["prices"] if p["value"] != initial.get(p["id"])),
                sum(1 for p in snapshot["prices"] if p["unique_trades"] > 0),
                len(snapshot["bot_stock"]), sum(s["amount"] for s in snapshot["bot_stock"]),
                snapshot["open_player_offers"], round(time.perf_counter() - wall_start, 1),
            ]
            summary_csv.writerow(summary)
            mf.flush()
            print(dict(zip(["game_hours", "tick", "items_priced", "items_changed", "items_ever_traded",
                            "bot_stock_items", "bot_stock_units", "open_player_offers", "wall_seconds"], summary)),
                  flush=True)
            if elapsed >= total_ticks:
                break
            client.wait(min(sample_ticks, total_ticks - elapsed))
        client.set_tick_ms(600)

    args.prices_out.parent.mkdir(parents=True, exist_ok=True)
    with args.prices_out.open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["item_id", "name", "price"])
        for p in snapshot["prices"]:
            out.writerow([p["id"], p["name"], p["value"]])
    meta = {
        "description": "Fixed price table for net worth: GE price index after the ambient bots traded "
                       f"for {args.hours:g} game-hours from a freshly seeded GE.",
        "decision": "Caleb, 2026-10-05 (docs/decision-log.md)",
        "server_commit": server_commit(),
        "started": started.isoformat(timespec="seconds"),
        "finished": datetime.now().astimezone().isoformat(timespec="seconds"),
        "start_tick": start_tick,
        "end_tick": start_tick + elapsed,
        "game_hours": round(elapsed / (60 * TICKS_PER_GAME_MINUTE), 3),
        "tick_ms": args.tick_ms,
        "items": len(snapshot["prices"]),
        "items_changed_from_seed": sum(1 for p in snapshot["prices"] if p["value"] != initial.get(p["id"])),
        "items_ever_traded": sum(1 for p in snapshot["prices"] if p["unique_trades"] > 0),
        "time_series": [str(prices_path), str(stock_path), str(summary_path)],
    }
    args.prices_out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
