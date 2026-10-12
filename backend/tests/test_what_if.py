"""What_If_Simulator tests incl. Req 10.5/10.6/10.7 (property/metamorphic)."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.review import Aspect, Platform
from app.services.market_radar.what_if import (
    SCORE_MAX,
    SCORE_MIN,
    WhatIfSimulator,
)

_SIM = WhatIfSimulator()
_MODEL = _SIM.platform_model(Platform.GOOGLE)


def test_driver_weights_ranked_by_abs_value() -> None:
    """Req 10.7: driver weights ranked by |value| descending."""
    model_dict = _MODEL.to_dict()
    weights = model_dict["driver_weights"]
    abs_values = [w["abs_weight"] for w in weights]
    assert abs_values == sorted(abs_values, reverse=True)
    for w in weights:
        assert w["lower"] <= w["weight"] <= w["upper"]


def test_identity_all_zero_returns_current(deltas=None) -> None:
    """Req 10.5: all-zero deltas return within 0.01 of current + current rank."""
    projection = _SIM.project(_MODEL, {})
    assert abs(projection["projected_rating"] - projection["current_rating"]) <= 0.01
    assert projection["projected_rank"] == _SIM.current_rank(_MODEL)


def test_projection_bounded_to_1_5() -> None:
    # Push every slider to its extremes; projection must stay in [1, 5].
    big_up = {a: 1.0 for a in Aspect}
    big_down = {a: -1.0 for a in Aspect}
    for deltas in (big_up, big_down):
        p = _SIM.project(_MODEL, deltas)
        assert SCORE_MIN <= p["projected_rating"] <= SCORE_MAX
        assert SCORE_MIN <= p["projected_lower"] <= SCORE_MAX
        assert SCORE_MIN <= p["projected_upper"] <= SCORE_MAX


def test_rank_in_range() -> None:
    p = _SIM.project(_MODEL, {Aspect.FOOD: 0.5})
    assert 1 <= p["projected_rank"] <= p["cluster_size"]


@settings(max_examples=40, deadline=None)
@given(aspect=st.sampled_from(list(Aspect)))
def test_metamorphic_step_follows_weight_sign(aspect: Aspect) -> None:
    """Req 10.6: a +step moves the projection in the sign of the weight.

    Unless the aspect is unavailable, its weight is 0, or the home score is at a
    bound (delta would be capped away).
    """
    model = _SIM.platform_model(Platform.GOOGLE)
    weight_by_aspect = {d.aspect: d for d in model.driver_weights}
    dw = weight_by_aspect[aspect]
    if not dw.available or abs(dw.weight) < 1e-9:
        return
    home_score = model._aspect_scores.get(model.home_property_id, {}).get(aspect.value, 3.0)
    if home_score >= SCORE_MAX - 1e-9:
        return  # already at the upper bound; +step is capped to 0
    base = _SIM.project(model, {})["projected_rating"]
    stepped = _SIM.project(model, {aspect: 0.1})["projected_rating"]
    if dw.weight > 0:
        assert stepped >= base - 1e-9
    else:
        assert stepped <= base + 1e-9
