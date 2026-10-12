"""In-Stay Sentinel API (Req 15, 17-21).

Exposes the Checkout Shield board, the complaint queue + triage views,
complaint creation (multi-channel), resolution, reassignment, the week metrics
and the WhatsApp/voice demo helpers.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.sentinel import Channel, Department
from app.services.sentinel.service import get_sentinel_service

router = APIRouter(prefix="/sentinel", tags=["in-stay-sentinel"])


@router.get("/board")
async def board() -> dict:
    """The live Checkout Shield risk board (Req 15)."""
    return get_sentinel_service().board()


@router.get("/metrics")
async def metrics() -> dict:
    """Week metrics: complaint-to-department time, in-stay resolution rate, repeats."""
    return get_sentinel_service().metrics()


@router.get("/complaints")
async def complaints() -> dict:
    """The complaint queue with triage, SOP and recurrence details."""
    return {"complaints": get_sentinel_service().queue()}


@router.get("/stays")
async def stays() -> dict:
    """In-house stays available for complaint attachment (demo helper)."""
    service = get_sentinel_service()
    return {
        "stays": [
            {
                "id": s.id,
                "room": s.room,
                "guest_pseudonym": s.guest_pseudonym,
                "whatsapp_number": s.whatsapp_number,
                "check_out": s.check_out.isoformat(),
            }
            for s in service.stays.values()
        ]
    }


class CreateComplaintRequest(BaseModel):
    channel: str
    text: str
    stay_id: str | None = None
    language: str = "en"
    room: str | None = None


@router.post("/complaints")
async def create_complaint(body: CreateComplaintRequest) -> dict:
    service = get_sentinel_service()
    try:
        channel = Channel(body.channel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unknown channel {body.channel!r}") from exc
    result = service.create_complaint(
        channel=channel,
        text=body.text,
        stay_id=body.stay_id,
        language=body.language,
        room=body.room,
    )
    return {
        "complaint": service.complaint_view(result.complaint),
        "acknowledgement": result.acknowledgement,
        "risk": None if result.risk is None else result.risk.score,
    }


class ResolveRequest(BaseModel):
    note: str


@router.post("/complaints/{complaint_id}/resolve")
async def resolve(complaint_id: str, body: ResolveRequest) -> dict:
    service = get_sentinel_service()
    if complaint_id not in service.complaints:
        raise HTTPException(status_code=404, detail="unknown complaint")
    complaint = service.resolve_complaint(complaint_id, body.note)
    return {"complaint": service.complaint_view(complaint)}


class ReassignRequest(BaseModel):
    to_department: str
    reason: str


@router.post("/complaints/{complaint_id}/reassign")
async def reassign(complaint_id: str, body: ReassignRequest) -> dict:
    service = get_sentinel_service()
    if complaint_id not in service.complaints:
        raise HTTPException(status_code=404, detail="unknown complaint")
    try:
        dept = Department(body.to_department)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="unknown department") from exc
    complaint = service.reassign(complaint_id, dept, body.reason)
    return {"complaint": service.complaint_view(complaint)}


@router.post("/escalate-overdue")
async def escalate_overdue() -> dict:
    service = get_sentinel_service()
    escalated = service.escalate_overdue()
    return {"escalated": [service.complaint_view(c) for c in escalated]}


@router.get("/notifications")
async def notifications() -> dict:
    return {"notifications": get_sentinel_service().notifications}


class WhatsAppDemoRequest(BaseModel):
    from_number: str = "+919800000101"
    body: str = "room mein geyser kaam nahi kar raha"
    language: str = "hi-Latn"


@router.post("/demo/whatsapp")
async def demo_whatsapp(body: WhatsAppDemoRequest) -> dict:
    """Simulate an inbound WhatsApp complaint so the loop is demonstrable (Req 20)."""
    service = get_sentinel_service()
    result = service.intake_from_whatsapp(body.from_number, body.body, body.language)
    return {
        "complaint": service.complaint_view(result.complaint),
        "acknowledgement": result.acknowledgement,
        "risk": None if result.risk is None else result.risk.score,
    }


class VoiceDemoRequest(BaseModel):
    from_number: str = "+919800000101"
    # Demo "audio" header format: lang=<tag>;conf=<float>|<transcript>
    audio_text: str = "lang=hi;conf=0.9|room mein geyser kaam nahi kar raha"
    duration_seconds: float = 20.0


@router.post("/demo/voice")
async def demo_voice(body: VoiceDemoRequest) -> dict:
    """Simulate an inbound WhatsApp voice note (Req 21)."""
    service = get_sentinel_service()
    try:
        result = service.intake_from_voice(
            body.from_number, body.audio_text.encode("utf-8"), body.duration_seconds
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "complaint": service.complaint_view(result.complaint),
        "acknowledgement": result.acknowledgement,
    }
