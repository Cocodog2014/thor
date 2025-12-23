"""Market session metrics update job for heartbeat.

Tracks market open, high, low, and range metrics at 5-15s intervals.
"""
from __future__ import annotations

import logging
from typing import Any

from core.infra.jobs import Job
from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.services.market_metrics import MarketHighMetric


logger = logging.getLogger(__name__)


class MarketMetricsJob(Job):
    name = "market_metrics"

    def __init__(self, interval_seconds: float = 10.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        try:
            enriched, _ = get_enriched_quotes_with_composite()
        except Exception:
            logger.exception("market_metrics: failed to load enriched quotes")
            return

        if not enriched:
            return

        missing_country = [r for r in enriched if not r.get("country")]
        if missing_country:
            logger.warning(
                "market_metrics: dropping %s quotes missing country", len(missing_country)
            )
        enriched = [r for r in enriched if r.get("country")]
        if not enriched:
            return

        countries = set()
        for row in enriched:
            country = row.get("country")
            if country:
                countries.add(country)

        for country in countries:
            try:
                country_rows = [r for r in enriched if r.get("country") == country]
                MarketHighMetric.update_from_quotes(country, country_rows)
            except Exception:
                logger.exception("market_metrics: update failed for %s", country)
