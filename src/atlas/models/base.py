"""Model specs and evaluators that refuse invalid test sets (T033).

Evaluators raise EvaluationError for an empty test set, missing labels or predictions,
overlapping train/test events (via splits.check_events) or forecast inputs whose vintage
(issue time) is unknown. T034 adds baselines, intervals and promotion rules on top.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from pydantic import Field

from atlas.contracts import ModelId, Strict
from atlas.features.base import FeatureSpec


class EvaluationError(ValueError):
    """The test set cannot give an honest score."""


class ModelSpec(Strict):
    model_id: ModelId
    task: Literal["regression", "classification", "scenario"]
    target: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    horizon_days: int = Field(ge=0)
    features: tuple[FeatureSpec, ...] = Field(min_length=1)
    baseline: str = Field(min_length=1)


def _checked(
    y_true: Sequence, y_pred: Sequence, vintages: Sequence[datetime | None] | None
) -> None:
    if not y_true:
        raise EvaluationError("empty test set")
    if len(y_true) != len(y_pred):
        raise EvaluationError("labels and predictions differ in length")
    if any(v is None for v in y_true):
        raise EvaluationError("missing labels in the test set")
    if any(p is None for p in y_pred):
        raise EvaluationError("missing predictions in the test set")
    if vintages is not None and any(v is None for v in vintages):
        raise EvaluationError("forecast inputs with unknown vintage (issue time)")


def evaluate_regression(y_true, y_pred, *, vintages=None) -> dict[str, float]:
    _checked(y_true, y_pred, vintages)
    errors = [p - t for t, p in zip(y_true, y_pred, strict=True)]
    return {
        "n": float(len(errors)),
        "mae": sum(abs(e) for e in errors) / len(errors),
        "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)),
    }


def evaluate_classification(y_true, p_pred, *, vintages=None) -> dict[str, float]:
    _checked(y_true, p_pred, vintages)
    if not set(y_true) <= {0, 1} or any(not 0 <= p <= 1 for p in p_pred):
        raise EvaluationError("labels must be 0/1 and probabilities in [0, 1]")
    if len(set(y_true)) < 2:
        raise EvaluationError("test set has only one class")
    brier = sum((p - t) ** 2 for t, p in zip(y_true, p_pred, strict=True)) / len(y_true)
    return {"n": float(len(y_true)), "prevalence": sum(y_true) / len(y_true), "brier": brier}


def evaluate_scenario(
    y_true, y_pred, scenarios: Sequence[str], *, vintages=None
) -> dict[str, dict]:
    """Regression scores per named scenario; every scenario must have test rows."""
    _checked(y_true, y_pred, vintages)
    if len(scenarios) != len(y_true):
        raise EvaluationError("one scenario label per row")
    out = {}
    for name in sorted(set(scenarios)):
        idx = [i for i, s in enumerate(scenarios) if s == name]
        out[name] = evaluate_regression([y_true[i] for i in idx], [y_pred[i] for i in idx])
    return out
