#!/usr/bin/env bash
# PahadPulse demo launcher (Req 34.1).
# Starts the FastAPI backend and the Next.js website concurrently and prints
# the dashboard URL. Later features extend this to seed data and run the
# scripted scenario (Req 34.2).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"

PIDS=()
cleanup() {
  echo ""
  echo "Shutting down PahadPulse demo..."
  for pid in "${PIDS[@]:-}"; do
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

echo "=============================================="
echo " PahadPulse demo"
echo "=============================================="

# --- Seed / DB init (Req 34.1) ---
# A fresh clone has no backend/data dir or SQLite schema, and the in-memory
# services only seed on first request. Seed explicitly BEFORE the servers start
# so the single demo command always yields a populated, working dashboard. The
# seed step is idempotent (safe to re-run) so it does not break `set -e`.
echo "Seeding demo data and initialising the database..."
(
  cd "$BACKEND_DIR"
  uv run python -m app.seed
)

# --- Backend API ---
echo "Starting FastAPI backend on http://$API_HOST:$API_PORT ..."
(
  cd "$BACKEND_DIR"
  uv run uvicorn app.main:app --host "$API_HOST" --port "$API_PORT"
) &
PIDS+=("$!")

# --- Frontend website ---
echo "Starting Next.js website on http://localhost:$WEB_PORT ..."
(
  cd "$FRONTEND_DIR"
  NEXT_PUBLIC_API_BASE_URL="http://$API_HOST:$API_PORT" npm run dev -- --port "$WEB_PORT"
) &
PIDS+=("$!")

echo ""
echo "----------------------------------------------"
echo " PahadPulse is starting up."
echo " API:       http://$API_HOST:$API_PORT  (health: /health)"
echo " Dashboard: http://localhost:$WEB_PORT"
echo "----------------------------------------------"
echo " Open the dashboard URL above in your browser."
echo " Press Ctrl+C to stop."
echo ""

wait
