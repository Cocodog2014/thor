"""
Shared Redis client for all LiveData broker feeds.

Provides a unified interface for publishing market data to Redis channels.
All broker integrations (Schwab, TOS, IBKR) use this client.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, Tuple

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


class LiveDataRedis:
    """
    Shared Redis client for publishing live market data.
    
    All broker feeds publish through this client to ensure consistent
    channel naming and data formatting.
    """
    
    def __init__(self):
        """Initialize Redis connection from Django settings."""
        self.client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0),
            decode_responses=True
        )
    
    def publish(self, channel: str, data: Dict[str, Any]) -> int:
        """
        Publish JSON data to a Redis channel.
        
        Args:
            channel: Redis channel name
            data: Dictionary to publish (will be JSON-serialized)
            
        Returns:
            Number of subscribers that received the message
        """
        try:
            # Use default=str to handle Decimal and datetime objects
            message = json.dumps(data, default=str)
            result = self.client.publish(channel, message)
            logger.debug(f"Published to {channel}: {len(message)} bytes to {result} subscribers")
            return result
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            return 0

    # --- Tick + bar capture primitives ---
    def set_tick(self, country: str, symbol: str, payload: Dict[str, Any], ttl: int = 10) -> None:
        """
        Cache latest tick for a symbol (per country) with a short TTL.
        Key: tick:{country}:{symbol}
        """
        key = f"tick:{country}:{symbol}".lower()
        try:
            self.client.set(key, json.dumps(payload, default=str), ex=ttl)
        except Exception as e:
            logger.error(f"Failed to set tick {key}: {e}")

    def upsert_current_bar_1m(self, country: str, symbol: str, tick: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Update the in-progress 1m bar for this symbol. Returns (closed_bar, current_bar).

        closed_bar is None unless the minute bucket rolled over.
        Expected tick keys: price/last and volume (best-effort fallback to 0 volume).
        """
        key = f"bar:1m:current:{country}:{symbol}".lower()
        now = int(time.time())
        bucket = now // 60

        price = tick.get("price") or tick.get("last") or tick.get("close")
        if price is None:
            raise ValueError("tick missing price/last/close field")
        try:
            price = float(price)
        except Exception as e:
            raise ValueError(f"invalid price value: {price}") from e

        volume = tick.get("volume") or tick.get("vol") or 0
        try:
            volume = float(volume)
        except Exception:
            volume = 0.0

        # Load existing bar
        existing_raw = self.client.get(key)
        existing = json.loads(existing_raw) if existing_raw else None

        closed_bar = None

        if existing and existing.get("bucket") != bucket:
            closed_bar = existing
            existing = None

        if not existing:
            current_bar = {
                "bucket": bucket,
                "t": bucket * 60,
                "o": price,
                "h": price,
                "l": price,
                "c": price,
                "v": volume,
                "country": country,
                "symbol": symbol,
            }
        else:
            current_bar = existing
            current_bar["h"] = max(current_bar["h"], price)
            current_bar["l"] = min(current_bar["l"], price)
            current_bar["c"] = price
            current_bar["v"] = (current_bar.get("v") or 0) + volume

        self.client.set(key, json.dumps(current_bar, default=str))
        return closed_bar, current_bar

    def enqueue_closed_bar(self, country: str, bar: Dict[str, Any]) -> None:
        """
        Push a finalized 1m bar onto the per-country queue for later DB flush.
        Key: q:bars:1m:{country}
        """
        key = f"q:bars:1m:{country}".lower()
        try:
            self.client.rpush(key, json.dumps(bar, default=str))
        except Exception as e:
            logger.error(f"Failed to enqueue closed bar for {country}: {e}")

    # --- Snapshot (latest) helpers ---
    LATEST_QUOTES_HASH = "live_data:latest:quotes"

    def set_latest_quote(self, symbol: str, data: Dict[str, Any]) -> None:
        """Cache the latest quote for a symbol in a Redis hash.

        Stored as JSON string to preserve types; use default=str for Decimals.
        """
        try:
            payload = json.dumps({"symbol": symbol.upper(), **data}, default=str)
            self.client.hset(self.LATEST_QUOTES_HASH, symbol.upper(), payload)
        except Exception as e:
            logger.error(f"Failed to cache latest quote for {symbol}: {e}")

    def get_latest_quote(self, symbol: str) -> Dict[str, Any] | None:
        try:
            raw = self.client.hget(self.LATEST_QUOTES_HASH, symbol.upper())
            if not raw:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Failed to read latest quote for {symbol}: {e}")
            return None

    def get_latest_quotes(self, symbols: list[str]) -> list[Dict[str, Any]]:
        out = []
        for s in symbols:
            q = self.get_latest_quote(s)
            if q:
                out.append(q)
        return out
    
    # --- Single-flight lock for Excel reads ---
    EXCEL_LOCK_KEY = "live_data:excel_lock"
    EXCEL_LOCK_TTL = 10  # seconds - prevents stale locks if a read crashes

    def acquire_excel_lock(self, timeout: int = 10) -> bool:
        """
        Try to acquire exclusive Excel read lock (SET NX with TTL).
        
        Args:
            timeout: Lock TTL in seconds (auto-expires if holder crashes)
        
        Returns:
            True if lock acquired, False if another reader holds it
        """
        try:
            result = self.client.set(
                self.EXCEL_LOCK_KEY,
                "locked",
                nx=True,  # Only set if key doesn't exist
                ex=timeout  # Auto-expire after timeout seconds
            )
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to acquire Excel lock: {e}")
            return False

    def release_excel_lock(self) -> None:
        """Release the Excel read lock."""
        try:
            self.client.delete(self.EXCEL_LOCK_KEY)
        except Exception as e:
            logger.error(f"Failed to release Excel lock: {e}")
    
    def publish_quote(self, symbol: str, data: Dict[str, Any]) -> int:
        """
        Publish quote data for a symbol (used by TOS and other streaming feeds).
        
        Args:
            symbol: Stock/futures symbol
            data: Quote data (bid, ask, last, volume, etc.)
        """
        from .channels import get_quotes_channel
        channel = get_quotes_channel(symbol)
        
        payload = {
            "type": "quote",
            "symbol": symbol.upper(),
            **data
        }
        # Publish to subscribers
        result = self.publish(channel, payload)
        # Cache snapshot
        self.set_latest_quote(symbol, payload)
        return result

    def set_json(self, key: str, value: Dict[str, Any], ex: int | None = None) -> None:
        """Store JSON payload at a Redis key (helper for background workers)."""
        try:
            payload = json.dumps(value, default=str)
            self.client.set(name=key, value=payload, ex=ex)
        except Exception as e:
            logger.error(f"Failed to set Redis key {key}: {e}")
    
    def publish_position(self, account_id: str, data: Dict[str, Any]) -> int:
        """
        Publish position update (used by Schwab API and other account feeds).
        
        Args:
            account_id: Account identifier
            data: Position data (symbol, quantity, market_value, etc.)
        """
        from .channels import get_positions_channel
        channel = get_positions_channel(account_id)
        
        payload = {
            "type": "position",
            "account_id": account_id,
            **data
        }
        return self.publish(channel, payload)
    
    def publish_balance(self, account_id: str, data: Dict[str, Any]) -> int:
        """
        Publish balance update (used by Schwab API and other account feeds).
        
        Args:
            account_id: Account identifier
            data: Balance data (cash, buying_power, account_value, etc.)
        """
        from .channels import get_balances_channel
        channel = get_balances_channel(account_id)
        
        payload = {
            "type": "balance",
            "account_id": account_id,
            **data
        }
        return self.publish(channel, payload)
    
    def publish_order(self, account_id: str, data: Dict[str, Any]) -> int:
        """
        Publish order update (used by Schwab API for order fills/status).
        
        Args:
            account_id: Account identifier
            data: Order data (order_id, symbol, status, etc.)
        """
        from .channels import get_orders_channel
        channel = get_orders_channel(account_id)
        
        payload = {
            "type": "order",
            "account_id": account_id,
            **data
        }
        return self.publish(channel, payload)
    
    def publish_transaction(self, account_id: str, data: Dict[str, Any]) -> int:
        """
        Publish transaction (buy/sell history).
        
        Args:
            account_id: Account identifier
            data: Transaction data (transaction_id, symbol, price, etc.)
        """
        from .channels import get_transactions_channel
        channel = get_transactions_channel(account_id)
        
        payload = {
            "type": "transaction",
            "account_id": account_id,
            **data
        }
        return self.publish(channel, payload)


# Singleton instance
live_data_redis = LiveDataRedis()
