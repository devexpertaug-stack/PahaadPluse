"""Market Radar analytics facade for the Deep-feature API (Req 7-13).

Wires the trends, market-model, changepoint, what-if, time-machine, playbook
and gap-finder services over the shared deterministic analytics panel, caching
the (relatively expensive) cluster fit + changepoint run so the API responds
well within the latency budgets.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from app.models.review import Aspect, Platform
from app.services.market_radar.analytics_dataset import (
    HOME_PROPERTY_ID,
    generate_observations,
    property_name,
)
from app.services.market_radar.changepoints import ChangepointDetector, ChangepointRun
from app.services.market_radar.gap_finder import GapFinder
from app.services.market_radar.market_model import ClusterFit, MarketModel
from app.services.market_radar.playbook import PlaybookGenerator
from app.services.market_radar.time_machine import TimeMachine
from app.services.market_radar.trends import TrendService
from app.services.market_radar.what_if import WhatIfSimulator


class AnalyticsService:
    """Process-wide facade over the Market Radar analytics."""

    def __init__(self) -> None:
        self._obs = generate_observations()
        self.trends = TrendService(self._obs)
        self.market_model = MarketModel(self._obs)
        self.what_if = WhatIfSimulator(self._obs, home_property_id=HOME_PROPERTY_ID)
        self.gap_finder = GapFinder(self._obs)
        self._fit: ClusterFit | None = None
        self._run: ChangepointRun | None = None

    def fit(self) -> ClusterFit:
        if self._fit is None:
            self._fit = self.market_model.fit_cluster()
        return self._fit

    def changepoint_run(self) -> ChangepointRun:
        if self._run is None:
            detector = ChangepointDetector(self._obs, home_property_id=HOME_PROPERTY_ID)
            self._run = detector.run(fit=self.fit())
        return self._run

    # ---- read models ----
    def trends_view(
        self,
        granularity: str,
        platforms: list[Platform] | None,
        start: date | None,
        end: date | None,
    ) -> dict:
        return self.trends.aspect_trends(
            granularity=granularity, platforms=platforms, start=start, end=end
        )

    def decomposition_view(self) -> dict:
        return self.fit().to_dict()

    def changepoints_view(self) -> dict:
        return self.changepoint_run().to_dict()

    def what_if_model(self, platform: Platform) -> dict:
        return self.what_if.platform_model(platform).to_dict()

    def what_if_project(self, platform: Platform, deltas: dict[str, float]) -> dict:
        model = self.what_if.platform_model(platform)
        parsed = {Aspect(a): v for a, v in deltas.items() if a in {x.value for x in Aspect}}
        return self.what_if.project(model, parsed)

    def time_machine_view(
        self, property_id: str, clicked: date, aspect: Aspect | None
    ) -> dict:
        tm = TimeMachine(self._obs)
        run = self.changepoint_run()
        result = tm.investigate(run.changepoints, property_id, clicked, aspect)
        return result.to_dict()

    def playbook_view(self) -> dict:
        pg = PlaybookGenerator(self._obs, home_property_id=HOME_PROPERTY_ID)
        return pg.generate(self.fit()).to_dict()

    def gap_finder_view(self) -> dict:
        return self.gap_finder.find().to_dict()

    def home_property(self) -> dict:
        return {"id": HOME_PROPERTY_ID, "name": property_name(HOME_PROPERTY_ID)}


@lru_cache
def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()
