"""24-hour rolling stats update job for heartbeat.

Tracks 24h highs, lows, and range at 15-60s intervals.
"""
from __future__ import annotations

from typing import Any

from core.infra.jobs import Job
from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.services.intraday_supervisor.feed_24h import update_24h_for_country


class TwentyFourHourJob(Job):
    name = "twentyfour_hour"

    def __init__(self, interval_seconds: float = 30.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        try:
            enriched, _ = get_enriched_quotes_with_composite()
        except Exception:
            return

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
                update_24h_for_country(country, country_rows)
            except Exception:
                pass
