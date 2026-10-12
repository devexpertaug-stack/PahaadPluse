"""Security helpers: pseudonymization, password hashing and session tokens.

Auth is demo-grade but follows the spec's Auth_Service intent (Req 30):

* Passwords are hashed with **argon2** via passlib's ``CryptContext``
  (``passlib[argon2]`` is a declared backend dependency) through
  :func:`hash_password` / :func:`verify_password`. Plaintext is never stored.
  (If argon2 were unavailable a labelled stdlib PBKDF2-HMAC-SHA256 fallback
  would be used instead.)
* Session tokens are **HMAC-SHA256 signed** (keyed off ``settings.session_secret``)
  and carry the user id, role, property scope and an expiry (~12h). See
  :func:`issue_session_token` / :func:`verify_session_token`. No third-party
  token library is required so the demo stays free and self-contained.

Only ``/health`` and the WhatsApp webhook are unauthenticated (Req 30.1).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from passlib.context import CryptContext

from app.core.config import get_settings

# ---------------------------------------------------------------------------
# Pseudonymization (privacy)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Password hashing (argon2)
# ---------------------------------------------------------------------------

# Single shared context. argon2 embeds its salt + parameters in the encoded
# hash, so each call produces a distinct, self-describing ``$argon2id$...``
# string.
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return an argon2 hash of ``password`` (never store plaintext)."""
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether ``password`` matches the stored argon2 ``password_hash``."""
    try:
        return _pwd_context.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Session tokens (HMAC-SHA256 signed, keyed off session_secret)
# ---------------------------------------------------------------------------

# ~12h session lifetime (Req 30).
SESSION_TTL_SECONDS = 12 * 60 * 60


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(payload_b64: str) -> str:
    settings = get_settings()
    digest = hmac.new(
        settings.session_secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64url_encode(digest)


def issue_session_token(
    *,
    user_id: str,
    role: str,
    property_id: str,
    ttl_seconds: int = SESSION_TTL_SECONDS,
    now: float | None = None,
) -> str:
    """Issue a signed ``<payload>.<signature>`` session token.

    The payload carries the user id, role, property scope and an absolute
    expiry (``exp``). The signature is an HMAC-SHA256 over the payload keyed on
    ``settings.session_secret`` so the token cannot be forged or tampered with.
    """
    issued_at = time.time() if now is None else now
    payload = {
        "sub": user_id,
        "role": role,
        "property_id": property_id,
        "iat": int(issued_at),
        "exp": int(issued_at + ttl_seconds),
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(payload_b64)
    return f"{payload_b64}.{signature}"


def verify_session_token(token: str, *, now: float | None = None) -> dict | None:
    """Return the token payload if valid and unexpired, else ``None``.

    Validates the HMAC signature in constant time and checks the expiry. Any
    malformed token returns ``None`` rather than raising.
    """
    if not token or "." not in token:
        return None
    payload_b64, _, signature = token.partition(".")
    expected = _sign(payload_b64)
    if not constant_time_equals(signature, expected):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        return None
    current = time.time() if now is None else now
    if int(payload.get("exp", 0)) < current:
        return None
    return payload
