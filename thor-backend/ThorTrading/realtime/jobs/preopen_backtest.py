"""Heartbeat job wrapper for pre-open backtests."""
from __future__ import annotations

import logging
from typing import Any

from core.infra.jobs import Job
from GlobalMarkets.services.active_markets import get_control_markets
from ThorTrading.constants import FUTURES_SYMBOLS
from ThorTrading.services.analytics.backtest_stats import compute_backtest_stats_for_country_future

log = logging.getLogger(__name__)


class PreOpenBacktestJob(Job):
    name = "preopen_backtest"

    def __init__(self, interval_seconds: float = 30.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        markets = get_control_markets()
        if not markets:
            return

        for m in markets:
            try:
                status = m.get_market_status()
                if not status:
                    continue

                if status.get("next_event") != "open":
                    continue

                seconds = int(status.get("seconds_to_next_event", 0) or 0)
                if seconds <= 0 or seconds > 60:
                    continue

                for future in FUTURES_SYMBOLS:
                    try:
                        compute_backtest_stats_for_country_future(country=m.country, future=future)
                    except Exception:
                        log.warning(
                            "preopen_backtest: stats failed for %s/%s", m.country, future, exc_info=True
                        )
            except Exception:
                log.warning(
                    "preopen_backtest: status check failed for market %s", getattr(m, "id", None), exc_info=True
                )


def register(registry):
    job = PreOpenBacktestJob()
    registry.register(job, interval_seconds=job.interval_seconds)
    log.debug("registered job: %s", job.name)
    return [job.name]
