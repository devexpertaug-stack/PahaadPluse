"""Deterministic analytics dataset for the Market Radar Deep features.

The checked-in sample dataset (``app.seed.sample_reviews``) is intentionally
small (one review per property/platform) and has no time depth, so it cannot
drive the time-series, Bayesian decomposition, changepoint, what-if, time
machine, playbook or gap-finder features on its own.

This module synthesises a *deterministic*, seed-reproducible panel of
``Aspect_Mention`` observations across the six-property Mussoorie cluster, all
five platforms and a configurable window of recent calendar months (default
18). Each generated mention is a lightweight :class:`MentionObservation` with a
property, platform, aspect, review date (IST), sentiment label and an evidence
quote + source URL, so every displayed number stays traceable to a record
(Req 27 spirit).

The generator deliberately injects:

* a market-wide seasonal signal shared across the cluster (so the Bayesian
  decomposition has a market-wide effect to recover),
* per-property offsets (so there is a property-specific effect),
* a clear negative trend / changepoint on one property-aspect (so BOCPD and the
  Time Machine have something real to find),
* a cluster-leader with consistently praised themes (for the Playbook), and
* a cluster-wide weak aspect where most properties run negative (for the Gap
  Finder).

Being pure + seeded keeps every downstream analytic (and the benchmark's
idempotence contract, Req 16.8) reproducible.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.models.review import Aspect, Platform, SentimentLabel
from app.seed.sample_reviews import PROPERTIES

IST = ZoneInfo("Asia/Kolkata")

# The Home_Property whose managers get changepoint notifications (Req 9.4) and
# whose lagging aspects drive the Playbook (Req 12).
HOME_PROPERTY_ID = "mus-forestseason"
# A strong competitor used as the Cluster_Leader fallback in tests/fixtures.
LEADER_PROPERTY_ID = "mus-cloudvalley"

DEFAULT_MONTHS = 18
DEFAULT_SEED = 20240601

_URL_PATTERN: dict[Platform, str] = {
    Platform.GOOGLE: "https://www.google.com/maps/place/{slug}-mussoorie",
    Platform.MAKEMYTRIP: "https://www.makemytrip.com/hotels/{slug}-mussoorie.html",
    Platform.BOOKING: "https://www.booking.com/hotel/in/{slug}-mussoorie.html",
    Platform.TRIPADVISOR: "https://www.tripadvisor.in/Hotel_Review-{slug}-mussoorie.html",
    Platform.AGODA: "https://www.agoda.com/{slug}-mussoorie/hotel/mussoorie-in.html",
}

# Short evidence quotes per aspect/polarity used for traceable mention quotes.
_QUOTES: dict[tuple[Aspect, SentimentLabel], list[str]] = {
    (Aspect.FOOD, SentimentLabel.POSITIVE): [
        "the breakfast was delicious and fresh",
        "khana badhiya tha, bahut swaad",
        "wonderful restaurant food every day",
    ],
    (Aspect.FOOD, SentimentLabel.NEGATIVE): [
        "the food was cold and bland",
        "khana kharab tha aur thanda",
        "breakfast variety was very limited",
    ],
    (Aspect.ROOM, SentimentLabel.POSITIVE): [
        "spacious room with a lovely valley view",
        "kamra saaf aur bada tha",
        "comfortable beds and a cosy room",
    ],
    (Aspect.ROOM, SentimentLabel.NEGATIVE): [
        "the room was cold and cramped",
        "kamra ganda aur chhota tha",
        "rooms felt damp and old",
    ],
    (Aspect.STAFF, SentimentLabel.POSITIVE): [
        "staff were warm and very helpful",
        "staff bahut accha aur madadgar",
        "friendly reception and attentive owners",
    ],
    (Aspect.STAFF, SentimentLabel.NEGATIVE): [
        "staff were rude and unhelpful",
        "staff ka vyavhaar kharab tha",
        "reception was slow to respond",
    ],
    (Aspect.CLEANLINESS, SentimentLabel.POSITIVE): [
        "spotless and very clean throughout",
        "sab kuch saaf suthra tha",
        "excellent cleanliness in every corner",
    ],
    (Aspect.CLEANLINESS, SentimentLabel.NEGATIVE): [
        "the bathroom was dirty on arrival",
        "safai bilkul theek nahi thi",
        "housekeeping missed the room twice",
    ],
    (Aspect.SERVICE, SentimentLabel.POSITIVE): [
        "service was prompt and professional",
        "service badhiya aur fast thi",
        "quick wifi help and great service",
    ],
    (Aspect.SERVICE, SentimentLabel.NEGATIVE): [
        "service was slow and the wifi failed",
        "service bakwaas thi, wifi band",
        "no response to our service requests",
    ],
    (Aspect.LOCATION, SentimentLabel.POSITIVE): [
        "great location near the Mall Road",
        "jagah zabardast, mall road paas",
        "central and quiet location",
    ],
    (Aspect.LOCATION, SentimentLabel.NEGATIVE): [
        "the location is far from everything",
        "jagah bahut door thi",
        "hard to reach, poor location",
    ],
    (Aspect.VALUE_FOR_MONEY, SentimentLabel.POSITIVE): [
        "great value for the price paid",
        "paisa vasool jagah hai",
        "good value, worth every rupee",
    ],
    (Aspect.VALUE_FOR_MONEY, SentimentLabel.NEGATIVE): [
        "overpriced for what you get",
        "bahut mehenga tha, paisa barbaad",
        "poor value for money",
    ],
    (Aspect.HOUSEKEEPING, SentimentLabel.POSITIVE): [
        "housekeeping was thorough and daily",
        "housekeeping roz accha tha",
        "fresh towels and tidy rooms daily",
    ],
    (Aspect.HOUSEKEEPING, SentimentLabel.NEGATIVE): [
        "housekeeping skipped our room",
        "housekeeping theek se nahi hui",
        "towels were not changed for days",
    ],
    (Aspect.BOOKING_EXPERIENCE, SentimentLabel.POSITIVE): [
        "smooth booking and easy check-in",
        "booking aur check-in aasaan tha",
        "effortless reservation process",
    ],
    (Aspect.BOOKING_EXPERIENCE, SentimentLabel.NEGATIVE): [
        "the booking process kept failing",
        "booking process bahut slow tha",
        "check-in was confusing and slow",
    ],
}

ALL_ASPECTS: tuple[Aspect, ...] = tuple(Aspect)
ALL_PLATFORMS: tuple[Platform, ...] = tuple(Platform)


@dataclass(frozen=True)
class MentionObservation:
    """A single aspect-level mention observation on the analytics panel."""

    property_id: str
    property_name: str
    platform: Platform
    aspect: Aspect
    date: date
    label: SentimentLabel
    evidence: str
    text: str
    source_url: str | None


def _slug(property_id: str) -> str:
    return property_id.replace("mus-", "")


def month_starts(months: int, today: date) -> list[date]:
    """Return the first-of-month dates for the most recent ``months`` months.

    Ordered oldest -> newest, ending with the month containing ``today``.
    """
    y, m = today.year, today.month
    starts: list[date] = []
    for back in range(months - 1, -1, -1):
        total = (y * 12 + (m - 1)) - back
        yy, mm = divmod(total, 12)
        starts.append(date(yy, mm + 1, 1))
    return starts


def _base_positive_rate(property_id: str, aspect: Aspect) -> float:
    """Baseline positive share for a property/aspect before trend + noise.

    Encodes the fixtures the Deep features rely on: a clear cluster leader, a
    declining Home_Property aspect, and a cluster-wide weak aspect.
    """
    # Cluster-wide weak aspect: almost everyone runs negative on Service.
    if aspect is Aspect.SERVICE:
        base = 0.30
    elif aspect is Aspect.VALUE_FOR_MONEY:
        base = 0.45
    else:
        base = 0.62

    # Property personalities (property-specific effect).
    personality = {
        "mus-forestseason": 0.08,  # the Home_Property (generally well-liked)
        "mus-pineview": 0.05,
        "mus-deodarresidency": 0.0,
        "mus-cloudvalley": 0.18,  # the leader
        "mus-himalayanook": 0.02,
        "mus-mallroadlodge": -0.08,
        "mus-camelsback": 0.06,
    }.get(property_id, 0.0)

    # Leader is especially strong on Food + Staff (praised themes for Playbook).
    if property_id == LEADER_PROPERTY_ID and aspect in (Aspect.FOOD, Aspect.STAFF):
        personality += 0.12

    return max(0.05, min(0.95, base + personality))


def _trend(property_id: str, aspect: Aspect, month_index: int, total_months: int) -> float:
    """Additive trend applied to the positive share over time.

    Injects a sharp decline on the Home_Property's Food aspect roughly 6 months
    before the end of the window so BOCPD + the Time Machine have a real decline
    changepoint to detect.
    """
    if property_id == HOME_PROPERTY_ID and aspect is Aspect.FOOD:
        breakpoint = total_months - 6
        if month_index >= breakpoint:
            return -0.40
    return 0.0


@lru_cache(maxsize=8)
def generate_observations(
    months: int = DEFAULT_MONTHS,
    seed: int = DEFAULT_SEED,
    today_iso: str | None = None,
) -> tuple[MentionObservation, ...]:
    """Generate the deterministic mention panel (cached per args)."""
    today = date.fromisoformat(today_iso) if today_iso else date(2024, 6, 15)
    rng = random.Random(seed)
    prop_names = {p.property_id: p.name for p in PROPERTIES}
    starts = month_starts(months, today)
    out: list[MentionObservation] = []

    for prop in PROPERTIES:
        for platform in ALL_PLATFORMS:
            for aspect in ALL_ASPECTS:
                for mi, start in enumerate(starts):
                    pos_rate = _base_positive_rate(prop.property_id, aspect)
                    pos_rate += _trend(prop.property_id, aspect, mi, months)
                    # Mild shared seasonal wobble (market-wide effect).
                    season = 0.05 * ((mi % 6) - 2.5) / 2.5
                    pos_rate = max(0.03, min(0.97, pos_rate + season))

                    # Volume: 3-6 mentions per property/platform/aspect/month.
                    volume = rng.randint(3, 6)
                    for _ in range(volume):
                        roll = rng.random()
                        if roll < pos_rate:
                            label = SentimentLabel.POSITIVE
                        elif roll < pos_rate + 0.18:
                            label = SentimentLabel.NEUTRAL
                        else:
                            label = SentimentLabel.NEGATIVE
                        day = 1 + rng.randint(0, 25)
                        obs_date = start + timedelta(days=day)
                        if obs_date > today:
                            obs_date = today
                        quote_label = (
                            SentimentLabel.POSITIVE
                            if label is SentimentLabel.POSITIVE
                            else SentimentLabel.NEGATIVE
                        )
                        quotes = _QUOTES[(aspect, quote_label)]
                        quote = quotes[rng.randrange(len(quotes))]
                        url = _URL_PATTERN[platform].format(slug=_slug(prop.property_id))
                        out.append(
                            MentionObservation(
                                property_id=prop.property_id,
                                property_name=prop_names[prop.property_id],
                                platform=platform,
                                aspect=aspect,
                                date=obs_date,
                                label=label,
                                evidence=quote,
                                text=quote,
                                source_url=url,
                            )
                        )
    return tuple(out)


def cluster_property_ids() -> list[str]:
    """Return the cluster's property ids in canonical order."""
    return [p.property_id for p in PROPERTIES]


def property_name(property_id: str) -> str:
    return {p.property_id: p.name for p in PROPERTIES}.get(property_id, property_id)
