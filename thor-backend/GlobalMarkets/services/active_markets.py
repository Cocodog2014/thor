"""Track active (open) control markets for heartbeat cadence.

Listeners attach to GlobalMarkets signals to maintain a Redis set of active
market IDs. Keep logic light and avoid domain cross-imports.
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.dispatch import receiver

from GlobalMarkets.signals import market_closed, market_opened
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)

ACTIVE_MARKETS_KEY = "heartbeat:active_markets"


def _is_control_market(market) -> bool:
    return getattr(market, "is_control_market", True) and getattr(market, "is_active", True)


def mark_open(market) -> None:
    if not _is_control_market(market):
        return
    try:
        live_data_redis.client.sadd(ACTIVE_MARKETS_KEY, market.id)
    except Exception:
        logger.exception("Failed to add market %s to active set", getattr(market, "country", market.id))


def mark_closed(market) -> None:
    if not _is_control_market(market):
        return
    try:
        live_data_redis.client.srem(ACTIVE_MARKETS_KEY, market.id)
    except Exception:
        logger.exception("Failed to remove market %s from active set", getattr(market, "country", market.id))


def get_active_market_ids() -> set[int]:
    try:
        members = live_data_redis.client.smembers(ACTIVE_MARKETS_KEY) or set()
        return {int(m) for m in members if str(m).isdigit()}
    except Exception:
        logger.exception("Failed to fetch active market ids")
        return set()


def has_active_markets() -> bool:
    try:
        return bool(live_data_redis.client.scard(ACTIVE_MARKETS_KEY))
    except Exception:
        logger.exception("Failed to count active markets")
        return False


def sync_active_markets(markets: Iterable) -> None:
    """Rebuild the active set from iterable of markets (open + control)."""
    try:
        pipe = live_data_redis.client.pipeline()
        pipe.delete(ACTIVE_MARKETS_KEY)
        ids = [m.id for m in markets if _is_control_market(m) and getattr(m, "status", "") == "OPEN"]
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
