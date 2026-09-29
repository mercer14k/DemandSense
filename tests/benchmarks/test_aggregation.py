import math

import pytest

from scripts.benchmark import aggregate


def test_volume_weighted_metrics_and_undefined_scale_count():
    rows = [
        {
            "group": "all",
            "model": "ridge",
            "actual_total": 10,
            "test_points": 2,
            "mae": 1,
            "mase": None,
            "rmse": 2,
            "bias": 0.2,
            "coverage_80": 1,
            "coverage_95": 1,
        },
        {
            "group": "all",
            "model": "ridge",
            "actual_total": 90,
            "test_points": 2,
            "mae": 5,
            "mase": 2,
            "rmse": 4,
            "bias": -0.1,
            "coverage_80": 0.5,
            "coverage_95": 1,
        },
    ]
    result = aggregate(rows)[0]
    assert result["wape"] == pytest.approx(12 / 100)
    assert result["bias"] == pytest.approx(-7 / 100)
    assert result["rmse"] == pytest.approx(math.sqrt(10))
    assert result["mase"] == 2 and result["mase_defined_series"] == 1
    assert result["coverage_80"] == 0.75
