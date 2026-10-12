"""Triage_Engine (Req 18).

Deterministic, offline classifier assigning a Department, Urgency, issue type
and matching SOP to a complaint. Rules:

* Housekeeping vs Maintenance split (Req 18.5): cleanliness / linen / towels /
  amenities -> Housekeeping; plumbing / electrical / heating / geyser / Wi-Fi
  hardware -> Maintenance.
* Safety / medical / fire / security terms in ANY supported language force
  Urgency P1 and route to Security (Req 18.3).
* Department confidence < 0.6 -> route to Front_Office for manual assignment
  while recording the original prediction (Req 18.7, 18.8).

The classifier works on English, romanised-Hindi and Devanagari text so a
Hinglish complaint like "room mein geyser kaam nahi kar raha" lands on
Maintenance.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.sentinel import SOP, Department, Urgency

# Issue-type cue vocabulary (English + Hinglish + Devanagari).
# Each entry: issue_type -> (department, urgency, cues)
_RULES: list[tuple[str, Department, Urgency, frozenset[str]]] = [
    (
        "safety",
        Department.SECURITY,
        Urgency.P1,
        frozenset(
            {
                "fire", "smoke", "medical", "ambulance", "injury", "injured",
                "bleeding", "unsafe", "safety", "theft", "stolen", "robbery",
                "harassment", "assault", "danger", "emergency", "security",
                # Hinglish / Devanagari
                "aag", "chori", "asurakshit", "khatra", "madad", "bachao",
                "आग", "चोरी", "असुरक्षित", "खतरा", "सुरक्षा", "मदद", "बचाओ",
                "आपातकाल", "घायल",
            }
        ),
    ),
    (
        "geyser",
        Department.MAINTENANCE,
        Urgency.P2,
        frozenset(
            {
                "geyser", "heater", "hot water", "water heater", "heating",
                "garam pani", "garam paani", "गीजर", "गरम पानी", "हीटर",
            }
        ),
    ),
    (
        "plumbing",
        Department.MAINTENANCE,
        Urgency.P2,
        frozenset(
            {
                "plumbing", "leak", "leaking", "tap", "flush", "drain", "pipe",
                "nal", "रिसाव", "नल", "पाइप",
            }
        ),
    ),
    (
        "electrical",
        Department.MAINTENANCE,
        Urgency.P2,
        frozenset(
            {
                "electrical", "power", "socket", "switch", "light", "bulb",
                "ac", "air conditioner", "fan", "bijli", "बिजली", "पंखा",
                "लाइट",
            }
        ),
    ),
    (
        "wifi",
        Department.MAINTENANCE,
        Urgency.P3,
        frozenset(
            {"wifi", "wi-fi", "internet", "router", "network", "वाईफाई", "इंटरनेट"}
        ),
    ),
    (
        "cleanliness",
        Department.HOUSEKEEPING,
        Urgency.P3,
        frozenset(
            {
                "dirty", "unclean", "cleanliness", "clean", "linen", "towel",
                "towels", "bedsheet", "sheets", "amenities", "soap", "shampoo",
                "housekeeping", "ganda", "saaf", "safai", "chaadar", "गंदा",
                "सफाई", "तौलिया", "चादर",
            }
        ),
    ),
    (
        "food",
        Department.FOOD_AND_BEVERAGE,
        Urgency.P3,
        frozenset(
            {
                "food", "breakfast", "dinner", "lunch", "meal", "restaurant",
                "khana", "khaana", "खाना", "नाश्ता", "भोजन",
            }
        ),
    ),
    (
        "spa",
        Department.SPA,
        Urgency.P4,
        frozenset({"spa", "massage", "salon", "स्पा", "मालिश"}),
    ),
]

_CONFIDENCE_FLOOR = 0.6


@dataclass
class TriageResult:
    """Output of the triage classifier."""

    department: Department
    urgency: Urgency
    issue_type: str
    confidence: float
    original_predicted_department: Department
    requires_manual_assignment: bool
    sop: SOP | None


def _normalise(text: str) -> str:
    return (text or "").lower()


def _match(text: str) -> tuple[str, Department, Urgency, float]:
    """Return (issue_type, department, urgency, confidence) for ``text``."""
    lower = _normalise(text)
    best: tuple[str, Department, Urgency, int] | None = None
    for issue_type, dept, urgency, cues in _RULES:
        hits = sum(1 for cue in cues if cue in lower)
        if hits == 0:
            continue
        # Safety always wins outright.
        if issue_type == "safety":
            return (issue_type, dept, urgency, 0.99)
        if best is None or hits > best[3]:
            best = (issue_type, dept, urgency, hits)
    if best is None:
        # No cue matched -> low confidence, generic.
        return ("general", Department.FRONT_OFFICE, Urgency.P3, 0.3)
    issue_type, dept, urgency, hits = best
    confidence = min(0.95, 0.55 + 0.2 * hits)
    return (issue_type, dept, urgency, round(confidence, 2))


class TriageEngine:
    """Classify a complaint and attach the matching SOP."""

    def __init__(self, sops: list[SOP]) -> None:
        # Index SOPs by (department, issue_type) and by issue_type.
        self._by_issue: dict[str, SOP] = {}
        self._by_dept: dict[Department, SOP] = {}
        for sop in sops:
            self._by_issue.setdefault(sop.issue_type, sop)
            self._by_dept.setdefault(Department(sop.department), sop)

    def classify(self, text: str) -> TriageResult:
        issue_type, dept, urgency, confidence = _match(text)
        original = dept
        requires_manual = False
        if issue_type != "safety" and confidence < _CONFIDENCE_FLOOR:
            # Route to Front_Office for manual assignment (keep original pred).
            dept = Department.FRONT_OFFICE
            requires_manual = True
        sop = self._find_sop(issue_type, dept)
        return TriageResult(
            department=dept,
            urgency=urgency,
            issue_type=issue_type,
            confidence=confidence,
            original_predicted_department=original,
            requires_manual_assignment=requires_manual,
            sop=sop,
        )

    def _find_sop(self, issue_type: str, dept: Department) -> SOP | None:
        if issue_type in self._by_issue:
            return self._by_issue[issue_type]
        if dept in self._by_dept:
            return self._by_dept[dept]
        return self._by_issue.get("general")
