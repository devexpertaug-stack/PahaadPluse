"""Market Radar review + admin API endpoints (Req 1.10, 5.7)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.market_radar.service import get_market_radar_service

router = APIRouter(prefix="/market-radar", tags=["market-radar"])


@router.get("/review-counts")
async def review_counts() -> dict:
    """Per-property, per-platform review counts for the Market Radar page."""
    service = get_market_radar_service()
    return {"properties": service.property_platform_counts()}


@router.get("/properties/{property_id}/reviews")
async def property_reviews(
    property_id: str,
    platform: str | None = Query(default=None),
) -> dict:
    """Reviews for a single property (optionally filtered by platform)."""
    service = get_market_radar_service()
    reviews = service.reviews_for(property_id, platform)
    if not reviews and property_id not in {
        p["property_id"] for p in service.property_platform_counts()
    }:
        raise HTTPException(status_code=404, detail=f"unknown property {property_id!r}")
    return {"property_id": property_id, "reviews": reviews}


@router.get("/admin/unmapped-categories")
async def unmapped_categories(threshold: int = Query(default=20, ge=0)) -> dict:
    """Admin surface: unmapped sub-rating categories over the threshold."""
    service = get_market_radar_service()
    return {
        "threshold": threshold,
        "categories": service.unmapped_categories(threshold),
    }
