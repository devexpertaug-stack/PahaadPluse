"""Trends tests incl. the Req 7.4 invariant (property-based)."""

from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.review import Aspect, Platform
from app.services.market_radar.trends import (
    TrendService,
    TrendValidationError,
    validate_range,
)

_SERVICE = TrendService()


def test_monthly_default_returns_twelve_buckets() -> None:
    result = _SERVICE.aspect_trends(aspects=[Aspect.FOOD])
    assert result["granularity"] == "monthly"
    assert len(result["trends"][0]["buckets"]) == 12


def test_weekly_periods_available() -> None:
    result = _SERVICE.aspect_trends(
        granularity="weekly",
        aspects=[Aspect.FOOD],
        start=date(2024, 1, 1),
        end=date(2024, 3, 1),
    )
    assert result["granularity"] == "weekly"
    assert len(result["trends"][0]["buckets"]) >= 8


def test_platform_filter_default_all_five() -> None:
    result = _SERVICE.aspect_trends(aspects=[Aspect.FOOD])
    assert len(result["platforms"]) == 5


def test_platform_filter_single() -> None:
    result = _SERVICE.aspect_trends(aspects=[Aspect.FOOD], platforms=[Platform.GOOGLE])
    assert result["platforms"] == ["Google"]


def test_complaint_percentage_one_dp_or_none() -> None:
    result = _SERVICE.aspect_trends(aspects=[Aspect.SERVICE])
    for bucket in result["trends"][0]["buckets"]:
        pct = bucket["complaint_percentage"]
        if bucket["total"] == 0:
            assert pct is None and bucket["no_data"] is True
        else:
            assert pct == round(pct, 1)
            # negative/total matches
            assert pct == round(100.0 * bucket["negative"] / bucket["total"], 1)


def test_range_validation_end_before_start() -> None:
    with pytest.raises(TrendValidationError):
        validate_range(date(2024, 6, 1), date(2024, 1, 1), today=date(2024, 6, 15))


def test_range_validation_over_36_months() -> None:
    with pytest.raises(TrendValidationError):
        validate_range(date(2020, 1, 1), date(2024, 6, 1), today=date(2024, 6, 15))


def test_range_validation_under_one_week() -> None:
    with pytest.raises(TrendValidationError):
        validate_range(date(2024, 6, 1), date(2024, 6, 3), today=date(2024, 6, 15))


@settings(max_examples=40, deadline=None)
@given(
    granularity=st.sampled_from(["monthly", "weekly"]),
    platforms=st.lists(st.sampled_from(list(Platform)), unique=True),
)
def test_invariant_pos_neu_neg_equals_total(granularity: str, platforms: list) -> None:
    """Req 7.4: positive + neutral + negative == total in every bucket."""
    result = _SERVICE.aspect_trends(
        granularity=granularity,
        platforms=platforms or None,
        start=date(2024, 1, 1),
        end=date(2024, 6, 1),
    )
    for trend in result["trends"]:
        for bucket in trend["buckets"]:
            assert bucket["positive"] + bucket["neutral"] + bucket["negative"] == bucket[
                "total"
            ]
