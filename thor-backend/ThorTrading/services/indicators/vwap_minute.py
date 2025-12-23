"""VWAP minute capture service used by heartbeat jobs."""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Tuple

from django.utils import timezone

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


def capture_vwap_minute(shared_state: Dict[str, Any]) -> Tuple[int, int]:
    """Capture one VWAP row per symbol per minute.

    Returns (samples_seen, rows_created).
    """
    vwap_state = shared_state.setdefault("vwap_minute", {})
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

    return samples, rows_created


__all__ = ["capture_vwap_minute"]
