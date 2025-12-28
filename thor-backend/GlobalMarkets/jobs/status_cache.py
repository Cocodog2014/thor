"""Cache and broadcast global market status for frontend consumption.

Writes the Redis payload expected by /markets/live_status_cached and also
broadcasts the same payload on the WebSocket bus.
"""
from __future__ import annotations

import logging

from thor_project.realtime.broadcaster import broadcast_global_market_status

logger = logging.getLogger(__name__)


class CacheMarketStatusJob:
    name = "gm.cache_market_status"

    def run(self, ctx=None):
        broadcast_global_market_status(getattr(ctx, "channel_layer", None), logger)


__all__ = ["CacheMarketStatusJob"]