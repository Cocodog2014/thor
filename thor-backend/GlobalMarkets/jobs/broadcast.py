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
        markets = list(Market.objects.filter(is_active=True))
        markets.sort(key=lambda m: m.get_sort_order())

        for market in markets:
            mt = get_market_time(market)
            status = None
            try:
                status = market.get_market_status()
            except Exception as exc:
                logger.debug("Market status fetch failed for %s: %s", market.country, exc)

            if not mt and not status:
                continue

            payload = {
                "market_id": market.id,
                "country": market.country,
            }

            if mt:
                payload["current_time"] = _serialize_market_time(mt)
            if status:
                ct = status.get("current_time") if isinstance(status, dict) else None
                if isinstance(ct, dict):
                    status = status.copy()
                    status["current_time"] = _serialize_market_time(ct)
                payload["market_status"] = status

            market_ticks.append(payload)

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
