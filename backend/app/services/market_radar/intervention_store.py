"""Process-wide store for logged Interventions + review-reply drafts.

Demo-grade in-memory state (mirrors the Sentinel service pattern). Interventions
feed both Proof of Impact (Req 24) and closed-loop review replies (Req 26);
reply drafts persist here until a manager approves them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache

from app.models.intervention import Intervention, ReplyDraft
from app.models.review import Aspect
from app.services.market_radar.analytics_dataset import HOME_PROPERTY_ID


class InterventionStore:
    """Holds Interventions + reply drafts for the Minimal features."""

    def __init__(self) -> None:
        self.interventions: dict[str, Intervention] = {}
        self.replies: dict[str, ReplyDraft] = {}
        self._seq = 0
        self._seed()

    def _seed(self) -> None:
        """Seed one Intervention on the declining Home_Property Food aspect so
        the Proof-of-Impact view has data on first load."""
        from datetime import date

        latest = date(2024, 6, 15)
        # ~45 days of post data -> clears the 30-day threshold.
        self.log(
            property_id=HOME_PROPERTY_ID,
            aspect=Aspect.FOOD,
            description="Replaced the breakfast vendor and added a live hot counter.",
            on=date(latest.year, latest.month - 2, 1),
        )

    def _next_id(self) -> str:
        self._seq += 1
        return f"iv-{self._seq:04d}"

    def log(
        self, *, property_id: str, aspect: Aspect, description: str, on
    ) -> Intervention:
        iv = Intervention(
            id=self._next_id(),
            property_id=property_id,
            aspect=aspect,
            description=description,
            date=on,
            logged_at=datetime.now(UTC),
        )
        self.interventions[iv.id] = iv
        return iv

    def for_property(self, property_id: str) -> list[Intervention]:
        return [
            iv for iv in self.interventions.values() if iv.property_id == property_id
        ]

    def save_reply(self, draft: ReplyDraft) -> ReplyDraft:
        self.replies[draft.id] = draft
        return draft


@lru_cache
def get_intervention_store() -> InterventionStore:
    return InterventionStore()
