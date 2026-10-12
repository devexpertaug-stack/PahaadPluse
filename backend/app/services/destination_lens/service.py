"""Destination Lens service (Req 14).

On review storage this service extracts Place_Entities, geocodes them
gazetteer-first (storing lat/lon + resolution confidence) and accumulates
negative-mention Hotspots per geocoded entity. The website heatmap filters
hotspots by issue theme and date range.

This is demo-grade in-memory state seeded from the checked-in sample review
dataset; persistence lives in the SQLite layer added by later features.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

from app.adapters.geocoder import GeoPoint, get_geocoder
from app.seed.sample_reviews import build_review_records
from app.services.destination_lens.entities import (
    THEMES,
    PlaceEntity,
    extract_place_entities,
)

# Gazetteer resolution confidence (external would be lower / variable).
_GAZETTEER_CONFIDENCE = 0.95


def _m(review_id, property_id, property_name, platform, d, text, url):
    return {
        "review_id": review_id,
        "property_id": property_id,
        "property_name": property_name,
        "platform": platform,
        "review_date": date.fromisoformat(d),
        "text": text,
        "author_pseudonym": "anon-destination",
        "source_url": url,
    }


# Synthetic place-level mentions so the website heatmap has content out of the
# box. These describe DESTINATION issues (not property reviews) drawn from the
# public reviews' language mix; author identity is a generic placeholder.
_DESTINATION_SEED: list[dict] = [
    _m("d-mall-1", "mus-forestseason", "The Forest Season Resort", "Google", "2024-03-10",
       "Terrible traffic jam near Mall Road every evening, took an hour to walk.",
       "https://www.google.com/maps/place/forestseason-mussoorie"),
    _m("d-mall-2", "mus-deodarresidency", "Deodar Residency", "TripAdvisor", "2024-04-02",
       "Mall Road mein bahut garbage pada tha, gandagi bahut thi.",
       "https://www.tripadvisor.in/Hotel_Review-deodarresidency-mussoorie.html"),
    _m("d-mall-3", "mus-cloudvalley", "Cloud Valley Resort", "MakeMyTrip", "2024-02-18",
       "माल रोड पर पार्किंग की बहुत समस्या है, कहीं जगह नहीं मिलती।",
       "https://www.makemytrip.com/hotels/cloudvalley-mussoorie.html"),
    _m("d-mall-4", "mus-mallroadlodge", "Mall Road Heritage Lodge", "Google", "2024-05-05",
       "Roads near the Mall are full of potholes, very bad road condition.",
       "https://www.google.com/maps/place/mallroadlodge-mussoorie"),
    _m("d-mall-5", "mus-himalayanook", "Himalayan Nook Homestay", "Booking.com", "2024-01-22",
       "Felt unsafe walking back from Mall Road late at night, poor safety.",
       None),
    _m("d-kempty-1", "mus-cloudvalley", "Cloud Valley Resort", "Google", "2024-03-28",
       "Kempty Falls was so crowded, huge traffic jam on the way and lots of garbage.",
       "https://www.google.com/maps/place/cloudvalley-mussoorie"),
    _m("d-kempty-2", "mus-camelsback", "Camel's Back Retreat", "Agoda", "2024-04-15",
       "Kempty Falls ke paas bahut kooda tha, water bhi ganda tha.",
       "https://www.agoda.com/camelsback-mussoorie/hotel/mussoorie-in.html"),
    _m("d-kempty-3", "mus-forestseason", "The Forest Season Resort", "TripAdvisor", "2024-05-20",
       "केम्प्टी फॉल पर पार्किंग नहीं मिली और गंदगी बहुत थी।",
       "https://www.tripadvisor.in/Hotel_Review-forestseason-mussoorie.html"),
    _m("d-gun-1", "mus-deodarresidency", "Deodar Residency", "Google", "2024-02-09",
       "Gun Hill ropeway queue was chaos, no parking and water shortage at the top.",
       "https://www.google.com/maps/place/deodarresidency-mussoorie"),
    _m("d-gun-2", "mus-mallroadlodge", "Mall Road Heritage Lodge", "MakeMyTrip", "2024-04-30",
       "Gun Hill ke paas safai ki kami, garbage har jagah.",
       "https://www.makemytrip.com/hotels/mallroadlodge-mussoorie.html"),
    _m("d-camel-1", "mus-camelsback", "Camel's Back Retreat", "Google", "2024-03-05",
       "Camel's Back Road had broken road condition and potholes everywhere.",
       "https://www.google.com/maps/place/camelsback-mussoorie"),
    _m("d-camel-2", "mus-himalayanook", "Himalayan Nook Homestay", "TripAdvisor", "2024-05-12",
       "कैमल बैक रोड पर पानी की सप्लाई की समस्या थी।",
       "https://www.tripadvisor.in/Hotel_Review-himalayanook-mussoorie.html"),
    _m("d-landour-1", "mus-forestseason", "The Forest Season Resort", "Booking.com", "2024-04-08",
       "Landour roads are narrow with bad traffic and no parking space at all.",
       "https://www.booking.com/hotel/in/forestseason-mussoorie.html"),
]


@dataclass
class Mention:
    """A single place mention extracted from a review (Req 14.1-14.3)."""

    review_id: str
    property_id: str
    property_name: str
    platform: str
    date: date
    canonical: str
    surface: str
    themes: list[str]
    is_negative: bool
    text: str
    author_pseudonym: str
    source_url: str | None
    latitude: float | None
    longitude: float | None
    resolution_confidence: float
    geocode_source: str | None


@dataclass
class Hotspot:
    """A geocoded hotspot aggregating negative mentions (Req 14.3)."""

    canonical: str
    label: str
    latitude: float
    longitude: float
    negative_count: int
    total_count: int
    themes: dict[str, int] = field(default_factory=dict)
    properties: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "canonical": self.canonical,
            "label": self.label,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "negative_count": self.negative_count,
            "total_count": self.total_count,
            "themes": self.themes,
            "distinct_properties": len(self.properties),
        }


def _title(canonical: str) -> str:
    return canonical.title()


class DestinationLensService:
    """Facade computing hotspots + mentions for the website + evidence packets."""

    def __init__(self) -> None:
        self._geocoder = get_geocoder()
        self._geo_cache: dict[str, GeoPoint | None] = {}
        self.mentions: list[Mention] = []
        self.issues_surfaced: int = 0
        self._seed()

    def _geocode(self, canonical: str) -> GeoPoint | None:
        if canonical not in self._geo_cache:
            self._geo_cache[canonical] = self._geocoder.geocode(canonical)
        return self._geo_cache[canonical]

    def _seed(self) -> None:
        for record in build_review_records(enrich_records=True):
            self.index_review(
                review_id=record.id,
                property_id=record.property_id,
                property_name=record.property_name,
                platform=record.platform,
                review_date=record.date,
                text=record.text,
                author_pseudonym=record.author_pseudonym,
                source_url=record.source_url,
            )
        for m in _DESTINATION_SEED:
            self.index_review(**m)

    def index_review(
        self,
        *,
        review_id: str,
        property_id: str,
        property_name: str,
        platform: str,
        review_date: date,
        text: str,
        author_pseudonym: str,
        source_url: str | None,
    ) -> list[PlaceEntity]:
        """Extract + geocode place entities for one review (Req 14.1-14.2)."""
        entities = extract_place_entities(text)
        for ent in entities:
            point = self._geocode(ent.canonical)
            self.mentions.append(
                Mention(
                    review_id=review_id,
                    property_id=property_id,
                    property_name=property_name,
                    platform=platform,
                    date=review_date,
                    canonical=ent.canonical,
                    surface=ent.surface,
                    themes=ent.themes,
                    is_negative=ent.is_negative,
                    text=text,
                    author_pseudonym=author_pseudonym,
                    source_url=source_url,
                    latitude=point.latitude if point else None,
                    longitude=point.longitude if point else None,
                    resolution_confidence=_GAZETTEER_CONFIDENCE if point else 0.0,
                    geocode_source=point.source if point else None,
                )
            )
        return entities

    # ---- read models ----
    def _filtered(
        self,
        theme: str | None,
        start: date | None,
        end: date | None,
        negative_only: bool = True,
    ) -> list[Mention]:
        out = []
        for m in self.mentions:
            if m.latitude is None:
                continue
            if negative_only and not m.is_negative:
                continue
            if theme and theme not in m.themes:
                continue
            if start and m.date < start:
                continue
            if end and m.date > end:
                continue
            out.append(m)
        return out

    def hotspots(
        self,
        theme: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[Hotspot]:
        """Negative-mention hotspots per geocoded entity (Req 14.3)."""
        buckets: dict[str, Hotspot] = {}
        # total mentions (any sentiment) for context
        totals: dict[str, int] = defaultdict(int)
        for m in self._filtered(theme, start, end, negative_only=False):
            totals[m.canonical] += 1
        for m in self._filtered(theme, start, end, negative_only=True):
            hs = buckets.get(m.canonical)
            if hs is None:
                hs = Hotspot(
                    canonical=m.canonical,
                    label=_title(m.canonical),
                    latitude=m.latitude,  # type: ignore[arg-type]
                    longitude=m.longitude,  # type: ignore[arg-type]
                    negative_count=0,
                    total_count=totals[m.canonical],
                )
                buckets[m.canonical] = hs
            hs.negative_count += 1
            hs.properties.add(m.property_id)
            for t in m.themes:
                hs.themes[t] = hs.themes.get(t, 0) + 1
        return sorted(
            buckets.values(), key=lambda h: h.negative_count, reverse=True
        )

    def heatmap_view(
        self,
        theme: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> dict:
        hotspots = self.hotspots(theme, start, end)
        return {
            "destination": "Mussoorie, Uttarakhand",
            "theme": theme,
            "themes_available": list(THEMES),
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "hotspots": [h.to_dict() for h in hotspots],
            "total_negative_mentions": sum(h.negative_count for h in hotspots),
        }

    def quotes_for(
        self,
        canonical: str,
        theme: str | None,
        start: date | None,
        end: date | None,
    ) -> list[Mention]:
        out = [
            m
            for m in self._filtered(theme, start, end, negative_only=True)
            if m.canonical == canonical
        ]
        out.sort(key=lambda m: m.date, reverse=True)
        return out

    def monthly_trend(
        self,
        canonical: str,
        theme: str | None,
        start: date | None,
        end: date | None,
    ) -> list[tuple[str, int]]:
        counts: dict[str, int] = defaultdict(int)
        for m in self._filtered(theme, start, end, negative_only=True):
            if m.canonical == canonical:
                counts[m.date.strftime("%Y-%m")] += 1
        return sorted(counts.items())

    def record_issue_surfaced(self) -> int:
        """Record that an Evidence Packet was surfaced to authorities (Req 14.8)."""
        self.issues_surfaced += 1
        return self.issues_surfaced


@lru_cache
def get_destination_lens_service() -> DestinationLensService:
    """Return the process-wide Destination Lens service (seeded once)."""
    return DestinationLensService()
