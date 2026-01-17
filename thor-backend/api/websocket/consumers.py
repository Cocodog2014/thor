"""
WebSocket consumers for real-time market data streaming.

Handles WebSocket connections and broadcasts market status, intraday bars,
quotes, and other real-time data from the heartbeat scheduler.
"""

import json
import logging
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async

from Instruments.services.watchlist_redis_sets import (
    get_watchlists_snapshot_from_redis,
    is_watchlists_hydrated,
    sync_watchlist_sets_to_redis,
)

logger = logging.getLogger(__name__)


class MarketDataConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for streaming real-time market data.
    
    Clients connect to /ws/ endpoint and receive:
    - Market status updates (open/closed)
    - Intraday 1-minute OHLCV bars
    - Quote ticks (price, volume, bid/ask)
    - 24-hour statistics
    - VWAP values
    - Heartbeat messages
    - Error messages
    
    Message Format (from frontend spec):
    {
        "type": "intraday_bar" | "market_status" | "quote_tick" | "heartbeat" | etc.,
        "data": { ...message-specific fields... }
    }
    """
    
    async def connect(self):
        """
        Called when a WebSocket connection is established.
        Joins the broadcast channel layer if available.
        """
        # Join the market data broadcast group if channel layer is configured
        if self.channel_layer:
            try:
                await self.channel_layer.group_add("market_data", self.channel_name)
            except AttributeError:
                pass  # channel_name may not be available in all test scenarios

            # Also join a private per-user group for user-scoped events (e.g. watchlist updates).
            try:
                user = self.scope.get("user")
                if user is not None and getattr(user, "is_authenticated", False):
                    await self.channel_layer.group_add(f"user.{int(user.id)}", self.channel_name)
            except Exception:
                logger.debug("Failed to join user websocket group", exc_info=True)
        
        await self.accept()
        try:
            user = self.scope.get("user")
            client = self.scope.get("client")
            headers = dict(self.scope.get("headers") or [])

            def _hdr(name: bytes) -> str | None:
                try:
                    v = headers.get(name)
                    return v.decode("utf-8", errors="replace") if v else None
                except Exception:
                    return None

            logger.info(
                "WS connect (client=%s authenticated=%s user_id=%s origin=%s ua=%s)",
                client,
                bool(user is not None and getattr(user, "is_authenticated", False)),
                getattr(user, "id", None),
                _hdr(b"origin"),
                _hdr(b"user-agent"),
            )
        except Exception:
            logger.debug("WebSocket client connected", exc_info=True)

        # NOTE:
        # Watchlist membership is sent on explicit client request (watchlists_request).
        # This avoids emitting watchlist_updated on every reconnect/background WS connect.
        self._last_watchlists_snapshot_key = ""
        self._last_watchlists_snapshot_sent_at = 0.0
    
    async def disconnect(self, close_code):
        """
        Called when a WebSocket connection is closed.
        Removes the client from broadcast groups.
        """
        # Leave the market data broadcast group if channel layer is configured
        if self.channel_layer:
            try:
                await self.channel_layer.group_discard("market_data", self.channel_name)
            except AttributeError:
                pass  # channel_name may not be available in all test scenarios

            try:
                user = self.scope.get("user")
                if user is not None and getattr(user, "is_authenticated", False):
                    await self.channel_layer.group_discard(f"user.{int(user.id)}", self.channel_name)
            except Exception:
                logger.debug("Failed to leave user websocket group", exc_info=True)
        logger.debug("WebSocket client disconnected")
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Called when data is received from the WebSocket.
        Currently used for heartbeat acknowledgments (optional).
        """
        if text_data:
            try:
                data = json.loads(text_data)
                message_type = data.get("type")
                
                # Handle client-side heartbeat ACK or ping messages
                if message_type == "ping":
                    try:
                        user = self.scope.get("user")
                        logger.debug(
                            "WS ping received -> pong sent (user_id=%s ts=%s)",
                            getattr(user, "id", None),
                            data.get("timestamp"),
                        )
                    except Exception:
                        # Never let logging break heartbeats.
                        pass
                    await self.send(text_data=json.dumps({
                        "type": "pong",
                        "timestamp": data.get("timestamp")
                    }))
                elif message_type in {"watchlists_request", "watchlist_request", "watchlists_snapshot"}:
                    user = self.scope.get("user")
                    if user is not None and getattr(user, "is_authenticated", False):
                        await self._send_watchlists_snapshot(user_id=int(user.id))
                else:
                    logger.debug(f"Received message from client: {message_type}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from client")

    @database_sync_to_async
    def _ensure_watchlists_hydrated(self, *, user_id: int) -> dict:
        """Ensure Redis has a current watchlists snapshot for this user.

        - If Redis already has members, return it.
        - If the hydrated sentinel is present (known-empty OK), return empty snapshot.
        - Otherwise, cold-cache: hydrate from DB then return snapshot.
        """

        snapshot = get_watchlists_snapshot_from_redis(user_id=int(user_id))
        if snapshot.get("paper") or snapshot.get("live"):
            return snapshot

        if is_watchlists_hydrated(user_id=int(user_id)):
            return snapshot

        sync_watchlist_sets_to_redis(int(user_id))
        return get_watchlists_snapshot_from_redis(user_id=int(user_id))

    async def _send_watchlists_snapshot(self, *, user_id: int) -> None:
        snapshot = await self._ensure_watchlists_hydrated(user_id=int(user_id))

        # Per-connection dedupe: if the client spams watchlists_request, don't resend
        # identical payloads back-to-back.
        try:
            snapshot_key = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        except Exception:
            snapshot_key = ""

        now = time.time()
        if snapshot_key and snapshot_key == getattr(self, "_last_watchlists_snapshot_key", ""):
            # Allow a periodic refresh if needed, but avoid tight loops.
            if now - float(getattr(self, "_last_watchlists_snapshot_sent_at", 0.0)) < 2.0:
                return

        self._last_watchlists_snapshot_key = snapshot_key
        self._last_watchlists_snapshot_sent_at = now

        await self.send(
            text_data=json.dumps(
                {
                    "type": "watchlist_updated",
                    "data": {
                        "user_id": int(user_id),
                        "watchlists": snapshot,
                    },
                }
            )
        )

    def _event_payload(self, event):
        """Normalize a Channels event into the payload sent to the browser."""
        if isinstance(event, dict) and "data" in event:
            return event.get("data")
        if isinstance(event, dict):
            return {k: v for k, v in event.items() if k != "type"}
        return event
    
    # ---- Broadcast message handlers ----
    # These methods are called by the channel layer when messages are sent
    # to the "market_data" group. Method name must match message["type"].
    
    async def intraday_bar(self, event):
        """Broadcast intraday bar update to client."""
        await self.send(text_data=json.dumps({
            "type": "intraday_bar",
            "data": event.get("data")
        }))
    
    async def market_status(self, event):
        """Broadcast market status update to client."""
        await self.send(text_data=json.dumps({
            "type": "market_status",
            "data": event.get("data")
        }))
    
    async def quote_tick(self, event):
        """Broadcast quote tick update to client."""
        await self.send(text_data=json.dumps({
            "type": "quote_tick",
            "data": event.get("data")
        }))

    async def balances(self, event):
        """Broadcast account balances snapshot/update to client."""
        data = self._event_payload(event)
        if isinstance(data, dict):
            inner_type = data.get("type")
            if inner_type in {"balance", "account_balance"}:
                # Reduce confusion: browser routes by envelope type, but keep inner payload consistent.
                data = {**data, "type": "balances"}
        await self.send(text_data=json.dumps({
            "type": "balances",
            "data": data,
        }))

    async def balance(self, event):
        """Normalize singular -> plural so the browser only sees 'balances'."""
        await self.balances(event)

    async def account_balance(self, event):
        """Normalize alias -> plural so the browser only sees 'balances'."""
        await self.balances(event)

    async def positions(self, event):
        """Broadcast positions snapshot/update to client."""
        data = self._event_payload(event)
        if isinstance(data, dict):
            # Optional: if someone sends a single position shape, wrap it consistently.
            if "positions" not in data and "symbol" in data:
                data = {"positions": [data]}

            inner_type = data.get("type")
            if inner_type in {"position", "positions"}:
                data = {**data, "type": "positions"}
        await self.send(text_data=json.dumps({
            "type": "positions",
            "data": data,
        }))

    async def position(self, event):
        """Normalize singular -> plural so the browser only sees 'positions'."""
        await self.positions(event)

    async def orders(self, event):
        """Broadcast orders snapshot/update to client."""
        data = self._event_payload(event)
        if isinstance(data, dict):
            inner_type = data.get("type")
            if inner_type in {"order", "orders"}:
                data = {**data, "type": "orders"}
        await self.send(text_data=json.dumps({
            "type": "orders",
            "data": data,
        }))

    async def order(self, event):
        """Normalize singular -> plural so the browser only sees 'orders'."""
        await self.orders(event)

    async def market_data(self, event):
        """Broadcast batched market data snapshot (quotes array) to client."""
        await self.send(text_data=json.dumps({
            "type": "market_data",
            "data": event.get("data")
        }))
    
    async def twenty_four_hour(self, event):
        """Broadcast 24-hour statistics update to client."""
        await self.send(text_data=json.dumps({
            "type": "twenty_four_hour",
            "data": event.get("data")
        }))

    async def market_24h(self, event):
        """Broadcast live 24h snapshot update to client.

        Channels maps event type names to handler methods by replacing '.' with '_',
        so legacy dotted names will still dispatch here. The preferred wire name is 'market_24h'.
        """
        await self.send(text_data=json.dumps({
            "type": "market_24h",
            "data": event.get("data"),
        }))

    async def market_52w(self, event):
        """Broadcast live 52w snapshot update to client.

        Channels maps event type names to handler methods by replacing '.' with '_',
        so legacy dotted names will still dispatch here. The preferred wire name is 'market_52w'.
        """
        await self.send(text_data=json.dumps({
            "type": "market_52w",
            "data": event.get("data"),
        }))
    
    async def vwap_update(self, event):
        """Broadcast VWAP update to client."""
        await self.send(text_data=json.dumps({
            "type": "vwap_update",
            "data": event.get("data")
        }))
    
    async def heartbeat(self, event):
        """Broadcast heartbeat message to client."""
        await self.send(text_data=json.dumps({
            "type": "heartbeat",
            "data": event.get("data")
        }))

    async def schwab_health(self, event):
        """Broadcast Schwab health snapshot to client."""
        await self.send(text_data=json.dumps({
            "type": "schwab_health",
            "data": self._event_payload(event),
        }))

    async def global_markets_tick(self, event):
        """Broadcast consolidated per-market clock tick to client."""
        await self.send(text_data=json.dumps({
            "type": "global_markets_tick",
            "data": event.get("data")
        }))
    
    async def error_message(self, event):
        """Broadcast error message to client."""
        await self.send(text_data=json.dumps({
            "type": "error_message",
            "data": event.get("data")
        }))

    async def watchlist_updated(self, event):
        """Broadcast watchlist membership/order update (user-scoped)."""
        await self.send(
            text_data=json.dumps({
                "type": "watchlist_updated",
                "data": self._event_payload(event),
            })
        )
