"""Review_Record domain model and the shared Market Radar enumerations.

The canonical review pipeline (parse -> collect -> detect language -> normalise
aspects -> classify sentiment) all operates on :class:`ReviewRecord`. The
pydantic model here is the single source of truth; the published JSON schema at
``app/schemas/review_record.schema.json`` is generated to match it and is used
to validate inbound Review_Record JSON (Req 3.4, 3.8).
"""

from __future__ import annotations

from datetime import date as date_type
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Platform(StrEnum):
    """Review source platforms in scope (Req 1/3)."""

    GOOGLE = "Google"
    MAKEMYTRIP = "MakeMyTrip"
    BOOKING = "Booking.com"
    TRIPADVISOR = "TripAdvisor"
    AGODA = "Agoda"


class Aspect(StrEnum):
    """The nine canonical cross-platform aspects (Req 5)."""

    FOOD = "Food"
    ROOM = "Room"
    HOUSEKEEPING = "Housekeeping"
    STAFF = "Staff"
    LOCATION = "Location"
    SERVICE = "Service"
    VALUE_FOR_MONEY = "Value_for_Money"
    CLEANLINESS = "Cleanliness"
    BOOKING_EXPERIENCE = "Booking_Experience"


class Language(StrEnum):
    """Detected language tags produced before sentiment (Req 4)."""

    EN = "en"
    HI = "hi"
    HI_LATN = "hi-Latn"
    UND = "und"


class Script(StrEnum):
    """Detected dominant script (Req 4.1)."""

    LATIN = "Latin"
    DEVANAGARI = "Devanagari"
    MIXED = "mixed"


class SentimentLabel(StrEnum):
    """Sentiment polarity labels used across the platform (Req 6)."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# Native rating scales per platform. Used for the documented linear
# native->normalised mapping (native min -> 1.0, max -> 5.0). (Req 3.3)
PLATFORM_RATING_SCALES: dict[Platform, tuple[float, float]] = {
    Platform.GOOGLE: (1.0, 5.0),
    Platform.MAKEMYTRIP: (1.0, 5.0),
    Platform.BOOKING: (1.0, 10.0),
    Platform.TRIPADVISOR: (1.0, 5.0),
    Platform.AGODA: (1.0, 10.0),
}


class AspectRating(BaseModel):
    """A normalised sub-rating mapped to a canonical Aspect (Req 5)."""

    model_config = ConfigDict(use_enum_values=True)

    aspect: Aspect
    source_category: str = Field(description="Raw platform category label.")
    native_value: float
    normalised_value: float = Field(ge=1.0, le=5.0)
    mapping_version: str


class AspectMention(BaseModel):
    """An aspect-level sentiment mention produced by the Sentiment_Engine."""

    model_config = ConfigDict(use_enum_values=True)

    aspect: Aspect
    label: SentimentLabel
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(min_length=1, description="Substring of the ORIGINAL text.")


class ReviewRecord(BaseModel):
    """Canonical normalised review record (Req 3).

    ``text`` always stores the ORIGINAL review text char-for-char. For
    romanised Hindi (``hi-Latn``) a Devanagari form is additionally stored in
    ``transliterated_text`` and is used as sentiment-model input, but evidence
    spans are always substrings of ``text`` (Req 4.4, 6.4).
    """

    model_config = ConfigDict(use_enum_values=True)

    # ---- Identity ----
    id: str = Field(description="Stable PahadPulse record id.")
    platform: Platform
    platform_review_id: str = Field(description="Native review id on the platform.")
    property_id: str = Field(description="Property identifier within the cluster.")
    property_name: str

    # ---- Author (pseudonymised; raw name never stored, Req 2) ----
    author_pseudonym: str

    # ---- Content ----
    date: date_type
    native_rating: float
    normalised_rating: float = Field(ge=1.0, le=5.0)
    text: str

    # ---- Language / script (Req 4) ----
    detected_language: Language = Language.UND
    script: Script = Script.LATIN
    detection_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    transliterated_text: str | None = None

    # ---- Provenance ----
    source_url: str | None = None

    # ---- Derived (Req 5/6) ----
    aspect_ratings: list[AspectRating] = Field(default_factory=list)
    overall_sentiment: SentimentLabel | None = None
    overall_sentiment_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    aspect_mentions: list[AspectMention] = Field(default_factory=list)
    sentiment_model_version: str | None = None

    # ---- Flags (Req 2/4/6) ----
    missing_source_url: bool = False
    transliteration_failed: bool = False
    sentiment_unsupported: bool = False
    sentiment_text_absent: bool = False
    sentiment_failed: bool = False
