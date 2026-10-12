"""Auth_Service: demo-grade user store, login and account lockout (Req 30).

A process-wide ``@lru_cache`` singleton (consistent with the other services)
that seeds the demo accounts on first access and authenticates
username/password against stored argon2 hashes. Successful logins issue a
signed ~12h session token (:mod:`app.core.security`). Repeated failures trigger
a basic account lockout.

Seeded demo accounts are scoped to **The Forest Season Resort**
(``property_id='mus-forestseason'``). The documented demo owner credentials are
``owner@forestseason.demo`` / ``ForestSeason@2024`` (recorded in the README);
only the hash is stored here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from app.core.security import (
    hash_password,
    issue_session_token,
    verify_password,
    verify_session_token,
)
from app.models.user import PublicUser, Role, User
from app.services.market_radar.analytics_dataset import (
    HOME_PROPERTY_ID,
    property_name,
)

# ---- Lockout policy (demo-grade) ----
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

# ---- Documented demo credentials (owner/manager for The Forest Season Resort) ----
DEMO_OWNER_USERNAME = "owner@forestseason.demo"
DEMO_OWNER_PASSWORD = "ForestSeason@2024"
DEMO_MANAGER_USERNAME = "manager@forestseason.demo"
DEMO_MANAGER_PASSWORD = "Mussoorie@2024"


@dataclass(frozen=True)
class AuthResult:
    """A successful authentication: the public user + a signed session token."""

    user: PublicUser
    token: str


class AccountLockedError(Exception):
    """Raised when authentication is refused because the account is locked."""


class InvalidCredentialsError(Exception):
    """Raised when the username is unknown or the password is wrong."""


def _public(user: User) -> PublicUser:
    return PublicUser(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        property_id=user.property_id,
        property_name=property_name(user.property_id),
    )


class AuthService:
    """In-memory user store with login + basic lockout (demo-grade)."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._seed_demo_users()

    # -- seeding -----------------------------------------------------------
    def _seed_demo_users(self) -> None:
        """Idempotently seed the demo accounts for The Forest Season Resort."""
        self._add_user(
            user_id="user-forestseason-owner",
            username=DEMO_OWNER_USERNAME,
            display_name="Forest Season Owner",
            role=Role.OWNER,
            property_id=HOME_PROPERTY_ID,
            password=DEMO_OWNER_PASSWORD,
        )
        self._add_user(
            user_id="user-forestseason-manager",
            username=DEMO_MANAGER_USERNAME,
            display_name="Forest Season Manager",
            role=Role.MANAGER,
            property_id=HOME_PROPERTY_ID,
            password=DEMO_MANAGER_PASSWORD,
        )

    def _add_user(
        self,
        *,
        user_id: str,
        username: str,
        display_name: str,
        role: Role,
        property_id: str,
        password: str,
    ) -> None:
        key = username.lower()
        if key in self._users:
            return  # idempotent: do not re-hash / reset an existing user
        self._users[key] = User(
            id=user_id,
            username=username,
            display_name=display_name,
            role=role,
            property_id=property_id,
            password_hash=hash_password(password),
        )

    # -- lookup ------------------------------------------------------------
    def get_by_username(self, username: str) -> User | None:
        return self._users.get(username.lower())

    def get_by_id(self, user_id: str) -> User | None:
        for user in self._users.values():
            if user.id == user_id:
                return user
        return None

    def public_user(self, user: User) -> PublicUser:
        return _public(user)

    # -- authentication ----------------------------------------------------
    def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate credentials, enforcing basic lockout.

        Raises :class:`AccountLockedError` when the account is locked and
        :class:`InvalidCredentialsError` for unknown users / wrong passwords.
        """
        now = datetime.now(UTC)
        user = self.get_by_username(username)
        if user is None:
            # Avoid user enumeration: same error as a wrong password.
            raise InvalidCredentialsError("invalid credentials")

        if user.is_locked(now=now):
            raise AccountLockedError("account temporarily locked")

        if not verify_password(password, user.password_hash):
            user.failed_attempts += 1
            if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = now + LOCKOUT_DURATION
            raise InvalidCredentialsError("invalid credentials")

        # Success: reset lockout counters and issue a token.
        user.failed_attempts = 0
        user.locked_until = None
        token = issue_session_token(
            user_id=user.id,
            role=str(user.role),
            property_id=user.property_id,
        )
        return AuthResult(user=_public(user), token=token)

    def user_from_token(self, token: str) -> User | None:
        """Resolve the current :class:`User` from a session token, or ``None``."""
        payload = verify_session_token(token)
        if payload is None:
            return None
        return self.get_by_id(str(payload.get("sub", "")))


@lru_cache
def get_auth_service() -> AuthService:
    """Return the process-wide cached :class:`AuthService` (seeds on first use).

    Demo-grade caveat: because this singleton is cached for the life of the
    process, the mutable lockout counters (``failed_attempts`` / ``locked_until``
    on the seeded users) are shared across every request. A locked demo account
    therefore stays locked for ``LOCKOUT_DURATION`` (~15 min) for everyone on
    that process until it expires or the backend restarts; the test suite calls
    ``_reset_demo_owner`` to stay order-independent. Acceptable for a
    single-tenant demo, but a real deployment would key lockout per-user in
    durable storage.
    """
    return AuthService()
