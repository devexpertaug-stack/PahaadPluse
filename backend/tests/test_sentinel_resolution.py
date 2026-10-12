"""Tests for Sentinel resolution, recurrence + escalation (Req 19)."""

from __future__ import annotations

from datetime import timedelta

from app.models.sentinel import Channel, ComplaintState, Urgency
from app.services.sentinel.service import SentinelService


def _service() -> SentinelService:
    return SentinelService()


def test_mark_resolved_records_timestamp_and_note() -> None:
    svc = _service()
    result = svc.create_complaint(
        channel=Channel.WHATSAPP, text="geyser broken", stay_id="stay-alpha"
    )
    resolved = svc.resolve_complaint(result.complaint.id, "replaced the geyser")
    assert resolved.state == ComplaintState.RESOLVED.value
    assert resolved.resolved_at is not None
    assert resolved.resolution_note == "replaced the geyser"


def test_recurrence_same_stay_links_and_raises_urgency() -> None:
    svc = _service()
    first = svc.create_complaint(
        channel=Channel.WHATSAPP, text="geyser not working", stay_id="stay-alpha"
    )
    second = svc.create_complaint(
        channel=Channel.WHATSAPP, text="geyser broken again", stay_id="stay-alpha"
    )
    assert second.complaint.is_recurrence is True
    assert second.complaint.recurrence_of == first.complaint.id
    # P2 geyser raised one level -> P1 (max).
    assert second.complaint.urgency == Urgency.P1.value


def test_recurrence_same_room_within_30_days() -> None:
    svc = _service()
    base = svc.now()
    svc.create_complaint(
        channel=Channel.IN_PERSON,
        text="geyser not working",
        room="101",
        created_at=base - timedelta(days=10),
    )
    second = svc.create_complaint(
        channel=Channel.IN_PERSON, text="geyser broken", room="101", created_at=base
    )
    assert second.complaint.is_recurrence is True


def test_recurrence_urgency_capped_at_p1() -> None:
    svc = _service()
    svc.create_complaint(channel=Channel.IN_PERSON, text="fire", room="101")
    second = svc.create_complaint(channel=Channel.IN_PERSON, text="fire again", room="101")
    assert second.complaint.urgency == Urgency.P1.value


def test_escalate_overdue_complaints_to_managers() -> None:
    svc = _service()
    # Create a complaint whose SOP target is already exceeded.
    result = svc.create_complaint(
        channel=Channel.WHATSAPP,
        text="geyser not working",
        stay_id="stay-alpha",
        created_at=svc.now() - timedelta(hours=5),
    )
    escalated = svc.escalate_overdue()
    ids = {c.id for c in escalated}
    assert result.complaint.id in ids
    assert svc.complaints[result.complaint.id].escalated is True


def test_in_stay_resolution_rate_computed() -> None:
    svc = _service()
    result = svc.create_complaint(
        channel=Channel.WHATSAPP, text="geyser broken", stay_id="stay-delta"
    )
    svc.resolve_complaint(result.complaint.id, "fixed before checkout")
    metrics = svc.metrics()
    assert 0.0 <= metrics["in_stay_resolution_rate"] <= 1.0
    assert metrics["in_stay_resolution_rate"] > 0.0
