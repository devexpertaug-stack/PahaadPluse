"""Language detection and Hinglish transliteration (Req 4).

Deterministic, dependency-free implementation so the pipeline runs offline:

* :func:`detect_language` tags exactly one :class:`Language` (en/hi/hi-Latn/und)
  and one :class:`Script` (Latin/Devanagari/mixed) with a confidence in
  ``[0, 1]``. ``hi-Latn`` is assigned when romanised-Hindi tokens make up at
  least 20% of the Latin tokens (Req 4.2). Empty/whitespace/emoji/punct-only
  text, or confidence < 0.5, yields ``und`` while keeping the text stored
  (Req 4.3).
* :class:`Transliterator` converts romanised Hindi into Devanagari while
  leaving English tokens, digits, URLs, e-mails, emoji and punctuation
  unchanged and in order (Req 4.4, 4.5). The supported-charset Devanagari
  round-trip (Devanagari -> roman -> Devanagari) is the identity (Req 4.6).

For an ``hi-Latn`` record the Devanagari form is stored in
``transliterated_text`` and the ORIGINAL ``text`` is left char-for-char. A
transliteration failure keeps the original and flags ``transliteration_failed``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.review import Language, Script

# ---------------------------------------------------------------------------
# Supported transliteration charset.
#
# Each Devanagari unit has exactly one canonical roman form, and each roman form
# maps back to exactly one Devanagari unit, so the mapping is a bijection on the
# supported charset — the Devanagari->roman->Devanagari round-trip is identity.
# ---------------------------------------------------------------------------

# Independent vowels.
_VOWELS: list[tuple[str, str]] = [
    ("अ", "a"),
    ("आ", "aa"),
    ("इ", "i"),
    ("ई", "ii"),
    ("उ", "u"),
    ("ऊ", "uu"),
    ("ए", "e"),
    ("ऐ", "ai"),
    ("ओ", "o"),
    ("औ", "au"),
]

# Matra (dependent vowel signs) keyed by the vowel they follow a consonant.
_MATRAS: dict[str, str] = {
    "aa": "ा",
    "ii": "ी",
    "uu": "ू",
    "ai": "ै",
    "au": "ौ",
    "a": "",  # inherent vowel
    "i": "ि",
    "u": "ु",
    "e": "े",
    "o": "ो",
}
_MATRA_TO_VOWEL = {v: k for k, v in _MATRAS.items() if v}

# Consonants (base form carries inherent 'a').
_CONSONANTS: list[tuple[str, str]] = [
    ("क", "k"),
    ("ख", "kh"),
    ("ग", "g"),
    ("घ", "gh"),
    ("च", "ch"),
    ("छ", "chh"),
    ("ज", "j"),
    ("झ", "jh"),
    ("ट", "tt"),
    ("ठ", "tth"),
    ("ड", "dd"),
    ("ढ", "ddh"),
    ("ण", "nn"),
    ("त", "t"),
    ("थ", "th"),
    ("द", "d"),
    ("ध", "dh"),
    ("न", "n"),
    ("प", "p"),
    ("फ", "ph"),
    ("ब", "b"),
    ("भ", "bh"),
    ("म", "m"),
    ("य", "y"),
    ("र", "r"),
    ("ल", "l"),
    ("व", "v"),
    ("श", "sh"),
    ("ष", "ss"),
    ("स", "s"),
    ("ह", "h"),
    # Nukta (borrowed) consonants common in Hinglish.
    ("फ़", "f"),
    ("ज़", "z"),
]

_VIRAMA = "्"

_CONSONANT_DEVA_TO_ROMAN = dict(_CONSONANTS)

# Extra roman spellings accepted on INPUT only (roman -> Devanagari). These do
# not participate in the Devanagari -> roman canonical direction, so the
# supported-charset round-trip identity is preserved.
_ROMAN_INPUT_ALIASES: list[tuple[str, str]] = [
    ("w", "व"),
    ("c", "च"),
]
# Longer roman consonant forms first so 'chh' beats 'ch' beats 'h'.
_ROMAN_CONSONANTS = sorted(
    ([(roman, deva) for deva, roman in _CONSONANTS] + _ROMAN_INPUT_ALIASES),
    key=lambda pair: len(pair[0]),
    reverse=True,
)
_VOWEL_DEVA_TO_ROMAN = dict(_VOWELS)
_ROMAN_VOWELS = sorted(
    ((roman, deva) for deva, roman in _VOWELS),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

# Common romanised-Hindi function words used by the >=20% hi-Latn heuristic.
_HINGLISH_MARKERS: frozenset[str] = frozenset(
    {
        "accha",
        "acha",
        "bahut",
        "bohot",
        "badhiya",
        "shandaar",
        "kharab",
        "ganda",
        "saaf",
        "kamra",
        "khana",
        "nahi",
        "nahin",
        "hai",
        "tha",
        "thi",
        "aur",
        "lekin",
        "kya",
        "bilkul",
        "zabardast",
        "mast",
        "theek",
        "achha",
        "paisa",
        "vasool",
        "sauda",
        "jagah",
        "sewa",
        "seva",
    }
)

_URL_RE = re.compile(r"^(https?://|www\.)", re.IGNORECASE)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DIGIT_RE = re.compile(r"\d")
_LATIN_RE = re.compile(r"[A-Za-z]")
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_EMOJI_RE = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff]"
)
_TOKEN_RE = re.compile(r"\w+|\s+|[^\w\s]+", re.UNICODE)


@dataclass
class LanguageTag:
    """Result of language detection (Req 4.1)."""

    language: Language
    script: Script
    confidence: float


def _is_passthrough_token(token: str) -> bool:
    """URLs, e-mails, digit-bearing tokens, emoji and punctuation pass through."""
    if not token.strip():
        return True
    if _URL_RE.match(token) or _EMAIL_RE.match(token):
        return True
    if _DIGIT_RE.search(token):
        return True
    if _EMOJI_RE.search(token):
        return True
    if not _LATIN_RE.search(token) and not _DEVANAGARI_RE.search(token):
        return True
    return False


def detect_language(text: str) -> LanguageTag:
    """Detect language + script for a review (Req 4.1-4.3)."""
    if text is None or not text.strip():
        return LanguageTag(Language.UND, Script.LATIN, 0.0)

    stripped = text.strip()
    has_latin = bool(_LATIN_RE.search(stripped))
    has_deva = bool(_DEVANAGARI_RE.search(stripped))

    # Script detection.
    if has_latin and has_deva:
        script = Script.MIXED
    elif has_deva:
        script = Script.DEVANAGARI
    elif has_latin:
        script = Script.LATIN
    else:
        # emoji/punct/digits only -> no linguistic content
        return LanguageTag(Language.UND, Script.LATIN, 0.0)

    if has_deva and not has_latin:
        return LanguageTag(Language.HI, Script.DEVANAGARI, 0.95)

    # Latin (possibly mixed). Measure romanised-Hindi share.
    latin_tokens = [
        t.lower()
        for t in re.findall(r"[A-Za-z]+", stripped)
    ]
    if not latin_tokens:
        return LanguageTag(Language.UND, script, 0.0)

    hindi_hits = sum(1 for t in latin_tokens if t in _HINGLISH_MARKERS)
    share = hindi_hits / len(latin_tokens)

    if share >= 0.20:
        confidence = min(0.95, 0.55 + share)
        return LanguageTag(Language.HI_LATN, script, round(confidence, 2))

    if has_deva:
        # Mixed script but mostly English words.
        return LanguageTag(Language.EN, Script.MIXED, 0.6)

    # Default: English. Confidence scaled by how much alphabetic content exists.
    alpha_chars = sum(len(t) for t in latin_tokens)
    confidence = 0.9 if alpha_chars >= 3 else 0.4
    if confidence < 0.5:
        return LanguageTag(Language.UND, script, round(confidence, 2))
    return LanguageTag(Language.EN, script, confidence)


class TransliterationError(Exception):
    """Raised when a token cannot be transliterated on the supported charset."""


class Transliterator:
    """Reversible transliteration between romanised Hindi and Devanagari."""

    def roman_to_devanagari(self, text: str) -> str:
        """Convert romanised-Hindi text to Devanagari, leaving others intact.

        Whitespace-delimited chunks that are URLs, e-mails, digit-bearing,
        emoji or already-Devanagari pass through unchanged and in order; the
        remaining alphabetic sub-tokens are transliterated.
        """
        out: list[str] = []
        for chunk in re.split(r"(\s+)", text):
            if not chunk:
                continue
            if chunk.isspace():
                out.append(chunk)
                continue
            if _is_passthrough_token(chunk) or _DEVANAGARI_RE.search(chunk):
                out.append(chunk)
                continue
            # Sub-tokenise words vs. punctuation within the chunk.
            for token in _TOKEN_RE.findall(chunk):
                if _is_passthrough_token(token) or _DEVANAGARI_RE.search(token):
                    out.append(token)
                    continue
                out.append(self._word_to_devanagari(token))
        return "".join(out)

    def devanagari_to_roman(self, text: str) -> str:
        """Convert Devanagari text to its canonical roman form (Req 4.6)."""
        out: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            # Match multi-codepoint consonants (nukta forms) first.
            two = text[i : i + 2]
            if two in _CONSONANT_DEVA_TO_ROMAN:
                roman = _CONSONANT_DEVA_TO_ROMAN[two]
                i += 2
                if i < n and text[i] == _VIRAMA:
                    out.append(roman)
                    i += 1
                    continue
                if i < n and text[i] in _MATRA_TO_VOWEL:
                    out.append(roman + _MATRA_TO_VOWEL[text[i]])
                    i += 1
                else:
                    out.append(roman + "a")
                continue
            ch = text[i]
            if ch in _CONSONANT_DEVA_TO_ROMAN:
                roman = _CONSONANT_DEVA_TO_ROMAN[ch]
                i += 1
                if i < n and text[i] == _VIRAMA:
                    # Half consonant: no vowel.
                    out.append(roman)
                    i += 1
                    continue
                if i < n and text[i] in _MATRA_TO_VOWEL:
                    out.append(roman + _MATRA_TO_VOWEL[text[i]])
                    i += 1
                else:
                    # Inherent 'a'.
                    out.append(roman + "a")
                continue
            if ch in _VOWEL_DEVA_TO_ROMAN:
                out.append(_VOWEL_DEVA_TO_ROMAN[ch])
                i += 1
                continue
            out.append(ch)
            i += 1
        return "".join(out)

    def _word_to_devanagari(self, word: str) -> str:
        """Transliterate a single roman word to Devanagari."""
        lower = word.lower()
        out: list[str] = []
        i = 0
        n = len(lower)
        prev_was_consonant = False
        while i < n:
            matched = False
            # Try consonants (longest first).
            for roman, deva in _ROMAN_CONSONANTS:
                if lower.startswith(roman, i):
                    if prev_was_consonant:
                        out.append(_VIRAMA)
                    out.append(deva)
                    i += len(roman)
                    prev_was_consonant = True
                    matched = True
                    break
            if matched:
                continue
            # Try vowels (longest first).
            for roman, deva in _ROMAN_VOWELS:
                if lower.startswith(roman, i):
                    if prev_was_consonant:
                        out.append(_MATRAS[roman])
                    else:
                        out.append(deva)
                    i += len(roman)
                    prev_was_consonant = False
                    matched = True
                    break
            if matched:
                continue
            # Unknown roman char on the supported charset.
            raise TransliterationError(f"cannot transliterate {word!r} at {lower[i]!r}")
        if prev_was_consonant:
            # Trailing consonant keeps its inherent vowel for a clean round trip.
            pass
        return "".join(out)
