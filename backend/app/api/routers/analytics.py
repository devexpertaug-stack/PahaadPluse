"""Market Radar Deep-feature analytics API (Req 7-13, 16).

Exposes trends, the hierarchical decomposition, changepoints, the what-if
simulator, the time machine, the playbook, the gap finder and the benchmark
results to the website.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.benchmark.harness import OUTPUT_DIR, run_benchmark
from app.models.review import Aspect, Platform
from app.services.market_radar.analytics_service import get_analytics_service
from app.services.market_radar.trends import TrendValidationError

router = APIRouter(prefix="/market-radar/analytics", tags=["market-radar-analytics"])


def _parse_platforms(platforms: list[str] | None) -> list[Platform] | None:
    if not platforms:
        return None
    out: list[Platform] = []
    for p in platforms:
        try:
            out.append(Platform(p))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"unknown platform {p!r}") from exc
    return out


@router.get("/trends")
async def trends(
    granularity: str = Query(default="monthly"),
    platform: list[str] | None = Query(default=None),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
) -> dict:
    service = get_analytics_service()
    try:
        return service.trends_view(granularity, _parse_platforms(platform), start, end)
    except TrendValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/decomposition")
async def decomposition() -> dict:
    return get_analytics_service().decomposition_view()


@router.get("/changepoints")
async def changepoints() -> dict:
    return get_analytics_service().changepoints_view()


@router.get("/what-if/{platform}")
async def what_if_model(platform: str) -> dict:
    try:
        selected = Platform(platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unknown platform {platform!r}") from exc
    return get_analytics_service().what_if_model(selected)


class WhatIfRequest(BaseModel):
    deltas: dict[str, float]


@router.post("/what-if/{platform}/project")
async def what_if_project(platform: str, body: WhatIfRequest) -> dict:
    try:
        selected = Platform(platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unknown platform {platform!r}") from exc
    return get_analytics_service().what_if_project(selected, body.deltas)


@router.get("/time-machine")
async def time_machine(
    property_id: str = Query(...),
    at: date = Query(...),
    aspect: str | None = Query(default=None),
) -> dict:
    parsed_aspect = None
    if aspect:
        try:
            parsed_aspect = Aspect(aspect)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"unknown aspect {aspect!r}") from exc
    return get_analytics_service().time_machine_view(property_id, at, parsed_aspect)


@router.get("/playbook")
async def playbook() -> dict:
    return get_analytics_service().playbook_view()


@router.get("/gap-finder")
async def gap_finder() -> dict:
    return get_analytics_service().gap_finder_view()


@router.get("/benchmark")
async def benchmark() -> dict:
    """Return the latest benchmark results (regenerated deterministically)."""
    import json

    result_path = OUTPUT_DIR / "benchmark_results.json"
    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    return run_benchmark().to_dict()
