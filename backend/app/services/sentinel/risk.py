"""Risk_Scorer for the Checkout Shield (Req 15).

Computes a Risk_Score in [0, 1] per in-house Stay from its Complaints (count,
urgency, open/resolved, recurrence), the Stay's message sentiment, the time to
checkout and Stay attributes. It also surfaces the top-3 contributing factors.

Design note — monotonicity (Req 15.7, tested as a metamorphic property):
the score is a logistic over a NON-NEGATIVE weighted sum of factors in which
every open complaint contributes a non-negative amount and resolving a
complaint only ever REMOVES its open-complaint contribution (resolved
complaints contribute zero to the open-driven terms). Therefore resolving an
open complaint, holding everything else fixed, can never increase the score.
Time-to-checkout and sentiment factors depend only on the Stay, not on which
complaints are open, so they are unchanged by a resolve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from app.models.sentinel import Complaint, ComplaintState, Stay, Urgency

# Per-urgency weight for an OPEN complaint (higher = riskier). Resolved
# complaints contribute 0 to these terms.
_URGENCY_WEIGHT: dict[Urgency, float] = {
    Urgency.P1: 1.6,
    Urgency.P2: 1.0,
    Urgency.P3: 0.6,
    Urgency.P4: 0.3,
}

_RECURRENCE_BONUS = 0.5  # extra risk per open recurrence
_SENTIMENT_WEIGHT = 1.2  # negative sentiment pushes risk up
_INTERCEPT = -1.4  # calibrates a clean stay to a low score
_LOGISTIC_SCALE = 1.0

_HIGH_RISK_THRESHOLD = 0.6
_PIN_HOURS = 4.0


@dataclass
class RiskFactor:
    """A single contributing factor to the risk score."""

    label: str
    contribution: float


@dataclass
class RiskScore:
    """A computed risk score for a Stay with explanatory factors."""

    stay_id: str
    score: float
    hours_to_checkout: float
    top_factors: list[RiskFactor]
    high_risk: bool
    pinned: bool


def _urgency(value) -> Urgency:  # noqa: ANN001 - may be str or enum
    return value if isinstance(value, Urgency) else Urgency(value)


def _is_open(complaint: Complaint) -> bool:
    state = complaint.state
    state_val = state.value if isinstance(state, ComplaintState) else state
    return state_val != ComplaintState.RESOLVED.value


def compute_risk(
    stay: Stay,
    complaints: list[Complaint],
    now: datetime,
) -> RiskScore:
    """Compute the Risk_Score for ``stay`` given its ``complaints``."""
    factors: list[RiskFactor] = []
    linear = _INTERCEPT

    # ---- Open-complaint terms (non-negative; removed when resolved) ----
    open_complaints = [c for c in complaints if _is_open(c)]
    open_urgency_sum = 0.0
    recurrence_sum = 0.0
    for c in open_complaints:
        if c.urgency is not None:
            open_urgency_sum += _URGENCY_WEIGHT.get(_urgency(c.urgency), 0.4)
        if c.is_recurrence:
            recurrence_sum += _RECURRENCE_BONUS
    if open_urgency_sum:
        linear += open_urgency_sum
        factors.append(
            RiskFactor(
                label=f"{len(open_complaints)} open complaint(s) by urgency",
                contribution=open_urgency_sum,
            )
        )
    if recurrence_sum:
        linear += recurrence_sum
        factors.append(
            RiskFactor(label="recurring issue(s)", contribution=recurrence_sum)
        )

    # ---- Message sentiment (Stay-level; independent of open/resolved) ----
    # message_sentiment in [-1, 1]; negative -> positive risk contribution.
    sentiment_term = max(0.0, -stay.message_sentiment) * _SENTIMENT_WEIGHT
    if sentiment_term > 0:
        linear += sentiment_term
        factors.append(
            RiskFactor(label="negative guest sentiment", contribution=sentiment_term)
        )

    # ---- Time-to-checkout (Stay-level; shorter window -> less recovery time) ----
    hours_to_checkout = (stay.check_out - now).total_seconds() / 3600.0
    # Only amplifies risk when there is already open risk (so a happy guest with
    # imminent checkout is not flagged). Still independent of resolve, because
    # it multiplies the *already-added* open terms is avoided; instead we add a
    # bounded urgency-time term that is non-negative and resolve-independent.
    if hours_to_checkout <= _PIN_HOURS and (open_urgency_sum or recurrence_sum):
        time_term = 0.5
        linear += time_term
        factors.append(
            RiskFactor(label="little time before checkout", contribution=time_term)
        )

    score = 1.0 / (1.0 + math.exp(-_LOGISTIC_SCALE * linear))
    score = round(min(1.0, max(0.0, score)), 4)

    factors.sort(key=lambda f: f.contribution, reverse=True)
    high_risk = score >= _HIGH_RISK_THRESHOLD
    pinned = high_risk and hours_to_checkout <= _PIN_HOURS
    return RiskScore(
        stay_id=stay.id,
        score=score,
        hours_to_checkout=round(hours_to_checkout, 2),
        top_factors=factors[:3],
        high_risk=high_risk,
        pinned=pinned,
    )
