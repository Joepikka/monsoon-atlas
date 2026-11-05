"""Champion decision against the strongest simple baseline (T034, plan section 11).

A candidate is only *eligible* if the test sample is large enough, both test scores exist,
it meets the model-specific threshold and the lower 95% paired block bootstrap bound of its
improvement is above 0. Even then it is not champion until the owner approves the release
(registry.approve). A missing score never becomes 0: the release is research-only.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from atlas.models.uncertainty import Improvement, paired_block_bootstrap

Status = Literal["candidate_eligible", "baseline_only", "research_only"]


@dataclass(frozen=True)
class Decision:
    status: Status
    reason: str
    improvement: Improvement | None


def _missing(values: Sequence[float | None] | None) -> bool:
    return values is None or any(v is None or not math.isfinite(v) for v in values)


def decide(
    baseline_loss: Sequence[float | None] | None,
    candidate_loss: Sequence[float | None] | None,
    blocks: Sequence[str],
    *,
    min_rows: int,
    min_blocks: int,
    max_loss_ratio: float = 1.0,
) -> Decision:
    """Compare per-row test losses of baseline and candidate on the same rows.

    `max_loss_ratio` is the model's own threshold, for example 0.95 for M05 (candidate MAE at
    most 0.95 x baseline MAE).
    """
    if _missing(baseline_loss) or _missing(candidate_loss):
        return Decision("research_only", "a test score is missing; it is not treated as 0", None)
    if len(baseline_loss) != len(candidate_loss) or len(blocks) != len(baseline_loss):
        return Decision(
            "research_only", "baseline and candidate were not scored on the same rows", None
        )
    if len(baseline_loss) < min_rows or len(set(blocks)) < min_blocks:
        return Decision(
            "research_only", f"test sample below {min_rows} rows or {min_blocks} blocks", None
        )
    imp = paired_block_bootstrap(baseline_loss, candidate_loss, blocks)
    base_mean = sum(baseline_loss) / len(baseline_loss)
    cand_mean = sum(candidate_loss) / len(candidate_loss)
    if cand_mean > max_loss_ratio * base_mean:
        return Decision(
            "baseline_only",
            f"candidate loss {cand_mean:.4g} misses the {max_loss_ratio} x baseline threshold",
            imp,
        )
    if imp.lower95 <= 0:
        return Decision(
            "baseline_only",
            f"lower 95% bound of improvement is {imp.lower95:.4g}, not above 0",
            imp,
        )
    return Decision(
        "candidate_eligible", "all gates pass; needs owner approval to become champion", imp
    )
