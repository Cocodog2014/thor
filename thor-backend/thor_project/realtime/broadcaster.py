"""WebSocket broadcast helpers for realtime heartbeat."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _get_redis_client():
    """
    Returns live_data_redis.client if available, else None.
    We keep this optional so imports never break app startup.
    """
    try:
        from LiveData.shared.redis_client import live_data_redis  # type: ignore
        return live_data_redis.client
    except Exception:
        return None


def _redis_set_json(key: str, payload: Dict[str, Any], ttl_seconds: int = 10) -> None:
    client = _get_redis_client()
    if not client:
        return
    try:
        client.setex(key, int(ttl_seconds), json.dumps(payload, default=str))
    except Exception:
        # Never allow Redis issues to break heartbeat
        pass


def broadcast_heartbeat_tick(channel_layer: Any, logger: logging.Logger) -> None:
    """Broadcast basic heartbeat tick with UTC timestamp."""
    try:
        from api.websocket.broadcast import broadcast_to_websocket_sync

        heartbeat_msg = {
            "type": "heartbeat",
            "data": {
                "timestamp": time.time(),
                "utc_iso": datetime.now(timezone.utc).isoformat(),
                "stale_after_seconds": 5,
            },
        }
        broadcast_to_websocket_sync(channel_layer, heartbeat_msg)
        _redis_set_json("thor:realtime:heartbeat", heartbeat_msg["data"], ttl_seconds=10)
    except Exception as exc:
        logger.debug("WebSocket heartbeat broadcast failed: %s", exc)


def broadcast_market_clocks(channel_layer: Any, logger: logging.Logger) -> None:
    """
    Broadcast per-market clock ticks every heartbeat so frontends advance clocks.

    Writes:
      - thor:global_markets:clocks (TTL)
    Broadcasts:
      - type=global_markets_tick
    """
    try:
        from api.websocket.broadcast import broadcast_to_websocket_sync
        from GlobalMarkets.models import Market
        from GlobalMarkets.services.market_clock import get_market_time

        def serialize_market_time(mt: dict[str, Any]) -> dict[str, Any]:
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

        markets = Market.objects.filter(is_active=True)
        market_ticks = []
        for market in markets:
            mt = get_market_time(market)
            if mt:
                market_ticks.append(
                    {
                        "market_id": market.id,
                        "country": market.country,
                        "current_time": serialize_market_time(mt),
                    }
                )

        if market_ticks:
            payload = {
                "timestamp": time.time(),
                "markets": market_ticks,
            }
            tick_msg = {"type": "global_markets_tick", "data": payload}

            # Broadcast
            broadcast_to_websocket_sync(channel_layer, tick_msg)

            # Cache
            _redis_set_json("thor:global_markets:clocks", payload, ttl_seconds=15)

    except Exception as exc:
        logger.debug("Global markets tick broadcast failed: %s", exc)


def broadcast_global_market_status(channel_layer: Any, logger: logging.Logger) -> None:
    """
    Broadcast consolidated market status for all active markets.

    Writes:
      - thor:global_markets:status (TTL)
    Broadcasts:
      - type=market_status with data={"timestamp":..., "markets":[...]}
        (consumer already supports "market_status")
    """
    try:
        from api.websocket.broadcast import broadcast_to_websocket_sync
        from GlobalMarkets.models import Market

        markets = Market.objects.filter(is_active=True)

        results = []
        for market in markets:
            try:
                st = market.get_market_status()
                if not isinstance(st, dict):
                    st = None
                results.append(
                    {
                        "market_id": market.id,
                        "country": market.country,
                        "status": market.status,
                        "market_status": st,
                        "server_time": time.time(),
                    }
                )
            except Exception as exc:
                logger.debug("Market status build failed for %s: %s", getattr(market, "country", "?"), exc)

        payload = {"timestamp": time.time(), "markets": results}

        msg = {"type": "market_status", "data": payload}
        broadcast_to_websocket_sync(channel_layer, msg)
        _redis_set_json("thor:global_markets:status", payload, ttl_seconds=15)

    except Exception as exc:
        logger.debug("Global market status broadcast failed: %s", exc)


__all__ = [
    "broadcast_heartbeat_tick",
    "broadcast_market_clocks",
    "broadcast_global_market_status",
]
