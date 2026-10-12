"""Deterministic generated review dataset for The Forest Season Resort.

The Forest Season Resort (``mus-forestseason``) is the Home_Property of the
Mussoorie Mall Road Cluster. The checked-in sample dataset hand-authors one
review per competitor property/platform, but the Home_Property needs enough
depth (all five platforms, ~18 months, a language mix and aspect-rich text) to
read as a real, lived-in property across the whole dashboard.

Honesty note: this environment cannot (and must not) crawl the live review
platforms — doing so has no free, credential-less path and would breach each
platform's terms (the responsible-collection module gates live crawling behind
robots.txt + terms, Req 2). So this module *generates* a representative,
seed-reproducible dataset and feeds it through the REAL ingestion pipeline
(ReviewParser + enrich), exactly like genuinely collected reviews. The same
file can also be posted through ``POST /market-radar/collection/upload`` to
demonstrate the live collection path end to end.

The generator is pure + seeded (:data:`FOREST_SEASON_SEED`) so the same seed
always yields the same records, which keeps the datasheet counts stable.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from app.models.review import Platform

FOREST_SEASON_ID = "mus-forestseason"
FOREST_SEASON_NAME = "The Forest Season Resort"

# Fixed seed for reproducibility (same seed -> identical records).
FOREST_SEASON_SEED = 20240915

# ~18-month collection window ending alongside the cluster's reference "now".
_WINDOW_START = date(2023, 1, 10)
_WINDOW_END = date(2024, 6, 20)

# Native rating scale per platform (Booking/Agoda are /10, others /5).
_SCALE_10 = {Platform.BOOKING, Platform.AGODA}

# Synthetic reviewer display names (pseudonymised downstream, no raw PII kept).
_AUTHORS: tuple[str, ...] = (
    "Aditya Rawat", "Shreya Menon", "Rohit Bisht", "Kavya Nair", "Imran Sheikh",
    "Priyanka Rana", "Daniel Fischer", "Mei Lin", "Harpreet Kaur", "Suresh Pillai",
    "Ananya Ghosh", "Thomas Weber", "Nikita Joshi", "Farhan Qureshi", "Elena Petrova",
    "Vivek Chauhan", "Sana Khan", "Gaurav Negi", "Ritu Agarwal", "Oliver Smith",
    "Deepika Rao", "Manav Thakur", "Yuki Sato", "Pooja Bhandari", "Arvind Kumar",
    "Isabella Rossi", "Tenzin Dorjee", "Megha Saxena", "Karthik Iyer", "Laura Martin",
)

# Aspect-rich, code-switched sentence fragments styled after the analytics
# dataset vocabulary. Keyed by (polarity) so we can compose multi-aspect text.
_POSITIVE: dict[str, tuple[str, ...]] = {
    "en": (
        "The forest-facing rooms were spacious and spotless, and the beds were very comfortable.",
        "Breakfast was delicious with fresh local produce and the staff were warm and attentive.",
        "Great location tucked in the deodar forest yet an easy drive to Mall Road.",
        "Excellent service, the housekeeping was thorough every single day.",
        "Wonderful value for money, the bonfire evenings and valley views were magical.",
    ),
    "hi-Latn": (
        "kamra bahut saaf aur bada tha, forest view zabardast tha.",
        "khana badhiya tha, breakfast mein local swaad aur staff bahut helpful.",
        "jagah shaant hai, deodar jungle ke beech lekin mall road paas.",
        "service fast thi aur housekeeping roz accha kaam karti thi.",
        "paisa vasool resort, bonfire aur valley view ekdam mast.",
    ),
    "hi": (
        "कमरा बहुत साफ़ और बड़ा था, जंगल का नज़ारा शानदार था।",
        "नाश्ता स्वादिष्ट था और स्टाफ़ बहुत मददगार और विनम्र था।",
        "जगह शांत है, देवदार के जंगल में फिर भी माल रोड पास।",
        "सेवा तेज़ थी और हाउसकीपिंग रोज़ अच्छे से होती थी।",
        "पैसा वसूल रिज़ॉर्ट, अलाव की शामें और घाटी का दृश्य बहुत सुंदर।",
    ),
}
_NEGATIVE: dict[str, tuple[str, ...]] = {
    "en": (
        "The breakfast was cold and the food quality has slipped lately, very disappointing.",
        "Service was slow and the wifi kept dropping all evening.",
        "The room felt damp and housekeeping skipped us twice during the stay.",
        "Overpriced for the facilities and the check-in process was confusing.",
        "The restaurant kitchen was understaffed and the dinner took over an hour.",
    ),
    "hi-Latn": (
        "breakfast thanda tha aur khana ab pehle jaisa accha nahi raha, nirasha hui.",
        "service slow thi aur wifi shaam bhar band hoti rahi.",
        "kamra thoda seelan wala tha aur housekeeping do baar miss hui.",
        "facilities ke hisaab se mehenga aur check-in process confusing tha.",
        "restaurant kitchen mein staff kam tha, dinner mein ek ghanta lag gaya.",
    ),
    "hi": (
        "नाश्ता ठंडा था और खाने की गुणवत्ता अब पहले जैसी नहीं रही, निराशा हुई।",
        "सेवा धीमी थी और वाईफ़ाई पूरी शाम बंद होती रही।",
        "कमरे में थोड़ी सीलन थी और हाउसकीपिंग दो बार मिस हुई।",
        "सुविधाओं के हिसाब से महंगा और चेक-इन प्रक्रिया भ्रमित करने वाली थी।",
        "रेस्तरां की रसोई में स्टाफ़ कम था, रात के खाने में एक घंटा लग गया।",
    ),
}
_NEUTRAL: dict[str, tuple[str, ...]] = {
    "en": (
        "Decent stay overall; the room was fine and the location is quiet.",
        "The property is pleasant but the food was average on our visit.",
    ),
    "hi-Latn": (
        "overall theek thaak stay; kamra sahi tha aur jagah shaant hai.",
        "property acchi hai par khana is baar average tha.",
    ),
    "hi": (
        "कुल मिलाकर ठीक-ठाक अनुभव; कमरा सही था और जगह शांत है।",
        "रिज़ॉर्ट अच्छा है पर इस बार खाना औसत था।",
    ),
}

_LANGS: tuple[str, ...] = ("en", "hi-Latn", "hi")
_PLATFORMS: tuple[Platform, ...] = tuple(Platform)


def _native_rating(platform: Platform, polarity: str, rng: random.Random) -> float:
    """Pick a plausible native rating for the platform scale and polarity."""
    if platform in _SCALE_10:
        if polarity == "pos":
            return float(rng.choice([8, 9, 9, 10]))
        if polarity == "neg":
            return float(rng.choice([3, 4, 5, 5]))
        return float(rng.choice([6, 7]))
    if polarity == "pos":
        return float(rng.choice([4, 5, 5]))
    if polarity == "neg":
        return float(rng.choice([1, 2, 2]))
    return float(rng.choice([3, 3]))


def _compose_text(polarity: str, lang: str, rng: random.Random) -> str:
    """Compose aspect-rich, sometimes multi-sentence text for a polarity/lang."""
    if polarity == "pos":
        pool = _POSITIVE[lang]
    elif polarity == "neg":
        pool = _NEGATIVE[lang]
    else:
        pool = _NEUTRAL[lang]
    first = rng.choice(pool)
    # ~45% of the time append a second aspect sentence for richer, code-switched
    # content that exercises multi-aspect sentiment + decomposition.
    if rng.random() < 0.45:
        second = rng.choice(pool)
        if second != first:
            return f"{first} {second}"
    return first


def generate_forest_season_seed(seed: int = FOREST_SEASON_SEED) -> list:
    """Generate the deterministic ``RawSeedReview`` list for the resort.

    Returns a list of :class:`app.seed.sample_reviews.RawSeedReview`. Imported
    lazily to avoid a circular import (``sample_reviews`` imports this module).
    """
    from app.seed.sample_reviews import RawSeedReview

    rng = random.Random(seed)
    span_days = (_WINDOW_END - _WINDOW_START).days

    # Per-platform review volume (12 + 10 + 9 + 11 + 10 = 52 reviews total).
    volumes: dict[Platform, int] = {
        Platform.GOOGLE: 12,
        Platform.MAKEMYTRIP: 10,
        Platform.BOOKING: 9,
        Platform.TRIPADVISOR: 11,
        Platform.AGODA: 10,
    }
    # Short platform codes for stable, unique review ids.
    codes: dict[Platform, str] = {
        Platform.GOOGLE: "g",
        Platform.MAKEMYTRIP: "mmt",
        Platform.BOOKING: "bk",
        Platform.TRIPADVISOR: "ta",
        Platform.AGODA: "ag",
    }

    out: list = []
    author_i = 0
    for platform in _PLATFORMS:
        for n in range(volumes[platform]):
            # Polarity mix: mostly positive with a steady stream of negatives so
            # sentiment/aspect/changepoint have signal; a few neutrals.
            roll = rng.random()
            if roll < 0.58:
                polarity = "pos"
            elif roll < 0.88:
                polarity = "neg"
            else:
                polarity = "neu"
            lang = rng.choice(_LANGS)
            text = _compose_text(polarity, lang, rng)
            offset = rng.randint(0, span_days)
            review_date = _WINDOW_START + timedelta(days=offset)
            author = _AUTHORS[author_i % len(_AUTHORS)]
            author_i += 1
            # Roughly 1-in-6 records omit the source URL to exercise the
            # "source URL unavailable" path (Req 2.9).
            has_url = rng.random() >= (1 / 6)
            out.append(
                RawSeedReview(
                    platform=platform,
                    platform_review_id=f"{codes[platform]}-fs-{n + 1}",
                    property_id=FOREST_SEASON_ID,
                    display_name=author,
                    date=review_date.isoformat(),
                    native_rating=_native_rating(platform, polarity, rng),
                    text=text,
                    has_source_url=has_url,
                )
            )
    return out
