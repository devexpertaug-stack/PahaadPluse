"""PahadPulse FastAPI application entrypoint.

Wires CORS for the frontend origin, the two public (unauthenticated) endpoints
required by Req 30.1 — ``GET /health`` and the WhatsApp inbound webhook — and
registers the (currently empty) subsystem routers.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.adapters.whatsapp import get_default_gateway
from app.api.routers import ALL_ROUTERS
from app.core.config import get_settings


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
        """Public WhatsApp inbound webhook placeholder.

        Verifies the HMAC signature (Req 20.4) when provided. For FEAT-001 this
        only acknowledges receipt; later features parse and route the payload.
        """
        payload = await request.body()
        signature = request.headers.get("x-hub-signature-256", "")
        gateway = get_default_gateway()
        verified = False
        if signature:
            verified = gateway.verify_webhook(payload, signature)
            if not verified:
                return Response(status_code=status.HTTP_401_UNAUTHORIZED)
        return Response(status_code=status.HTTP_202_ACCEPTED)

    # ---- Subsystem routers (empty for now) ----
    for router in ALL_ROUTERS:
        app.include_router(router)

    return app


app = create_app()
