"""F1 Rating What-If Simulator (Req 10).

Estimates a per-Aspect, per-Platform ``Driver_Weight`` — the change in a
property's normalised overall rating per +1 point change in that Aspect's
score — by regressing (ordinary least squares, closed form) the per-review
normalised overall rating on the per-review aspect scores across *all* Cluster
Review_Records on that platform. Each weight carries a 90% interval from the
regression's standard error.

A projection combines all non-zero slider deltas with the driver weights to
return, within the latency budget:

* the projected overall rating to 2dp, bounded to ``[1, 5]`` (Req 10.4);
* its 90% interval; and
* the projected Cluster rank (1..N).

Properties:

* identity (Req 10.5): all-zero deltas return within 0.01 of the current rating
  and the current rank.
* metamorphic (Req 10.6): a single +step on one aspect moves the projection in
  the sign of that aspect's Driver_Weight, unless the slider is at a bound or
  the weight is 0.
* driver weights are ranked by ``|value|`` descending (Req 10.7).

Low-confidence labels apply when a platform has < 50 Cluster reviews; aspects
with no data are flagged so the UI can disable their sliders; a projection
failure or > 2s latency keeps the previous values + an error (handled by the
caller).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from app.models.review import Aspect, Platform
from app.services.market_radar.analytics_dataset import (
    MentionObservation,
    cluster_property_ids,
    generate_observations,
    property_name,
)

SLIDER_MIN = -1.0
SLIDER_MAX = 1.0
SLIDER_STEP = 0.1
SCORE_MIN = 1.0
SCORE_MAX = 5.0
LOW_CONFIDENCE_REVIEWS = 50
Z_90 = 1.6448536269514722


@dataclass
class DriverWeight:
    """A per-aspect driver weight with a 90% interval."""

    aspect: Aspect
    weight: float
    lower: float
    upper: float
    available: bool

    def to_dict(self) -> dict:
        return {
            "aspect": self.aspect.value,
            "weight": round(self.weight, 4),
            "lower": round(self.lower, 4),
            "upper": round(self.upper, 4),
            "available": self.available,
            "abs_weight": round(abs(self.weight), 4),
        }


@dataclass
class PlatformModel:
    """Driver weights + baselines for one platform."""

    platform: Platform
    driver_weights: list[DriverWeight]
    current_rating: float
    review_count: int
    low_confidence: bool
    estimated_at: datetime
    # per-property current ratings for ranking
    property_ratings: dict[str, float]
    home_property_id: str
    _aspect_scores: dict[str, dict[str, float]]  # prop -> aspect -> mean score

    def to_dict(self) -> dict:
        ranked = sorted(self.driver_weights, key=lambda d: abs(d.weight), reverse=True)
        return {
            "platform": self.platform.value,
            "current_rating": round(self.current_rating, 2),
            "review_count": self.review_count,
            "low_confidence": self.low_confidence,
            "estimated_at": self.estimated_at.isoformat(),
            "home_property_id": self.home_property_id,
            "driver_weights": [d.to_dict() for d in ranked],
            "cluster_size": len(self.property_ratings),
        }


def _score_from_label(label: str) -> float:
    """Map a sentiment label to a per-review aspect score on [1, 5]."""
    return {"positive": 5.0, "neutral": 3.0, "negative": 1.0}.get(label, 3.0)


class WhatIfSimulator:
    """Estimate driver weights and run bounded projections."""

    def __init__(
        self,
        observations: tuple[MentionObservation, ...] | None = None,
        home_property_id: str | None = None,
    ) -> None:
        self._obs = observations if observations is not None else generate_observations()
        self._home = home_property_id or cluster_property_ids()[0]

    def platform_model(self, platform: Platform, now: datetime | None = None) -> PlatformModel:
        now = now or datetime.now(UTC)
        # Build per (property, review-id) rows: overall rating + aspect scores.
        # We approximate "a review" by (property, platform, date) grouping of
        # mentions; the overall rating is the mean aspect score of that group.
        rows: list[tuple[dict[Aspect, float], float]] = []
        prop_aspect_scores: dict[str, dict[Aspect, list[float]]] = {}
        prop_overall: dict[str, list[float]] = {}
        groups: dict[tuple[str, str], dict[Aspect, list[float]]] = {}

        for o in self._obs:
            if o.platform != platform:
                continue
            gkey = (o.property_id, o.date.isoformat())
            groups.setdefault(gkey, {}).setdefault(o.aspect, []).append(
                _score_from_label(o.label.value)
            )
            prop_aspect_scores.setdefault(o.property_id, {}).setdefault(o.aspect, []).append(
                _score_from_label(o.label.value)
            )

        review_count = len(groups)
        for (prop, _date), aspect_scores in groups.items():
            per_aspect = {a: sum(v) / len(v) for a, v in aspect_scores.items()}
            overall = sum(per_aspect.values()) / len(per_aspect)
            rows.append((per_aspect, overall))
            prop_overall.setdefault(prop, []).append(overall)

        driver_weights = self._fit_weights(rows)
        property_ratings = {
            p: round(sum(v) / len(v), 4) for p, v in prop_overall.items()
        }
        current_rating = property_ratings.get(self._home, 3.0)
        mean_scores = {
            p: {a.value: (sum(s) / len(s)) for a, s in am.items()}
            for p, am in prop_aspect_scores.items()
        }

        return PlatformModel(
            platform=platform,
            driver_weights=driver_weights,
            current_rating=current_rating,
            review_count=review_count,
            low_confidence=review_count < LOW_CONFIDENCE_REVIEWS,
            estimated_at=now,
            property_ratings=property_ratings,
            home_property_id=self._home,
            _aspect_scores=mean_scores,
        )

    def _fit_weights(
        self, rows: list[tuple[dict[Aspect, float], float]]
    ) -> list[DriverWeight]:
        """OLS of overall rating on per-aspect scores (one simple reg per aspect).

        A full multivariate OLS is sensitive to collinear aspect scores; a
        stable, interpretable Driver_Weight is the per-aspect slope from a
        simple linear regression of overall rating on that aspect's score,
        which is exactly "change in overall per 1-point aspect change" and keeps
        the metamorphic sign contract clean.
        """
        weights: list[DriverWeight] = []
        for aspect in Aspect:
            xs: list[float] = []
            ys: list[float] = []
            for per_aspect, overall in rows:
                if aspect in per_aspect:
                    xs.append(per_aspect[aspect])
                    ys.append(overall)
            if len(xs) < 2:
                weights.append(DriverWeight(aspect, 0.0, 0.0, 0.0, available=False))
                continue
            n = len(xs)
            mx = sum(xs) / n
            my = sum(ys) / n
            sxx = sum((x - mx) ** 2 for x in xs)
            sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False))
            if sxx <= 1e-9:
                weights.append(DriverWeight(aspect, 0.0, 0.0, 0.0, available=False))
                continue
            slope = sxy / sxx
            # Residual standard error -> SE of slope -> 90% interval.
            intercept = my - slope * mx
            resid = [y - (intercept + slope * x) for x, y in zip(xs, ys, strict=False)]
            dof = max(1, n - 2)
            s2 = sum(r * r for r in resid) / dof
            se = math.sqrt(s2 / sxx) if sxx > 0 else 0.0
            weights.append(
                DriverWeight(
                    aspect=aspect,
                    weight=slope,
                    lower=slope - Z_90 * se,
                    upper=slope + Z_90 * se,
                    available=True,
                )
            )
        return weights

    def project(
        self,
        model: PlatformModel,
        deltas: dict[Aspect, float],
    ) -> dict:
        """Project the overall rating + rank from slider deltas (Req 10.4)."""
        weight_by_aspect = {d.aspect: d for d in model.driver_weights}
        home_scores = model._aspect_scores.get(model.home_property_id, {})

        total_delta = 0.0
        lo_delta = 0.0
        hi_delta = 0.0
        applied: list[dict] = []
        for aspect, raw in deltas.items():
            dw = weight_by_aspect.get(aspect)
            if dw is None or not dw.available or raw == 0.0:
                continue
            # Cap the delta so the aspect's current score + delta stays in [1, 5].
            current = home_scores.get(aspect.value, 3.0)
            capped = max(SCORE_MIN - current, min(SCORE_MAX - current, raw))
            total_delta += dw.weight * capped
            lo_delta += dw.lower * capped
            hi_delta += dw.upper * capped
            applied.append({"aspect": aspect.value, "delta": round(capped, 2)})

        projected = _bound(model.current_rating + total_delta)
        # Interval endpoints also bounded.
        lo = _bound(model.current_rating + min(lo_delta, hi_delta))
        hi = _bound(model.current_rating + max(lo_delta, hi_delta))

        rank = self._rank(model, projected)
        return {
            "platform": model.platform.value,
            "current_rating": round(model.current_rating, 2),
            "projected_rating": round(projected, 2),
            "projected_lower": round(lo, 2),
            "projected_upper": round(hi, 2),
            "projected_rank": rank,
            "cluster_size": len(model.property_ratings),
            "low_confidence": model.low_confidence,
            "applied_deltas": applied,
        }

    def _rank(self, model: PlatformModel, projected: float) -> int:
        """1-based rank of the projected rating among the cluster (desc)."""
        others = [
            v for p, v in model.property_ratings.items() if p != model.home_property_id
        ]
        rank = 1 + sum(1 for v in others if v > projected)
        return rank

    def current_rank(self, model: PlatformModel) -> int:
        return self._rank(model, model.current_rating)


def _bound(v: float) -> float:
    return max(SCORE_MIN, min(SCORE_MAX, v))


def available_aspects(model: PlatformModel) -> list[str]:
    return [d.aspect.value for d in model.driver_weights if d.available]


def property_label(property_id: str) -> str:
    return property_name(property_id)
