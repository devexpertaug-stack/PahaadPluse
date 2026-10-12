"""Auth_Service tests (Req 30): hashing, login, lockout and current-user."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.core.security import (
    hash_password,
    issue_session_token,
    verify_password,
    verify_session_token,
)
from app.main import app
from app.services.auth.service import (
    DEMO_OWNER_PASSWORD,
    DEMO_OWNER_USERNAME,
    MAX_FAILED_ATTEMPTS,
    AccountLockedError,
    AuthService,
    InvalidCredentialsError,
    get_auth_service,
)

client = TestClient(app)


def _reset_demo_owner() -> None:
    """Clear any accumulated lockout state on the shared seeded owner.

    The endpoint tests hit the process-wide ``@lru_cache`` auth service, so a
    wrong-password test can leave ``failed_attempts`` elevated for other tests.
    Resetting keeps the suite order-independent.
    """
    user = get_auth_service().get_by_username(DEMO_OWNER_USERNAME)
    if user is not None:
        user.failed_attempts = 0
        user.locked_until = None


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def test_hash_verify_roundtrip() -> None:
    hashed = hash_password("S3cret!pass")
    assert hashed != "S3cret!pass"  # never plaintext
    assert hashed.startswith("$argon2")
    assert verify_password("S3cret!pass", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_session_token_roundtrip_and_expiry() -> None:
    token = issue_session_token(user_id="u1", role="owner", property_id="mus-forestseason")
    payload = verify_session_token(token)
    assert payload is not None
    assert payload["sub"] == "u1"
    assert payload["role"] == "owner"
    assert payload["property_id"] == "mus-forestseason"
    # Tampered / garbage tokens are rejected.
    assert verify_session_token("garbage") is None
    assert verify_session_token(token + "x") is None
    # Expired tokens are rejected.
    expired = issue_session_token(
        user_id="u1", role="owner", property_id="mus-forestseason",
        ttl_seconds=-1, now=time.time() - 10,
    )
    assert verify_session_token(expired) is None


# ---------------------------------------------------------------------------
# Login endpoint
# ---------------------------------------------------------------------------
def test_login_success_returns_scoped_user() -> None:
    _reset_demo_owner()
    r = client.post(
        "/auth/login",
        json={"username": DEMO_OWNER_USERNAME, "password": DEMO_OWNER_PASSWORD},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["user"]["property_id"] == "mus-forestseason"
    assert body["user"]["property_name"] == "The Forest Season Resort"
    assert body["user"]["role"] in {"owner", "manager"}


def test_login_wrong_password_401() -> None:
    r = client.post(
        "/auth/login",
        json={"username": DEMO_OWNER_USERNAME, "password": "definitely-wrong"},
    )
    assert r.status_code == 401


def test_login_unknown_user_401() -> None:
    r = client.post(
        "/auth/login",
        json={"username": "nobody@nowhere.demo", "password": "x"},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Account lockout (uses an isolated service so it does not affect the seeded demo user)
# ---------------------------------------------------------------------------
def test_lockout_after_repeated_failures() -> None:
    svc = AuthService()
    for _ in range(MAX_FAILED_ATTEMPTS):
        with pytest.raises(InvalidCredentialsError):
            svc.authenticate(DEMO_OWNER_USERNAME, "wrong")
    # Now the account is locked even for the correct password.
    with pytest.raises(AccountLockedError):
        svc.authenticate(DEMO_OWNER_USERNAME, DEMO_OWNER_PASSWORD)


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------
def test_me_with_valid_token() -> None:
    _reset_demo_owner()
    login = client.post(
        "/auth/login",
        json={"username": DEMO_OWNER_USERNAME, "password": DEMO_OWNER_PASSWORD},
    )
    token = login.json()["token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["property_id"] == "mus-forestseason"
    assert body["username"] == DEMO_OWNER_USERNAME


def test_me_rejects_missing_and_invalid_token() -> None:
    assert client.get("/auth/me").status_code == 401
    assert client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    ).status_code == 401


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------
def test_demo_credentials_are_seeded() -> None:
    svc = get_auth_service()
    user = svc.get_by_username(DEMO_OWNER_USERNAME)
    assert user is not None
    assert user.property_id == "mus-forestseason"
    # Password is stored only as a hash and matches the documented demo password.
    assert user.password_hash.startswith("$argon2")
    assert verify_password(DEMO_OWNER_PASSWORD, user.password_hash)
