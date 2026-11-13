"""The sim-to-real tables (ROADMAP's Nov 19–21: "the sim-to-real table from the calibration gate"), from the summary
`scripts/sim_to_real.py` writes to `results/summary/sim-to-real/`: every calibration case's latest server runs against
sim-v1.2, re-simulated (Caleb, 2026-11-12, `m002-sim-to-real`).

- **The family table** (the report's body, `family_table`): per family, its cases, the range of sim over server on
  each kind of gated metric (XP an hour; output an hour: items, products, coins, kills or catches; duration), how
  many gated metrics are within the gate, the cases outside it, and the speed check's 600 ms runs that agree with the
  50 ms ones. Combat's gp/hr is gated by its parts (OQ-20 (a)), so its drop tables get a row of their own
  (`drops_row`).
- **The case table** (the appendix, `case_table`): every case, with sim over server on each kind of gated metric
  (where a family gates two of a kind, the one farthest from 1), whether all are within the gate, and the note.
"""

from __future__ import annotations

import pandas as pd

GATE = 0.2
KINDS = {  # a gated metric -> the kind of measure it is
    "xp_per_hour": "xp", "fishing_xp_per_hour": "xp", "agility_xp_per_hour": "xp", "strength_xp_per_hour": "xp",
    "xp": "xp", "items_per_hour": "output", "made_per_hour": "output", "made": "output", "gp_per_hour": "output",
    "catches_per_hour": "output", "kills_per_hour": "output", "hp_lost": "output", "ticks_to_full": "duration",
    "ticks": "duration", "enter_ticks": "duration", "inside_ticks": "duration", "ticks_a_tiara": "duration",
    "outer_ticks": "duration", "teleport_ticks": "duration", "expected_ticks": "duration",
}
KIND_NAMES = {"xp": "XP/hr", "output": "output/hr", "duration": "duration"}
FAMILIES = {  # the summary's family -> its name in the report, in the report's order
    "gathering": "Gathering (woodcutting, mining, fishing)",
    "barbfishing": "Barbarian fishing",
    "processing": "Processing (smelting, smithing, cooking, firemaking, burying)",
    "crafting": "Crafting",
    "herblore": "Herblore",
    "thieving": "Thieving (pickpocketing)",
    "agility": "Agility (courses)",
    "runecrafting": "Runecrafting (at the ruins)",
    "abyss": "Runecrafting (through the Abyss)",
    "combat": "Combat (melee, ranged, magic)",
    "travel": "Travel",
}
SPEED_FAMILIES = {"travel-validation": "travel"}  # a speed check's file prefix -> the summary's family


def _bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower() == "true"


def gated(cases: pd.DataFrame) -> pd.DataFrame:
    """The gated rows, with each metric's kind."""
    rows = cases[_bool(cases["gated"])].copy()
    rows["within_gate"] = _bool(rows["within_gate"])
    rows["kind"] = rows["metric"].map(KINDS)
    if rows["kind"].isna().any():
        raise ValueError(f"metrics with no kind: {sorted(rows.loc[rows['kind'].isna(), 'metric'].unique())}")
    return rows


def _label(case: str, band) -> str:
    return f"{case}, band {int(float(band))}" if str(band) not in ("", "nan") else case


def _range(values: pd.Series) -> str:
    return "" if values.empty else (f"{values.min():.2f}" if len(values) == 1 or values.min() == values.max()
                                    else f"{values.min():.2f} to {values.max():.2f}")


def family_table(cases: pd.DataFrame, speed: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = gated(cases)
    speed_by = {}
    if speed is not None:
        fam = speed["family"].map(lambda f: SPEED_FAMILIES.get(f, f))
        agrees = _bool(speed["agrees"])
        speed_by = {f: f"{int(agrees[fam == f].sum())} of {int((fam == f).sum())}" for f in fam.unique()}
    out = []
    for family, name in FAMILIES.items():
        mine = rows[rows["family"] == family]
        if mine.empty:
            continue
        outside = mine[~mine["within_gate"]]
        names = sorted({f"{_label(r.case, r.band)} ({r.metric} {r.sim_over_server:.2f})"
                        for r in outside.itertuples()})
        out.append({
            "family": name, "cases": mine.groupby(["case", "band"], dropna=False).ngroups,
            **{KIND_NAMES[k]: _range(mine.loc[mine["kind"] == k, "sim_over_server"]) for k in KIND_NAMES},
            "within_gate": f"{int(mine['within_gate'].sum())} of {len(mine)}",
            "outside": "; ".join(names), "speed_check": speed_by.get(family, ""),
            "measured": f"{mine['measured'].min()[:10]} to {mine['measured'].max()[:10]}"})
    return pd.DataFrame(out)


def drops_row(drops: pd.DataFrame) -> pd.DataFrame:
    """Combat's drop tables (OQ-20 (a)), one row: the monsters probed, the items whose server count falls in the
    sim's central 99%, those that don't, and the most gp a kill from items the sim never drops."""
    misses = [f"{r.monster}: {r.not_fitting}" for r in drops.itertuples() if isinstance(r.not_fitting, str)
              and r.not_fitting]
    return pd.DataFrame([{
        "family": "Combat's drop tables", "monsters": len(drops), "kills": int(drops["kills"].sum()),
        "items_fit": f"{int(drops['items_fit'].sum())} of {int(drops['items_checked'].sum())}",
        "not_fitting": "; ".join(misses),
        "sim_never_gp_per_kill_max": float(drops["sim_never_gp_per_kill"].max())}])


def case_table(cases: pd.DataFrame) -> pd.DataFrame:
    rows = gated(cases)
    rows["distance"] = (rows["sim_over_server"] - 1).abs()
    out = []
    order = {f: i for i, f in enumerate(FAMILIES)}
    for (family, case, band), mine in rows.groupby(["family", "case", "band"], dropna=False, sort=False):
        row = {"family": FAMILIES.get(family, family), "case": case,
               "band": "" if str(band) in ("", "nan") else int(float(band)),
               "server_runs": int(mine["server_runs"].max())}
        for kind, name in KIND_NAMES.items():
            of_kind = mine[mine["kind"] == kind]
            if of_kind.empty:
                row[name] = ""
                continue
            far = of_kind.loc[of_kind["distance"].idxmax()]
            row[name] = f"{far['sim_over_server']:.2f}" + (f" ({far['metric']})" if len(of_kind) > 1 else "")
        row["within_gate"] = bool(mine["within_gate"].all())
        notes = [n for n in mine["note"].fillna("").astype(str).unique() if n]
        row["note"] = "; ".join(notes)
        row["_order"] = order.get(family, len(order))
        out.append(row)
    table = pd.DataFrame(out)
    return table.sort_values(["_order"], kind="stable").drop(columns="_order").reset_index(drop=True)
