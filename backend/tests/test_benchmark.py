"""Benchmark harness tests incl. the Req 16.8 idempotence property."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.benchmark.harness import run_benchmark
from app.benchmark.metrics import bootstrap_ci, confusion_matrix, macro_f1
from app.benchmark.systems import default_systems


def test_three_systems_evaluated() -> None:
    result = run_benchmark()
    assert len(result.systems) == 3
    names = {s.name for s in result.systems}
    assert any("Sentiment_Engine" in n for n in names)
    assert any("off-the-shelf" in n for n in names)
    assert any("Plain-LLM" in n for n in names)


def test_each_system_reports_three_metrics_with_ci() -> None:
    result = run_benchmark()
    for system in result.systems:
        d = system.to_dict()
        for key in ("overall_sentiment", "aspect_detection", "aspect_sentiment"):
            assert 0.0 <= d[key]["macro_f1"] <= 1.0
            lo, hi = d[key]["ci_95"]
            assert lo <= hi


def test_confusion_matrix_present_per_aspect() -> None:
    result = run_benchmark()
    for system in result.systems:
        assert system.aspect_confusion
        for payload in system.aspect_confusion.values():
            matrix = payload["matrix"]
            assert set(matrix.keys()) == {"positive", "neutral", "negative"}


def test_macro_f1_perfect_and_zero() -> None:
    perfect = [("positive", "positive"), ("negative", "negative")]
    assert macro_f1(perfect) == 1.0
    wrong = [("positive", "negative"), ("negative", "positive")]
    assert macro_f1(wrong) == 0.0


def test_confusion_matrix_counts() -> None:
    m = confusion_matrix([("positive", "positive"), ("positive", "negative")])
    assert m["positive"]["positive"] == 1
    assert m["positive"]["negative"] == 1


@settings(max_examples=5, deadline=None)
@given(seed=st.integers(min_value=1, max_value=10_000))
def test_idempotent_for_fixed_seed(seed: int) -> None:
    """Req 16.8: identical scores for the same inputs/model versions/seed."""
    first = run_benchmark(seed=seed, systems=default_systems())
    second = run_benchmark(seed=seed, systems=default_systems())
    assert first.to_dict() == second.to_dict()


def test_bootstrap_ci_deterministic() -> None:
    items = [("positive", "positive")] * 50 + [("negative", "positive")] * 50
    a = bootstrap_ci(items, macro_f1, seed=7)
    b = bootstrap_ci(items, macro_f1, seed=7)
    assert a == b
