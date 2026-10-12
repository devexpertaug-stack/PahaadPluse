"""Subsystem routers.

Each router is registered on the FastAPI app. For FEAT-001 they are empty
placeholders; later features add endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routers.analytics import router as analytics_router
from app.api.routers.collection import router as collection_router
from app.api.routers.reviews import router as market_radar_router

destination_router = APIRouter(prefix="/destination", tags=["destination-lens"])
sentinel_router = APIRouter(prefix="/sentinel", tags=["in-stay-sentinel"])
guest_compass_router = APIRouter(prefix="/guest-compass", tags=["guest-compass"])
concierge_router = APIRouter(prefix="/concierge", tags=["bhasha-concierge"])

ALL_ROUTERS = [
    market_radar_router,
    collection_router,
    analytics_router,
    destination_router,
    sentinel_router,
    guest_compass_router,
    concierge_router,
]

__all__ = [
    "market_radar_router",
    "collection_router",
    "analytics_router",
    "destination_router",
    "sentinel_router",
    "guest_compass_router",
    "concierge_router",
    "ALL_ROUTERS",
]
