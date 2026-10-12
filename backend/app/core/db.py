"""Async SQLAlchemy engine and session management.

Defaults to a local SQLite file under ``backend/data/`` so no external database
daemon is required for the demo.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _ensure_sqlite_dir(database_url: str) -> None:
    """Create the parent directory for a local SQLite file if needed."""
    marker = "sqlite+aiosqlite:///"
    if database_url.startswith(marker):
        rel = database_url[len(marker) :]
        if rel and rel != ":memory:":
            Path(rel).parent.mkdir(parents=True, exist_ok=True)


def create_engine() -> AsyncEngine:
    """Create the async engine from configured settings."""
    settings = get_settings()
    _ensure_sqlite_dir(settings.database_url)
    return create_async_engine(settings.database_url, future=True, echo=False)


engine: AsyncEngine = create_engine()
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an async database session."""
    async with SessionLocal() as session:
        yield session
