# Contributing to PahadPulse

Thanks for helping build PahadPulse. This guide covers conventions for the
monorepo (FastAPI backend + Next.js website).

## Prerequisites

- **Python 3.11** managed by [`uv`](https://docs.astral.sh/uv/). The system
  Python may be older, so the backend pins `3.11.15` via `backend/.python-version`.
- **Node 22** with `npm`.

## Setup

```bash
make setup   # backend: uv sync · frontend: npm install
cp .env.example .env   # fill values as needed; defaults run fully offline
```

## Project structure

- `backend/app/core` — config (pydantic-settings), db session, security, audit.
- `backend/app/adapters` — one module per external service. Each defines an
  **interface** plus a **local/fallback implementation**. Never call an external
  service directly from a service module; always go through an adapter.
- `backend/app/api/routers` — one router per subsystem.
- `frontend/components/ui` — the themed design-system component library.
- `frontend/components/layout` — the shared app shell (sidebar + header).
- `frontend/app` — one route per subsystem page.

## Secrets & privacy (Req 32.2)

- Real secrets, encryption keys, and the pseudonymisation salt live **only** in
  `.env` or a secrets store, **never** in source control or dataset files.
- `.env.example` documents every variable with safe placeholder values.

## Testing & quality gates

```bash
# Backend
cd backend && uv run ruff check . && uv run pytest

# Frontend
cd frontend && npm run lint && npm run build && npm test
```

All checks must be green before committing.

## Commit conventions

Use conventional-commit prefixes: `feat:`, `fix:`, `chore:`, `docs:`,
`refactor:`. Keep each commit scoped to a single feature.
