"""Subsystem routers.

Each router is registered on the FastAPI app.
"""

from __future__ import annotations

from app.api.routers.analytics import router as analytics_router
from app.api.routers.auth import router as auth_router
from app.api.routers.collection import router as collection_router
from app.api.routers.concierge import router as concierge_router
from app.api.routers.destination import router as destination_router
from app.api.routers.guest_compass import router as guest_compass_router
from app.api.routers.minimal import router as minimal_router
from app.api.routers.reviews import router as market_radar_router
from app.api.routers.sentinel import router as sentinel_router

ALL_ROUTERS = [
    auth_router,
    market_radar_router,
    collection_router,
    analytics_router,
    destination_router,
    sentinel_router,
    minimal_router,
    guest_compass_router,
    concierge_router,
]

__all__ = [
    "auth_router",
    "market_radar_router",
    "collection_router",
    "analytics_router",
    "destination_router",
    "sentinel_router",
    "minimal_router",
    "guest_compass_router",
    "concierge_router",
    "ALL_ROUTERS",
]
