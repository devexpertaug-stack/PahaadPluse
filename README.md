# PahadPulse

**PahadPulse** is a closed-loop hospitality guest-intelligence platform for
Uttarakhand hill towns (Mussoorie and beyond). It is delivered as a **single
professional website**: a Python **FastAPI** backend and a **Next.js**
(App Router + TypeScript + Tailwind) dashboard sharing one cohesive
green/white + forest + hill-town design system.

> This repository is being built feature by feature. **FEAT-001** established
> the green baseline: scaffolding, the themed design system, the
> external-service adapter interfaces with working local/fallback
> implementations, and a single demo command. **FEAT-002** adds the Market
> Radar foundation data layer — the canonical review pipeline (parse → collect →
> language/transliteration → aspect normalisation → aspect-level sentiment), the
> published Review_Record JSON schema, responsible-collection controls, the
> checked-in sample Mussoorie dataset + datasheet and the Hinglish evaluation
> set — surfaced on the `/market-radar` pages. Other subsystems remain themed
> placeholders that later features fill in.

## Market Radar data layer (FEAT-002)

The canonical review pipeline lives in `backend/app/services/market_radar/`:

- `parsing.py` — Review_Parser / Review_Printer with the per-platform linear
  native→normalised rating mapping (native min→1.0, max→5.0) and schema-valid
  canonical JSON.
- `collector.py` — Review_Collector: upload (≤20 MB / ≤10 000) + sample dataset
  + adapters, dedupe by `(platform, platform_review_id)`, new/updated/failure
  counts, 30/60/120/240/480s retry cap and a per-(property, platform)
  concurrent-job guard.
- `responsible.py` — robots.txt + 24h cache, 1 req/5s rate limit, PahadPulse
  contact user-agent and salted-hash pseudonymisation (salt from env only).
- `language.py` — language detection (en/hi/hi-Latn/und + script) and reversible
  Hinglish ↔ Devanagari transliteration.
- `aspects.py` — versioned cross-platform Aspect_Normalizer over the nine
  canonical aspects.
- The Sentiment_Engine lives in `backend/app/adapters/sentiment.py` (deterministic
  fallback + MuRIL/IndicBERT stub behind one interface).

Checked-in datasets under `data/` (regenerate from the backend):

```bash
cd backend
uv run python scripts/gen_schema.py            # Review_Record JSON schema
uv run python scripts/build_dataset.py         # sample_reviews + datasheet counts
uv run python scripts/build_hinglish_test_set.py  # Hinglish evaluation set + kappa
```

## The single demo command (Req 34.1)

```bash
make setup   # one-time: backend uv sync + frontend npm install
make demo    # seeds demo data, then starts the API and the website
```

`make demo` now **seeds and initialises the backend before launching the
servers**, so a fresh clone yields a populated, working dashboard end to end:

1. It runs the explicit seed step (`cd backend && uv run python -m app.seed`),
   which ensures `backend/data/` exists, creates the database schema, and warms
   every in-memory service so the sample dataset is loaded eagerly. The step is
   idempotent — safe to run repeatedly.
2. It then launches the FastAPI backend and the Next.js website concurrently,
   wiring `NEXT_PUBLIC_API_BASE_URL` and CORS so the browser can reach the API,
   and prints the dashboard URL (http://localhost:3000).

The backend also runs this same seed on startup via a FastAPI lifespan hook, so
the services are warm the moment the API accepts requests (and any seeding error
surfaces at startup rather than on the first browser request) regardless of how
uvicorn is launched.

To seed the backend independently (e.g. before running the API by hand):

```bash
cd backend && uv run python -m app.seed
```

## Signing in (demo credentials)

The dashboard is gated behind a demo login (`/login`). The seed step creates an
**owner/manager account for The Forest Season Resort** (`mus-forestseason`) with
known, documented credentials. Passwords are stored only as argon2 hashes; the
login endpoint returns a signed session token (HMAC keyed on `SESSION_SECRET`)
that expires after ~12 hours.

| Role    | Username                       | Password            |
| ------- | ------------------------------ | ------------------- |
| Owner   | `owner@forestseason.demo`      | `ForestSeason@2024` |
| Manager | `manager@forestseason.demo`    | `Mussoorie@2024`    |

Sign in at `http://localhost:3000/login` (the login page also shows a one-click
"demo credentials" hint). The header then shows the logged-in user and the
property scope (The Forest Season Resort), with a **Log out** action. Repeated
failed logins trigger a basic account lockout.

The auth API: `POST /auth/login` → `{ token, user }`; `GET /auth/me` →
the current resort-scoped user (send `Authorization: Bearer <token>`). Only
`GET /health` and the WhatsApp webhook stay public (Req 30.1).

## Architecture (text diagram)

```
                         ┌──────────────────────────────────────────┐
   Browser ──────────▶   │  Next.js website (frontend/)              │
   (one website)         │  App Router · TypeScript · Tailwind       │
                         │  Themed design system + app shell         │
                         │  Pages: Metrics home + every subsystem    │
                         └───────────────┬──────────────────────────┘
                                         │  typed fetch (lib/api.ts)
                                         ▼
                         ┌──────────────────────────────────────────┐
                         │  FastAPI backend (backend/app/)           │
                         │  api/routers · services · core · models  │
                         │                                           │
                         │  Adapters (interface + local fallback):   │
                         │   sentiment · llm · whatsapp · voice ·    │
                         │   geocoder                                │
                         └───────────────┬──────────────────────────┘
                                         ▼
                         ┌──────────────────────────────────────────┐
                         │  SQLite (backend/data/) · audit · config  │
                         └──────────────────────────────────────────┘
```

Every external service is behind an **adapter interface** with a working
local/mock/fallback implementation selected by config, so the platform runs with
**no third-party credentials**.

## Subsystems (one website, one page each)

| Subsystem           | Routes |
| ------------------- | ------ |
| Metrics Overview    | `/` |
| Market Radar        | `/market-radar`, `/time-machine`, `/what-if`, `/playbook`, `/gap-finder` |
| Destination Lens    | `/destination` |
| In-Stay Sentinel    | `/checkout-shield`, `/complaints` |
| Guest Compass       | `/guest-compass` |
| Bhasha Concierge    | `/concierge`, `/benchmark` |

## Deep vs Minimal feature map

Features flagged **Deep** are built fully; the rest are **Minimal** scaffolds.

| Code | Feature                         | Tier    |
| ---- | ------------------------------- | ------- |
| F1   | What-If Simulator               | Deep    |
| F2   | Time Machine                    | Deep    |
| F3   | Checkout Shield                 | Deep    |
| F4   | Market Radar data layer         | Deep    |
| F5   | Playbook                        | Deep    |
| F6   | Gap Finder                      | Deep    |
| F7   | (Destination baseline)          | Minimal |
| F8   | Destination Heatmap + Evidence  | Deep    |
| F12  | Hinglish Benchmark              | Deep    |

## Repository layout

```
backend/     FastAPI service (app/: core, models, schemas, adapters, services, api/routers)
frontend/    Next.js website (app/ routes, components/ design system + shell, lib/)
scripts/     demo.sh (invoked by `make demo`)
data/        checked-in dataset artifacts (sample_reviews, datasheet, hinglish_test_set)
.env.example documents all external config and feature flags (Req 32.2)
Makefile     setup · test · lint · build · demo
```

## Local development

```bash
# Backend (Python 3.11 via uv)
cd backend && uv sync && uv run ruff check . && uv run pytest

# Frontend (Node 22)
cd frontend && npm install && npm run lint && npm run build && npm test
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for conventions.

## In-Stay Sentinel demos (no live provider)

```bash
cd backend
# Simulate an inbound Hinglish WhatsApp complaint and watch it reach the
# Checkout Shield with an updated Risk_Score (mock gateway, offline):
uv run python -m app.services.sentinel.demo

# Regenerate the Risk_Scorer validation (ROC AUC + calibration) on a held-out
# synthetic set — results land in data/sentinel/:
uv run python -m app.services.sentinel.validation
```

The Destination Lens Evidence Packet (PDF, with an optional Hindi/Devanagari
mode) is generated by the `destination_official` role via
`POST /destination/evidence-packet`. The Checkout Shield board at
`/checkout-shield` refreshes every 4s (short polling; see
[docs/risk_scorer_validation.md](./docs/risk_scorer_validation.md) for the
rationale).
