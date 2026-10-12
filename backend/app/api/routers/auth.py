"""Auth_Service API (Req 30): login + current-user.

* ``POST /auth/login`` — exchange username/email + password for a signed
  session token and the resort-scoped user. Returns 401 on bad credentials and
  423 (Locked) when the account is locked out after repeated failures.
* ``GET /auth/me`` — resolve the current user from an ``Authorization: Bearer``
  token (or ``session`` cookie). Returns 401 when the token is missing/invalid.

Only ``/health`` and the WhatsApp webhook stay public (Req 30.1); existing demo
endpoints are intentionally left ungated so the demo keeps working.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.models.user import PublicUser, User
from app.services.auth.service import (
    AccountLockedError,
    AuthService,
    InvalidCredentialsError,
    get_auth_service,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login body. ``username`` accepts an email or a username."""

    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: PublicUser


def _extract_token(request: Request) -> str | None:
    """Pull a bearer token from the Authorization header or session cookie."""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    cookie = request.cookies.get("session")
    return cookie.strip() if cookie else None


def get_current_user(
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> User:
    """FastAPI dependency resolving the current user from the request token."""
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = auth.user_from_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Authenticate and issue a session token scoped to the user's property."""
    try:
        result = auth.authenticate(body.username, body.password)
    except AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="account temporarily locked due to repeated failed logins",
        ) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid username or password",
        ) from exc
    return LoginResponse(token=result.token, user=result.user)


@router.get("/me", response_model=PublicUser)
async def me(
    user: User = Depends(get_current_user),
    auth: AuthService = Depends(get_auth_service),
) -> PublicUser:
    """Return the current authenticated, resort-scoped user."""
    return auth.public_user(user)
