"""Cross-platform Aspect_Normalizer (Req 5).

Maps platform-specific sub-rating categories onto the nine canonical
:class:`~app.models.review.Aspect` values via a *versioned* mapping table, and
normalises each sub-rating onto ``[1.0, 5.0]`` using the same per-platform
linear mapping as :func:`app.services.market_radar.parsing.normalise_rating`.

Behaviour:

* Unmapped categories are stored against no Aspect and counted; those seen more
  than 20 times are surfaced to admins (Req 5.6, 5.7).
* Non-numeric / out-of-scale sub-ratings store nothing, record an error and
  continue (Req 5.4).
* When several categories map to the same Aspect their normalised values are
  averaged (Req 5.5).
* Publishing a new mapping version re-normalises affected records (Req 5.8);
  the mapping version is stored on every produced :class:`AspectRating`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.models.review import (
    Aspect,
    AspectRating,
    Platform,
)
from app.services.market_radar.parsing import normalise_rating

# ---------------------------------------------------------------------------
# Versioned mapping table: (version) -> {platform -> {lower category -> Aspect}}
# ---------------------------------------------------------------------------

MappingTable = dict[Platform, dict[str, Aspect]]

_MAPPING_V1: MappingTable = {
    Platform.GOOGLE: {
        "food": Aspect.FOOD,
        "rooms": Aspect.ROOM,
        "service": Aspect.SERVICE,
        "location": Aspect.LOCATION,
        "cleanliness": Aspect.CLEANLINESS,
    },
    Platform.MAKEMYTRIP: {
        "food & dining": Aspect.FOOD,
        "room": Aspect.ROOM,
        "hospitality": Aspect.STAFF,
        "location": Aspect.LOCATION,
        "cleanliness": Aspect.CLEANLINESS,
        "value for money": Aspect.VALUE_FOR_MONEY,
    },
    Platform.BOOKING: {
        "staff": Aspect.STAFF,
        "cleanliness": Aspect.CLEANLINESS,
        "comfort": Aspect.ROOM,
        "location": Aspect.LOCATION,
        "value for money": Aspect.VALUE_FOR_MONEY,
        "facilities": Aspect.SERVICE,
    },
    Platform.TRIPADVISOR: {
        "rooms": Aspect.ROOM,
        "service": Aspect.SERVICE,
        "value": Aspect.VALUE_FOR_MONEY,
        "cleanliness": Aspect.CLEANLINESS,
        "location": Aspect.LOCATION,
        "sleep quality": Aspect.ROOM,
    },
    Platform.AGODA: {
        "staff": Aspect.STAFF,
        "cleanliness": Aspect.CLEANLINESS,
        "facilities": Aspect.SERVICE,
        "location": Aspect.LOCATION,
        "value for money": Aspect.VALUE_FOR_MONEY,
        "food": Aspect.FOOD,
    },
}

# A second published version that adds Housekeeping + Booking_Experience mappings
# so re-normalisation on a new version is exercisable (Req 5.8).
_MAPPING_V2: MappingTable = {
    platform: dict(categories) for platform, categories in _MAPPING_V1.items()
}
_MAPPING_V2[Platform.BOOKING]["housekeeping"] = Aspect.HOUSEKEEPING
_MAPPING_V2[Platform.AGODA]["booking experience"] = Aspect.BOOKING_EXPERIENCE
_MAPPING_V2[Platform.MAKEMYTRIP]["booking process"] = Aspect.BOOKING_EXPERIENCE

MAPPING_VERSIONS: dict[str, MappingTable] = {
    "aspect-map-v1": _MAPPING_V1,
    "aspect-map-v2": _MAPPING_V2,
}

LATEST_MAPPING_VERSION = "aspect-map-v2"


@dataclass
class SubRating:
    """A raw platform sub-rating category + value fed to the normaliser."""

    category: str
    value: object  # may be non-numeric; validated by the normaliser


@dataclass
class AspectNormalizationError:
    """A non-fatal sub-rating error (Req 5.4)."""

    category: str
    reason: str


@dataclass
class AspectNormalizationResult:
    """Outcome of normalising one record's sub-ratings."""

    aspect_ratings: list[AspectRating]
    unmapped_categories: list[str] = field(default_factory=list)
    errors: list[AspectNormalizationError] = field(default_factory=list)


class AspectNormalizer:
    """Normalise platform sub-ratings to canonical aspect ratings."""

    def __init__(self, version: str = LATEST_MAPPING_VERSION) -> None:
        if version not in MAPPING_VERSIONS:
            raise ValueError(f"unknown mapping version {version!r}")
        self.version = version
        self._table = MAPPING_VERSIONS[version]
        # Running count of unmapped categories for the admin surface (Req 5.7).
        self._unmapped_counts: dict[tuple[str, str], int] = defaultdict(int)

    def normalize(
        self, platform: Platform, sub_ratings: list[SubRating]
    ) -> AspectNormalizationResult:
        """Normalise a record's sub-ratings into canonical AspectRatings."""
        platform_map = self._table.get(platform, {})
        bucketed: dict[Aspect, list[tuple[str, float, float]]] = defaultdict(list)
        unmapped: list[str] = []
        errors: list[AspectNormalizationError] = []

        for sub in sub_ratings:
            key = sub.category.strip().lower()
            aspect = platform_map.get(key)
            if aspect is None:
                unmapped.append(sub.category)
                self._unmapped_counts[(platform.value, sub.category)] += 1
                continue
            try:
                native = float(sub.value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                errors.append(
                    AspectNormalizationError(sub.category, f"non-numeric value {sub.value!r}")
                )
                continue
            try:
                normalised = normalise_rating(platform, native)
            except ValueError as exc:
                errors.append(AspectNormalizationError(sub.category, str(exc)))
                continue
            bucketed[aspect].append((sub.category, native, normalised))

        aspect_ratings: list[AspectRating] = []
        for aspect, entries in bucketed.items():
            avg_native = round(sum(e[1] for e in entries) / len(entries), 2)
            avg_norm = round(sum(e[2] for e in entries) / len(entries), 2)
            source = "+".join(sorted({e[0] for e in entries}))
            aspect_ratings.append(
                AspectRating(
                    aspect=aspect,
                    source_category=source,
                    native_value=avg_native,
                    normalised_value=avg_norm,
                    mapping_version=self.version,
                )
            )
        aspect_ratings.sort(key=lambda ar: ar.aspect)
        return AspectNormalizationResult(
            aspect_ratings=aspect_ratings,
            unmapped_categories=unmapped,
            errors=errors,
        )

    def unmapped_over_threshold(self, threshold: int = 20) -> list[tuple[str, str, int]]:
        """Return (platform, category, count) for unmapped categories > threshold."""
        return [
            (platform, category, count)
            for (platform, category), count in sorted(self._unmapped_counts.items())
            if count > threshold
        ]

    @property
    def unmapped_counts(self) -> dict[tuple[str, str], int]:
        """Expose the running unmapped-category counts."""
        return dict(self._unmapped_counts)
