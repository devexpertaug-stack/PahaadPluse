"""WhatsApp gateway adapter.

Defines the :class:`WhatsAppGateway` interface and an in-process mock that
records outbound messages and can simulate inbound webhooks. A real HMAC
signature-verification helper is provided for inbound webhooks (Req 20.4).
"""

from __future__ import annotations

import hashlib
import hmac
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.config import get_settings


@dataclass
class OutboundMessage:
    """An outbound WhatsApp message."""

    to: str
    body: str
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class InboundMessage:
    """An inbound WhatsApp message."""

    from_number: str
    body: str
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def verify_signature(signing_secret: str, payload: bytes, signature: str) -> bool:
    """Verify an inbound webhook HMAC-SHA256 signature (Req 20.4).

    ``signature`` may be prefixed with ``sha256=`` (common for webhook headers).
    Comparison is constant-time.
    """
    if signature.startswith("sha256="):
        signature = signature[len("sha256=") :]
    expected = hmac.new(
        signing_secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


class WhatsAppGateway(ABC):
    """Interface for sending and receiving WhatsApp messages."""

    @abstractmethod
    def send(self, to: str, body: str) -> OutboundMessage:
        """Send an outbound message."""

    @abstractmethod
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify an inbound webhook signature."""


class MockWhatsAppGateway(WhatsAppGateway):
    """In-process mock that records outbound and simulates inbound messages."""

    def __init__(self, signing_secret: str) -> None:
        self._signing_secret = signing_secret
        self.outbox: list[OutboundMessage] = []
        self.inbox: list[InboundMessage] = []

    def send(self, to: str, body: str) -> OutboundMessage:
        message = OutboundMessage(to=to, body=body)
        self.outbox.append(message)
        return message

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        return verify_signature(self._signing_secret, payload, signature)

    def simulate_inbound(self, from_number: str, body: str) -> InboundMessage:
        """Record a simulated inbound message (used by the demo scenario)."""
        message = InboundMessage(from_number=from_number, body=body)
        self.inbox.append(message)
        return message

    def sign(self, payload: bytes) -> str:
        """Produce a valid signature for ``payload`` (test/demo helper)."""
        return "sha256=" + hmac.new(
            self._signing_secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()


def get_whatsapp_gateway() -> WhatsAppGateway:
    """Select the WhatsApp gateway based on configuration.

    Only the in-process mock is implemented for FEAT-001; real providers are
    added in a later feature behind the same interface.
    """
    settings = get_settings()
    _ = settings.whatsapp_provider  # provider selection reserved for later features
    return MockWhatsAppGateway(signing_secret=settings.whatsapp_signing_secret)


# A shared mock instance so the webhook route and demo scenario can observe the
# same outbox/inbox during a single process run.
_default_gateway: WhatsAppGateway | None = None


def get_default_gateway() -> WhatsAppGateway:
    """Return a process-wide shared gateway instance."""
    global _default_gateway
    if _default_gateway is None:
        _default_gateway = get_whatsapp_gateway()
    return _default_gateway
