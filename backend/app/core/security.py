"""Security helpers: password hashing and session tokens.

Placeholder scaffold for FEAT-001. Later features expand auth/role handling.
Only `/health` and the WhatsApp webhook are unauthenticated (Req 30.1).
"""

from __future__ import annotations

import hashlib
import hmac

from app.core.config import get_settings


def pseudonymize(identifier: str) -> str:
    """Return a deterministic pseudonym for a guest identifier (Req privacy).

    Uses an HMAC with the configured salt so the same input always maps to the
    same opaque token without exposing the original value.
    """
    settings = get_settings()
    return hmac.new(
        settings.pseudonym_salt.encode("utf-8"),
        identifier.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    """Constant-time string comparison for secrets/signatures."""
    return hmac.compare_digest(a, b)
