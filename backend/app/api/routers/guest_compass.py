"""Guest Compass API (Req 28).

Front-desk recommendations for a Stay, accept/decline outcome recording and the
uptake / ancillary-revenue metrics.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.guest_compass.service import StayContext, get_guest_compass
from app.services.sentinel.service import get_sentinel_service

router = APIRouter(prefix="/guest-compass", tags=["guest-compass"])


# Demo stays for the Guest Compass page (independent of the Sentinel seed, but a
# couple share Sentinel stay ids so P1/P2 suppression is observable).
_DEMO_STAYS: dict[str, dict] = {
    "gc-honeymoon": {
        "purpose": "honeymoon",
        "party": "couple",
        "check_in": "2024-06-10",
        "label": "Honeymoon couple · Deluxe",
    },
    "gc-family": {
        "purpose": "leisure",
        "party": "family",
        "check_in": "2024-06-12",
        "label": "Family of four · Valley suite",
    },
    "gc-business": {
        "purpose": "business",
        "party": "solo",
        "check_in": "2024-06-11",
        "label": "Business solo traveller",
    },
    "stay-charlie": {
        "purpose": "leisure",
        "party": "couple",
        "check_in": "2024-06-13",
        "label": "In-house stay with an open complaint",
    },
}


def _has_open_p1_p2(stay_id: str) -> bool:
    sentinel = get_sentinel_service()
    return any(
        c.stay_id == stay_id and c.is_open and str(c.urgency) in {"P1", "P2"}
        for c in sentinel.complaints.values()
    )


def _context(stay_id: str) -> StayContext:
    if stay_id not in _DEMO_STAYS:
        raise HTTPException(status_code=404, detail="unknown stay")
    spec = _DEMO_STAYS[stay_id]
    return StayContext(
        stay_id=stay_id,
        purpose=spec["purpose"],
        party=spec["party"],
        check_in=date.fromisoformat(spec["check_in"]),
        has_open_p1_p2=_has_open_p1_p2(stay_id),
        has_history=False,
    )


@router.get("/stays")
async def stays() -> dict:
    return {
        "stays": [
            {
                "id": sid,
                "label": spec["label"],
                "purpose": spec["purpose"],
                "party": spec["party"],
                "has_open_p1_p2": _has_open_p1_p2(sid),
            }
            for sid, spec in _DEMO_STAYS.items()
        ]
    }


@router.get("/recommendations/{stay_id}")
async def recommendations(stay_id: str) -> dict:
    compass = get_guest_compass()
    return compass.recommend(_context(stay_id))


class OutcomeRequest(BaseModel):
    item_id: str
    accepted: bool
    revenue_inr: float = 0.0


@router.post("/stays/{stay_id}/outcome")
async def record_outcome(stay_id: str, body: OutcomeRequest) -> dict:
    compass = get_guest_compass()
    ctx = _context(stay_id)
    try:
        outcome = compass.record_outcome(
            ctx, body.item_id, body.accepted, body.revenue_inr
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "outcome": {
            "stay_id": outcome.stay_id,
            "item_id": outcome.item_id,
            "accepted": outcome.accepted,
            "revenue_inr": outcome.revenue_inr,
        },
        "recommendations": compass.recommend(ctx),
        "metrics": compass.metrics(guests_this_week=len(_DEMO_STAYS)),
    }


@router.get("/metrics")
async def metrics() -> dict:
    return get_guest_compass().metrics(guests_this_week=len(_DEMO_STAYS))
