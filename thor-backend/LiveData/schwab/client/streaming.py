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
    # Some streaming libs wrap numeric fields as objects, e.g. {"value": "400.12"}
    # or {"val": 400.12}. Unwrap common shapes.
    if isinstance(value, dict):
        for k in ("value", "val", "price", "p"):
            if k in value:
                return _to_float(value.get(k))
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
        tick.get("QUOTE_TIME_MILLIS"),
        tick.get("trade_time"),
        tick.get("TRADE_TIME_MILLIS"),
    ]
    for c in candidates:
        try:
            if c is None:
                continue
            ts = float(c)
            # Many Schwab fields are epoch-millis. Normalize to seconds.
            if ts > 1e12:
                ts = ts / 1000.0
            return ts
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


def _get_any(d: Dict[str, Any], *keys: Any) -> Any:
    """Return the first non-None value for any key, trying str/int forms.

    Schwab streaming often uses numeric field IDs serialized as strings
    (e.g. "1" for bid, "2" for ask, "3" for last).
    """
    for key in keys:
        if key is None:
            continue
        # Try as-is
        if key in d and d.get(key) is not None:
            return d.get(key)
        # Try str/int conversions
        try:
            sk = str(key)
            if sk in d and d.get(sk) is not None:
                return d.get(sk)
        except Exception:
            pass
        try:
            ik = int(key)  # may raise
            if ik in d and d.get(ik) is not None:
                return d.get(ik)
        except Exception:
            pass
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
        self._missing_routing_last_log: float = 0.0
        self._missing_price_last_log: dict[str, float] = {}
        self._logged_first_message: bool = False
        self._logged_first_payload: bool = False
        self._logged_first_redis_snapshot: bool = False

    @staticmethod
    def _to_session_key(value: Any) -> Optional[str]:
        """Coerce routing snapshot values into Redis session keys.

        Accepts:
        - "session:44" (pass-through)
        - 44 / "44" (converted)
        - legacy tokens like "USA:20251228:44" (converted)
        Returns:
        - "session:<n>" or None
        """
        if value is None:
            return None

        s = str(value).strip()
        if not s:
            return None

        lower = s.lower()
        if lower.startswith("session:"):
            num = lower.split(":", 1)[1].strip()
            if num.isdigit():
                return f"session:{int(num)}"
            return None

        # If it's just a number
        if s.isdigit():
            return f"session:{int(s)}"

        # Legacy tokens like "USA:YYYYMMDD:44" -> take last segment if numeric
        last = s.split(":")[-1].strip()
        if last.isdigit():
            return f"session:{int(last)}"
        return None

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
        snap = self._get_active_session_snapshot()
        if not snap:
            return None

        main = (payload.get("assetMainType") or payload.get("assetType") or "").upper()

        if "FUTURE" in main:
            return self._to_session_key(snap.get("futures") or snap.get("default"))
        if "EQUITY" in main or "STOCK" in main:
            return self._to_session_key(snap.get("equities") or snap.get("default"))

        return self._to_session_key(snap.get("default"))

    # ------------------------------------------------------------------
    # Payload normalization
    # ------------------------------------------------------------------
    def _normalize_payload(self, tick: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Level One Equity/Futures in schwab-py may provide numeric field IDs:
        # 0 symbol, 1 bid, 2 ask, 3 last, 8 total volume
        symbol_raw = _get_any(tick, "symbol", "key", "SYMBOL", "KEY", 0, "0")
        if not symbol_raw:
            return None
        symbol = str(symbol_raw).lstrip("/").upper()

        # Some Schwab streams use short keys:
        #   b = bid, a = ask, t = last/trade
        bid = _to_float(_get_any(tick, "bid", "bidPrice", "BID_PRICE", "BID", "b", "B", 1, "1"))
        ask = _to_float(_get_any(tick, "ask", "askPrice", "ASK_PRICE", "ASK", "a", "A", 2, "2"))
        last = _to_float(
            _get_any(
                tick,
                "last",
                "lastPrice",
                "LAST_PRICE",
                "trade",
                "tradePrice",
                "t",
                "T",
                "close",
                "MARK",
                3,
                "3",
            )
        )
        volume = _to_float(
            _get_any(
                tick,
                "volume",
                "totalVolume",
                "TOTAL_VOLUME",
                "lastSize",
                "LAST_SIZE",
                8,
                "8",
            )
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

        if not self._logged_first_payload:
            self._logged_first_payload = True
            logger.warning("Schwab first normalized payload=%s", payload)

        # Diagnostics: when price fields are missing, log the raw tick schema (throttled)
        if bid is None and ask is None and last is None:
            now = time.time()
            last_log = self._missing_price_last_log.get(symbol, 0.0)
            if now - last_log > 30:
                keys = sorted([str(k) for k in tick.keys()])
                sample = {
                    k: tick.get(k)
                    for k in (
                        "0",
                        "1",
                        "2",
                        "3",
                        "8",
                        "key",
                        "symbol",
                        "bid",
                        "ask",
                        "last",
                        "bidPrice",
                        "askPrice",
                        "lastPrice",
                        "BID_PRICE",
                        "ASK_PRICE",
                        "LAST_PRICE",
                        "TOTAL_VOLUME",
                        "QUOTE_TIME_MILLIS",
                        "TRADE_TIME_MILLIS",
                    )
                    if k in tick
                }
                logger.debug("Schwab tick missing bid/ask/last for %s; keys=%s sample=%s", symbol, keys, sample)
                self._missing_price_last_log[symbol] = now

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
            # Always publish quotes (session-agnostic)
            live_data_redis.publish_quote(payload["symbol"], payload)

            if not self._logged_first_redis_snapshot:
                self._logged_first_redis_snapshot = True
                try:
                    snap = live_data_redis.get_latest_quote(payload["symbol"])  # immediate readback
                    logger.warning("Schwab first Redis latest quote snapshot=%s", snap)
                except Exception:
                    logger.exception("Failed reading back latest quote after publish")

            session_key = self._resolve_session_key(payload)
            if not session_key:
                # No routing available: don't write bars/ticks to session namespaces
                # (and don't spam warnings)
                broadcast_to_websocket_sync(self.channel_layer, {"type": "quote_tick", "data": payload})
                return

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
            if not self._logged_first_message:
                self._logged_first_message = True
                try:
                    if isinstance(message, dict):
                        keys = sorted([str(k) for k in message.keys()])
                        if isinstance(message.get("content"), list) and message.get("content"):
                            first = message.get("content")[0]
                            first_keys = sorted([str(k) for k in first.keys()]) if isinstance(first, dict) else []
                            sample = None
                            if isinstance(first, dict):
                                want = (
                                    "0",
                                    "1",
                                    "2",
                                    "3",
                                    "8",
                                    "key",
                                    "symbol",
                                    "bid",
                                    "ask",
                                    "last",
                                    "b",
                                    "a",
                                    "t",
                                    "BID_PRICE",
                                    "ASK_PRICE",
                                    "LAST_PRICE",
                                    "TOTAL_VOLUME",
                                    "QUOTE_TIME_MILLIS",
                                    "TRADE_TIME_MILLIS",
                                )
                                sample = {k: first.get(k) for k in want if k in first}
                            logger.warning(
                                "Schwab first message keys=%s content_len=%s first_tick_keys=%s first_tick_sample=%s",
                                keys,
                                len(message.get("content")),
                                first_keys,
                                sample,
                            )
                        else:
                            logger.warning("Schwab first message keys=%s", keys)
                    else:
                        logger.warning("Schwab first message type=%s", type(message))
                except Exception:
                    logger.exception("Failed logging first Schwab message")

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
