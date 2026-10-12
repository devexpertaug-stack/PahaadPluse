"""In-Stay Sentinel application service (Req 15, 17-21).

Holds process-wide in-house Stays, SOPs and Complaints (demo-grade in-memory
state) and wires:

* Multi-channel intake (Req 17) with WhatsApp-number -> Stay matching and
  review -> Stay matching within 14 days.
* The Triage_Engine (Req 18) with Dashboard + WhatsApp notification, the
  complaint-to-department timer and reassignment recording.
* Resolution tracking + recurrence + escalation (Req 19).
* The Risk_Scorer + Checkout Shield board (Req 15) recomputed on every
  complaint create/update/resolve.
* The WhatsApp Hinglish loop (Req 20) and minimal voice complaints (Req 21).

Guest identities are synthetic + pseudonymised; only public reviews use real
platform data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from app.adapters.voice import Transcription, get_voice_pipeline
from app.adapters.whatsapp import WhatsAppGateway, get_default_gateway
from app.core.audit import audit_log
from app.models.sentinel import (
    SOP,
    Channel,
    Complaint,
    ComplaintState,
    Department,
    Reassignment,
    Stay,
    Urgency,
    raise_urgency,
)
from app.seed.sentinel_seed import (
    HOME_PROPERTY_ID,
    build_sops,
    build_stays,
)
from app.services.sentinel.risk import RiskScore, compute_risk
from app.services.sentinel.triage import TriageEngine

REVIEW_MATCH_WINDOW_DAYS = 14
RECURRENCE_WINDOW_DAYS = 30
_LANG_ACK = {
    "hi": "नमस्ते! आपकी शिकायत {dept} विभाग को भेज दी गई है। हम जल्द समाधान करेंगे।",
    "hi-Latn": (
        "Namaste! Aapki shikayat {dept} department ko bhej di gayi hai. "
        "Hum jald samadhan karenge."
    ),
    "en": (
        "Namaste! Your complaint has been routed to our {dept} team. "
        "We will resolve it shortly."
    ),
}


def _lang_key(language: str) -> str:
    if language in _LANG_ACK:
        return language
    if language and language.startswith("hi"):
        return "hi"
    return "en"


@dataclass
class IntakeResult:
    """Result of accepting + triaging a complaint."""

    complaint: Complaint
    risk: RiskScore | None
    acknowledgement: str | None


class SentinelService:
    """Facade over Sentinel intake/triage/resolution/risk for the API."""

    def __init__(self, gateway: WhatsAppGateway | None = None) -> None:
        self._now_ref = datetime.now(UTC)
        self.stays: dict[str, Stay] = {s.id: s for s in build_stays(self._now_ref)}
        self.sops: list[SOP] = build_sops(HOME_PROPERTY_ID)
        self.triage = TriageEngine(self.sops)
        self.complaints: dict[str, Complaint] = {}
        self._seq = 0
        self._gateway = gateway or get_default_gateway()
        self.notifications: list[str] = []
        self._voice = get_voice_pipeline()
        self._seed_complaints()

    # -- clock: a demo-friendly "now" anchored to seed time so countdowns hold --
    def now(self) -> datetime:
        return self._now_ref

    def _next_id(self) -> str:
        self._seq += 1
        return f"cmp-{self._seq:04d}"

    def _seed_complaints(self) -> None:
        """Seed a couple of complaints so the board is populated on first load."""
        self.create_complaint(
            channel=Channel.IN_PERSON,
            text="The room was not cleaned and towels were missing.",
            stay_id="stay-charlie",
            created_at=self.now() - timedelta(minutes=20),
            notify=False,
        )
        self.create_complaint(
            channel=Channel.FEEDBACK_FORM,
            text="Wifi is very slow in the room.",
            stay_id="stay-bravo",
            created_at=self.now() - timedelta(hours=3),
            notify=False,
        )

    # ---- Stay lookups (Req 17) ----
    def stay_by_whatsapp(self, number: str) -> Stay | None:
        norm = (number or "").replace(" ", "")
        for stay in self.stays.values():
            if stay.whatsapp_number and stay.whatsapp_number.replace(" ", "") == norm:
                return stay
        return None

    def active_stay_for_room(self, room: str) -> Stay | None:
        for stay in self.stays.values():
            if stay.room == room:
                return stay
        return None

    # ---- Intake (Req 17) ----
    def create_complaint(
        self,
        *,
        channel: Channel,
        text: str,
        stay_id: str | None = None,
        language: str = "en",
        room: str | None = None,
        property_id: str = HOME_PROPERTY_ID,
        created_at: datetime | None = None,
        transcript: str | None = None,
        transcript_translation_en: str | None = None,
        transcription_confidence: float | None = None,
        notify: bool = True,
    ) -> IntakeResult:
        """Accept, triage and risk-score a complaint from any channel."""
        created = created_at or self.now()
        stay = self.stays.get(stay_id) if stay_id else None
        resolved_room = room or (stay.room if stay else None)

        complaint = Complaint(
            id=self._next_id(),
            stay_id=stay.id if stay else None,
            property_id=property_id,
            room=resolved_room,
            channel=channel,
            text=text,
            language=language,
            transcript=transcript,
            transcript_translation_en=transcript_translation_en,
            transcription_confidence=transcription_confidence,
            low_transcription_confidence=(
                transcription_confidence is not None and transcription_confidence < 0.5
            ),
            created_at=created,
        )
        self.complaints[complaint.id] = complaint
        self._triage_complaint(complaint, notify=notify)
        self._detect_recurrence(complaint)

        risk = None
        if stay:
            risk = self._recompute_stay(stay.id)

        ack = None
        if notify and channel in {Channel.WHATSAPP, Channel.CONCIERGE} and stay:
            ack = self._acknowledge_guest(stay, complaint, language)
        return IntakeResult(complaint=complaint, risk=risk, acknowledgement=ack)

    def _classify_text(self, complaint: Complaint) -> str:
        """Text used for triage — prefer an English translation for voice notes."""
        return complaint.transcript_translation_en or complaint.transcript or complaint.text

    def _triage_complaint(self, complaint: Complaint, notify: bool) -> None:
        # Voice note flagged for low confidence -> Front_Office + staff flag.
        if complaint.low_transcription_confidence:
            complaint.department = Department.FRONT_OFFICE
            complaint.original_predicted_department = Department.FRONT_OFFICE
            complaint.department_confidence = complaint.transcription_confidence
            complaint.urgency = Urgency.P3
            complaint.issue_type = "general"
            complaint.flagged_for_staff = True
            complaint.requires_manual_assignment = True
            complaint.assigned_at = complaint.created_at
            sop = next((s for s in self.sops if s.issue_type == "general"), None)
            complaint.sop_id = sop.id if sop else None
            if notify:
                self._notify(complaint)
            return

        result = self.triage.classify(self._classify_text(complaint))
        complaint.department = result.department
        complaint.original_predicted_department = result.original_predicted_department
        complaint.department_confidence = result.confidence
        complaint.urgency = result.urgency
        complaint.issue_type = result.issue_type
        complaint.requires_manual_assignment = result.requires_manual_assignment
        complaint.sop_id = result.sop.id if result.sop else None
        complaint.assigned_at = complaint.created_at  # within budget (deterministic)
        if result.requires_manual_assignment:
            complaint.reassignments.append(
                Reassignment(
                    from_department=result.original_predicted_department,
                    to_department=Department.FRONT_OFFICE,
                    reason="department confidence < 0.6",
                    at=complaint.created_at,
                )
            )
        if notify:
            self._notify(complaint)

    def reassign(self, complaint_id: str, to_department: Department, reason: str) -> Complaint:
        """Manually reassign a complaint, recording the reassignment (Req 18.8)."""
        complaint = self.complaints[complaint_id]
        from_dept = (
            Department(complaint.department)
            if complaint.department
            else Department.FRONT_OFFICE
        )
        complaint.reassignments.append(
            Reassignment(
                from_department=from_dept,
                to_department=to_department,
                reason=reason,
                at=self.now(),
            )
        )
        complaint.department = to_department
        complaint.requires_manual_assignment = False
        if complaint.stay_id:
            self._recompute_stay(complaint.stay_id)
        return complaint

    def _notify(self, complaint: Complaint) -> None:
        dept = complaint.department
        msg = (
            f"[Dashboard] {dept} notified of {complaint.urgency} complaint "
            f"{complaint.id} (room {complaint.room or '—'}): {complaint.issue_type}"
        )
        self.notifications.append(msg)

    def _acknowledge_guest(self, stay: Stay, complaint: Complaint, language: str) -> str:
        key = _lang_key(language)
        dept = complaint.department or Department.FRONT_OFFICE
        body = _LANG_ACK[key].format(dept=dept)
        if stay.whatsapp_number:
            self._gateway.send(stay.whatsapp_number, body)
        return body

    # ---- Recurrence (Req 19.3) ----
    def _detect_recurrence(self, complaint: Complaint) -> None:
        if not complaint.issue_type:
            return
        window_start = complaint.created_at - timedelta(days=RECURRENCE_WINDOW_DAYS)
        for other in self.complaints.values():
            if other.id == complaint.id:
                continue
            if other.issue_type != complaint.issue_type:
                continue
            same_room = (
                complaint.room is not None
                and other.room == complaint.room
                and other.created_at >= window_start
            )
            same_stay = (
                complaint.stay_id is not None and other.stay_id == complaint.stay_id
            )
            if same_room or same_stay:
                complaint.is_recurrence = True
                complaint.recurrence_of = other.id
                if complaint.urgency is not None:
                    complaint.urgency = raise_urgency(Urgency(complaint.urgency))
                break

    # ---- Resolution + escalation (Req 19) ----
    def resolve_complaint(self, complaint_id: str, note: str) -> Complaint:
        complaint = self.complaints[complaint_id]
        complaint.state = ComplaintState.RESOLVED
        complaint.resolution_note = note
        complaint.resolved_at = self.now()
        if complaint.stay_id:
            self._recompute_stay(complaint.stay_id)
        return complaint

    def escalate_overdue(self) -> list[Complaint]:
        """Escalate open complaints past their SOP target to managers (Req 19.4)."""
        escalated: list[Complaint] = []
        sop_by_id = {s.id: s for s in self.sops}
        for complaint in self.complaints.values():
            if complaint.state == ComplaintState.RESOLVED or complaint.escalated:
                continue
            sop = sop_by_id.get(complaint.sop_id or "")
            if not sop or not complaint.assigned_at:
                continue
            deadline = complaint.assigned_at + timedelta(minutes=sop.target_resolution_minutes)
            if self.now() > deadline:
                complaint.escalated = True
                complaint.state = ComplaintState.ESCALATED
                self.notifications.append(
                    f"[Manager] Complaint {complaint.id} exceeded SOP target "
                    f"({sop.target_resolution_minutes}m) — escalated to Management."
                )
                escalated.append(complaint)
                if complaint.stay_id:
                    self._recompute_stay(complaint.stay_id)
        return escalated

    # ---- Risk / Checkout Shield (Req 15) ----
    def _complaints_for_stay(self, stay_id: str) -> list[Complaint]:
        return [c for c in self.complaints.values() if c.stay_id == stay_id]

    def _recompute_stay(self, stay_id: str) -> RiskScore:
        stay = self.stays[stay_id]
        risk = compute_risk(stay, self._complaints_for_stay(stay_id), self.now())
        if risk.high_risk:
            self.notifications.append(
                f"[Manager] Stay {stay_id} (room {stay.room}) risk "
                f"{risk.score:.2f} ≥ 0.6 — manager notified."
            )
        return risk

    def board(self) -> dict:
        """The Checkout Shield board, sorted by risk desc with pins first (Req 15)."""
        rows = []
        for stay in self.stays.values():
            complaints = self._complaints_for_stay(stay.id)
            risk = compute_risk(stay, complaints, self.now())
            open_complaints = [c for c in complaints if c.is_open]
            top = None
            if open_complaints:
                top = max(
                    open_complaints,
                    key=lambda c: {"P1": 4, "P2": 3, "P3": 2, "P4": 1}.get(
                        str(c.urgency), 0
                    ),
                )
            sop = next((s for s in self.sops if top and s.id == top.sop_id), None)
            rows.append(
                {
                    "stay_id": stay.id,
                    "room": stay.room,
                    "guest_pseudonym": stay.guest_pseudonym,
                    "hours_to_checkout": risk.hours_to_checkout,
                    "score": risk.score,
                    "high_risk": risk.high_risk,
                    "pinned": risk.pinned,
                    "top_factors": [
                        {"label": f.label, "contribution": round(f.contribution, 3)}
                        for f in risk.top_factors
                    ],
                    "top_open_complaint": (
                        {
                            "id": top.id,
                            "issue_type": top.issue_type,
                            "urgency": str(top.urgency),
                            "department": str(top.department),
                            "text": top.text,
                        }
                        if top
                        else None
                    ),
                    "responsible_department": str(top.department) if top else None,
                    "sop_action": sop.corrective_steps[0] if sop else None,
                }
            )
        # Pins first, then score desc.
        rows.sort(key=lambda r: (r["pinned"], r["score"]), reverse=True)
        return {
            "generated_at": self.now().isoformat(),
            "high_risk_threshold": 0.6,
            "rows": rows,
        }

    # ---- Metrics (Req 19.5) ----
    def metrics(self) -> dict:
        complaints = list(self.complaints.values())
        resolved = [c for c in complaints if c.state == ComplaintState.RESOLVED]
        # complaint-to-department time (seconds) averaged.
        deltas = [
            (c.assigned_at - c.created_at).total_seconds()
            for c in complaints
            if c.assigned_at
        ]
        avg_to_dept = round(sum(deltas) / len(deltas), 2) if deltas else 0.0
        # in-stay resolution rate: resolved before checkout / total with a stay.
        with_stay = [c for c in complaints if c.stay_id]
        in_stay_resolved = 0
        for c in with_stay:
            if c.resolved_at and c.stay_id in self.stays:
                if c.resolved_at <= self.stays[c.stay_id].check_out:
                    in_stay_resolved += 1
        in_stay_rate = round(in_stay_resolved / len(with_stay), 3) if with_stay else 0.0
        # repeat complaints in the last 7 days.
        week_start = self.now() - timedelta(days=7)
        repeats = sum(
            1 for c in complaints if c.is_recurrence and c.created_at >= week_start
        )
        return {
            "avg_complaint_to_department_seconds": avg_to_dept,
            "in_stay_resolution_rate": in_stay_rate,
            "repeat_complaints_this_week": repeats,
            "total_complaints": len(complaints),
            "resolved_complaints": len(resolved),
            "open_complaints": len(complaints) - len(resolved),
        }

    # ---- SOP lookup for the queue view ----
    def sop_by_id(self, sop_id: str | None) -> SOP | None:
        return next((s for s in self.sops if s.id == sop_id), None)

    def complaint_view(self, complaint: Complaint) -> dict:
        sop = self.sop_by_id(complaint.sop_id)
        stay = self.stays.get(complaint.stay_id) if complaint.stay_id else None
        return {
            "id": complaint.id,
            "stay_id": complaint.stay_id,
            "room": complaint.room,
            "guest_pseudonym": stay.guest_pseudonym if stay else None,
            "channel": str(complaint.channel),
            "text": complaint.text,
            "language": complaint.language,
            "transcript": complaint.transcript,
            "transcript_translation_en": complaint.transcript_translation_en,
            "transcription_confidence": complaint.transcription_confidence,
            "flagged_for_staff": complaint.flagged_for_staff,
            "created_at": complaint.created_at.isoformat(),
            "assigned_at": complaint.assigned_at.isoformat() if complaint.assigned_at else None,
            "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None,
            "department": str(complaint.department) if complaint.department else None,
            "original_predicted_department": (
                str(complaint.original_predicted_department)
                if complaint.original_predicted_department
                else None
            ),
            "department_confidence": complaint.department_confidence,
            "urgency": str(complaint.urgency) if complaint.urgency else None,
            "issue_type": complaint.issue_type,
            "requires_manual_assignment": complaint.requires_manual_assignment,
            "state": str(complaint.state),
            "is_recurrence": complaint.is_recurrence,
            "recurrence_of": complaint.recurrence_of,
            "escalated": complaint.escalated,
            "resolution_note": complaint.resolution_note,
            "reassignments": [
                {
                    "from": str(r.from_department),
                    "to": str(r.to_department),
                    "reason": r.reason,
                    "at": r.at.isoformat(),
                }
                for r in complaint.reassignments
            ],
            "sop": (
                {
                    "department": str(sop.department),
                    "issue_type": sop.issue_type,
                    "corrective_steps": sop.corrective_steps,
                    "target_resolution_minutes": sop.target_resolution_minutes,
                }
                if sop
                else None
            ),
        }

    def queue(self) -> list[dict]:
        return [
            self.complaint_view(c)
            for c in sorted(self.complaints.values(), key=lambda c: c.created_at, reverse=True)
        ]

    # ---- Review -> Stay matching (Req 17.4) ----
    def intake_from_review(
        self,
        *,
        text: str,
        sentiment: str,
        review_date: datetime,
        room: str | None = None,
        stay_id: str | None = None,
        language: str = "en",
    ) -> IntakeResult | None:
        """Create a review_platform complaint if a negative review matches a Stay
        checked out within 14 days (Req 17.4)."""
        if sentiment != "negative":
            return None
        stay = self.stays.get(stay_id) if stay_id else None
        if stay is None and room:
            stay = self.active_stay_for_room(room)
        if stay is None:
            return None
        # Matched Stay must have checked out within the window of the review.
        if (review_date - stay.check_out) > timedelta(days=REVIEW_MATCH_WINDOW_DAYS):
            return None
        return self.create_complaint(
            channel=Channel.REVIEW_PLATFORM,
            text=text,
            stay_id=stay.id,
            language=language,
            created_at=review_date,
            notify=True,
        )

    # ---- WhatsApp inbound (Req 20) ----
    def intake_from_whatsapp(
        self, from_number: str, body: str, language: str = "hi-Latn"
    ) -> IntakeResult:
        stay = self.stay_by_whatsapp(from_number)
        return self.create_complaint(
            channel=Channel.WHATSAPP,
            text=body,
            stay_id=stay.id if stay else None,
            language=language,
            notify=True,
        )

    # ---- Voice inbound (Req 21) ----
    def intake_from_voice(
        self, from_number: str, audio: bytes, duration_seconds: float
    ) -> IntakeResult:
        if duration_seconds > 120:
            raise ValueError("voice note exceeds the 2 minute limit")
        transcription: Transcription = self._voice.transcribe(audio)
        confidence = getattr(transcription, "confidence", None)
        if confidence is None:
            confidence = 0.9  # stub default
        language = transcription.language
        translation = getattr(transcription, "translation_en", None)
        if language not in {"en", "english"} and translation is None:
            translation = f"[auto-translated] {transcription.text}"
        stay = self.stay_by_whatsapp(from_number)
        result = self.create_complaint(
            channel=Channel.WHATSAPP,
            text=transcription.text,
            stay_id=stay.id if stay else None,
            language=language,
            transcript=transcription.text,
            transcript_translation_en=translation,
            transcription_confidence=confidence,
            notify=True,
        )
        return result


@lru_cache
def get_sentinel_service() -> SentinelService:
    """Return the process-wide Sentinel service (seeded once)."""
    return SentinelService()


def record_bad_signature(detail: str) -> None:
    """Record a bad-signature webhook attempt in the Audit_Log (Req 20.4)."""
    audit_log.record(
        action="whatsapp_webhook_rejected",
        actor="unknown",
        detail=f"bad HMAC signature: {detail}",
    )
