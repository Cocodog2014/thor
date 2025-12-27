"""
Schwab streaming producer (schwab-py compatible).

Consumes streaming ticks, normalizes them into Thor quote payloads,
publishes to Redis, updates 1m bars, and broadcasts WebSocket events.

This module is resilient to missing schwab-py at import time; it only
tries to call schwab-py APIs when run().
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Iterable, Optional

from channels.layers import get_channel_layer

from api.websocket.broadcast import broadcast_to_websocket_sync
from LiveData.shared.redis_client import live_data_redis
from ThorTrading.services.config.country_codes import normalize_country_code

logger = logging.getLogger(__name__)


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

    def _normalize_payload(self, tick: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        symbol_raw = tick.get("symbol") or tick.get("key") or tick.get("SYMBOL")
        if not symbol_raw:
            return None
        symbol = str(symbol_raw).lstrip("/").upper()

        bid = _to_float(
            tick.get("bid")
            or tick.get("bidPrice")
            or tick.get("BID_PRICE")
            or tick.get("BID")
        )
        ask = _to_float(
            tick.get("ask")
            or tick.get("askPrice")
            or tick.get("ASK_PRICE")
            or tick.get("ASK")
        )
        last = _to_float(
            tick.get("last")
            or tick.get("lastPrice")
            or tick.get("LAST_PRICE")
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

        raw_country = tick.get("country") or tick.get("market") or tick.get("venue") or tick.get("exchange")
        country = normalize_country_code(raw_country) or raw_country or live_data_redis.DEFAULT_COUNTRY

        payload: Dict[str, Any] = {
            "symbol": symbol,
            "country": country,
            "bid": bid,
            "ask": ask,
            "last": last,
            "volume": volume,
            "timestamp": ts,
            "source": "SCHWAB",
        }

        # Preserve optional fields if present
        for key in ("assetType", "assetMainType", "exchange", "description"):
            if tick.get(key) is not None:
                payload[key] = tick.get(key)

        return payload

    def _build_bar_tick(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        price = payload.get("last") or payload.get("close") or payload.get("bid") or payload.get("ask")
        if price is None:
            return None
        return {
            "symbol": payload.get("symbol"),
            "country": payload.get("country") or live_data_redis.DEFAULT_COUNTRY,
            "price": price,
            "last": payload.get("last"),
            "volume": payload.get("volume"),
            "bid": payload.get("bid"),
            "ask": payload.get("ask"),
            "timestamp": payload.get("timestamp"),
        }

    def process_tick(self, tick: Dict[str, Any]) -> None:
        payload = self._normalize_payload(tick)
        if not payload:
            return

        try:
            # Publish quote (GLOBAL-safe)
            live_data_redis.publish_quote(payload["symbol"], payload)

            # Short TTL tick cache (per-country)
            live_data_redis.set_tick(payload.get("country") or live_data_redis.DEFAULT_COUNTRY, payload["symbol"], payload, ttl=10)

            # Update 1m bar
            bar_tick = self._build_bar_tick(payload)
            if bar_tick:
                country = bar_tick.get("country") or live_data_redis.DEFAULT_COUNTRY
                closed_bar, _current_bar = live_data_redis.upsert_current_bar_1m(country, payload["symbol"], bar_tick)
                if closed_bar:
                    live_data_redis.enqueue_closed_bar(country, closed_bar)

            # Broadcast to WebSocket
            message = {"type": "quote_tick", "data": payload}
            broadcast_to_websocket_sync(self.channel_layer, message)
        except Exception:
            logger.exception("Failed to process Schwab tick for %s", payload.get("symbol"))

    def process_message(self, message: Any) -> None:
        """Handle a message from schwab-py (dict with optional content list)."""
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

    async def run(
        self,
        streamer: Any,
        *,
        equities: Iterable[str] | None = None,
        futures: Iterable[str] | None = None,
    ) -> None:
        """
        Attach to a schwab-py Streamer and stream ticks.

        This is defensive: it only calls methods if the streamer exposes them.
        """
        if streamer is None:
            logger.error("No schwab streamer provided; aborting run()")
            return

        try:
            if equities and hasattr(streamer, "add_level_one_equity_subs"):
                streamer.add_level_one_equity_subs([s.upper() for s in equities])
            if futures and hasattr(streamer, "add_level_one_futures_subs"):
                streamer.add_level_one_futures_subs([s.upper() for s in futures])

            if hasattr(streamer, "start") and callable(streamer.start):
                await streamer.start()

            # Try a few common async iteration patterns
            if hasattr(streamer, "listen") and callable(streamer.listen):
                async for message in streamer.listen():
                    self.process_message(message)
            elif hasattr(streamer, "__aiter__"):
                async for message in streamer:
                    self.process_message(message)
            else:
                logger.warning("Streamer does not support async iteration; no messages consumed")
        except Exception:
            logger.exception("Schwab streaming loop failed")


schwab_streaming_producer = SchwabStreamingProducer()

__all__ = ["SchwabStreamingProducer", "schwab_streaming_producer"]
