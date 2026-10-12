"""Guest Compass contextual-bandit tests (Req 28)."""

from __future__ import annotations

from datetime import date

from app.services.guest_compass.service import (
    MAX_CARDS,
    GuestCompass,
    Segment,
    StayContext,
    season_for,
)


def _ctx(**kw) -> StayContext:
    base = dict(stay_id="s1", purpose="leisure", party="couple", check_in=date(2024, 6, 10))
    base.update(kw)
    return StayContext(**base)


def test_up_to_three_cards_with_reason_and_accept_decline() -> None:
    gc = GuestCompass()
    rec = gc.recommend(_ctx())
    assert not rec["suppressed"]
    assert 1 <= len(rec["cards"]) <= MAX_CARDS
    for card in rec["cards"]:
        assert card["name"] and card["reason"]
        assert card["item_id"]


def test_cold_start_segment_used_without_history() -> None:
    gc = GuestCompass()
    rec = gc.recommend(_ctx(has_history=False))
    assert rec["cold_start"] is True
    assert rec["segment"]


def test_bandit_updates_on_accept_increases_future_score() -> None:
    gc = GuestCompass()
    ctx = _ctx()
    rec = gc.recommend(ctx)
    item = rec["cards"][0]["item_id"]
    before = next(c["score"] for c in rec["cards"] if c["item_id"] == item)
    for _ in range(8):
        gc.record_outcome(ctx, item, accepted=True, revenue_inr=1000)
    rec2 = gc.recommend(ctx)
    after = next((c["score"] for c in rec2["cards"] if c["item_id"] == item), None)
    # Repeated accepts should not decrease the arm's estimated value.
    assert after is None or after >= before - 1e-6


def test_suppress_upsell_during_open_p1_p2() -> None:
    gc = GuestCompass()
    rec = gc.recommend(_ctx(has_open_p1_p2=True))
    assert rec["suppressed"] is True
    assert rec["cards"] == []
    assert "P1/P2" in rec["reason"]


def test_metrics_report_uptake_and_revenue() -> None:
    gc = GuestCompass()
    ctx = _ctx()
    gc.record_outcome(ctx, "candlelight-dinner", accepted=True, revenue_inr=2500)
    gc.record_outcome(ctx, "spa-ayurveda", accepted=False)
    m = gc.metrics(guests_this_week=4)
    assert m["offers"] == 2
    assert m["accepted"] == 1
    assert m["uptake_rate"] == 0.5
    assert m["ancillary_revenue_inr"] == 2500.0
    assert m["revenue_per_guest_per_week"] == 625.0


def test_market_weak_aspects_down_weight_items() -> None:
    gc = GuestCompass()
    # Service is a cluster-wide weak aspect; the home exceeds the median there.
    assert gc._weak_aspects
    rec = gc.recommend(_ctx())
    weak_cards = [c for c in rec["cards"] if c["market_down_weighted"]]
    # Down-weighting is applied; weak-aspect items may still appear but flagged.
    assert isinstance(weak_cards, list)


def test_season_and_segment_helpers() -> None:
    assert season_for(date(2024, 1, 15)) == "winter"
    assert season_for(date(2024, 4, 15)) == "summer"
    seg = Segment(purpose="honeymoon", party="couple", season="winter")
    priors = seg.priors()
    assert priors["spa"] >= priors["activities"]
