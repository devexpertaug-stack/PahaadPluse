"""Canonical sample Mussoorie review dataset (Req 2.8).

This module is the single source of truth for the checked-in sample dataset. It
describes a Cluster of six Mussoorie Properties with reviews across all five
platforms (Google, MakeMyTrip, Booking.com, TripAdvisor, Agoda) and a mix of
English, Devanagari-Hindi and romanised-Hindi (Hinglish) text.

Honesty note (per the datasheet): this environment cannot crawl the live review
platforms, so the records below are a *representative, hand-authored* dataset
written to mirror the structure, length and language mix of genuine public
Mussoorie reviews collected within each platform's terms. Reviewer identities
are pseudonymised with a salted hash (salt from env, never committed), and
``source_url`` values are HONEST PLACEHOLDERS on each platform's domain — they
point at the platform's property page pattern rather than fabricated specific
review permalinks. A small number of records deliberately omit the source URL
to exercise the "source URL unavailable" handling (Req 2.9).

Generating the dataset from code guarantees the datasheet counts always match
the actual records.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.review import Platform
from app.services.market_radar.parsing import ReviewParser, normalise_rating
from app.services.market_radar.pipeline import enrich
from app.services.market_radar.responsible import pseudonymise_reviewer

CLUSTER_NAME = "Mussoorie Mall Road Cluster"
COLLECTION_DATE_RANGE = ("2023-09-01", "2024-06-30")


@dataclass(frozen=True)
class PropertySpec:
    """A property in the sample cluster."""

    property_id: str
    name: str


PROPERTIES: list[PropertySpec] = [
    PropertySpec("mus-pineview", "Pine View Inn"),
    PropertySpec("mus-deodarresidency", "Deodar Residency"),
    PropertySpec("mus-cloudvalley", "Cloud Valley Resort"),
    PropertySpec("mus-himalayanook", "Himalayan Nook Homestay"),
    PropertySpec("mus-mallroadlodge", "Mall Road Heritage Lodge"),
    PropertySpec("mus-camelsback", "Camel's Back Retreat"),
]

# Platform property-page URL patterns used for honest placeholder source URLs.
_URL_PATTERN: dict[Platform, str] = {
    Platform.GOOGLE: "https://www.google.com/maps/place/{slug}-mussoorie",
    Platform.MAKEMYTRIP: "https://www.makemytrip.com/hotels/{slug}-mussoorie.html",
    Platform.BOOKING: "https://www.booking.com/hotel/in/{slug}-mussoorie.html",
    Platform.TRIPADVISOR: "https://www.tripadvisor.in/Hotel_Review-{slug}-mussoorie.html",
    Platform.AGODA: "https://www.agoda.com/{slug}-mussoorie/hotel/mussoorie-in.html",
}


@dataclass(frozen=True)
class RawSeedReview:
    """A raw seed review before pseudonymisation + parsing."""

    platform: Platform
    platform_review_id: str
    property_id: str
    display_name: str
    date: str
    native_rating: float
    text: str
    has_source_url: bool = True


def _slug(property_id: str) -> str:
    return property_id.replace("mus-", "")


# ---------------------------------------------------------------------------
# The dataset. Kept compact but covering every platform + language per property.
# Native ratings use each platform's native scale (Booking/Agoda are /10).
# ---------------------------------------------------------------------------
_SEED: list[RawSeedReview] = [
    # ---- Pine View Inn ----
    RawSeedReview(Platform.GOOGLE, "g-pv-1", "mus-pineview", "Aarav Mehta", "2024-03-14", 5,
                  "Beautiful valley view and very clean rooms. Staff were friendly and helpful."),
    RawSeedReview(Platform.MAKEMYTRIP, "mmt-pv-1", "mus-pineview", "Riya Sharma", "2024-02-02", 4,
                  "kamra bahut accha tha aur khana badhiya. staff saaf aur helpful."),
    RawSeedReview(Platform.BOOKING, "bk-pv-1", "mus-pineview", "Daniel O'Brien", "2023-11-21", 9,
                  "Great location near Mall Road. Breakfast was delicious and the room spacious."),
    RawSeedReview(Platform.TRIPADVISOR, "ta-pv-1", "mus-pineview", "Neha Kapoor", "2024-04-05", 4,
                  "कमरा बहुत अच्छा था और स्टाफ़ मददगार था। जगह शांत थी।"),
    RawSeedReview(Platform.AGODA, "ag-pv-1", "mus-pineview", "Wei Chen", "2024-01-18", 8,
                  "Value for money was good but the wifi was slow in the evening."),
    # ---- Deodar Residency ----
    RawSeedReview(Platform.GOOGLE, "g-dr-1", "mus-deodarresidency", "Sanjay Rawat", "2024-05-09", 4,
                  "Clean rooms and tasty food. Location is central and quiet."),
    RawSeedReview(Platform.MAKEMYTRIP, "mmt-dr-1", "mus-deodarresidency", "Pooja Nair", "2023-10-30", 3,
                  "jagah shandaar lekin kamra thoda mehenga tha. service theek thi."),
    RawSeedReview(Platform.BOOKING, "bk-dr-1", "mus-deodarresidency", "Emma Wilson", "2024-02-27", 7,
                  "Comfortable beds and helpful staff, though housekeeping was a bit slow."),
    RawSeedReview(Platform.TRIPADVISOR, "ta-dr-1", "mus-deodarresidency", "Vikram Singh", "2024-03-22", 5,
                  "खाना स्वादिष्ट था और कमरा साफ़ था। बहुत अच्छा अनुभव रहा।"),
    RawSeedReview(Platform.AGODA, "ag-dr-1", "mus-deodarresidency", "Ananya Das", "2023-12-11", 6,
                  "staff accha tha par booking process thoda slow tha. paisa vasool jagah."),
    # ---- Cloud Valley Resort ----
    RawSeedReview(Platform.GOOGLE, "g-cv-1", "mus-cloudvalley", "Rohan Gupta", "2024-04-19", 5,
                  "Amazing views and excellent service. The restaurant food was wonderful."),
    RawSeedReview(Platform.MAKEMYTRIP, "mmt-cv-1", "mus-cloudvalley", "Isha Verma", "2024-01-07", 2,
                  "kamra ganda tha aur service bakwaas. khana bhi kharab tha.", has_source_url=False),
    RawSeedReview(Platform.BOOKING, "bk-cv-1", "mus-cloudvalley", "Lukas Müller", "2023-09-28", 8,
                  "Lovely cleanliness and great facilities. Staff were polite and quick."),
    RawSeedReview(Platform.TRIPADVISOR, "ta-cv-1", "mus-cloudvalley", "Meera Joshi", "2024-05-30", 3,
                  "कमरा अच्छा था लेकिन सेवा धीमी थी। जगह अच्छी है।"),
    RawSeedReview(Platform.AGODA, "ag-cv-1", "mus-cloudvalley", "Carlos Ruiz", "2024-02-14", 9,
                  "zabardast location aur mast view. staff bahut helpful the."),
    # ---- Himalayan Nook Homestay ----
    RawSeedReview(Platform.GOOGLE, "g-hn-1", "mus-himalayanook", "Priya Bhatt", "2024-03-03", 4,
                  "Cosy homestay with friendly owners. Breakfast was homemade and delicious."),
    RawSeedReview(Platform.MAKEMYTRIP, "mmt-hn-1", "mus-himalayanook", "Arjun Rana", "2023-11-15", 5,
                  "owner bahut acche the aur khana ghar jaisa tha. jagah shant hai."),
    RawSeedReview(Platform.BOOKING, "bk-hn-1", "mus-himalayanook", "Sophie Dubois", "2024-04-12", 6,
                  "Nice room but the location is a bit far from the Mall Road."),
    RawSeedReview(Platform.TRIPADVISOR, "ta-hn-1", "mus-himalayanook", "Kabir Khanna", "2024-01-25", 4,
                  "स्टाफ़ बहुत मददगार था और कमरा साफ़ था। खाना स्वादिष्ट था।"),
    RawSeedReview(Platform.AGODA, "ag-hn-1", "mus-himalayanook", "Yuki Tanaka", "2023-10-08", 7,
                  "Clean and comfortable, good value for money. Wifi could be better.",
                  has_source_url=False),
    # ---- Mall Road Heritage Lodge ----
    RawSeedReview(Platform.GOOGLE, "g-mr-1", "mus-mallroadlodge", "Deepak Chauhan", "2024-05-21", 3,
                  "Heritage charm but rooms were cold and the service was slow."),
    RawSeedReview(Platform.MAKEMYTRIP, "mmt-mr-1", "mus-mallroadlodge", "Nisha Pillai", "2024-02-19", 4,
                  "location zabardast hai, mall road ke paas. kamra accha aur saaf tha."),
    RawSeedReview(Platform.BOOKING, "bk-mr-1", "mus-mallroadlodge", "James Carter", "2023-12-02", 7,
                  "Good central location and friendly staff. Breakfast variety was limited."),
    RawSeedReview(Platform.TRIPADVISOR, "ta-mr-1", "mus-mallroadlodge", "Shreya Iyer", "2024-04-27", 5,
                  "कमरा साफ़ और आरामदायक था। स्टाफ़ की सेवा बहुत अच्छी थी।"),
    RawSeedReview(Platform.AGODA, "ag-mr-1", "mus-mallroadlodge", "Olivia Brown", "2024-01-30", 5,
                  "Rooms were noisy at night and overpriced for the facilities offered."),
    # ---- Camel's Back Retreat ----
    RawSeedReview(Platform.GOOGLE, "g-cb-1", "mus-camelsback", "Harish Negi", "2024-03-28", 5,
                  "Peaceful retreat with lovely gardens. Staff were warm and attentive."),
    RawSeedReview(Platform.MAKEMYTRIP, "mmt-cb-1", "mus-camelsback", "Tanvi Desai", "2023-10-19", 4,
                  "jagah bahut shant aur saaf thi. khana badhiya aur staff accha."),
    RawSeedReview(Platform.BOOKING, "bk-cb-1", "mus-camelsback", "Michael Scott", "2024-05-16", 8,
                  "Excellent cleanliness and comfort. Great value for the price paid."),
    RawSeedReview(Platform.TRIPADVISOR, "ta-cb-1", "mus-camelsback", "Aisha Begum", "2024-02-08", 4,
                  "कमरा अच्छा और शांत था। सेवा अच्छी थी पर खाना साधारण था।"),
    RawSeedReview(Platform.AGODA, "ag-cb-1", "mus-camelsback", "Ravi Prasad", "2023-11-07", 9,
                  "mast retreat, bilkul shant. staff bahut helpful aur jagah saaf.",
                  has_source_url=False),
]


def _source_url(platform: Platform, property_id: str, has_url: bool) -> str | None:
    if not has_url:
        return None
    return _URL_PATTERN[platform].format(slug=_slug(property_id))


def build_raw_records() -> list[dict]:
    """Build pseudonymised raw review dicts (pre-parse) from the seed."""
    prop_names = {p.property_id: p.name for p in PROPERTIES}
    out: list[dict] = []
    for seed in _SEED:
        out.append(
            {
                "id": f"{seed.platform.value}:{seed.platform_review_id}",
                "platform": seed.platform.value,
                "platform_review_id": seed.platform_review_id,
                "property_id": seed.property_id,
                "property_name": prop_names[seed.property_id],
                "author_pseudonym": pseudonymise_reviewer(
                    seed.display_name, seed.platform.value
                ),
                "date": seed.date,
                "native_rating": seed.native_rating,
                "normalised_rating": normalise_rating(seed.platform, seed.native_rating),
                "text": seed.text,
                "source_url": _source_url(seed.platform, seed.property_id, seed.has_source_url),
                "missing_source_url": not seed.has_source_url,
            }
        )
    return out


def build_review_records(enrich_records: bool = True) -> list:
    """Parse + optionally enrich the seed into ReviewRecords."""
    parser = ReviewParser()
    records = [parser.parse_one(raw) for raw in build_raw_records()]
    if enrich_records:
        records = [enrich(r) for r in records]
    return records
