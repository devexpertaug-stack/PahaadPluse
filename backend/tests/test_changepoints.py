"""Changepoint_Detector tests (Req 9)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.review import Aspect
from app.services.market_radar.changepoints import (
    POSTERIOR_THRESHOLD,
    ChangepointDetector,
    bocpd_posteriors,
)
from app.services.market_radar.market_model import MarketModel

_MODEL = MarketModel()
_FIT = _MODEL.fit_cluster()
_DETECTOR = ChangepointDetector()
_RUN = _DETECTOR.run(fit=_FIT)


def test_detects_injected_home_food_decline() -> None:
    """The synthetic dataset injects a Food decline on the Home_Property."""
    hits = [
        c
        for c in _RUN.changepoints
        if c.property_id == "mus-pineview"
        and c.aspect == Aspect.FOOD
        and c.direction == "decline"
    ]
    assert hits, "expected the injected Home Food decline to be detected"
    assert all(c.posterior > POSTERIOR_THRESHOLD for c in hits)


def test_decline_notification_has_time_machine_link() -> None:
    notifs = [n for n in _RUN.notifications if n.aspect == "Food"]
    assert notifs
    assert notifs[0].time_machine_link.startswith("/time-machine?property=mus-pineview")


def test_posteriors_bounded_and_spike_on_shift() -> None:
    series = [4.0, 4.1, 3.9, 4.0, 4.1, 1.5, 1.4, 1.6, 1.5]
    post = bocpd_posteriors(series)
    assert all(0.0 <= p <= 1.0 for p in post)
    # The sharp drop at index 5 should produce the largest posterior.
    assert post.index(max(post)) == 5
    assert max(post) > POSTERIOR_THRESHOLD


def test_merge_keeps_higher_posterior() -> None:
    # All detected changepoints are unique per (prop, aspect, series, direction)
    # within the 14-day window after merging.
    seen = set()
    for c in _RUN.changepoints:
        key = (c.property_id, c.aspect, c.series, c.direction, c.date)
        assert key not in seen
        seen.add(key)


def test_time_to_identification_non_negative() -> None:
    for c in _RUN.changepoints:
        assert c.time_to_identification_days is None or c.time_to_identification_days >= 0


def test_insufficient_history_skips_short_series() -> None:
    # Only the first two months of observations -> monthly series too short.
    obs = tuple(o for o in _MODEL._obs if o.date.year == 2023 and o.date.month <= 2)
    model = MarketModel(obs)
    detector = ChangepointDetector(obs)
    run = detector.run(fit=model.fit_cluster())
    assert any(s["label"] == "insufficient history" for s in run.skipped)


def test_run_failure_keeps_prior() -> None:
    prev = _RUN
    failed = _DETECTOR.run(force_failure=True, previous=prev)
    assert failed.failure is True
    assert failed.changepoints == prev.changepoints
    assert failed.last_successful_run == prev.ran_at


def test_run_at_timestamp_set() -> None:
    run = _DETECTOR.run(fit=_FIT, now=datetime(2024, 6, 15, tzinfo=UTC))
    assert run.ran_at == datetime(2024, 6, 15, tzinfo=UTC)
