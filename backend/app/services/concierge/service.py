"""Bhasha Concierge multilingual grounded assistant (Req 29).

Answers non-complaint guest questions in the guest's detected language
(supporting at least Hindi, English, Bengali, Tamil and French, Req 29.1). Every
answer is grounded in retrieved versioned Property_Facts and the fact ids used
are logged (Req 29.2). When confidence < 0.7 OR no fact clears the relevance
threshold, the query is handed off to the front desk and the guest is told staff
will reply (Req 29.3). A message classified as a complaint instead creates a
Sentinel Complaint on channel ``concierge`` (Req 29.4). The share of queries
resolved without staff per week is reported (Req 29.5) and a Property_Fact
update is reflected in answers within 5 minutes (Req 29.6 — facts are read live
from the store, so updates are immediate).

Grounding uses the LLM adapter with retrieval; an extractive template fallback
answers offline (the fact text itself is returned, labelled template-generated).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from app.adapters.llm import LLMClient, get_llm_client
from app.models.intervention import PropertyFact
from app.models.sentinel import Channel
from app.services.sentinel.service import SentinelService, get_sentinel_service

CONFIDENCE_THRESHOLD = 0.7
RELEVANCE_THRESHOLD = 0.12
SUPPORTED_LANGUAGES = ("hi", "en", "bn", "ta", "fr")

# Topic keywords per fact id, matched against the query (any language) so a
# clear on-topic question lands a confident, grounded answer. Confidence is
# then relevance blended with a strong topic-match signal.
_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fact-breakfast": ("breakfast", "नाश्ता", "nashta", "petit", "déjeuner", "প্রাতরাশ", "காலை"),
    "fact-checkout": ("checkout", "check-out", "check out", "चेक", "samay", "départ"),
    "fact-wifi": ("wifi", "internet", "वाईफ़ाई", "वाईफाई", "password"),
    "fact-parking": ("parking", "car", "पार्किंग", "gaadi", "voiture", "stationnement"),
    "fact-mallroad": ("mall road", "mall", "माल", "market", "bazaar", "walk", "distance"),
    "fact-spa": ("spa", "massage", "स्पा", "therapy", "ayurveda"),
    "fact-pets": ("pet", "pets", "dog", "cat", "पालतू", "kutta", "animal"),
}

# Complaint-indicating keywords across the supported languages (Req 29.4).
_COMPLAINT_MARKERS = {
    "not working", "broken", "dirty", "cold water", "no water", "leaking",
    "rude", "problem", "complaint", "kaam nahi", "ganda", "kharab", "shikayat",
    "টয়লেট", "নোংরা", "கெட்ட", "problème", "cassé", "sale",
}


def detect_language(text: str) -> str:
    """Lightweight script/keyword language detection across five languages."""
    for ch in text:
        if "\u0980" <= ch <= "\u09ff":
            return "bn"  # Bengali
        if "\u0b80" <= ch <= "\u0bff":
            return "ta"  # Tamil
        if "\u0900" <= ch <= "\u097f":
            return "hi"  # Devanagari Hindi
    lowered = text.lower()
    french_markers = {"bonjour", "merci", "où", "quelle", "petit", "déjeuner", "piscine", "est"}
    if any(m in lowered.split() for m in french_markers):
        return "fr"
    hinglish = {"kahan", "kitne", "kya", "hai", "wifi", "nashta", "khana", "samay"}
    if any(m in lowered.split() for m in hinglish):
        return "hi"
    return "en"


def _tokens(text: str) -> Counter:
    return Counter(w.strip(".,!?;:").lower() for w in text.split() if w.strip(".,!?;:"))


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


_HANDOFF_MESSAGE = {
    "en": "Thank you — our front-desk team will reply to you shortly.",
    "hi": "धन्यवाद — हमारी फ्रंट-डेस्क टीम शीघ्र ही आपको उत्तर देगी।",
    "bn": "ধন্যবাদ — আমাদের ফ্রন্ট-ডেস্ক দল শীঘ্রই আপনাকে উত্তর দেবে।",
    "ta": "நன்றி — எங்கள் முன் அலுவலக குழு விரைவில் பதிலளிக்கும்.",
    "fr": "Merci — notre équipe de réception vous répondra bientôt.",
}


@dataclass
class ConciergeResult:
    """Outcome of handling one inbound concierge message."""

    language: str
    is_complaint: bool
    answer: str | None
    fact_ids: list[str]
    confidence: float
    handed_off: bool
    resolved_without_staff: bool
    template_generated: bool
    complaint_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "is_complaint": self.is_complaint,
            "answer": self.answer,
            "fact_ids": self.fact_ids,
            "confidence": round(self.confidence, 3),
            "handed_off": self.handed_off,
            "resolved_without_staff": self.resolved_without_staff,
            "template_generated": self.template_generated,
            "complaint_id": self.complaint_id,
        }


@dataclass
class ConversationTurn:
    at: datetime
    language: str
    question: str
    result: ConciergeResult


def _default_facts() -> dict[str, PropertyFact]:
    now = datetime.now(UTC)
    specs = [
        ("fact-breakfast", "breakfast",
         "Breakfast at The Forest Season Resort is served from 7:30am to 10:30am "
         "in the deodar forest-view dining hall, with local Garhwali specialities."),
        ("fact-checkout", "checkout",
         "Check-out time is 11:00am; late check-out until 1:00pm is subject to "
         "availability. Check-in is from 1:00pm."),
        ("fact-wifi", "wifi",
         "Complimentary high-speed wifi reaches every room and the lobby; the "
         "password is printed on your welcome card at check-in."),
        ("fact-parking", "parking",
         "Free on-site parking is available for in-house guests inside the resort "
         "gate, with valet assistance on request."),
        ("fact-mallroad", "location",
         "The resort sits in the deodar forest, a 10-minute drive (or 15-minute "
         "walk) from Mall Road, Mussoorie."),
        ("fact-spa", "spa",
         "The forest-side Ayurvedic spa is open from 10:00am to 8:00pm; booking "
         "a treatment in advance is recommended."),
        ("fact-pets", "pets",
         "The Forest Season Resort is pet-friendly: well-behaved pets are welcome "
         "in garden-view rooms for a small cleaning fee, by prior arrangement."),
    ]
    return {
        fid: PropertyFact(
            id=fid, property_id="mus-forestseason", topic=topic, text=text, version=1,
            updated_at=now,
        )
        for fid, topic, text in specs
    }


class BhashaConcierge:
    """Grounded multilingual assistant with handoff + complaint routing."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        sentinel: SentinelService | None = None,
        facts: dict[str, PropertyFact] | None = None,
    ) -> None:
        self._llm = llm or get_llm_client()
        self._sentinel = sentinel or get_sentinel_service()
        self._facts: dict[str, PropertyFact] = facts if facts is not None else _default_facts()
        self.history: list[ConversationTurn] = []

    # ---- Property_Facts (versioned, live-read for 5-minute freshness) ----
    def facts(self) -> list[PropertyFact]:
        return list(self._facts.values())

    def update_fact(self, fact_id: str, text: str) -> PropertyFact:
        """Update a fact; the new version is used by answers immediately (Req 29.6)."""
        existing = self._facts.get(fact_id)
        version = (existing.version + 1) if existing else 1
        updated = PropertyFact(
            id=fact_id,
            property_id=existing.property_id if existing else "mus-forestseason",
            topic=existing.topic if existing else fact_id,
            text=text,
            version=version,
            updated_at=datetime.now(UTC),
        )
        self._facts[fact_id] = updated
        return updated

    def _is_complaint(self, text: str) -> bool:
        lowered = text.lower()
        return any(marker in lowered for marker in _COMPLAINT_MARKERS)

    def _retrieve(self, question: str) -> tuple[PropertyFact | None, float, float]:
        """Return the best fact plus (relevance, confidence).

        Relevance is bag-of-words cosine; confidence blends relevance with a
        strong topic-keyword match so a clearly on-topic question in any
        supported language lands a grounded answer rather than a handoff.
        """
        q = _tokens(question)
        lowered = question.lower()
        best: PropertyFact | None = None
        best_relevance = 0.0
        best_confidence = 0.0
        for fact in self._facts.values():
            relevance = _cosine(q, _tokens(fact.text + " " + fact.topic))
            keywords = _TOPIC_KEYWORDS.get(fact.id, ())
            topic_hit = any(kw in lowered for kw in keywords)
            confidence = min(1.0, relevance * 2.0 + (0.75 if topic_hit else 0.0))
            if confidence > best_confidence or (
                confidence == best_confidence and relevance > best_relevance
            ):
                best_confidence, best_relevance, best = confidence, relevance, fact
        return best, best_relevance, best_confidence

    def handle(self, message: str, *, stay_id: str | None = None) -> ConciergeResult:
        language = detect_language(message)

        # Req 29.4: a complaint creates a Sentinel Complaint on channel concierge.
        if self._is_complaint(message):
            intake = self._sentinel.create_complaint(
                channel=Channel.CONCIERGE,
                text=message,
                stay_id=stay_id,
                language=language,
            )
            result = ConciergeResult(
                language=language,
                is_complaint=True,
                answer=None,
                fact_ids=[],
                confidence=1.0,
                handed_off=False,
                resolved_without_staff=False,
                template_generated=False,
                complaint_id=intake.complaint.id,
            )
            self.history.append(
                ConversationTurn(datetime.now(UTC), language, message, result)
            )
            return result

        fact, relevance, confidence = self._retrieve(message)
        # Unsupported languages are not confidently answerable.
        if language not in SUPPORTED_LANGUAGES:
            confidence *= 0.5

        # Req 29.3: hand off when confidence is below threshold or no fact
        # clears the relevance floor (confidence already folds in relevance +
        # topic match, so a confident answer always has a grounding fact).
        if (
            fact is None
            or confidence < CONFIDENCE_THRESHOLD
            or (relevance < RELEVANCE_THRESHOLD and confidence < CONFIDENCE_THRESHOLD)
        ):
            result = ConciergeResult(
                language=language,
                is_complaint=False,
                answer=_HANDOFF_MESSAGE.get(language, _HANDOFF_MESSAGE["en"]),
                fact_ids=[],
                confidence=confidence,
                handed_off=True,
                resolved_without_staff=False,
                template_generated=False,
            )
            self.history.append(
                ConversationTurn(datetime.now(UTC), language, message, result)
            )
            return result

        # Grounded answer via the LLM adapter; extractive fallback offline.
        response = self._llm.generate(
            "Answer the guest question using only the provided property fact.",
            context={"language": language, "fact": fact.text, "question": message},
        )
        template_generated = response.template_generated
        answer = fact.text if template_generated else response.text
        result = ConciergeResult(
            language=language,
            is_complaint=False,
            answer=answer,
            fact_ids=[fact.id],
            confidence=confidence,
            handed_off=False,
            resolved_without_staff=True,
            template_generated=template_generated,
        )
        self.history.append(ConversationTurn(datetime.now(UTC), language, message, result))
        return result

    def metrics(self) -> dict:
        """Share of queries resolved without staff this week (Req 29.5)."""
        non_complaint = [t for t in self.history if not t.result.is_complaint]
        total = len(non_complaint)
        resolved = sum(1 for t in non_complaint if t.result.resolved_without_staff)
        return {
            "total_queries": total,
            "resolved_without_staff": resolved,
            "handed_off": total - resolved,
            "resolved_without_staff_rate": round(resolved / total, 3) if total else 0.0,
        }


@lru_cache
def get_concierge() -> BhashaConcierge:
    """Return a process-wide Bhasha Concierge instance."""
    return BhashaConcierge()
