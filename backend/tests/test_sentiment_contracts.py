"""Behavioural-contract tests for the Sentiment_Engine (Req 6)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.adapters.sentiment import FallbackSentimentEngine, get_sentiment_engine
from app.services.market_radar.language import Transliterator

_ENGINE = FallbackSentimentEngine()
_T = Transliterator()


def test_overall_label_and_confidence_for_non_empty_text() -> None:
    a = _ENGINE.analyze("The room was clean and the staff were friendly")
    assert a.overall_label == "positive"
    assert 0.0 <= a.overall_confidence <= 1.0
    assert a.model_version


def test_aspect_mentions_have_valid_fields() -> None:
    text = "The food was delicious but the room was dirty and noisy"
    a = _ENGINE.analyze(text)
    assert a.mentions
    for m in a.mentions:
        assert 0.0 <= m.confidence <= 1.0
        assert m.evidence and m.evidence in text


def test_evidence_spans_are_substrings_of_original_not_transliterated() -> None:
    # hi-Latn: original stays roman, model input is Devanagari.
    original = "kamra saaf tha staff accha"
    model_input = _T.roman_to_devanagari(original)
    a = _ENGINE.analyze(original_text=original, model_input=model_input, language="hi-Latn")
    for m in a.mentions:
        assert m.evidence in original  # NOT in the Devanagari model input


def test_idempotence_same_text_same_version() -> None:
    text = "Clean rooms, friendly staff, great location, poor wifi"
    first = _ENGINE.analyze(text)
    second = _ENGINE.analyze(text)
    assert first == second


def test_unsupported_language_marks_and_no_labels() -> None:
    a = _ENGINE.analyze("bonjour la chambre", language="fr")
    assert a.unsupported is True
    assert a.overall_label is None
    assert a.mentions == []


def test_empty_text_is_text_absent() -> None:
    a = _ENGINE.analyze("   ")
    assert a.text_absent is True
    assert a.overall_label is None


def test_model_version_recorded_everywhere() -> None:
    a = _ENGINE.analyze("great food and clean rooms")
    assert a.model_version == "lexicon-fallback-v1"


def test_default_engine_is_fallback() -> None:
    assert isinstance(get_sentiment_engine(), FallbackSentimentEngine)


@given(
    text=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Zs")),
        min_size=1,
        max_size=80,
    )
)
def test_idempotence_property(text: str) -> None:
    first = _ENGINE.analyze(text)
    second = _ENGINE.analyze(text)
    assert first == second
    for m in first.mentions:
        assert m.evidence in text
