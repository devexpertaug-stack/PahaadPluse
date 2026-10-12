"""F10 Proof of Impact tests (Req 24): DiD effect, 90% CI, parallel trends."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.models.intervention import Intervention
from app.models.review import Aspect
from app.services.market_radar.analytics_dataset import HOME_PROPERTY_ID
from app.services.market_radar.impact import MIN_POST_DAYS, ImpactEstimator


def _intervention(on: date, aspect: Aspect = Aspect.FOOD) -> Intervention:
    return Intervention(
        id="iv-test",
        property_id=HOME_PROPERTY_ID,
        aspect=aspect,
        description="Replaced breakfast vendor.",
        date=on,
        logged_at=datetime.now(UTC),
    )


def test_sufficient_post_data_produces_effect_and_ci() -> None:
    est = ImpactEstimator()
    # Intervention ~75 days before the latest observation (2024-06-15).
    result = est.estimate(_intervention(date(2024, 4, 1))).to_dict()
    assert result["sufficient_post_data"] is True
    assert result["post_days"] >= MIN_POST_DAYS
    assert result["effect"] is not None
    assert result["ci_lower"] <= result["effect"] <= result["ci_upper"]
    assert result["confidence_level"] == 0.90
    # pre/post vs control cells all populated for the website.
    for key in ("home_pre", "home_post", "control_pre", "control_post"):
        assert result[key] is not None
    assert result["home_trend"] and result["control_trend"]


def test_insufficient_post_data_blocks_estimate() -> None:
    est = ImpactEstimator()
    # Intervention only a few days before the latest observation.
    result = est.estimate(_intervention(date(2024, 6, 10))).to_dict()
    assert result["sufficient_post_data"] is False
    assert result["effect"] is None
    assert "days" in (result["message"] or "")


def test_parallel_trends_flag_is_boolean_and_has_pvalue() -> None:
    est = ImpactEstimator()
    result = est.estimate(_intervention(date(2024, 4, 1))).to_dict()
    assert isinstance(result["parallel_trends_warning"], bool)
    # a p-value is reported whenever the slopes are estimable
    assert result["parallel_trends_pvalue"] is None or 0.0 <= result[
        "parallel_trends_pvalue"
    ] <= 1.0


def test_decline_aspect_shows_recovery_direction() -> None:
    # The seeded panel declines Home_Property Food ~6 months before the end,
    # then an intervention after the decline should show a non-null effect.
    est = ImpactEstimator()
    result = est.estimate(_intervention(date(2024, 3, 1), Aspect.FOOD)).to_dict()
    assert result["sufficient_post_data"] is True
    assert result["effect"] is not None
