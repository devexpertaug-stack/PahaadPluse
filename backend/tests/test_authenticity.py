"""F9 Authenticity-adjusted benchmarks tests (Req 23)."""

from __future__ import annotations

from app.services.market_radar.authenticity import (
    SUSPICION_EXCLUDE_THRESHOLD,
    AuthenticityFilter,
)


def test_flags_burst_duplicate_and_single_author() -> None:
    af = AuthenticityFilter()
    flags = af.flags()
    assert any(f.burst for f in flags.values())
    assert any(f.near_duplicate for f in flags.values())
    assert any(f.single_review_author for f in flags.values())


def test_suspicion_in_unit_interval_and_labelled_signals() -> None:
    af = AuthenticityFilter()
    for f in af.flags().values():
        assert 0.0 <= f.suspicion <= 1.0
        assert f.to_dict()["label"] == "suspicious signals"


def test_adjusted_view_reranks_excluding_high_suspicion() -> None:
    av = AuthenticityFilter().adjusted_view()
    assert av["suspicion_exclude_threshold"] == SUSPICION_EXCLUDE_THRESHOLD
    assert av["excluded_count"] > 0
    # Every ranking row shows both original and adjusted rank side by side.
    for row in av["rankings"]:
        assert "original_rank" in row and "adjusted_rank" in row
        assert row["rank_delta"] == row["original_rank"] - row["adjusted_rank"]
    # The injected promotional campaign should move at least one property.
    assert any(row["rank_delta"] != 0 for row in av["rankings"])


def test_flagged_reviews_carry_source_url() -> None:
    av = AuthenticityFilter().adjusted_view()
    assert av["flagged_reviews"]
    for r in av["flagged_reviews"]:
        assert r["source_url"]
        assert r["label"] == "suspicious signals"


def test_campaign_boost_drops_after_adjustment() -> None:
    av = AuthenticityFilter().adjusted_view()
    by_id = {r["property_id"]: r for r in av["rankings"]}
    boosted = by_id["mus-forestseason"]
    # The boosted property's adjusted rank is worse than its (inflated) original.
    assert boosted["adjusted_rank"] >= boosted["original_rank"]
