"""VWAP minute capture job for heartbeat.

Captures one row per symbol per minute via heartbeat instead of a dedicated thread.
State (last_minute_per_symbol) is stored in the shared heartbeat state dict.
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.utils import timezone

from core.infra.jobs import Job
from LiveData.shared.redis_client import live_data_redis
from ThorTrading.constants import FUTURES_SYMBOLS, REDIS_SYMBOL_MAP
from ThorTrading.models.vwap import VwapMinute

logger = logging.getLogger(__name__)


def _floor_to_minute(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def _dec(val):
    if val in (None, "", " "):
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def _int(val):
    if val in (None, "", " "):
        return None
    try:
        return int(val)
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return None


class VwapMinuteCaptureJob(Job):
    """Capture VWAP minute snapshots from latest quotes."""

    name = "vwap_minute_capture"

    def __init__(self, interval_seconds: float = 60.0):
        self.interval_seconds = max(5.0, float(interval_seconds))

    def should_run(self, now: float, state: dict[str, Any]) -> bool:
        last = state.get("last_run", {}).get(self.name)
        return last is None or (now - last) >= self.interval_seconds

    def run(self, ctx: Any) -> None:
        # Initialize per-symbol minute tracking in shared state
        vwap_state = ctx.shared_state.setdefault("vwap_minute", {})
        last_minute_per_symbol = vwap_state.setdefault("last_minute", {})

        now = timezone.now()
        current_minute = _floor_to_minute(now)
        samples = 0
        rows_created = 0

        for sym in FUTURES_SYMBOLS:
            try:
                redis_key = REDIS_SYMBOL_MAP.get(sym, sym)
                quote = live_data_redis.get_latest_quote(redis_key)
                if not quote:
                    continue

                samples += 1

                # Skip duplicates for this minute
                if last_minute_per_symbol.get(sym) == current_minute:
                    continue

                defaults = {
                    "last_price": _dec(quote.get("last")),
                    "cumulative_volume": _int(quote.get("volume")),
                }
                _, created = VwapMinute.objects.update_or_create(
                    symbol=sym,
                    timestamp_minute=current_minute,
                    defaults=defaults,
                )
                last_minute_per_symbol[sym] = current_minute
                if created:
                    rows_created += 1
            except Exception:
                logger.exception("VWAP row creation failed for %s", sym)

        if samples or rows_created:
            logger.debug("VWAP capture: samples=%s rows=%s", samples, rows_created)
