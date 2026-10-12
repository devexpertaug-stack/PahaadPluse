"""Guest Compass contextual-bandit recommender (Req 28).

When a front-desk user opens a Stay we recommend up to three items drawn from
rooms / food / activities / spa / local-experiences, using the Stay context. A
cold-start segment (stay purpose + party composition + season) provides
segment-level priors when there is no past-stay history (Req 28.2). A
contextual-bandit policy (LinUCB) ranks candidate items from a context feature
vector and updates from accept/decline outcomes (Req 28.3). Aspects where the
Home_Property's negative share exceeds the Cluster median are down-weighted as a
market signal from the Market_Model (Req 28.4). Outcomes + any ancillary revenue
entered are recorded (Req 28.6); uptake rate + ancillary revenue per guest per
week are reported (Req 28.7). Upsell cards are suppressed while the Stay has an
open P1/P2 complaint (Req 28.8).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from app.models.review import Aspect, SentimentLabel
from app.services.market_radar.analytics_dataset import (
    HOME_PROPERTY_ID,
    MentionObservation,
    generate_observations,
)

MAX_CARDS = 3
RIDGE_LAMBDA = 1.0
UCB_ALPHA = 0.6


@dataclass(frozen=True)
class CatalogItem:
    """A recommendable ancillary item."""

    id: str
    category: str  # rooms | food | activities | spa | local-experiences
    name: str
    reason: str
    price_inr: float
    # Aspects whose market weakness should down-weight this item (Req 28.4).
    related_aspects: tuple[Aspect, ...] = ()


CATALOG: list[CatalogItem] = [
    CatalogItem("room-upgrade", "rooms", "Valley-view room upgrade",
                "Panoramic Doon valley view for your stay", 1800.0, (Aspect.ROOM,)),
    CatalogItem("candlelight-dinner", "food", "Candlelight hilltop dinner",
                "A quiet dinner with a Himalayan sunset", 2500.0, (Aspect.FOOD,)),
    CatalogItem("breakfast-inroom", "food", "In-room breakfast",
                "Fresh local breakfast served in your room", 600.0, (Aspect.FOOD,)),
    CatalogItem("nature-walk", "activities", "Guided Camel's Back nature walk",
                "Morning guided walk along the ridge", 800.0, (Aspect.LOCATION,)),
    CatalogItem("spa-ayurveda", "spa", "Ayurvedic hill spa therapy",
                "90-minute relaxation therapy", 2200.0, (Aspect.SERVICE,)),
    CatalogItem("mall-road-tour", "local-experiences", "Mall Road heritage tour",
                "Evening guided heritage walk", 1200.0, (Aspect.LOCATION,)),
    CatalogItem("bonfire-evening", "activities", "Private bonfire evening",
                "Bonfire with snacks for your group", 1500.0, (Aspect.SERVICE,)),
]

# Category index used in the context/arm feature vector.
_CATEGORIES = ["rooms", "food", "activities", "spa", "local-experiences"]


@dataclass
class Segment:
    """Cold-start segment with a prior preference per category (Req 28.2)."""

    purpose: str
    party: str  # solo | couple | family | group
    season: str  # winter | summer | monsoon | autumn

    def priors(self) -> dict[str, float]:
        """Segment-level priors (0..1) per category."""
        base = {c: 0.3 for c in _CATEGORIES}
        if self.party == "couple":
            base["food"] += 0.3
            base["spa"] += 0.2
        if self.party == "family":
            base["activities"] += 0.3
            base["rooms"] += 0.1
        if self.party == "group":
            base["activities"] += 0.3
            base["local-experiences"] += 0.2
        if self.party == "solo":
            base["local-experiences"] += 0.3
        if self.purpose == "honeymoon":
            base["spa"] += 0.3
            base["food"] += 0.2
        if self.purpose == "business":
            base["rooms"] += 0.2
        if self.season in ("winter", "autumn"):
            base["food"] += 0.1
        if self.season == "summer":
            base["activities"] += 0.1
        return {k: min(1.0, v) for k, v in base.items()}

    def key(self) -> str:
        return f"{self.purpose}|{self.party}|{self.season}"


def season_for(d: date) -> str:
    m = d.month
    if m in (12, 1, 2):
        return "winter"
    if m in (3, 4, 5):
        return "summer"
    if m in (6, 7, 8, 9):
        return "monsoon"
    return "autumn"


@dataclass
class LinUCBArm:
    """Per-arm LinUCB state (ridge regression with an exploration bonus)."""

    dim: int
    A: list[list[float]] = field(default_factory=list)
    b: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.A:
            self.A = [
                [RIDGE_LAMBDA if i == j else 0.0 for j in range(self.dim)]
                for i in range(self.dim)
            ]
        if not self.b:
            self.b = [0.0] * self.dim

    def _solve(self) -> list[float]:
        return _mat_vec(_inverse(self.A), self.b)

    def ucb(self, x: list[float]) -> float:
        theta = self._solve()
        mean = sum(t * xi for t, xi in zip(theta, x, strict=False))
        ainv = _inverse(self.A)
        var = sum(x[i] * sum(ainv[i][j] * x[j] for j in range(self.dim)) for i in range(self.dim))
        return mean + UCB_ALPHA * math.sqrt(max(0.0, var))

    def update(self, x: list[float], reward: float) -> None:
        for i in range(self.dim):
            for j in range(self.dim):
                self.A[i][j] += x[i] * x[j]
            self.b[i] += reward * x[i]


@dataclass
class Outcome:
    """A recorded recommendation outcome (Req 28.6)."""

    stay_id: str
    item_id: str
    accepted: bool
    revenue_inr: float
    at: datetime


@dataclass
class StayContext:
    """Minimal Stay context the recommender needs."""

    stay_id: str
    purpose: str
    party: str
    check_in: date
    has_open_p1_p2: bool = False
    has_history: bool = False


class GuestCompass:
    """Contextual-bandit recommender + outcome tracking (Req 28)."""

    def __init__(
        self,
        observations: tuple[MentionObservation, ...] | None = None,
        home_property_id: str = HOME_PROPERTY_ID,
    ) -> None:
        self._obs = observations if observations is not None else generate_observations()
        self._home = home_property_id
        self.dim = len(_CATEGORIES) + 1  # category one-hot + market-weakness feature
        self.arms: dict[str, LinUCBArm] = {
            item.id: LinUCBArm(dim=self.dim) for item in CATALOG
        }
        self.outcomes: list[Outcome] = []
        self._weak_aspects = self._market_weak_aspects()

    # ---- market signal from the Market_Model (Req 28.4) ----
    def _market_weak_aspects(self) -> set[Aspect]:
        """Aspects where the home negative share exceeds the Cluster median."""
        home_neg: dict[Aspect, tuple[int, int]] = {}
        cluster_neg: dict[Aspect, list[float]] = {}
        per_prop: dict[tuple[str, Aspect], list[int]] = {}
        for o in self._obs:
            key = (o.property_id, o.aspect)
            per_prop.setdefault(key, []).append(1 if o.label is SentimentLabel.NEGATIVE else 0)
        for (pid, aspect), labels in per_prop.items():
            share = sum(labels) / len(labels)
            cluster_neg.setdefault(aspect, []).append(share)
            if pid == self._home:
                home_neg[aspect] = (sum(labels), len(labels))
        weak: set[Aspect] = set()
        for aspect, shares in cluster_neg.items():
            if aspect not in home_neg:
                continue
            median = _median(shares)
            k, n = home_neg[aspect]
            home_share = k / n if n else 0.0
            if home_share > median:
                weak.add(aspect)
        return weak

    def _features(self, item: CatalogItem) -> list[float]:
        vec = [0.0] * self.dim
        vec[_CATEGORIES.index(item.category)] = 1.0
        # Last feature flags whether the item touches a market-weak aspect.
        weak = any(a in self._weak_aspects for a in item.related_aspects)
        vec[-1] = 1.0 if weak else 0.0
        return vec

    def recommend(self, ctx: StayContext) -> dict:
        # Req 28.8: suppress all upsell cards during an open P1/P2 complaint.
        if ctx.has_open_p1_p2:
            return {
                "stay_id": ctx.stay_id,
                "suppressed": True,
                "reason": "open P1/P2 complaint — upsell cards suppressed",
                "cards": [],
            }

        segment = Segment(
            purpose=ctx.purpose, party=ctx.party, season=season_for(ctx.check_in)
        )
        priors = segment.priors()

        scored: list[tuple[float, CatalogItem]] = []
        for item in CATALOG:
            x = self._features(item)
            score = self.arms[item.id].ucb(x)
            # Cold-start blend with the segment prior when no history (Req 28.2).
            if not ctx.has_history:
                score = 0.5 * score + 0.5 * priors[item.category]
            # Down-weight items tied to a market-weak aspect (Req 28.4).
            if any(a in self._weak_aspects for a in item.related_aspects):
                score *= 0.6
            scored.append((score, item))

        scored.sort(key=lambda s: s[0], reverse=True)
        cards = []
        for score, item in scored[:MAX_CARDS]:
            cards.append(
                {
                    "item_id": item.id,
                    "category": item.category,
                    "name": item.name,
                    "reason": item.reason,
                    "price_inr": item.price_inr,
                    "score": round(score, 4),
                    "market_down_weighted": any(
                        a in self._weak_aspects for a in item.related_aspects
                    ),
                }
            )
        return {
            "stay_id": ctx.stay_id,
            "suppressed": False,
            "segment": segment.key(),
            "cold_start": not ctx.has_history,
            "market_weak_aspects": sorted(a.value for a in self._weak_aspects),
            "cards": cards,
        }

    def record_outcome(
        self, ctx: StayContext, item_id: str, accepted: bool, revenue_inr: float = 0.0
    ) -> Outcome:
        """Record accept/decline + revenue and update the bandit (Req 28.3/28.6)."""
        if item_id not in self.arms:
            raise KeyError(f"unknown item {item_id!r}")
        item = next(i for i in CATALOG if i.id == item_id)
        x = self._features(item)
        reward = 1.0 if accepted else 0.0
        self.arms[item_id].update(x, reward)
        outcome = Outcome(
            stay_id=ctx.stay_id,
            item_id=item_id,
            accepted=accepted,
            revenue_inr=revenue_inr if accepted else 0.0,
            at=datetime.now(UTC),
        )
        self.outcomes.append(outcome)
        return outcome

    def metrics(self, guests_this_week: int = 1) -> dict:
        """Uptake rate + ancillary revenue per guest per week (Req 28.7)."""
        total = len(self.outcomes)
        accepted = sum(1 for o in self.outcomes if o.accepted)
        revenue = sum(o.revenue_inr for o in self.outcomes)
        uptake = (accepted / total) if total else 0.0
        guests = max(1, guests_this_week)
        return {
            "offers": total,
            "accepted": accepted,
            "uptake_rate": round(uptake, 3),
            "ancillary_revenue_inr": round(revenue, 2),
            "revenue_per_guest_per_week": round(revenue / guests, 2),
            "guests_this_week": guests,
        }


# ---- tiny linear-algebra helpers (small fixed dim, no numpy dependency) ----
def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _inverse(m: list[list[float]]) -> list[list[float]]:
    n = len(m)
    a = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m)]
    for col in range(n):
        pivot = a[col][col]
        if abs(pivot) < 1e-12:
            for r in range(col + 1, n):
                if abs(a[r][col]) > 1e-12:
                    a[col], a[r] = a[r], a[col]
                    pivot = a[col][col]
                    break
        pivot = a[col][col] or 1e-12
        a[col] = [v / pivot for v in a[col]]
        for r in range(n):
            if r == col:
                continue
            factor = a[r][col]
            a[r] = [v - factor * a[col][k] for k, v in enumerate(a[r])]
    return [row[n:] for row in a]


def _mat_vec(m: list[list[float]], v: list[float]) -> list[float]:
    return [sum(m[i][j] * v[j] for j in range(len(v))) for i in range(len(m))]


_compass: GuestCompass | None = None


def get_guest_compass() -> GuestCompass:
    """Return a process-wide Guest Compass instance (bandit state persists)."""
    global _compass
    if _compass is None:
        _compass = GuestCompass()
    return _compass
