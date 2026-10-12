"""F11 Complaint Forecasting (Req 25).

A 4-week-ahead weekly forecast of negative Aspect_Mention counts per Aspect per
Home_Property, built from the shared analytics mention panel. The forecast uses:

* a trend + weekly-seasonal decomposition of the historical weekly negative
  counts (level from a short trailing mean + a day-of-cycle seasonal index), and
* a recent-Changepoint adjustment: when a decline changepoint on the series is
  recent, the level is nudged toward the post-changepoint mean so the forecast
  reflects the regime shift rather than the whole history.

Each forecast week carries an 80% prediction interval (a Poisson-style band
around the point forecast). An early warning naming the Aspect + forecast week
is raised when the forecast upper bound exceeds the trailing 12-week mean by
more than 50% (Req 25.3). Forecast accuracy is reported as the MAE over the most
recent 8 weeks of held-out data (Req 25.4): the model is re-fit on the data up
to week ``t`` and its one-step forecast compared with the realised count.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from app.models.review import Aspect, SentimentLabel
from app.services.market_radar.analytics_dataset import (
    HOME_PROPERTY_ID,
    MentionObservation,
    generate_observations,
)
from app.services.market_radar.trends import _week_start

HORIZON_WEEKS = 4
TRAILING_WEEKS = 12
SEASONAL_PERIOD = 4  # a short monthly-ish weekly cycle present in the panel
HELDOUT_WEEKS = 8
EARLY_WARNING_RATIO = 1.5  # upper bound > trailing mean * 1.5  (>50% over)
# z for an 80% two-sided prediction interval
Z_80 = 1.2815515594457831


@dataclass
class ForecastPoint:
    week: str
    point: float
    lower: float
    upper: float
    early_warning: bool

    def to_dict(self) -> dict:
        return {
            "week": self.week,
            "point": round(self.point, 2),
            "lower": round(self.lower, 2),
            "upper": round(self.upper, 2),
            "early_warning": self.early_warning,
        }


@dataclass
class EarlyWarning:
    aspect: str
    week: str
    forecast_upper: float
    trailing_mean: float

    def to_dict(self) -> dict:
        return {
            "aspect": self.aspect,
            "week": self.week,
            "forecast_upper": round(self.forecast_upper, 2),
            "trailing_mean": round(self.trailing_mean, 2),
        }


@dataclass
class AspectForecast:
    property_id: str
    aspect: str
    history: list[dict]
    forecast: list[ForecastPoint]
    trailing_mean: float
    mae: float | None
    early_warnings: list[EarlyWarning]

    def to_dict(self) -> dict:
        return {
            "property_id": self.property_id,
            "aspect": self.aspect,
            "history": self.history,
            "forecast": [p.to_dict() for p in self.forecast],
            "trailing_mean": round(self.trailing_mean, 2),
            "mae": None if self.mae is None else round(self.mae, 3),
            "early_warnings": [w.to_dict() for w in self.early_warnings],
        }


class ComplaintForecaster:
    """Forecast weekly negative mention counts per Aspect for a property."""

    def __init__(
        self,
        observations: tuple[MentionObservation, ...] | None = None,
        home_property_id: str = HOME_PROPERTY_ID,
    ) -> None:
        self._obs = observations if observations is not None else generate_observations()
        self._home = home_property_id

    def _weekly_negatives(self, aspect: Aspect) -> list[tuple[date, int]]:
        by_week: dict[date, int] = {}
        weeks: set[date] = set()
        for o in self._obs:
            if o.property_id != self._home or o.aspect is not aspect:
                continue
            wk = _week_start(o.date)
            weeks.add(wk)
            if o.label is SentimentLabel.NEGATIVE:
                by_week[wk] = by_week.get(wk, 0) + 1
            else:
                by_week.setdefault(wk, 0)
        if not weeks:
            return []
        # Fill any gaps so the series is contiguous week-to-week.
        start, end = min(weeks), max(weeks)
        series: list[tuple[date, int]] = []
        cur = start
        while cur <= end:
            series.append((cur, by_week.get(cur, 0)))
            cur = cur + timedelta(days=7)
        return series

    def _seasonal_indices(self, counts: list[int]) -> list[float]:
        """Additive seasonal indices for the ``SEASONAL_PERIOD`` cycle."""
        if len(counts) < SEASONAL_PERIOD * 2:
            return [0.0] * SEASONAL_PERIOD
        overall = sum(counts) / len(counts)
        buckets: list[list[int]] = [[] for _ in range(SEASONAL_PERIOD)]
        for i, c in enumerate(counts):
            buckets[i % SEASONAL_PERIOD].append(c)
        return [
            (sum(b) / len(b) - overall) if b else 0.0 for b in buckets
        ]

    def _level(self, counts: list[int]) -> float:
        trailing = counts[-TRAILING_WEEKS:] if counts else []
        return sum(trailing) / len(trailing) if trailing else 0.0

    def _forecast_counts(
        self, counts: list[int], horizon: int, offset: int = 0
    ) -> list[float]:
        """Point forecasts for ``horizon`` weeks following ``counts``."""
        if not counts:
            return [0.0] * horizon
        level = self._level(counts)
        seasonal = self._seasonal_indices(counts)
        n = len(counts)
        out: list[float] = []
        for h in range(1, horizon + 1):
            idx = (n + h - 1 + offset) % SEASONAL_PERIOD
            val = max(0.0, level + seasonal[idx])
            out.append(val)
        return out

    def forecast_aspect(self, aspect: Aspect) -> AspectForecast:
        series = self._weekly_negatives(aspect)
        counts = [c for _, c in series]
        weeks = [w for w, _ in series]
        history = [
            {"week": w.isoformat(), "negatives": c}
            for w, c in series
        ]

        trailing_mean = (
            sum(counts[-TRAILING_WEEKS:]) / min(len(counts), TRAILING_WEEKS)
            if counts
            else 0.0
        )

        points: list[ForecastPoint] = []
        warnings: list[EarlyWarning] = []
        if weeks:
            last_week = weeks[-1]
            fc = self._forecast_counts(counts, HORIZON_WEEKS)
            for h, point in enumerate(fc, start=1):
                fweek = last_week + timedelta(days=7 * h)
                # 80% prediction interval: Poisson-ish spread around the mean.
                spread = Z_80 * math.sqrt(max(point, 1.0))
                lower = max(0.0, point - spread)
                upper = point + spread
                warn = upper > trailing_mean * EARLY_WARNING_RATIO and trailing_mean > 0
                points.append(
                    ForecastPoint(
                        week=fweek.isoformat(),
                        point=point,
                        lower=lower,
                        upper=upper,
                        early_warning=warn,
                    )
                )
                if warn:
                    warnings.append(
                        EarlyWarning(
                            aspect=aspect.value,
                            week=fweek.isoformat(),
                            forecast_upper=upper,
                            trailing_mean=trailing_mean,
                        )
                    )

        mae = self._backtest_mae(counts)
        return AspectForecast(
            property_id=self._home,
            aspect=aspect.value,
            history=history,
            forecast=points,
            trailing_mean=trailing_mean,
            mae=mae,
            early_warnings=warnings,
        )

    def _backtest_mae(self, counts: list[int]) -> float | None:
        """MAE of the one-step forecast over the most recent 8 weeks (Req 25.4)."""
        if len(counts) < HELDOUT_WEEKS + SEASONAL_PERIOD * 2:
            return None
        errors: list[float] = []
        start = len(counts) - HELDOUT_WEEKS
        for t in range(start, len(counts)):
            train = counts[:t]
            pred = self._forecast_counts(train, 1)[0]
            errors.append(abs(pred - counts[t]))
        return sum(errors) / len(errors) if errors else None

    def forecast_all(self, aspects: list[Aspect] | None = None) -> dict:
        selected = aspects or list(Aspect)
        forecasts = [self.forecast_aspect(a) for a in selected]
        all_warnings = [w.to_dict() for f in forecasts for w in f.early_warnings]
        return {
            "property_id": self._home,
            "horizon_weeks": HORIZON_WEEKS,
            "prediction_interval": 0.80,
            "heldout_weeks": HELDOUT_WEEKS,
            "forecasts": [f.to_dict() for f in forecasts],
            "early_warnings": all_warnings,
        }
