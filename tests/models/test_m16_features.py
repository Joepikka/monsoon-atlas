"""T214: the M16 rule on hand-built test inputs (not real feeds), as-of safety and the data gate."""

from pathlib import Path

import numpy as np
import pytest
import yaml

from atlas.features import m16

ROOT = Path(__file__).resolve().parents[2]
RAMP = np.arange(1.0, 29.0)  # test input: median 14.5, MAD 7.0 (hand-computed)
SCALE = m16.MAD_SCALE * 7.0


def test_robust_z_matches_a_hand_computed_window():
    out = m16.detect(np.append(RAMP, [60.0, 14.5]))
    assert out["status"][28, 0] == m16.EVALUATED
    assert out["z"][28, 0] == pytest.approx((60.0 - 14.5) / SCALE)  # about 4.38
    assert out["flag_z"][28, 0] and not out["flag_z"][29, 0]


def test_threshold_is_strictly_above_four():
    top, low = 14.5 + m16.THRESHOLD * SCALE, 14.5 - m16.THRESHOLD * SCALE
    for value, flagged in ((top - 0.01, False), (top + 0.01, True), (low - 0.01, True)):
        assert m16.detect(np.append(RAMP, value))["flag_z"][28, 0] == flagged, value  # low too


def test_mad_zero_gives_no_z_and_no_flag():
    out = m16.detect(np.append(np.zeros(28), [100.0]))
    assert out["status"][28, 0] == m16.MAD_ZERO
    assert np.isnan(out["z"][28, 0]) and not out["flag_z"][28, 0] and not out["flag_bound"][28, 0]


def test_missing_values_never_become_zero_or_flag():
    values = np.append(RAMP, [np.nan, 60.0])
    out = m16.detect(values)
    assert out["status"][28, 0] == m16.MISSING
    assert np.isnan(out["z"][28, 0]) and not out["flag_z"][28, 0]
    # the missing day is left out of the next window (27 usable values), not counted as 0
    assert out["status"][29, 0] == m16.EVALUATED
    gappy = np.append(RAMP, [0.0, 60.0])  # the same day read as 0 changes the window
    assert out["z"][29, 0] != m16.detect(gappy)["z"][29, 0]


def test_too_few_valid_values_give_no_z():
    values = np.append(np.full(10, np.nan), np.append(RAMP[:20], [99.0]))
    out = m16.detect(values)  # last row has 20 valid prior days, MIN_VALID is 21
    assert out["status"][-1, 0] == m16.TOO_FEW_VALID and not out["flag_z"][-1, 0]
    assert (out["status"][:28, 0] != m16.EVALUATED).all()  # the first month has no history


def test_unit_bound_flags_and_stays_out_of_later_windows():
    values = np.append(RAMP, [-5.0, 60.0])
    out = m16.detect(values, lower=0.0)
    assert out["flag_bound"][28, 0] and out["status"][28, 0] == m16.BOUND
    assert not out["flag_z"][28, 0]
    # -5 did not enter the window: it is 2..28, median 15, MAD 7
    assert out["z"][29, 0] == pytest.approx((60.0 - 15.0) / SCALE)
    assert not m16.detect(np.append(RAMP, [9e9]), lower=0.0)["flag_bound"][28, 0]  # no upper bound
    assert m16.detect(np.append(RAMP, [9e9]), upper=1e6)["flag_bound"][28, 0]


def test_future_values_cannot_change_an_earlier_flag():
    rng = np.random.default_rng(16)
    base = rng.gamma(2.0, 5.0, size=(200, 3))
    base[rng.random(base.shape) < 0.05] = np.nan
    ref = m16.detect(base, lower=0.0)
    for cut in (30, 90, 150):
        changed = base.copy()
        changed[cut:] = rng.gamma(0.5, 400.0, size=changed[cut:].shape)  # mutate the future
        out = m16.detect(changed, lower=0.0)
        for key in ("z", "status", "flag_z", "flag_bound"):
            np.testing.assert_array_equal(out[key][:cut], ref[key][:cut], err_msg=key)


def test_each_entity_column_is_independent():
    both = m16.detect(np.column_stack([np.append(RAMP, 60.0), np.append(RAMP, 15.0)]))
    assert both["flag_z"][28].tolist() == [True, False]


def test_strength_buckets_and_label_gate():
    assert [m16.strength_bucket(z) for z in (4.1, -6.0, 6.5, -10.0, 10.1, 55.0)] == [
        "4-6",
        "4-6",
        "6-10",
        "6-10",
        "10+",
        "10+",
    ]
    assert m16.label_gate(0)["quality_claim_allowed"] is False
    assert m16.label_gate(99)["quality_claim_allowed"] is False
    assert m16.label_gate(100) == {
        "adjudicated_flags": 100,
        "required": 100,
        "quality_claim_allowed": True,
    }
    assert set(m16.SEASONS) == set(range(1, 13))


def test_config_states_the_rule_the_code_runs_and_makes_no_claim():
    config = yaml.safe_load((ROOT / "configs/models/m16.yaml").read_text("utf-8"))
    assert config["rule"]["window_days"] == m16.WINDOW_DAYS
    assert config["rule"]["min_valid_days"] == m16.MIN_VALID
    assert config["rule"]["threshold"] == m16.THRESHOLD
    assert config["rule"]["mad_scale"] == m16.MAD_SCALE
    assert config["data_gate"]["min_adjudicated_flags"] == m16.MIN_LABELS
    assert config["unit_bounds"]["S08"] == {"field": "rain_mm", "lower": 0.0, "upper": None}
    assert config["enabled"] is False and config["split_manifest"] is None
    assert config["candidates"]["isolation_forest"].startswith("not run")
    assert config["planned_splits"]["test"] == ["2025-01-01", "2025-12-31"]
