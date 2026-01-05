"""Track active (open) markets for heartbeat cadence.

Listeners attach to GlobalMarkets signals to maintain a Redis set of active
market IDs. Keep logic light and avoid domain cross-imports.
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional

from django.dispatch import receiver

from GlobalMarkets.signals import market_closed, market_opened
from GlobalMarkets.services.normalize import normalize_country_code
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)

ACTIVE_MARKETS_KEY = "heartbeat:active_markets"
def mark_open(market) -> None:
    try:
        live_data_redis.client.sadd(ACTIVE_MARKETS_KEY, market.id)
    except Exception:
        logger.exception("Failed to add market %s to active set", getattr(market, "country", market.id))


def mark_closed(market) -> None:
    try:
        live_data_redis.client.srem(ACTIVE_MARKETS_KEY, market.id)
    except Exception:
        logger.exception("Failed to remove market %s from active set", getattr(market, "country", market.id))


def get_active_market_ids() -> set[int]:
    try:
        members = live_data_redis.client.smembers(ACTIVE_MARKETS_KEY) or set()
        ids = set()
        for m in members:
            if isinstance(m, (bytes, bytearray)):
                m = m.decode("utf-8", "ignore")
            s = str(m).strip()
            if s.isdigit():
                ids.add(int(s))
        return ids
    except Exception:
        logger.exception("Failed to fetch active market ids")
        return set()


def get_active_control_countries() -> set[str]:
    ids = get_active_market_ids()
    if not ids:
        return set()

    try:
        from GlobalMarkets.models.market import Market

        qs = Market.objects.filter(id__in=ids, is_active=True, status="OPEN")
        return {m.country for m in qs if getattr(m, "country", None)}
    except Exception:
        logger.exception("Failed to fetch active control countries")
        return set()


def get_control_markets(statuses: Iterable[str] | None = None):
    """Return active markets, optionally filtered by status values."""
    try:
        from GlobalMarkets.models.market import Market

        qs = Market.objects.filter(is_active=True)
        if statuses is not None:
            qs = qs.filter(status__in=list(statuses))
        return qs
    except Exception:
        logger.exception("Failed to fetch control markets")
        return []


def _country(m) -> Optional[str]:
    raw = getattr(m, "country", None)
    return (normalize_country_code(raw) or raw) if raw else None


def _tz_sort_key(m) -> tuple:
    """Try to sort markets east->west using whatever timezone info exists on Market.

    Falls back safely if those fields don't exist.
    """
    off_min = getattr(m, "utc_offset_minutes", None)
    if isinstance(off_min, int):
        # East (positive) first, West (negative) later -> sort by descending
        return (-off_min, _country(m) or "")

    off_hr = getattr(m, "utc_offset", None)
    if isinstance(off_hr, (int, float)):
        return (-(float(off_hr) * 60.0), _country(m) or "")

    return (0, _country(m) or "")


def get_control_countries(
    *,
    require_session_capture: bool = False,
    statuses: Iterable[str] | None = None,
) -> list[str]:
    """Return normalized control country codes, ordered and de-duped."""
    qs = get_control_markets(statuses=statuses)

    if require_session_capture and hasattr(qs, "filter"):
        qs = qs.filter(enable_session_capture=True)

    markets = list(qs)
    markets.sort(key=_tz_sort_key)

    countries: list[str] = []
    for m in markets:
        c = _country(m)
        if c:
            countries.append(c)

    seen: set[str] = set()
    ordered: list[str] = []
    for c in countries:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def has_active_markets() -> bool:
    try:
        return bool(live_data_redis.client.scard(ACTIVE_MARKETS_KEY))
    except Exception:
        logger.exception("Failed to count active markets")
        return False


def sync_active_markets(markets: Iterable) -> None:
    """Rebuild the active set from iterable of markets (open markets)."""
    try:
        pipe = live_data_redis.client.pipeline()
        pipe.delete(ACTIVE_MARKETS_KEY)
        ids = [m.id for m in markets if getattr(m, "is_active", True) and getattr(m, "status", "") == "OPEN"]
        if ids:
            pipe.sadd(ACTIVE_MARKETS_KEY, *ids)
        pipe.execute()
    except Exception:
        logger.exception("Failed to sync active markets set")


@receiver(market_opened)
def _on_market_opened(sender, instance, **kwargs):
    mark_open(instance)


@receiver(market_closed)
def _on_market_closed(sender, instance, **kwargs):
    mark_closed(instance)
