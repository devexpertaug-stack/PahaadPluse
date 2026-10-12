"""Run-path seeding + schema initialisation for PahadPulse.

The backend serves every API endpoint from process-wide in-memory services
that self-seed from in-code sample data on first access (e.g.
``get_market_radar_service()`` seeds from
:func:`app.seed.sample_reviews.build_review_records`). Those services are
``@lru_cache``/singleton backed, so the first request triggers the seed.

On a *fresh clone* that laziness is the problem: nothing has ensured the
``backend/data`` directory exists, the SQLite schema is never created, and any
seeding error would only surface on the first browser request (making the stack
look empty/broken). This module makes seeding **explicit, eager and
idempotent** so a single documented command produces a populated, working
stack:

* :func:`ensure_schema` ensures ``backend/data`` exists and creates the ORM
  schema (``Base.metadata.create_all``) without raising on an empty/absent DB.
* :func:`warm_services` instantiates every process-wide service so the seed
  runs now (not on first request) and any seed error surfaces immediately.
* :func:`seed_all` runs both and is safe to call repeatedly (idempotent).

All of this is invoked from the FastAPI lifespan (so a live server is warm on
startup) and from the ``python -m app.seed`` entrypoint (so ``scripts/demo.sh``
can seed before launching the servers).
"""

from __future__ import annotations

# Importing the ORM model modules registers any tables on ``Base.metadata`` so
# ``create_all`` below sees them. The current domain models are pydantic (the
# services keep state in memory), so no tables are registered today, but the
# imports make the schema step correct the moment an ORM model is added.
from app import models  # noqa: F401
from app.core.db import Base, engine
from app.services.auth.service import get_auth_service
from app.services.concierge.service import get_concierge
from app.services.destination_lens.service import get_destination_lens_service
from app.services.guest_compass.service import get_guest_compass
from app.services.market_radar.analytics_service import get_analytics_service
from app.services.market_radar.intervention_store import get_intervention_store
from app.services.market_radar.service import get_market_radar_service
from app.services.sentinel.service import get_sentinel_service


async def ensure_schema() -> None:
    """Create the DB schema, ensuring the SQLite directory exists first.

    ``create_async_engine`` already ran :func:`app.core.db._ensure_sqlite_dir`
    for the configured URL, so the parent directory is created lazily; calling
    ``create_all`` here guarantees the schema exists before any request. Safe to
    run against an empty or absent database and safe to re-run (idempotent).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def warm_services() -> None:
    """Instantiate every process-wide service so demo data is loaded eagerly.

    Each getter is cached/singleton-backed, so calling it here forces the seed
    now and surfaces any seeding error at startup instead of on the first
    browser request. Re-running is a no-op (the cached instances are reused),
    which keeps the whole seed step idempotent.
    """
    get_market_radar_service()
    get_analytics_service()
    get_intervention_store()
    get_destination_lens_service()
    get_sentinel_service()
    get_guest_compass()
    get_concierge()
    # Seed the demo auth accounts (owner/manager for The Forest Season Resort).
    get_auth_service()


async def seed_all() -> None:
    """Ensure the schema exists and warm every seeded service.

    This is the single idempotent entrypoint used by both the FastAPI lifespan
    and the ``python -m app.seed`` CLI.
    """
    await ensure_schema()
    warm_services()
