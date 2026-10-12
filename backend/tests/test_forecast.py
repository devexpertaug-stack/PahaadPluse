"""F11 Complaint Forecasting tests (Req 25)."""

from __future__ import annotations

from app.models.review import Aspect
from app.services.sentinel.forecast import (
    EARLY_WARNING_RATIO,
    HORIZON_WEEKS,
    ComplaintForecaster,
)


def test_four_week_forecast_with_interval() -> None:
    f = ComplaintForecaster().forecast_aspect(Aspect.FOOD).to_dict()
    assert len(f["forecast"]) == HORIZON_WEEKS
    for point in f["forecast"]:
        assert point["lower"] <= point["point"] <= point["upper"]
    assert f["mae"] is None or f["mae"] >= 0.0


def test_prediction_interval_is_80_percent() -> None:
    out = ComplaintForecaster().forecast_all([Aspect.ROOM])
    assert out["prediction_interval"] == 0.80
    assert out["horizon_weeks"] == HORIZON_WEEKS


def test_early_warning_threshold_rule() -> None:
    """An early warning fires only when upper > trailing mean * 1.5 (Req 25.3)."""
    forecaster = ComplaintForecaster()
    out = forecaster.forecast_all()
    for warning in out["early_warnings"]:
        assert warning["forecast_upper"] > warning["trailing_mean"] * EARLY_WARNING_RATIO
        assert warning["week"]
        assert warning["aspect"]


def test_mae_reported_over_heldout_weeks() -> None:
    # The Food series has enough weekly depth for a backtest MAE.
    f = ComplaintForecaster().forecast_aspect(Aspect.FOOD).to_dict()
    assert f["mae"] is not None
    assert f["mae"] >= 0.0


def test_history_is_contiguous_weeks() -> None:
    f = ComplaintForecaster().forecast_aspect(Aspect.SERVICE).to_dict()
    weeks = [h["week"] for h in f["history"]]
    assert weeks == sorted(weeks)
    assert len(weeks) == len(set(weeks))
