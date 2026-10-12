# PahadPulse backend

FastAPI service for PahadPulse. Python 3.11 managed with `uv`.

```bash
uv sync
uv run ruff check .
uv run pytest
uv run uvicorn app.main:app --reload
```

Only two endpoints are unauthenticated (Req 30.1):

- `GET /health`
- `POST /webhooks/whatsapp` (WhatsApp inbound webhook placeholder)

All external services are behind adapters in `app/adapters/` with local
fallback implementations selected by config, so the service runs with no
third-party credentials.
