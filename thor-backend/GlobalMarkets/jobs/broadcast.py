import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def _serialize_market_time(mt: dict[str, Any]) -> dict[str, Any]:
    ts = mt.get("timestamp")
    dt = mt.get("datetime")
    return {
        "timestamp": ts,
        "iso": dt.isoformat() if dt else None,
        "formatted_24h": mt.get("formatted_24h") or mt.get("time"),
        "formatted_12h": mt.get("formatted_12h"),
        "time": mt.get("time"),
        "year": mt.get("year"),
        "month": mt.get("month"),
        "date": mt.get("date"),
        "day": mt.get("day"),
        "day_number": mt.get("day_number"),
        "utc_offset": mt.get("utc_offset"),
        "dst_active": mt.get("dst_active"),
    }


def _broadcast(channel_layer, message):
    try:
        from api.websocket.broadcast import broadcast_to_websocket_sync
    except Exception:
        return
    try:
        broadcast_to_websocket_sync(channel_layer, message)
    except Exception as exc:
        logger.debug("WebSocket broadcast failed: %s", exc)


class BroadcastMarketClocksJob:
    name = "gm.broadcast_clocks"

    def run(self, ctx=None):
        channel_layer = getattr(ctx, "channel_layer", None) if ctx else None
        if not channel_layer:
            return

        try:
            from GlobalMarkets.models import Market
            from GlobalMarkets.services.market_clock import get_market_time
        except Exception as exc:
            logger.debug("Clock broadcast imports failed: %s", exc)
            return

        market_ticks = []
        for market in Market.objects.filter(is_active=True):
            mt = get_market_time(market)
            if mt:
                market_ticks.append(
                    {
                        "market_id": market.id,
                        "country": market.country,
                        "current_time": _serialize_market_time(mt),
                    }
                )

        if not market_ticks:
            return

        tick_msg = {
            "type": "global_markets_tick",
            "data": {
                "timestamp": time.time(),
                "markets": market_ticks,
            },
        }

        _broadcast(channel_layer, tick_msg)
