"""F10 Proof of Impact — difference-in-differences effect of an Intervention
(Req 24).

A manager logs an :class:`~app.models.intervention.Intervention` (date, Aspect,
description, Home_Property). Once at least 30 days of post-Intervention reviews
exist for the Aspect, we estimate the causal effect on the Aspect *score* using
the other Cluster Properties as a control group (a classic 2x2
difference-in-differences):

    effect = (home_post - home_pre) - (control_post - control_pre)

The Aspect score for a (group, period) cell is ``1 + 4 * positive_share`` on the
``[1, 5]`` scale used across the platform. A 90% confidence interval comes from
the standard DiD standard error (the combined variance of the four cell means,
each a binomial-proportion variance propagated to the score scale). A
parallel-trends check regresses the pre-period weekly scores of the home vs
control group and warns when the two pre-trend slopes differ significantly
(p < 0.05) — the identifying assumption of DiD (Req 24.4).

Every number is sourced from the shared analytics mention panel so the website
can show pre/post trends for the Home_Property vs control and the drilldown can
re-derive each count.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from app.models.intervention import Intervention
from app.models.review import Aspect, SentimentLabel
from app.services.market_radar.analytics_dataset import (
    HOME_PROPERTY_ID,
    MentionObservation,
    generate_observations,
)
from app.services.market_radar.trends import _week_start

Z_90 = 1.6448536269514722
MIN_POST_DAYS = 30
# A t-ish critical value for the parallel-trends slope-difference test. With the
# modest weekly sample we use the normal approximation at the 5% two-sided level.
PARALLEL_TRENDS_P = 0.05


def _score_from_share(p: float) -> float:
    return 1.0 + 4.0 * p


@dataclass
class CellStat:
    """Mean Aspect score + variance for a (group, period) DiD cell."""

    n: int
    positives: int
    mean_score: float
    var_score: float

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "positives": self.positives,
            "mean_score": round(self.mean_score, 4),
        }


@dataclass
class ImpactResult:
    """Outcome of a Proof-of-Impact estimation for one Intervention."""

    intervention_id: str
    property_id: str
    aspect: str
    intervention_date: str
    sufficient_post_data: bool
    post_days: int
    effect: float | None
    ci_lower: float | None
    ci_upper: float | None
    home_pre: CellStat | None
    home_post: CellStat | None
    control_pre: CellStat | None
    control_post: CellStat | None
    parallel_trends_warning: bool
    parallel_trends_pvalue: float | None
    home_trend: list[dict]
    control_trend: list[dict]
    message: str | None = None

    def to_dict(self) -> dict:
        return {
            "intervention_id": self.intervention_id,
            "property_id": self.property_id,
            "aspect": self.aspect,
            "intervention_date": self.intervention_date,
            "sufficient_post_data": self.sufficient_post_data,
            "post_days": self.post_days,
            "effect": None if self.effect is None else round(self.effect, 4),
            "ci_lower": None if self.ci_lower is None else round(self.ci_lower, 4),
            "ci_upper": None if self.ci_upper is None else round(self.ci_upper, 4),
            "confidence_level": 0.90,
            "home_pre": self.home_pre.to_dict() if self.home_pre else None,
            "home_post": self.home_post.to_dict() if self.home_post else None,
            "control_pre": self.control_pre.to_dict() if self.control_pre else None,
            "control_post": self.control_post.to_dict() if self.control_post else None,
            "parallel_trends_warning": self.parallel_trends_warning,
            "parallel_trends_pvalue": (
                None
                if self.parallel_trends_pvalue is None
                else round(self.parallel_trends_pvalue, 4)
            ),
            "home_trend": self.home_trend,
            "control_trend": self.control_trend,
            "message": self.message,
        }


class ImpactEstimator:
    """Estimate the DiD effect of an Intervention from the mention panel."""

    def __init__(
        self,
        observations: tuple[MentionObservation, ...] | None = None,
        home_property_id: str = HOME_PROPERTY_ID,
    ) -> None:
        self._obs = observations if observations is not None else generate_observations()
        self._home = home_property_id
        self._today = max((o.date for o in self._obs), default=date.today())

    def _cell(self, labels: list[int]) -> CellStat:
        n = len(labels)
        k = sum(labels)
        p = k / n if n else 0.0
        mean = _score_from_share(p)
        # binomial-proportion variance of the mean, propagated to the [1,5] scale.
        var_p = (p * (1 - p) / n) if n else 0.0
        var_score = (4.0**2) * var_p
        return CellStat(n=n, positives=k, mean_score=mean, var_score=var_score)

    def _labels(
        self,
        *,
        home: bool,
        aspect: Aspect,
        start: date | None,
        end: date | None,
    ) -> list[int]:
        out: list[int] = []
        for o in self._obs:
            if o.aspect is not aspect:
                continue
            is_home = o.property_id == self._home
            if home and not is_home:
                continue
            if not home and is_home:
                continue
            if start is not None and o.date < start:
                continue
            if end is not None and o.date >= end:
                continue
            out.append(1 if o.label is SentimentLabel.POSITIVE else 0)
        return out

    def _weekly_scores(
        self, *, home: bool, aspect: Aspect, start: date | None, end: date | None
    ) -> list[tuple[date, float]]:
        by_week: dict[date, list[int]] = {}
        for o in self._obs:
            if o.aspect is not aspect:
                continue
            is_home = o.property_id == self._home
            if home and not is_home:
                continue
            if not home and is_home:
                continue
            if start is not None and o.date < start:
                continue
            if end is not None and o.date >= end:
                continue
            wk = _week_start(o.date)
            by_week.setdefault(wk, []).append(
                1 if o.label is SentimentLabel.POSITIVE else 0
            )
        return [
            (wk, _score_from_share(sum(v) / len(v)))
            for wk, v in sorted(by_week.items())
        ]

    def _slope(self, points: list[tuple[date, float]]) -> tuple[float, float, int]:
        """OLS slope + its standard error for weekly ``(date, score)`` points."""
        n = len(points)
        if n < 3:
            return 0.0, float("inf"), n
        xs = [(p[0] - points[0][0]).days / 7.0 for p in points]
        ys = [p[1] for p in points]
        xbar = sum(xs) / n
        ybar = sum(ys) / n
        sxx = sum((x - xbar) ** 2 for x in xs)
        if sxx <= 1e-9:
            return 0.0, float("inf"), n
        sxy = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys, strict=False))
        slope = sxy / sxx
        resid = [y - (ybar + slope * (x - xbar)) for x, y in zip(xs, ys, strict=False)]
        dof = n - 2
        sigma2 = sum(r**2 for r in resid) / dof if dof > 0 else 0.0
        se = math.sqrt(sigma2 / sxx) if sxx > 0 else float("inf")
        return slope, se, n

    def estimate(self, intervention: Intervention) -> ImpactResult:
        aspect = Aspect(intervention.aspect)
        idate = (
            intervention.date
            if isinstance(intervention.date, date)
            else date.fromisoformat(str(intervention.date))
        )
        post_days = (self._today - idate).days
        # pre-period: 90 days before the intervention; post-period: from the
        # intervention date to the latest observation.
        pre_start = idate - timedelta(days=90)

        home_pre = self._cell(
            self._labels(home=True, aspect=aspect, start=pre_start, end=idate)
        )
        home_post = self._cell(
            self._labels(home=True, aspect=aspect, start=idate, end=None)
        )
        control_pre = self._cell(
            self._labels(home=False, aspect=aspect, start=pre_start, end=idate)
        )
        control_post = self._cell(
            self._labels(home=False, aspect=aspect, start=idate, end=None)
        )

        home_trend = [
            {"week": wk.isoformat(), "score": round(s, 4)}
            for wk, s in self._weekly_scores(
                home=True, aspect=aspect, start=pre_start, end=None
            )
        ]
        control_trend = [
            {"week": wk.isoformat(), "score": round(s, 4)}
            for wk, s in self._weekly_scores(
                home=False, aspect=aspect, start=pre_start, end=None
            )
        ]

        # Parallel-trends check on the pre-period weekly scores.
        home_pre_pts = self._weekly_scores(
            home=True, aspect=aspect, start=pre_start, end=idate
        )
        control_pre_pts = self._weekly_scores(
            home=False, aspect=aspect, start=pre_start, end=idate
        )
        pt_warning, pt_p = self._parallel_trends(home_pre_pts, control_pre_pts)

        if post_days < MIN_POST_DAYS or home_post.n == 0 or control_post.n == 0:
            return ImpactResult(
                intervention_id=intervention.id,
                property_id=intervention.property_id,
                aspect=aspect.value,
                intervention_date=idate.isoformat(),
                sufficient_post_data=False,
                post_days=max(0, post_days),
                effect=None,
                ci_lower=None,
                ci_upper=None,
                home_pre=home_pre,
                home_post=home_post,
                control_pre=control_pre,
                control_post=control_post,
                parallel_trends_warning=pt_warning,
                parallel_trends_pvalue=pt_p,
                home_trend=home_trend,
                control_trend=control_trend,
                message=(
                    f"Need {MIN_POST_DAYS} days of post-intervention reviews; "
                    f"have {max(0, post_days)}."
                ),
            )

        effect = (home_post.mean_score - home_pre.mean_score) - (
            control_post.mean_score - control_pre.mean_score
        )
        se = math.sqrt(
            home_post.var_score
            + home_pre.var_score
            + control_post.var_score
            + control_pre.var_score
        )
        ci_lower = effect - Z_90 * se
        ci_upper = effect + Z_90 * se
        return ImpactResult(
            intervention_id=intervention.id,
            property_id=intervention.property_id,
            aspect=aspect.value,
            intervention_date=idate.isoformat(),
            sufficient_post_data=True,
            post_days=post_days,
            effect=effect,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            home_pre=home_pre,
            home_post=home_post,
            control_pre=control_pre,
            control_post=control_post,
            parallel_trends_warning=pt_warning,
            parallel_trends_pvalue=pt_p,
            home_trend=home_trend,
            control_trend=control_trend,
            message=None,
        )

    def _parallel_trends(
        self,
        home_pts: list[tuple[date, float]],
        control_pts: list[tuple[date, float]],
    ) -> tuple[bool, float | None]:
        """Warn when the pre-period slopes differ significantly (Req 24.4)."""
        hs, hse, hn = self._slope(home_pts)
        cs, cse, cn = self._slope(control_pts)
        if not math.isfinite(hse) or not math.isfinite(cse):
            return False, None
        se_diff = math.sqrt(hse**2 + cse**2)
        if se_diff <= 1e-9:
            return False, None
        z = abs(hs - cs) / se_diff
        # two-sided normal p-value
        p = 2.0 * (1.0 - _norm_cdf(z))
        return (p < PARALLEL_TRENDS_P), p


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
