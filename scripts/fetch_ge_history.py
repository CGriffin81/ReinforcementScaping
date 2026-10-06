"""Download historical Grand Exchange prices from the RuneScape Wiki's Weird Gloop exchange API.

Decision (Caleb, 2026-10-05): freeze the GE at historical 2009 prices. 2009Scape targets game content
"in and around January 1st, 2009" (2009scape.org, About 2009Scape), so the table uses January 2009.

Every unnoted item that is tradeable in 2009Scape is requested, by its 2009 item id. The wiki's current item
list can't be used as a filter: RuneScape later re-issued many items under new ids (rune armour, for one),
but the API still serves the old ids' history. Responses are cached one file per item, so an interrupted run
resumes where it stopped.

The ``sample`` endpoint is used (about 500 evenly spaced prices across an item's whole history, ~33 KB per
item) rather than ``all`` (daily, ~445 KB per item), to keep the load on a community-run API modest.

    uv run python scripts/fetch_ge_history.py [--rate 4]
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from pathlib import Path

API = "https://api.weirdgloop.org/exchange/history/rs/sample?id={}"
USER_AGENT = "ReinforcementScaping-research (CS898BG course project; github.com/CGriffin81)"
CACHE = Path("results/ge_history/sample")
COINS = 995


def get_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def cached(path: Path) -> bool:
    """A cache file counts only if it parses; an interrupted write is fetched again."""
    try:
        json.loads(path.read_text())
        return True
    except (OSError, ValueError):
        return False


def unnoted_tradeable_ids(definitions_csv: Path) -> set[int]:
    with definitions_csv.open(newline="") as f:
        return {int(row["unnoted_id"]) for row in csv.DictReader(f)} - {COINS}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--items", type=Path, default=Path("data/item_definitions.csv"),
                        help="2009Scape item definitions (scripts/export_item_definitions.py)")
    parser.add_argument("--rate", type=float, default=4.0, help="maximum requests per second")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    wanted = sorted(unnoted_tradeable_ids(args.items))
    todo = [i for i in wanted if not cached(CACHE / f"{i}.json")]
    print(f"{len(wanted)} items to cover, {len(todo)} not cached yet", flush=True)

    interval = 1.0 / args.rate
    for n, item_id in enumerate(todo, 1):
        started = time.perf_counter()
        for attempt in range(3):
            try:
                data = get_json(API.format(item_id))
                (CACHE / f"{item_id}.json").write_text(json.dumps(data))
                break
            except Exception as e:  # network hiccups: back off and retry, then move on
                if attempt == 2:
                    print(f"failed {item_id}: {e}", flush=True)
                time.sleep(5 * (attempt + 1))
        if n % 100 == 0:
            print(f"{n}/{len(todo)}", flush=True)
        time.sleep(max(0.0, interval - (time.perf_counter() - started)))
    print("done", flush=True)


if __name__ == "__main__":
    main()
