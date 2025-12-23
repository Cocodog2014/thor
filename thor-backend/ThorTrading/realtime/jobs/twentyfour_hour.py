"""Heartbeat job wrapper for 24-hour rolling stats."""
from __future__ import annotations

import logging
from typing import Any

from core.infra.jobs import Job
from ThorTrading.services.quotes import get_enriched_quotes_with_composite
from ThorTrading.services.indicators.twentyfour import update_24h_for_country

log = logging.getLogger(__name__)


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
            log.exception("24h: failed to load enriched quotes")
            return

        if not enriched:
            return

        missing_country = [r for r in enriched if not r.get("country")]
        if missing_country:
            log.warning("24h: dropping %s quotes missing country", len(missing_country))
        enriched = [r for r in enriched if r.get("country")]
        if not enriched:
            return

        countries = {r.get("country") for r in enriched if r.get("country")}

        for country in countries:
            try:
                country_rows = [r for r in enriched if r.get("country") == country]
                update_24h_for_country(country, country_rows)
            except Exception:
                log.exception("24h: update failed for %s", country)


def register(registry):
    job = TwentyFourHourJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
