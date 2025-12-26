"""VWAP minute capture service used by heartbeat jobs."""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Tuple

from django.utils import timezone

from LiveData.shared.redis_client import live_data_redis
from ThorTrading.models import TradingInstrument
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


def _tracked_symbols() -> list[tuple[str, str]]:
    """Return list of (normalized_symbol, redis_key) for active watchlist instruments."""
    try:
        qs = TradingInstrument.objects.filter(is_active=True, is_watchlist=True)
        symbols = []
        for sym in qs.values_list("symbol", flat=True):
            if not sym:
                continue
            norm = sym.lstrip("/").upper()
            symbols.append((norm, sym))
        return symbols
    except Exception:
        logger.exception("VWAP: failed to load tracked instruments")
        return []


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

    for norm_sym, redis_key in _tracked_symbols():
        try:
            quote = live_data_redis.get_latest_quote(redis_key)
            if not quote:
                continue

            samples += 1

            if last_minute_per_symbol.get(norm_sym) == current_minute:
                continue

            defaults = {
                "last_price": _dec(quote.get("last")),
                "cumulative_volume": _int(quote.get("volume")),
            }
            _, created = VwapMinute.objects.update_or_create(
                symbol=norm_sym,
                timestamp_minute=current_minute,
                defaults=defaults,
            )
            last_minute_per_symbol[norm_sym] = current_minute
            if created:
                rows_created += 1
        except Exception:
            logger.exception("VWAP row creation failed for %s", norm_sym)

    return samples, rows_created


__all__ = ["capture_vwap_minute"]
