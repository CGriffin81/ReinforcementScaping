"""The progress report (Caleb, 2026-11-23): its supporting results built from the figure tables and the committed
summaries, both documents printed to PDF with headless Edge, and a zip of them with the proposal to submit.

    uv run python scripts/figures.py           # first: writes results/figures/, which this reads
    uv run python scripts/progress_report.py

`docs/progress-report/progress-report.html` is written by hand. This script writes `supporting-results.html` beside
it, then `progress-report.pdf`, `supporting-results.pdf` and `progress-report-submission.zip`. It needs Windows,
for Edge (Chromium prints the pages' `@page` CSS, page numbers included). Both documents are in APA 7 format
(Caleb, 2026-11-23; `report.css`): the supporting results' tables are Table S1 on, its figures Figure S1 on.
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import subprocess
import tempfile
import time
import zipfile
from collections.abc import Callable, Sequence
from pathlib import Path

import pandas as pd

from rlscape.analysis import measures as ms
from rlscape.eval.harness import REPO

REPORT = REPO / "docs" / "progress-report"
FIGURES = REPO / "results" / "figures"
SUMMARY = REPO / "results" / "summary"
PROPOSAL = REPO / "CS898BG_RL_Project_Proposal_2009Scape.pdf"
EDGE = (Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"))
DATE = "November 23, 2026"


def _figures_script():
    """scripts/figures.py, for its names (experiments, series, baselines) and its summary reader."""
    spec = importlib.util.spec_from_file_location("figures_script", REPO / "scripts" / "figures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


figs = _figures_script()
E3_ORDER = [figs.series_name(figs.E3, v) for v in figs.WEIGHTINGS]
RQ4_ORDER = [figs.REFERENCE, "PPO + RND", "γ_hr 0.9", "γ_hr 0.5", "PBRS"]
BASELINE_ORDER = ["guide", "greedy XP/hr", "greedy GP/hr", "random"]


# --- formatting --------------------------------------------------------------------------------------------------

def esc(text: object) -> str:
    """Escaped for HTML, with the figures' "γ_hr" set as γ with a subscript."""
    return html.escape(str(text)).replace("γ_hr", "γ<sub>hr</sub>")


def levels(x: float) -> str:
    return f"{x:,.0f}"


def gp_ci(mean: float, low: float, high: float) -> str:
    """Net worth with its CI, all three in one unit: M if the mean or the CI's top reaches a million, else k."""
    if max(abs(mean), abs(high)) >= 1e6:
        return f"{mean / 1e6:.2f}M [{low / 1e6:.2f}M, {high / 1e6:.2f}M]"
    return f"{mean / 1e3:,.0f}k [{low / 1e3:,.0f}k, {high / 1e3:,.0f}k]"


def ci(fmt: Callable[[float], str], mean: float, low: float, high: float) -> str:
    return f"{fmt(mean)} [{fmt(low)}, {fmt(high)}]"


def two(x: float) -> str:
    return f"{x:.2f}"


def three(x: float) -> str:
    return f"{x:.3f}"


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def table(header: Sequence[str], rows: Sequence[Sequence[object]], numeric: Sequence[int] = ()) -> str:
    """An HTML table; the `numeric` columns centred, as APA sets them (report.css)."""
    def cell(tag: str, i: int, value: object) -> str:
        cls = ' class="num"' if i in numeric else ""
        return f"<{tag}{cls}>{esc(value)}</{tag}>"
    head = "".join(cell("th", i, h) for i, h in enumerate(header))
    body = "\n".join("<tr>" + "".join(cell("td", i, v) for i, v in enumerate(row)) + "</tr>" for row in rows)
    return f"<table>\n<thead><tr>{head}</tr></thead>\n<tbody>\n{body}\n</tbody>\n</table>"


def read(name: str) -> pd.DataFrame:
    path = FIGURES / f"{name}.csv"
    if not path.exists():
        raise SystemExit(f"{path} is missing: run `uv run python scripts/figures.py` first")
    return pd.read_csv(path)


def ordered(frame: pd.DataFrame, column: str, order: Sequence[str]) -> pd.DataFrame:
    rank = {name: i for i, name in enumerate(order)}
    frame = frame[frame[column].isin(rank)]
    return frame.sort_values(column, key=lambda s: s.map(rank), kind="stable")


# --- the tables ----------------------------------------------------------------------------------------------------

def experiments() -> str:
    rows = [
        ("E1", "Baselines", "Random, greedy XP/hr, greedy GP/hr and a scripted guide, 30 seeded episodes each",
         "-", "RQ1's reference; the reward's units", "e1-baselines"),
        ("E2", "PPO sanity ladder", "A toy task with a known optimum; PPO against random; GAE λ × learning rate, "
         "2 seeds each", "8 (1M decisions each)", "Checks the learner; picks its settings", "e2-ppo-sanity-ladder"),
        ("E3", "Reward-weight sweep", "Five weightings from all skill (1, 0) to all wealth (0, 1), 5 seeds each",
         "25", "RQ1, RQ2, RQ3, H1, H2", "e3-reward-weight-sweep"),
        ("E4", "PPO + RND", "Random network distillation's exploration bonus, at (.5, .5)", "5", "RQ2, RQ4, H3",
         "e4-rnd-exploration"),
        ("E5", "Weight-conditioned PPO", "The weighting drawn each episode and given in the observation; "
         "evaluated at 13 weightings", "5", "RQ3", "e5-weight-conditioned-ppo"),
        ("E6a", "Discount sweep", "γ_hr 0.9 and 0.5 per game-hour, at (.5, .5) (E3's is 0.99)", "10", "RQ4",
         "e6a-discount-sweep"),
        ("E6b", "PBRS", "Potential-based shaping, Φ the best gathering income the levels allow, at (.5, .5)", "5",
         "RQ4", "e6b-pbrs-shaping"),
    ]
    return table(["ID", "Experiment", "What it runs", "Training runs", "Answers", "Config and summary"], rows,
                 numeric=[3])


def checkpoint(hour: int) -> str:
    progress = read("progress")
    at = progress[progress["hour"] == hour].copy()
    at["variant"] = at["variant"].map(lambda v: figs.BASELINES.get(v, v))
    rows = []
    for name in BASELINE_ORDER + E3_ORDER:
        level = at[(at["variant"] == name) & (at["metric"] == "Total level")]
        worth = at[(at["variant"] == name) & (at["metric"] == "Net worth (gp)")]
        if level.empty or worth.empty:
            continue
        lv, nw = level.iloc[0], worth.iloc[0]
        who = f"{int(lv['seeds'])} episodes" if not lv["trained"] else f"{int(lv['seeds'])} seeds × 30 episodes"
        rows.append([name, who, ci(levels, lv["mean"], lv["ci_low"], lv["ci_high"]),
                     gp_ci(nw["mean"], nw["ci_low"], nw["ci_high"])])
    return table(["Policy", "Evaluated on", "Total level [95% CI]", "Net worth, gp [95% CI]"], rows, numeric=[2, 3])


def rq4_progress() -> pd.DataFrame:
    """Hour 20 of E3's (.5, .5) and of E4, E6a and E6b: each series' level and net worth over its training seeds."""
    data = figs.Summaries(SUMMARY)
    frames = []
    for experiment in (figs.E3, figs.E4, figs.E6A, figs.E6B):
        checkpoints = data.evaluation(experiment, "checkpoints.csv")
        if checkpoints is None:
            continue
        for metric in ("total_level", "net_worth"):
            p = ms.progress(checkpoints, metric)
            p = p[p["trained"] & (p["hour"] == 20)]
            p = p.assign(series=[figs.series_name(experiment, v) for v in p["variant"]], metric=metric)
            frames.append(p)
    out = pd.concat(frames, ignore_index=True)
    return out[out["series"].isin(RQ4_ORDER)]


def rq4() -> str:
    at20 = rq4_progress()
    value = read("weighted_value").set_index("series")
    eff = read("sample_efficiency")
    rows = []
    for name in RQ4_ORDER:
        lv = at20[(at20["series"] == name) & (at20["metric"] == "total_level")]
        nw = at20[(at20["series"] == name) & (at20["metric"] == "net_worth")]
        if lv.empty or nw.empty or name not in value.index:
            continue
        lv, nw, v = lv.iloc[0], nw.iloc[0], value.loc[name]
        runs = eff[eff["series"] == name]
        reached = runs[runs["matched"]]
        when = (f" (by {reached['to_step'].min() / 1e6:.2f}M–{reached['to_step'].max() / 1e6:.2f}M)"
                if len(reached) else "")
        rows.append([name, int(lv["seeds"]), ci(levels, lv["mean"], lv["ci_low"], lv["ci_high"]),
                     gp_ci(nw["mean"], nw["ci_low"], nw["ci_high"]),
                     ci(two, v["value"], v["value_low"], v["value_high"]),
                     f"{int(v['seeds_above'])} of {int(v['seeds'])}",
                     f"{len(reached)} of {len(runs)}{when}"])
    return table(["Variant", "Seeds", "Total level", "Net worth, gp", "Weighted value", "Seeds above 0.57",
                  "Runs reaching 0.57 in training"], rows, numeric=[1, 2, 3, 4])


def weighted() -> str:
    value = read("weighted_value")
    rows = [[r["series"], figs.weighting((r["u_skill"], r["u_wealth"])),
             ci(two, r["value"], r["value_low"], r["value_high"]),
             f"{r['best_baseline']}, {r['best_baseline_value']:.2f}", f"{int(r['seeds_above'])} of {int(r['seeds'])}"]
            for _, r in value.iterrows()]
    return table(["Agent", "Weighting (skill, wealth)", "Value at hour 20 [95% CI]", "E1's best baseline there",
                  "Seeds above it"], rows, numeric=[2])


def pareto() -> str:
    hv = read("hypervolume").merge(read("training_cost"), on=["method", "seeds"])
    rows = [[r["method"], ci(three, r["mean"], r["ci_low"], r["ci_high"]), f"{r['runs_per_front']:.0f}",
             f"{r['decisions_per_front'] / 1e6:.1f}M", ci(lambda x: f"{x:.1f}", r["wall_hours_per_front"],
                                                       r["wall_hours_low"], r["wall_hours_high"])]
            for _, r in hv.iterrows()]
    return table(["Method", "Hypervolume [95% CI]", "Runs a front", "Training decisions a front",
                  "Training hours a front [95% CI]"], rows, numeric=[1, 2, 3, 4])


def verdicts() -> str:
    v = read("verdicts")
    counts = v.groupby(["series", "verdict"]).size().unstack(fill_value=0)
    rows = []
    for name in E3_ORDER + RQ4_ORDER[1:]:
        if name in counts.index:
            c = counts.loc[name]
            rows.append([name, *(int(c.get(k, 0)) for k in ("gradual", "sudden", "no gain"))])
    return table(["Series", "Gradual", "Sudden", "No gain"], rows, numeric=[1, 2, 3])


def consistency() -> str:
    c = ordered(read("consistency"), "series", E3_ORDER + RQ4_ORDER[1:])
    rows = [[r["series"], int(r["pairs"]), ci(three, r["js_bits"], r["ci_low"], r["ci_high"])]
            for _, r in c.iterrows()]
    return table(["Series", "Pairs of seeds", "Mean JS divergence, bits [95% CI]"], rows, numeric=[1, 2])


def divergence() -> str:
    d = read("mix_divergence")
    rows = [[r["series_a"], r["series_b"], int(r["pairs"]), ci(three, r["js_bits"], r["ci_low"], r["ci_high"])]
            for _, r in d.iterrows()]
    return table(["Weighting", "Against", "Pairs of seeds", "Mean JS divergence, bits [95% CI]"], rows,
                 numeric=[2, 3])


def walking() -> str:
    w = read("rq5_walking_summary")
    w = w[w["trained"] & w["share"].isin(["walk_share", "overhead_share"])]
    names = {"gamma_hr0.5": "γ_hr 0.5", "gamma_hr0.9": "γ_hr 0.9", "e5": "E5 (its 13 weightings)", "rnd": "PPO + RND",
             "pbrs": "PBRS"}
    w = w.assign(series=w["variant"].map(lambda v: names.get(v, v)))
    rows = []
    for name in E3_ORDER + [n for n in w["series"].unique() if n not in E3_ORDER]:
        walk = w[(w["series"] == name) & (w["share"] == "walk_share")]
        over = w[(w["series"] == name) & (w["share"] == "overhead_share")]
        if walk.empty or over.empty:
            continue
        a, b = walk.iloc[0], over.iloc[0]
        rows.append([name, ci(pct, a["mean"], a["ci_low"], a["ci_high"]),
                     ci(pct, b["mean"], b["ci_low"], b["ci_high"])])
    return table(["Series", "Game time walking [95% CI]", "The walker's overhead: the most click-ahead saves"], rows,
                 numeric=[1, 2])


def sim_to_real() -> str:
    s = read("sim_to_real_families").fillna("")
    rows = [[r["family"], int(r["cases"]), r["within_gate"], r["XP/hr"], r["output/hr"], r["duration"]]
            for _, r in s.iterrows()]
    total = s["cases"].sum()
    inside = sum(int(x.split(" of ")[0]) for x in s["within_gate"])
    gated = sum(int(x.split(" of ")[1]) for x in s["within_gate"])
    rows.append(["All", int(total), f"{inside} of {gated}", "", "", ""])
    return table(["Family", "Cases", "Metrics within ±20%", "XP/hr (sim ÷ server)", "Output/hr", "Duration"], rows,
                 numeric=[1])


def gem_store() -> str:
    g = read("gem_store_rounds")
    rows = [[r["series"], r["round"], ci(levels, r["total_level"], r["total_level_low"], r["total_level_high"]),
             gp_ci(r["net_worth"], r["net_worth_low"], r["net_worth_high"]),
             ci(pct, r["gem_store_share"], r["gem_store_share_low"], r["gem_store_share_high"])]
            for _, r in g.iterrows()]
    return table(["Weighting", "Round", "Total level", "Net worth, gp", "Game time buying uncut emeralds"], rows,
                 numeric=[2, 3, 4])


# --- the document ------------------------------------------------------------------------------------------------

FIGURE_LIST = (  # name, size class, APA title, note
    ("progress", "", "Total Level and Net Worth at Each 2-Hour Checkpoint of Evaluation",
     "E1's four baselines (grey, 30 episodes each) and E3's five weightings (the mean over five training seeds, each "
     "the mean of 30 episodes; band: bootstrap 95% CI)."),
    ("pareto", "narrow", "The Skill–Wealth Trade-Off at Hour 20",
     "Skill gain in units of the scripted guide's, wealth gain in units of greedy GP/hr's. Blue: E3's five agents, "
     "one per weighting; orange: E5's one weight-conditioned agent at its evaluated weightings. Each staircase is a "
     "method's front; the legend gives the hypervolumes."),
    ("mix", "narrow", "Each Policy's Activity Mix in Evaluation",
     "Each activity's share of the 20 game-hours (the mean over the policy's episodes, and for an agent over its "
     "five training seeds). Woodcutting includes chopping that burns or fletches the logs where they are cut, as the "
     "option catalog files those options."),
    ("learning_e3", "", "E3's Learning Curves",
     "Episode reward in units of E1's ideal point, the mean over five runs with a 95% CI band. The grey line is E1's "
     "best baseline at that weighting. Each run's changepoints are ticks along the foot and a sudden jump is a "
     "triangle at the top; the title counts each run's verdict (the decision log's OQ-82 (c) rule)."),
    ("time_e3", "", "E3's Time Allocation Over Training",
     "Each activity's share of game time in each 100,000-decision block of training episodes."),
    ("learning_rq4", "", "RQ4's Learning Curves at (.5, .5)",
     "The exploration bonus (E4), the discount (E6a) and potential-based shaping (E6b), each against E3's plain PPO "
     "(γ_hr = 0.99)."),
    ("time_rq4", "", "RQ4's Time Allocation Over Training",
     "As Figure S5, for E4, E6a and E6b against E3's plain PPO at (.5, .5)."),
    ("discovery", "narrow", "When Each Activity Is Discovered at (.5, .5)",
     "By plain PPO and by PPO + RND: the first 100,000-decision block of training in which the activity takes at "
     "least 5% of the game time, one dot per run; the right column counts the runs that discover it."),
    ("entropy", "", "The Policy's Entropy Over Training", "In nats, the mean over each series' runs."),
)


def figure(name: str, size: str, title: str, note: str, number: int) -> str:
    """An APA figure: its number in bold, its title in italics, the image, and a note (with the figure's file)."""
    cls = f' class="{size}"' if size else ""
    src = Path("../../results/figures") / f"{name}.png"
    return (f'<figure{cls}>\n<p class="figure-number">Figure S{number}</p>\n<p class="figure-title">{esc(title)}</p>\n'
            f'<img src="{src.as_posix()}" alt="{esc(title)}">\n'
            f'<p class="figure-note"><i>Note.</i> {esc(note)} (<code>{esc(name)}</code>)</p>\n</figure>')


def apa_table(number: int, title: str, body: str, note: str = "") -> str:
    """An APA table: its number in bold, its title in italics, the table, and a note below if it has one. The note
    is HTML."""
    note = f'\n<p class="table-note"><i>Note.</i> {note}</p>' if note else ""
    return (f'<div class="apa-table">\n<p class="table-number">Table S{number}</p>\n'
            f'<p class="table-title">{esc(title)}</p>\n{body}{note}\n</div>')


def supporting() -> str:
    tables = [
        ("The Experiments as Run", experiments(),
         "In the numbering used since November 9 (the proposal's E2 to E5 are now E3 to E6b; the sanity ladder, E2, "
         "is new). Every training run is 2 million decisions unless it says otherwise; every configuration has five "
         "training seeds, each evaluated on the same 30 seeded 20-hour episodes."),
        ("Every Policy at the First Checkpoint (Hour 2)", checkpoint(2),
         "A trained policy's mean is over its five training seeds, each the mean of its 30 episodes; the CI is a "
         "bootstrap over the seeds. A baseline's is over its 30 episodes."),
        ("Every Policy at the Last Checkpoint (Hour 20)", checkpoint(20), "As Table S2."),
        ("The Reward's Weighted Value Against E1's Best Baseline", weighted(),
         "The value is u · (skill gain ÷ 323.87 levels) + (1 − u) · (wealth gain ÷ 1,763,863 gp) over the 20 hours, "
         "at the weighting the agent trained for; E1's best baseline is the one with the highest value there."),
        ("RQ4: What Changes at (.5, .5)", rq4(),
         "All at (.5, .5); 0.57 is greedy GP/hr's weighted value there, E1's best. “Seeds” counts the seeds at "
         "hour 20: PBRS's fifth seed's evaluation episodes stop at the evaluator's cap of 100,000 decisions before "
         "hour 20. “Runs reaching 0.57 in training”: the training decisions by which a run's learning curve holds "
         "at or above it."),
        ("RQ3: One Weight-Conditioned Agent Against Five", pareto(),
         "Each method's front at hour 20, in units of E1's best 20-hour gain on each objective. Training hours are "
         "each run's own wall time; the runs trained about five at a time on one machine."),
        ("RQ2: Gradual or Sudden Learning, per Run", verdicts(),
         "Each run's verdict by the decision log's rule on its learning curve's changepoints (OQ-82 (c)). A run with "
         "no gain ends no higher than it starts."),
        ("H2: How Alike a Series' Own Seeds' Activity Mixes Are", consistency(),
         "The Jensen–Shannon divergence between two seeds' activity mixes in evaluation, in bits (0: the same mix; "
         "1: no activity in common)."),
        ("H2: How Alike E3's Weightings' Activity Mixes Are", divergence(), "As Table S8, between weightings."),
        ("RQ5: The Bound on Click-Ahead Pathing", walking(),
         "The walker's overhead is the game time it spends beyond the shortest walk; a perfect learned click-ahead "
         "could save at most that. The scripted prayer flick never drains prayer and gets the prayer's full effect, "
         "so a learned flick cannot beat it."),
        ("The Simulator Against the Server (the Calibration Gate)", sim_to_real(),
         "Every calibration case's latest server runs against the simulator (sim-v1.2; the experiments ran on "
         "sim-v1.4, which plays out the same wherever sim-v1.2 completes). The ratio ranges are the simulator's over "
         "the server's; each metric outside ±20% is explained in <code>results/summary/sim-to-real/README.md</code>."),
        ("The Trainer's Two Changes: E3's First Round Against Its Rerun", gem_store(),
         "On November 15 the trainer stopped bootstrapping the value at the 20-hour limit (the episode really ends "
         "there, and the observation has the time left) and counted each decision as at least 100 ticks; all 50 runs "
         "were trained again. At the mixed weightings, the first round found the Gem Store trade (buying uncut "
         "emeralds in a shop to sell on the GE) in five of 15 runs, and the rerun in none."),
    ]
    body = "\n".join(apa_table(i + 1, title, content, note) for i, (title, content, note) in enumerate(tables))
    figures = "\n".join(figure(name, size, title, note, i + 1)
                        for i, (name, size, title, note) in enumerate(FIGURE_LIST))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Supporting Results</title>
<link rel="stylesheet" href="report.css"></head>
<body>
<h1>Supporting Results for the Progress Report</h1>
<h1>Learning to Climb: Hierarchical Reinforcement Learning for Skill and Wealth Accumulation in 2009Scape</h1>
<p>Caleb Griffin, School of Computing, Wichita State University. CS898BG: Reinforcement Learning, Dr. Sourabh Bose.
{DATE}. The tables and figures behind the progress report, from
the committed experiment summaries (<code>results/summary/</code>), rebuilt by <code>scripts/figures.py</code> and
<code>scripts/progress_report.py</code>. Weightings are (skill, wealth), each objective in units of E1's best 20-hour
gain on it (323.87 levels, the scripted guide's; 1,763,863 gp, greedy GP/hr's). CI is a bootstrap 95% confidence
interval.</p>
<h2>Supplemental Tables</h2>
{body}
<h2 class="page-break">Supplemental Figures</h2>
{figures}
</body></html>
"""


# --- printing ------------------------------------------------------------------------------------------------------

def edge() -> Path:
    for path in EDGE:
        if path.exists():
            return path
    raise SystemExit("Microsoft Edge isn't installed where this looks: " + ", ".join(map(str, EDGE)))


def print_pdf(page: Path, pdf: Path) -> None:
    """Prints a page to PDF with headless Edge, in a profile of its own so that a running Edge doesn't take it. Edge
    can return before the file is written, so this waits for the file's size to hold for a second."""
    pdf.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        subprocess.run([str(edge()), "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={profile}", f"--print-to-pdf={pdf}", page.resolve().as_uri()],
                       check=True, capture_output=True, timeout=180)
        size, deadline = -1, time.monotonic() + 120
        while time.monotonic() < deadline:
            now = pdf.stat().st_size if pdf.exists() else -1
            if now > 0 and now == size:
                return
            size = now
            time.sleep(1)
    raise SystemExit(f"Edge didn't write {pdf}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--no-pdf", action="store_true", help="write supporting-results.html only")
    args = parser.parse_args()
    (REPORT / "supporting-results.html").write_text(supporting(), encoding="utf-8")
    print("wrote", REPORT / "supporting-results.html")
    if args.no_pdf:
        return
    for name in ("progress-report", "supporting-results"):
        print_pdf(REPORT / f"{name}.html", REPORT / f"{name}.pdf")
        print("wrote", REPORT / f"{name}.pdf")
    bundle = REPORT / "progress-report-submission.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(REPORT / "progress-report.pdf", "1-progress-report.pdf")
        z.write(REPORT / "supporting-results.pdf", "2-supporting-results.pdf")
        z.write(PROPOSAL, f"3-original-proposal-{PROPOSAL.name}")
    print("wrote", bundle)


if __name__ == "__main__":
    main()
