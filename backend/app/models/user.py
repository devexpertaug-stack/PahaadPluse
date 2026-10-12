"""User account domain model for the demo auth service (Req 30).

Users authenticate against the Auth_Service, which issues a signed session
token carrying the user's role and property scope. Passwords are stored only as
hashes (see :mod:`app.core.security`), never in plaintext. Basic account
lockout fields support throttling repeated failed logins (demo-grade).

The model is kept demo-grade and in-memory (consistent with the other
``@lru_cache`` singleton services); it is intentionally pydantic rather than an
ORM table.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    """Account roles recognised by the platform (Req 30)."""

    OWNER = "owner"
    MANAGER = "manager"
    FRONT_DESK = "front_desk"
    DEPARTMENT_STAFF = "department_staff"
    DESTINATION_OFFICIAL = "destination_official"
    ADMIN = "admin"


class User(BaseModel):
    """A platform user scoped to a single property (Req 30 property scoping)."""

    id: str
    username: str
    display_name: str
    role: Role
    property_id: str
    password_hash: str
    # ---- Basic account lockout (demo-grade) ----
    failed_attempts: int = 0
    locked_until: datetime | None = None

    def is_locked(self, *, now: datetime) -> bool:
        """Return whether the account is currently locked out."""
        return self.locked_until is not None and now < self.locked_until


class PublicUser(BaseModel):
    """The user projection returned to clients (no secrets)."""

    id: str
    username: str
    display_name: str
    role: Role
    property_id: str
    property_name: str = Field(default="")
