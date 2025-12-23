"""Heartbeat job wrapper for flushing closed bars."""
from __future__ import annotations

import logging
from typing import Any

from core.infra.jobs import Job
from GlobalMarkets.services.active_markets import get_active_control_countries
from ThorTrading.services.intraday.flush import flush_closed_bars

log = logging.getLogger(__name__)


class ClosedBarsFlushJob(Job):
    name = "closed_bars_flush"

    def __init__(self, interval_seconds: float = 60.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        countries = get_active_control_countries()
        if not countries:
            return

        for country in countries:
            try:
                total = 0
                batch_size = 500
                while True:
                    inserted = flush_closed_bars(country, batch_size=batch_size)
                    if not inserted:
                        break
                    total += inserted
                if total:
                    log.info("Closed bar flush inserted %s rows for %s", total, country)
            except Exception:
                log.warning("Closed bar flush failed for %s", country, exc_info=True)


def register(registry):
    job = ClosedBarsFlushJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
