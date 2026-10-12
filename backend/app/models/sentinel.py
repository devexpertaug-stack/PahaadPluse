"""In-Stay Sentinel domain models (Req 15, 17-21).

These pydantic models describe the Stay / Complaint / SOP entities that power
multi-channel intake, triage, resolution tracking and the Checkout Shield risk
board. Guest identities are synthetic + pseudonymised; no real guest PII is
stored (per the platform privacy requirement).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Department(StrEnum):
    """Departments a complaint can be routed to (Req 18)."""

    HOUSEKEEPING = "Housekeeping"
    MAINTENANCE = "Maintenance"
    FRONT_OFFICE = "Front_Office"
    FOOD_AND_BEVERAGE = "Food_and_Beverage"
    SPA = "Spa"
    SECURITY = "Security"
    MANAGEMENT = "Management"


class Urgency(StrEnum):
    """Complaint urgency levels (Req 18). P1 is the most critical."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


# Ordered worst -> least so we can "raise by one level" (Req 19.3).
_URGENCY_ORDER: list[Urgency] = [Urgency.P4, Urgency.P3, Urgency.P2, Urgency.P1]


def raise_urgency(current: Urgency, levels: int = 1) -> Urgency:
    """Raise ``current`` urgency by ``levels`` (capped at P1)."""
    idx = _URGENCY_ORDER.index(current)
    return _URGENCY_ORDER[min(idx + levels, len(_URGENCY_ORDER) - 1)]


class Channel(StrEnum):
    """Intake channels for complaints (Req 17)."""

    IN_PERSON = "in_person"
    WHATSAPP = "whatsapp"
    FEEDBACK_FORM = "feedback_form"
    REVIEW_PLATFORM = "review_platform"
    CONCIERGE = "concierge"


class ComplaintState(StrEnum):
    """Lifecycle states of a complaint (Req 18/19)."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class PartyComposition(BaseModel):
    """Who is on the Stay (synthetic)."""

    adults: int = 1
    children: int = 0
    description: str = ""


class Stay(BaseModel):
    """An in-house guest Stay (Req 15/17). Guest identity is a pseudonym."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    property_id: str
    property_name: str
    guest_pseudonym: str
    whatsapp_number: str | None = None
    room: str
    check_in: datetime
    check_out: datetime
    purpose: str = "leisure"
    party: PartyComposition = Field(default_factory=PartyComposition)
    preferences: list[str] = Field(default_factory=list)
    message_sentiment: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Running message-sentiment signal in [-1, 1] (negative is worse).",
    )

    @property
    def is_in_house(self) -> bool:  # convenience (not persisted)
        return True


class SOP(BaseModel):
    """A standard operating procedure for an (issue_type) in a Property (Req 18.6)."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    property_id: str
    department: Department
    issue_type: str
    corrective_steps: list[str]
    target_resolution_minutes: int


class Reassignment(BaseModel):
    """A record of a department reassignment (Req 18.8)."""

    from_department: Department
    to_department: Department
    reason: str
    at: datetime


class Complaint(BaseModel):
    """A guest complaint flowing through the Sentinel (Req 17-21)."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    stay_id: str | None
    property_id: str
    room: str | None
    channel: Channel
    text: str
    language: str = "en"
    # Voice (Req 21)
    transcript: str | None = None
    transcript_translation_en: str | None = None
    transcription_confidence: float | None = None
    low_transcription_confidence: bool = False

    # Timestamps (Req 17.6/18.4/19.1)
    created_at: datetime
    assigned_at: datetime | None = None
    resolved_at: datetime | None = None

    # Triage output (Req 18)
    department: Department | None = None
    original_predicted_department: Department | None = None
    department_confidence: float | None = None
    urgency: Urgency | None = None
    issue_type: str | None = None
    sop_id: str | None = None
    requires_manual_assignment: bool = False
    flagged_for_staff: bool = False

    # Resolution + recurrence (Req 19)
    state: ComplaintState = ComplaintState.OPEN
    resolution_note: str | None = None
    is_recurrence: bool = False
    recurrence_of: str | None = None
    escalated: bool = False
    reassignments: list[Reassignment] = Field(default_factory=list)

    @property
    def is_open(self) -> bool:
        return self.state != ComplaintState.RESOLVED
