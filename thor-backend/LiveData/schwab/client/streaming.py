"""
Schwab streaming producer (schwab-py compatible).

Consumes streaming ticks, normalizes them into Thor quote payloads,
publishes to Redis, updates 1m bars, and broadcasts WebSocket events.

IMPORTANT:
- No country logic here.
- Session routing is done via session_key.
- session_key will later be provided by GlobalMarkets.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Iterable, Optional

from channels.layers import get_channel_layer

from api.websocket.broadcast import broadcast_to_websocket_sync
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)

# Temporary fallback until GlobalMarkets injects real sessions
FALLBACK_SESSION_KEY = "GLOBAL"


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _extract_timestamp(tick: Dict[str, Any]) -> float:
    candidates = [
        tick.get("timestamp"),
        tick.get("ts"),
        tick.get("time"),
        tick.get("quoteTimeInLong"),
        tick.get("QUOTE_TIME"),
        tick.get("trade_time"),
    ]
    for c in candidates:
        try:
            if c is None:
                continue
            return float(c)
        except Exception:
            continue
    return time.time()


class SchwabStreamingProducer:
    """Normalize Schwab streaming ticks into Thor quote + bar updates."""

    def __init__(self, channel_layer: Any | None = None):
        self.channel_layer = channel_layer or get_channel_layer()

    # ------------------------------------------------------------------
    # Session routing (THIS is where session numbers will live)
    # ------------------------------------------------------------------
    def _resolve_session_key(self, payload: Dict[str, Any]) -> str:
        """
        TEMPORARY:
        Return GLOBAL until GlobalMarkets injects:
          - session_group
          - session_date
          - session_number

        Final form:
          f"{group}:{YYYYMMDD}:{session_number}"
        """
        return FALLBACK_SESSION_KEY

    # ------------------------------------------------------------------
    # Payload normalization
    # ------------------------------------------------------------------
    def _normalize_payload(self, tick: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        symbol_raw = tick.get("symbol") or tick.get("key") or tick.get("SYMBOL")
        if not symbol_raw:
            return None
        symbol = str(symbol_raw).lstrip("/").upper()

        bid = _to_float(tick.get("bid") or tick.get("bidPrice"))
        ask = _to_float(tick.get("ask") or tick.get("askPrice"))
        last = _to_float(
            tick.get("last")
            or tick.get("lastPrice")
            or tick.get("close")
            or tick.get("MARK")
        )
        volume = _to_float(
            tick.get("volume")
            or tick.get("totalVolume")
            or tick.get("lastSize")
        )
        ts = _extract_timestamp(tick)

        payload: Dict[str, Any] = {
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "last": last,
            "volume": volume,
            "timestamp": ts,
            "source": "SCHWAB",
        }

        for key in ("assetType", "assetMainType", "exchange", "description"):
            if tick.get(key) is not None:
                payload[key] = tick.get(key)

        return payload

    # ------------------------------------------------------------------
    # Bar construction
    # ------------------------------------------------------------------
    def _build_bar_tick(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        price = payload.get("last") or payload.get("bid") or payload.get("ask")
        if price is None:
            return None

        return {
            "symbol": payload["symbol"],
            "price": price,
            "last": payload.get("last"),
            "volume": payload.get("volume"),
            "bid": payload.get("bid"),
            "ask": payload.get("ask"),
            "timestamp": payload["timestamp"],
        }

    # ------------------------------------------------------------------
    # Main tick handler
    # ------------------------------------------------------------------
    def process_tick(self, tick: Dict[str, Any]) -> None:
        payload = self._normalize_payload(tick)
        if not payload:
            return

        try:
            session_key = self._resolve_session_key(payload)

            # Publish quote (session-agnostic)
            live_data_redis.publish_quote(payload["symbol"], payload)

            # Short TTL tick cache (session-based)
            live_data_redis.set_tick(
                session_key,
                payload["symbol"],
                payload,
                ttl=10,
            )

            # Update 1m bar (SESSION BASED)
            bar_tick = self._build_bar_tick(payload)
            if bar_tick:
                closed_bar, _current_bar = live_data_redis.upsert_current_bar_1m(
                    session_key,
                    payload["symbol"],
                    bar_tick,
                )
                if closed_bar:
                    live_data_redis.enqueue_closed_bar(session_key, closed_bar)

            # Broadcast to WebSocket
            broadcast_to_websocket_sync(
                self.channel_layer,
                {"type": "quote_tick", "data": payload},
            )

        except Exception:
            logger.exception(
                "Failed to process Schwab tick for %s",
                payload.get("symbol"),
            )

    # ------------------------------------------------------------------
    # Message fan-in
    # ------------------------------------------------------------------
    def process_message(self, message: Any) -> None:
        try:
            if isinstance(message, dict) and isinstance(message.get("content"), list):
                for tick in message["content"]:
                    if isinstance(tick, dict):
                        self.process_tick(tick)
            elif isinstance(message, dict):
                self.process_tick(message)
        except Exception:
            logger.exception("Failed to process Schwab streaming message")


schwab_streaming_producer = SchwabStreamingProducer()

__all__ = ["SchwabStreamingProducer", "schwab_streaming_producer"]
