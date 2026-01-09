"""
Realtime broadcaster for Thor.

PURPOSE
-------
This file is called by the realtime heartbeat (engine).
It decides WHEN to broadcast things.

FOR GLOBAL MARKETS:
- It checks market status periodically
- It ONLY broadcasts when a status actually changes
- This results in ~8 messages per day total

IMPORTANT RULES
---------------
- No per-second clock broadcasts
- No duplicate Global Market message types
- No business logic here (GlobalMarkets owns logic)
"""

from __future__ import annotations

import logging
import json
from datetime import timezone as dt_timezone
import time
from typing import Dict

from django.utils import timezone

from GlobalMarkets.models import Market
from GlobalMarkets.services import compute_market_status
from GlobalMarkets.ws_push import broadcast_global_markets_tick
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)

# Cache of last-known statuses to detect changes
_LAST_MARKET_STATUS: Dict[str, str] = {}


def _update_live_data_active_session(now_utc) -> None:
    """Write the active session routing snapshot used by LiveData stream routing.

    This is intentionally cheap and can run every heartbeat tick.
    It is NOT a websocket broadcast; it's internal routing state.
    """

    try:
        dt = now_utc.astimezone(dt_timezone.utc)
    except Exception:
        dt = timezone.now().astimezone(dt_timezone.utc)

    session_number = int(dt.strftime("%Y%m%d"))
    payload = {
        "default": str(session_number),
        "equities": str(session_number),
        "futures": str(session_number),
        "session_number": session_number,
        "updated_at": int(time.time()),
    }

    try:
        # Keep a generous TTL so restarts don't break routing.
        live_data_redis.client.set(
            live_data_redis.ACTIVE_SESSION_KEY_REDIS,
            json.dumps(payload, default=str),
            ex=60 * 60 * 72,
        )
    except Exception:
        logger.debug("Failed to write %s", live_data_redis.ACTIVE_SESSION_KEY_REDIS, exc_info=True)


def maybe_broadcast_global_market_status() -> None:
    """
    Called by the realtime heartbeat.

    DOES NOTHING unless at least one market's OPEN/CLOSED status changes.
    """

    now = timezone.now()

    # Always keep LiveData session routing up-to-date (even if no market status changes).
    _update_live_data_active_session(now)

    markets_payload = []
    status_changed = False

    for market in Market.objects.filter(is_active=True):
        computed = compute_market_status(market, now_utc=now)
        current_status = computed.status

        # Persist status transitions to the DB so admin + REST stay correct.
        # This remains transition-only: Market.mark_status is a no-op if unchanged.
        try:
            market.mark_status(current_status, when=now)
        except Exception:
            logger.debug("Failed to persist market status for %s", getattr(market, "key", market.pk), exc_info=True)

        # Detect change
        if _LAST_MARKET_STATUS.get(market.key) != current_status:
            _LAST_MARKET_STATUS[market.key] = current_status
            status_changed = True

        markets_payload.append({
            "key": market.key,
            "name": market.name,
            "status": current_status,
            "next_transition_utc": (
                computed.next_transition_utc.isoformat()
                if computed.next_transition_utc
                else None
            ),
        })

    # No change → no broadcast
    if not status_changed:
        return

    logger.info("Global market status changed — broadcasting update")

    broadcast_global_markets_tick({
        "server_time_utc": now.isoformat(),
        "markets": markets_payload,
    })


__all__ = [
    "maybe_broadcast_global_market_status",
]

