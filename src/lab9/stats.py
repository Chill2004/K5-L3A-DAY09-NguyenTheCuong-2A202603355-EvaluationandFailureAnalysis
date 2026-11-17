"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
import math

import numpy as np
from scipy.stats import bootstrap

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """Đếm tp/fp/fn/tn, với FAIL là lớp positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge must have equal lengths")

    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}

    for actual, predicted in zip(human, judge):
        if actual not in {"PASS", "FAIL"} or predicted not in {"PASS", "FAIL"}:
            raise ValueError("labels must be PASS or FAIL")

        if actual == POS and predicted == POS:
            counts["tp"] += 1
        elif actual != POS and predicted == POS:
            counts["fp"] += 1
        elif actual == POS and predicted != POS:
            counts["fn"] += 1
        else:
            counts["tn"] += 1

    return counts


def precision_recall(
    human: Sequence[str],
    judge: Sequence[str],
) -> tuple[float, float]:
    counts = confusion(human, judge)
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    counts = confusion(human, judge)
    n = sum(counts.values())
    if n == 0:
        raise ValueError("labels must not be empty")

    tp, fp = counts["tp"], counts["fp"]
    fn, tn = counts["fn"], counts["tn"]

    observed = (tp + tn) / n
    human_positive = (tp + fn) / n
    judge_positive = (tp + fp) / n
    expected = (
        human_positive * judge_positive
        + (1 - human_positive) * (1 - judge_positive)
    )

    if expected == 1.0:
        raise ValueError("kappa is undefined when expected agreement is 1")

    return (observed - expected) / (1 - expected)


def rogan_gladen(
    observed_rate: float,
    sensitivity: float,
    specificity: float,
) -> float:
    values = (observed_rate, sensitivity, specificity)
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values):
        raise ValueError("rates must be finite and between 0 and 1")

    denominator = sensitivity + specificity - 1
    if denominator <= 0:
        raise ValueError("sensitivity + specificity must exceed 1")

    corrected = (observed_rate + specificity - 1) / denominator
    return min(1.0, max(0.0, corrected))


def paired_bootstrap(
    a: Sequence[float],
    b: Sequence[float],
    *,
    n_resamples: int = 1000,
    rng: int = 2027,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    first = np.asarray(a, dtype=float)
    second = np.asarray(b, dtype=float)

    if first.ndim != 1 or second.ndim != 1:
        raise ValueError("inputs must be one-dimensional")
    if len(first) != len(second) or len(first) < 2:
        raise ValueError("inputs must have equal lengths of at least 2")
    if not np.isfinite(first).all() or not np.isfinite(second).all():
        raise ValueError("inputs must contain only finite values")
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, int):
        raise ValueError("n_resamples must be a positive integer")
    if n_resamples <= 0:
        raise ValueError("n_resamples must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")

    if np.array_equal(first, second):
        return 0.0, 0.0, 0.0

    def difference(first_sample, second_sample, axis=-1):
        return np.mean(first_sample, axis=axis) - np.mean(
            second_sample, axis=axis
        )

    result = bootstrap(
        (first, second),
        statistic=difference,
        paired=True,
        vectorized=True,
        n_resamples=n_resamples,
        confidence_level=confidence,
        method="percentile",
        rng=np.random.default_rng(rng),
    )

    delta = float(np.mean(first) - np.mean(second))
    return (
        delta,
        float(result.confidence_interval.low),
        float(result.confidence_interval.high),
    )


def pass_at_k(n: int, c: int, k: int) -> float:
    """Xác suất có ít nhất một lần pass trong k lần lấy không hoàn lại."""
    if any(isinstance(value, bool) or not isinstance(value, int)
           for value in (n, c, k)):
        raise ValueError("n, c and k must be integers")
    if n < 1 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("require n >= 1, 0 <= c <= n and 1 <= k <= n")

    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """Xác suất cả k lần đều pass khi lấy không hoàn lại."""
    if any(isinstance(value, bool) or not isinstance(value, int)
           for value in (n, c, k)):
        raise ValueError("n, c and k must be integers")
    if n < 1 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("require n >= 1, 0 <= c <= n and 1 <= k <= n")

    if c < k:
        return 0.0
    return math.comb(c, k) / math.comb(n, k)