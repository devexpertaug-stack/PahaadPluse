"""Tests for Sentinel multi-channel intake + triage (Req 17, 18)."""

from __future__ import annotations

from datetime import timedelta

from app.models.sentinel import Channel, Department, Urgency
from app.services.sentinel.service import SentinelService


def _service() -> SentinelService:
    return SentinelService()


def test_intake_accepts_all_five_channels() -> None:
    svc = _service()
    for channel in Channel:
        result = svc.create_complaint(
            channel=channel, text="Room was dirty", stay_id="stay-bravo"
        )
        assert result.complaint.channel == channel.value
        assert result.complaint.created_at is not None


def test_whatsapp_number_matches_in_house_stay() -> None:
    svc = _service()
    result = svc.intake_from_whatsapp("+919800000101", "geyser kaam nahi kar raha")
    assert result.complaint.stay_id == "stay-alpha"
    assert result.complaint.channel == Channel.WHATSAPP.value


def test_front_desk_free_text_in_any_language() -> None:
    svc = _service()
    hi = svc.create_complaint(
        channel=Channel.IN_PERSON, text="कमरे में सफाई नहीं है", stay_id="stay-bravo"
    )
    assert hi.complaint.department == Department.HOUSEKEEPING.value


def test_housekeeping_vs_maintenance_split() -> None:
    svc = _service()
    hk = svc.triage.classify("towels and linen were dirty, no cleaning")
    assert hk.department == Department.HOUSEKEEPING
    mt = svc.triage.classify("the geyser and water heater are broken")
    assert mt.department == Department.MAINTENANCE
    wifi = svc.triage.classify("wifi router not working")
    assert wifi.department == Department.MAINTENANCE


def test_safety_terms_force_p1_in_any_language() -> None:
    svc = _service()
    for text in [
        "there is a fire in the room",
        "aag lag gayi hai",
        "आग लग गई है, मदद करो",
        "I feel unsafe, someone tried to rob me",
    ]:
        result = svc.triage.classify(text)
        assert result.urgency == Urgency.P1
        assert result.department == Department.SECURITY


def test_low_confidence_routes_to_front_office_with_original_prediction() -> None:
    svc = _service()
    result = svc.create_complaint(
        channel=Channel.IN_PERSON, text="it was just not great overall", stay_id="stay-bravo"
    )
    assert result.complaint.department == Department.FRONT_OFFICE.value
    assert result.complaint.requires_manual_assignment is True
    assert result.complaint.department_confidence < 0.6


def test_reassignment_is_recorded_with_original_prediction() -> None:
    svc = _service()
    result = svc.create_complaint(
        channel=Channel.IN_PERSON, text="unclear complaint text here", stay_id="stay-bravo"
    )
    cid = result.complaint.id
    svc.reassign(cid, Department.HOUSEKEEPING, "front office triaged manually")
    complaint = svc.complaints[cid]
    assert complaint.department == Department.HOUSEKEEPING.value
    assert len(complaint.reassignments) >= 1
    assert complaint.original_predicted_department is not None


def test_triage_attaches_sop_and_assigns_within_budget() -> None:
    svc = _service()
    result = svc.create_complaint(
        channel=Channel.WHATSAPP, text="geyser not working", stay_id="stay-alpha"
    )
    complaint = result.complaint
    assert complaint.sop_id is not None
    assert complaint.assigned_at is not None
    # complaint-to-department time is deterministic + within the 5s budget.
    delta = (complaint.assigned_at - complaint.created_at).total_seconds()
    assert delta <= 5.0


def test_department_notified_on_triage() -> None:
    svc = _service()
    before = len(svc.notifications)
    svc.create_complaint(channel=Channel.WHATSAPP, text="geyser broken", stay_id="stay-alpha")
    assert len(svc.notifications) > before


def test_review_matched_to_recent_stay_creates_review_platform_complaint() -> None:
    svc = _service()
    stay = svc.stays["stay-bravo"]
    review_date = stay.check_out + timedelta(days=3)
    result = svc.intake_from_review(
        text="rooms were dirty and smelly",
        sentiment="negative",
        review_date=review_date,
        stay_id="stay-bravo",
    )
    assert result is not None
    assert result.complaint.channel == Channel.REVIEW_PLATFORM.value


def test_review_outside_14_day_window_is_not_matched() -> None:
    svc = _service()
    stay = svc.stays["stay-bravo"]
    review_date = stay.check_out + timedelta(days=30)
    result = svc.intake_from_review(
        text="rooms were dirty",
        sentiment="negative",
        review_date=review_date,
        stay_id="stay-bravo",
    )
    assert result is None


def test_whatsapp_ack_in_guest_language_names_department() -> None:
    svc = _service()
    result = svc.intake_from_whatsapp(
        "+919800000101", "room mein geyser kaam nahi kar raha", language="hi-Latn"
    )
    assert result.acknowledgement is not None
    assert "Maintenance" in result.acknowledgement
    # the mock gateway recorded an outbound message to the guest
    assert any(m.to == "+919800000101" for m in svc._gateway.outbox)
