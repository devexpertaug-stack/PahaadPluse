"""Focused synthetic seed for the In-Stay Sentinel subsystem (FEAT-004).

Provides enough in-house Stays and per-Property SOPs to make the Checkout
Shield + triage demonstrable. Guest identities are SYNTHETIC and pseudonymised
(salted hash) — no real guest PII is stored. Only public reviews use real
platform data (per the platform privacy requirement).

Stay check-in/checkout datetimes are anchored to a reference "now" so the
checkout countdowns on the board are meaningful during a demo.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.models.sentinel import (
    SOP,
    Department,
    PartyComposition,
    Stay,
)


def pseudonymise_guest(identifier: str) -> str:
    """Stable salted-hash pseudonym for a synthetic guest (no raw name stored)."""
    settings = get_settings()
    digest = hmac.new(
        settings.pseudonym_salt.encode("utf-8"),
        f"guest\x1f{identifier.strip().lower()}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"guest-{digest[:10]}"


# Reference property (matches the home property used across the platform).
HOME_PROPERTY_ID = "mus-pineview"
HOME_PROPERTY_NAME = "Pine View Inn"


# ---------------------------------------------------------------------------
# Per-Property SOPs (Req 18.6). target_resolution_minutes drives escalation.
# ---------------------------------------------------------------------------
def build_sops(property_id: str = HOME_PROPERTY_ID) -> list[SOP]:
    return [
        SOP(
            id=f"sop-{property_id}-housekeeping-cleanliness",
            property_id=property_id,
            department=Department.HOUSEKEEPING,
            issue_type="cleanliness",
            corrective_steps=[
                "Acknowledge the guest and apologise.",
                "Dispatch housekeeping to the room within 15 minutes.",
                "Deep-clean the reported area and replace linen/towels.",
                "Confirm resolution with the guest and log the outcome.",
            ],
            target_resolution_minutes=45,
        ),
        SOP(
            id=f"sop-{property_id}-maintenance-geyser",
            property_id=property_id,
            department=Department.MAINTENANCE,
            issue_type="geyser",
            corrective_steps=[
                "Acknowledge the guest and apologise.",
                "Send maintenance to inspect the geyser/water heater.",
                "Repair or swap the unit; offer a room change if delayed.",
                "Verify hot water and confirm with the guest.",
            ],
            target_resolution_minutes=60,
        ),
        SOP(
            id=f"sop-{property_id}-maintenance-wifi",
            property_id=property_id,
            department=Department.MAINTENANCE,
            issue_type="wifi",
            corrective_steps=[
                "Acknowledge the guest.",
                "Restart the room access point and check the uplink.",
                "Provide a portable hotspot if the fault persists.",
            ],
            target_resolution_minutes=90,
        ),
        SOP(
            id=f"sop-{property_id}-fnb-food",
            property_id=property_id,
            department=Department.FOOD_AND_BEVERAGE,
            issue_type="food",
            corrective_steps=[
                "Apologise and collect the specifics of the complaint.",
                "Replace the dish or adjust the order.",
                "Offer a complimentary gesture where appropriate.",
            ],
            target_resolution_minutes=30,
        ),
        SOP(
            id=f"sop-{property_id}-security-safety",
            property_id=property_id,
            department=Department.SECURITY,
            issue_type="safety",
            corrective_steps=[
                "Treat as critical (P1): dispatch security immediately.",
                "Ensure the guest's safety and secure the area.",
                "Escalate to the duty manager and record the incident.",
            ],
            target_resolution_minutes=15,
        ),
        SOP(
            id=f"sop-{property_id}-frontoffice-general",
            property_id=property_id,
            department=Department.FRONT_OFFICE,
            issue_type="general",
            corrective_steps=[
                "Acknowledge the guest and clarify the issue.",
                "Assign to the correct department.",
                "Follow up until resolved.",
            ],
            target_resolution_minutes=60,
        ),
    ]


def build_stays(now: datetime | None = None) -> list[Stay]:
    """Build synthetic in-house Stays anchored around ``now`` (defaults to UTC now)."""
    now = now or datetime.now(UTC)
    specs = [
        # (guest_seed, room, hours_to_checkout, whatsapp, purpose, sentiment)
        ("alpha", "101", 3, "+919800000101", "honeymoon", -0.1),
        ("bravo", "204", 20, "+919800000204", "family", 0.2),
        ("charlie", "309", 2, "+919800000309", "business", -0.3),
        ("delta", "112", 36, "+919800000112", "leisure", 0.4),
        ("echo", "215", 8, "+919800000215", "leisure", 0.1),
        ("foxtrot", "320", 1, "+919800000320", "family", -0.2),
    ]
    stays: list[Stay] = []
    for i, (seed, room, hrs, wa, purpose, sentiment) in enumerate(specs):
        check_in = now - timedelta(days=1, hours=i)
        check_out = now + timedelta(hours=hrs)
        stays.append(
            Stay(
                id=f"stay-{seed}",
                property_id=HOME_PROPERTY_ID,
                property_name=HOME_PROPERTY_NAME,
                guest_pseudonym=pseudonymise_guest(seed),
                whatsapp_number=wa,
                room=room,
                check_in=check_in,
                check_out=check_out,
                purpose=purpose,
                party=PartyComposition(adults=2, children=0 if i % 2 else 1),
                preferences=["quiet room"] if i % 2 == 0 else ["high floor"],
                message_sentiment=sentiment,
            )
        )
    return stays
