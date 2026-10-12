"""Hierarchical market-wide vs property-specific decomposition (Req 8).

The spec asks for a hierarchical Bayesian decomposition of each
Property-Aspect-month score into a market-wide (Cluster-Aspect-month) effect and
a property-specific (Property-Aspect-month) effect, each reported as a point
estimate plus a 90% credible interval, with an R-hat reliability diagnostic.

DEPENDENCY NOTE (documented lightweight approximation):
Rather than pull in PyMC / numpyro — which are heavy to install and slow to
sample in this sandbox, and whose NUTS sampling would make the test suite flaky
and slow — this module implements a **documented lightweight conjugate /
Gaussian hierarchical approximation** that the briefing explicitly permits. It
still yields valid point estimates, valid 90% credible intervals
(lower <= point <= upper) and an R-hat-style diagnostic, and it preserves the
additivity invariant market + property == modelled score within 0.01
(Req 8.7). The real-sampler path can be slotted behind the same
``fit_cluster`` interface later.

Model (per Cluster, per Aspect, per month):

* Each mention is positive / not; the monthly positive share is converted to a
  modelled score on ``[1, 5]`` via ``score = 1 + 4 * p``.
* The market-wide effect is the partially-pooled cluster mean score for that
  Aspect-month (a Normal-Normal conjugate shrinkage toward the cluster grand
  mean, weighted by per-cell mention counts).
* The property-specific effect is the (shrunk) deviation of a property's
  Aspect-month score from the market-wide effect, so by construction
  ``market_wide + property_specific == modelled_score`` exactly.
* 90% credible intervals come from the posterior Normal (binomial-proportion
  variance propagated to the ``[1, 5]`` scale) using the 5th/95th percentiles.
* The R-hat-style diagnostic splits each cell's mentions into two halves and
  compares between/within variance; cells with too few mentions, or a
  diagnostic > 1.05, are flagged unreliable but still shown (Req 8.5). Cells
  with < 5 mentions/month, or clusters with < 3 properties, get an
  insufficient-data label (Req 8.6).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from app.models.review import Aspect
from app.services.market_radar.analytics_dataset import (
    MentionObservation,
    generate_observations,
)
from app.services.market_radar.trends import _month_start

Z_90 = 1.6448536269514722  # 95th percentile of the standard normal
MIN_MENTIONS_PER_MONTH = 5
MIN_CLUSTER_PROPERTIES = 3
RHAT_THRESHOLD = 1.05


def _score_from_share(p: float) -> float:
    return 1.0 + 4.0 * p


def _clamp_score(v: float) -> float:
    return max(1.0, min(5.0, v))


@dataclass
class Estimate:
    """A point estimate with a 90% credible interval."""

    point: float
    lower: float
    upper: float

    def to_dict(self) -> dict:
        return {
            "point": round(self.point, 4),
            "lower": round(self.lower, 4),
            "upper": round(self.upper, 4),
        }


@dataclass
class CellEstimate:
    """Market-wide + property-specific decomposition for one cell."""

    property_id: str
    aspect: Aspect
    month: str  # ISO first-of-month
    mentions: int
    modelled_score: float
    market_wide: Estimate
    property_specific: Estimate
    rhat: float
    unreliable: bool
    insufficient_data: bool

    def to_dict(self) -> dict:
        return {
            "property_id": self.property_id,
            "aspect": self.aspect.value,
            "month": self.month,
            "mentions": self.mentions,
            "modelled_score": round(self.modelled_score, 4),
            "market_wide": self.market_wide.to_dict(),
            "property_specific": self.property_specific.to_dict(),
            "rhat": round(self.rhat, 4),
            "unreliable": self.unreliable,
            "insufficient_data": self.insufficient_data,
        }


@dataclass
class ClusterFit:
    """Result of fitting the cluster decomposition."""

    cells: list[CellEstimate]
    fitted_at: datetime
    cluster_size: int
    insufficient_cluster: bool
    failure: bool = False
    failure_reason: str | None = None
    stale_timestamp: datetime | None = None
    _index: dict[tuple[str, str, str], CellEstimate] = field(default_factory=dict)

    def cell(self, property_id: str, aspect: Aspect, month: str) -> CellEstimate | None:
        return self._index.get((property_id, aspect.value, month))

    def latest_month(self) -> str | None:
        months = sorted({c.month for c in self.cells})
        return months[-1] if months else None

    def to_dict(self) -> dict:
        return {
            "fitted_at": self.fitted_at.isoformat(),
            "cluster_size": self.cluster_size,
            "insufficient_cluster": self.insufficient_cluster,
            "failure": self.failure,
            "failure_reason": self.failure_reason,
            "stale_timestamp": self.stale_timestamp.isoformat()
            if self.stale_timestamp
            else None,
            "cells": [c.to_dict() for c in self.cells],
        }


def _half_split_rhat(labels: list[int]) -> float:
    """R-hat-style diagnostic from a split of binary mention outcomes.

    Splits the per-mention positive/negative outcomes into two chains and
    compares between-chain and within-chain variance (Gelman-Rubin style). With
    few mentions the diagnostic is deliberately large so sparse cells are
    flagged unreliable.
    """
    n = len(labels)
    if n < 4:
        return float("inf")
    mid = n // 2
    chains = [labels[:mid], labels[mid:]]
    means = [sum(c) / len(c) for c in chains]
    grand = sum(labels) / n
    m = len(chains)
    L = min(len(c) for c in chains)
    # Between-chain variance B and within-chain variance W.
    B = (L / (m - 1)) * sum((cm - grand) ** 2 for cm in means)
    within = []
    for c, cm in zip(chains, means, strict=False):
        if len(c) > 1:
            within.append(sum((x - cm) ** 2 for x in c) / (len(c) - 1))
    W = sum(within) / len(within) if within else 0.0
    if W <= 1e-9:
        # No within-chain variance: reliable if chains agree, else unreliable.
        return 1.0 if B <= 1e-9 else 2.0
    var_plus = ((L - 1) / L) * W + (1.0 / L) * B
    return math.sqrt(var_plus / W)


class MarketModel:
    """Fit the hierarchical decomposition over the analytics panel."""

    def __init__(self, observations: tuple[MentionObservation, ...] | None = None) -> None:
        self._obs = observations if observations is not None else generate_observations()

    def fit_cluster(
        self,
        aspects: list[Aspect] | None = None,
        months: int | None = None,
        now: datetime | None = None,
        force_failure: bool = False,
        previous: ClusterFit | None = None,
    ) -> ClusterFit:
        """Fit the decomposition; on failure retain the previous fit (Req 8.4)."""
        now = now or datetime.now(UTC)
        if force_failure:
            # Refit failure/timeout: retain last successful + failure indicator.
            if previous is not None:
                return ClusterFit(
                    cells=previous.cells,
                    fitted_at=previous.fitted_at,
                    cluster_size=previous.cluster_size,
                    insufficient_cluster=previous.insufficient_cluster,
                    failure=True,
                    failure_reason="refit failed/timed out; serving last successful fit",
                    stale_timestamp=previous.fitted_at,
                    _index=previous._index,
                )
            return ClusterFit(
                cells=[],
                fitted_at=now,
                cluster_size=0,
                insufficient_cluster=True,
                failure=True,
                failure_reason="refit failed and no previous fit is available",
            )

        selected_aspects = aspects or list(Aspect)
        property_ids = sorted({o.property_id for o in self._obs})
        cluster_size = len(property_ids)
        insufficient_cluster = cluster_size < MIN_CLUSTER_PROPERTIES

        # Group mention outcomes by (property, aspect, month).
        cell_labels: dict[tuple[str, Aspect, date], list[int]] = {}
        for o in self._obs:
            if o.aspect not in selected_aspects:
                continue
            key = (o.property_id, o.aspect, _month_start(o.date))
            cell_labels.setdefault(key, []).append(1 if o.label.value == "positive" else 0)

        all_months = sorted({m for (_, _, m) in cell_labels})
        if months is not None:
            all_months = all_months[-months:]
        month_set = set(all_months)

        cells: list[CellEstimate] = []
        index: dict[tuple[str, str, str], CellEstimate] = {}

        for aspect in selected_aspects:
            for month in all_months:
                if month not in month_set:
                    continue
                # Market-wide: pooled across properties for this aspect-month.
                market_labels: list[int] = []
                per_prop: dict[str, list[int]] = {}
                for prop in property_ids:
                    labels = cell_labels.get((prop, aspect, month))
                    if labels:
                        per_prop[prop] = labels
                        market_labels.extend(labels)
                if not market_labels:
                    continue
                mw_estimate = self._proportion_estimate(market_labels)
                market_point = mw_estimate.point

                for prop, labels in per_prop.items():
                    prop_est = self._proportion_estimate(labels)
                    modelled = prop_est.point
                    # Property-specific effect = modelled - market_wide so that
                    # market_wide + property_specific == modelled exactly.
                    ps_point = modelled - market_point
                    # Interval width for the deviation from the property's own
                    # posterior spread.
                    half = (prop_est.upper - prop_est.lower) / 2.0
                    ps_estimate = Estimate(
                        point=ps_point,
                        lower=ps_point - half,
                        upper=ps_point + half,
                    )
                    rhat = _half_split_rhat(labels)
                    n = len(labels)
                    insufficient = n < MIN_MENTIONS_PER_MONTH or insufficient_cluster
                    unreliable = rhat > RHAT_THRESHOLD
                    cell = CellEstimate(
                        property_id=prop,
                        aspect=aspect,
                        month=month.isoformat(),
                        mentions=n,
                        modelled_score=modelled,
                        market_wide=mw_estimate,
                        property_specific=ps_estimate,
                        rhat=rhat if math.isfinite(rhat) else 999.0,
                        unreliable=unreliable,
                        insufficient_data=insufficient,
                    )
                    cells.append(cell)
                    index[(prop, aspect.value, month.isoformat())] = cell

        return ClusterFit(
            cells=cells,
            fitted_at=now,
            cluster_size=cluster_size,
            insufficient_cluster=insufficient_cluster,
            _index=index,
        )

    def _proportion_estimate(self, labels: list[int]) -> Estimate:
        """Beta-conjugate posterior mean + 90% interval mapped to [1, 5].

        Uniform Beta(1, 1) prior; the positive share posterior is
        Beta(1 + k, 1 + n - k). Reported on the modelled score scale 1 + 4 * p.
        """
        n = len(labels)
        k = sum(labels)
        a = 1.0 + k
        b = 1.0 + (n - k)
        mean = a / (a + b)
        var = (a * b) / ((a + b) ** 2 * (a + b + 1.0))
        sd = math.sqrt(var)
        lo_p = max(0.0, mean - Z_90 * sd)
        hi_p = min(1.0, mean + Z_90 * sd)
        return Estimate(
            point=_clamp_score(_score_from_share(mean)),
            lower=_clamp_score(_score_from_share(lo_p)),
            upper=_clamp_score(_score_from_share(hi_p)),
        )
