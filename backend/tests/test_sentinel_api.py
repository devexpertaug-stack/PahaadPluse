"""API-level tests for the Sentinel + WhatsApp loop (Req 20, 21)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.core.audit import audit_log
from app.main import app
from app.services.sentinel.service import get_sentinel_service

client = TestClient(app)


def test_board_and_metrics_endpoints() -> None:
    board = client.get("/sentinel/board")
    assert board.status_code == 200
    assert "rows" in board.json()
    metrics = client.get("/sentinel/metrics")
    assert metrics.status_code == 200
    body = metrics.json()
    assert "in_stay_resolution_rate" in body
    assert "repeat_complaints_this_week" in body


def test_whatsapp_demo_helper_surfaces_hinglish_complaint_on_board() -> None:
    service = get_sentinel_service()
    resp = client.post(
        "/sentinel/demo/whatsapp",
        json={
            "from_number": "+919800000101",
            "body": "room mein geyser kaam nahi kar raha",
            "language": "hi-Latn",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["complaint"]["department"] == "Maintenance"
    assert "Maintenance" in (data["acknowledgement"] or "")
    # The complaint's stay now appears on the board with a non-zero score.
    board = client.get("/sentinel/board").json()
    row = next(r for r in board["rows"] if r["stay_id"] == "stay-alpha")
    assert row["score"] > 0.0
    assert row["top_open_complaint"] is not None
    assert service is get_sentinel_service()  # shared process-wide state


def test_webhook_bad_signature_returns_403_and_audits() -> None:
    before = len(audit_log.entries)
    resp = client.post(
        "/webhooks/whatsapp",
        content=b'{"from":"+91","body":"test"}',
        headers={"x-hub-signature-256": "sha256=deadbeef"},
    )
    assert resp.status_code == 403
    entries = audit_log.entries
    assert len(entries) == before + 1
    assert entries[-1].action == "whatsapp_webhook_rejected"


def test_webhook_valid_signature_routes_into_sentinel() -> None:
    from app.adapters.whatsapp import get_default_gateway

    gateway = get_default_gateway()
    payload = json.dumps(
        {"from": "+919800000204", "body": "wifi internet not working", "language": "en"}
    ).encode("utf-8")
    signature = gateway.sign(payload)  # type: ignore[attr-defined]
    resp = client.post(
        "/webhooks/whatsapp",
        content=payload,
        headers={"x-hub-signature-256": signature},
    )
    assert resp.status_code == 202


def test_voice_demo_transcribes_translates_and_replies_in_language() -> None:
    resp = client.post(
        "/sentinel/demo/voice",
        json={
            "from_number": "+919800000309",
            "audio_text": "lang=hi;conf=0.9|room mein geyser kaam nahi kar raha",
            "duration_seconds": 20.0,
        },
    )
    assert resp.status_code == 200
    complaint = resp.json()["complaint"]
    assert complaint["transcript"] is not None
    # non-English transcript stores an English translation
    assert complaint["transcript_translation_en"] is not None
    assert complaint["language"].startswith("hi")


def test_voice_low_confidence_flags_and_routes_to_front_office() -> None:
    resp = client.post(
        "/sentinel/demo/voice",
        json={
            "from_number": "+919800000309",
            "audio_text": "lang=hi;conf=0.3|kuch samajh nahi aaya",
            "duration_seconds": 15.0,
        },
    )
    assert resp.status_code == 200
    complaint = resp.json()["complaint"]
    assert complaint["flagged_for_staff"] is True
    assert complaint["department"] == "Front_Office"


def test_voice_rejects_over_two_minutes() -> None:
    resp = client.post(
        "/sentinel/demo/voice",
        json={
            "from_number": "+919800000309",
            "audio_text": "lang=en;conf=0.9|too long",
            "duration_seconds": 130.0,
        },
    )
    assert resp.status_code == 400


def test_evidence_packet_only_for_destination_official() -> None:
    denied = client.post(
        "/destination/evidence-packet",
        params={"canonical": "mall road", "role": "front_desk"},
    )
    assert denied.status_code == 403
    ok = client.post(
        "/destination/evidence-packet",
        params={"canonical": "mall road", "role": "destination_official"},
    )
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "application/pdf"
    assert int(ok.headers["X-Issues-Surfaced"]) >= 1


def test_destination_heatmap_endpoint_filters_by_theme() -> None:
    resp = client.get("/destination/heatmap", params={"theme": "traffic"})
    assert resp.status_code == 200
    assert resp.json()["theme"] == "traffic"
    bad = client.get("/destination/heatmap", params={"theme": "nope"})
    assert bad.status_code == 400
