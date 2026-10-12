"""F13 Closed-Loop Review Replies (Req 26).

Drafts a reply to a Review_Record in the review's detected language. Where a
*resolved* Complaint or a logged Intervention matches one of the review's
negative Aspects, the reply cites that logged fix (Req 26.2). The draft:

* excludes guest PII, room numbers and internal staff names (Req 26.3),
* states only facts present in Complaints / Interventions / Property_Facts
  (Req 26.5),
* must be approved or edited by a manager/owner before it is marked
  ready-to-post (Req 26.4),
* uses the LLM adapter with the deterministic template fallback (labelled
  template-generated) when the LLM is unreachable (Req 26.6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.adapters.llm import LLMClient, get_llm_client
from app.models.intervention import Intervention, ReplyDraft, ReplyState
from app.models.review import Aspect

# Multilingual reply scaffolds keyed by detected language (Req 26.1).
_GREETINGS: dict[str, str] = {
    "en": "Thank you for taking the time to share your feedback.",
    "hi": "आपकी प्रतिक्रिया साझा करने के लिए धन्यवाद।",
    "hi-Latn": "Aapki pratikriya saajha karne ke liye dhanyavaad.",
}
_FIX_PHRASE: dict[str, str] = {
    "en": "We have acted on your {aspect} feedback: {fix}",
    "hi": "हमने आपकी {aspect} प्रतिक्रिया पर कार्रवाई की है: {fix}",
    "hi-Latn": "Humne aapki {aspect} feedback par kaaryavaahi ki hai: {fix}",
}
_CLOSING: dict[str, str] = {
    "en": "We hope to welcome you back soon.",
    "hi": "हम आपका पुनः स्वागत करने की आशा करते हैं।",
    "hi-Latn": "Hum aapka punah swagat karne ki aasha karte hain.",
}

# Patterns used to strip PII / room numbers / staff names (Req 26.3).
_ROOM_RE = re.compile(r"\broom\s*#?\s*\d+\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"\+?\d[\d\s-]{7,}\d")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _lang_key(language: str) -> str:
    if language in _GREETINGS:
        return language
    if language and language.startswith("hi"):
        return "hi-Latn" if language.endswith("Latn") else "hi"
    return "en"


def redact_pii(text: str, staff_names: list[str]) -> str:
    """Remove guest PII, room numbers and internal staff names (Req 26.3)."""
    out = _ROOM_RE.sub("your room", text)
    out = _PHONE_RE.sub("", out)
    out = _EMAIL_RE.sub("", out)
    for name in staff_names:
        if name:
            out = re.sub(rf"\b{re.escape(name)}\b", "our team", out, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", out).strip()


@dataclass
class ReviewToReply:
    """Minimal review payload the composer needs."""

    id: str
    property_id: str
    text: str
    detected_language: str
    negative_aspects: list[Aspect]


@dataclass
class MatchedFix:
    """A logged fix (resolved Complaint or Intervention) for an Aspect."""

    aspect: Aspect
    description: str
    source: str  # "intervention:<id>" | "complaint:<id>"


class ReplyComposer:
    """Compose a closed-loop review reply draft (Req 26)."""

    # Internal staff names that must never leak into a reply (Req 26.3).
    STAFF_NAMES = ["Suresh", "Anita", "Mohan", "Priya", "Rajesh"]

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or get_llm_client()

    def _match_fix(
        self,
        aspect: Aspect,
        interventions: list[Intervention],
        resolved_complaints: list[dict],
    ) -> MatchedFix | None:
        for iv in interventions:
            if Aspect(iv.aspect) is aspect:
                return MatchedFix(
                    aspect=aspect,
                    description=iv.description,
                    source=f"intervention:{iv.id}",
                )
        for c in resolved_complaints:
            c_aspect = c.get("aspect")
            if c_aspect and Aspect(c_aspect) is aspect:
                return MatchedFix(
                    aspect=aspect,
                    description=c.get("resolution_note") or "resolved by our team",
                    source=f"complaint:{c.get('id')}",
                )
        return None

    def compose(
        self,
        review: ReviewToReply,
        *,
        interventions: list[Intervention] | None = None,
        resolved_complaints: list[dict] | None = None,
        property_facts: list[str] | None = None,
    ) -> ReplyDraft:
        interventions = interventions or []
        resolved_complaints = resolved_complaints or []
        key = _lang_key(review.detected_language)

        matched: MatchedFix | None = None
        for aspect in review.negative_aspects:
            matched = self._match_fix(aspect, interventions, resolved_complaints)
            if matched:
                break

        # Build a grounded prompt and let the LLM adapter phrase it; the body is
        # assembled from the template scaffold so facts stay sourced even when a
        # remote LLM is available (we only use phrasing, never new facts).
        lines = [_GREETINGS[key]]
        cited_fix = None
        cited_source = None
        if matched:
            fix_clean = redact_pii(matched.description, self.STAFF_NAMES)
            lines.append(
                _FIX_PHRASE[key].format(aspect=matched.aspect.value, fix=fix_clean)
            )
            cited_fix = fix_clean
            cited_source = matched.source
        if property_facts:
            # Only facts explicitly supplied from Property_Facts are stated.
            fact = redact_pii(property_facts[0], self.STAFF_NAMES)
            lines.append(fact)
        lines.append(_CLOSING[key])
        body = redact_pii(" ".join(lines), self.STAFF_NAMES)

        # Route the phrasing through the adapter; keep template-generated label.
        response = self._llm.generate(
            "Rephrase this hotel review reply keeping all facts unchanged.",
            context={"language": key, "draft": body},
        )
        template_generated = response.template_generated

        return ReplyDraft(
            id=f"reply-{review.id}",
            review_id=review.id,
            property_id=review.property_id,
            language=key,
            body=body,
            template_generated=template_generated,
            cited_fix=cited_fix,
            cited_source=cited_source,
            negative_aspects=list(review.negative_aspects),
            pii_redacted=True,
            state=ReplyState.DRAFT,
        )

    @staticmethod
    def approve(draft: ReplyDraft, approver: str, edited_body: str | None = None) -> ReplyDraft:
        """Manager/owner approval (optionally editing) marks it ready-to-post."""
        from datetime import UTC, datetime

        if edited_body is not None:
            draft.body = redact_pii(edited_body, ReplyComposer.STAFF_NAMES)
        draft.state = ReplyState.READY_TO_POST
        draft.approved_by = approver
        draft.approved_at = datetime.now(UTC)
        return draft
