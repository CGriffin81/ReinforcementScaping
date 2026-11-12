"""The report's figures, drawn with matplotlib from the measures' tables (rlscape.analysis.measures). Each function
returns its figure; scripts/figures.py saves it as PDF and PNG with its data beside it as CSV (the table view).

The style follows the dataviz method's reference palette (light mode, for print):
- categorical hues in its fixed order (`SERIES`), assigned by entity, never by rank;
- 1.5 pt lines, CI bands as a 10% wash, hairline solid gridlines on y only, no top or right spine;
- a legend for two series or more, text in ink (never a series color), and gray for a folded "other".

Each figure's color sets were checked with the method's validator (dataviz `validate_palette.js`, 2026-11-11):
the five weightings and the seven activity hues as adjacent sets; aqua with green, with blue, and with violet and
orange; and blue with orange, as all pairs. Aqua, yellow and magenta are below 3:1 contrast on the surface, so each
figure's CSV is its table view.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # files only, no window: before pyplot loads a backend
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = SERIES
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE, OTHER_FILL = "#e1e0d9", "#c3c2b7", "#fcfcfb", "#c3c2b7"
WIDTH = 6.5  # inches: a report's text width
STYLE = {
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans"], "font.size": 8,
    "axes.titlesize": 8.5, "axes.titleweight": "semibold", "axes.titlelocation": "left", "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5, "legend.frameon": False,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": AXIS, "ytick.color": AXIS,
    "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
    "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-", "axes.axisbelow": True,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "lines.linewidth": 1.5, "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
    "pdf.fonttype": 42, "savefig.dpi": 200, "savefig.bbox": "tight",
}
plt.rcParams.update(STYLE)

DECISIONS = FuncFormatter(lambda x, _: "0" if x == 0 else f"{x / 1e6:g}M")


def _panels(n: int, height: float, cols: int | None = None, sharey: bool = False):
    cols = cols or n
    rows = -(-n // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(WIDTH, height * rows), sharex=True, sharey=sharey,
                             squeeze=False, layout="constrained")
    for ax in axes.flat[n:]:
        ax.set_visible(False)
    return fig, list(axes.flat[:n])


def _band(ax, x, row_mean, low, high, color, label):
    ax.fill_between(x, low, high, color=color, alpha=0.10, linewidth=0)
    ax.plot(x, row_mean, color=color, label=label)


def _end_labels(ax, items: Sequence[tuple[str, float, float]], gap: float = 8.0) -> None:
    """Name lines at their right ends (`items`: text, x, y), spaced at least `gap` points apart; a label moved off
    its line's end gets a hairline leader back to it."""
    if not items:
        return
    ax.figure.canvas.draw()  # the axes' final limits, for display coordinates
    to_points = ax.transData + ax.figure.dpi_scale_trans.inverted()
    placed = sorted(((to_points.transform((x, y))[1] * 72, text, x, y) for text, x, y in items))
    ys = [p[0] for p in placed]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + gap)
    shift = max(0.0, ys[-1] - placed[-1][0]) / 2 if len(ys) > 1 else 0.0  # centre the stack on the lines
    for (y0, text, x, y), y1 in zip(placed, ys):
        dy = y1 - shift - y0 if len(ys) > 1 else 0.0
        moved = abs(dy) > 1
        ax.annotate(text, (x, y), xytext=(10 if moved else 3, dy), textcoords="offset points", va="center",
                    color=INK2, fontsize=7, annotation_clip=False,
                    arrowprops={"arrowstyle": "-", "color": AXIS, "linewidth": 0.5, "shrinkA": 0, "shrinkB": 1}
                    if moved else None)


# --- learning curves -----------------------------------------------------------------------------------------------

def learning_curves(stats: pd.DataFrame, changes: pd.DataFrame, verdicts: pd.DataFrame,
                    panels: Sequence[tuple[str, Sequence[str]]], colors: Mapping[str, str],
                    references: Mapping[str, tuple[str, float]] | None = None, cols: int | None = None):
    """Mean episode reward per bin over each series' seeds, with its 95% CI (`stats`: series, to_step, mean,
    ci_low, ci_high), one panel per `panels` entry (its title and series). Each run's changepoints are ticks along
    the panel's foot, its sudden jump a triangle at the top (`changes`: series, step, sudden). Each series' runs'
    verdicts are counted in its panel's title when the panel has one series, else in the figure's legend.
    `references` gives a panel a labelled level (e.g. E1's best baseline there)."""
    fig, axes = _panels(len(panels), 1.9, cols)
    single = all(len(series) == 1 for _, series in panels)

    def tally(s: str) -> str:
        counts = verdicts[verdicts["series"] == s]["verdict"].value_counts()
        text = ", ".join(f"{counts[v]} {v}" for v in ("sudden", "gradual", "no gain") if v in counts)
        return f"{s} ({text})" if text else s

    for ax, (title, series) in zip(axes, panels):
        for s in series:
            rows = stats[stats["series"] == s].sort_values("to_step")
            _band(ax, rows["to_step"], rows["mean"], rows["ci_low"], rows["ci_high"], colors[s], tally(s))
            mine = changes[changes["series"] == s]
            sudden = mine["sudden"].astype(bool)
            # an empty marker line on the axis transform collapses constrained layout, so each is drawn only if any
            if (~sudden).any():
                ax.plot(mine.loc[~sudden, "step"], np.full((~sudden).sum(), 0.015), "|", color=colors[s],
                        markersize=5, transform=ax.get_xaxis_transform(), clip_on=False)
            if sudden.any():
                ax.plot(mine.loc[sudden, "step"], np.full(sudden.sum(), 0.97), "v", color=colors[s], markersize=5,
                        markeredgecolor=SURFACE, markeredgewidth=0.8, transform=ax.get_xaxis_transform(),
                        clip_on=False)
        if references and title in references:
            name, level = references[title]
            ax.axhline(level, color=MUTED, linewidth=0.8)
            ax.annotate(name, (0.99, level), xycoords=("axes fraction", "data"), xytext=(0, 2),
                        textcoords="offset points", ha="right", va="bottom", color=INK2, fontsize=6.5)
        ax.set_title(tally(series[0]) if single else title)
        ax.set_xlim(0, stats["to_step"].max())
        ax.xaxis.set_major_formatter(DECISIONS)
        ax.set_xlabel("Training decisions")
    cols = cols or len(panels)
    for ax in axes[::cols]:
        ax.set_ylabel("Episode reward\n(E1's ideal point = 1)")
    if not single:
        handles = {}  # each series once, though it's in several panels
        for ax in axes:
            for h, n in zip(*ax.get_legend_handles_labels()):
                handles.setdefault(n, h)
        fig.legend(list(handles.values()), list(handles), loc="outside lower center", ncols=min(len(handles), 3))
    return fig


# --- progress at the checkpoints (RQ1) -----------------------------------------------------------------------------

def progress(tables: Mapping[str, pd.DataFrame], labels: Mapping[str, str], colors: Mapping[str, str],
             baselines: Sequence[str]):
    """Each metric's panel (`tables`: its title to a measures.progress table) over the game hours: trained variants
    as lines with their CIs over training seeds, baselines as thin gray lines named at their ends."""
    fig, axes = _panels(len(tables), 2.4)
    for ax, (title, table) in zip(axes, tables.items()):
        ends = []
        for variant, rows in table.groupby("variant", sort=False):
            rows = rows.sort_values("hour")
            if variant in baselines:
                ax.plot(rows["hour"], rows["mean"], color=MUTED, linewidth=0.9)
                ends.append((labels.get(variant, variant), rows["hour"].iloc[-1], rows["mean"].iloc[-1]))
            elif variant in colors:
                _band(ax, rows["hour"], rows["mean"], rows["ci_low"], rows["ci_high"], colors[variant],
                      labels.get(variant, variant))
        ax.set_title(title)
        ax.set_xlabel("Game hours")
        ax.set_xticks(range(0, 21, 4))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1e6:g}M" if abs(v) >= 1e6 else f"{v:,.0f}"))
        _end_labels(ax, ends)
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(handles, names, loc="outside lower center", ncols=min(len(names), 5))
    return fig


# --- time allocation -----------------------------------------------------------------------------------------------

def activity_colors(order: Sequence[str]) -> dict[str, str]:
    """The figure's activities in their fixed order: the first seven take the categorical hues, then `other`."""
    return {a: (SERIES[i] if a != "other" else OTHER_FILL) for i, a in enumerate(order)}


def fold(shares: pd.DataFrame, kept: Sequence[str], keys: Sequence[str]) -> pd.DataFrame:
    """Shares with every activity outside `kept` summed into `other`."""
    frame = shares.assign(activity=shares["activity"].where(shares["activity"].isin(kept), "other"))
    return frame.groupby([*keys, "activity"], as_index=False, sort=False)["share"].sum()


def time_allocation(shares: pd.DataFrame, panels: Sequence[tuple[str, str]], colors: Mapping[str, str],
                    cols: int | None = None):
    """Stacked areas of each panel's series' mean game-time share per activity across its training bins
    (`shares`: series, to_step, activity, share, folded to `colors`' activities)."""
    order = list(colors)
    fig, axes = _panels(len(panels), 1.8, cols, sharey=True)
    for ax, (title, series) in zip(axes, panels):
        table = shares[shares["series"] == series].pivot_table(index="to_step", columns="activity", values="share",
                                                               aggfunc="sum", fill_value=0)
        table = table.reindex(columns=order, fill_value=0)
        ax.stackplot(table.index, *[table[a] for a in order], colors=[colors[a] for a in order],
                     edgecolor=SURFACE, linewidth=0.4, labels=order)
        ax.set_title(title)
        ax.set_ylim(0, 1)
        ax.set_xlim(0, table.index.max())
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.xaxis.set_major_formatter(DECISIONS)
        ax.grid(False)
    for ax in axes:
        ax.set_xlabel("Training decisions")
    axes[0].set_ylabel("Share of game time")
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(handles[::-1], names[::-1], loc="outside right center")
    return fig


def activity_mix(shares: pd.DataFrame, rows: Sequence[tuple[str, str]], colors: Mapping[str, str]):
    """One 100% bar per row (`rows`: its label and policy variant) of the evaluated policies' mean game-time share
    per activity (`shares`: variant, activity, share, folded to `colors`' activities)."""
    order = list(colors)
    fig, ax = plt.subplots(figsize=(WIDTH, 0.32 * len(rows) + 0.9), layout="constrained")
    for y, (label, variant) in enumerate(rows):
        mine = shares[shares["variant"] == variant].set_index("activity")["share"].reindex(order, fill_value=0)
        left = 0.0
        for a in order:
            ax.barh(y, mine[a], left=left, height=0.62, color=colors[a], edgecolor=SURFACE, linewidth=1,
                    label=a if y == 0 else None)
            left += mine[a]
    ax.set_yticks(range(len(rows)), [label for label, _ in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel("Share of game time in evaluation (20 hours)")
    ax.grid(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.legend(loc="outside lower center", ncols=min(len(order), 8))
    return fig


# --- discovery -----------------------------------------------------------------------------------------------------

def discovery_timeline(found: pd.DataFrame, series: Sequence[str], colors: Mapping[str, str], max_step: float):
    """Each run's discovery of each activity (`found`: series, seed, activity, to_step; NaN never), one row per
    activity found by any run, a dot per run, each series on its own line within the row. The right margin counts
    the runs that found it."""
    found = found[found["series"].isin(series)]
    seen = found.dropna(subset=["to_step"])
    order = seen.groupby("activity")["to_step"].median().sort_values().index.tolist()
    fig, ax = plt.subplots(figsize=(WIDTH, 0.28 * len(order) + 1.0), layout="constrained")
    offsets = np.linspace(-0.18, 0.18, len(series)) if len(series) > 1 else [0.0]
    for offset, s in zip(offsets, series):
        mine = seen[seen["series"] == s]
        rng = np.random.default_rng(0)  # a little spread, so runs found in the same bin stay apart
        y = mine["activity"].map({a: i for i, a in enumerate(order)}) + offset + rng.uniform(-0.05, 0.05, len(mine))
        ax.scatter(mine["to_step"], y, s=22, color=colors[s], edgecolors=SURFACE, linewidths=1, label=s, zorder=3)
        runs = found[found["series"] == s].groupby("activity")["to_step"].agg(lambda t: t.notna().sum())
        total = found[found["series"] == s]["seed"].nunique()
        for i, a in enumerate(order):
            ax.annotate(f"{int(runs.get(a, 0))}/{total}", (1, i + offset), xycoords=("axes fraction", "data"),
                        xytext=(4, 0), textcoords="offset points", va="center", fontsize=6.5, color=INK2)
    ax.set_yticks(range(len(order)), order)
    ax.invert_yaxis()
    ax.set_xlim(0, max_step)
    ax.xaxis.set_major_formatter(DECISIONS)
    ax.set_xlabel("Training decisions by the end of the bin in which the activity first took 5% of game time")
    ax.grid(True, axis="x")
    ax.grid(False, axis="y")
    ax.tick_params(axis="y", length=0)
    fig.legend(loc="outside lower center", ncols=len(series))
    return fig


# --- the front -----------------------------------------------------------------------------------------------------

def pareto(methods: Mapping[str, pd.DataFrame], colors: Mapping[str, str], baselines: pd.DataFrame,
           hv: pd.DataFrame, labels: Mapping[str, str]):
    """Each method's policies (`methods`: name to a table of variant, skill, wealth with CIs over training seeds:
    skill_low/high, wealth_low/high), joined along their front, and E1's baselines as gray points named beside them.
    The legend gives each method's hypervolume (`hv`: method, mean, ci_low, ci_high)."""
    from rlscape.analysis.measures import front

    fig, ax = plt.subplots(figsize=(WIDTH * 0.62, WIDTH * 0.56), layout="constrained")
    for method, table in methods.items():
        row = hv[hv["method"] == method]
        name = method
        if not row.empty:
            r = row.iloc[0]
            ci = f" [{r['ci_low']:.2f}, {r['ci_high']:.2f}]" if pd.notna(r["ci_low"]) else ""
            name = f"{method}: hypervolume {r['mean']:.2f}{ci}"
        ordered = table.sort_values("skill")
        ax.errorbar(ordered["skill"], ordered["wealth"],
                    xerr=[ordered["skill"] - ordered["skill_low"], ordered["skill_high"] - ordered["skill"]],
                    yerr=[ordered["wealth"] - ordered["wealth_low"], ordered["wealth_high"] - ordered["wealth"]],
                    fmt="none", ecolor=colors[method], elinewidth=0.8, alpha=0.6)
        edge = front(ordered)  # the attainment staircase: what the method's mean policies dominate
        ax.plot(edge["skill"], edge["wealth"], color=colors[method], linewidth=1, drawstyle="steps-pre")
        ax.plot(ordered["skill"], ordered["wealth"], "o", color=colors[method], markersize=5,
                markeredgecolor=SURFACE, markeredgewidth=1, label=name, zorder=3)
        if "label" in ordered:
            for _, r in ordered.dropna(subset=["label"]).iterrows():
                ax.annotate(r["label"], (r["skill"], r["wealth"]), xytext=(4, 3), textcoords="offset points",
                            fontsize=6.5, color=INK2)
    ax.scatter(baselines["skill"], baselines["wealth"], s=22, color=MUTED, edgecolors=SURFACE, linewidths=1,
               zorder=2)
    for _, r in baselines.iterrows():
        ax.annotate(labels.get(r["variant"], r["variant"]), (r["skill"], r["wealth"]), xytext=(4, -8),
                    textcoords="offset points", fontsize=6.5, color=INK2)
    ax.axhline(0, color=AXIS, linewidth=0.8)
    ax.axvline(0, color=AXIS, linewidth=0.8)
    ax.set_xlabel("Skill gain in 20 hours ÷ the guide's (levels)")
    ax.set_ylabel("Wealth gain in 20 hours ÷ greedy GP/hr's")
    ax.grid(True, axis="both")
    fig.legend(loc="outside lower center")
    return fig


# --- entropy -------------------------------------------------------------------------------------------------------

def entropy(stats: pd.DataFrame, panels: Sequence[tuple[str, Sequence[str]]], colors: Mapping[str, str]):
    """The policy's mean entropy (nats) over the options open, per training bin, with its CI over seeds
    (`stats`: series, to_step, mean, ci_low, ci_high)."""
    fig, axes = _panels(len(panels), 2.0, sharey=True)
    for ax, (title, series) in zip(axes, panels):
        for s in series:
            rows = stats[stats["series"] == s].sort_values("to_step")
            _band(ax, rows["to_step"], rows["mean"], rows["ci_low"], rows["ci_high"], colors[s], s)
        ax.set_title(title)
        ax.set_xlim(0, stats["to_step"].max())
        ax.xaxis.set_major_formatter(DECISIONS)
        ax.set_xlabel("Training decisions")
        ax.legend(loc="upper right")
    axes[0].set_ylabel("Policy entropy (nats)")
    return fig
