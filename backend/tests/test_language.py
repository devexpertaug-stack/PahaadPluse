"""Tests for language detection + transliteration (Req 4)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.models.review import Language, Script
from app.services.market_radar.language import (
    Transliterator,
    detect_language,
)

_T = Transliterator()


def test_english_detected() -> None:
    tag = detect_language("The room was very clean and the staff friendly")
    assert tag.language == Language.EN
    assert tag.script == Script.LATIN


def test_devanagari_detected_as_hi() -> None:
    tag = detect_language("कमरा बहुत अच्छा था")
    assert tag.language == Language.HI
    assert tag.script == Script.DEVANAGARI


def test_romanised_hindi_detected_as_hi_latn() -> None:
    tag = detect_language("kamra bahut accha tha staff saaf nahi")
    assert tag.language == Language.HI_LATN
    assert tag.script == Script.LATIN


def test_below_threshold_stays_english() -> None:
    tag = detect_language("The breakfast and the view were excellent overall")
    assert tag.language == Language.EN


def test_empty_and_emoji_only_are_und() -> None:
    assert detect_language("").language == Language.UND
    assert detect_language("   ").language == Language.UND
    assert detect_language("😀😀 123 !!!").language == Language.UND


def test_transliteration_leaves_passthrough_tokens_unchanged() -> None:
    text = "visit www.hotel.com or mail info@hotel.com 100% done 😀"
    out = _T.roman_to_devanagari(text)
    assert "www.hotel.com" in out
    assert "info@hotel.com" in out
    assert "100%" in out
    assert "😀" in out


# ---- property test: supported-charset Devanagari round trip (Req 4.6) ----

_CONSONANTS = [
    "क", "ख", "ग", "च", "ज", "ट", "त", "द", "न", "प",
    "ब", "म", "र", "ल", "व", "स", "ह", "फ़", "ज़",
]
_MATRAS = ["", "ा", "ि", "ी", "ु", "ू", "े", "ै", "ो", "ौ"]


@st.composite
def _devanagari_word(draw: st.DrawFn) -> str:
    length = draw(st.integers(min_value=1, max_value=5))
    syllables = []
    for _ in range(length):
        cons = draw(st.sampled_from(_CONSONANTS))
        matra = draw(st.sampled_from(_MATRAS))
        syllables.append(cons + matra)
    return "".join(syllables)


@given(word=_devanagari_word())
def test_devanagari_roman_devanagari_identity(word: str) -> None:
    roman = _T.devanagari_to_roman(word)
    back = _T.roman_to_devanagari(roman)
    assert back == word
