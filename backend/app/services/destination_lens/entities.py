"""Place-entity extraction for the Destination Lens (Req 14.1).

Deterministic, dependency-free extraction of place names from review text,
covering English, romanised-Hindi (Hinglish) and Devanagari forms. Each
extracted entity carries the issue themes present in the surrounding text so a
mention can be bucketed into the destination heatmap.

The theme vocabulary is intentionally small and offline: traffic, parking,
water, garbage, road condition and safety (Req 14.3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Known place names -> canonical gazetteer key (matches geocoder gazetteer).
# Includes Devanagari + common romanised spellings so Hinglish/Hindi reviews
# resolve to the same canonical landmark.
PLACE_ALIASES: dict[str, str] = {
    "mussoorie": "mussoorie",
    "मसूरी": "mussoorie",
    "mall road": "mall road",
    "mallroad": "mall road",
    "the mall": "mall road",
    "माल रोड": "mall road",
    "gun hill": "gun hill",
    "गन हिल": "gun hill",
    "kempty falls": "kempty falls",
    "kempty": "kempty falls",
    "केम्प्टी फॉल": "kempty falls",
    "landour": "landour",
    "लंढौर": "landour",
    "camel's back road": "camel's back road",
    "camels back": "camel's back road",
    "camel back road": "camel's back road",
    "कैमल बैक रोड": "camel's back road",
    "dehradun": "dehradun",
    "देहरादून": "dehradun",
    "nainital": "nainital",
    "नैनीताल": "nainital",
    "rishikesh": "rishikesh",
    "ऋषिकेश": "rishikesh",
    "haridwar": "haridwar",
    "हरिद्वार": "haridwar",
    "almora": "almora",
    "अल्मोड़ा": "almora",
    "ranikhet": "ranikhet",
    "रानीखेत": "ranikhet",
}

# Theme -> trigger terms (English + Hinglish + Devanagari).
THEME_CUES: dict[str, frozenset[str]] = {
    "traffic": frozenset(
        {"traffic", "jam", "congestion", "jaam", "bheed", "ट्रैफिक", "जाम", "भीड़"}
    ),
    "parking": frozenset(
        {"parking", "park", "parked", "parking space", "पार्किंग"}
    ),
    "water": frozenset(
        {"water", "pani", "paani", "supply", "shortage", "tap", "पानी", "जल"}
    ),
    "garbage": frozenset(
        {"garbage", "trash", "litter", "waste", "kooda", "kuda", "gandagi",
         "कूड़ा", "गंदगी", "कचरा"}
    ),
    "road condition": frozenset(
        {"pothole", "potholes", "road", "broken road", "gaddha", "gaddhe",
         "sadak", "सड़क", "गड्ढा", "गड्ढे"}
    ),
    "safety": frozenset(
        {"unsafe", "safety", "theft", "robbery", "harassment", "danger",
         "dangerous", "asurakshit", "chori", "असुरक्षित", "चोरी", "खतरा"}
    ),
}

THEMES: tuple[str, ...] = tuple(THEME_CUES.keys())

# Light negative lexicon reused to decide whether a mention is "negative".
_NEGATIVE_TERMS = frozenset(
    {
        "bad", "dirty", "poor", "terrible", "awful", "worst", "overflowing",
        "broken", "unsafe", "danger", "dangerous", "shortage", "no", "lack",
        "problem", "issue", "kharab", "ganda", "gandagi", "bakwaas", "nahi",
        "nahin", "pareshan", "खराब", "गंदा", "गंदगी", "समस्या", "नहीं",
    }
)

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass
class PlaceEntity:
    """A place entity extracted from review text (Req 14.1)."""

    surface: str  # the literal matched text
    canonical: str  # gazetteer key
    themes: list[str] = field(default_factory=list)
    is_negative: bool = False


def _themes_in_text(lower_text: str) -> list[str]:
    found: list[str] = []
    for theme, cues in THEME_CUES.items():
        if any(cue in lower_text for cue in cues):
            found.append(theme)
    return found


def _is_negative(lower_text: str) -> bool:
    tokens = {t.lower() for t in _TOKEN_RE.findall(lower_text)}
    if tokens & _NEGATIVE_TERMS:
        return True
    # Devanagari / phrase-level negatives captured by substring.
    return any(term in lower_text for term in _NEGATIVE_TERMS if not term.isascii())


def extract_place_entities(text: str) -> list[PlaceEntity]:
    """Extract place entities + their issue themes from ``text`` (Req 14.1)."""
    if not text or not text.strip():
        return []
    lower = text.lower()
    themes = _themes_in_text(lower)
    negative = _is_negative(lower)

    found: dict[str, PlaceEntity] = {}
    # Match longer aliases first so "mall road" wins over a bare "road".
    for alias in sorted(PLACE_ALIASES, key=len, reverse=True):
        if alias in lower:
            canonical = PLACE_ALIASES[alias]
            if canonical not in found:
                found[canonical] = PlaceEntity(
                    surface=alias,
                    canonical=canonical,
                    themes=list(themes),
                    is_negative=negative,
                )
    return list(found.values())
