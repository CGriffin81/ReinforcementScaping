"""The sim-to-real table (scripts/sim_to_real.py, rlscape/analysis/sim_to_real.py): which stored run stands for a
case, a re-simulation through a runner's own sim, and the tables the figure script makes from the summary."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from rlscape.analysis import sim_to_real as s2r
from rlscape.gamedata import server as gd

REPO = Path(__file__).resolve().parents[1]
needs_server_data = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")


def script(name: str):
    spec = importlib.util.spec_from_file_location(f"{name}_script", REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tool(tmp_path, monkeypatch):
    module = script("sim_to_real")
    monkeypatch.setattr(module, "CALIBRATION", tmp_path)
    return module


def save(root: Path, name: str, cases: list[dict]) -> None:
    (root / name).write_text(json.dumps({"args": {"budget": 1500}, "cases": cases}), encoding="utf-8")


def test_a_files_date_comes_from_its_name(tool):
    assert tool.stamp("gathering-20261031-1440.json") == "2026-10-31 14:40"
    assert tool.stamp("combat-20261108-1823-i2-valuable.json") == "2026-11-08 18:23"
    assert tool.stamp("travel-validation-20261109-0104-i6.json") == "2026-11-09 01:04"


def test_the_speed_checks_reruns_and_earlier_resimulations_are_left_out_and_since_is_kept(tool, tmp_path):
    for name in ("gathering-20261031-1330.json", "gathering-20261031-1440.json", "gathering-20261106-1845-600ms.json",
                 "combat-20261105-1936-resim.json", "drops-20261106-2007-rejudged.json"):
        save(tmp_path, name, [])
    assert tool.files("gathering") == ["gathering-20261031-1330.json", "gathering-20261031-1440.json"]
    assert tool.files("gathering", "20261031-1440") == ["gathering-20261031-1440.json"]
    assert tool.files("combat") == [] and tool.files("drops") == []


def test_a_case_comes_from_the_last_file_that_measured_it(tool, tmp_path):
    def case(option, band, runs):
        return {"case": {"option_id": option, "band": band}, "server_runs": [{}] * runs}
    save(tmp_path, "processing-1.json", [case("smelt_iron", 31, 3), case("smelt_bronze", 1, 3)])
    save(tmp_path, "processing-2.json", [case("smelt_iron", 31, 8)])
    family = tool.Family("processing", ["processing-1.json", "processing-2.json"],
                         tool.case_fields("option_id", "band"), resim=None)
    found = {entry["case"]["option_id"]: (name, len(entry["server_runs"])) for name, entry, _ in tool.latest(family)}
    assert found == {"smelt_iron": ("processing-2.json", 8), "smelt_bronze": ("processing-1.json", 3)}


@needs_server_data
def test_a_resimulation_runs_the_runners_own_sim_from_the_stored_case():
    """Herblore's sim is deterministic: its own run as the server's side gives 1.00 on every metric."""
    tool = script("sim_to_real")
    herblore = tool.runner("calibrate_herblore")
    case = herblore.CASES[0]
    run = herblore.sim_run(case, 1500)
    stored = {"case": {"case_id": case.case_id, "band": case.band}, "server_runs": [run, run]}
    row = tool._standard("calibrate_herblore", deterministic=True)(stored, {"budget": 1500})
    assert row.case == case.case_id and row.server_runs == 2 and row.sim_runs == 1
    assert row.compare and all(v["sim_over_server"] == 1.0 for v in row.compare.values())


def cases_frame() -> pd.DataFrame:
    rows = [  # family, case, band, metric, gated, sim over server
        ("gathering", "wc_logs", "1", "xp_per_hour", True, 1.06),
        ("gathering", "wc_logs", "1", "ticks_to_full", True, 0.95),
        ("gathering", "fish_shrimp", "1", "items_per_hour", True, 0.66),
        ("gathering", "fish_shrimp", "1", "xp_per_hour", True, 1.09),
        ("combat", "melee Rat (none loot)", "1", "xp_per_hour", True, 0.93),
        ("combat", "melee Rat (none loot)", "1", "gp_per_hour", False, 3.0),
        ("combat", "melee Rat (none loot)", "1", "kills_per_hour", True, 0.92),
        ("combat", "melee Rat (none loot)", "1", "ticks", True, 1.10),
        ("travel", "home teleport from Falador (check set)", "", "ticks", True, 1.06),
    ]
    return pd.DataFrame([{"family": f, "case": c, "band": b, "metric": m, "gated": str(g), "server": 1.0,
                          "sim": r, "sim_over_server": r, "within_gate": str(abs(r - 1) <= 0.2), "server_runs": 3,
                          "sim_runs": 200, "measured": "2026-11-05 19:01", "source": "x.json",
                          "sim_over_server_then": "", "note": "dies at Draynor" if c == "fish_shrimp" else ""}
                         for f, c, b, m, g, r in rows])


def test_the_family_table_counts_gated_metrics_only_and_names_the_cases_outside():
    speed = pd.DataFrame({"family": ["gathering", "travel-validation", "travel-validation"],
                          "agrees": ["True", "True", "False"]})
    table = s2r.family_table(cases_frame(), speed).set_index("family")
    gathering = table.loc[s2r.FAMILIES["gathering"]]
    assert gathering["cases"] == 2 and gathering["within_gate"] == "3 of 4"
    assert gathering["XP/hr"] == "1.06 to 1.09" and gathering["output/hr"] == "0.66"
    assert gathering["outside"] == "fish_shrimp, band 1 (items_per_hour 0.66)" and gathering["speed_check"] == "1 of 1"
    combat = table.loc[s2r.FAMILIES["combat"]]  # its gp/hr is gated by its parts, not counted here
    assert combat["within_gate"] == "3 of 3" and combat["outside"] == ""
    assert table.loc[s2r.FAMILIES["travel"], "speed_check"] == "1 of 2"
    assert list(table.index) == [s2r.FAMILIES[f] for f in ("gathering", "combat", "travel")]  # the report's order


def test_the_case_table_shows_each_kind_farthest_from_one_and_the_note():
    table = s2r.case_table(cases_frame()).set_index("case")
    rat = table.loc["melee Rat (none loot)"]
    assert rat["XP/hr"] == "0.93" and rat["output/hr"] == "0.92" and rat["duration"] == "1.10"
    shrimp = table.loc["fish_shrimp"]
    assert not shrimp["within_gate"] and shrimp["note"] == "dies at Draynor" and shrimp["band"] == 1
    assert table.loc["home teleport from Falador (check set)", "band"] == ""


def test_the_drop_tables_row_sums_the_monsters():
    drops = pd.DataFrame({"monster": ["Moss giant", "Hill Giant"], "kills": [200, 210], "items_checked": [20, 15],
                          "items_fit": [19, 15], "not_fitting": ["Nature rune", ""],
                          "sim_never_gp_per_kill": [12.5, 3.0]})
    row = s2r.drops_row(drops).iloc[0]
    assert row["monsters"] == 2 and row["kills"] == 410 and row["items_fit"] == "34 of 35"
    assert row["not_fitting"] == "Moss giant: Nature rune" and row["sim_never_gp_per_kill_max"] == 12.5


def test_the_figure_script_makes_the_tables_from_a_summary(tmp_path):
    figures = script("figures")
    gate = tmp_path / "summary" / "sim-to-real"
    gate.mkdir(parents=True)
    cases_frame().to_csv(gate / "cases.csv", index=False)
    figures.build(tmp_path / "summary", tmp_path / "out")
    assert (tmp_path / "out" / "sim_to_real_families.csv").exists()
    assert (tmp_path / "out" / "sim_to_real_cases.csv").exists()
    assert not (tmp_path / "out" / "sim_to_real_drops.csv").exists()  # no drops.csv in this summary
