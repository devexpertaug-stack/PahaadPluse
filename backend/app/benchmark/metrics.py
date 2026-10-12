"""Scoring metrics for the Hinglish benchmark (Req 16.3-16.5, 16.7, 16.8).

Provides macro-F1 computation, deterministic (seeded) bootstrap 95% confidence
intervals, and per-aspect confusion matrices. All functions are pure and
seed-driven so the harness is idempotent (Req 16.8).
"""

from __future__ import annotations

import random
from collections import defaultdict

LABELS = ("positive", "neutral", "negative")


def macro_f1(pairs: list[tuple[str, str]]) -> float:
    """Macro-averaged F1 over the three sentiment classes.

    ``pairs`` is a list of ``(gold, predicted)`` label tuples.
    """
    if not pairs:
        return 0.0
    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)
    present = set()
    for gold, pred in pairs:
        present.add(gold)
        if gold == pred:
            tp[gold] += 1
        else:
            fp[pred] += 1
            fn[gold] += 1
    f1s = []
    for label in present:
        p_denom = tp[label] + fp[label]
        r_denom = tp[label] + fn[label]
        prec = tp[label] / p_denom if p_denom else 0.0
        rec = tp[label] / r_denom if r_denom else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        f1s.append(f1)
    return sum(f1s) / len(f1s) if f1s else 0.0


def detection_f1(pairs: list[tuple[bool, bool]]) -> float:
    """Binary F1 for aspect *detection* (present vs absent)."""
    tp = sum(1 for g, p in pairs if g and p)
    fp = sum(1 for g, p in pairs if not g and p)
    fn = sum(1 for g, p in pairs if g and not p)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0


def bootstrap_ci(
    items: list,
    score_fn,
    seed: int,
    resamples: int = 500,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Seeded bootstrap 95% CI for ``score_fn(items)`` (Req 16.4).

    Deterministic given the same ``items``, ``seed`` and ``resamples`` so the
    harness is idempotent (Req 16.8).
    """
    if not items:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(items)
    scores: list[float] = []
    for _ in range(resamples):
        sample = [items[rng.randrange(n)] for _ in range(n)]
        scores.append(score_fn(sample))
    scores.sort()
    lo_idx = int((alpha / 2) * resamples)
    hi_idx = min(resamples - 1, int((1 - alpha / 2) * resamples))
    return (round(scores[lo_idx], 4), round(scores[hi_idx], 4))


def confusion_matrix(pairs: list[tuple[str, str]]) -> dict[str, dict[str, int]]:
    """3x3 confusion matrix keyed ``gold -> predicted -> count``."""
    matrix = {g: {p: 0 for p in LABELS} for g in LABELS}
    for gold, pred in pairs:
        if gold in matrix and pred in matrix[gold]:
            matrix[gold][pred] += 1
    return matrix
