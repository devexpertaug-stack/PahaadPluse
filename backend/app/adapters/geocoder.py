"""Geocoder adapter.

Defines the :class:`Geocoder` interface and a local-gazetteer-first
implementation seeded with Mussoorie / Uttarakhand hill-town locations
(Req 14.2). An external provider can sit behind the same interface later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import GeocoderProvider, get_settings

# Curated local gazetteer of Uttarakhand hill-town landmarks (lat, lon).
_GAZETTEER: dict[str, tuple[float, float]] = {
    "mussoorie": (30.4599, 78.0644),
    "mall road": (30.4575, 78.0707),
    "gun hill": (30.4612, 78.0680),
    "kempty falls": (30.4760, 78.0190),
    "landour": (30.4590, 78.0920),
    "camel's back road": (30.4620, 78.0730),
    "dehradun": (30.3165, 78.0322),
    "nainital": (29.3919, 79.4542),
    "rishikesh": (30.0869, 78.2676),
    "haridwar": (29.9457, 78.1642),
    "almora": (29.5971, 79.6591),
    "ranikhet": (29.6434, 79.4322),
}


@dataclass
class GeoPoint:
    """A geocoded location."""

    query: str
    latitude: float
    longitude: float
    source: str  # "gazetteer" | "external"
    matched_name: str | None = None


class Geocoder(ABC):
    """Interface for resolving place names to coordinates."""

    @abstractmethod
    def geocode(self, query: str) -> GeoPoint | None:
        """Resolve ``query`` to a :class:`GeoPoint` or ``None`` if unknown."""


class GazetteerGeocoder(Geocoder):
    """Local-gazetteer-first geocoder (works fully offline)."""

    def __init__(self, gazetteer: dict[str, tuple[float, float]] | None = None) -> None:
        self._gazetteer = gazetteer or _GAZETTEER

    def geocode(self, query: str) -> GeoPoint | None:
        if not query or not query.strip():
            return None
        key = query.strip().lower()
        if key in self._gazetteer:
            lat, lon = self._gazetteer[key]
            return GeoPoint(
                query=query,
                latitude=lat,
                longitude=lon,
                source="gazetteer",
                matched_name=key,
            )
        # Loose substring match against known landmarks.
        for name, (lat, lon) in self._gazetteer.items():
            if name in key or key in name:
                return GeoPoint(
                    query=query,
                    latitude=lat,
                    longitude=lon,
                    source="gazetteer",
                    matched_name=name,
                )
        return None


def get_geocoder() -> Geocoder:
    """Select the geocoder based on configuration.

    The gazetteer is always used first; external providers are added later
    behind the same interface.
    """
    settings = get_settings()
    _ = settings.geocoder_provider  # external provider reserved for later features
    if settings.geocoder_provider is GeocoderProvider.EXTERNAL:
        # External adapter not yet implemented; fall back to the gazetteer.
        return GazetteerGeocoder()
    return GazetteerGeocoder()
