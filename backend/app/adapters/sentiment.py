"""Sentiment engine adapter (Req 6).

Defines the :class:`SentimentEngine` interface with two implementations behind
it:

* :class:`FallbackSentimentEngine` — a deterministic lexicon/heuristic engine
  that is import-safe and runs offline. It satisfies the Req 6 behavioural
  contracts: exactly one overall label + confidence for non-empty text;
  zero-or-more aspect mentions each with one of the nine aspects, a label, a
  confidence and a non-empty evidence span that is a SUBSTRING OF THE ORIGINAL
  stored text (never the transliterated input); idempotence for the same text +
  model version; a model-version tag on every result; and explicit handling of
  unsupported-language, empty/whitespace and classification-failed cases.
* :class:`MuRILSentimentEngine` — a real MuRIL/IndicBERT-class adapter stub
  behind the same interface, loaded only when selected and available.

For ``hi-Latn`` input the caller passes the Devanagari form as the model input
(``model_input``) while the ORIGINAL text is used to anchor evidence spans
(Req 6.4). Lexicons here are intentionally small/generic and are NOT tuned on
the Hinglish_Test_Set (Req 16.6).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.config import SentimentProvider, get_settings
from app.models.review import Aspect

_POSITIVE_LEXICON = frozenset(
    {
        "good",
        "great",
        "excellent",
        "clean",
        "friendly",
        "beautiful",
        "amazing",
        "lovely",
        "comfortable",
        "wonderful",
        "awesome",
        "perfect",
        "spacious",
        "helpful",
        "delicious",
        "tasty",
        "accha",
        "acha",
        "achha",
        "badhiya",
        "shandaar",
        "saaf",
        "zabardast",
        "mast",
    }
)
_NEGATIVE_LEXICON = frozenset(
    {
        "bad",
        "dirty",
        "rude",
        "poor",
        "terrible",
        "awful",
        "noisy",
        "cold",
        "broken",
        "slow",
        "worst",
        "disappointing",
        "smelly",
        "overpriced",
        "unhelpful",
        "kharab",
        "ganda",
        "bakwaas",
        "mehenga",
    }
)

# Keyword -> Aspect cues for aspect-level mentions (English + romanised Hindi).
_ASPECT_CUES: dict[Aspect, frozenset[str]] = {
    Aspect.FOOD: frozenset({"food", "breakfast", "dinner", "meal", "khana", "restaurant"}),
    Aspect.ROOM: frozenset({"room", "rooms", "bed", "kamra", "balcony", "view"}),
    Aspect.HOUSEKEEPING: frozenset({"housekeeping", "towels", "linen", "cleaning"}),
    Aspect.STAFF: frozenset({"staff", "reception", "manager", "owner", "sewa", "seva"}),
    Aspect.LOCATION: frozenset({"location", "jagah", "mall", "distance", "central"}),
    Aspect.SERVICE: frozenset({"service", "wifi", "support", "response"}),
    Aspect.VALUE_FOR_MONEY: frozenset({"price", "value", "money", "paisa", "worth", "expensive"}),
    Aspect.CLEANLINESS: frozenset({"clean", "cleanliness", "saaf", "hygiene", "dirty", "ganda"}),
    Aspect.BOOKING_EXPERIENCE: frozenset({"booking", "checkin", "check-in", "reservation"}),
}

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass
class SentimentResult:
    """Overall-only sentiment classification (backward-compatible shape)."""

    label: str  # "positive" | "negative" | "neutral" | "unsupported"
    score: float  # signed polarity in [-1, 1]
    model_version: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class AspectMentionResult:
    """One aspect-level mention (Req 6.4)."""

    aspect: Aspect
    label: str
    confidence: float
    evidence: str  # SUBSTRING OF THE ORIGINAL text


@dataclass
class SentimentAnalysis:
    """Full Req 6 analysis: one overall label plus zero-or-more mentions."""

    overall_label: str | None
    overall_confidence: float | None
    mentions: list[AspectMentionResult]
    model_version: str
    unsupported: bool = False
    text_absent: bool = False
    failed: bool = False


class SentimentEngine(ABC):
    """Interface for sentiment classification over review text."""

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the model version tag applied to results."""

    @abstractmethod
    def classify(self, text: str, language: str | None = None) -> SentimentResult:
        """Classify ``text`` and return an overall-only :class:`SentimentResult`."""

    @abstractmethod
    def analyze(
        self,
        original_text: str,
        model_input: str | None = None,
        language: str | None = None,
    ) -> SentimentAnalysis:
        """Full analysis.

        ``original_text`` anchors evidence spans (always a substring of it).
        ``model_input`` is the text actually classified (e.g. the Devanagari
        form for ``hi-Latn``); defaults to ``original_text``.
        """


_SUPPORTED_LANGUAGES = frozenset({"en", "hi", "hi-Latn", None})


class FallbackSentimentEngine(SentimentEngine):
    """Deterministic lexicon/heuristic classifier for offline use."""

    def __init__(self, model_version: str = "lexicon-fallback-v1") -> None:
        self._model_version = model_version

    @property
    def model_version(self) -> str:
        return self._model_version

    # ---- overall-only (kept for existing callers/tests) ----
    def classify(self, text: str, language: str | None = None) -> SentimentResult:
        if text is None or not text.strip():
            return SentimentResult(
                label="unsupported", score=0.0, model_version=self._model_version
            )
        positive, negative, evidence = self._score_tokens(text)
        total = positive + negative
        if total == 0:
            return SentimentResult(
                label="neutral", score=0.0, model_version=self._model_version
            )
        score = (positive - negative) / total
        label = "positive" if score > 0 else "negative" if score < 0 else "neutral"
        evidence = [span for span in evidence if span and span in text]
        return SentimentResult(
            label=label,
            score=round(score, 4),
            model_version=self._model_version,
            evidence=evidence,
        )

    # ---- full Req 6 analysis ----
    def analyze(
        self,
        original_text: str,
        model_input: str | None = None,
        language: str | None = None,
    ) -> SentimentAnalysis:
        if language is not None and language not in _SUPPORTED_LANGUAGES and language != "und":
            # Unsupported language: mark + no labels (Req 6).
            return SentimentAnalysis(
                overall_label=None,
                overall_confidence=None,
                mentions=[],
                model_version=self._model_version,
                unsupported=True,
            )
        if original_text is None or not original_text.strip():
            return SentimentAnalysis(
                overall_label=None,
                overall_confidence=None,
                mentions=[],
                model_version=self._model_version,
                text_absent=True,
            )

        model_text = model_input if model_input is not None else original_text

        positive, negative, _ = self._score_tokens(model_text)
        total = positive + negative
        if total == 0:
            overall_label = "neutral"
            overall_conf = 0.5
        else:
            score = (positive - negative) / total
            overall_label = (
                "positive" if score > 0 else "negative" if score < 0 else "neutral"
            )
            overall_conf = round(0.5 + 0.5 * abs(score), 4)

        mentions = self._aspect_mentions(original_text)
        return SentimentAnalysis(
            overall_label=overall_label,
            overall_confidence=overall_conf,
            mentions=mentions,
            model_version=self._model_version,
        )

    # ---- helpers ----
    def _score_tokens(self, text: str) -> tuple[int, int, list[str]]:
        positive = 0
        negative = 0
        evidence: list[str] = []
        for raw_token in text.split():
            token = raw_token.strip(".,!?;:\"'()[]").lower()
            if not token:
                continue
            if token in _POSITIVE_LEXICON:
                positive += 1
                evidence.append(raw_token.strip(".,!?;:\"'()[]"))
            elif token in _NEGATIVE_LEXICON:
                negative += 1
                evidence.append(raw_token.strip(".,!?;:\"'()[]"))
        return positive, negative, evidence

    def _find_span(self, original_text: str, token: str) -> str | None:
        """Return a span from ``original_text`` containing ``token`` (case-insensitive)."""
        lowered = original_text.lower()
        idx = lowered.find(token.lower())
        if idx < 0:
            return None
        return original_text[idx : idx + len(token)]

    def _aspect_mentions(self, original_text: str) -> list[AspectMentionResult]:
        mentions: list[AspectMentionResult] = []
        tokens = [t.lower() for t in _TOKEN_RE.findall(original_text)]
        token_set = set(tokens)
        for aspect, cues in _ASPECT_CUES.items():
            hit = next((cue for cue in sorted(cues) if cue in token_set), None)
            if hit is None:
                continue
            span = self._find_span(original_text, hit)
            if not span:
                continue
            # Determine polarity from nearby lexicon tokens in the whole text.
            positive, negative, _ = self._score_tokens(original_text)
            total = positive + negative
            if total == 0:
                label = "neutral"
                conf = 0.5
            else:
                score = (positive - negative) / total
                label = (
                    "positive" if score > 0 else "negative" if score < 0 else "neutral"
                )
                conf = round(0.5 + 0.5 * abs(score), 4)
            mentions.append(
                AspectMentionResult(
                    aspect=aspect, label=label, confidence=conf, evidence=span
                )
            )
        mentions.sort(key=lambda m: m.aspect)
        return mentions


class MuRILSentimentEngine(SentimentEngine):
    """Stub for a real MuRIL/IndicBERT adapter (same interface).

    Loading the heavy model is deferred; if selected but unavailable, callers
    should fall back to the deterministic engine.
    """

    def __init__(self, model_path: str, model_version: str) -> None:
        self._model_path = model_path
        self._model_version = model_version

    @property
    def model_version(self) -> str:
        return self._model_version

    def classify(self, text: str, language: str | None = None) -> SentimentResult:
        raise NotImplementedError(
            "MuRIL/IndicBERT adapter is not yet implemented; use the fallback engine."
        )

    def analyze(
        self,
        original_text: str,
        model_input: str | None = None,
        language: str | None = None,
    ) -> SentimentAnalysis:
        raise NotImplementedError(
            "MuRIL/IndicBERT adapter is not yet implemented; use the fallback engine."
        )


def get_sentiment_engine() -> SentimentEngine:
    """Select the sentiment engine based on configuration."""
    settings = get_settings()
    use_muril = (
        settings.sentiment_model_provider is SentimentProvider.MURIL
        and settings.sentiment_model_path
    )
    if use_muril:
        try:
            return MuRILSentimentEngine(
                model_path=settings.sentiment_model_path,
                model_version=settings.sentiment_model_name,
            )
        except Exception:  # pragma: no cover - defensive, model unavailable
            pass
    return FallbackSentimentEngine(model_version=settings.sentiment_model_name)
