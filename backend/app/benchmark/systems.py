"""Systems evaluated by the Hinglish benchmark (Req 16).

Three systems are compared on the held-out Hinglish_Test_Set:

1. ``SentimentEngineSystem`` — PahadPulse's own :class:`SentimentEngine`
   (the deterministic lexicon fallback by default; swappable for a real
   MuRIL/IndicBERT adapter behind the same interface).
2. ``GenericLexiconSystem`` — a generic, off-the-shelf-style English lexicon
   sentiment tool (a compact VADER-like word-list classifier). It stands in
   for a third-party tool that is not tuned for Hinglish, so its weakness on
   romanised Hindi is a fair, documented baseline.
3. ``PlainLLMBaselineSystem`` — a plain-LLM zero-shot baseline. Offline it uses
   a documented deterministic *mock* LLM (seeded template heuristic) behind the
   same prompt contract, so the baseline is reproducible without live
   credentials (Req 16 allows a documented mock/template baseline offline).

Every system exposes the same :meth:`predict` contract returning an overall
label plus a per-aspect label dict, so the harness can score all three
identically. None of them is tuned on the test set (Req 16.6).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.adapters.sentiment import SentimentEngine, get_sentiment_engine
from app.models.review import Aspect

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)

# Keyword cues to detect which aspects a review talks about (en + hi + hi-Latn).
_ASPECT_CUES: dict[Aspect, frozenset[str]] = {
    Aspect.FOOD: frozenset({"food", "khana", "breakfast", "dinner", "bhojan", "nashta"}),
    Aspect.ROOM: frozenset({"room", "kamra", "kamre", "bed", "balcony"}),
    Aspect.HOUSEKEEPING: frozenset({"housekeeping", "safai", "saaf-safai", "towels"}),
    Aspect.STAFF: frozenset({"staff", "karmchari", "reception", "owner", "maalik"}),
    Aspect.LOCATION: frozenset({"location", "jagah", "sthan", "mall", "door"}),
    Aspect.SERVICE: frozenset({"service", "seva", "sewa", "wifi", "turant", "sust"}),
    Aspect.VALUE_FOR_MONEY: frozenset(
        {"daam", "paisa", "value", "money", "mehenga", "faayda", "faydemand", "keemat"}
    ),
    Aspect.CLEANLINESS: frozenset({"cleanliness", "safai", "saaf", "dhool", "badboo", "gandagi"}),
    Aspect.BOOKING_EXPERIENCE: frozenset(
        {"booking", "check-in", "checkin", "reservation", "dikkat"}
    ),
}

# A tiny generic English sentiment word list (VADER-ish), deliberately NOT
# tuned for Hinglish so it is a fair generic baseline.
_GENERIC_POS = frozenset(
    {"good", "great", "excellent", "nice", "love", "wonderful", "clean", "comfortable", "best"}
)
_GENERIC_NEG = frozenset(
    {"bad", "poor", "terrible", "worst", "dirty", "rude", "slow", "noisy", "awful", "small"}
)

# Romanised-Hindi polarity cues used by the plain-LLM mock + the engine-agnostic
# detectors. Kept distinct from the Sentiment_Engine's tuning lexicon.
_HI_POS = frozenset(
    {
        "yaadgaar",
        "shaandaar",
        "umda",
        "sundar",
        "aaraamdayak",
        "faydemand",
        "turant",
        "tezz",
        "swaadisht",
        "madadgar",
        "roz",
    }
)
_HI_NEG = frozenset(
    {
        "niraashajanak",
        "pareshan",
        "ghutan",
        "dhool",
        "badboo",
        "sust",
        "zyada",
        "chhota",
        "kharaab",
        "gande",
        "ganda",
        "dikkat",
    }
)


ALL_ASPECTS_FALLBACK = tuple(a.value for a in Aspect)


@dataclass
class Prediction:
    overall_label: str
    aspect_labels: dict[str, str]


def detect_aspects(text: str) -> set[Aspect]:
    tokens = {t.lower() for t in _TOKEN_RE.findall(text)}
    found: set[Aspect] = set()
    for aspect, cues in _ASPECT_CUES.items():
        if tokens & cues:
            found.add(aspect)
    return found


class BenchmarkSystem(ABC):
    name: str

    @abstractmethod
    def predict(self, text: str) -> Prediction: ...


class SentimentEngineSystem(BenchmarkSystem):
    name = "PahadPulse Sentiment_Engine"

    def __init__(self, engine: SentimentEngine | None = None) -> None:
        self._engine = engine or get_sentiment_engine()

    def predict(self, text: str) -> Prediction:
        analysis = self._engine.analyze(text, language="hi-Latn")
        overall = analysis.overall_label or "neutral"
        aspect_labels = {m.aspect.value: m.label for m in analysis.mentions}
        return Prediction(overall_label=overall, aspect_labels=aspect_labels)


def _polarity(tokens: set[str], pos: frozenset[str], neg: frozenset[str]) -> str:
    p = len(tokens & pos)
    n = len(tokens & neg)
    if p > n:
        return "positive"
    if n > p:
        return "negative"
    return "neutral"


class GenericLexiconSystem(BenchmarkSystem):
    name = "Generic English lexicon (off-the-shelf)"

    def predict(self, text: str) -> Prediction:
        tokens = {t.lower() for t in _TOKEN_RE.findall(text)}
        overall = _polarity(tokens, _GENERIC_POS, _GENERIC_NEG)
        aspect_labels = {a.value: overall for a in detect_aspects(text)}
        return Prediction(overall_label=overall, aspect_labels=aspect_labels)


class PlainLLMBaselineSystem(BenchmarkSystem):
    name = "Plain-LLM zero-shot (mock)"

    def predict(self, text: str) -> Prediction:
        # Deterministic mock of a zero-shot LLM: combine generic English and
        # romanised-Hindi polarity cues over the whole review, and per aspect.
        tokens = {t.lower() for t in _TOKEN_RE.findall(text)}
        pos = _GENERIC_POS | _HI_POS
        neg = _GENERIC_NEG | _HI_NEG
        overall = _polarity(tokens, pos, neg)
        aspect_labels = {a.value: overall for a in detect_aspects(text)}
        return Prediction(overall_label=overall, aspect_labels=aspect_labels)


def default_systems() -> list[BenchmarkSystem]:
    return [
        SentimentEngineSystem(),
        GenericLexiconSystem(),
        PlainLLMBaselineSystem(),
    ]
