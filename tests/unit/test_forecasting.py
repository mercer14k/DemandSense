import copy

import numpy as np
import pytest
from demandsense.forecasting import (
    MODEL_NAMES,
    analyze,
    apply_scenario,
    classify,
    finite_quantile,
    metrics,
    predict_all,
)
from demandsense.generator import generate
from demandsense.schemas import Observation, ScenarioInput


def test_fixed_seed_and_stable_identifiers():
    a, b = list(generate(2, 70)), list(generate(2, 70))
    assert a == b
    assert len({r["record_id"] for r in a}) == len(a)
    assert a != list(generate(2, 70, seed=43))
    assert list(generate(1, 70)) == a[:210]


def test_generator_contract(series):
    for row in series:
        Observation.model_validate(row)
    assert any(r["promotion"] for r in series)
    assert any(r["stockout"] for r in series)
    assert any(r["provenance"]["shock_multiplier"] < 1 for r in series)


def test_hand_computed_metrics():
    result = metrics([10, 20], [12, 18], np.arange(21))
    assert result["wape"] == pytest.approx(4 / 30)
    assert result["rmse"] == 2
    assert result["mase"] == pytest.approx(2 / 7)
    assert result["bias"] == 0
    assert metrics([0, 0], [0, 0], [0] * 21)["wape"] is None
    assert metrics([0, 0], [0, 0], [0] * 21)["mase"] is None


def test_seasonal_naive_exact():
    y = np.tile([1, 2, 3, 4, 5, 6, 7], 10)
    np.testing.assert_array_equal(predict_all(y, 14)["seasonal_naive"], y[:14])


def test_intermittent_decay():
    y = np.array([0, 8, 0, 0, 0, 0, 10, 0] * 10)
    p = predict_all(y, 14)
    assert p["croston_sba"][0] > 0
    assert predict_all(np.r_[y, np.zeros(40)], 14)["tsb"][0] < p["tsb"][0]
    assert classify(y)["class"] == "intermittent"


def test_finite_sample_radius():
    assert finite_quantile([1, 2, 3, 4, 5], 0.8) == 5
    with pytest.raises(ValueError):
        finite_quantile([], 0.8)


def test_complete_deterministic_analysis(series):
    a, b = analyze(series), analyze(series)
    assert a == b
    assert {r["model"] for r in a["leaderboard"]} == set(MODEL_NAMES)
    assert sum(s["selected"] for s in a["leaderboard"]) == 1
    assert a["calibration_origins"][-1]["forecast_start"] < a["origins"][0]["start"]
    assert len(a["backtest"]) == 42
    for p in a["forecast"]:
        assert 0 <= p["lower95"] <= p["lower80"] <= p["point"] <= p["upper80"] <= p["upper95"]


def test_test_window_cannot_influence_model_selection(series):
    before = analyze(series)
    changed = copy.deepcopy(series)
    for r in changed[-42:]:
        r["demand"] = r["demand"] * 100 + 100
    after = analyze(changed)
    assert before["selected_model"] == after["selected_model"]
    assert {s["model"]: s["selection_mae"] for s in before["leaderboard"]} == {
        s["model"]: s["selection_mae"] for s in after["leaderboard"]
    }
    assert before["backtest"][:14][0]["point"] == after["backtest"][:14][0]["point"]


def test_future_changes_do_not_change_prior_origin_prediction(series):
    a = analyze(series)
    changed = copy.deepcopy(series)
    for row in changed[-14:]:
        row["demand"] += 1000
    b = analyze(changed)
    assert [x["point"] for x in a["backtest"]] == [x["point"] for x in b["backtest"]]


def test_latent_ground_truth_is_not_a_model_feature(series):
    a = analyze(series)
    altered = copy.deepcopy(series)
    for row in altered:
        row["provenance"] = {"expected_uncensored": 1e20, "shock_multiplier": 500}
    assert analyze(altered) == a


def test_all_zero_history_is_explicit(series):
    for row in series:
        row["demand"] = 0
    result = analyze(series)
    assert result["classification"]["class"] == "all_zero"
    assert result["metrics"]["wape"] is None
    assert result["metrics"]["mase"] is None
    assert all(p["point"] == 0 for p in result["forecast"])
    assert any("All-zero" in w for w in result["warnings"])


@pytest.mark.parametrize("change", ["gap", "duplicate", "short", "negative", "nan"])
def test_invalid_history_rejected(series, change):
    if change == "gap":
        series.pop(100)
    elif change == "duplicate":
        series[3]["date"] = series[2]["date"]
    elif change == "short":
        series = series[:100]
    elif change == "negative":
        series[0]["demand"] = -1
    else:
        series[0]["demand"] = float("nan")
    with pytest.raises(ValueError):
        analyze(series)


def test_scenario_arithmetic_and_immutability(series):
    baseline = analyze(series)
    saved = copy.deepcopy(baseline)
    inputs = ScenarioInput(name="Promo", uplift_pct=25, start_day=2, end_day=4)
    result = apply_scenario(baseline, inputs)
    assert baseline == saved
    assert result["forecast"][0] == baseline["forecast"][0]
    assert result["forecast"][1]["point"] == pytest.approx(baseline["forecast"][1]["point"] * 1.25)
    assert result["delta_units"] == pytest.approx(sum(p["point"] for p in baseline["forecast"][1:4]) * 0.25)
    with pytest.raises(ValueError):
        apply_scenario(baseline, ScenarioInput(name="Too long", uplift_pct=5, end_day=20))


@pytest.mark.parametrize(
    "patch",
    [
        {"uplift_pct": float("inf")},
        {"uplift_pct": -101},
        {"start_day": 9, "end_day": 2},
        {"shell": "anything"},
    ],
)
def test_scenario_schema_rejects_invalid_input(patch):
    with pytest.raises(ValueError):
        ScenarioInput.model_validate({"name": "Test", "uplift_pct": 10, **patch})
