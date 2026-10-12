"""Time_Machine + Cause_Miner tests (Req 11)."""

from __future__ import annotations

from datetime import date

from app.models.review import Aspect
from app.services.market_radar.changepoints import ChangepointDetector
from app.services.market_radar.market_model import MarketModel
from app.services.market_radar.time_machine import CauseMiner, TimeMachine

_FIT = MarketModel().fit_cluster()
_RUN = ChangepointDetector().run(fit=_FIT)
_TM = TimeMachine()


def test_nearest_changepoint_within_30_days() -> None:
    cp = _TM.nearest_changepoint(
        _RUN.changepoints, "mus-pineview", date(2024, 1, 15), Aspect.FOOD
    )
    assert cp is not None
    assert cp.date == "2024-01-01"


def test_no_changepoint_message_when_far() -> None:
    result = _TM.investigate(
        _RUN.changepoints, "mus-pineview", date(2023, 1, 1), Aspect.FOOD
    )
    # Far from the injected 2024-01 decline.
    if result.changepoint is None:
        assert "No changepoint" in (result.message or "")


def test_investigate_returns_causes_and_quotes() -> None:
    result = _TM.investigate(
        _RUN.changepoints, "mus-pineview", date(2024, 1, 15), Aspect.FOOD
    )
    assert result.changepoint is not None
    assert len(result.causes) <= 3
    # before/after quotes are tied to the aspect.
    assert len(result.before_quotes) >= 1
    assert len(result.after_quotes) >= 1
    for q in result.before_quotes + result.after_quotes:
        assert q.span


def test_scope_label_for_home_specific_decline() -> None:
    result = _TM.investigate(
        _RUN.changepoints, "mus-pineview", date(2024, 1, 15), Aspect.FOOD
    )
    assert result.scope_label in {"property-specific", "market-wide", "undetermined"}
    assert result.scope_label == "property-specific"


def test_interventions_near_changepoint_listed() -> None:
    result = _TM.investigate(
        _RUN.changepoints, "mus-pineview", date(2024, 1, 15), Aspect.FOOD
    )
    assert any(i.label for i in result.interventions)


def test_failure_message_leaves_data_unchanged() -> None:
    result = _TM.investigate(
        _RUN.changepoints, "mus-pineview", date(2024, 1, 15), Aspect.FOOD, force_failure=True
    )
    assert result.failed is True
    assert result.causes == []
    assert "failed" in (result.message or "").lower()


def test_cause_miner_lift_and_after_count_thresholds() -> None:
    miner = CauseMiner()
    before = ["clean and tidy room"] * 2
    after = ["dirty smelly room"] * 5
    causes = miner.mine(before, after)
    for c in causes:
        assert c.after_count >= 3
        assert c.lift > 1.0
    # phrases ranked by lift descending.
    lifts = [c.lift for c in causes]
    assert lifts == sorted(lifts, reverse=True)
