"""Aspect sentiment trends over time (Req 7).

Builds per-Aspect positive/neutral/negative time series over IST periods from
the analytics mention panel:

* monthly periods are calendar months; weekly periods run Monday 00:00 to
  Sunday 23:59 IST (Req 7.1), with mentions counted by their review date.
* a platform filter defaults to all five platforms (Req 7.2) and is applied in
  one pass (well within the 3s budget).
* the category complaint trend is ``negative / total`` as a percentage to one
  decimal place (Req 7.3); zero-mention periods report 0 counts and a no-data
  indicator for the percentage (Req 7.6).
* every bucket satisfies the invariant ``positive + neutral + negative ==
  total`` (Req 7.4).
* the date range must be between 1 week and 36 months with the default being
  the most recent 12 calendar months; an end-before-start or >36-month range is
  a validation error that leaves charts unchanged (Req 7.5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.models.review import Aspect, Platform, SentimentLabel
from app.services.market_radar.analytics_dataset import (
    MentionObservation,
    generate_observations,
)

MIN_RANGE_DAYS = 7
MAX_RANGE_MONTHS = 36
DEFAULT_RANGE_MONTHS = 12


class TrendValidationError(ValueError):
    """Raised for an invalid date range; charts are left unchanged (Req 7.5)."""


@dataclass
class TrendBucket:
    """One period's counts for one aspect."""

    period: str  # ISO date of the period start
    positive: int = 0
    neutral: int = 0
    negative: int = 0

    @property
    def total(self) -> int:
        return self.positive + self.neutral + self.negative

    def complaint_percentage(self) -> float | None:
        """negative/total as a percentage to 1dp, or None when no data."""
        if self.total == 0:
            return None
        return round(100.0 * self.negative / self.total, 1)

    def to_dict(self) -> dict:
        return {
            "period": self.period,
            "positive": self.positive,
            "neutral": self.neutral,
            "negative": self.negative,
            "total": self.total,
            "complaint_percentage": self.complaint_percentage(),
            "no_data": self.total == 0,
        }


@dataclass
class AspectTrend:
    """A full time series for one aspect."""

    aspect: Aspect
    buckets: list[TrendBucket] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "aspect": self.aspect.value,
            "buckets": [b.to_dict() for b in self.buckets],
        }


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _add_months(d: date, n: int) -> date:
    total = d.year * 12 + (d.month - 1) + n
    y, m = divmod(total, 12)
    return date(y, m + 1, 1)


def _week_start(d: date) -> date:
    """Monday of the week containing ``d`` (IST, Req 7.1)."""
    return d - timedelta(days=d.weekday())


def _period_starts(start: date, end: date, granularity: str) -> list[date]:
    starts: list[date] = []
    if granularity == "weekly":
        cur = _week_start(start)
        last = _week_start(end)
        while cur <= last:
            starts.append(cur)
            cur = cur + timedelta(days=7)
    else:  # monthly
        cur = _month_start(start)
        last = _month_start(end)
        while cur <= last:
            starts.append(cur)
            cur = _add_months(cur, 1)
    return starts


def _bucket_key(d: date, granularity: str) -> date:
    return _week_start(d) if granularity == "weekly" else _month_start(d)


def validate_range(start: date | None, end: date | None, today: date) -> tuple[date, date]:
    """Validate/complete the date range (Req 7.5).

    Defaults to the most recent 12 calendar months ending today. Raises
    :class:`TrendValidationError` when end < start or the span exceeds 36
    months or is shorter than one week.
    """
    if end is None:
        end = today
    if start is None:
        start = _add_months(_month_start(end), -(DEFAULT_RANGE_MONTHS - 1))
    if end < start:
        raise TrendValidationError("end date is before start date")
    if (end - start).days < MIN_RANGE_DAYS:
        raise TrendValidationError("date range must be at least 1 week")
    # >36 months (measured on month boundaries) is invalid.
    span_months = (end.year - start.year) * 12 + (end.month - start.month)
    if span_months > MAX_RANGE_MONTHS or (
        span_months == MAX_RANGE_MONTHS and end.day >= start.day
    ):
        raise TrendValidationError("date range must not exceed 36 months")
    return start, end


class TrendService:
    """Compute aspect trends from the analytics mention panel."""

    def __init__(self, observations: tuple[MentionObservation, ...] | None = None) -> None:
        self._obs = observations if observations is not None else generate_observations()

    def aspect_trends(
        self,
        granularity: str = "monthly",
        platforms: list[Platform] | None = None,
        start: date | None = None,
        end: date | None = None,
        today: date | None = None,
        aspects: list[Aspect] | None = None,
    ) -> dict:
        """Return per-aspect trends honouring the filters + invariants."""
        if granularity not in ("monthly", "weekly"):
            raise TrendValidationError(f"unknown granularity {granularity!r}")
        today = today or max((o.date for o in self._obs), default=date.today())
        start, end = validate_range(start, end, today)

        selected_platforms = set(platforms) if platforms else set(Platform)
        selected_aspects = aspects or list(Aspect)

        starts = _period_starts(start, end, granularity)
        # aspect -> period_start -> TrendBucket
        series: dict[Aspect, dict[date, TrendBucket]] = {
            a: {s: TrendBucket(period=s.isoformat()) for s in starts}
            for a in selected_aspects
        }

        for obs in self._obs:
            if obs.aspect not in series:
                continue
            if obs.platform not in selected_platforms:
                continue
            if obs.date < start or obs.date > end:
                continue
            key = _bucket_key(obs.date, granularity)
            bucket = series[obs.aspect].get(key)
            if bucket is None:
                continue
            if obs.label is SentimentLabel.POSITIVE:
                bucket.positive += 1
            elif obs.label is SentimentLabel.NEUTRAL:
                bucket.neutral += 1
            else:
                bucket.negative += 1

        trends = [
            AspectTrend(aspect=a, buckets=[series[a][s] for s in starts])
            for a in selected_aspects
        ]
        return {
            "granularity": granularity,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "platforms": sorted(p.value for p in selected_platforms),
            "trends": [t.to_dict() for t in trends],
        }

    def complaint_trend(
        self,
        aspect: Aspect,
        granularity: str = "monthly",
        platforms: list[Platform] | None = None,
        start: date | None = None,
        end: date | None = None,
        today: date | None = None,
    ) -> dict:
        """Category complaint trend (negative/total %) for one aspect."""
        result = self.aspect_trends(
            granularity=granularity,
            platforms=platforms,
            start=start,
            end=end,
            today=today,
            aspects=[aspect],
        )
        return result["trends"][0]
