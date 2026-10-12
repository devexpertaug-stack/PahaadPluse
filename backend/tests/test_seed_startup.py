"""Tests for the run-path seed + startup lifespan (FEAT-003).

A fresh clone must become a populated, working backend from a single command.
These tests cover the explicit seed entrypoint and the FastAPI lifespan that
run on a cold start: the schema is created without raising, the seeded services
are warm, and every data endpoint returns non-empty data.
"""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.seed.warm import ensure_schema, seed_all, warm_services

DATA_ENDPOINTS = [
    "/market-radar/review-counts",
    "/market-radar/properties/mus-pineview/reviews",
    "/sentinel/board",
    "/sentinel/metrics",
    "/destination/heatmap",
    "/guest-compass/stays",
    "/guest-compass/metrics",
    "/concierge/metrics",
    "/market-radar/analytics/trends",
    "/minimal/impact",
]


def test_ensure_schema_is_idempotent() -> None:
    """Creating the schema twice must not raise (empty/absent DB safe)."""
    asyncio.run(ensure_schema())
    asyncio.run(ensure_schema())


def test_warm_services_is_idempotent() -> None:
    """Warming the seeded services repeatedly is a no-op and must not raise."""
    warm_services()
    warm_services()


def test_seed_all_is_idempotent() -> None:
    """The single seed entrypoint is safe to run repeatedly."""
    asyncio.run(seed_all())
    asyncio.run(seed_all())


def test_lifespan_warms_data_endpoints() -> None:
    """Entering the lifespan (TestClient context) yields populated endpoints."""
    with TestClient(app) as client:
        for path in DATA_ENDPOINTS:
            response = client.get(path)
            assert response.status_code == 200, path
            body = response.json()
            assert body not in ({}, [], None), path
            assert body, path
