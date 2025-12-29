"""
Schwab streaming producer (schwab-py compatible).

Consumes streaming ticks, normalizes them into Thor quote payloads,
publishes to Redis, updates 1m bars, and broadcasts WebSocket events.

IMPORTANT:
- No country logic.
- Routing is via session_key.
- session_key MUST be provided by GlobalMarkets via Redis.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Iterable, Optional

from channels.layers import get_channel_layer

from api.websocket.broadcast import broadcast_to_websocket_sync
from LiveData.shared.redis_client import live_data_redis

logger = logging.getLogger(__name__)

# GlobalMarkets must write this key to Redis
ACTIVE_SESSION_KEY_REDIS = "live_data:active_session"


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


def _safe_json_loads(raw: Any) -> Optional[dict]:
    if raw is None:
        return None
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            return json.loads(raw)
        if isinstance(raw, dict):
            return raw
    except Exception:
        return None
    return None


class SchwabStreamingProducer:
    """
    Normalize Schwab streaming ticks into Thor quote + bar updates.

    Session routing:
      - We do NOT use country.
      - We route bars/ticks using session_key.
      - session_key is fetched from Redis (written by GlobalMarkets heartbeat).
    """

    def __init__(self, channel_layer: Any | None = None):
        self.channel_layer = channel_layer or get_channel_layer()
        self._session_cache: Optional[dict] = None
        self._session_cache_until: float = 0.0  # unix time

    # ------------------------------------------------------------------
    # Session routing (THIS is where session numbers belong)
    # ------------------------------------------------------------------
    def _get_active_session_snapshot(self) -> Optional[dict]:
        """
        Reads active session routing from Redis.

        Expected Redis JSON structure (example):
        {
          "default": "USA:20251228:44",
          "equities": "USA:20251228:44",
          "futures": "USA:20251228:44",
          "updated_at": 1735412345
        }
        """
        now = time.time()
        if self._session_cache and now < self._session_cache_until:
            return self._session_cache

        raw = None
        try:
            raw = live_data_redis.client.get(ACTIVE_SESSION_KEY_REDIS)
        except Exception:
            logger.exception("Failed reading %s from Redis", ACTIVE_SESSION_KEY_REDIS)

        data = _safe_json_loads(raw)

        # Cache for a short time to avoid Redis GET per tick
        self._session_cache = data
        self._session_cache_until = now + 2.0  # 2s cache
        return data

    def _resolve_session_key(self, payload: Dict[str, Any]) -> Optional[str]:
        """
        Returns a session_key like:
                    "session:44"

        No GLOBAL fallback. If routing is missing, return None and we skip bar writes.
        """
        snap = self._get_active_session_snapshot()
        if not snap:
            return None

        # Try to route by asset type if provided
        main = (payload.get("assetMainType") or payload.get("assetType") or "").upper()

        if "FUTURE" in main:
            return snap.get("futures") or snap.get("default")
        if "EQUITY" in main or "STOCK" in main:
            return snap.get("equities") or snap.get("default")

        # Unknown asset type -> default routing
        return snap.get("default")

    # ------------------------------------------------------------------
    # Payload normalization
    # ------------------------------------------------------------------
    def _normalize_payload(self, tick: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        symbol_raw = tick.get("symbol") or tick.get("key") or tick.get("SYMBOL")
        if not symbol_raw:
            return None
        symbol = str(symbol_raw).lstrip("/").upper()

        bid = _to_float(tick.get("bid") or tick.get("bidPrice") or tick.get("BID"))
        ask = _to_float(tick.get("ask") or tick.get("askPrice") or tick.get("ASK"))
        last = _to_float(
            tick.get("last")
            or tick.get("lastPrice")
            or tick.get("close")
            or tick.get("MARK")
        )
        volume = _to_float(
            tick.get("volume")
            or tick.get("totalVolume")
            or tick.get("TOTAL_VOLUME")
            or tick.get("lastSize")
            or tick.get("LAST_SIZE")
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

            # Always publish quotes (session-agnostic)
            live_data_redis.publish_quote(payload["symbol"], payload)

            # If we don't know the session, skip bar writes (no GLOBAL fallback)
            if not session_key:
                logger.warning(
                    "No active session routing in Redis (%s). Skipping bar/tick cache for %s",
                    ACTIVE_SESSION_KEY_REDIS,
                    payload.get("symbol"),
                )
            else:
                payload["session_key"] = session_key
                session_number = live_data_redis._parse_session_number(session_key)  # internal helper
                if session_number is not None:
                    payload["session_number"] = session_number

                # Short TTL tick cache (keyed by session)
                live_data_redis.set_tick(session_key, payload["symbol"], payload, ttl=10)

                # Update 1m bar (keyed by session)
                bar_tick = self._build_bar_tick(payload)
                if bar_tick:
                    if session_number is not None:
                        bar_tick["session_number"] = session_number
                    closed_bar, _cur = live_data_redis.upsert_current_bar_1m(
                        session_key, payload["symbol"], bar_tick
                    )
                    if closed_bar:
                        live_data_redis.enqueue_closed_bar(session_key, closed_bar)

            # Broadcast to WebSocket
            broadcast_to_websocket_sync(self.channel_layer, {"type": "quote_tick", "data": payload})

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
                for tick in message.get("content", []):
                    if isinstance(tick, dict):
                        self.process_tick(tick)
                return
            if isinstance(message, dict):
                self.process_tick(message)
        except Exception:
            logger.exception("Failed to process Schwab streaming message")


schwab_streaming_producer = SchwabStreamingProducer()

__all__ = ["SchwabStreamingProducer", "schwab_streaming_producer"]
