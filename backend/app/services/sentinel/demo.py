"""Live WhatsApp Hinglish demo helper (Req 20).

Simulates an inbound WhatsApp complaint end to end with NO live provider, using
the in-process mock gateway + the shared Sentinel state. Run it to see a
Hinglish complaint get triaged and surface on the Checkout Shield within the
time budget:

    cd backend && uv run python -m app.services.sentinel.demo

It prints the triage result, the guest acknowledgement, the updated board row
and demonstrates the HMAC bad-signature 403 + Audit_Log path.
"""

from __future__ import annotations

import json
import time

from app.core.audit import audit_log
from app.services.sentinel.service import get_sentinel_service, record_bad_signature


def run_demo(
    from_number: str = "+919800000309",
    body: str = "room mein geyser kaam nahi kar raha",
    language: str = "hi-Latn",
) -> dict:
    service = get_sentinel_service()

    t0 = time.monotonic()
    result = service.intake_from_whatsapp(from_number, body, language)
    triage_elapsed = time.monotonic() - t0

    board = service.board()
    row = next(
        (r for r in board["rows"] if r["stay_id"] == result.complaint.stay_id),
        None,
    )
    surfaced_elapsed = time.monotonic() - t0

    # Demonstrate the bad-signature path (Req 20.4).
    record_bad_signature(detail="demo: forged signature")

    return {
        "inbound": {"from": from_number, "body": body, "language": language},
        "triaged_in_seconds": round(triage_elapsed, 4),
        "surfaced_in_seconds": round(surfaced_elapsed, 4),
        "department": result.complaint.department,
        "urgency": result.complaint.urgency,
        "acknowledgement": result.acknowledgement,
        "board_row": row,
        "audit_entries": len(audit_log.entries),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, ensure_ascii=False))
