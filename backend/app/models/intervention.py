"""Intervention + Reply + Property_Fact domain models (Req 24, 26, 29).

These back the Minimal differentiating features:

* :class:`Intervention` — a manager-logged operational change (Proof of Impact,
  Req 24) and the fix a closed-loop review reply can cite (Req 26).
* :class:`ReplyDraft` — a drafted review reply awaiting manager approval
  (Req 26).
* :class:`PropertyFact` — a versioned fact the Bhasha Concierge grounds its
  answers in (Req 29).
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.review import Aspect


class Intervention(BaseModel):
    """A manager-logged operational intervention on an Aspect (Req 24.1)."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    property_id: str
    aspect: Aspect
    description: str
    date: date_type
    logged_at: datetime


class ReplyState(StrEnum):
    """Lifecycle of a closed-loop review reply (Req 26.4)."""

    DRAFT = "draft"
    READY_TO_POST = "ready_to_post"


class ReplyDraft(BaseModel):
    """A drafted reply to a Review_Record awaiting manager approval (Req 26)."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    review_id: str
    property_id: str
    language: str
    body: str
    template_generated: bool
    cited_fix: str | None = None
    cited_source: str | None = None  # "intervention:<id>" | "complaint:<id>"
    negative_aspects: list[Aspect] = Field(default_factory=list)
    pii_redacted: bool = False
    state: ReplyState = ReplyState.DRAFT
    approved_by: str | None = None
    approved_at: datetime | None = None


class PropertyFact(BaseModel):
    """A versioned Property_Fact used to ground Concierge answers (Req 29.2)."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    property_id: str
    topic: str
    text: str
    version: int = 1
    updated_at: datetime
