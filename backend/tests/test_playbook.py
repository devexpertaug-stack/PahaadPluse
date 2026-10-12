"""Playbook_Generator tests (Req 12)."""

from __future__ import annotations

from app.adapters.llm import TemplateLLMClient
from app.models.review import Aspect
from app.services.market_radar.market_model import MarketModel
from app.services.market_radar.playbook import MAX_ACTION_WORDS, PlaybookGenerator

_FIT = MarketModel().fit_cluster()
_PG = PlaybookGenerator(llm=TemplateLLMClient())
_RESULT = _PG.generate(_FIT)


def test_identifies_lagging_food_aspect() -> None:
    aspects = {a.aspect for a in _RESULT.lagging}
    assert Aspect.FOOD in aspects


def test_lagging_rule_ci_gap() -> None:
    for lag in _RESULT.lagging:
        assert lag.home_upper < lag.leader_lower


def test_themes_have_counts_and_quotes() -> None:
    for lag in _RESULT.lagging:
        assert lag.themes
        for theme in lag.themes:
            assert theme.leader_positive_count >= 3
            assert 2 <= len(theme.quotes) <= 5
            for q in theme.quotes:
                assert q.source_url  # only public reviews with source URLs
            assert theme.home_positive_count >= 0
            assert theme.home_negative_count >= 0


def test_action_paragraph_template_fallback_labelled() -> None:
    for lag in _RESULT.lagging:
        assert lag.action_template_generated is True
        assert "template-generated" in lag.action_paragraph
        assert len(lag.action_paragraph.split()) <= MAX_ACTION_WORDS


def test_action_paragraph_cites_exact_counts() -> None:
    for lag in _RESULT.lagging:
        theme = lag.themes[0]
        assert str(theme.leader_positive_count) in lag.action_paragraph
        assert str(theme.home_positive_count) in lag.action_paragraph


def test_no_lagging_message_when_home_is_leader() -> None:
    pg = PlaybookGenerator(home_property_id="mus-cloudvalley", llm=TemplateLLMClient())
    result = pg.generate(MarketModel().fit_cluster())
    # The leader as home should surface few/no lagging aspects.
    if not result.lagging and not result.undetermined:
        assert result.message is not None
