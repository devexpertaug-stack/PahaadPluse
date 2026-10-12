"""Bhasha Concierge tests (Req 29): grounding, handoff, routing, freshness."""

from __future__ import annotations

from app.adapters.llm import TemplateLLMClient
from app.services.concierge.service import (
    SUPPORTED_LANGUAGES,
    BhashaConcierge,
    detect_language,
)
from app.services.sentinel.service import SentinelService


def _concierge() -> BhashaConcierge:
    return BhashaConcierge(llm=TemplateLLMClient(), sentinel=SentinelService())


def test_detects_five_required_languages() -> None:
    assert detect_language("What time is breakfast?") == "en"
    assert detect_language("नाश्ता कितने बजे है?") == "hi"
    assert detect_language("প্রাতরাশ কখন?") == "bn"
    assert detect_language("காலை உணவு எப்போது?") == "ta"
    assert detect_language("Où est le petit déjeuner?") == "fr"
    for lang in ("hi", "en", "bn", "ta", "fr"):
        assert lang in SUPPORTED_LANGUAGES


def test_grounds_answer_in_property_fact_and_logs_fact_ids() -> None:
    c = _concierge()
    r = c.handle("What time is breakfast?")
    assert not r.handed_off
    assert r.fact_ids == ["fact-breakfast"]
    assert r.resolved_without_staff is True


def test_answer_in_guest_language() -> None:
    c = _concierge()
    r = c.handle("Où est le petit déjeuner?")
    assert r.language == "fr"
    assert not r.handed_off


def test_handoff_below_confidence_threshold() -> None:
    c = _concierge()
    r = c.handle("Can you arrange a helicopter to Everest base camp?")
    assert r.handed_off is True
    assert r.confidence < 0.7
    assert r.fact_ids == []
    assert r.answer  # guest told staff will reply


def test_complaint_message_routes_to_sentinel_concierge_channel() -> None:
    sentinel = SentinelService()
    c = BhashaConcierge(llm=TemplateLLMClient(), sentinel=sentinel)
    r = c.handle("the geyser is not working and the room is dirty")
    assert r.is_complaint is True
    assert r.complaint_id is not None
    created = sentinel.complaints[r.complaint_id]
    assert str(created.channel) == "concierge"


def test_resolved_without_staff_metric() -> None:
    c = _concierge()
    c.handle("What time is breakfast?")
    c.handle("Are pets allowed at the resort?")
    c.handle("Can you arrange a private jet?")  # handoff
    m = c.metrics()
    assert m["total_queries"] == 3
    assert m["resolved_without_staff"] == 2
    assert m["handed_off"] == 1


def test_fact_update_reflected_immediately() -> None:
    c = _concierge()
    before = c.handle("What time is breakfast?").answer
    c.update_fact("fact-breakfast", "Breakfast is served from 8am to 11am in the garden.")
    after = c.handle("What time is breakfast?").answer
    assert before != after
    assert "8am" in after
