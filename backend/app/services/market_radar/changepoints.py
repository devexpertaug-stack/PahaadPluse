"""Bayesian Online Changepoint Detection + notifications (Req 9).

Runs a BOCPD pass (Adams & MacKay, 2007) over two series per property:

* the property-specific Aspect score series at monthly granularity (derived
  from the Market_Model decomposition's modelled scores), and
* the raw negative-share series at weekly granularity.

A :class:`Changepoint` is recorded when the posterior probability of a change
at a point exceeds 0.5 (Req 9.1). Direction follows Req 9.2: a *decline* when
the mean after the point is materially lower (score down / negative-share up),
an *improvement* when higher, else *no_change*. Changepoints for the same
(property, aspect, series, direction) within 14 days are merged, keeping the
higher posterior (Req 9.3). A decline on a Home_Property aspect raises a
dashboard notification carrying a Time_Machine deep link (Req 9.4) and the
time-to-identification metric is recorded (Req 9.5). The unreliable flag from
the Market_Model is propagated (Req 9.6); a run failure keeps prior
changepoints and records the failure + last successful run time (Req 9.7);
series shorter than 6 monthly / 8 weekly points are skipped with an
insufficient-history label (Req 9.8).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.models.review import Aspect
from app.services.market_radar.analytics_dataset import (
    HOME_PROPERTY_ID,
    MentionObservation,
    generate_observations,
)
from app.services.market_radar.market_model import ClusterFit, MarketModel
from app.services.market_radar.trends import _week_start

POSTERIOR_THRESHOLD = 0.5
MERGE_WINDOW_DAYS = 14
MIN_MONTHLY_POINTS = 6
MIN_WEEKLY_POINTS = 8
DIRECTION_EPS = 0.15  # minimum mean shift to call a direction


@dataclass
class Changepoint:
    """A detected changepoint on a property/aspect/series."""

    property_id: str
    aspect: Aspect | None
    series: str  # "aspect_score_monthly" | "negative_share_weekly"
    date: str  # ISO date of the changepoint period
    direction: str  # "decline" | "improvement"
    posterior: float
    unreliable: bool = False
    time_to_identification_days: int | None = None

    def to_dict(self) -> dict:
        return {
            "property_id": self.property_id,
            "aspect": self.aspect.value if self.aspect else None,
            "series": self.series,
            "date": self.date,
            "direction": self.direction,
            "posterior": round(self.posterior, 4),
            "unreliable": self.unreliable,
            "time_to_identification_days": self.time_to_identification_days,
        }


@dataclass
class Notification:
    """A manager dashboard notification for a decline changepoint (Req 9.4)."""

    property_id: str
    aspect: str | None
    series: str
    date: str
    message: str
    time_machine_link: str

    def to_dict(self) -> dict:
        return {
            "property_id": self.property_id,
            "aspect": self.aspect,
            "series": self.series,
            "date": self.date,
            "message": self.message,
            "time_machine_link": self.time_machine_link,
        }


@dataclass
class ChangepointRun:
    """Outcome of a changepoint-detection run."""

    changepoints: list[Changepoint]
    notifications: list[Notification]
    skipped: list[dict]  # insufficient-history labels (Req 9.8)
    ran_at: datetime
    failure: bool = False
    last_successful_run: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "ran_at": self.ran_at.isoformat(),
            "failure": self.failure,
            "last_successful_run": self.last_successful_run.isoformat()
            if self.last_successful_run
            else None,
            "changepoints": [c.to_dict() for c in self.changepoints],
            "notifications": [n.to_dict() for n in self.notifications],
            "skipped": self.skipped,
        }


def bocpd_posteriors(series: list[float], hazard: float = 0.25) -> list[float]:
    """Return the per-point changepoint posterior P(run length resets).

    A compact BOCPD (Adams & MacKay) with a Gaussian observation model and a
    constant hazard. The returned list is aligned to ``series``; index ``t`` is
    the posterior mass on run length 0 after observing point ``t`` — i.e. the
    probability that a changepoint occurred *at* ``t``. Index 0 is always 0.

    ``rl[r]`` holds the (unnormalised then normalised) probability of run length
    ``r`` and ``mean_run[r]`` / ``count_run[r]`` the running mean/count of the
    observations assigned to that hypothesis. A grounded prior mean (the global
    series mean) keeps a fresh run (r == 0) from perfectly explaining every
    point, so a genuine level shift produces a posterior spike.
    """
    n = len(series)
    if n < 2:
        return [0.0] * n
    # Estimate the observation noise from successive first differences (robust
    # to a level shift, unlike the raw series variance which the shift inflates).
    diffs = [series[i] - series[i - 1] for i in range(1, n)]
    diff_var = _variance(diffs) / 2.0 if len(diffs) >= 2 else _variance(series)
    var = max(1e-3, diff_var)
    prior_mean = sum(series) / n
    posteriors = [0.0]
    # Initialise with the first observation as run length 1.
    rl = [1.0]
    mean_run = [series[0]]
    count_run = [1]
    for t in range(1, n):
        x = series[t]
        size = len(rl)
        # Predictive probability of x under each surviving run length, plus the
        # changepoint hypothesis (a fresh run predicts from the prior mean).
        growth = [0.0] * (size + 1)
        cp_mass = 0.0
        for r in range(size):
            pred = _gauss_pdf(x, mean_run[r], var)
            growth[r + 1] = rl[r] * pred * (1.0 - hazard)
            cp_mass += rl[r] * _gauss_pdf(x, prior_mean, var) * hazard
        new_rl = [cp_mass] + growth[1:]
        total = sum(new_rl)
        if total <= 0:
            new_rl = [1.0] + [0.0] * size
            total = 1.0
        new_rl = [v / total for v in new_rl]
        posteriors.append(new_rl[0])
        # Update sufficient statistics: run length 0 starts fresh at x.
        new_mean = [x]
        new_count = [1]
        for r in range(size):
            c = count_run[r] + 1
            m = mean_run[r] + (x - mean_run[r]) / c
            new_mean.append(m)
            new_count.append(c)
        rl = new_rl
        mean_run = new_mean
        count_run = new_count
    return posteriors


def _variance(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def _gauss_pdf(x: float, mu: float, var: float) -> float:
    return math.exp(-((x - mu) ** 2) / (2.0 * var)) / math.sqrt(2.0 * math.pi * var)


class ChangepointDetector:
    """Detect changepoints over the analytics panel + Market_Model fit."""

    def __init__(
        self,
        observations: tuple[MentionObservation, ...] | None = None,
        home_property_id: str = HOME_PROPERTY_ID,
    ) -> None:
        self._obs = observations if observations is not None else generate_observations()
        self._home = home_property_id

    def run(
        self,
        fit: ClusterFit | None = None,
        aspects: list[Aspect] | None = None,
        now: datetime | None = None,
        force_failure: bool = False,
        previous: ChangepointRun | None = None,
    ) -> ChangepointRun:
        now = now or datetime.now(UTC)
        if force_failure:
            prior_cps = previous.changepoints if previous else []
            prior_notifs = previous.notifications if previous else []
            last_ok = previous.ran_at if previous else None
            return ChangepointRun(
                changepoints=prior_cps,
                notifications=prior_notifs,
                skipped=[],
                ran_at=now,
                failure=True,
                last_successful_run=last_ok,
            )

        if fit is None:
            fit = MarketModel(self._obs).fit_cluster(aspects=aspects)
        selected_aspects = aspects or list(Aspect)
        property_ids = sorted({o.property_id for o in self._obs})

        changepoints: list[Changepoint] = []
        skipped: list[dict] = []

        # ---- Monthly property-specific Aspect score series ----
        for prop in property_ids:
            for aspect in selected_aspects:
                months, scores, unreliables = self._aspect_score_series(fit, prop, aspect)
                if len(scores) < MIN_MONTHLY_POINTS:
                    skipped.append(
                        {
                            "property_id": prop,
                            "aspect": aspect.value,
                            "series": "aspect_score_monthly",
                            "label": "insufficient history",
                            "points": len(scores),
                        }
                    )
                    continue
                post = bocpd_posteriors(scores)
                changepoints.extend(
                    self._emit(
                        prop,
                        aspect,
                        "aspect_score_monthly",
                        months,
                        scores,
                        post,
                        unreliables,
                        improvement_is_up=True,
                        now=now,
                    )
                )

        # ---- Weekly raw negative-share series (per property, all aspects) ----
        for prop in property_ids:
            weeks, shares = self._negative_share_series(prop)
            if len(shares) < MIN_WEEKLY_POINTS:
                skipped.append(
                    {
                        "property_id": prop,
                        "aspect": None,
                        "series": "negative_share_weekly",
                        "label": "insufficient history",
                        "points": len(shares),
                    }
                )
                continue
            post = bocpd_posteriors(shares)
            changepoints.extend(
                self._emit(
                    prop,
                    None,
                    "negative_share_weekly",
                    weeks,
                    shares,
                    post,
                    [False] * len(shares),
                    improvement_is_up=False,  # rising negative share = decline
                    now=now,
                )
            )

        changepoints = self._merge(changepoints)
        notifications = self._notify(changepoints)
        return ChangepointRun(
            changepoints=changepoints,
            notifications=notifications,
            skipped=skipped,
            ran_at=now,
        )

    def _aspect_score_series(
        self, fit: ClusterFit, prop: str, aspect: Aspect
    ) -> tuple[list[date], list[float], list[bool]]:
        cells = [c for c in fit.cells if c.property_id == prop and c.aspect == aspect]
        cells.sort(key=lambda c: c.month)
        months = [date.fromisoformat(c.month) for c in cells]
        scores = [c.modelled_score for c in cells]
        unreliables = [c.unreliable for c in cells]
        return months, scores, unreliables

    def _negative_share_series(self, prop: str) -> tuple[list[date], list[float]]:
        by_week: dict[date, list[int]] = {}
        for o in self._obs:
            if o.property_id != prop:
                continue
            wk = _week_start(o.date)
            by_week.setdefault(wk, []).append(1 if o.label.value == "negative" else 0)
        weeks = sorted(by_week)
        shares = [sum(by_week[w]) / len(by_week[w]) for w in weeks]
        return weeks, shares

    def _emit(
        self,
        prop: str,
        aspect: Aspect | None,
        series: str,
        periods: list[date],
        values: list[float],
        posteriors: list[float],
        unreliables: list[bool],
        improvement_is_up: bool,
        now: datetime,
    ) -> list[Changepoint]:
        out: list[Changepoint] = []
        for t in range(1, len(values)):
            if posteriors[t] <= POSTERIOR_THRESHOLD:
                continue
            before = sum(values[:t]) / t
            after = sum(values[t:]) / (len(values) - t)
            delta = after - before
            if abs(delta) < DIRECTION_EPS:
                continue
            rising = delta > 0
            improvement = rising if improvement_is_up else not rising
            direction = "improvement" if improvement else "decline"
            cp_date = periods[t]
            unreliable = unreliables[t] if t < len(unreliables) else False
            ttid = (now.date() - cp_date).days
            out.append(
                Changepoint(
                    property_id=prop,
                    aspect=aspect,
                    series=series,
                    date=cp_date.isoformat(),
                    direction=direction,
                    posterior=posteriors[t],
                    unreliable=unreliable,
                    time_to_identification_days=max(0, ttid),
                )
            )
        return out

    def _merge(self, changepoints: list[Changepoint]) -> list[Changepoint]:
        """Merge same (property, aspect, series, direction) within 14 days."""
        changepoints.sort(
            key=lambda c: (c.property_id, str(c.aspect), c.series, c.direction, c.date)
        )
        merged: list[Changepoint] = []
        for cp in changepoints:
            placed = False
            for existing in merged:
                if (
                    existing.property_id == cp.property_id
                    and existing.aspect == cp.aspect
                    and existing.series == cp.series
                    and existing.direction == cp.direction
                    and abs(
                        (date.fromisoformat(existing.date) - date.fromisoformat(cp.date)).days
                    )
                    <= MERGE_WINDOW_DAYS
                ):
                    if cp.posterior > existing.posterior:
                        existing.posterior = cp.posterior
                        existing.date = cp.date
                        existing.time_to_identification_days = cp.time_to_identification_days
                    placed = True
                    break
            if not placed:
                merged.append(cp)
        merged.sort(key=lambda c: c.date)
        return merged

    def _notify(self, changepoints: list[Changepoint]) -> list[Notification]:
        notifs: list[Notification] = []
        for cp in changepoints:
            if cp.direction != "decline" or cp.property_id != self._home:
                continue
            aspect_q = f"&aspect={cp.aspect.value}" if cp.aspect else ""
            link = (
                f"/time-machine?property={cp.property_id}&date={cp.date}{aspect_q}"
            )
            label = cp.aspect.value if cp.aspect else "negative share"
            notifs.append(
                Notification(
                    property_id=cp.property_id,
                    aspect=cp.aspect.value if cp.aspect else None,
                    series=cp.series,
                    date=cp.date,
                    message=(
                        f"Decline detected for {label} at {cp.property_id} on "
                        f"{cp.date} (posterior {cp.posterior:.2f}). Investigate in "
                        "the Time Machine."
                    ),
                    time_machine_link=link,
                )
            )
        return notifs
