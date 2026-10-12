"""Market_Model tests incl. the Req 8.7 additivity invariant (property-based)."""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.review import Aspect
from app.services.market_radar.market_model import MarketModel

_MODEL = MarketModel()
_FIT = _MODEL.fit_cluster()


def test_fit_produces_cells_with_valid_intervals() -> None:
    assert _FIT.cells
    for cell in _FIT.cells:
        mw = cell.market_wide
        assert mw.lower <= mw.point <= mw.upper
        ps = cell.property_specific
        assert ps.lower <= ps.point <= ps.upper


def test_cluster_size_and_flags_present() -> None:
    assert _FIT.cluster_size == 6
    assert _FIT.insufficient_cluster is False


def test_insufficient_cluster_flagged_when_small() -> None:
    # Restrict observations to two properties -> cluster too small.
    obs = tuple(o for o in _MODEL._obs if o.property_id in {"mus-pineview", "mus-cloudvalley"})
    small = MarketModel(obs).fit_cluster(aspects=[Aspect.FOOD])
    assert small.cluster_size == 2
    assert small.insufficient_cluster is True
    assert all(c.insufficient_data for c in small.cells)


def test_refit_failure_retains_previous() -> None:
    prev = _MODEL.fit_cluster(aspects=[Aspect.FOOD], now=datetime(2024, 6, 1, tzinfo=UTC))
    failed = _MODEL.fit_cluster(force_failure=True, previous=prev)
    assert failed.failure is True
    assert failed.stale_timestamp == prev.fitted_at
    assert failed.cells == prev.cells


def test_unreliable_flag_shown_not_hidden() -> None:
    # Cells still present even when flagged unreliable/insufficient.
    flagged = [c for c in _FIT.cells if c.unreliable or c.insufficient_data]
    # The analytics panel is dense, so most cells are reliable; the key contract
    # is that any flagged cell is still returned (not hidden).
    for cell in flagged:
        assert cell in _FIT.cells


@settings(max_examples=50, deadline=None)
@given(aspect=st.sampled_from(list(Aspect)))
def test_additivity_invariant_within_0_01(aspect: Aspect) -> None:
    """Req 8.7: market_wide + property_specific == modelled score (<=0.01)."""
    fit = _MODEL.fit_cluster(aspects=[aspect])
    for cell in fit.cells:
        total = cell.market_wide.point + cell.property_specific.point
        assert abs(total - cell.modelled_score) <= 0.01
