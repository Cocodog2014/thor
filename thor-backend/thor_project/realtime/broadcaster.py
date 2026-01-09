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
from typing import Dict

from django.utils import timezone

from GlobalMarkets.models import Market
from GlobalMarkets.services import compute_market_status
from GlobalMarkets.ws_push import broadcast_global_markets_tick

logger = logging.getLogger(__name__)

# Cache of last-known statuses to detect changes
_LAST_MARKET_STATUS: Dict[str, str] = {}


def maybe_broadcast_global_market_status() -> None:
    """
    Called by the realtime heartbeat.

    DOES NOTHING unless at least one market's OPEN/CLOSED status changes.
    """

    now = timezone.now()
    markets_payload = []
    status_changed = False

    for market in Market.objects.filter(is_active=True):
        computed = compute_market_status(market, now_utc=now)
        current_status = computed.status

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

