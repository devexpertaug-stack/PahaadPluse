"""F14 Every-number-is-clickable Drilldown (Req 27).

Every displayed count / share / score / chart point on the website must link
back to the exact source records behind it. This module is the single,
reusable backend engine for that: given a *metric reference* (which panel, which
property/aspect/period/label the number was computed from) it returns the list
of underlying ``Review_Record`` or ``Complaint`` source rows, each with its
highlighted :class:`~app.models.review.AspectMention` evidence span and its
source URL (or the ``source URL unavailable`` sentinel, Req 2.9 / 27.2).

The invariant that makes the drilldown trustworthy (Req 27.3): for a *count*
metric the number of listed source records equals the clicked count. The
analytics panel (``analytics_dataset.generate_observations``) is the shared,
seed-reproducible source of truth already used by every Market Radar Deep
feature, so a count rendered anywhere on the site can be re-derived here from
the same observations — guaranteeing the count matches. The property-based test
``tests/test_drilldown.py`` enforces this across random metric references.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.models.review import Aspect, Platform, SentimentLabel
from app.services.market_radar.analytics_dataset import (
    MentionObservation,
    generate_observations,
)
from app.services.market_radar.trends import _bucket_key, _month_start, _week_start

SOURCE_URL_UNAVAILABLE = "source URL unavailable"


@dataclass(frozen=True)
class EvidenceSpan:
    """A highlighted evidence span within a source record's text."""

    text: str
    quote: str
    start: int
    end: int

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "quote": self.quote,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True)
class SourceRecord:
    """One source row behind a displayed number."""

    kind: str  # "review" | "complaint"
    property_id: str
    property_name: str
    platform: str | None
    aspect: str | None
    label: str | None
    date: str
    source_url: str | None
    evidence: EvidenceSpan

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "property_id": self.property_id,
            "property_name": self.property_name,
            "platform": self.platform,
            "aspect": self.aspect,
            "label": self.label,
            "date": self.date,
            # Req 27.2: show the source URL or the explicit unavailable sentinel.
            "source_url": self.source_url or SOURCE_URL_UNAVAILABLE,
            "source_url_available": self.source_url is not None,
            "evidence": self.evidence.to_dict(),
        }


@dataclass(frozen=True)
class DrilldownResult:
    """The resolved drilldown for a metric reference."""

    metric: str
    clicked_value: float | int | None
    is_count: bool
    records: list[SourceRecord]

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "clicked_value": self.clicked_value,
            "is_count": self.is_count,
            "count": len(self.records),
            # Req 27.3 invariant surfaced to the UI so it can assert visually.
            "count_matches": (
                None if not self.is_count else len(self.records) == self.clicked_value
            ),
            "records": [r.to_dict() for r in self.records],
        }


def _evidence_span(text: str, quote: str) -> EvidenceSpan:
    """Locate ``quote`` inside ``text`` so the UI can highlight it.

    The analytics panel stores the quote as the record text itself, so the span
    covers the full text; this still exercises the real substring-locating path
    used for genuine Review_Records whose evidence is a substring of the text.
    """
    start = text.find(quote)
    if start < 0:
        start, end = 0, len(text)
        quote = text
    else:
        end = start + len(quote)
    return EvidenceSpan(text=text, quote=quote, start=start, end=end)


def _obs_to_record(obs: MentionObservation) -> SourceRecord:
    return SourceRecord(
        kind="review",
        property_id=obs.property_id,
        property_name=obs.property_name,
        platform=obs.platform.value,
        aspect=obs.aspect.value,
        label=obs.label.value,
        date=obs.date.isoformat(),
        source_url=obs.source_url,
        evidence=_evidence_span(obs.text, obs.evidence),
    )


class DrilldownService:
    """Resolve a displayed metric back to its source records."""

    def __init__(self, observations: tuple[MentionObservation, ...] | None = None) -> None:
        self._obs = observations if observations is not None else generate_observations()

    # ---- filtering ----
    def _filter(
        self,
        *,
        property_id: str | None = None,
        aspect: Aspect | None = None,
        platforms: Iterable[Platform] | None = None,
        label: SentimentLabel | None = None,
        start: date | None = None,
        end: date | None = None,
        period: date | None = None,
        granularity: str | None = None,
    ) -> list[MentionObservation]:
        platform_set = set(platforms) if platforms else None
        out: list[MentionObservation] = []
        for o in self._obs:
            if property_id is not None and o.property_id != property_id:
                continue
            if aspect is not None and o.aspect is not aspect:
                continue
            if platform_set is not None and o.platform not in platform_set:
                continue
            if label is not None and o.label is not label:
                continue
            if start is not None and o.date < start:
                continue
            if end is not None and o.date > end:
                continue
            if period is not None and granularity is not None:
                if _bucket_key(o.date, granularity) != _period_key(period, granularity):
                    continue
            out.append(o)
        return out

    def count_metric(
        self,
        *,
        metric: str,
        clicked_value: int,
        property_id: str | None = None,
        aspect: Aspect | None = None,
        platforms: Iterable[Platform] | None = None,
        label: SentimentLabel | None = None,
        start: date | None = None,
        end: date | None = None,
        period: date | None = None,
        granularity: str | None = None,
    ) -> DrilldownResult:
        """Resolve a count metric; the listed records equal the count (Req 27.3)."""
        matches = self._filter(
            property_id=property_id,
            aspect=aspect,
            platforms=platforms,
            label=label,
            start=start,
            end=end,
            period=period,
            granularity=granularity,
        )
        records = [_obs_to_record(o) for o in sorted(matches, key=lambda o: o.date)]
        return DrilldownResult(
            metric=metric,
            clicked_value=clicked_value,
            is_count=True,
            records=records,
        )

    def share_or_score_metric(
        self,
        *,
        metric: str,
        clicked_value: float,
        property_id: str | None = None,
        aspect: Aspect | None = None,
        platforms: Iterable[Platform] | None = None,
        start: date | None = None,
        end: date | None = None,
        period: date | None = None,
        granularity: str | None = None,
    ) -> DrilldownResult:
        """Resolve a share/score/chart-point metric to the records it summarises.

        For a non-count metric the invariant does not apply (a share is derived
        from many records), so all contributing records are listed with their
        evidence; the UI shows how the number was computed from them.
        """
        matches = self._filter(
            property_id=property_id,
            aspect=aspect,
            platforms=platforms,
            start=start,
            end=end,
            period=period,
            granularity=granularity,
        )
        records = [_obs_to_record(o) for o in sorted(matches, key=lambda o: o.date)]
        return DrilldownResult(
            metric=metric,
            clicked_value=clicked_value,
            is_count=False,
            records=records,
        )


def _period_key(period: date, granularity: str) -> date:
    return _week_start(period) if granularity == "weekly" else _month_start(period)


_service: DrilldownService | None = None


def get_drilldown_service() -> DrilldownService:
    """Return a process-wide drilldown service over the shared panel."""
    global _service
    if _service is None:
        _service = DrilldownService()
    return _service
