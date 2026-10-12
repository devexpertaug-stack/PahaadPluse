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

## The demo in one line

**[The Forest Season Resort](#the-forest-season-resort-demo-home-property)** —
a Mussoorie resort set in the deodar forest — is the demo's **home property**.
It carries ~18 months of multilingual, multi-platform reviews so every analytics
page has real depth. To run the full populated, login-capable stack:

```bash
make setup   # one-time: backend uv sync + frontend npm install
make demo    # seeds the resort data + demo users, then starts both servers
```

Then open **http://localhost:3000**, go to `/login`, and sign in with:

| Role    | Username                    | Password            |
| ------- | --------------------------- | ------------------- |
| Owner   | `owner@forestseason.demo`   | `ForestSeason@2024` |
| Manager | `manager@forestseason.demo` | `Mussoorie@2024`    |

Everything runs **FREE with no third-party credentials**. See
[Signing in](#signing-in-demo-credentials), the
[honesty note](#is-this-real-scraped-data-honesty-note), and
[Getting a live URL (free)](#getting-a-live-url-free) below.

## The Forest Season Resort (demo home property)

The cluster's **home property is The Forest Season Resort** (`mus-forestseason`),
a Mussoorie resort in the deodar forest. It is the account you log in as and the
property every dashboard centres on. Its ~18-month, five-platform
(Google / MakeMyTrip / Booking.com / TripAdvisor / Agoda) review history is run
through the real ingestion pipeline so the Deep analytics — time-series
decomposition, Bayesian changepoint detection, Time Machine, Playbook,
gap-finder, Checkout Shield risk scoring — all have genuine depth. Six
surrounding Mussoorie properties act as competitors to give cluster context. The
dataset itself is **synthetic/representative** (see the honesty note); it is run
through the identical pipeline that real collected reviews would use.

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

**Known limitation (demo-grade auth).** The login is a **UI gate, not a
multi-tenant authorization boundary**. Only `/auth/*` enforces the token today;
the data endpoints (market-radar / sentinel / concierge / destination / minimal)
are intentionally left open and no route checks the token's `property_id` scope,
so this is a single-property demo and must not be read as tenant isolation. The
lockout state also lives on a single process-wide auth singleton, so a locked
demo account stays locked for ~15 minutes **for everyone** on that process — if
you fat-finger the password five times before a live presentation, restart the
backend (or wait out the lockout) to clear it.

The `/login` screen is a full-bleed branded page: a vibrant alpine gradient with
layered mountain/forest silhouettes, built entirely from the theme and inline
SVG so it stays free and self-contained (no external or copyrighted image). To
use your own photo instead, drop it into `frontend/public/` (e.g.
`login-bg.jpg`) and set a single `backgroundImage` on the root `<div>` of
`frontend/app/login/page.tsx` (e.g. `style={{ backgroundImage:
"url(/login-bg.jpg)" }}`); the gradient overlay is kept semi-transparent so it
still reads well over a photo.

## Is this real scraped data? (honesty note)

**No — and deliberately so.** The review corpus is a **synthetic, representative
dataset**, not a verbatim scrape of any platform. It is written to mirror the
structure, length, rating distribution and language mix (English / Devanagari /
Hinglish) of genuine public Mussoorie reviews, and it is run through the
**real** ingestion/collection pipeline exactly as live-collected reviews would
be:

```
Review_Collector → Review_Parser (parse) → language/transliteration
→ aspect-level sentiment → Aspect_Normalizer (normalise)
→ market model → Bayesian changepoints
```

The Forest Season Resort's reviews are produced by a deterministic, seeded
generator (`backend/app/seed/forest_season_reviews.py`), then fed through the
identical `ReviewParser` + enrichment path; the same JSON can be POSTed to
`POST /market-radar/collection/upload` to exercise the live Review_Collector end
to end.

**Genuine live scraping of Google, MakeMyTrip, Booking.com, TripAdvisor and
Agoda is NOT performed.** Doing so requires each platform's **official API or
written permission** and must respect each site's **robots.txt and terms of
service** — there is no free, credential-less path that honours those terms. The
scrape-mode mechanism is kept for authenticity in
`backend/app/services/market_radar/responsible.py`: it fetches and caches
robots.txt (24h), skips disallowed URLs, rate-limits to ≤1 request / 5s per
domain, disables a domain on server errors, and sends an identified
`PahadPulse/<version> (+mailto:<contact>)` user-agent. Reviewer identities are
never stored — only a salted-HMAC `author_pseudonym`.

Everything in this demo therefore runs **FREE, offline, with no third-party
credentials**. Full provenance, counts and pseudonymisation details are in
[`data/datasheet.md`](./data/datasheet.md).

## Getting a live URL (free)

You asked for a public live URL. This project is **deploy-ready** and there are
several **zero-cost** ways to get one. **No paid AWS or other cloud resources
are provisioned by this project** — there is no infra-as-code that spins up paid
services. A real managed cloud deployment (including anything on your AWS
credits) is a **separate, explicitly-confirmed step** and is intentionally not
done automatically.

> The app reads two configurable values: the frontend calls the API via
> **`NEXT_PUBLIC_API_BASE_URL`** (default `http://127.0.0.1:8000`, see
> [`frontend/.env.example`](./frontend/.env.example)); the backend allows the
> browser origin via **`FRONTEND_ORIGIN`** (CORS, see
> [`.env.example`](./.env.example)). Point these at each other and the deployed
> frontend and backend talk cleanly.

### Option A — GitHub Codespaces (fastest free public URL)

1. Push this repo to GitHub, then **Code → Codespaces → Create codespace**. The
   included [`.devcontainer/devcontainer.json`](./.devcontainer/devcontainer.json)
   installs Python 3.11, Node 22 and `uv` and runs `make setup` automatically.
2. In the Codespace terminal, run `make demo`.
3. Open the **Ports** panel, find port **3000**, and set its **Visibility to
   Public** — Codespaces gives you an instant `https://…-3000.app.github.dev`
   URL you can share for the demo. (Port 8000 is forwarded too; the frontend in
   the Codespace reaches the API over `localhost`, so you usually only make 3000
   public.)

> **Set a strong `SESSION_SECRET` before you make the port public.** `make demo`
> otherwise signs session tokens with the committed default
> (`dev-only-session-secret-change-me`), which anyone can read from this repo and
> use to forge tokens on a public URL. Export a strong secret (and
> `PSEUDONYM_SALT` / `PII_ENCRYPTION_KEY`) in the Codespace terminal **before**
> `make demo`, e.g. `export SESSION_SECRET="$(openssl rand -hex 32)"`, or set
> them as Codespaces secrets.

Codespaces includes a monthly free usage allowance; stop the codespace when
you are done. **Free, nothing provisioned in your cloud account.**

### Option B — Vercel (frontend) + a free-tier backend

Deploy the two halves on free tiers and wire them with the env vars above:

1. **Backend** on a free tier (Render / Railway / Fly.io free plan):
   - Start command (example): `cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Set **`FRONTEND_ORIGIN`** to your Vercel URL, e.g.
     `https://pahadpulse.vercel.app` (this is the CORS allow-list).
   - Set a strong **`SESSION_SECRET`** (and `PSEUDONYM_SALT`, `PII_ENCRYPTION_KEY`).
   - Note the public API URL it gives you, e.g. `https://pahadpulse-api.onrender.com`.
2. **Frontend** on **Vercel free tier** (root directory `frontend/`):
   - Set **`NEXT_PUBLIC_API_BASE_URL`** to the backend URL from step 1.
   - Deploy — Vercel gives you the public `https://…vercel.app` URL.
3. Open the Vercel URL, go to `/login`, and sign in with the demo credentials.

Free tiers only; **no paid AWS/cloud resources** are required or provisioned.

### Option C — Free tunnel over local `make demo`

For a quick temporary public URL from your own machine while `make demo` runs:

```bash
make demo                              # terminal 1: local stack on :3000 / :8000
cloudflared tunnel --url http://localhost:3000   # terminal 2 (or: ngrok http 3000)
```

The tunnel prints a public `https://…` URL. Cloudflare Quick Tunnels and
ngrok's free tier are both **free**. For login to work through the tunnel, the
browser and the API must agree on origins: either run the API behind a second
tunnel and set `NEXT_PUBLIC_API_BASE_URL` + `FRONTEND_ORIGIN` to the tunnel
URLs, or prefer Option A/B which handle this cleanly.

> **Note on this sandbox.** The build/CI sandbox cannot itself open a public
> listener (a dev-server guard blocks live `uvicorn`/`next dev`), so the live
> URL is produced by **you** running one of the free options above from your own
> machine or Codespace. The code paths are verified in-process here (seed +
> `TestClient`); the servers run normally on a real machine via `make demo`.

### Optional — local containers (free, provisions nothing)

If you prefer containers for a Codespace or local run, you can containerise the
two apps for **local/Codespaces use only** (nothing is provisioned in any
cloud). This repo ships the devcontainer above rather than a Dockerfile to keep
`make demo` the single, simplest entry point; add a `Dockerfile`/`compose.yml`
yourself only if your target host needs it.

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
