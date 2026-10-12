"""PahadPulse FastAPI application entrypoint.

Wires CORS for the frontend origin, the two public (unauthenticated) endpoints
required by Req 30.1 — ``GET /health`` and the WhatsApp inbound webhook — and
registers the (currently empty) subsystem routers.
"""

from __future__ import annotations

import json

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.adapters.whatsapp import get_default_gateway
from app.api.routers import ALL_ROUTERS
from app.core.config import get_settings
from app.services.sentinel.service import get_sentinel_service, record_bad_signature


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    app = FastAPI(
        title="PahadPulse API",
        version=__version__,
        description="Hospitality guest-intelligence platform for Uttarakhand hill towns.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Public, unauthenticated endpoints (Req 30.1) ----
    @app.get("/health", tags=["public"])
    async def health() -> dict[str, str]:
        """Public health check."""
        return {"status": "ok", "service": "pahadpulse", "version": __version__}

    @app.post("/webhooks/whatsapp", tags=["public"])
    async def whatsapp_webhook(request: Request) -> Response:
        """Public WhatsApp inbound webhook (Req 20).

        Verifies the HMAC-SHA256 signature when provided. A webhook that fails
        verification returns HTTP 403 and records an Audit_Log entry (Req 20.4).
        A verified (or unsigned demo) inbound message is routed into the Sentinel
        so a Hinglish complaint reaches the Checkout Shield.
        """
        payload = await request.body()
        signature = request.headers.get("x-hub-signature-256", "")
        gateway = get_default_gateway()
        if signature:
            if not gateway.verify_webhook(payload, signature):
                record_bad_signature(detail=f"signature={signature[:16]}...")
                return Response(status_code=status.HTTP_403_FORBIDDEN)

        # Route the inbound message into the Sentinel (Req 20.1-20.3).
        try:
            data = json.loads(payload or b"{}")
        except json.JSONDecodeError:
            data = {}
        from_number = data.get("from") or data.get("from_number")
        body = data.get("body") or data.get("text")
        if from_number and body:
            service = get_sentinel_service()
            service.intake_from_whatsapp(
                from_number, body, data.get("language", "hi-Latn")
            )
        return Response(status_code=status.HTTP_202_ACCEPTED)

    # ---- Subsystem routers (empty for now) ----
    for router in ALL_ROUTERS:
        app.include_router(router)

    return app


app = create_app()
