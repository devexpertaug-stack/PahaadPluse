"""Minimal differentiating-feature API (Req 22, 23, 24, 25, 26, 27).

Exposes the Drilldown engine plus Proof of Impact, Complaint Forecasting,
Authenticity-adjusted benchmarks, closed-loop review replies and the owner's
weekly Hindi voice briefing. These sit under the Market Radar / Sentinel
subsystems on the website.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.review import Aspect, Platform, SentimentLabel
from app.services.common.drilldown import get_drilldown_service
from app.services.concierge.service import get_concierge  # noqa: F401 (shared process)
from app.services.market_radar.authenticity import get_authenticity_filter
from app.services.market_radar.briefing import BriefingGenerator
from app.services.market_radar.impact import ImpactEstimator
from app.services.market_radar.intervention_store import get_intervention_store
from app.services.market_radar.replies import ReplyComposer, ReviewToReply
from app.services.sentinel.forecast import ComplaintForecaster
from app.services.sentinel.service import get_sentinel_service

router = APIRouter(prefix="/minimal", tags=["minimal-features"])


# ---------------------------------------------------------------------------
# F14 Drilldown (Req 27)
# ---------------------------------------------------------------------------
def _parse_aspect(aspect: str | None) -> Aspect | None:
    if not aspect:
        return None
    try:
        return Aspect(aspect)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unknown aspect {aspect!r}") from exc


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


@router.get("/drilldown")
async def drilldown(
    metric: str = Query(...),
    kind: str = Query(default="count"),
    clicked_value: float = Query(...),
    property_id: str | None = Query(default=None),
    aspect: str | None = Query(default=None),
    label: str | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    period: date | None = Query(default=None),
    granularity: str | None = Query(default=None),
) -> dict:
    """Resolve a displayed number to its exact source records (Req 27)."""
    service = get_drilldown_service()
    parsed_aspect = _parse_aspect(aspect)
    parsed_platforms = _parse_platforms(platform)
    parsed_label = None
    if label:
        try:
            parsed_label = SentimentLabel(label)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"unknown label {label!r}") from exc

    if kind == "count":
        result = service.count_metric(
            metric=metric,
            clicked_value=int(clicked_value),
            property_id=property_id,
            aspect=parsed_aspect,
            platforms=parsed_platforms,
            label=parsed_label,
            start=start,
            end=end,
            period=period,
            granularity=granularity,
        )
    else:
        result = service.share_or_score_metric(
            metric=metric,
            clicked_value=clicked_value,
            property_id=property_id,
            aspect=parsed_aspect,
            platforms=parsed_platforms,
            start=start,
            end=end,
            period=period,
            granularity=granularity,
        )
    return result.to_dict()


# ---------------------------------------------------------------------------
# F10 Proof of Impact (Req 24)
# ---------------------------------------------------------------------------
class LogInterventionRequest(BaseModel):
    property_id: str
    aspect: str
    description: str
    date: date


@router.post("/interventions")
async def log_intervention(body: LogInterventionRequest) -> dict:
    store = get_intervention_store()
    aspect = _parse_aspect(body.aspect)
    iv = store.log(
        property_id=body.property_id,
        aspect=aspect,
        description=body.description,
        on=body.date,
    )
    estimator = ImpactEstimator(home_property_id=body.property_id)
    return {
        "intervention": {
            "id": iv.id,
            "property_id": iv.property_id,
            "aspect": iv.aspect,
            "description": iv.description,
            "date": str(iv.date),
        },
        "impact": estimator.estimate(iv).to_dict(),
    }


@router.get("/impact")
async def impact() -> dict:
    """Proof-of-Impact estimates for all logged interventions."""
    store = get_intervention_store()
    estimator = ImpactEstimator()
    results = [estimator.estimate(iv).to_dict() for iv in store.interventions.values()]
    return {"results": results}


# ---------------------------------------------------------------------------
# F11 Complaint Forecasting (Req 25)
# ---------------------------------------------------------------------------
@router.get("/forecast")
async def forecast(aspect: str | None = Query(default=None)) -> dict:
    forecaster = ComplaintForecaster()
    aspects = [_parse_aspect(aspect)] if aspect else None
    return forecaster.forecast_all(aspects)


# ---------------------------------------------------------------------------
# F9 Authenticity-adjusted benchmarks (Req 23)
# ---------------------------------------------------------------------------
@router.get("/authenticity")
async def authenticity() -> dict:
    return get_authenticity_filter().adjusted_view()


# ---------------------------------------------------------------------------
# F13 Closed-loop review replies (Req 26)
# ---------------------------------------------------------------------------
class DraftReplyRequest(BaseModel):
    review_id: str
    property_id: str
    text: str
    detected_language: str = "en"
    negative_aspects: list[str] = []


@router.post("/replies/draft")
async def draft_reply(body: DraftReplyRequest) -> dict:
    store = get_intervention_store()
    composer = ReplyComposer()
    aspects = [_parse_aspect(a) for a in body.negative_aspects]
    review = ReviewToReply(
        id=body.review_id,
        property_id=body.property_id,
        text=body.text,
        detected_language=body.detected_language,
        negative_aspects=[a for a in aspects if a is not None],
    )
    resolved = _resolved_complaints_for(body.property_id)
    draft = composer.compose(
        review,
        interventions=store.for_property(body.property_id),
        resolved_complaints=resolved,
    )
    store.save_reply(draft)
    return {"reply": draft.model_dump(mode="json")}


class ApproveReplyRequest(BaseModel):
    approver: str
    edited_body: str | None = None


@router.post("/replies/{reply_id}/approve")
async def approve_reply(reply_id: str, body: ApproveReplyRequest) -> dict:
    store = get_intervention_store()
    draft = store.replies.get(reply_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="unknown reply draft")
    ReplyComposer.approve(draft, body.approver, body.edited_body)
    return {"reply": draft.model_dump(mode="json")}


def _resolved_complaints_for(property_id: str) -> list[dict]:
    sentinel = get_sentinel_service()
    out: list[dict] = []
    for c in sentinel.complaints.values():
        if c.property_id != property_id:
            continue
        if str(c.state) != "resolved":
            continue
        out.append(
            {
                "id": c.id,
                "aspect": _issue_to_aspect(c.issue_type),
                "resolution_note": c.resolution_note,
            }
        )
    return out


def _issue_to_aspect(issue_type: str | None) -> str | None:
    mapping = {
        "cleanliness": "Cleanliness",
        "housekeeping": "Housekeeping",
        "food": "Food",
        "room": "Room",
        "wifi": "Service",
        "service": "Service",
    }
    return mapping.get(issue_type or "")


# ---------------------------------------------------------------------------
# F7 Owner's weekly Hindi voice briefing (Req 22)
# ---------------------------------------------------------------------------
class BriefingRequest(BaseModel):
    opted_in_owners: list[str] = ["+919800000900"]


@router.post("/briefing")
async def briefing(body: BriefingRequest) -> dict:
    sentinel = get_sentinel_service()
    changepoints = get_changepoint_count()
    open_p1_p2 = sum(
        1
        for c in sentinel.complaints.values()
        if c.is_open and str(c.urgency) in {"P1", "P2"}
    )
    generator = BriefingGenerator()
    result = generator.generate(
        open_p1_p2=open_p1_p2,
        new_changepoints=changepoints,
        opted_in_owners=body.opted_in_owners,
    )
    return {"briefing": result.to_dict()}


def get_changepoint_count() -> int:
    from app.services.market_radar.analytics_service import get_analytics_service

    run = get_analytics_service().changepoint_run()
    home = run.notifications
    return len(home)
