# PahadPulse — root Makefile
# Single entry points for setup, quality gates, and the demo (Req 34.1).

.DEFAULT_GOAL := help
.PHONY: help setup test lint build demo

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## Install backend (uv) and frontend (npm) dependencies
	cd backend && uv sync
	cd frontend && npm install

lint: ## Lint backend (ruff) and frontend (eslint)
	cd backend && uv run ruff check .
	cd frontend && npm run lint

test: ## Run backend (pytest) and frontend (vitest) tests
	cd backend && uv run pytest
	cd frontend && npm test

build: ## Build the frontend and verify the backend imports
	cd backend && uv run python -c "import app.main"
	cd frontend && npm run build

demo: ## Start the API and the website; print the dashboard URL
	./scripts/demo.sh
