"""The analysis (rlscape/analysis/, scripts/figures.py): its measures on known geometry and known curves, on a real
tiny training run's behaviour and on real evaluation traces, and the figure script end to end on a real tiny
experiment's published summaries beside E1's committed one."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rlscape.analysis import measures as ms
from rlscape.analysis.activities import ACTIVITIES, COMBAT, GATHERING, OTHER, activity
from rlscape.envs.weights import SKILL_UNIT, WEALTH_UNIT
from rlscape.gamedata import server as gd

REPO = Path(__file__).resolve().parents[1]
needs_server_data = pytest.mark.skipif(not gd.SERVER_CONFIGS.exists(), reason="server submodule missing")
WEIGHTING = "normalised_weights0.5-0.5"  # E3's variant, so the figure script reads the tiny run as E3's
TINY = {"seeds": [0], "total_decisions": 48, "n_envs": 2, "vec_env": "dummy", "device": "cpu",
        "env": {"hours": 0.25}, "ppo": {"gamma_hr": 0.9, "n_steps": 8, "batch_size": 8, "n_epochs": 1},
        "checkpoint_every": 16, "decision_log": True, "sweep": {"env.normalised_weights": [[0.5, 0.5]]}}
FAMILIES = {"gathering": set(GATHERING), "combat": set(COMBAT), "processing": {"smithing", "cooking", "firemaking",
            "prayer"}, "alchemy": {"alchemy"}, "selling": {"selling"}, "buying": {"buying"},
            "inventory": {"banking", OTHER}, "loot": {OTHER}}


def _script():
    spec = importlib.util.spec_from_file_location("figures_script", REPO / "scripts" / "figures.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --- activities ----------------------------------------------------------------------------------------------------

def test_options_group_into_oq76s_twenty_activities_and_other():
    assert len(ACTIVITIES) == 20 and OTHER not in ACTIVITIES
    cases = {"skill_woodcutting_xp1": "woodcutting", "skill_woodcutting_fletch": "woodcutting",
             "skill_runecrafting_gp2": "runecrafting", "fight_melee_gp2_defensive": "melee",
             "fight_magic_xp3": "magic", "smelt_iron": "smithing", "smith_mithril": "smithing",
             "cook_fish": "cooking", "burn_logs": "firemaking", "bury_bones": "prayer", "sell_ge_1621": "selling",
             "sell_store_misc": "selling", "buy_shop_1621": "buying", "high_alch_440": "alchemy",
             "low_alch_misc": "alchemy", "bank_withdraw_for_cook_fish": "banking", "bank_deposit": "banking",
             "drop_440": OTHER, "take_knife": OTHER, "reclaim_gravestone": OTHER, "loot_valuable": OTHER}
    assert {option: activity(option) for option in cases} == cases


# --- the front ------------------------------------------------------------------------------------------------------

def test_the_hypervolume_is_the_area_the_points_dominate_above_the_fresh_character():
    assert ms.hypervolume([(1, 1)]) == 1
    assert ms.hypervolume([(1, 0.1), (0.5, 0.5)]) == pytest.approx(0.1 + 0.25 - 0.05)
    assert ms.hypervolume([(0.4, 0.4), (0.5, 0.5), (1, 0.1)]) == pytest.approx(0.3)  # dominated: adds nothing
    assert ms.hypervolume([(1, -0.2), (-0.1, 2)]) == 0  # behind the fresh character on either objective
    assert ms.hypervolume([(2, 1)], reference=(1, 0)) == 1
    pts = pd.DataFrame({"skill": [1, 0.5, 0.4, 0.2], "wealth": [0.1, 0.5, 0.4, 0.6]})
    assert list(ms.front(pts).itertuples(index=False, name=None)) == [(0.2, 0.6), (0.5, 0.5), (1, 0.1)]


def test_labels_name_the_variant_the_training_seed_and_e5s_weighting():
    assert ms.parse_label("normalised_weights0.5-0.5/seed3") == ("normalised_weights0.5-0.5", 3, None)
    assert ms.parse_label("e5/seed2@0.25") == ("e5", 2, 0.25)
    assert ms.parse_label("rnd/seed0") == ("rnd", 0, None)
    assert ms.parse_label("scripted_guide") == ("scripted_guide", None, None)


def test_hypervolumes_are_per_training_seed_in_normalised_units_with_a_ci_over_the_seeds():
    # two seeds of two weightings, each policy's gain the same on every evaluation seed
    gain = {("a", 0): (1, 0), ("b", 0): (0, 1), ("a", 1): (1, 0.5), ("b", 1): (0.5, 1)}
    episodes = pd.DataFrame([{"policy": f"{v}/seed{k}", "seed": s, "r_skill": x * SKILL_UNIT,
                              "r_wealth": y * WEALTH_UNIT} for (v, k), (x, y) in gain.items() for s in range(3)])
    pts = ms.points(ms.gains(episodes))
    assert set(pts["episodes"]) == {3}
    per_seed, summary = ms.hypervolumes(pts, {"sweep": ["a", "b"]})
    assert per_seed.set_index("train_seed")["hypervolume"].to_dict() == pytest.approx({0: 0, 1: 0.75})
    row = summary.iloc[0]
    assert (row["seeds"], row["mean"]) == (2, pytest.approx(0.375))
    assert 0 <= row["ci_low"] <= row["mean"] <= row["ci_high"] <= 0.75


# --- learning curves and changepoints -------------------------------------------------------------------------------

def test_a_learning_curve_bins_episodes_by_the_decision_they_ended_and_drops_a_sliver_of_a_last_bin():
    curves = pd.DataFrame({"variant": "", "seed": 0, "step": [100, 900, 1100, 1500, 2050],
                           "reward": [1.0, 3.0, 5.0, 7.0, 9.0]})
    binned = ms.binned_curve(curves, every=1000)
    assert list(binned["bin"]) == [0, 1] and list(binned["episodes"]) == [2, 2]  # 2,050 ends 50 into bin 2
    assert list(binned["reward"]) == [2.0, 6.0] and list(binned["to_step"]) == [1000, 2000]
    assert binned["value"].tolist() == pytest.approx([2 / SKILL_UNIT, 6 / SKILL_UNIT])


def test_the_mean_over_seeds_carries_a_runs_last_value_into_its_empty_bins():
    """2026-11-16: seed 1 finishes an episode only in bins 0 and 3 (a looping run's long episodes), seed 0 in every
    bin to 4. Carried, seed 1 keeps bin 0's value through bins 1 and 2 and bin 3's into bin 4, so each bin has both."""
    curves = pd.DataFrame({"variant": "v", "seed": [0, 0, 0, 0, 0, 1, 1],
                           "step": [500, 1500, 2500, 3500, 4500, 500, 3500],
                           "reward": [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 0.0]})
    carried = ms.carried_curve(ms.binned_curve(curves, every=1000), every=1000)
    seed1 = carried[carried["seed"] == 1].set_index("bin")
    assert list(seed1.index) == [0, 1, 2, 3, 4] and list(seed1["reward"]) == [10.0, 10.0, 10.0, 0.0, 0.0]
    assert list(seed1["carried"]) == [False, True, True, False, True] and list(seed1["episodes"]) == [1, 0, 0, 1, 0]
    assert list(seed1["to_step"]) == [1000, 2000, 3000, 4000, 5000]
    assert not carried[carried["seed"] == 0]["carried"].any() and carried.groupby("bin").size().eq(2).all()


def test_a_runs_last_behaviour_bin_is_left_out_when_under_half_full():
    bins = pd.DataFrame({"variant": "v", "seed": 0, "bin": [0, 1, 2], "from_step": [0, 100, 200],
                         "to_step": [100, 200, 300], "decisions": [100, 100, 8]})
    assert list(ms.full_bins(bins)["bin"]) == [0, 1]
    assert list(ms.full_bins(bins.assign(decisions=[100, 100, 50]))["bin"]) == [0, 1, 2]


def verdicts(y: np.ndarray, every: int = ms.CURVE_BIN) -> tuple[dict, dict, list[int]]:
    """Both rules' verdicts of a curve binned every `every` decisions, and its changepoints' decisions."""
    starts, means = ms.segments(y)
    steps = [s * every for s in starts[1:]]
    return ms.decided_verdict(means), ms.revised_verdict(steps, means, ms.noise(y)), steps


def test_a_step_is_sudden_a_ramp_gradual_and_a_flat_or_falling_curve_has_no_gain_under_both_rules():
    noise = np.random.default_rng(0).normal(0, 0.01, 60)
    step = np.r_[np.zeros(30), np.full(30, 0.3)] + noise
    decided, revised, steps = verdicts(step)
    assert decided["verdict"] == revised["verdict"] == "sudden" and revised["gain"] == pytest.approx(0.3, abs=0.01)
    assert steps[revised["rise"][0]] == 600_000  # BIC lets small spurious segments into noise too
    ramp = np.linspace(0, 0.3, 60) + noise
    assert [v["verdict"] for v in verdicts(ramp)[:2]] == ["gradual", "gradual"]
    assert [v["verdict"] for v in verdicts(noise)[:2]] == ["no gain", "no gain"]
    assert [v["verdict"] for v in verdicts(step[::-1])[:2]] == ["no gain", "no gain"]


def test_a_jump_pelt_splits_over_adjacent_bins_is_one_rise_under_oq82():
    # E3 (.25, .75)'s gem trade, in small: flat, a rise over 120,000 decisions in 2-bin steps, flat
    y = np.r_[np.full(30, 0.25), [0.45, 0.45, 0.85, 0.85, 1.25, 1.25], np.full(24, 1.45)]
    y = y + np.random.default_rng(2).normal(0, 0.005, len(y))
    decided, revised, steps = verdicts(y)
    assert steps == [600_000, 640_000, 680_000, 720_000]
    assert decided["verdict"] == "gradual" and decided["largest_share"] == pytest.approx(0.4 / 1.2, abs=0.02)
    # 720,000 is 120,000 after the rise's first changepoint, so not in it
    assert revised["verdict"] == "sudden" and revised["rise"] == [0, 1, 2]
    assert revised["largest_share"] == pytest.approx(1.0 / 1.2, abs=0.02)


def test_the_rise_from_the_random_start_is_the_warm_ups_not_a_jump():
    y = np.r_[[0.1, 0.1, 0.3, 0.3], np.full(56, 0.4)] + np.random.default_rng(3).normal(0, 0.005, 60)
    decided, revised, steps = verdicts(y)
    assert steps and max(steps) <= ms.WARMUP
    assert decided["verdict"] == "sudden"  # OQ-78 (a)
    assert revised["verdict"] == "no gain" and revised["initial_rise"] == pytest.approx(0.3, abs=0.01)


def test_a_flat_runs_wiggle_after_the_warm_up_is_no_gain():
    y = np.r_[np.full(30, 0.40), np.full(20, 0.43), np.full(10, 0.401)]
    y = y + np.random.default_rng(4).normal(0, 0.005, len(y))
    revised = verdicts(y)[1]
    assert len(revised["rise"]) == 1 and revised["gain"] < ms.NOISE_FLOOR * ms.noise(y)
    assert revised["verdict"] == "no gain"


def test_rises_join_consecutive_rising_changepoints_near_the_first():
    steps = [200_000, 240_000, 260_000, 400_000, 420_000, 600_000]
    jumps = [0.1, 0.2, 0.1, 0.3, -0.1, 0.2]
    assert ms.rises(steps, jumps) == [[0, 1, 2], [3], [5]]  # a fall ends a rise and is in none
    assert ms.rises([0, 50_000, 120_000], [1, 1, 1]) == [[0, 1], [2]]


def test_each_runs_changepoints_are_placed_at_the_decision_their_segment_starts():
    noise = np.random.default_rng(1).normal(0, 0.01, 40)
    value = np.r_[np.zeros(25), np.full(15, 0.2)] + noise
    binned = pd.DataFrame({"variant": "v", "seed": 0, "bin": range(40), "value": value})
    runs, points = ms.run_changes(binned)
    assert runs.iloc[0][["segments", "verdict", "verdict_oq78a"]].tolist() == [2, "sudden", "sudden"]
    assert points.iloc[0][["step", "warmup", "sudden", "sudden_oq78a"]].tolist() == [500_000, False, True, True]


# --- sample efficiency, consistency and milestones ----------------------------------------------------------------

def test_a_run_matches_its_target_from_the_first_bin_it_stays_at_for_five_bins_or_to_its_end():
    def run(seed, values):
        return pd.DataFrame({"variant": "v", "seed": seed, "bin": range(len(values)), "value": values,
                             "to_step": [(b + 1) * 1000 for b in range(len(values))]})
    binned = pd.concat([run(0, [0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0]),  # bins 1-3 dip at 4: from bin 5
                        run(1, [0, 0, 0, 0, 0, 0, 0, 0, 1, 1]),  # only its last two bins, but to its end
                        run(2, [0, 0, 0, 0.99])], ignore_index=True)
    table = ms.sample_efficiency(binned, {"v": 1.0}).set_index("seed")
    assert table["to_step"].tolist()[:2] == [6000, 9000] and table["matched"].tolist() == [True, True, False]
    assert np.isnan(table.loc[2, "to_step"])


def test_the_jensen_shannon_divergence_is_0_for_the_same_mix_and_1_bit_for_nothing_shared():
    assert ms.js_divergence([0.5, 0.5], [0.5, 0.5]) == 0
    assert ms.js_divergence([1, 0], [0, 1]) == pytest.approx(1)
    m = np.array([0.75, 0.25])
    expected = (np.log2(1 / 0.75) + 0.5 * np.log2(0.5 / m[0]) + 0.5 * np.log2(0.5 / m[1])) / 2
    assert ms.js_divergence([1, 0], [0.5, 0.5]) == pytest.approx(expected)


def test_consistency_is_the_mean_divergence_over_a_variants_seed_pairs_of_their_mean_mixes():
    mixes = {0: {"melee": 1.0}, 1: {"melee": 0.5, "mining": 0.5}, 2: {"mining": 1.0}}
    rows = [{"variant": "v", "train_seed": k, "seed": s, "activity": a, "share": share}
            for k, mix in mixes.items() for s in (0, 1) for a, share in mix.items()]
    table = ms.consistency(pd.DataFrame(rows))
    pairs = [ms.js_divergence([1, 0], [0.5, 0.5]), ms.js_divergence([1, 0], [0, 1]),
             ms.js_divergence([0.5, 0.5], [0, 1])]
    assert table.iloc[0][["seeds", "pairs"]].tolist() == [3, 3]
    assert table.iloc[0]["js_bits"] == pytest.approx(np.mean(pairs))


def test_the_level_milestones_are_the_guides_whole_level_gain_in_e1():
    checkpoints = pd.read_csv(REPO / "results" / "summary" / "e1-baselines" / "checkpoints.csv")
    guide = checkpoints[checkpoints.policy == "scripted_guide"].pivot(index="seed", columns="hour",
                                                                     values="total_level")
    assert ms.LEVEL_TARGET == pytest.approx((guide[20] - guide[0]).mean())
    assert ms.MILESTONES["gp_100"][1] == pytest.approx(WEALTH_UNIT * 100_000)


def test_a_milestone_is_reached_at_the_end_of_the_first_decision_past_its_gain():
    gp = ms.MILESTONES["gp_50"][1]
    decisions = pd.DataFrame({"policy": "p", "seed": 0, "decision": range(4), "t1": [6_000, 12_000, 30_000, 60_000],
                              "total_level": [40, 60, 200, 352], "net_worth": [1033, 1033 + gp - 1, 1033 + gp, 2e6]})
    checkpoints = pd.DataFrame({"policy": "p", "seed": 0, "hour": [0], "total_level": [35], "net_worth": [1033]})
    hours = ms.milestones(decisions, checkpoints).set_index("milestone")["hours"]
    assert hours.to_dict() == {"levels_50": 5.0, "levels_100": 10.0, "gp_50": 5.0, "gp_100": 10.0}
    summary = ms.milestone_summary(pd.DataFrame({"s": "x", "milestone": "m", "hours": [1.0, 2.0, np.inf]}), ["s"])
    assert summary.iloc[0][["episodes", "reached", "median_hours"]].tolist() == [3, pytest.approx(2 / 3), 2.0]


# --- behaviour from a real run, traces from real episodes ---------------------------------------------------------

@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    pytest.importorskip("rlscape.agents.ppo")
    if not gd.SERVER_CONFIGS.exists():
        pytest.skip("server submodule missing")
    from rlscape.agents.training import train, variants
    (variant, config), = variants(dict(TINY))
    assert variant == WEIGHTING
    root = tmp_path_factory.mktemp("analysis") / "runs"
    return train(config, "e3-reward-weight-sweep", 0, root / variant / "seed0")


@needs_server_data
def test_every_catalog_option_has_its_familys_activity_and_every_activity_has_options(trained):
    catalog = json.loads((trained / "options.json").read_text(encoding="utf-8"))
    for option in catalog:
        assert activity(option["id"]) in FAMILIES[option["family"]], option
    assert {activity(o["id"]) for o in catalog} == {*ACTIVITIES, OTHER}


@needs_server_data
def test_time_shares_add_up_to_each_bin_and_discovery_is_the_first_bin_at_5_percent(trained):
    from rlscape.eval.behaviour import training_behaviour
    tables = training_behaviour(trained)
    bins, options = (tables[k].assign(variant=WEIGHTING, seed=0) for k in ("bins", "options"))
    shares = ms.time_shares(options, bins)
    assert shares.groupby("bin")["share"].sum().tolist() == pytest.approx([1.0] * len(bins))
    assert set(shares["activity"]) == {*ACTIVITIES, OTHER}
    found = ms.discovery(shares)
    assert len(found) == len(ACTIVITIES) + 1
    for row in found.itertuples():
        mine = shares[shares["activity"] == row.activity].sort_values("bin")
        reached = mine[mine["share"] >= ms.DISCOVERY_SHARE]
        assert (np.isnan(row.bin) if reached.empty else row.bin == reached["bin"].iloc[0]), row


@needs_server_data
def test_an_evaluation_traces_shares_are_its_decisions_durations():
    from rlscape.eval.harness import run_tables
    _, _, decisions = run_tables(["random", "greedy_wealth"], [0, 1], {"horizon_ticks": 6_000})
    shares = ms.trace_shares(decisions)
    assert shares.groupby(["policy", "seed"])["share"].sum().tolist() == pytest.approx([1.0] * 4)
    first = decisions[(decisions.policy == "random") & (decisions.seed == 0)].sort_values("decision")
    ticks = np.diff(np.r_[0, first["t1"]])
    by_activity = pd.Series(ticks, index=first["option"].map(activity)).groupby(level=0).sum() / ticks.sum()
    mine = shares[(shares.policy == "random") & (shares.seed == 0)].set_index("activity")["share"]
    assert mine[mine > 0].sort_index().to_dict() == pytest.approx(by_activity.sort_index().to_dict())


# --- the figure script ----------------------------------------------------------------------------------------------

@needs_server_data
def test_the_figure_script_rebuilds_every_figure_its_published_summaries_allow(trained, tmp_path):
    from rlscape.eval.harness import run_tables, save, summarize
    from rlscape.eval.publish import publish, publish_training
    summary = tmp_path / "summary"
    shutil.copytree(REPO / "results" / "summary" / "e1-baselines", summary / "e1-baselines")
    publish_training(trained.parents[1], "e3-reward-weight-sweep", root=summary, allow_dirty=True)
    policies = ["random", f"{WEIGHTING}/seed0=ppo:{trained / 'model.zip'}"]
    checkpoints, episodes, decisions = run_tables(policies, [0, 1], {"horizon_ticks": 12_000})  # hours 0 and 2
    run = save(tmp_path / "eval", {"policies": policies}, checkpoints, episodes, summarize(checkpoints),
               decisions=decisions)
    publish(run, "e3-reward-weight-sweep", root=summary, allow_dirty=True)

    out = tmp_path / "figures"
    made = _script().build(summary, out, curve_bin=8)
    assert set(made) == {"learning_e3", "time_e3", "entropy", "mix", "progress", "pareto"}
    for name in made:
        assert all((out / f"{name}.{kind}").stat().st_size > 0 for kind in ("pdf", "png", "csv")), name
    hv = pd.read_csv(out / "hypervolume_per_seed.csv")
    assert hv[["method", "train_seed", "policies"]].values.tolist() == [["E3: an agent per weighting", 0, 1]]
    runs = pd.read_csv(out / "verdicts.csv")
    assert runs[["series", "seed"]].values.tolist() == [["E3 (.5, .5)", 0]]
    assert {"verdict", "verdict_oq78a", "initial_rise"} <= set(runs.columns)
    assert set(pd.read_csv(out / "discovery.csv")["series"]) == {"E3 (.5, .5)"}
    efficiency = pd.read_csv(out / "sample_efficiency.csv")
    assert efficiency[["series", "seed"]].values.tolist() == [["E3 (.5, .5)", 0]]
    reached = pd.read_csv(out / "milestones.csv")
    assert len(reached) == 2 * 2 * len(ms.MILESTONES)  # two policies, two seeds
    assert set(pd.read_csv(out / "milestones_summary.csv")["series"]) == {"random", "E3 (.5, .5)"}
    assert pd.read_csv(out / "consistency.csv")[["series", "seeds", "pairs"]].values.tolist() == [
        ["E3 (.5, .5)", 1, 0]]
