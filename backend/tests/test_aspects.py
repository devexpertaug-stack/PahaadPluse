"""Tests for the cross-platform Aspect_Normalizer (Req 5)."""

from __future__ import annotations

from app.models.review import Aspect, Platform
from app.services.market_radar.aspects import (
    LATEST_MAPPING_VERSION,
    AspectNormalizer,
    SubRating,
)


def test_maps_categories_and_normalises_to_1_5() -> None:
    norm = AspectNormalizer("aspect-map-v1")
    result = norm.normalize(
        Platform.BOOKING,
        [SubRating("Staff", 10.0), SubRating("Location", 1.0)],
    )
    by_aspect = {ar.aspect: ar for ar in result.aspect_ratings}
    assert by_aspect[Aspect.STAFF.value].normalised_value == 5.0
    assert by_aspect[Aspect.LOCATION.value].normalised_value == 1.0
    for ar in result.aspect_ratings:
        assert 1.0 <= ar.normalised_value <= 5.0
        assert ar.mapping_version == "aspect-map-v1"


def test_collision_averaging() -> None:
    norm = AspectNormalizer("aspect-map-v1")
    # TripAdvisor 'rooms' and 'sleep quality' both map to ROOM.
    result = norm.normalize(
        Platform.TRIPADVISOR,
        [SubRating("Rooms", 5.0), SubRating("Sleep quality", 3.0)],
    )
    room = next(ar for ar in result.aspect_ratings if ar.aspect == Aspect.ROOM.value)
    assert room.normalised_value == 4.0  # average of 5 and 3


def test_bad_subrating_recorded_not_stored() -> None:
    norm = AspectNormalizer("aspect-map-v1")
    result = norm.normalize(
        Platform.GOOGLE,
        [SubRating("Food", "n/a"), SubRating("Rooms", 99.0), SubRating("Service", 4.0)],
    )
    aspects = {ar.aspect for ar in result.aspect_ratings}
    assert Aspect.SERVICE.value in aspects
    assert Aspect.FOOD.value not in aspects
    assert Aspect.ROOM.value not in aspects
    assert len(result.errors) == 2


def test_unmapped_categories_surface_over_threshold() -> None:
    norm = AspectNormalizer("aspect-map-v1")
    for _ in range(21):
        norm.normalize(Platform.GOOGLE, [SubRating("Parking", 4.0)])
    over = norm.unmapped_over_threshold(threshold=20)
    assert ("Google", "Parking", 21) in over


def test_new_version_renormalises_affected_platforms() -> None:
    v1 = AspectNormalizer("aspect-map-v1")
    v2 = AspectNormalizer("aspect-map-v2")
    # 'Housekeeping' is unmapped in v1 but mapped in v2 for Booking.com.
    r1 = v1.normalize(Platform.BOOKING, [SubRating("Housekeeping", 8.0)])
    r2 = v2.normalize(Platform.BOOKING, [SubRating("Housekeeping", 8.0)])
    assert r1.aspect_ratings == []
    assert any(ar.aspect == Aspect.HOUSEKEEPING.value for ar in r2.aspect_ratings)
    assert r2.aspect_ratings[0].mapping_version == LATEST_MAPPING_VERSION
