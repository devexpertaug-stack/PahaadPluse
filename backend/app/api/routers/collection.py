"""Market Radar collection-job API endpoints (Req 1.3, 1.4, 1.10)."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.review import Platform
from app.services.market_radar.collector import (
    ConcurrentJobError,
    UploadRejectedError,
    parse_upload,
)
from app.services.market_radar.service import get_market_radar_service

router = APIRouter(prefix="/market-radar/collection", tags=["market-radar"])


def _job_payload(job) -> dict:  # noqa: ANN001 - CollectionJob
    return {
        "job_id": job.job_id,
        "platform": job.platform,
        "property_id": job.property_id,
        "started_at": job.started_at.isoformat(),
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "status": job.status,
        "new_count": job.new_count,
        "updated_count": job.updated_count,
        "failure_count": job.failure_count,
        "attempts": job.attempts,
    }


@router.get("/jobs")
async def list_jobs() -> dict:
    """List collection-job status records."""
    service = get_market_radar_service()
    return {"jobs": [_job_payload(j) for j in service.recent_jobs()]}


@router.post("/upload")
async def upload_reviews(
    platform: str = Form(...),
    property_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    """Ingest reviews from an uploaded CSV/JSON file (Req 1.3)."""
    try:
        selected = Platform(platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unknown platform {platform!r}") from exc

    data = await file.read()
    try:
        rows = parse_upload(data, file.filename or "upload.json")
    except UploadRejectedError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    service = get_market_radar_service()
    try:
        job = service.collector.ingest(selected, property_id, rows)
    except ConcurrentJobError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _job_payload(job)
