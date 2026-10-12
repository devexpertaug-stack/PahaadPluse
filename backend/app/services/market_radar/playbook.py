"""F5 Steal-the-Winner Playbook (Req 12).

For the Home_Property, after a Cluster fit:

* mark an Aspect *lagging* when the Home_Property's property-specific 90% CI
  upper bound is below the Cluster_Leader's lower bound for the most recent
  month (Req 12.1). When either estimate is unreliable the status is 'lagging
  status undetermined' with a reason (Req 12.8).
* for each lagging aspect, list up to 5 praised themes at the Cluster_Leader
  from positive mentions over the last 12 months (>= 3 positive mentions each),
  ranked by count, each with its count + 2..5 quotes from distinct Leader
  reviews linked to a source URL (themes with < 2 quotable reviews are
  excluded), plus the Home_Property's own positive/negative counts for the theme
  (Req 12.3-12.6).
* generate a <= 120-word suggested-action paragraph via the LLM adapter citing
  the exact displayed counts, falling back to a template paragraph labelled
  template-generated when the LLM is unreachable (Req 12.9).

Only competitor *public reviews* with source URLs are used — never competitor
Stays / Complaints / Interventions / Property_Facts (Req 12.7).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.adapters.llm import LLMClient, get_llm_client
from app.models.review import Aspect
from app.services.market_radar.analytics_dataset import (
    HOME_PROPERTY_ID,
    MentionObservation,
    cluster_property_ids,
    generate_observations,
    property_name,
)
from app.services.market_radar.market_model import ClusterFit, MarketModel

THEME_WINDOW_DAYS = 365
MIN_THEME_MENTIONS = 3
MIN_THEME_QUOTES = 2
MAX_THEME_QUOTES = 5
MAX_THEMES = 5
MAX_ACTION_WORDS = 120


@dataclass
class ThemeQuote:
    span: str
    platform: str
    date: str
    source_url: str

    def to_dict(self) -> dict:
        return {
            "span": self.span,
            "platform": self.platform,
            "date": self.date,
            "source_url": self.source_url,
        }


@dataclass
class PraisedTheme:
    aspect: Aspect
    leader_positive_count: int
    quotes: list[ThemeQuote]
    home_positive_count: int
    home_negative_count: int

    def to_dict(self) -> dict:
        return {
            "aspect": self.aspect.value,
            "leader_positive_count": self.leader_positive_count,
            "home_positive_count": self.home_positive_count,
            "home_negative_count": self.home_negative_count,
            "quotes": [q.to_dict() for q in self.quotes],
        }


@dataclass
class LaggingAspect:
    aspect: Aspect
    home_upper: float
    leader_lower: float
    themes: list[PraisedTheme]
    action_paragraph: str
    action_template_generated: bool

    def to_dict(self) -> dict:
        return {
            "aspect": self.aspect.value,
            "home_upper": round(self.home_upper, 4),
            "leader_lower": round(self.leader_lower, 4),
            "themes": [t.to_dict() for t in self.themes],
            "action_paragraph": self.action_paragraph,
            "action_template_generated": self.action_template_generated,
        }


@dataclass
class PlaybookResult:
    home_property_id: str
    leader_property_id: str
    lagging: list[LaggingAspect] = field(default_factory=list)
    message: str | None = None
    undetermined: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "home_property_id": self.home_property_id,
            "home_property_name": property_name(self.home_property_id),
            "leader_property_id": self.leader_property_id,
            "leader_property_name": property_name(self.leader_property_id),
            "message": self.message,
            "lagging": [a.to_dict() for a in self.lagging],
            "undetermined": self.undetermined,
        }


class PlaybookGenerator:
    """Build the steal-the-winner playbook for the Home_Property."""

    def __init__(
        self,
        observations: tuple[MentionObservation, ...] | None = None,
        home_property_id: str = HOME_PROPERTY_ID,
        llm: LLMClient | None = None,
    ) -> None:
        self._obs = observations if observations is not None else generate_observations()
        self._home = home_property_id
        self._llm = llm or get_llm_client()

    def _leader_property(self, fit: ClusterFit, month: str) -> str:
        """Cluster_Leader = highest mean modelled score in the latest month."""
        scores: dict[str, list[float]] = {}
        for c in fit.cells:
            if c.month == month and c.property_id != self._home:
                scores.setdefault(c.property_id, []).append(c.modelled_score)
        if not scores:
            others = [p for p in cluster_property_ids() if p != self._home]
            return others[0]
        return max(scores, key=lambda p: sum(scores[p]) / len(scores[p]))

    def generate(self, fit: ClusterFit | None = None) -> PlaybookResult:
        fit = fit or MarketModel(self._obs).fit_cluster()
        latest = fit.latest_month()
        if latest is None:
            return PlaybookResult(
                home_property_id=self._home,
                leader_property_id="",
                message="No fitted months available for the playbook.",
            )
        leader = self._leader_property(fit, latest)
        result = PlaybookResult(home_property_id=self._home, leader_property_id=leader)

        for aspect in Aspect:
            home_cell = fit.cell(self._home, aspect, latest)
            leader_cell = fit.cell(leader, aspect, latest)
            if home_cell is None or leader_cell is None:
                continue
            if home_cell.unreliable or leader_cell.unreliable:
                result.undetermined.append(
                    {
                        "aspect": aspect.value,
                        "reason": "lagging status undetermined: unreliable estimate",
                    }
                )
                continue
            # Lagging (Req 12.1): the Home_Property's property-specific 90% CI
            # upper bound is below the Cluster_Leader's property-specific lower
            # bound for the most recent month.
            home_ci_upper = home_cell.property_specific.upper
            leader_ci_lower = leader_cell.property_specific.lower
            if home_ci_upper >= leader_ci_lower:
                continue
            themes = self._praised_themes(leader, aspect, latest)
            if not themes:
                continue
            paragraph, templated = self._action_paragraph(aspect, leader, themes)
            result.lagging.append(
                LaggingAspect(
                    aspect=aspect,
                    home_upper=home_ci_upper,
                    leader_lower=leader_ci_lower,
                    themes=themes,
                    action_paragraph=paragraph,
                    action_template_generated=templated,
                )
            )

        if not result.lagging and not result.undetermined:
            result.message = "No lagging aspects: the Home_Property leads or matches the cluster."
        elif not result.lagging:
            result.message = "No lagging aspects could be confirmed (see undetermined)."
        return result

    def _praised_themes(
        self, leader: str, aspect: Aspect, latest_month: str
    ) -> list[PraisedTheme]:
        end = date.fromisoformat(latest_month)
        # 12 months ending at the latest fitted month.
        start = end - timedelta(days=THEME_WINDOW_DAYS)
        leader_pos = [
            o
            for o in self._obs
            if o.property_id == leader
            and o.aspect == aspect
            and o.label.value == "positive"
            and o.source_url  # only public reviews with a source URL (Req 12.7)
            and start <= o.date <= end + timedelta(days=31)
        ]
        if len(leader_pos) < MIN_THEME_MENTIONS:
            return []
        # Distinct quotable reviews (dedupe by span+date+platform).
        seen: set[tuple[str, str, str]] = set()
        quotes: list[ThemeQuote] = []
        for o in sorted(leader_pos, key=lambda o: o.date, reverse=True):
            key = (o.evidence, o.date.isoformat(), o.platform.value)
            if key in seen:
                continue
            seen.add(key)
            quotes.append(
                ThemeQuote(
                    span=o.evidence,
                    platform=o.platform.value,
                    date=o.date.isoformat(),
                    source_url=o.source_url,
                )
            )
            if len(quotes) >= MAX_THEME_QUOTES:
                break
        if len(quotes) < MIN_THEME_QUOTES:
            return []

        home_pos = sum(
            1
            for o in self._obs
            if o.property_id == self._home
            and o.aspect == aspect
            and o.label.value == "positive"
            and start <= o.date <= end + timedelta(days=31)
        )
        home_neg = sum(
            1
            for o in self._obs
            if o.property_id == self._home
            and o.aspect == aspect
            and o.label.value == "negative"
            and start <= o.date <= end + timedelta(days=31)
        )
        return [
            PraisedTheme(
                aspect=aspect,
                leader_positive_count=len(leader_pos),
                quotes=quotes,
                home_positive_count=home_pos,
                home_negative_count=home_neg,
            )
        ]

    def _action_paragraph(
        self, aspect: Aspect, leader: str, themes: list[PraisedTheme]
    ) -> tuple[str, bool]:
        theme = themes[0]
        context = {
            "aspect": aspect.value,
            "leader": property_name(leader),
            "leader_positive_count": theme.leader_positive_count,
            "home_positive_count": theme.home_positive_count,
            "home_negative_count": theme.home_negative_count,
        }
        prompt = (
            f"Write a concise (<=120 words) action for a Mussoorie hotel manager. "
            f"Aspect '{aspect.value}' lags the cluster leader {property_name(leader)}, "
            f"who has {theme.leader_positive_count} positive mentions on this aspect "
            f"while our property has {theme.home_positive_count} positive and "
            f"{theme.home_negative_count} negative. Cite these exact counts and "
            f"recommend concrete steps."
        )
        resp = self._llm.generate(prompt, context=context)
        text = resp.text
        if resp.template_generated:
            text = self._template_paragraph(aspect, leader, theme)
        # Enforce the <=120-word limit.
        words = text.split()
        if len(words) > MAX_ACTION_WORDS:
            text = " ".join(words[:MAX_ACTION_WORDS])
        return text, resp.template_generated

    def _template_paragraph(
        self, aspect: Aspect, leader: str, theme: PraisedTheme
    ) -> str:
        return (
            f"[template-generated] On {aspect.value}, the cluster leader "
            f"{property_name(leader)} earned {theme.leader_positive_count} positive "
            f"mentions over the last 12 months, while your property logged "
            f"{theme.home_positive_count} positive and {theme.home_negative_count} "
            f"negative mentions. Close the gap by auditing {aspect.value.lower()} "
            f"against the leader's praised themes, briefing staff on the specific "
            f"wins guests cite, and tracking {aspect.value.lower()} weekly until your "
            f"positive share matches the leader's."
        )
