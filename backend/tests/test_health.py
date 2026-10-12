"""Tests for the public endpoints (Req 30.1)."""

from __future__ import annotations

import hashlib
import hmac

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def test_health_is_public_and_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "pahadpulse"


def test_whatsapp_webhook_accepts_without_signature() -> None:
    response = client.post("/webhooks/whatsapp", content=b"{}")
    assert response.status_code == 202


def test_whatsapp_webhook_rejects_bad_signature() -> None:
    response = client.post(
        "/webhooks/whatsapp",
        content=b"{}",
        headers={"x-hub-signature-256": "sha256=deadbeef"},
    )
    # Bad signature -> 403 + Audit_Log entry (Req 20.4).
    assert response.status_code == 403


def test_whatsapp_webhook_accepts_valid_signature() -> None:
    settings = get_settings()
    payload = b'{"event":"inbound"}'
    signature = (
        "sha256="
        + hmac.new(
            settings.whatsapp_signing_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
    )
    response = client.post(
        "/webhooks/whatsapp",
        content=payload,
        headers={"x-hub-signature-256": signature},
    )
    assert response.status_code == 202
