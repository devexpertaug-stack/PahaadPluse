"""F6 Market Gap Finder (Req 13).

Finds issue themes (Aspects) where the whole Cluster underperforms:

* rank themes first by the count of distinct Cluster Properties whose negative
  share exceeds the *destination median* negative share for that theme, then by
  total negative mentions (Req 13.1, 13.2);
* for each theme report the Aspect, the affected-property count, total negative
  mentions, a 6-month negative-share trend, and >= 3 linked evidence quotes
  (Req 13.3);
* label a theme a 'market gap' when its negative share is above the median at
  >= 60% of Cluster Properties (Req 13.5);
* invariant: affected properties <= Cluster size (Req 13.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from statistics import median

from app.models.review import Aspect
from app.services.market_radar.analytics_dataset import (
    MentionObservation,
    generate_observations,
)
from app.services.market_radar.trends import _month_start

MARKET_GAP_FRACTION = 0.60
MIN_QUOTES = 3
TREND_MONTHS = 6


@dataclass
class GapQuote:
    span: str
    platform: str
    date: str
    property_id: str
    source_url: str | None

    def to_dict(self) -> dict:
        return {
            "span": self.span,
            "platform": self.platform,
            "date": self.date,
            "property_id": self.property_id,
            "source_url": self.source_url,
        }


@dataclass
class GapTheme:
    aspect: Aspect
    affected_properties: int
    cluster_size: int
    total_negatives: int
    destination_median: float
    trend: list[dict]  # [{month, negative_share}]
    quotes: list[GapQuote]
    market_gap: bool

    def to_dict(self) -> dict:
        return {
            "aspect": self.aspect.value,
            "affected_properties": self.affected_properties,
            "cluster_size": self.cluster_size,
            "total_negatives": self.total_negatives,
            "destination_median": round(self.destination_median, 4),
            "trend": self.trend,
            "quotes": [q.to_dict() for q in self.quotes],
            "market_gap": self.market_gap,
        }


@dataclass
class GapFinderResult:
    themes: list[GapTheme] = field(default_factory=list)
    cluster_size: int = 0

    def to_dict(self) -> dict:
        return {
            "cluster_size": self.cluster_size,
            "themes": [t.to_dict() for t in self.themes],
        }


class GapFinder:
    """Rank cluster-wide issue themes by breadth then depth."""

    def __init__(self, observations: tuple[MentionObservation, ...] | None = None) -> None:
        self._obs = observations if observations is not None else generate_observations()

    def find(self, today: date | None = None) -> GapFinderResult:
        property_ids = sorted({o.property_id for o in self._obs})
        cluster_size = len(property_ids)
        today = today or max((o.date for o in self._obs), default=date.today())

        themes: list[GapTheme] = []
        for aspect in Aspect:
            # Per-property negative share for this aspect.
            shares: dict[str, float] = {}
            totals_neg: dict[str, int] = {}
            for prop in property_ids:
                labels = [
                    o.label.value
                    for o in self._obs
                    if o.property_id == prop and o.aspect == aspect
                ]
                if not labels:
                    continue
                neg = sum(1 for lbl in labels if lbl == "negative")
                shares[prop] = neg / len(labels)
                totals_neg[prop] = neg
            if not shares:
                continue
            med = median(shares.values())
            affected = [p for p, s in shares.items() if s > med]
            affected_count = len(affected)
            total_negatives = sum(totals_neg.values())
            market_gap = cluster_size > 0 and (
                affected_count / cluster_size >= MARKET_GAP_FRACTION
            )
            themes.append(
                GapTheme(
                    aspect=aspect,
                    affected_properties=affected_count,
                    cluster_size=cluster_size,
                    total_negatives=total_negatives,
                    destination_median=med,
                    trend=self._trend(aspect, today),
                    quotes=self._quotes(aspect),
                    market_gap=market_gap,
                )
            )

        # Rank: affected-property count desc, then total negatives desc.
        themes.sort(key=lambda t: (t.affected_properties, t.total_negatives), reverse=True)
        return GapFinderResult(themes=themes, cluster_size=cluster_size)

    def _trend(self, aspect: Aspect, today: date) -> list[dict]:
        # Last 6 calendar months of cluster-wide negative share.
        months: list[date] = []
        cur = _month_start(today)
        for _ in range(TREND_MONTHS):
            months.append(cur)
            # step back one month
            total = cur.year * 12 + (cur.month - 1) - 1
            y, m = divmod(total, 12)
            cur = date(y, m + 1, 1)
        months.reverse()
        out: list[dict] = []
        for mstart in months:
            labels = [
                o.label.value
                for o in self._obs
                if o.aspect == aspect and _month_start(o.date) == mstart
            ]
            if labels:
                neg = sum(1 for lbl in labels if lbl == "negative")
                share = round(neg / len(labels), 4)
            else:
                share = None
            out.append({"month": mstart.isoformat(), "negative_share": share})
        return out

    def _quotes(self, aspect: Aspect) -> list[GapQuote]:
        negs = [
            o
            for o in self._obs
            if o.aspect == aspect and o.label.value == "negative"
        ]
        negs.sort(key=lambda o: o.date, reverse=True)
        seen: set[tuple[str, str]] = set()
        quotes: list[GapQuote] = []
        for o in negs:
            key = (o.property_id, o.evidence)
            if key in seen:
                continue
            seen.add(key)
            quotes.append(
                GapQuote(
                    span=o.evidence,
                    platform=o.platform.value,
                    date=o.date.isoformat(),
                    property_id=o.property_id,
                    source_url=o.source_url,
                )
            )
            if len(quotes) >= max(MIN_QUOTES, 3):
                break
        return quotes
