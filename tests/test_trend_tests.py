"""D196: Mann-Kendall, Sen's slope and Benjamini-Hochberg behave as the textbook says."""

import numpy as np
import pytest

from atlas.analysis.monsoon import fdr, mann_kendall, sen_slope


def test_mann_kendall_finds_a_clear_trend_and_not_noise():
    rng = np.random.default_rng(0)
    up = list(np.arange(30) * 0.5 + rng.normal(0, 3, 30))
    s, p = mann_kendall(up)
    assert s > 0 and p < 1e-4
    assert mann_kendall(list(rng.normal(0, 1, 30)))[1] > 0.05
    assert mann_kendall([1.0] * 12) == (0.0, 1.0)  # all ties: no trend


def test_sen_slope_ignores_one_outlier_year():
    years = list(range(2000, 2020))
    values = [2.0 * (y - 2000) for y in years]
    values[5] = 500.0
    assert sen_slope(years, values) == pytest.approx(2.0)


def test_benjamini_hochberg_q_values_and_labels():
    rows = [
        {"mann_kendall_p": p, "lag1_autocorrelation": a}
        for p, a in [(0.001, 0.0), (0.01, 0.5), (0.03, 0.0), (0.04, 0.0), (0.5, 0.0)]
    ]
    out = fdr(rows)
    assert [r["fdr_q"] for r in out] == [0.005, 0.025, 0.05, 0.05, 0.5]
    assert out[0]["significance"] == "significant (5% false discovery rate)"
    assert out[1]["significance"].endswith("autocorrelated, so weaker than it looks")
    assert out[2]["significance"] == "not significant"  # q = 0.05 is not below 0.05
