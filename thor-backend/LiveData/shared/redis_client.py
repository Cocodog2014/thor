"""
Shared Redis client for all LiveData broker feeds.

Provides a unified interface for publishing market data to Redis channels.
All broker integrations (Schwab, TOS, IBKR) use this client.
"""

import redis
import json
import logging
from typing import Dict, Any
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
