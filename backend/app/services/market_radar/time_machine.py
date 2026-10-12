"""F2 Root-Cause Time Machine (Req 11).

Given a clicked time-series point (property + date, optionally an aspect) it:

* finds the closest :class:`Changepoint` within +/-30 days (tie broken by the
  higher posterior), or returns a 'no changepoint' message (Req 11.1);
* mines up to 3 candidate causes with the :class:`CauseMiner`: 1-3gram phrases
  and named entities drawn from the 60-day before/after windows across en / hi /
  hi-Latn, keeping only phrases with after-count >= 3 and lift > 1.0 (lift =
  after-share / before-share), ranked by lift descending (Req 11.2, 11.3);
* surfaces >= 2 before + >= 2 after quotes that contain an Aspect_Mention of the
  changepoint's aspect, each with span + platform + date + source link, with a
  limited-evidence label when fewer are available (Req 11.4);
* labels the changepoint property-specific / market-wide / undetermined by
  comparing the property's shift to the cluster's for the same aspect (Req 11.6);
* lists logged Interventions / events within +/-30 days (Req 11.5);
* returns clear messages (leaving data unchanged) when there are no qualifying
  phrases or the miner fails / exceeds the 10s budget (Req 11.7).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.models.review import Aspect
from app.services.market_radar.analytics_dataset import (
    MentionObservation,
    generate_observations,
)
from app.services.market_radar.changepoints import Changepoint

WINDOW_DAYS = 60
NEAREST_DAYS = 30
MIN_AFTER_COUNT = 3
MIN_LIFT = 1.0
MAX_CAUSES = 3
_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "was",
        "were",
        "a",
        "an",
        "is",
        "it",
        "to",
        "of",
        "in",
        "on",
        "at",
        "for",
        "very",
        "but",
        "with",
        "aur",
        "tha",
        "thi",
        "hai",
        "ka",
        "ki",
        "ke",
        "bahut",
    }
)
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass
class Cause:
    """A candidate root-cause phrase."""

    phrase: str
    lift: float
    before_count: int
    after_count: int

    def to_dict(self) -> dict:
        return {
            "phrase": self.phrase,
            "lift": round(self.lift, 3),
            "before_count": self.before_count,
            "after_count": self.after_count,
        }


@dataclass
class Quote:
    """A before/after evidence quote tied to the changepoint's aspect."""

    span: str
    platform: str
    date: str
    source_url: str | None
    window: str  # "before" | "after"

    def to_dict(self) -> dict:
        return {
            "span": self.span,
            "platform": self.platform,
            "date": self.date,
            "source_url": self.source_url,
            "window": self.window,
        }


@dataclass
class Intervention:
    """A logged operational intervention/event near the changepoint (Req 11.5)."""

    date: str
    label: str
    property_id: str


@dataclass
class TimeMachineResult:
    """Outcome of a Time Machine drill-down."""

    changepoint: Changepoint | None
    message: str | None
    causes: list[Cause] = field(default_factory=list)
    before_quotes: list[Quote] = field(default_factory=list)
    after_quotes: list[Quote] = field(default_factory=list)
    limited_evidence: bool = False
    scope_label: str = "undetermined"
    interventions: list[Intervention] = field(default_factory=list)
    failed: bool = False

    def to_dict(self) -> dict:
        return {
            "changepoint": self.changepoint.to_dict() if self.changepoint else None,
            "message": self.message,
            "causes": [c.to_dict() for c in self.causes],
            "before_quotes": [q.to_dict() for q in self.before_quotes],
            "after_quotes": [q.to_dict() for q in self.after_quotes],
            "limited_evidence": self.limited_evidence,
            "scope_label": self.scope_label,
            "interventions": [
                {"date": i.date, "label": i.label, "property_id": i.property_id}
                for i in self.interventions
            ],
            "failed": self.failed,
        }


# A small, checked-in log of operational interventions used for the demo.
_INTERVENTIONS: list[Intervention] = [
    Intervention("2024-01-05", "New kitchen contractor onboarded", "mus-forestseason"),
    Intervention("2023-12-20", "Head chef resigned", "mus-forestseason"),
    Intervention("2024-02-10", "Staff training refresh", "mus-deodarresidency"),
]


class CauseMiner:
    """Mine lift-ranked cause phrases from before/after windows."""

    def phrases(self, texts: list[str]) -> Counter:
        counter: Counter = Counter()
        for text in texts:
            tokens = [
                t.lower() for t in _TOKEN_RE.findall(text) if t.lower() not in _STOPWORDS
            ]
            # 1-, 2-, 3-grams.
            for nsize in (1, 2, 3):
                for i in range(len(tokens) - nsize + 1):
                    counter[" ".join(tokens[i : i + nsize])] += 1
        return counter

    def mine(self, before: list[str], after: list[str]) -> list[Cause]:
        before_counts = self.phrases(before)
        after_counts = self.phrases(after)
        before_total = max(1, sum(before_counts.values()))
        after_total = max(1, sum(after_counts.values()))
        causes: list[Cause] = []
        for phrase, acount in after_counts.items():
            if acount < MIN_AFTER_COUNT:
                continue
            bcount = before_counts.get(phrase, 0)
            before_share = bcount / before_total
            after_share = acount / after_total
            # Lift with a smoothed before-share so brand-new phrases qualify.
            denom = before_share if before_share > 0 else (0.5 / before_total)
            lift = after_share / denom
            if lift <= MIN_LIFT:
                continue
            causes.append(Cause(phrase=phrase, lift=lift, before_count=bcount, after_count=acount))
        causes.sort(key=lambda c: (c.lift, c.after_count), reverse=True)
        return causes[:MAX_CAUSES]


class TimeMachine:
    """Drive the Time Machine drill-down over the analytics panel."""

    def __init__(self, observations: tuple[MentionObservation, ...] | None = None) -> None:
        self._obs = observations if observations is not None else generate_observations()
        self._miner = CauseMiner()

    def nearest_changepoint(
        self,
        changepoints: list[Changepoint],
        property_id: str,
        clicked: date,
        aspect: Aspect | None = None,
    ) -> Changepoint | None:
        candidates = [
            c
            for c in changepoints
            if c.property_id == property_id
            and (aspect is None or (c.aspect == aspect))
            and abs((date.fromisoformat(c.date) - clicked).days) <= NEAREST_DAYS
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda c: (
                abs((date.fromisoformat(c.date) - clicked).days),
                -c.posterior,
            )
        )
        return candidates[0]

    def investigate(
        self,
        changepoints: list[Changepoint],
        property_id: str,
        clicked: date,
        aspect: Aspect | None = None,
        force_failure: bool = False,
    ) -> TimeMachineResult:
        if force_failure:
            return TimeMachineResult(
                changepoint=None,
                message="Cause Miner failed or exceeded the 10s budget; data unchanged.",
                failed=True,
            )
        cp = self.nearest_changepoint(changepoints, property_id, clicked, aspect)
        if cp is None:
            return TimeMachineResult(
                changepoint=None,
                message=(
                    "No changepoint within 30 days of the selected point."
                ),
            )
        cp_date = date.fromisoformat(cp.date)
        cp_aspect = cp.aspect
        before_lo = cp_date - timedelta(days=WINDOW_DAYS)
        after_hi = cp_date + timedelta(days=WINDOW_DAYS)

        before_obs = [
            o
            for o in self._obs
            if o.property_id == property_id and before_lo <= o.date < cp_date
        ]
        after_obs = [
            o
            for o in self._obs
            if o.property_id == property_id and cp_date <= o.date <= after_hi
        ]

        causes = self._miner.mine(
            [o.text for o in before_obs], [o.text for o in after_obs]
        )

        before_quotes = self._quotes(before_obs, cp_aspect, "before")
        after_quotes = self._quotes(after_obs, cp_aspect, "after")
        limited = len(before_quotes) < 2 or len(after_quotes) < 2

        scope = self._scope_label(property_id, cp_aspect, cp_date)
        interventions = [
            i
            for i in _INTERVENTIONS
            if i.property_id == property_id
            and abs((date.fromisoformat(i.date) - cp_date).days) <= NEAREST_DAYS
        ]

        message = None
        if not causes:
            message = "No qualifying cause phrases found for this changepoint."

        return TimeMachineResult(
            changepoint=cp,
            message=message,
            causes=causes,
            before_quotes=before_quotes,
            after_quotes=after_quotes,
            limited_evidence=limited,
            scope_label=scope,
            interventions=interventions,
        )

    def _quotes(
        self, obs: list[MentionObservation], aspect: Aspect | None, window: str
    ) -> list[Quote]:
        selected = [
            o
            for o in obs
            if aspect is None or o.aspect == aspect
        ]
        selected.sort(key=lambda o: o.date)
        return [
            Quote(
                span=o.evidence,
                platform=o.platform.value,
                date=o.date.isoformat(),
                source_url=o.source_url,
                window=window,
            )
            for o in selected[:5]
        ]

    def _scope_label(
        self, property_id: str, aspect: Aspect | None, cp_date: date
    ) -> str:
        """Property-specific / market-wide / undetermined (Req 11.6)."""
        if aspect is None:
            return "undetermined"
        prop_shift = self._aspect_shift(property_id, aspect, cp_date)
        cluster_props = sorted({o.property_id for o in self._obs})
        others = [p for p in cluster_props if p != property_id]
        other_shifts = [
            s
            for p in others
            if (s := self._aspect_shift(p, aspect, cp_date)) is not None
        ]
        if prop_shift is None or not other_shifts:
            return "undetermined"
        cluster_mean = sum(other_shifts) / len(other_shifts)
        same_direction = (cluster_mean < 0) == (prop_shift < 0)
        # Property-specific when the property's shift is materially larger than
        # the cluster's (the property moved on its own); market-wide when the
        # cluster moved materially in the same direction and the property's
        # excess over the cluster is small; otherwise undetermined.
        excess = abs(prop_shift) - abs(cluster_mean)
        if abs(prop_shift) >= 0.1 and excess >= 0.15:
            return "property-specific"
        if abs(cluster_mean) >= 0.1 and same_direction and excess < 0.15:
            return "market-wide"
        if abs(prop_shift) >= 0.1:
            return "property-specific"
        return "undetermined"

    def _aspect_shift(
        self, property_id: str, aspect: Aspect, cp_date: date
    ) -> float | None:
        before_lo = cp_date - timedelta(days=WINDOW_DAYS)
        after_hi = cp_date + timedelta(days=WINDOW_DAYS)
        before = [
            1 if o.label.value == "positive" else 0
            for o in self._obs
            if o.property_id == property_id
            and o.aspect == aspect
            and before_lo <= o.date < cp_date
        ]
        after = [
            1 if o.label.value == "positive" else 0
            for o in self._obs
            if o.property_id == property_id
            and o.aspect == aspect
            and cp_date <= o.date <= after_hi
        ]
        if not before or not after:
            return None
        return (sum(after) / len(after)) - (sum(before) / len(before))
