"""The sim-to-real table's data: every calibration case's latest server runs against the frozen sim, re-simulated with
no server, into the committed summary that scripts/figures.py builds the table from.

Caleb, 2026-11-12 (`m002-sim-to-real`): the table compares the server with sim-v1.2, the sim every experiment trains
on, not with the sim of each calibration's day (Oct 31 to Nov 9; v1's last changes, v1.1's directional walks and
v1.2's fletch slot came after); the report shows a table per family and every case in an appendix. The gate is env
contract §7's: each calibrated option's XP/hr, gp/hr and duration within ±20% of the server's, gp/hr taken by its
parts where rare drops make up the loot (OQ-20 (a): the drop tables item by item, the looting through kills/hr).

The server's runs come from results/calibration/ (git-ignored), as each family's runner saved them. Per family,
FAMILIES names the files that hold its results (the ones the decision log reports), and a case's row comes from the
last of them that measured it (they're listed oldest first, but for a rerun the log prefers). Left out: the 600 ms
reruns (the speed check's, copied as scripts/speed_check.py measured them), earlier re-simulations (`-resim`,
`-rejudged`), runs the decision log superseded, and measurements that fitted the sim's inputs rather than test an
option (Agility's course entries and spike pit, the shortcuts' own crossings, the travel constants, the essence
pouches, the Abyss's failed tries). The sim's side is each runner's own sim function, called now, from the same start
as the server run, with SIM_RUNS seeds (0, 1, ...); the server's rates are each runner's own on the stored runs.

Writes to --out (default results/summary/sim-to-real/):
- `cases.csv`: one row per case and metric: the family, the case and its band, the metric, whether it's on the gate
  (GATED), the server's and the sim's values, sim over server, within the gate, the runs on each side, the server
  runs' date and file, sim over server as calibrated then, and a note (NOTES, or what the re-simulation found);
- `drops.csv`: the drop tables (OQ-20 (a)): per monster, the server's kills, the items the sim's sampler checks and
  those whose server count falls in its central 99%, and the gp a kill from items the sim never drops;
- `speed_check.csv`: the speed check (OQ-21): each case's measure at 50 ms and at 600 ms ticks, both on the server;
- `config.json`: the commit, whether the tree was clean, the sim tag the commit descends from, SIM_RUNS, and each
  source file with its SHA-256;
- `README.md`: the family table (rlscape/analysis/sim_to_real.py), and how the cases were chosen.

Into results/summary/ it refuses a tree with uncommitted changes, whose SHA wouldn't reproduce the summary, unless
--allow-dirty (as scripts/publish_summary.py does).

Usage:
    uv run python scripts/sim_to_real.py
    uv run python scripts/sim_to_real.py --families gathering combat --out results/summary/sim-to-real
"""

from __future__ import annotations

import argparse
import csv
import functools
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
CALIBRATION = REPO / "results" / "calibration"
GATE = 0.2  # env contract §7
SIM_RUNS = 200  # the runners' default; herblore's sim is deterministic, and so are the timed families' (one run)
SIM_TAG = "sim-v1.2"
COLUMNS = ("family", "case", "band", "metric", "gated", "server", "sim", "sim_over_server", "within_gate",
           "server_runs", "sim_runs", "measured", "source", "sim_over_server_then", "note")

# The metrics on the gate, per family: XP/hr, gp/hr (or what it's made of) and duration (env contract §7). The other
# metrics a runner compares are kept, marked not gated. Combat's gp/hr is gated by its parts (OQ-20 (a)): drops.csv
# and kills/hr; its food an hour is the runner's check on the danger model.
GATED = {
    "gathering": {"xp_per_hour", "items_per_hour", "ticks_to_full"},
    "processing": {"xp_per_hour", "ticks", "xp"},
    "crafting": {"xp_per_hour", "made_per_hour", "ticks", "made"},
    "herblore": {"xp_per_hour", "made_per_hour", "ticks", "made"},
    "thieving": {"xp_per_hour", "gp_per_hour"},
    "barbfishing": {"fishing_xp_per_hour", "agility_xp_per_hour", "strength_xp_per_hour", "catches_per_hour"},
    "combat": {"xp_per_hour", "kills_per_hour", "ticks"},
    "agility": {"xp_per_hour"},
    "runecrafting": {"enter_ticks", "inside_ticks", "ticks_a_tiara"},
    "travel": {"ticks"},
    "abyss": {"ticks", "expected_ticks", "outer_ticks", "teleport_ticks", "hp_lost"},
}

# What the decision log says of a case outside the gate (family, case, band) -> the note.
NOTES = {
    ("gathering", "fish_shrimp", 1): "dies at Draynor in 9 of 10 server runs (its dark wizards); the server run counts "
                                     "the catch at 0 hitpoints, the sim's after its death (DeathTask keeps 3 items), "
                                     "so XP/hr (1.09) is the measure (decision log, 2026-11-05)",
    ("thieving", "pickpocket_heroes", 81): "the heroes' table pays mostly in rare items, which 3 runs can't settle "
                                           "(decision log, 2026-11-07; OQ-20)",
    ("combat", "melee Abyssal leech (none loot)", 61): "a documented gap (OQ-51 (a)): the crowd round the leeches "
                                                       "isn't thinned by killing them",
    ("combat", "magic Poison spider (none loot)", 31): "OQ-35's case with neighbours; the food runs out in about "
                                                       "300 ticks (decision log, 2026-11-08)",
    ("combat", "ranged Abyssal demon (valuable loot)", 91): "borderline before (1.19), tipped by the server's noise "
                                                            "after the region fix (decision log, 2026-11-08)",
    ("combat", "melee Experiment (none loot)", 91): "the sim's XP/hr rose 14% with its changes after the stored run "
                                                    "(decision log, 2026-11-08)",
    ("combat", "melee Abyssal walker (none loot)", 91): "fitted on these runs by the time to run out of food (1.02); "
                                                        "this is the mean run's length, and one of the five server "
                                                        "runs didn't run out (decision log, 2026-11-09)",
    ("combat", "magic Black Knight (valuable loot)", 1): "not in the decision log, which gave this case's XP/hr (1.06) "
                                                        "after OQ-47 (c)",
    ("agility", "barbarian course laps", 15): "run to sample the course's falls, not reported against the gate then "
                                              "(decision log, 2026-11-08)",
    ("travel", "Varrock east bank to Al Kharid, paying the toll (check set)", ""):
        "not in the decision log: the server's walk from Lumbridge took 178 ticks on 2026-11-06 (the same at 600 ms) "
        "against 66 on 2026-11-01 (0.95 then), after every quest was complete from the start (free passage at the "
        "toll gate)",
    ("travel", "out of the Abyss from its north (abyss set)", ""): "starts beside the passage (decision log, "
                                                                   "2026-11-09)",
    ("abyss", "hitpoints lost in the outer ring (Defence 20)", ""): "the check at Defence 20, \"a small, noisy "
                                                                     "sample\"; Defence 40, the fit, 0.99 (decision "
                                                                     "log, 2026-11-08)",
}


@functools.cache
def runner(name: str):
    """A calibration runner in scripts/, imported once as a module (each guards its main)."""
    spec = importlib.util.spec_from_file_location(f"_calibration_{name}", REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up there
    spec.loader.exec_module(module)
    return module


def tuples(value: Any) -> Any:
    """JSON lists back to the tuples the runners' frozen Case dataclasses hold."""
    return tuple(tuples(v) for v in value) if isinstance(value, list) else value


def stamp(name: str) -> str:
    """A results file's date, from its name: `<family>-YYYYMMDD-HHMM...json`."""
    digits = name.split("-2026", 1)[1][:9]
    return datetime.strptime("2026" + digits, "%Y%m%d-%H%M").strftime("%Y-%m-%d %H:%M")


def mean(values: Iterable[float]) -> float:
    return float(np.mean(list(values)))


@dataclass
class Row:
    case: str
    band: int | str
    compare: dict[str, dict[str, Any]]  # metric -> {"server", "sim"}, as the runner's compare gives them
    server_runs: int
    sim_runs: int
    note: str = ""
    then: dict[str, float] | None = None  # sim over server as calibrated, where the runner kept it otherwise


def pair(server: float, sim: float) -> dict[str, float]:
    return {"server": server, "sim": sim}


@dataclass
class Family:
    name: str
    files: list[str]  # results/calibration/ names; a case's row comes from the last of them that measured it
    key: Callable[[dict[str, Any]], tuple]  # a stored entry -> its identity across files
    resim: Callable[[dict[str, Any], dict[str, Any]], Row]  # (stored entry, the file's args) -> its row now
    entries: Callable[[dict[str, Any]], Iterable[dict[str, Any]]] = field(default=lambda saved: saved["cases"])


def case_fields(*names: str) -> Callable[[dict[str, Any]], tuple]:
    return lambda entry: tuple(json.dumps(entry["case"].get(n)) for n in names)


def entry_fields(*names: str) -> Callable[[dict[str, Any]], tuple]:
    return lambda entry: tuple(json.dumps(entry.get(n)) for n in names)


# --- the runners' sims, from a stored entry ---

def _standard(module: str, defaults: dict[str, Any] | None = None, deterministic: bool = False):
    """Runners whose rows are (case, server_runs) and that have Case, sim_runs (or sim_run), rates and compare."""
    def resim(stored: dict[str, Any], args: dict[str, Any]) -> Row:
        m = runner(module)
        case = m.Case(**{k: tuples(v) for k, v in stored["case"].items()})
        runs = [{**(defaults or {}), **r} for r in stored["server_runs"]]  # fields older runs didn't record
        budget = args.get("budget", 1500)
        sims = [m.sim_run(case, budget)] if deterministic else m.sim_runs(case, SIM_RUNS, budget)
        label = stored["case"].get("option_id") or stored["case"].get("case_id")
        return Row(label, case.band, m.compare(m.rates(runs), m.rates(sims)), len(runs), len(sims))
    return resim


def _barbfishing(stored: dict[str, Any], args: dict[str, Any]) -> Row:
    m = runner("calibrate_barbfishing")
    levels = tuple(stored["case"][s] for s in m.SKILLS)
    sims = [m.sim_run(levels, seed, args.get("budget", 3000)) for seed in range(SIM_RUNS)]
    s, sim = m.per_hour(stored["server_runs"]), m.per_hour(sims)
    return Row("barb_fish (" + ", ".join(f"{k} {v}" for k, v in stored["case"].items()) + ")", levels[0],
               {k: pair(s[k], sim[k]) for k in s if s[k]}, len(stored["server_runs"]), len(sims))


def _combat(stored: dict[str, Any], args: dict[str, Any]) -> Row:
    m = runner("calibrate_combat")
    case = m.Case(**{**stored["case"], "site": tuple(stored["case"]["site"])})
    sims = m.sim_runs(case, SIM_RUNS, args.get("budget", 1500))
    c = stored["case"]
    return Row(f"{c['combat_class']} {c['name']} ({c.get('loot', 'none')} loot)", case.band,
               m.compare(m.rates(stored["server_runs"], case), m.rates(sims, case)), len(stored["server_runs"]),
               len(sims))


def _agility_laps(saved: dict[str, Any]) -> list[dict[str, Any]]:
    """A lap run with at least two whole laps, as measure_agility.compare needs (the entry and pit runs fit inputs)."""
    laps = saved.get("laps") or []
    whole = [lap for lap in laps if "abandoned" in lap and not lap["abandoned"]]
    return [saved] if len(whole) >= 2 and all("abandoned" in lap for lap in laps) else []


def _agility(saved: dict[str, Any], args: dict[str, Any]) -> Row:
    m = runner("measure_agility")
    c = m.compare(saved, m.COURSES[args["course"]])
    return Row(f"{args['course']} course laps", args["agility"],
               {"xp_per_hour": pair(c["server_xp_per_hour"], c["sim_xp_per_hour"])}, c["laps"], 1,
               then={"xp_per_hour": saved["compare"]["sim_over_server"]} if "compare" in saved else None)


def _runecrafting_entries(saved: dict[str, Any]) -> list[dict[str, Any]]:
    out = [{"what": "rc", "rune": rune, **v} for rune, v in saved.get("rc", {}).items()]
    return out + ([{"what": "tiara", "rune": "air", **saved["tiara"]}] if "tiara" in saved else [])


def _runecrafting(entry: dict[str, Any], args: dict[str, Any]) -> Row:
    m = runner("calibrate_runecrafting")
    if entry["what"] == "tiara":
        each = [r["each"] for r in entry["runs"] if r.get("each") is not None]
        return Row("make air tiaras at the altar", "", {"ticks_a_tiara": pair(mean(each), m.TIARA_TICKS)},
                   len(each), 1, then={"ticks_a_tiara": entry["compare"]["each"]["sim_over_server"]})
    done = [r for r in entry["runs"] if "inside" in r]
    sim = m.sim_rc(entry["rune"])
    return Row(f"rc_{entry['rune']} at the ruins", "",
               {f"{k}_ticks": pair(mean(r[k] for r in done), sim[k]) for k in ("enter", "inside")}, len(done), 1,
               then={f"{k}_ticks": v["sim_over_server"] for k, v in entry.get("compare", {}).items()})


def _travel_entries(saved: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"set": saved["args"]["set"], **trip} for trip in saved["trips"] if trip.get("arrived")]


def _travel(entry: dict[str, Any], args: dict[str, Any]) -> Row:
    m = runner("validate_travel")
    trip = next((t for t in m.SETS[entry["set"]] if t.name == entry["trip"]), None)
    if trip is None:
        return Row(entry["trip"], "", {}, 1, 0, "no longer one of validate_travel's trips")
    state = m.sim_character(trip)
    used = [t.id for t in m.route(state, trip.end).transports]
    note = "" if used == entry["transports"] else f"the sim's route now takes {used or 'none'}, the server's run " \
                                                  f"took {entry['transports'] or 'none'}"
    return Row(f"{entry['trip']} ({entry['set']} set)", "",
               {"ticks": pair(entry["server_ticks"], m.route_ticks(state, trip.end))}, 1, 1, note,
               {"ticks": entry.get("sim_over_server")})


def ratio_then(value: Any) -> float | None:
    """A stored summary's sim over server: a ratio dict, or (the first files) none."""
    return value.get("sim_over_server") if isinstance(value, dict) else None


def _abyss_entries(saved: dict[str, Any]) -> list[dict[str, Any]]:
    """The file's runs grouped as measure_abyss.summarise compares them: the outer ring per kind of obstacle, the
    teleport and the hitpoints lost (the --pass runs), each rift (--rifts), each rune's whole crossing (--trips)."""
    out = []
    passed = [r for r in saved.get("pass", []) if r.get("outer") is not None]
    for kind in sorted({r["kind"] for r in passed}):
        out.append({"what": "outer", "kind": kind, "runs": [r for r in passed if r["kind"] == kind]})
    summary = saved.get("summary", {})
    if passed:
        out.append({"what": "teleport", "kind": "", "runs": passed, "then": ratio_then(summary.get("teleport"))})
    if passed and "defence" in saved["args"]:  # the hitpoints from the runs that set their Defence (23:17 on): a fit
        out.append({"what": "hp_lost", "kind": "", "defence": saved["args"]["defence"], "runs": passed,  # at 40,
                    "then": ratio_then(summary.get("hp_lost"))})  # a check at 20 (decision log, 2026-11-08)
    rifts = [r for r in saved.get("rifts", []) if "ticks" in r]
    for rune in sorted({r["rune"] for r in rifts}):
        out.append({"what": "rift", "kind": rune, "runs": [r for r in rifts if r["rune"] == rune]})
    runes = runner("measure_abyss").ABYSS_RUNES  # an earlier file's chaos trips: abyss_rc_chaos isn't an option now
    trips = [r for r in saved.get("trips", []) if "server" in r and r["rune"] in runes]
    for rune in sorted({r["rune"] for r in trips}):
        out.append({"what": "trip", "kind": rune, "runs": [r for r in trips if r["rune"] == rune]})
    return out


def _abyss(entry: dict[str, Any], args: dict[str, Any]) -> Row:
    m = runner("measure_abyss")
    m.TRIP_LEVELS["defence"] = args.get("defence", m.TRIP_LEVELS["defence"])  # as the run's --defence set it
    runs, what, kind = entry["runs"], entry["what"], entry["kind"]
    if what == "outer":
        return Row(f"the outer ring by the {kind}", "", {"outer_ticks": pair(
            mean(r["outer"] for r in runs), mean(m.sim_outer_ticks(kind, r["steps"]) for r in runs))}, len(runs), 1,
            then={"outer_ticks": mean(r["sim_outer"] for r in runs) / mean(r["outer"] for r in runs)})
    if what == "teleport":
        return Row("the mage's teleport", "", {"teleport_ticks": pair(
            mean(r["teleport"] for r in runs), m.TELEPORT_TICKS + 4 / 2)}, len(runs), 1,
            then={"teleport_ticks": entry["then"]})
    if what == "hp_lost":
        swing = sum(r["exposed"] * m.mean_damage(m.sim_character(m.pass_levels(r["kind"], r["level"])))
                    for r in runs)
        return Row(f"hitpoints lost in the outer ring (Defence {entry['defence']})", "", {"hp_lost": pair(
            float(sum(r["hp_lost"] for r in runs)), m.ATTACKS_PER_TICK * swing)}, len(runs), 1,
            then={"hp_lost": entry["then"]})
    if what == "rift":
        return Row(f"through the {kind} rift", "", {"ticks": pair(
            mean(r["ticks"] for r in runs), mean(m.sim_rift_ticks(r["steps"]) for r in runs))}, len(runs), 1,
            then={"ticks": mean(r["sim"] for r in runs) / mean(r["ticks"] for r in runs)})
    return Row(f"abyss_rc_{kind}, a whole crossing", "", {
        "ticks": pair(mean(r["server"] for r in runs), mean(
            m.sim_trip_ticks(kind, r["kind"], r["tries"], r["steps"], r["inner_steps"]) for r in runs)),
        "expected_ticks": pair(mean(r["server"] for r in runs), mean(
            m.sim_trip_expected(kind, r["segment"]) for r in runs))}, len(runs), 1,
        then={"ticks": mean(r["sim"] for r in runs) / mean(r["server"] for r in runs),
              "expected_ticks": mean(r["sim_expected"] for r in runs) / mean(r["server"] for r in runs)})


def files(prefix: str, since: str = "", exclude: Iterable[str] = ()) -> list[str]:
    """The family's results files from `since` (a YYYYMMDD-HHMM stamp) on, the speed check's 600 ms reruns and
    earlier re-simulations left out."""
    out = []
    for path in sorted(CALIBRATION.glob(f"{prefix}-2026*.json")):
        name = path.name
        if any(s in name for s in ("600ms", "-resim", "-rejudged", *exclude)):
            continue
        if name[len(prefix) + 1:len(prefix) + 14] >= since:
            out.append(name)
    return out


def combat_files() -> list[str]:
    """The fight sets as the ranker picks them at the freeze, each on the server with the region fix (2026-11-08,
    the re-check in the decision log): melee's and ranged's fit sets (slot 0, no looting) and check sets (slot 3,
    valuable loot), five runs where the A/B reran them; magic's, rerun with OQ-43 (a) and, for band 1's Black
    Knights, OQ-47 (c); the band-31 and -91 poison spiders (OQ-35's case with neighbours); the Abyss's fights."""
    return [f"combat-{s}.json" for s in (
        "20261108-1814-i2", "20261108-1823-i2-valuable", "20261108-1814-i3", "20261108-1825-i3-valuable",
        "20261108-1846-i2", "20261108-1853-i2-valuable",
        "20261108-2102-i7", "20261108-2104-i7", "20261108-2122-i7", "20261108-2138-i7-slot3-valuable",
        "20261108-2151-i7-valuable",
        "20261109-0132-i6", "20261109-0819-i6", "20261109-0834-i6", "20261109-0905-i7")]


def processing_files() -> list[str]:
    """Every option from the run after the four fixes (0522); firemaking resimulated with the step-offs (0525); iron
    from its 8-run file (0440), as the decision log reports them."""
    return ["processing-20261107-0522.json", "processing-20261107-0525-burn_logs-b1+31+61+91.json",
            "processing-20261107-0440-smelt_iron-b31+61+91-i3.json"]


FAMILIES: dict[str, Callable[[], Family]] = {
    # From 14:40 on Oct 31, when the ambient bots went off (the runs before had them on).
    "gathering": lambda: Family("gathering", files("gathering", "20261031-1440"), case_fields("option_id", "band"),
                                _standard("calibrate", {"died": False})),
    "processing": lambda: Family("processing", processing_files(), case_fields("option_id", "band"),
                                 _standard("calibrate_processing")),
    "crafting": lambda: Family("crafting", files("crafting"), case_fields("case_id", "band"),
                               _standard("calibrate_crafting")),
    "herblore": lambda: Family("herblore", files("herblore"), case_fields("case_id", "band"),
                               _standard("calibrate_herblore", deterministic=True)),
    "thieving": lambda: Family("thieving", files("thieving"), case_fields("option_id", "band"),
                               _standard("calibrate_thieving")),
    "barbfishing": lambda: Family("barbfishing", files("barbfishing"), case_fields("fishing", "agility", "strength"),
                                  _barbfishing),
    "combat": lambda: Family("combat", combat_files(), case_fields("combat_class", "band", "npc", "site", "loot"),
                             _combat),
    "agility": lambda: Family("agility", files("agility"), lambda s: (s["args"]["course"], s["args"]["agility"]),
                              _agility, _agility_laps),
    "runecrafting": lambda: Family("runecrafting", files("runecrafting"), entry_fields("what", "rune"),
                                   _runecrafting, _runecrafting_entries),
    # From the first run that named its set (the runs before were the fit set's, which 18:29's ran whole).
    "travel": lambda: Family("travel", files("travel-validation", "20261101-1821"), entry_fields("set", "trip"),
                             _travel, _travel_entries),
    "abyss": lambda: Family("abyss", files("abyss"), entry_fields("what", "kind", "defence"), _abyss,
                            _abyss_entries),
}


def latest(family: Family) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """(file, stored entry, the file's args) for each case's last measurement among the family's files."""
    found: dict[tuple, tuple[str, dict[str, Any], dict[str, Any]]] = {}
    for name in family.files:
        saved = json.loads((CALIBRATION / name).read_text(encoding="utf-8"))
        for entry in family.entries(saved):
            found[family.key(entry)] = (name, entry, saved.get("args", {}))
    return list(found.values())


def rows_for(family: Family) -> tuple[list[dict[str, Any]], set[str]]:
    out, used = [], set()
    for name, stored, args in latest(family):
        row = family.resim(stored, args)
        used.add(name)
        then = row.then if row.then is not None else {
            metric: (v or {}).get("sim_over_server", "") for metric, v in stored.get("compare", {}).items()}
        for metric, values in row.compare.items():
            server, sim = float(values["server"]), float(values["sim"])
            if not server and not sim:
                continue  # nothing on either side (no loot kept, no XP from a stage)
            ratio = sim / server if server else float("inf")
            gated = metric in GATED[family.name]
            inside = abs(ratio - 1) <= GATE
            note = row.note or (NOTES.get((family.name, row.case, row.band), "") if gated and not inside else "")
            out.append({"family": family.name, "case": row.case, "band": row.band, "metric": metric,
                        "gated": gated, "server": round(server, 2), "sim": round(sim, 2),
                        "sim_over_server": round(ratio, 3), "within_gate": inside, "server_runs": row.server_runs,
                        "sim_runs": row.sim_runs, "measured": stamp(name), "source": name,
                        "sim_over_server_then": "" if then.get(metric) in (None, "") else round(then[metric], 3),
                        "note": note})
    return out, used


def drops() -> tuple[list[dict[str, Any]], set[str]]:
    """Each probed monster's latest drop counts, judged by the sim's drop sampler now (probe_drops.judge), with
    SIM_REPLICATES runs of the same kills from seed 0."""
    m = runner("probe_drops")
    pool = {e.npc.id: e for e in m.enemy_pool()}
    found: dict[int, tuple[str, dict[str, Any]]] = {}
    for name in files("drops"):
        for monster in json.loads((CALIBRATION / name).read_text(encoding="utf-8"))["monsters"]:
            if monster.get("kills"):
                found[monster["npc"]] = (name, monster)
    out = []
    for name, monster in found.values():
        counts = {int(k): v for k, v in monster["counts"].items()}
        sims = m.sim_counts(pool[monster["npc"]].drops, monster["kills"], m.SIM_REPLICATES, np.random.default_rng(0))
        verdict = m.judge(counts, sims, monster["kills"])
        misses = [r["name"] for r in verdict["items"] if not r["fits"] and not r["sim_never"]]
        out.append({"npc": monster["npc"], "monster": monster["name"], "kills": monster["kills"],
                    "items_checked": verdict["checked"], "items_fit": verdict["fits"], "not_fitting": "; ".join(misses),
                    "sim_never_gp_per_kill": round(verdict["sim_never_gp_per_kill"], 1), "measured": stamp(name),
                    "source": name})
    return sorted(out, key=lambda r: r["monster"]), {name for name, _ in found.values()}


def speed_check() -> tuple[list[dict[str, Any]], set[str]]:
    """The speed check's rows as scripts/speed_check.py measured them: both sides on the server, at 50 and 600 ms."""
    rows: dict[tuple, dict[str, Any]] = {}
    used = set()
    for name in files("speed-check"):
        used.add(name)
        for r in json.loads((CALIBRATION / name).read_text(encoding="utf-8"))["rows"]:
            fast = Path(r["fast"].replace("\\", "/")).name
            # the first checks named their measure in the key (fast_xp_per_hour, fast_ticks), the last in "measure"
            measure = r.get("measure") or next(k[5:] for k in r if k.startswith("fast_") and k != "fast_mean")
            fast_value, slow_value = (r.get(f"{side}_mean", r.get(f"{side}_{measure}")) for side in ("fast", "slow"))
            rows[(fast, r["case"], measure)] = {
                "family": fast.split("-2026")[0], "case": r["case"], "measure": measure,
                "at_50ms": round(fast_value, 2), "at_600ms": round(slow_value, 2),
                "slow_over_fast": r["slow_over_fast"], "se_difference": r.get("se_difference", ""),
                "agrees": r["agrees"], "runs": "/".join(str(n) for n in r.get("runs", [1, 1])), "source": name}
    return list(rows.values()), used


def provenance(sources: Iterable[str]) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    descends = subprocess.run(["git", "merge-base", "--is-ancestor", SIM_TAG, "HEAD"], cwd=REPO).returncode == 0
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain")),
            "sim_tag": SIM_TAG, "descends_from_sim_tag": descends, "sim_runs": SIM_RUNS, "gate": GATE,
            "made": datetime.now().astimezone().isoformat(timespec="seconds"),
            "sources": {name: hashlib.sha256((CALIBRATION / name).read_bytes()).hexdigest()
                        for name in sorted(sources)}}


def write(path: Path, rows: list[dict[str, Any]], columns: Iterable[str] | None = None) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, list(columns or rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


README_RULES = """\
## How the cases were chosen

- **The server's side** is each case's last measurement among the files its family lists (`FAMILIES` in
  `scripts/sim_to_real.py`), from the git-ignored `results/calibration/`, at 50 ms ticks. The server's code was frozen
  at upstream from Oct 31; the fork's own rule changes went on to Nov 9 (CLAUDE.md lists them). Where the decision
  log found one touched a family's measurements, it re-measured them (combat's sets after the region fix,
  2026-11-08), and the runs here are those re-measurements.
- **The sim's side** is each runner's own sim function, called on sim-v1.2 from the same start, with 200 seeds
  (one run where the sim is deterministic: Herblore, the timed families). The server's rates are each runner's own.
- **Gathering** from 14:40 on Oct 31, when the ambient bots went off. **Processing:** the run after its four fixes,
  firemaking's step-off run and iron's 8-run file. **Combat:** the fit sets (the ranker's top by XP, no looting) and
  check sets (its top by gp, valuable loot) for melee, ranged and magic as the decision log's last re-checks have
  them, OQ-35's poison spiders and the Abyss's fights; its gp/hr is gated by its parts (OQ-20 (a): the drop tables,
  and kills/hr). **Travel:** the fit, check, shortcut and Abyss sets, one run a trip. **The Abyss:** the outer ring per
  obstacle, the teleport and the rifts (the `--pass` and `--rifts` runs), the hitpoints from the runs that set their
  Defence (a fit at 40, a check at 20), and each rune's whole crossing.
- **Left out:** the 600 ms reruns (the speed check's own table), earlier re-simulations, runs the decision log
  superseded, chaos's crossings (`abyss_rc_chaos` isn't an option), and measurements that fitted the sim's inputs
  rather than test an option: Agility's course entries and spike pit, the shortcuts' own crossings, the travel
  constants, the essence pouches and the Abyss's failed tries.
- **Fitted and checked:** the calibration measured each family's overheads on the server and fitted the sim to them,
  so many cases agree partly by construction. Combat's fit and check sets, and travel's fit and check sets, keep the
  two apart; elsewhere the cases are the ones the overheads were fitted on, at several bands.
"""


def table_md(table: pd.DataFrame) -> str:
    cols = list(table.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in table.itertuples(index=False)]
    return "\n".join(lines)


def readme(out: Path, prov: dict[str, Any], command: str) -> str:
    from rlscape.analysis import sim_to_real as tables
    cases = pd.read_csv(out / "cases.csv", keep_default_na=False)
    speed = pd.read_csv(out / "speed_check.csv", keep_default_na=False) if (out / "speed_check.csv").exists() else None
    parts = [
        "# sim-to-real", "",
        "The calibration gate's cases (env contract §7: XP/hr, gp/hr and duration within ±20%), each case's latest "
        "server runs against sim-v1.2, re-simulated by `scripts/sim_to_real.py` (Caleb, 2026-11-12, "
        "`m002-sim-to-real`). `scripts/figures.py` makes the report's tables from these files.", "",
        "| | |", "|---|---|", f"| Command | `{command}` |", f"| Git SHA | `{prov['commit']}`"
        + (" (uncommitted changes: not reproducible from this SHA)" if prov["dirty"] else "") + " |",
        f"| Sim | `{prov['sim_tag']}` (the commit descends from it: {prov['descends_from_sim_tag']}) |",
        f"| Made | {prov['made']} |", f"| Sources | {len(prov['sources'])} files of `results/calibration/` "
        "(their SHA-256 in `config.json`) |", "",
        "## Per family (gated metrics; sim over server)", "", table_md(tables.family_table(cases, speed)), ""]
    if (out / "drops.csv").exists():
        parts += ["## Combat's drop tables (OQ-20 (a))", "",
                  table_md(tables.drops_row(pd.read_csv(out / "drops.csv", keep_default_na=False))), ""]
    parts += [README_RULES, "## Files", "",
              "- `cases.csv`: one row per case and metric, gated or not, with the server runs' file and date, sim "
              "over server as calibrated then, and a note;",
              "- `drops.csv`: per monster probed, the items whose server count falls in the sim's central 99%;",
              "- `speed_check.csv`: each speed-check case at 50 and 600 ms ticks, both on the server (OQ-21);",
              "- `config.json`: the provenance and each source file's SHA-256.", ""]
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--families", nargs="*", choices=sorted(FAMILIES), help="default: every family")
    parser.add_argument("--no-drops", action="store_true", help="skip the drop tables (the slowest part)")
    parser.add_argument("--out", type=Path, default=REPO / "results" / "summary" / "sim-to-real")
    parser.add_argument("--allow-dirty", action="store_true", help="into results/summary from uncommitted changes")
    args = parser.parse_args()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True,
                                check=True).stdout.strip())
    if dirty and not args.allow_dirty and (REPO / "results" / "summary") in args.out.resolve().parents:
        raise SystemExit("the tree has uncommitted changes, so its SHA wouldn't reproduce this summary: commit "
                         "first, or pass --allow-dirty")
    sys.path.insert(0, str(REPO / "scripts"))
    rows, used = [], set()
    for name in args.families or FAMILIES:
        start = time.perf_counter()
        family_rows, family_used = rows_for(FAMILIES[name]())
        rows += family_rows
        used |= family_used
        gated = [r for r in family_rows if r["gated"]]
        print(f"{name:12s} {len({(r['case'], r['band']) for r in family_rows}):3d} cases, "
              f"{sum(r['within_gate'] for r in gated)} of {len(gated)} gated metrics within the gate "
              f"({time.perf_counter() - start:.0f} s)", flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    write(args.out / "cases.csv", rows, COLUMNS)
    if not args.no_drops:
        start = time.perf_counter()
        drop_rows, drop_used = drops()
        used |= drop_used
        write(args.out / "drops.csv", drop_rows)
        print(f"drops        {len(drop_rows):3d} monsters, {sum(r['items_fit'] for r in drop_rows)} of "
              f"{sum(r['items_checked'] for r in drop_rows)} items fit ({time.perf_counter() - start:.0f} s)")
    speed_rows, speed_used = speed_check()
    used |= speed_used
    write(args.out / "speed_check.csv", speed_rows)
    print(f"speed check  {len(speed_rows):3d} rows, {sum(bool(r['agrees']) for r in speed_rows)} agree")
    prov = provenance(used)
    (args.out / "config.json").write_text(json.dumps(prov, indent=1) + "\n", encoding="utf-8")
    command = "uv run python scripts/sim_to_real.py" + (f" {' '.join(sys.argv[1:])}" if sys.argv[1:] else "")
    (args.out / "README.md").write_text(readme(args.out, prov, command), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
