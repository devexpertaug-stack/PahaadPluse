"""Risk_Scorer + Checkout Shield tests, incl. the monotonicity metamorphic
property (Req 15.7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.sentinel import (
    Channel,
    Complaint,
    ComplaintState,
    Department,
    Stay,
    Urgency,
)
from app.services.sentinel.risk import compute_risk
from app.services.sentinel.service import SentinelService

_NOW = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)


def _stay(hours_to_checkout: float = 10.0, sentiment: float = 0.0) -> Stay:
    return Stay(
        id="stay-x",
        property_id="mus-pineview",
        property_name="Pine View Inn",
        guest_pseudonym="guest-x",
        room="101",
        check_in=_NOW - timedelta(days=1),
        check_out=_NOW + timedelta(hours=hours_to_checkout),
        message_sentiment=sentiment,
    )


def _complaint(
    cid: str,
    urgency: Urgency,
    state: ComplaintState = ComplaintState.OPEN,
    recurrence: bool = False,
) -> Complaint:
    return Complaint(
        id=cid,
        stay_id="stay-x",
        property_id="mus-pineview",
        room="101",
        channel=Channel.WHATSAPP,
        text="issue",
        created_at=_NOW,
        urgency=urgency,
        department=Department.MAINTENANCE,
        issue_type="geyser",
        state=state,
        is_recurrence=recurrence,
    )


def test_score_in_unit_interval() -> None:
    risk = compute_risk(_stay(), [_complaint("c1", Urgency.P2)], _NOW)
    assert 0.0 <= risk.score <= 1.0


def test_clean_stay_is_low_risk() -> None:
    risk = compute_risk(_stay(sentiment=0.5), [], _NOW)
    assert risk.score < 0.6
    assert risk.high_risk is False


def test_high_risk_and_pin_rules() -> None:
    # Two P1 complaints with imminent checkout -> high risk + pinned.
    stay = _stay(hours_to_checkout=2.0, sentiment=-0.5)
    complaints = [_complaint("c1", Urgency.P1), _complaint("c2", Urgency.P1, recurrence=True)]
    risk = compute_risk(stay, complaints, _NOW)
    assert risk.score >= 0.6
    assert risk.high_risk is True
    assert risk.pinned is True


def test_top_three_factors_returned() -> None:
    stay = _stay(hours_to_checkout=1.0, sentiment=-0.8)
    complaints = [_complaint("c1", Urgency.P1, recurrence=True)]
    risk = compute_risk(stay, complaints, _NOW)
    assert len(risk.top_factors) <= 3
    assert risk.top_factors  # at least one factor


# ---- Metamorphic property (Req 15.7) ----
_URGENCIES = [Urgency.P1, Urgency.P2, Urgency.P3, Urgency.P4]


@settings(max_examples=200)
@given(
    urgencies=st.lists(st.sampled_from(_URGENCIES), min_size=1, max_size=6),
    resolve_index=st.integers(min_value=0, max_value=5),
    hours=st.floats(min_value=0.1, max_value=48.0),
    sentiment=st.floats(min_value=-1.0, max_value=1.0),
    recurrence_flags=st.lists(st.booleans(), min_size=1, max_size=6),
)
def test_resolving_open_complaint_never_increases_score(
    urgencies: list[Urgency],
    resolve_index: int,
    hours: float,
    sentiment: float,
    recurrence_flags: list[bool],
) -> None:
    """Resolving one open complaint (others fixed) must not increase the score."""
    stay = _stay(hours_to_checkout=hours, sentiment=sentiment)
    complaints = []
    for i, u in enumerate(urgencies):
        rec = recurrence_flags[i % len(recurrence_flags)]
        complaints.append(_complaint(f"c{i}", u, recurrence=rec))

    idx = resolve_index % len(complaints)
    before = compute_risk(stay, complaints, _NOW).score

    resolved = []
    for i, c in enumerate(complaints):
        if i == idx:
            resolved.append(c.model_copy(update={"state": ComplaintState.RESOLVED}))
        else:
            resolved.append(c)
    after = compute_risk(stay, resolved, _NOW).score

    assert after <= before + 1e-9


def test_board_sorts_pins_first_then_score() -> None:
    svc = SentinelService()
    board = svc.board()
    rows = board["rows"]
    # pinned rows come before non-pinned
    pinned = [r["pinned"] for r in rows]
    assert pinned == sorted(pinned, reverse=True)
    # within equal pin status, score is non-increasing
    for a, b in zip(rows, rows[1:], strict=False):
        if a["pinned"] == b["pinned"]:
            assert a["score"] >= b["score"] - 1e-9
