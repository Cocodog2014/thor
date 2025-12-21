"""WebSocket broadcast helpers for realtime heartbeat."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any


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
    except Exception as exc:
        logger.debug("WebSocket heartbeat broadcast failed: %s", exc)


def broadcast_market_clocks(channel_layer: Any, logger: logging.Logger) -> None:
    """Broadcast per-market clock ticks every heartbeat so frontends advance clocks."""
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
            tick_msg = {
                "type": "global_markets_tick",
                "data": {
                    "timestamp": time.time(),
                    "markets": market_ticks,
                },
            }
            broadcast_to_websocket_sync(channel_layer, tick_msg)
    except Exception as exc:
        logger.debug("Global markets tick broadcast failed: %s", exc)


def broadcast_account_and_status(channel_layer: Any, logger: logging.Logger) -> None:
    """Broadcast account balance and market status snapshots."""
    try:
        from api.websocket.broadcast import broadcast_to_websocket_sync
        from api.websocket.messages import build_account_balance_message, build_market_status_message
    except Exception as exc:
        logger.debug("WebSocket broadcast helpers unavailable: %s", exc)
        return

    # 1. Broadcast account balance (for TEST-001)
    try:
        from ActAndPos.models import Account

        account = Account.objects.filter(account_id="TEST-001").first()
        if account:
            balance_data = {
                "account_id": account.account_id,
                "cash": float(account.cash or 0),
                "portfolio_value": float(account.net_liq or 0),
                "buying_power": float(account.buying_power or 0),
                "equity": float(account.equity or 0),
                "timestamp": time.time(),
            }
            balance_msg = build_account_balance_message(balance_data)
            broadcast_to_websocket_sync(channel_layer, balance_msg)
    except Exception as exc:
        logger.debug("Account balance broadcast failed: %s", exc)

    # 2. Broadcast market status per active market
    try:
        from GlobalMarkets.models import Market

        markets = Market.objects.filter(is_active=True)
        for market in markets:
            try:
                status_data = market.get_market_status()
                if status_data:
                    status_data["current_time"] = float(time.time())
                    market_data = {
                        "market_id": market.id,
                        "country": market.country,
                        "status": market.status,
                        "market_status": status_data,
                        "current_time": status_data.get("current_time"),
                    }
                    market_msg = build_market_status_message(market_data)
                    broadcast_to_websocket_sync(channel_layer, market_msg)
            except Exception as exc:
                logger.debug("Market status broadcast failed for %s: %s", market.country, exc)
    except Exception as exc:
        logger.debug("Market status broadcast failed: %s", exc)


__all__ = [
    "broadcast_heartbeat_tick",
    "broadcast_market_clocks",
    "broadcast_account_and_status",
]
