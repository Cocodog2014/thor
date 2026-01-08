"""
Shared Redis client for all LiveData broker feeds.

Provides a unified interface for publishing market data to Redis channels.
All broker integrations (Schwab, TOS, IBKR) use this client.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone as dt_timezone
from typing import Dict, Any, Optional, Tuple, List

import redis
from django.conf import settings
from django.utils import timezone as dj_timezone

# from GlobalMarkets.services.normalize import normalize_country_code

logger = logging.getLogger(__name__)


def _to_epoch_seconds_utc(value) -> int:
    """
    Accepts:
      - int/float epoch seconds
      - ISO string (best-effort)
      - datetime (aware or naive; naive assumed UTC)
    Returns epoch seconds (int) in UTC.
    """
    if value is None:
        return int(dj_timezone.now().timestamp())

    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=dt_timezone.utc)
        return int(dt.astimezone(dt_timezone.utc).timestamp())

    if isinstance(value, str):
        s = value.strip()
        # Try ISO first
        try:
            # handle trailing Z
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=dt_timezone.utc)
            return int(dt.astimezone(dt_timezone.utc).timestamp())
        except Exception:
            pass

        # Last resort: numeric string epoch
        try:
            return int(float(s))
        except Exception:
            return int(dj_timezone.now().timestamp())

    return int(dj_timezone.now().timestamp())


class LiveDataRedis:
    """
    Shared Redis client for publishing live market data.

    All broker feeds publish through this client to ensure consistent
    channel naming and data formatting.

    Updated to route by `routing_key` (session_number-based). The caller must
    supply the active routing key; there is no GLOBAL fallback for bars.
    """

    DEFAULT_COUNTRY = "GLOBAL"

    # --- Snapshot (latest) helpers ---
    LATEST_QUOTES_HASH = "live_data:latest:quotes"
    ACTIVE_QUOTES_ZSET = "live_data:active_symbols"

    # --- Instrument quote-source preference map (symbol -> source) ---
    # Values: AUTO | SCHWAB | TOS
    INSTRUMENT_QUOTE_SOURCE_HASH = "instruments:quote_source"

    # --- Single-flight lock for Excel reads ---
    EXCEL_LOCK_KEY = "live_data:excel_lock"
    EXCEL_LOCK_TTL = 10  # seconds

    # --- Active session routing snapshot (written by GlobalMarkets heartbeat) ---
    ACTIVE_SESSION_KEY_REDIS = "live_data:active_session"

    def __init__(self):
        """Initialize Redis connection from Django settings."""
        self.client = redis.Redis(
            host=getattr(settings, "REDIS_HOST", "localhost"),
            port=getattr(settings, "REDIS_PORT", 6379),
            db=getattr(settings, "REDIS_DB", 0),
            decode_responses=True,
        )

    # -------------------------
    # Routing helpers
    # -------------------------
    def _routing_prefix(self, routing_key: str | None) -> str:
        """Normalize routing key for Redis keys (session-first)."""
        if routing_key is None:
            return "global"
        return str(routing_key).strip().lower() or "global"

    @staticmethod
    def _parse_session_number(routing_key: str | None) -> int | None:
        if not routing_key:
            return None
        raw = str(routing_key).lower()
        if raw.startswith("session:"):
            raw = raw.split(":", 1)[1]
        # Support daily ISO session keys like "2026-01-06" by mapping to int 20260106.
        # This keeps session_number compatible with existing int-based DB fields.
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            raw = raw.replace("-", "")
        try:
            return int(raw)
        except Exception:
            return None

    def _get_active_session_snapshot(self) -> dict | None:
        """Return the cached active session routing payload from Redis."""
        try:
            raw = self.client.get(self.ACTIVE_SESSION_KEY_REDIS)
        except Exception:
            logger.debug("Failed to read %s", self.ACTIVE_SESSION_KEY_REDIS, exc_info=True)
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            logger.debug("Failed to parse %s payload", self.ACTIVE_SESSION_KEY_REDIS, exc_info=True)
            return None

    def get_active_session_number(self, asset_type: str | None = None) -> int | None:
        """Fetch active session_number from GlobalMarkets heartbeat snapshot."""
        snap = self._get_active_session_snapshot() or {}
        if not snap or not isinstance(snap, dict):
            return None

        num = snap.get("session_number")
        if num is not None:
            try:
                return int(num)
            except Exception:
                return None

        asset = (asset_type or "").upper()
        if asset in {"FUTURE", "FUTURES"}:
            return self._parse_session_number(snap.get("futures") or snap.get("default"))
        if asset in {"EQUITY", "EQUITIES", "STOCK"}:
            return self._parse_session_number(snap.get("equities") or snap.get("default"))
        return self._parse_session_number(snap.get("default"))

    def get_active_session_key(self, asset_type: str | None = None) -> str | None:
        """Backward-compatible alias: returns the active session_number as a string."""
        num = self.get_active_session_number(asset_type=asset_type)
        return str(num) if num is not None else None

    # -------------------------
    # Country normalization
    # -------------------------
    def _norm_country(self, country: str) -> str:
        normalized = normalize_country_code(country) if country is not None else None
        return normalized or country

    # -------------------------
    # Pub/Sub base
    # -------------------------
    def publish(self, channel: str, data: Dict[str, Any]) -> int:
        """
        Publish JSON data to a Redis channel.

        Returns:
            Number of subscribers that received the message
        """
        try:
            message = json.dumps(data, default=str)
            result = self.client.publish(channel, message)
            logger.debug("Published to %s: %s bytes to %s subscribers", channel, len(message), result)
            return result
        except Exception as e:
            logger.error("Failed to publish to %s: %s", channel, e)
            return 0

    # -------------------------
    # Tick + bar capture primitives
    # -------------------------

    # --- Live 24h snapshot (session_number + symbol) ---
    def upsert_live_24h_snapshot(
        self,
        session_number: int,
        symbol: str,
        *,
        price: Any,
        volume: Any = None,
        ttl_seconds: int = 60 * 60 * 48,
    ) -> Dict[str, Any] | None:
        """Upsert the live 24h snapshot in Redis.

        Key: live:24h:{session_number}:{SYMBOL}
        Stored as Redis HASH fields:
          open_24h, high_24h, low_24h, close_24h, volume_24h, updated_at
        """

        try:
            sn = int(session_number)
        except Exception:
            return None

        sym = (symbol or "").strip().upper()
        if not sym:
            return None

        try:
            px = float(price)
        except Exception:
            return None

        key = f"live:24h:{sn}:{sym}".lower()

        try:
            open_s, high_s, low_s, close_s, vol_s = self.client.hmget(
                key, "open_24h", "high_24h", "low_24h", "close_24h", "volume_24h"
            )
        except Exception:
            open_s = high_s = low_s = close_s = vol_s = None

        def _to_float(v: Any) -> float | None:
            if v in (None, ""):
                return None
            try:
                return float(v)
            except Exception:
                return None

        def _to_int(v: Any) -> int | None:
            if v in (None, ""):
                return None
            try:
                return int(float(v))
            except Exception:
                return None

        open_v = _to_float(open_s)
        high_v = _to_float(high_s)
        low_v = _to_float(low_s)
        close_v = _to_float(close_s)
        vol_v = _to_int(vol_s) or 0

        if open_v is None:
            open_v = px
        if high_v is None or px > high_v:
            high_v = px
        if low_v is None or px < low_v:
            low_v = px
        close_v = px

        # Prefer a monotonic volume if we get a provider-supplied cumulative volume.
        if volume not in (None, ""):
            try:
                incoming = int(float(volume))
                if incoming >= vol_v:
                    vol_v = incoming
            except Exception:
                pass

        updated_at = float(time.time())

        payload = {
            "open": open_v,
            "high": high_v,
            "low": low_v,
            "close": close_v,
            "volume": int(vol_v or 0),
            "updated_at": updated_at,
            "session_number": sn,
            "symbol": sym,
        }

        try:
            self.client.hset(
                key,
                mapping={
                    "open_24h": open_v,
                    "high_24h": high_v,
                    "low_24h": low_v,
                    "close_24h": close_v,
                    "volume_24h": int(vol_v or 0),
                    "updated_at": updated_at,
                },
            )
            self.client.expire(key, int(ttl_seconds))
        except Exception:
            logger.debug("Failed to upsert live 24h snapshot %s", key, exc_info=True)
            return None

        return payload

    def get_live_24h_snapshot(self, session_number: int, symbol: str) -> Dict[str, Any] | None:
        """Read the live 24h snapshot from Redis."""
        try:
            sn = int(session_number)
        except Exception:
            return None
        sym = (symbol or "").strip().upper()
        if not sym:
            return None
        key = f"live:24h:{sn}:{sym}".lower()
        try:
            data = self.client.hgetall(key)
        except Exception:
            return None
        if not data:
            return None
        try:
            return {
                "session_number": sn,
                "symbol": sym,
                "open": float(data.get("open_24h")) if data.get("open_24h") is not None else None,
                "high": float(data.get("high_24h")) if data.get("high_24h") is not None else None,
                "low": float(data.get("low_24h")) if data.get("low_24h") is not None else None,
                "close": float(data.get("close_24h")) if data.get("close_24h") is not None else None,
                "volume": int(float(data.get("volume_24h") or 0)),
                "updated_at": float(data.get("updated_at")) if data.get("updated_at") is not None else None,
            }
        except Exception:
            return None
    def set_tick(self, routing_key: str, symbol: str, payload: Dict[str, Any], ttl: int = 10) -> None:
        """
        Cache latest tick for a symbol scoped by routing_key (session).
        Key: tick:{routing_key}:{symbol}
        """
        key = f"tick:{self._routing_prefix(routing_key)}:{symbol}".lower()
        try:
            self.client.set(key, json.dumps(payload, default=str), ex=ttl)
        except Exception as e:
            logger.error("Failed to set tick %s: %s", key, e)

    def upsert_current_bar_1m(
        self,
        routing_key: str,
        symbol: str,
        tick: Dict[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Update the in-progress 1m bar for this symbol. Returns (closed_bar, current_bar).

        Uses the tick's UTC timestamp to determine the minute bucket when available.
        Falls back to server/Django time (UTC) when not.

        Expected tick keys: price/last/close and (optional) volume.
        Optional tick timestamp keys (any one): ts, timestamp, time, datetime
        """
        prefix = self._routing_prefix(routing_key)
        key = f"bar:1m:current:{prefix}:{symbol}".lower()

        # 1) price + volume
        price = tick.get("price") or tick.get("last") or tick.get("close")
        if price is None:
            raise ValueError("tick missing price/last/close field")
        price = float(price)

        volume = tick.get("volume") or tick.get("v") or 0
        try:
            volume = float(volume) if volume is not None else 0
        except Exception:
            volume = 0

        # 1b) bid/ask/spread (optional)
        bid = tick.get("bid")
        ask = tick.get("ask")

        try:
            bid = float(bid) if bid is not None else None
        except Exception:
            bid = None

        try:
            ask = float(ask) if ask is not None else None
        except Exception:
            ask = None

        spread = None
        if bid is not None and ask is not None:
            spread = ask - bid

        # 2) timestamp (UTC)
        ts_raw = tick.get("ts") or tick.get("timestamp") or tick.get("time") or tick.get("datetime")
        ts_epoch = _to_epoch_seconds_utc(ts_raw)
        # Some providers round timestamps to the next minute (or clocks can skew),
        # which can prematurely roll bars forward. Clamp to server time.
        now_epoch = int(dj_timezone.now().timestamp())
        if ts_epoch > now_epoch:
            ts_epoch = now_epoch

        # 3) load existing bar
        closed_bar = None
        existing_raw = self.client.get(key)
        existing = None
        if existing_raw:
            try:
                existing = json.loads(existing_raw)
            except Exception:
                existing = None

        # 4) minute bucket (UTC)
        bucket = ts_epoch // 60
        # Never allow time to go backwards for a given symbol's current bar.
        if existing and existing.get("bucket") is not None:
            try:
                existing_bucket = int(existing.get("bucket"))
                if bucket < existing_bucket:
                    bucket = existing_bucket
            except Exception:
                pass
        minute_epoch = bucket * 60
        timestamp_minute = datetime.fromtimestamp(minute_epoch, tz=dt_timezone.utc).isoformat()

        # 5) rollover or update
        session_number = self._parse_session_number(routing_key)

        if not existing or existing.get("bucket") != bucket:
            # if we had a previous bucket, that bar is now closed
            if existing and existing.get("bucket") is not None:
                if "timestamp_minute" not in existing and "t" in existing:
                    try:
                        t_epoch = int(existing["t"])
                        existing["timestamp_minute"] = datetime.fromtimestamp(t_epoch, tz=dt_timezone.utc).isoformat()
                    except Exception:
                        pass
                closed_bar = {**existing, "routing_key": routing_key}
                if session_number is not None:
                    closed_bar["session_number"] = session_number

            current_bar = {
                "bucket": bucket,
                "t": minute_epoch,  # epoch minute start (UTC)
                "timestamp_minute": timestamp_minute,  # ISO UTC minute start
                "o": price,
                "h": price,
                "l": price,
                "c": price,
                "v": volume,
                "bid": bid,
                "ask": ask,
                "spread": spread,
                "country": tick.get("country"),
                "symbol": symbol,
                "routing_key": routing_key,
                **({"session_number": session_number} if session_number is not None else {}),
            }
        else:
            current_bar = existing
            current_bar["h"] = max(float(current_bar["h"]), price)
            current_bar["l"] = min(float(current_bar["l"]), price)
            current_bar["c"] = price
            current_bar["v"] = float(current_bar.get("v") or 0) + volume

            if bid is not None:
                current_bar["bid"] = bid
            if ask is not None:
                current_bar["ask"] = ask
            if bid is not None and ask is not None:
                current_bar["spread"] = ask - bid

            current_bar["timestamp_minute"] = current_bar.get("timestamp_minute") or timestamp_minute
            current_bar["t"] = current_bar.get("t") or minute_epoch

        current_bar["routing_key"] = routing_key
        if session_number is not None:
            current_bar["session_number"] = session_number
        self.client.set(key, json.dumps(current_bar, default=str))
        return closed_bar, current_bar

    def enqueue_closed_bar(self, routing_key: str, bar: Dict[str, Any]) -> None:
        """
        Push a finalized 1m bar onto the session queue for later DB flush.
        Key: q:bars:1m:{routing_key}
        """
        prefix = self._routing_prefix(routing_key)
        key = f"q:bars:1m:{prefix}"
        session_number = self._parse_session_number(routing_key)
        meta = {"routing_key": routing_key}
        if session_number is not None:
            meta["session_number"] = session_number

        bar = {**bar, **meta}
        try:
            self.client.rpush(key, json.dumps(bar, default=str))
        except Exception as e:
            logger.error("Failed to enqueue closed bar for %s: %s", routing_key, e)

    def requeue_processing_closed_bars(self, routing_key: str, limit: int = 10000) -> int:
        """Move any bars stuck in the processing queue back to the main queue (crash recovery)."""
        prefix = self._routing_prefix(routing_key)
        source = f"q:bars:1m:{prefix}:processing"
        target = f"q:bars:1m:{prefix}"
        moved = 0
        try:
            for _ in range(limit):
                item = self.client.rpoplpush(source, target)
                if not item:
                    break
                moved += 1
        except Exception as e:
            logger.error("Failed to requeue processing bars for %s: %s", prefix, e)
        return moved

    def checkout_closed_bars(self, routing_key: str, count: int = 500) -> Tuple[List[dict], List[str], int]:
        """
        Atomically move up to `count` bars from the main queue to a processing queue.

        Returns: (decoded_bars, raw_items, queue_left)
        """
        prefix = self._routing_prefix(routing_key)
        source = f"q:bars:1m:{prefix}"
        processing = f"q:bars:1m:{prefix}:processing"
        items: List[str] = []

        try:
            pipe = self.client.pipeline()
            for _ in range(count):
                pipe.lmove(source, processing, "LEFT", "RIGHT")
            pipe.llen(source)
            results = pipe.execute()
            *moved_items, queue_left = results
            items = [i for i in moved_items if i]
        except Exception as e:
            logger.error("Failed to checkout closed bars for %s: %s", prefix, e)
            return [], [], 0

        if not items:
            return [], [], int(queue_left or 0)

        decoded: List[dict] = []
        for item in items:
            try:
                decoded.append(json.loads(item))
            except Exception:
                logger.warning("Failed to decode closed bar payload for %s: %s", prefix, item)

        return decoded, items, int(queue_left or 0)

    def acknowledge_closed_bars(self, routing_key: str, items: List[str]) -> None:
        """Remove successfully processed items from the processing queue."""
        if not items:
            return
        prefix = self._routing_prefix(routing_key)
        key = f"q:bars:1m:{prefix}:processing"
        try:
            pipe = self.client.pipeline()
            for item in items:
                pipe.lrem(key, 1, item)
            pipe.execute()
        except Exception as e:
            logger.error("Failed to acknowledge closed bars for %s: %s", prefix, e)

    def return_closed_bars(self, routing_key: str, items: List[str]) -> None:
        """Return items to the main queue if processing failed (and remove from processing queue)."""
        if not items:
            return
        prefix = self._routing_prefix(routing_key)
        main_key = f"q:bars:1m:{prefix}"
        processing_key = f"q:bars:1m:{prefix}:processing"
        try:
            pipe = self.client.pipeline()
            for item in items:
                pipe.lrem(processing_key, 1, item)
            pipe.rpush(main_key, *items)
            pipe.execute()
        except Exception as e:
            logger.error("Failed to return closed bars for %s: %s", prefix, e)

    # -------------------------
    # Latest quote snapshot helpers
    # -------------------------
    def set_latest_quote(self, symbol: str, data: Dict[str, Any]) -> None:
        """Cache the latest quote for a symbol in a Redis hash (GLOBAL-safe)."""
        try:
            sym = symbol.upper()
            raw = data.get("country") or data.get("market") or self.DEFAULT_COUNTRY
            norm = self._norm_country(raw) or raw or self.DEFAULT_COUNTRY

            payload = json.dumps({"symbol": sym, **data, "country": norm}, default=str)
            self.client.hset(self.LATEST_QUOTES_HASH, sym, payload)
        except Exception as e:
            logger.error("Failed to cache latest quote for %s: %s", symbol, e)

    def get_latest_quote(self, symbol: str) -> Dict[str, Any] | None:
        try:
            raw = self.client.hget(self.LATEST_QUOTES_HASH, symbol.upper())
            if not raw:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.error("Failed to read latest quote for %s: %s", symbol, e)
            return None

    def get_latest_quotes(self, symbols: list[str]) -> list[Dict[str, Any]]:
        out: list[Dict[str, Any]] = []
        for s in symbols:
            q = self.get_latest_quote(s)
            if q:
                out.append(q)
        return out

    # -------------------------
    # Excel lock
    # -------------------------
    def acquire_excel_lock(self, timeout: int = 10) -> bool:
        """Try to acquire exclusive Excel read lock (SET NX with TTL)."""
        try:
            result = self.client.set(self.EXCEL_LOCK_KEY, "locked", nx=True, ex=timeout)
            return bool(result)
        except Exception as e:
            logger.error("Failed to acquire Excel lock: %s", e)
            return False

    def release_excel_lock(self) -> None:
        """Release the Excel read lock."""
        try:
            self.client.delete(self.EXCEL_LOCK_KEY)
        except Exception as e:
            logger.error("Failed to release Excel lock: %s", e)

    # -------------------------
    # Publish helpers (quotes/positions/balances/orders/transactions)
    # -------------------------
    def publish_quote(
        self,
        symbol: str,
        data: Dict[str, Any],
        *,
        provider: str | None = None,
        asset_type: str | None = None,
        ts: int | float | str | datetime | None = None,
        broadcast_ws: bool = False,
    ) -> int:
        """
        Publish quote data for a symbol and optionally fan out to WebSocket.

        Args:
            symbol: Ticker/contract symbol
            data: Quote payload (bid/ask/last/volume/etc.)
            provider: Source feed identifier (e.g., "schwab")
            asset_type: Asset category (e.g., "EQUITY", "FUTURE", "INDEX")
            ts: Optional timestamp for this quote. If omitted, best-effort from data or now.
            broadcast_ws: If True, also emit a `quote_tick` over Channels
        """
        from .channels import get_quotes_channel

        sym = symbol.upper()
        channel = get_quotes_channel(sym)

        # Enforce per-symbol quote source preference when we can identify the provider.
        provider_norm = (
            (provider or data.get("provider") or data.get("source") or "")
            .strip()
            .upper()
        )
        if provider_norm:
            try:
                desired = self.client.hget(self.INSTRUMENT_QUOTE_SOURCE_HASH, sym)
            except Exception:
                desired = None
            desired_norm = (desired or "AUTO").strip().upper()
            if desired_norm not in {"", "AUTO"} and provider_norm != desired_norm:
                # Ignore ticks from non-selected feeds (prevents cross-feed overwrites).
                return 0

        raw = data.get("country") or data.get("market") or self.DEFAULT_COUNTRY
        norm = self._norm_country(raw) or raw or self.DEFAULT_COUNTRY

        ts_raw = ts or data.get("ts") or data.get("timestamp") or data.get("time") or data.get("datetime")
        ts_epoch = _to_epoch_seconds_utc(ts_raw)

        payload: Dict[str, Any] = {
            "type": "quote",
            "symbol": sym,
            **data,
            "country": norm,
            "ts": ts_epoch,
        }

        # If another provider sends partial quotes (e.g. volume-only), don't
        # overwrite previously-known bid/ask/last with None.
        try:
            existing = self.get_latest_quote(sym) or {}
            for k in ("bid", "ask", "last"):
                if payload.get(k) is None and existing.get(k) is not None:
                    payload[k] = existing.get(k)
        except Exception:
            # Never fail publishing due to a merge attempt.
            pass
        if provider:
            payload["provider"] = provider
        if asset_type:
            payload["asset_type"] = asset_type

        result = self.publish(channel, payload)
        self.set_latest_quote(sym, payload)

        # Track "active" symbols for snapshot batching (score = last update epoch seconds)
        try:
            self.client.zadd(self.ACTIVE_QUOTES_ZSET, {sym: float(ts_epoch)})
        except Exception:
            logger.debug("Failed to update active symbols zset", exc_info=True)

        if broadcast_ws:
            try:
                from api.websocket.broadcast import broadcast_to_websocket_sync

                broadcast_to_websocket_sync(
                    channel_layer=None,
                    message={"type": "quote_tick", "data": payload},
                )
            except Exception:
                logger.exception("Failed to broadcast quote to WebSocket for %s", sym)

        return result

    def publish_raw_quote(self, symbol: str, data: Dict[str, Any]) -> int:
        """Publish a raw quote without requiring country. Stores snapshot and publishes a raw channel."""
        symbol_upper = symbol.upper()
        payload = {"symbol": symbol_upper, **data}
        try:
            key = f"raw:quote:{symbol_upper}"
            self.set_json(key, payload)
            channel = "raw:quotes"
            return self.publish(channel, payload)
        except Exception:
            logger.exception("Failed to publish raw quote for %s", symbol_upper)
            return 0

    def set_json(self, key: str, value: Dict[str, Any], ex: int | None = None) -> None:
        """Store JSON payload at a Redis key (helper for background workers)."""
        try:
            payload = json.dumps(value, default=str)
            self.client.set(name=key, value=payload, ex=ex)
        except Exception as e:
            logger.error("Failed to set Redis key %s: %s", key, e)

    def publish_position(self, account_id: str, data: Dict[str, Any]) -> int:
        """Publish position update."""
        from .channels import get_positions_channel

        channel = get_positions_channel(account_id)
        payload = {"type": "position", "account_id": account_id, **data}
        return self.publish(channel, payload)

    def publish_balance(self, account_id: str, data: Dict[str, Any]) -> int:
        """Publish balance update."""
        from .channels import get_balances_channel

        channel = get_balances_channel(account_id)
        payload = {"type": "balance", "account_id": account_id, **data}
        return self.publish(channel, payload)

    def publish_order(self, account_id: str, data: Dict[str, Any]) -> int:
        """Publish order update."""
        from .channels import get_orders_channel

        channel = get_orders_channel(account_id)
        payload = {"type": "order", "account_id": account_id, **data}
        return self.publish(channel, payload)

    def publish_transaction(self, account_id: str, data: Dict[str, Any]) -> int:
        """Publish transaction update."""
        from .channels import get_transactions_channel

        channel = get_transactions_channel(account_id)
        payload = {"type": "transaction", "account_id": account_id, **data}
        return self.publish(channel, payload)


# Singleton instance
live_data_redis = LiveDataRedis()
