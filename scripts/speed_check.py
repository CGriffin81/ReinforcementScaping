"""The gate's speed check (env contract §7; Caleb, 2026-11-06, OQ-21): the same calibration cases on the server at
calibration's tick (50 ms, 12x real time) and at the real one (600 ms) must agree within their run-to-run noise.

It compares two results files of one kind, written by scripts/calibrate.py (gathering), scripts/calibrate_combat.py
(combat) or scripts/validate_travel.py (travel), case by case:
- gathering and combat: each run's XP/hr (XP over its ticks). They agree when the means differ by at most two
  standard errors of the difference (TOLERANCE_SE), from each side's runs.
- travel: each trip's ticks. A trip is run once at each speed, so there's no spread to judge by: they agree within
  TRAVEL_TOLERANCE.

Usage, after running the same cases with --tick-ms 50 and --tick-ms 600:
    uv run python scripts/speed_check.py FAST.json SLOW.json [FAST.json SLOW.json ...]
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TICKS_PER_HOUR = 6000
TOLERANCE_SE = 2.0
TRAVEL_TOLERANCE = 0.05


def run_xp(run: dict) -> float:
    """A run's XP: gathering records it whole, combat per skill."""
    return run["xp"] if "xp" in run else sum(v for k, v in run.items() if k.startswith("xp_"))


def per_hour(runs: list[dict]) -> list[float]:
    return [run_xp(r) / r["ticks"] * TICKS_PER_HOUR for r in runs if r["ticks"] > 0]


def compare_runs(fast: list[float], slow: list[float]) -> dict:
    mean_f, mean_s = statistics.fmean(fast), statistics.fmean(slow)
    var = lambda xs: statistics.variance(xs) / len(xs) if len(xs) > 1 else 0.0  # noqa: E731
    se = (var(fast) + var(slow)) ** 0.5
    return {"fast_xp_per_hour": mean_f, "slow_xp_per_hour": mean_s, "slow_over_fast": mean_s / mean_f if mean_f else None,
            "se_difference": se, "agrees": abs(mean_s - mean_f) <= TOLERANCE_SE * se,
            "runs": [len(fast), len(slow)]}


def compare(fast_path: Path, slow_path: Path) -> list[dict]:
    fast, slow = json.loads(fast_path.read_text()), json.loads(slow_path.read_text())
    if "trips" in fast:
        slow_trips = {t["trip"]: t for t in slow["trips"]}
        out = []
        for trip in fast["trips"]:
            other = slow_trips.get(trip["trip"])
            if other is None or not trip.get("server_ticks") or not other.get("server_ticks"):
                continue
            ratio = other["server_ticks"] / trip["server_ticks"]
            out.append({"case": trip["trip"], "fast_ticks": trip["server_ticks"], "slow_ticks": other["server_ticks"],
                        "slow_over_fast": ratio, "agrees": abs(ratio - 1) <= TRAVEL_TOLERANCE})
        return out
    key = lambda case: json.dumps(case, sort_keys=True)  # noqa: E731
    slow_cases = {key(c["case"]): c for c in slow["cases"]}
    out = []
    for case in fast["cases"]:
        other = slow_cases.get(key(case["case"]))
        if other is None:
            continue
        label = case["case"].get("option_id") or f'{case["case"]["combat_class"]} {case["case"]["name"]}'
        out.append({"case": f'{label}, band {case["case"]["band"]}',
                    **compare_runs(per_hour(case["server_runs"]), per_hour(other["server_runs"]))})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", type=Path, nargs="+", help="pairs: the 50 ms file, then the 600 ms file")
    args = parser.parse_args()
    if len(args.files) % 2:
        parser.error("give the files in pairs")
    rows = []
    for fast, slow in zip(args.files[::2], args.files[1::2]):
        for row in compare(fast, slow):
            rows.append({"fast": str(fast), "slow": str(slow), **row})
            ratio = row["slow_over_fast"]
            print(f'{"ok  " if row["agrees"] else "MISS"} {row["case"]}: 600 ms over 50 ms '
                  f'{ratio:.2f}' if ratio is not None else f'{row["case"]}: no XP')
    out = REPO / "results" / "calibration" / f"speed-check-{datetime.now():%Y%m%d-%H%M}.json"
    out.write_text(json.dumps({"files": [str(f) for f in args.files], "rows": rows}, indent=1))
    print(f"{sum(r['agrees'] for r in rows)} of {len(rows)} agree; saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
