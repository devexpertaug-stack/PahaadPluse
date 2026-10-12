"""Market Radar application service wiring the pipeline for the API.

Holds a process-wide :class:`ReviewCollector` seeded from the checked-in sample
dataset and exposes the read models the website needs: per-property /
per-platform review counts (Req 1.10) and the admin unmapped-category surface
(Req 5.7). This is demo-grade in-memory state; persistence lives in the SQLite
layer added by later features.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache

from app.models.review import Platform
from app.seed.sample_reviews import PROPERTIES, build_review_records
from app.services.market_radar.aspects import AspectNormalizer, SubRating
from app.services.market_radar.collector import CollectionJob, ReviewCollector


class MarketRadarService:
    """Facade over the collector + normaliser for API routers."""

    def __init__(self) -> None:
        self.collector = ReviewCollector()
        self.normalizer = AspectNormalizer()
        self._seed()

    def _seed(self) -> None:
        for record in build_review_records(enrich_records=True):
            self.collector.store.put(record)
        # Prime some unmapped-category counts so the admin surface has content.
        for _ in range(23):
            self.normalizer.normalize(Platform.GOOGLE, [SubRating("Parking", 4.0)])
        for _ in range(21):
            self.normalizer.normalize(Platform.MAKEMYTRIP, [SubRating("Spa", 4.0)])

    # ---- read models ----
    def property_platform_counts(self) -> list[dict]:
        """Per-property, per-platform review counts (Req 1.10)."""
        counts: Counter[tuple[str, str, str]] = Counter()
        missing_url: dict[tuple[str, str, str], int] = defaultdict(int)
        for r in self.collector.store.all():
            key = (r.property_id, r.property_name, r.platform)
            counts[key] += 1
            if r.missing_source_url:
                missing_url[key] += 1

        prop_names = {p.property_id: p.name for p in PROPERTIES}
        platforms = [p.value for p in Platform]
        out: list[dict] = []
        for prop_id, name in prop_names.items():
            per_platform = {
                platform: counts.get((prop_id, name, platform), 0) for platform in platforms
            }
            out.append(
                {
                    "property_id": prop_id,
                    "property_name": name,
                    "total": sum(per_platform.values()),
                    "per_platform": per_platform,
                    "missing_source_url": sum(
                        missing_url.get((prop_id, name, platform), 0)
                        for platform in platforms
                    ),
                }
            )
        return out

    def reviews_for(self, property_id: str, platform: str | None = None) -> list[dict]:
        records = self.collector.store.for_property(property_id, platform)
        records.sort(key=lambda r: r.date, reverse=True)
        return [self._public_review(r) for r in records]

    def _public_review(self, r) -> dict:  # noqa: ANN001 - ReviewRecord
        return {
            "id": r.id,
            "platform": r.platform,
            "property_id": r.property_id,
            "property_name": r.property_name,
            "author_pseudonym": r.author_pseudonym,
            "date": r.date.isoformat(),
            "native_rating": r.native_rating,
            "normalised_rating": r.normalised_rating,
            "text": r.text,
            "detected_language": r.detected_language,
            "script": r.script,
            "overall_sentiment": r.overall_sentiment,
            "source_url": r.source_url,
            "source_url_available": not r.missing_source_url,
        }

    def unmapped_categories(self, threshold: int = 20) -> list[dict]:
        """Unmapped categories over the admin threshold (Req 5.7)."""
        return [
            {"platform": platform, "category": category, "count": count}
            for platform, category, count in self.normalizer.unmapped_over_threshold(threshold)
        ]

    def recent_jobs(self) -> list[CollectionJob]:
        return list(self.collector.jobs.values())


@lru_cache
def get_market_radar_service() -> MarketRadarService:
    """Return the process-wide Market Radar service (seeded once)."""
    return MarketRadarService()
