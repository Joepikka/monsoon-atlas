"""T102 acceptance: the deterministic training smoke test passes; test rows cannot affect the fit;
every evaluated model has the same target units and rows. Real IMD rain 1981-2024 (S08, local
raw); needs the geo and ml locks."""

import json
from datetime import date
from functools import cache
from pathlib import Path

import pyarrow as pa
import pytest

pytest.importorskip("shapely")
pytest.importorskip("lightgbm")
pytest.importorskip("sklearn")

from atlas.config import load_state  # noqa: E402
from atlas.contracts import RawArtifact  # noqa: E402
from atlas.features import m05 as features  # noqa: E402
from atlas.features.base import LeakageError  # noqa: E402
from atlas.ingest.base import SourceUnavailable  # noqa: E402
from atlas.ingest.s17 import S17  # noqa: E402
from atlas.models import m05  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
KA = load_state(ROOT / "configs" / "states" / "ka.yaml")
TUNE, TEST = features.splits()[0], features.splits()[2]


def artifact(source: str, eid: str) -> RawArtifact:
    manifest = json.loads((ROOT / f"tests/fixtures/{source}/manifest.json").read_text("utf-8"))
    e = next(x for x in manifest["evidence"] if x["id"] == eid)
    if not (RAW / e["raw_path"]).exists():
        pytest.skip("raw evidence is local only")
    return RawArtifact(
        sha256=e["sha256"],
        path=RAW / e["raw_path"],
        fetched_at=e["fetched_at"],
        media_type=e["media_type"],
        response_status=e["status"],
        source_url=e["url"],
        schema_mapping_version="test",
    )


@cache
def rows() -> pa.Table:
    try:
        raws = features.year_artifacts(RAW, range(1981, 2025))
    except SourceUnavailable:
        pytest.skip("S08 1981-2024 year files are local only")
    districts = S17("ka").parse(
        artifact("s17", "e06"), KA.source("S17"), adm1=artifact("s17", "e05")
    )
    return features.feature_rows(
        features.spi_table(features.district_monthly_rain(raws, districts))
    )


def parts(table: pa.Table):
    train = m05.rows_in(table, TUNE.train_start, TUNE.train_end)
    tune = m05.rows_in(table, TUNE.test_start, TUNE.test_end)
    test = m05.rows_in(table, TEST.test_start, TEST.test_end)
    return train, tune, test


@cache
def fitted() -> m05.Fit:
    train, tune, _ = parts(rows())
    return m05.fit(train, tune, TEST, lgbm_trials=4)


def test_fit_is_deterministic():
    train, tune, test = parts(rows())
    again = m05.fit(train, tune, TEST, lgbm_trials=4)
    first = fitted()
    assert (again.ridge_alpha, again.ridge_coef, again.choice) == (
        first.ridge_alpha,
        first.ridge_coef,
        first.choice,
    )
    assert again.lgbm_model == first.lgbm_model
    assert again.predict(test) == first.predict(test)


def test_test_rows_cannot_affect_the_fit():
    train, tune, test = parts(rows())
    with pytest.raises(LeakageError, match="test window"):
        m05.fit(pa.concat_tables([train, test]), tune, TEST, lgbm_trials=1)
    # Changing every test target leaves the fit unchanged: the fit never sees those rows.
    changed = rows().set_column(
        rows().schema.get_field_index("target_spi3"),
        "target_spi3",
        pa.array(
            [
                y + 5 if TEST.test_start <= m <= TEST.test_end else y
                for y, m in zip(
                    rows()["target_spi3"].to_pylist(),
                    rows()["target_month"].to_pylist(),
                    strict=True,
                )
            ]
        ),
    )
    train2, tune2, _ = parts(changed)
    refit = m05.fit(train2, tune2, TEST, lgbm_trials=4)
    assert refit.ridge_coef == fitted().ridge_coef and refit.lgbm_model == fitted().lgbm_model


def test_all_models_share_rows_and_spi_units():
    _, tune, test = parts(rows())
    assert (
        test.num_rows == 30 * 60 and tune.num_rows == 30 * 24
    )  # 2020-2024 and 2017-2018, 30 districts
    preds = fitted().predict(test)
    assert set(preds) >= {"persistence", "climatology", "ridge", "lightgbm"}
    assert {len(v) for v in preds.values()} == {test.num_rows}
    for name, values in preds.items():
        assert all(-6 < v < 6 for v in values), name  # SPI units, not mm
    assert fitted().choice in {"ridge", "lightgbm"}
    assert set(fitted().tune_mae) == {"ridge", "lightgbm", "persistence"}


def test_artifacts_and_mlflow_run_are_saved(tmp_path):
    split_sha = features.write_split_manifest(tmp_path / "splits.json")
    data_sha = m05.table_sha256(rows())
    path = m05.save(fitted(), tmp_path / "m05", split_sha, data_sha)
    saved = json.loads(path.read_text("utf-8"))
    assert saved["split_sha256"] == split_sha and saved["dataset_sha256"] == data_sha
    assert (
        saved["evidence"] == "hindcast (D39)" and (tmp_path / "m05" / "m05_lightgbm.txt").exists()
    )
    assert m05.log_mlflow(
        fitted(), f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}", split_sha, data_sha
    )


def test_blocked_gate_keeps_only_a_no_model_manifest(tmp_path):
    short = m05.rows_in(rows(), date(2000, 1, 1), date(2024, 12, 31))
    assert short.num_rows < rows().num_rows
    gate = {"status": "blocked", "reasons": ["only 25 years of rain, need 30"]}
    path = m05.no_model_manifest(tmp_path / "m05", gate)
    assert json.loads(path.read_text("utf-8"))["status"] == "blocked"
    assert sorted(p.name for p in (tmp_path / "m05").iterdir()) == ["m05_no_model.json"]
