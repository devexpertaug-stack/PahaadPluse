"""F14 Drilldown tests, including the count invariant (Req 27.3).

The key property: for a *count* metric the number of listed source records
equals the clicked count. We re-derive the clicked count from the shared panel,
then ask the drilldown to resolve it and assert the listed records match.
"""

from __future__ import annotations

from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.review import Aspect, Platform, SentimentLabel
from app.services.common.drilldown import (
    SOURCE_URL_UNAVAILABLE,
    DrilldownService,
    get_drilldown_service,
)
from app.services.market_radar.analytics_dataset import (
    cluster_property_ids,
    generate_observations,
)

OBS = generate_observations()
SERVICE = DrilldownService(OBS)
PROPERTY_IDS = cluster_property_ids()


def _true_count(property_id: str, aspect: Aspect, label: SentimentLabel) -> int:
    return sum(
        1
        for o in OBS
        if o.property_id == property_id and o.aspect is aspect and o.label is label
    )


@settings(max_examples=60, deadline=None)
@given(
    property_id=st.sampled_from(PROPERTY_IDS),
    aspect=st.sampled_from(list(Aspect)),
    label=st.sampled_from(list(SentimentLabel)),
)
def test_count_invariant(property_id: str, aspect: Aspect, label: SentimentLabel) -> None:
    """Listed records == clicked count for a count metric (Req 27.3)."""
    clicked = _true_count(property_id, aspect, label)
    result = SERVICE.count_metric(
        metric="aspect_label_count",
        clicked_value=clicked,
        property_id=property_id,
        aspect=aspect,
        label=label,
    )
    assert len(result.records) == clicked
    body = result.to_dict()
    assert body["count"] == clicked
    assert body["count_matches"] is True


def test_count_invariant_with_platform_filter() -> None:
    platform = Platform.GOOGLE
    clicked = sum(
        1
        for o in OBS
        if o.property_id == PROPERTY_IDS[0]
        and o.aspect is Aspect.FOOD
        and o.label is SentimentLabel.NEGATIVE
        and o.platform is platform
    )
    result = SERVICE.count_metric(
        metric="x",
        clicked_value=clicked,
        property_id=PROPERTY_IDS[0],
        aspect=Aspect.FOOD,
        label=SentimentLabel.NEGATIVE,
        platforms=[platform],
    )
    assert len(result.records) == clicked


def test_records_have_evidence_and_source_url() -> None:
    result = SERVICE.count_metric(
        metric="x",
        clicked_value=0,
        property_id=PROPERTY_IDS[0],
        aspect=Aspect.STAFF,
        label=SentimentLabel.POSITIVE,
    )
    assert result.records, "expected some records"
    for rec in result.records:
        d = rec.to_dict()
        # Evidence span is located within the record text.
        ev = d["evidence"]
        assert ev["text"][ev["start"] : ev["end"]] == ev["quote"]
        # Source URL present or the explicit unavailable sentinel (Req 27.2).
        assert d["source_url"] is not None
        if not d["source_url_available"]:
            assert d["source_url"] == SOURCE_URL_UNAVAILABLE


def test_share_metric_is_not_count_gated() -> None:
    result = SERVICE.share_or_score_metric(
        metric="negative_share",
        clicked_value=0.42,
        property_id=PROPERTY_IDS[0],
        aspect=Aspect.SERVICE,
    )
    body = result.to_dict()
    assert body["is_count"] is False
    assert body["count_matches"] is None
    assert body["records"]


def test_default_service_is_shared() -> None:
    assert get_drilldown_service() is get_drilldown_service()


def test_period_filtered_count(_date: date = date(2024, 5, 1)) -> None:
    clicked = sum(
        1
        for o in OBS
        if o.property_id == PROPERTY_IDS[0]
        and o.aspect is Aspect.ROOM
        and o.label is SentimentLabel.NEGATIVE
        and o.date.year == 2024
        and o.date.month == 5
    )
    result = SERVICE.count_metric(
        metric="monthly_negative",
        clicked_value=clicked,
        property_id=PROPERTY_IDS[0],
        aspect=Aspect.ROOM,
        label=SentimentLabel.NEGATIVE,
        period=_date,
        granularity="monthly",
    )
    assert len(result.records) == clicked
