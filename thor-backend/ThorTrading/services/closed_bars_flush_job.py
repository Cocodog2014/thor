"""Closed 1m bars flush job for heartbeat.

Bulk inserts closed intraday bars from Redis into the database at 60s intervals.
"""
from __future__ import annotations

from typing import Any

from core.infra.jobs import Job
from GlobalMarkets.services.active_markets import get_active_market_ids
from ThorTrading.services.intraday_supervisor.flush_worker import flush_closed_bars


class ClosedBarsFlushJob(Job):
    name = "closed_bars_flush"

    def __init__(self, interval_seconds: float = 60.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        # Only flush during active market hours
        if not get_active_market_ids():
            return

        from GlobalMarkets.models.market import Market

        try:
            markets = Market.objects.filter(is_active=True, is_control_market=True, status="OPEN")
            countries = set(m.country for m in markets)
        except Exception:
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
            except Exception:
                pass
