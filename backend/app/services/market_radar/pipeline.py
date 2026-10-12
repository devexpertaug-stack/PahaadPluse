"""Enrichment pipeline tying language, aspects and sentiment onto a record.

Given a parsed :class:`~app.models.review.ReviewRecord`, :func:`enrich` runs
language detection + transliteration (Req 4), optional aspect normalisation
(Req 5) and the Sentiment_Engine (Req 6) and returns an updated record. Evidence
spans are anchored to the ORIGINAL ``text`` while the Devanagari form is used as
the model input for ``hi-Latn`` (Req 6.4).
"""

from __future__ import annotations

from app.adapters.sentiment import SentimentEngine, get_sentiment_engine
from app.models.review import (
    AspectMention,
    Language,
    ReviewRecord,
    SentimentLabel,
)
from app.services.market_radar.language import (
    TransliterationError,
    Transliterator,
    detect_language,
)

_transliterator = Transliterator()


def enrich(record: ReviewRecord, engine: SentimentEngine | None = None) -> ReviewRecord:
    """Return ``record`` enriched with language, transliteration and sentiment."""
    engine = engine or get_sentiment_engine()

    tag = detect_language(record.text)
    update: dict[str, object] = {
        "detected_language": tag.language.value,
        "script": tag.script.value,
        "detection_confidence": tag.confidence,
    }

    transliterated: str | None = None
    transliteration_failed = False
    if tag.language == Language.HI_LATN:
        try:
            transliterated = _transliterator.roman_to_devanagari(record.text)
        except TransliterationError:
            transliteration_failed = True
            transliterated = None
    update["transliterated_text"] = transliterated
    update["transliteration_failed"] = transliteration_failed

    model_input = transliterated if transliterated else record.text
    analysis = engine.analyze(
        original_text=record.text,
        model_input=model_input,
        language=tag.language.value,
    )
    update["sentiment_model_version"] = analysis.model_version
    update["sentiment_unsupported"] = analysis.unsupported
    update["sentiment_text_absent"] = analysis.text_absent
    update["sentiment_failed"] = analysis.failed

    if analysis.overall_label is not None:
        update["overall_sentiment"] = SentimentLabel(analysis.overall_label).value
        update["overall_sentiment_confidence"] = analysis.overall_confidence
        update["aspect_mentions"] = [
            AspectMention(
                aspect=m.aspect,
                label=SentimentLabel(m.label),
                confidence=m.confidence,
                evidence=m.evidence,
            )
            for m in analysis.mentions
        ]
    else:
        update["overall_sentiment"] = None
        update["overall_sentiment_confidence"] = None
        update["aspect_mentions"] = []

    return record.model_copy(update=update)
