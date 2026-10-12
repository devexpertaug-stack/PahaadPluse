"""Seed/initialise entrypoint: ``python -m app.seed``.

Runs the explicit, idempotent run-path seed (create the DB schema + warm every
process-wide service) so a fresh clone has a populated, ready backend before
the servers start. ``scripts/demo.sh`` invokes this before launching uvicorn.
"""

from __future__ import annotations

import asyncio

from app.seed.warm import seed_all


def main() -> None:
    """Create the schema and eagerly seed every service."""
    print("PahadPulse: initialising database schema and seeding demo data...")
    asyncio.run(seed_all())
    print("PahadPulse: seed complete. Backend is ready to serve populated data.")


if __name__ == "__main__":
    main()
