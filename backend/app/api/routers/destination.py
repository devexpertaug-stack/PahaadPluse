"""Destination Lens API (Req 14).

Exposes the geocoded hotspot heatmap (filterable by theme + date range) and the
Evidence Packet PDF endpoint. Packet generation is restricted to the
destination_official role.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response

from app.services.destination_lens.entities import THEMES
from app.services.destination_lens.evidence_packet import EvidencePacketGenerator
from app.services.destination_lens.service import get_destination_lens_service

router = APIRouter(prefix="/destination", tags=["destination-lens"])


def _validate_theme(theme: str | None) -> str | None:
    if theme and theme not in THEMES:
        raise HTTPException(status_code=400, detail=f"unknown theme {theme!r}")
    return theme


@router.get("/themes")
async def themes() -> dict:
    """Available issue themes for the heatmap filter (Req 14.3)."""
    return {"themes": list(THEMES)}


@router.get("/heatmap")
async def heatmap(
    theme: str | None = Query(default=None),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
) -> dict:
    """Negative-mention hotspots filtered by theme + date range (Req 14.3)."""
    _validate_theme(theme)
    return get_destination_lens_service().heatmap_view(theme, start, end)


@router.get("/hotspots/{canonical}/quotes")
async def hotspot_quotes(
    canonical: str,
    theme: str | None = Query(default=None),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
) -> dict:
    """Representative public quotes for a hotspot (pseudonyms excluded)."""
    _validate_theme(theme)
    service = get_destination_lens_service()
    quotes = service.quotes_for(canonical, theme, start, end)
    return {
        "canonical": canonical,
        "quotes": [
            {
                "text": q.text,
                "platform": q.platform,
                "date": q.date.isoformat(),
                "source_url": q.source_url,
                "property_name": q.property_name,
            }
            for q in quotes
        ],
    }


@router.post("/evidence-packet")
async def evidence_packet(
    canonical: str = Query(...),
    theme: str | None = Query(default=None),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    language: str = Query(default="en"),
    role: str = Query(default="destination_official"),
) -> Response:
    """Generate an Evidence Packet PDF for a hotspot + theme (Req 14.4-14.8).

    Restricted to the ``destination_official`` role (Req 14.9). Returns the PDF
    with an ``X-Issues-Surfaced`` header reflecting the metric increment.
    """
    if role != "destination_official":
        raise HTTPException(
            status_code=403,
            detail="only destination_official may generate evidence packets",
        )
    _validate_theme(theme)
    service = get_destination_lens_service()
    generator = EvidencePacketGenerator(service)
    result = generator.generate(canonical, theme, start, end, language=language)
    return Response(
        content=result.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="evidence-{canonical}.pdf"',
            "X-Issues-Surfaced": str(result.issues_surfaced),
            "X-Quote-Count": str(result.quote_count),
            "X-Distinct-Properties": str(result.distinct_properties),
        },
    )


@router.get("/metrics")
async def destination_metrics() -> dict:
    """Issues-surfaced metric (Req 14.8)."""
    return {"issues_surfaced": get_destination_lens_service().issues_surfaced}
