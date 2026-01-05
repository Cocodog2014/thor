"""52-week extremes tracking job for heartbeat.

Monitors rolling 52-week highs and lows at 1-5s intervals.
"""
from __future__ import annotations

from typing import Any

from core.infra.jobs import Job


class Week52ExtremesJob(Job):
    name = "week52_extremes"

    def __init__(self, interval_seconds: float = 2.0):
        self.interval_seconds = interval_seconds

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        from LiveData.shared.redis_client import live_data_redis
        from Instruments.models.market_52w import Rolling52WeekStats
        from decimal import Decimal

        SYMBOLS = ["YM", "ES", "NQ", "RTY", "CL", "SI", "HG", "GC", "VX", "DX", "ZB"]
        SYMBOL_MAP = {
            "RTY": "RT",
            "ZB": "30YRBOND",
        }

        for sym in SYMBOLS:
            try:
                redis_sym = SYMBOL_MAP.get(sym, sym)
                quote = live_data_redis.get_latest_quote(redis_sym)
                if not quote or not quote.get("last"):
                    continue

                try:
                    last_price = Decimal(str(quote["last"]))
                except Exception:
                    continue

                stats, created = Rolling52WeekStats.objects.get_or_create(
                    symbol=sym,
                    defaults={
                        "high_52w": last_price,
                        "low_52w": last_price,
                    },
                )

                if not created:
                    stats.update_from_price(last_price)
            except Exception:
                pass
