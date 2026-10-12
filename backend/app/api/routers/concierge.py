"""Bhasha Concierge API (Req 29).

Handles inbound guest messages (grounded answers, handoff, complaint routing),
exposes the versioned Property_Facts + a fact-update endpoint, and the
queries-resolved-without-staff metric.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.concierge.service import get_concierge

router = APIRouter(prefix="/concierge", tags=["bhasha-concierge"])


class MessageRequest(BaseModel):
    message: str
    stay_id: str | None = None


@router.post("/message")
async def message(body: MessageRequest) -> dict:
    concierge = get_concierge()
    result = concierge.handle(body.message, stay_id=body.stay_id)
    return {"result": result.to_dict()}


@router.get("/facts")
async def facts() -> dict:
    concierge = get_concierge()
    return {
        "facts": [
            {
                "id": f.id,
                "topic": f.topic,
                "text": f.text,
                "version": f.version,
                "updated_at": f.updated_at.isoformat(),
            }
            for f in concierge.facts()
        ]
    }


class UpdateFactRequest(BaseModel):
    text: str


@router.post("/facts/{fact_id}")
async def update_fact(fact_id: str, body: UpdateFactRequest) -> dict:
    concierge = get_concierge()
    if not any(f.id == fact_id for f in concierge.facts()):
        raise HTTPException(status_code=404, detail="unknown fact")
    updated = concierge.update_fact(fact_id, body.text)
    return {
        "fact": {
            "id": updated.id,
            "topic": updated.topic,
            "text": updated.text,
            "version": updated.version,
            "updated_at": updated.updated_at.isoformat(),
        }
    }


@router.get("/conversation")
async def conversation() -> dict:
    concierge = get_concierge()
    return {
        "turns": [
            {
                "at": t.at.isoformat(),
                "language": t.language,
                "question": t.question,
                "result": t.result.to_dict(),
            }
            for t in concierge.history
        ]
    }


@router.get("/metrics")
async def metrics() -> dict:
    return get_concierge().metrics()
