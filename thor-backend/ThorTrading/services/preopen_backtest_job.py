"""Pre-open backtest computation job for heartbeat.

Runs backtest statistics 30-60 seconds before market open.
"""
from __future__ import annotations

from typing import Any

from core.infra.jobs import Job
from ThorTrading.constants import FUTURES_SYMBOLS
from ThorTrading.services.backtest_stats import compute_backtest_stats_for_country_future


class PreOpenBacktestJob(Job):
    name = "preopen_backtest"

    def __init__(self, interval_seconds: float = 30.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        from GlobalMarkets.models.market import Market

        markets = Market.objects.filter(is_active=True, is_control_market=True)

        for m in markets:
            try:
                status = m.get_market_status()
                if not status:
                    continue

                # Only fire when we are in the [1, 60] second pre-open window
                if status.get("next_event") != "open":
                    continue

                seconds = int(status.get("seconds_to_next_event", 0) or 0)
                if seconds <= 0 or seconds > 60:
                    continue

                # Market is about to open within a minute – run backtests
                for future in FUTURES_SYMBOLS:
                    try:
                        compute_backtest_stats_for_country_future(country=m.country, future=future)
                    except Exception:
                        pass
            except Exception:
                pass
