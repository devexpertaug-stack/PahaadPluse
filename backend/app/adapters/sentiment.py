"""Sentiment engine adapter.

Defines the :class:`SentimentEngine` interface and a deterministic
lexicon/heuristic fallback that is import-safe and testable offline. A real
MuRIL/IndicBERT adapter is stubbed behind the same interface and only loaded if
selected and available.

The fallback honours the spec's behavioural contracts that are cheap to satisfy
now: it is idempotent, tags a model version, returns evidence spans that are
substrings of the ORIGINAL text, and handles unsupported/empty input. Later
features flesh out multilingual handling and calibration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.config import SentimentProvider, get_settings

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
        "accha",
        "badhiya",
        "shandaar",
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
        "kharab",
        "ganda",
        "bakwaas",
    }
)


@dataclass
class SentimentResult:
    """Result of a sentiment classification."""

    label: str  # "positive" | "negative" | "neutral" | "unsupported"
    score: float  # signed polarity in [-1, 1]
    model_version: str
    evidence: list[str] = field(default_factory=list)


class SentimentEngine(ABC):
    """Interface for sentiment classification over review text."""

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the model version tag applied to results."""

    @abstractmethod
    def classify(self, text: str, language: str | None = None) -> SentimentResult:
        """Classify ``text`` and return a :class:`SentimentResult`."""


class FallbackSentimentEngine(SentimentEngine):
    """Deterministic lexicon/heuristic classifier for offline use."""

    def __init__(self, model_version: str = "lexicon-fallback-v1") -> None:
        self._model_version = model_version

    @property
    def model_version(self) -> str:
        return self._model_version

    def classify(self, text: str, language: str | None = None) -> SentimentResult:
        if text is None or not text.strip():
            return SentimentResult(
                label="unsupported", score=0.0, model_version=self._model_version
            )

        evidence: list[str] = []
        positive = 0
        negative = 0
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

        total = positive + negative
        if total == 0:
            return SentimentResult(
                label="neutral", score=0.0, model_version=self._model_version
            )

        score = (positive - negative) / total
        if score > 0:
            label = "positive"
        elif score < 0:
            label = "negative"
        else:
            label = "neutral"

        # Evidence spans must be substrings of the ORIGINAL text.
        evidence = [span for span in evidence if span and span in text]
        return SentimentResult(
            label=label,
            score=round(score, 4),
            model_version=self._model_version,
            evidence=evidence,
        )


class MuRILSentimentEngine(SentimentEngine):
    """Stub for a real MuRIL/IndicBERT adapter (same interface).

    Loading the heavy model is deferred to a later feature. If selected but the
    model is unavailable, callers should fall back to the deterministic engine.
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
