"""The gate's speed check (env contract §7; Caleb, 2026-11-06, OQ-21): the same calibration cases on the server at
calibration's tick (50 ms, 12x real time) and at the real one (600 ms) must agree within their run-to-run noise.

It compares two results files of one kind, case by case. The kinds, and the scripts that write them:
- **Gathering, combat and Barbarian Fishing** (scripts/calibrate.py, calibrate_combat.py, calibrate_barbfishing.py):
  each run's XP/hr (XP over its ticks; per skill, summed). Combat also compares each run's food eaten an hour.
- **An Agility course** (scripts/measure_agility.py): each whole lap's XP/hr.
- **Travel** (scripts/validate_travel.py): each trip's ticks.
- **Crafting and Herblore loads** (scripts/calibrate_crafting.py, calibrate_herblore.py): each run's ticks to the last
  product.
- **Runecrafting at the ruins** (scripts/calibrate_runecrafting.py): each run's ticks entering, and inside (the walks,
  the crafting and the portal), a rune at a time; with --tiaras, the ticks between tiaras.
- **Whole Abyss trips** (scripts/measure_abyss.py --trips): each trip's server ticks over the sim's own estimate for
  that trip. The landing is random, and the sim's estimate is for the actual landing, so the ratio pairs them. All
  the runes are pooled.

When they agree:
- XP/hr, laps and food: the means differ by at most two standard errors of the difference (TOLERANCE_SE), from each
  side's runs.
- Travel: a trip is run once at each speed, so there's no spread to judge by. The ticks agree within
  TRAVEL_TOLERANCE.
- The other timings (loads, the ruins, the tiaras, Abyss trips): within two standard errors, or within
  TIMING_TOLERANCE where the runs have little spread. A load can take the same ticks every run, giving a standard
  error of 0.

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
TIMING_TOLERANCE = TRAVEL_TOLERANCE


def run_xp(run: dict) -> float:
    """A run's XP: gathering records it whole, combat per skill, Barbarian Fishing per skill in a dict."""
    if "xp" in run:
        return sum(run["xp"].values()) if isinstance(run["xp"], dict) else run["xp"]
    return sum(v for k, v in run.items() if k.startswith("xp_"))


def label(case: dict) -> str:
    if "option_id" in case:
        return f'{case["option_id"]}, band {case["band"]}'
    if "case_id" in case:
        return f'{case["case_id"]}, band {case["band"]}'
    if "combat_class" in case:
        return f'{case["combat_class"]} {case["name"]}, band {case["band"]}'
    fields = ", ".join(f"{k} {v}" for k, v in case.items())
    return f"barb_fish at {fields}" if set(case) == {"fishing", "agility", "strength"} else fields


def per_hour(runs: list[dict]) -> list[float]:
    return [run_xp(r) / r["ticks"] * TICKS_PER_HOUR for r in runs if r["ticks"] > 0]


def food_per_hour(runs: list[dict]) -> list[float]:
    return [r["eaten"] / r["ticks"] * TICKS_PER_HOUR for r in runs if r["ticks"] > 0]


def compare_means(fast: list[float], slow: list[float], measure: str, floor: float = 0.0) -> dict:
    """The two sides' means agree within TOLERANCE_SE standard errors of their difference, or within `floor` of the
    fast side's mean (a share of it), whichever is wider."""
    mean_f, mean_s = statistics.fmean(fast), statistics.fmean(slow)
    var = lambda xs: statistics.variance(xs) / len(xs) if len(xs) > 1 else 0.0  # noqa: E731
    se = (var(fast) + var(slow)) ** 0.5
    return {"measure": measure, "fast_mean": mean_f, "slow_mean": mean_s,
            "slow_over_fast": mean_s / mean_f if mean_f else None, "se_difference": se,
            "agrees": abs(mean_s - mean_f) <= max(TOLERANCE_SE * se, floor * abs(mean_f)),
            "runs": [len(fast), len(slow)]}


def compare_runs(fast: list[float], slow: list[float]) -> dict:
    return compare_means(fast, slow, "xp_per_hour")


def compare_timings(fast: list[float], slow: list[float], measure: str = "ticks") -> dict:
    return compare_means(fast, slow, measure, TIMING_TOLERANCE)


def compare_runecrafting(fast: dict, slow: dict) -> list[dict]:
    """The ruins: each rune's entering and inside ticks (runs that got outside again); the tiaras' ticks apart."""
    out = []
    for rune, row in fast["rc"].items():
        other = slow["rc"].get(rune)
        if other is None:
            continue
        for measure in ("enter", "inside"):
            f = [r[measure] for r in row["runs"] if "inside" in r]
            s = [r[measure] for r in other["runs"] if "inside" in r]
            if f and s:
                out.append({"case": f"rc_{rune} {measure}", **compare_timings(f, s, f"{measure}_ticks")})
    if "tiara" in fast and "tiara" in slow:
        each = lambda d: [r["each"] for r in d["tiara"]["runs"] if r["each"] is not None]  # noqa: E731
        if each(fast) and each(slow):
            out.append({"case": "make_tiara_air, ticks between tiaras",
                        **compare_timings(each(fast), each(slow), "ticks_each")})
    return out


def compare_abyss_trips(fast: dict, slow: dict) -> list[dict]:
    """Whole Abyss trips: each trip's server ticks over the sim's estimate for the same landing, all runes pooled."""
    ratio = lambda d: [t["server"] / t["sim"] for t in d["trips"] if t.get("server") and t.get("sim")]  # noqa: E731
    f, s = ratio(fast), ratio(slow)
    if not f or not s:
        return []
    return [{"case": "abyss_rc trips, all runes (server over the sim's estimate)",
             **compare_timings(f, s, "server_over_sim")}]


def compare_cases(fast: dict, slow: dict) -> list[dict]:
    """The files that list cases with their server runs: gathering, combat, Barbarian Fishing, Crafting, Herblore."""
    key = lambda case: json.dumps(case, sort_keys=True)  # noqa: E731
    slow_cases = {key(c["case"]): c for c in slow["cases"]}
    out = []
    for case in fast["cases"]:
        other = slow_cases.get(key(case["case"]))
        if other is None:
            continue
        name, runs_f, runs_s = label(case["case"]), case["server_runs"], other["server_runs"]
        if "case_id" in case["case"]:  # a Crafting or Herblore load: its ticks
            out.append({"case": name, **compare_timings([r["ticks"] for r in runs_f], [r["ticks"] for r in runs_s])})
            continue
        out.append({"case": name, **compare_runs(per_hour(runs_f), per_hour(runs_s))})
        if "combat_class" in case["case"] and all("eaten" in r for r in runs_f + runs_s):
            out.append({"case": f"{name} (food/hr)",
                        **compare_means(food_per_hour(runs_f), food_per_hour(runs_s), "food_per_hour")})
    return out


def compare(fast_path: Path, slow_path: Path) -> list[dict]:
    fast, slow = json.loads(fast_path.read_text()), json.loads(slow_path.read_text())
    if "rc" in fast:
        return compare_runecrafting(fast, slow)
    if fast.get("trips") and "rune" in fast["trips"][0]:
        return compare_abyss_trips(fast, slow)
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
    if "laps" in fast:  # one course at one level a file: its whole laps
        laps = lambda d: [lap for lap in d["laps"] if not lap["abandoned"]]  # noqa: E731
        return [{"case": f'{fast["course"]} laps, Agility {fast["agility"]}',
                 **compare_runs(per_hour(laps(fast)), per_hour(laps(slow)))}]
    return compare_cases(fast, slow)


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
                  f'{ratio:.2f}' if ratio is not None else f'{row["case"]}: nothing measured')
    out = REPO / "results" / "calibration" / f"speed-check-{datetime.now():%Y%m%d-%H%M}.json"
    out.write_text(json.dumps({"files": [str(f) for f in args.files], "rows": rows}, indent=1))
    print(f"{sum(r['agrees'] for r in rows)} of {len(rows)} agree; saved {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
