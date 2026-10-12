# PahadPulse

**PahadPulse** is a closed-loop hospitality guest-intelligence platform for
Uttarakhand hill towns (Mussoorie and beyond). It is delivered as a **single
professional website**: a Python **FastAPI** backend and a **Next.js**
(App Router + TypeScript + Tailwind) dashboard sharing one cohesive
green/white + forest + hill-town design system.

> This repository is being built feature by feature. **FEAT-001** (this commit)
> establishes the green baseline: scaffolding, the themed design system, the
> external-service adapter interfaces with working local/fallback
> implementations, and a single demo command. Subsystems are themed placeholders
> that later features fill in.

## The single demo command (Req 34.1)

```bash
make setup   # one-time: backend uv sync + frontend npm install
make demo    # starts the API and the website, prints the dashboard URL
```

`make demo` launches the FastAPI backend and the Next.js website concurrently
and prints the dashboard URL (http://localhost:3000). Later features extend the
demo script to seed the sample dataset and run the scripted scenario (Req 34.2).

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
| F4   | (Market Radar baseline)         | Minimal |
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
data/        checked-in dataset artifacts (added by later features)
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
