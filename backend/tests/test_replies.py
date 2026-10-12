"""F13 Closed-loop review reply tests (Req 26)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.adapters.llm import TemplateLLMClient
from app.models.intervention import Intervention, ReplyState
from app.models.review import Aspect
from app.services.market_radar.replies import ReplyComposer, ReviewToReply, redact_pii


def _intervention(aspect: Aspect, desc: str) -> Intervention:
    return Intervention(
        id="iv-1",
        property_id="mus-pineview",
        aspect=aspect,
        description=desc,
        date=date(2024, 4, 1),
        logged_at=datetime.now(UTC),
    )


def test_reply_in_detected_language() -> None:
    composer = ReplyComposer(llm=TemplateLLMClient())
    review = ReviewToReply(
        id="r1",
        property_id="mus-pineview",
        text="खाना ठंडा था",
        detected_language="hi",
        negative_aspects=[Aspect.FOOD],
    )
    draft = composer.compose(review)
    assert draft.language == "hi"
    assert "धन्यवाद" in draft.body


def test_reply_cites_matching_logged_fix() -> None:
    composer = ReplyComposer(llm=TemplateLLMClient())
    review = ReviewToReply(
        id="r2",
        property_id="mus-pineview",
        text="the food was cold",
        detected_language="en",
        negative_aspects=[Aspect.FOOD],
    )
    draft = composer.compose(
        review,
        interventions=[_intervention(Aspect.FOOD, "Added a live hot breakfast counter.")],
    )
    assert draft.cited_source == "intervention:iv-1"
    assert "hot breakfast counter" in draft.body


def test_reply_excludes_pii_room_and_staff_names() -> None:
    cleaned = redact_pii(
        "Thanks Suresh, we moved you from room 214 — call +91 98000 11111 or a@b.com",
        ReplyComposer.STAFF_NAMES,
    )
    assert "Suresh" not in cleaned
    assert "214" not in cleaned
    assert "98000" not in cleaned
    assert "@" not in cleaned
    assert "our team" in cleaned


def test_reply_requires_manager_approval_before_ready() -> None:
    composer = ReplyComposer(llm=TemplateLLMClient())
    review = ReviewToReply(
        id="r3",
        property_id="mus-pineview",
        text="service was slow",
        detected_language="en",
        negative_aspects=[Aspect.SERVICE],
    )
    draft = composer.compose(review)
    assert draft.state == ReplyState.DRAFT
    assert draft.template_generated is True  # template fallback labelled
    ReplyComposer.approve(draft, "owner@pineview", edited_body=None)
    assert draft.state == ReplyState.READY_TO_POST
    assert draft.approved_by == "owner@pineview"


def test_reply_states_only_sourced_facts() -> None:
    composer = ReplyComposer(llm=TemplateLLMClient())
    review = ReviewToReply(
        id="r4",
        property_id="mus-pineview",
        text="room was cold",
        detected_language="en",
        negative_aspects=[Aspect.ROOM],
    )
    # No matching intervention/complaint -> no fabricated fix is cited.
    draft = composer.compose(review, interventions=[], resolved_complaints=[])
    assert draft.cited_fix is None
    assert draft.cited_source is None
