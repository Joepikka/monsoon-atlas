"""T033 acceptance: an injected future feature or an overlapping train/test event causes a failure;
split manifests are saved with dates and a hash; transforms are fitted on training rows only;
evaluators refuse invalid test sets. Uses the committed real S02 ERA5 fixture (CC BY 4.0)."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pytest

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.features.base import FeatureSpec, LeakageError, assert_as_of, build_features
from atlas.ingest.s02 import S02
from atlas.models.base import (
    EvaluationError,
    ModelSpec,
    evaluate_classification,
    evaluate_regression,
    evaluate_scenario,
)
from atlas.models.splits import (
    DatasetSplit,
    TrainOnlyScaler,
    check_events,
    rolling_origin,
    spatial_blocks,
    write_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
RECENT = ROOT / "tests" / "fixtures" / "s02_openmeteo_era5_bengaluru_2026-10-20_11-04.json"
FETCHED = datetime(2026, 11, 5, 13, 1, 7, 707756, tzinfo=UTC)  # real retrieval time
CELL = "om_era5_13.0000N_77.5000E"


def era5() -> pa.Table:
    raw = RawArtifact(
        sha256=hashlib.sha256(RECENT.read_bytes()).hexdigest(),
        path=RECENT,
        fetched_at=FETCHED,
        media_type="application/json",
        response_status=200,
        source_url="https://archive-api.open-meteo.com/v1/archive",
        schema_mapping_version="s02-v1",
    )
    config = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S02")
    t = S02("ka", [(12.97, 77.59)], date(2026, 10, 20), date(2026, 11, 4)).parse(raw, config)
    return t.select(["source_id", "valid_at", "available_at", "rain_mm"]).append_column(
        "unit_id", t["cell_id"]
    )


def spine(*issues: datetime) -> pa.Table:
    return pa.table(
        {
            "unit_id": [CELL] * len(issues),
            "issue_at": pa.array(issues, pa.timestamp("us", tz="UTC")),
        }
    )


RAIN14 = FeatureSpec(
    name="rain_14d", source="S02", field="rain_mm", lag_days=0, window_days=14, aggregation="sum"
)
HINDCAST = RAIN14.model_copy(
    update={"name": "rain_14d_hc", "available_rule": "valid_plus_lag", "publication_lag_days": 6}
)


def test_features_use_only_rows_known_at_issue():
    after_fetch = datetime(2026, 11, 5, 14, tzinfo=UTC)
    before_fetch = datetime(2026, 11, 1, tzinfo=UTC)
    out = build_features(spine(after_fetch, before_fetch), era5(), [RAIN14, HINDCAST]).to_pylist()
    # Live rule: after the fetch, 22 to 30 Oct are known (31 Oct onwards is still null upstream).
    assert out[0]["rain_14d"] == pytest.approx(3.5 + 11.6 + 37.6 + 5.3)
    assert out[0]["rain_14d__known_at"] == FETCHED
    # Before the fetch nothing was known: null, never zero.
    assert out[1]["rain_14d"] is None and out[1]["rain_14d__known_at"] is None
    # Hindcast rule with ERA5's 6-day lag: only days up to 25 Oct count on 1 Nov.
    assert out[1]["rain_14d_hc"] == pytest.approx(0.3 + 1.8 + 3.5 + 11.6 + 37.6 + 5.3)
    assert out[1]["rain_14d_hc__known_at"] <= before_fetch
    assert_as_of(pa.Table.from_pylist(out), ["rain_14d", "rain_14d_hc"])


def test_injected_future_feature_fails():
    issue = datetime(2026, 11, 5, 14, tzinfo=UTC)
    obs = era5()
    future = obs.slice(0, 1).to_pylist()[0] | {
        "valid_at": issue - timedelta(hours=1),
        "available_at": issue + timedelta(days=1),  # published after the issue time
        "rain_mm": 500.0,
    }
    injected = pa.concat_tables([obs, pa.Table.from_pylist([future], schema=obs.schema)])
    clean = build_features(spine(issue), injected, [RAIN14])
    assert clean["rain_14d"][0].as_py() == pytest.approx(58.0)  # the late row is not used
    naive = clean.set_column(
        clean.schema.get_field_index("rain_14d__known_at"),
        "rain_14d__known_at",
        pa.array([issue + timedelta(days=1)], pa.timestamp("us", tz="UTC")),
    )
    with pytest.raises(LeakageError, match="known after issue"):
        assert_as_of(naive, ["rain_14d"])


def test_rolling_origin_purges_horizon_and_lag():
    splits = rolling_origin(
        date(1981, 1, 1),
        date(2020, 1, 1),
        date(2024, 12, 31),
        step_days=366,
        horizon_days=31,
        publication_lag_days=6,
    )
    assert [s.test_start.year for s in splits] == [2020, 2021, 2022, 2023, 2024]
    for s in splits:
        assert (s.test_start - s.train_end).days == 38 and s.purge_days == 37
    with pytest.raises(ValueError, match="more than 37 days"):
        DatasetSplit(
            name="bad",
            train_start=date(1981, 1, 1),
            train_end=date(2019, 12, 31),
            test_start=date(2020, 1, 1),
            test_end=date(2020, 12, 31),
            purge_days=37,
        )


def test_overlapping_train_test_event_fails():
    test_events = [("flood-2024-07", date(2024, 7, 10), date(2024, 7, 20))]
    check_events(
        [("flood-2023-08", date(2023, 8, 1), date(2023, 8, 9))], test_events, purge_days=37
    )
    with pytest.raises(LeakageError, match="overlaps"):
        check_events(
            [("rain-2024-06", date(2024, 6, 1), date(2024, 6, 10))], test_events, purge_days=37
        )
    with pytest.raises(LeakageError):
        check_events(
            [("flood-2024-07", date(2024, 7, 1), date(2024, 7, 2))], test_events, purge_days=0
        )


def test_spatial_blocks_never_split_a_block():
    units = {f"district-{i}": f"catchment-{i % 4}" for i in range(12)}
    folds = spatial_blocks(units, 2)
    assert sorted(b for f in folds for b in f) == sorted(set(units.values()))
    assert not set(folds[0]) & set(folds[1])
    with pytest.raises(ValueError):
        spatial_blocks(units, 5)


def test_split_manifest_saved_with_dates_and_hash(tmp_path):
    splits = rolling_origin(
        date(1981, 1, 1),
        date(2020, 1, 1),
        date(2021, 12, 31),
        step_days=366,
        horizon_days=31,
        publication_lag_days=6,
    )
    digest = write_manifest(splits, tmp_path / "m05_splits.json")
    saved = json.loads((tmp_path / "m05_splits.json").read_text("utf-8"))
    assert saved["sha256"] == digest and saved["splits"][0]["test_start"] == "2020-01-01"
    later = [splits[0].model_copy(update={"test_end": date(2020, 12, 30)}), *splits[1:]]
    assert write_manifest(later, tmp_path / "other.json") != digest


def test_transform_is_fitted_on_training_rows_only():
    rows = era5().to_pylist()
    values = [r["rain_mm"] for r in rows]
    days = [(r["valid_at"] - timedelta(hours=18, minutes=30)).date() for r in rows]
    split = DatasetSplit(
        name="s",
        train_start=date(2026, 10, 20),
        train_end=date(2026, 10, 24),
        test_start=date(2026, 10, 27),
        test_end=date(2026, 10, 30),
        purge_days=1,
    )
    scaler = TrainOnlyScaler().fit(values, days, split)
    train = [0.3, 1.8, 3.5, 11.6, 37.6]  # 20 to 24 Oct
    assert scaler.mean == pytest.approx(sum(train) / 5)
    assert scaler.transform([None])[0] is None


def test_evaluators_refuse_invalid_test_sets():
    issued = datetime(2026, 11, 5, tzinfo=UTC)
    assert evaluate_regression([1.0, 3.0], [2.0, 2.0]) == {"n": 2.0, "mae": 1.0, "rmse": 1.0}
    assert evaluate_classification([0, 1], [0.2, 0.6])["brier"] == pytest.approx((0.04 + 0.16) / 2)
    assert set(evaluate_scenario([1.0, 2.0], [1.0, 2.5], ["dry", "wet"])) == {"dry", "wet"}
    cases = [
        (lambda: evaluate_regression([], []), "empty"),
        (lambda: evaluate_regression([1.0, None], [1.0, 2.0]), "missing labels"),
        (lambda: evaluate_regression([1.0], [1.0], vintages=[None]), "unknown vintage"),
        (
            lambda: evaluate_classification([1, 1], [0.5, 0.5], vintages=[issued, issued]),
            "one class",
        ),
    ]
    for call, message in cases:
        with pytest.raises(EvaluationError, match=message):
            call()


def test_model_spec_needs_features_and_a_model_id():
    spec = ModelSpec(
        model_id="M05",
        task="regression",
        target="spi3_next_month",
        unit="district",
        horizon_days=31,
        features=(RAIN14,),
        baseline="spi3 persistence",
    )
    assert spec.features[0].lag_days == 0
    with pytest.raises(ValueError):
        ModelSpec(**(spec.model_dump() | {"features": ()}))
    with pytest.raises(ValueError):
        ModelSpec(**(spec.model_dump() | {"model_id": "drought"}))
