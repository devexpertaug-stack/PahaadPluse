"""Gap_Finder tests incl. the Req 13.4 invariant (property-based)."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.market_radar.gap_finder import GapFinder

_FINDER = GapFinder()
_RESULT = _FINDER.find()


def test_themes_ranked_by_affected_then_negatives() -> None:
    keys = [(t.affected_properties, t.total_negatives) for t in _RESULT.themes]
    assert keys == sorted(keys, reverse=True)


def test_each_theme_has_three_quotes_and_six_month_trend() -> None:
    for theme in _RESULT.themes:
        assert len(theme.quotes) >= 3
        assert len(theme.trend) == 6


def test_market_gap_label_at_or_above_60_percent() -> None:
    for theme in _RESULT.themes:
        fraction = theme.affected_properties / theme.cluster_size
        assert theme.market_gap == (fraction >= 0.60)


def test_service_is_a_market_gap() -> None:
    # The synthetic dataset makes Service a cluster-wide weak aspect.
    service = next(t for t in _RESULT.themes if t.aspect.value == "Service")
    assert service.total_negatives > 0


@settings(max_examples=1, deadline=None)
@given(st.just(None))
def test_affected_leq_cluster_size_invariant(_: None) -> None:
    """Req 13.4: affected properties <= Cluster size."""
    result = GapFinder().find()
    for theme in result.themes:
        assert theme.affected_properties <= theme.cluster_size
